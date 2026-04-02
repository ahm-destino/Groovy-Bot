"""
Ticket tier service for multi-tier ticket management
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from decimal import Decimal

from app.models.ticket_tier import TicketTier
from app.models import Event, Conversation
from app.services.menu import send_back_to_menu
from app.services.interaction_tracking import record_interaction_sent
from sqlalchemy.orm.attributes import flag_modified


def _option_ids(options):
    ids = []
    for opt in options or []:
        if isinstance(opt, dict) and opt.get("id"):
            ids.append(opt["id"])
    return ids


async def _track_interaction(
    db: AsyncSession,
    phone: str,
    conversation: Conversation,
    kind: str,
    context: str,
    options
):
    log = await record_interaction_sent(
        db=db,
        phone=phone,
        kind=kind,
        context=context,
        options=options
    )
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state["last_interaction_id"] = str(log.id)
    conversation.flow_state["last_interaction_option_ids"] = _option_ids(options)
    flag_modified(conversation, "flow_state")
    await db.commit()


async def create_ticket_tiers(
    event_id: str,
    tiers: List[Dict[str, Any]],
    db: AsyncSession
) -> List[TicketTier]:
    """
    Create multiple ticket tiers for an event
    """
    created_tiers = []

    for tier_data in tiers:
        tier = TicketTier(
            event_id=event_id,
            name=tier_data['name'],
            description=tier_data.get('description'),
            price=Decimal(str(tier_data['price'])),
            capacity=tier_data['capacity'],
            sort_order=tier_data.get('sort_order', 0),
            available_from=tier_data.get('available_from'),
            available_until=tier_data.get('available_until')
        )
        db.add(tier)
        created_tiers.append(tier)

    await db.commit()

    for tier in created_tiers:
        await db.refresh(tier)

    return created_tiers


async def get_event_tiers(
    event_id: str,
    db: AsyncSession,
    available_only: bool = False
) -> List[TicketTier]:
    """Get all ticket tiers for an event"""
    query = select(TicketTier).where(
        TicketTier.event_id == event_id
    ).order_by(TicketTier.sort_order)

    if available_only:
        query = query.where(TicketTier.status == 'active')

    result = await db.execute(query)
    tiers = result.scalars().all()

    if available_only:
        tiers = [t for t in tiers if t.is_available()]

    return tiers


async def get_tier_by_id(
    tier_id: str,
    db: AsyncSession
) -> Optional[TicketTier]:
    """Get a specific ticket tier"""
    result = await db.execute(
        select(TicketTier).where(TicketTier.id == tier_id)
    )
    return result.scalar_one_or_none()


async def update_tier_capacity(
    tier_id: str,
    quantity: int,
    db: AsyncSession,
    increment: bool = True
):
    """Update tier tickets sold count"""
    tier = await get_tier_by_id(tier_id, db)

    if not tier:
        raise ValueError("Tier not found")

    if increment:
        tier.tickets_sold = (tier.tickets_sold or 0) + quantity
        if tier.tickets_sold >= tier.capacity:
            tier.status = 'sold_out'
    else:
        tier.tickets_sold = max(0, tier.tickets_sold - quantity)
        if tier.status == 'sold_out' and tier.tickets_sold < tier.capacity:
            tier.status = 'active'

    await db.commit()


async def format_tiers_message(
    event_id: str,
    db: AsyncSession
) -> str:
    """Format ticket tiers for WhatsApp message"""
    tiers = await get_event_tiers(event_id, db, available_only=True)

    if not tiers:
        return "No ticket tiers available"

    message = "Ticket options\n\n"

    for i, tier in enumerate(tiers, 1):
        message += f"{i}. {tier.name}"

        if tier.description:
            message += f"\n   {tier.description}"

        message += f"\n   Price: NGN {tier.price:,.0f}"
        message += f"\n   Available: {tier.remaining_capacity()}/{tier.capacity}"

        if tier.available_until:
            if tier.available_until > datetime.utcnow():
                time_left = tier.available_until - datetime.utcnow()
                if time_left.days > 0:
                    message += f"\n   Available for {time_left.days} more days"
                elif time_left.seconds > 3600:
                    hours = time_left.seconds // 3600
                    message += f"\n   Available for {hours} more hours"

        message += "\n\n"

    message += "Reply with:\n"
    message += "- Book [tier] [quantity] (e.g., Book 1 2)\n"
    message += "- Tier number to see details"

    return message


class TierBookingFlow:
    """Multi-turn flow for booking with tiers"""

    @staticmethod
    async def start_flow(event_id: str, phone: str, db: AsyncSession):
        """Start tier selection flow"""
        from app.models import Conversation

        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return

        tiers = await get_event_tiers(event_id, db, available_only=True)

        if not tiers:
            from app.services.whatsapp import whatsapp_service
            await whatsapp_service.send_message(
                phone,
                "Sorry, no tickets available for this event."
            )
            await send_back_to_menu(phone, db)
            return

        message = await format_tiers_message(event_id, db)

        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)

        conversation.flow_state = {
            'tier_booking': True,
            'event_id': str(event_id),
            'available_tiers': [str(t.id) for t in tiers]
        }
        await db.commit()

        from app.services.whatsapp import whatsapp_service
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)

    @staticmethod
    async def process_selection(
        tier_number: int,
        quantity: int,
        phone: str,
        db: AsyncSession
    ):
        """Process tier selection and quantity"""
        from app.models import Conversation, User
        from app.services.bookings import create_booking
        from app.services.whatsapp import whatsapp_service

        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation or not conversation.flow_state:
            await whatsapp_service.send_message(
                phone,
                "Session expired. Please search for events again."
            )
            await send_back_to_menu(phone, db)
            return

        available_tiers = conversation.flow_state.get('available_tiers', [])

        if tier_number < 1 or tier_number > len(available_tiers):
            await whatsapp_service.send_message(
                phone,
                f"Please select a tier between 1 and {len(available_tiers)}"
            )
            await send_back_to_menu(phone, db)
            return

        tier_id = available_tiers[tier_number - 1]
        tier = await get_tier_by_id(tier_id, db)

        if not tier or not tier.is_available():
            await whatsapp_service.send_message(
                phone,
                "Sorry, this tier is no longer available."
            )
            await send_back_to_menu(phone, db)
            return

        if quantity > tier.remaining_capacity():
            await whatsapp_service.send_message(
                phone,
                f"Only {tier.remaining_capacity()} tickets available for {tier.name}"
            )
            await send_back_to_menu(phone, db)
            return

        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(phone=phone)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        from app.models import Booking
        total_amount = tier.price * quantity

        booking = Booking(
            user_id=user.id,
            event_id=tier.event_id,
            phone=phone,
            quantity=quantity,
            total_amount=total_amount,
            status='pending',
            booking_source='whatsapp',
            tier_id=tier.id
        )

        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        await update_tier_capacity(tier_id, quantity, db, increment=True)

        result = await db.execute(
            select(Event).where(Event.id == tier.event_id)
        )
        event = result.scalar_one()

        message = "Booking summary\n\n"
        message += f"Event: {event.title}\n"
        message += f"Tier: {tier.name}\n"
        message += f"Tickets: {quantity} x NGN {tier.price:,.0f}\n\n"
        message += f"Total: NGN {booking.total_amount:,.0f}\n\n"
        message += "Choose payment method:"

        buttons = [
            {"id": f"pay_card_{booking.id}", "title": "Card"},
            {"id": f"pay_bank_{booking.id}", "title": "Transfer"},
            {"id": f"pay_ussd_{booking.id}", "title": "USSD"}
        ]
        await whatsapp_service.send_interactive(
            phone=phone,
            message=message,
            buttons=buttons
        )
        await _track_interaction(
            db=db,
            phone=phone,
            conversation=conversation,
            kind="button",
            context="tier_payment_method",
            options=buttons
        )
        await send_back_to_menu(phone, db)

        conversation.flow_state = {
            'booking_id': str(booking.id),
            'step': 'payment_method'
        }
        await db.commit()
