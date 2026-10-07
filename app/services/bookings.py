from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.models import Booking, Event, User
from app.services.payments import flutterwave_service
from app.services.tickets import generate_tickets_for_booking
from app.services.whatsapp import whatsapp_service
from app.services.menu import send_back_to_menu


async def create_booking(
    user_id: str,
    event_id: str,
    phone: str,
    quantity: int,
    db: AsyncSession
) -> Booking:
    """
    Create a new booking (reserves tickets for 15 minutes).

    Reservation is a single conditional UPDATE, so the capacity check and the
    increment happen atomically inside the database. Two buyers racing for the
    last seat can no longer both pass the check and oversell the event.
    """
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    event = (await db.execute(
        select(Event).where(Event.id == event_id)
    )).scalar_one()

    # Atomic reserve: only updates while enough capacity remains. If no row
    # matches, the event is sold out for this quantity.
    reserve = await db.execute(
        update(Event)
        .where(
            Event.id == event_id,
            func.coalesce(Event.tickets_sold, 0) + quantity <= Event.capacity
        )
        .values(tickets_sold=func.coalesce(Event.tickets_sold, 0) + quantity)
    )

    if reserve.rowcount == 0:
        await db.rollback()
        remaining = event.capacity - (event.tickets_sold or 0)
        raise ValueError(f"Only {max(remaining, 0)} tickets available")

    total_amount = event.ticket_price * quantity

    booking = Booking(
        user_id=user_id,
        event_id=event_id,
        phone=phone,
        quantity=quantity,
        total_amount=total_amount,
        status='pending',
        booking_source='whatsapp'
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return booking


async def initiate_payment(
    booking_id: str,
    payment_method: str,
    db: AsyncSession
) -> dict:
    """
    Initialize payment for a booking
    """
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one()

    result = await db.execute(
        select(User).where(User.id == booking.user_id)
    )
    user = result.scalar_one()

    reference = f"GRV-{booking.id.hex[:12].upper()}"

    channels_map = {
        'card': ['card'],
        'bank': ['bank', 'bank_transfer'],
        'ussd': ['ussd'],
        'mobile_money': ['mobile_money']
    }
    channels = channels_map.get(payment_method, ['card', 'bank', 'ussd', 'mobile_money'])

    payment_data = await flutterwave_service.initialize_transaction(
        email=user.email or f"{booking.phone}@grooovy.app",
        amount=booking.total_amount,
        reference=reference,
        metadata={
            'booking_id': str(booking.id),
            'event_id': str(booking.event_id),
            'phone': booking.phone,
            'quantity': booking.quantity
        },
        channels=channels
    )

    booking.payment_reference = reference
    booking.payment_method = payment_method
    await db.commit()

    return {
        'payment_url': payment_data['authorization_url'],
        'reference': reference,
        'expires_at': datetime.now() + timedelta(minutes=15)
    }


async def instant_book(
    user_id: str,
    event_id: str,
    phone: str,
    quantity: int,
    db: AsyncSession
) -> dict:
    """
    Instant booking without payment (for testing/demo)
    Directly creates and confirms booking, generates tickets
    """
    try:
        # Create booking
        booking = await create_booking(
            user_id=user_id,
            event_id=event_id,
            phone=phone,
            quantity=quantity,
            db=db
        )
        
        # Instantly confirm booking (no payment needed)
        booking.status = 'confirmed'
        booking.confirmed_at = datetime.now()
        booking.payment_method = 'instant_demo'
        booking.payment_reference = f'demo_{booking.id}'
        await db.commit()
        
        # Generate tickets immediately
        tickets = await generate_tickets_for_booking(
            booking=booking,
            db=db
        )
        
        # Get event for details
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one()
        
        return {
            'success': True,
            'booking_id': str(booking.id),
            'event': event,
            'quantity': quantity,
            'total_amount': booking.total_amount,
            'tickets': tickets,
            'message': f'✅ Booking confirmed! You have {quantity} ticket(s) for {event.title}.'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Booking failed: {str(e)}'
        }


async def confirm_payment(
    reference: str,
    db: AsyncSession
) -> dict:
    """
    Confirm payment and generate tickets.

    Safe to call more than once for the same reference: Paystack retries its
    webhook, so an already-confirmed booking is returned without re-issuing
    tickets or re-sending the confirmation.
    """
    payment_data = await flutterwave_service.verify_transaction(reference)

    if payment_data.get('status') != 'success':
        return {
            'success': False,
            'message': 'Payment not successful',
            'booking': None,
            'tickets': []
        }

    result = await db.execute(
        select(Booking).where(Booking.payment_reference == reference)
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        return {
            'success': False,
            'message': 'Booking not found for reference',
            'booking': None,
            'tickets': []
        }

    # Idempotency: don't double-confirm or re-issue tickets on webhook retries.
    if booking.status == 'confirmed':
        return {
            'success': True,
            'booking': booking,
            'tickets': [],
            'already_confirmed': True
        }

    # Guard against underpayment / tampering. Flutterwave amounts are in whole
    # Naira (verify_transaction returns them as a Decimal), so compare directly.
    paid_amount = payment_data.get('amount')
    if paid_amount is not None:
        try:
            if Decimal(str(paid_amount)) < booking.total_amount - Decimal('0.01'):
                return {
                    'success': False,
                    'message': 'Amount paid does not match booking total',
                    'booking': booking,
                    'tickets': []
                }
        except (InvalidOperation, TypeError, ValueError):
            pass

    booking.status = 'confirmed'
    booking.confirmed_at = datetime.now()
    await db.commit()

    tickets = await generate_tickets_for_booking(booking, db)
    await send_booking_confirmation(booking, tickets, db)

    return {
        'success': True,
        'booking': booking,
        'tickets': tickets
    }


async def send_booking_confirmation(
    booking: Booking,
    tickets: list,
    db: AsyncSession
):
    """Send booking confirmation and tickets via WhatsApp"""
    result = await db.execute(
        select(Event).where(Event.id == booking.event_id)
    )
    event = result.scalar_one()

    if booking.is_gift and not booking.gift_redeemed:
        from app.services.gift_tickets import deliver_gift_tickets
        await deliver_gift_tickets(str(booking.id), db)
        return

    message = (
        "Payment confirmed.\n\n"
        f"Booking ID: #GRV-{booking.id.hex[:8].upper()}\n"
        f"Event: {event.title}\n"
        f"Tickets: {len(tickets)}x\n"
        f"Total: NGN {booking.total_amount:,.0f}\n\n"
        "Receipt sent to your email.\n"
        "Your tickets are ready."
    )

    await whatsapp_service.send_message(booking.phone, message)

    for i, ticket in enumerate(tickets, 1):
        caption = f"Ticket {i}: {ticket.ticket_code}\n"
        caption += "Show at venue entrance\n"
        caption += "Works offline"

        if ticket.entry_code and event.location_revealed:
            caption += f"\nEntry code: {ticket.entry_code}"

        await whatsapp_service.send_image(
            phone=booking.phone,
            image_url=ticket.qr_code_url,
            caption=caption
        )
    await send_back_to_menu(booking.phone, db)


async def cancel_booking(
    booking_id: str,
    reason: str,
    db: AsyncSession
) -> dict:
    """
    Cancel a booking and initiate refund
    """
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one()

    if booking.status != 'confirmed':
        return {
            'success': False,
            'message': 'Only confirmed bookings can be cancelled'
        }

    result = await db.execute(
        select(Event).where(Event.id == booking.event_id)
    )
    event = result.scalar_one()

    if event.event_date < datetime.now():
        return {
            'success': False,
            'message': 'Cannot cancel past events'
        }

    try:
        await flutterwave_service.initiate_refund(
            transaction_reference=booking.payment_reference,
            reason=reason
        )
    except Exception:
        return {
            'success': False,
            'message': 'Refund failed'
        }

    booking.status = 'cancelled'
    booking.cancelled_at = datetime.now()

    from app.models import Ticket
    result = await db.execute(
        select(Ticket).where(Ticket.booking_id == booking.id)
    )
    tickets = result.scalars().all()

    for ticket in tickets:
        ticket.status = 'cancelled'

    event.tickets_sold = (event.tickets_sold or 0) - booking.quantity
    await db.commit()

    message = (
        "Booking cancelled.\n\n"
        f"Booking ID: #GRV-{booking.id.hex[:8].upper()}\n"
        f"Refund: NGN {booking.total_amount:,.0f}\n\n"
        "Refund will be processed within 5-7 business days."
    )
    await whatsapp_service.send_message(booking.phone, message)

    return {
        'success': True,
        'message': 'Booking cancelled and refund initiated'
    }


async def cleanup_expired_bookings(db: AsyncSession):
    """
    Release tickets from expired pending bookings
    (Run as scheduled task every 5 minutes)
    """
    from sqlalchemy import and_

    cutoff_time = datetime.now() - timedelta(minutes=15)

    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.status == 'pending',
                Booking.booked_at < cutoff_time
            )
        )
    )
    expired_bookings = result.scalars().all()

    for booking in expired_bookings:
        result = await db.execute(
            select(Event).where(Event.id == booking.event_id)
        )
        event = result.scalar_one()
        event.tickets_sold = (event.tickets_sold or 0) - booking.quantity

        booking.status = 'expired'
        booking.cancelled_at = datetime.now()

    await db.commit()

    return len(expired_bookings)
