"""
Gift tickets service for purchasing and sending tickets as gifts
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime
from decimal import Decimal

from app.models import Booking, Ticket, Event, User, Conversation
from app.services.whatsapp import whatsapp_service
from app.services.payments import flutterwave_service
from app.services.interaction_tracking import record_interaction_sent
from app.services.menu import send_back_to_menu


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


async def create_gift_booking(
    sender_id: str,
    event_id: str,
    recipient_phone: str,
    quantity: int,
    gift_message: str,
    sender_phone: str,
    db: AsyncSession
) -> Booking:
    """
    Create a booking for gift tickets
    
    Args:
        sender_id: Gift sender's user ID
        event_id: Event UUID
        recipient_phone: Recipient's phone number
        quantity: Number of tickets
        gift_message: Personal message from sender
        sender_phone: Sender's phone number
        db: Database session
    
    Returns:
        Booking object
    """
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one()
    
    # Check availability
    available = event.capacity - (event.tickets_sold or 0)
    if available < quantity:
        raise ValueError(f"Only {available} tickets available")
    
    # Calculate total
    total_amount = event.ticket_price * quantity
    
    # Normalize recipient phone
    if not recipient_phone.startswith('+'):
        recipient_phone = '+234' + recipient_phone.lstrip('0')
    
    # Create gift booking
    booking = Booking(
        user_id=sender_id,
        event_id=event_id,
        phone=sender_phone,  # Sender's phone for payment
        quantity=quantity,
        total_amount=total_amount,
        status='pending',
        booking_source='whatsapp',
        is_gift=True,
        gift_sender_id=sender_id,
        gift_recipient_phone=recipient_phone,
        gift_message=gift_message,
        gift_redeemed=False
    )
    
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    # Reserve tickets
    event.tickets_sold = (event.tickets_sold or 0) + quantity
    await db.commit()
    
    return booking


async def deliver_gift_tickets(
    booking_id: str,
    db: AsyncSession
):
    """
    Deliver gift tickets to recipient after payment confirmation
    """
    # Get booking
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one()
    
    if not booking.is_gift:
        raise ValueError("This is not a gift booking")
    
    if booking.gift_redeemed:
        raise ValueError("Gift already delivered")
    
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == booking.event_id)
    )
    event = result.scalar_one()
    
    # Get sender
    result = await db.execute(
        select(User).where(User.id == booking.gift_sender_id)
    )
    sender = result.scalar_one()
    
    # Get or create recipient user
    result = await db.execute(
        select(User).where(User.phone == booking.gift_recipient_phone)
    )
    recipient = result.scalar_one_or_none()
    
    if not recipient:
        recipient = User(phone=booking.gift_recipient_phone)
        db.add(recipient)
        await db.commit()
        await db.refresh(recipient)
    
    # Generate tickets for recipient
    from app.services.tickets import generate_tickets_for_booking
    
    # Temporarily change booking user to recipient
    original_user_id = booking.user_id
    booking.user_id = recipient.id
    await db.commit()
    
    tickets: List[Ticket] = await generate_tickets_for_booking(booking, db)  # type: ignore
    
    for ticket in tickets:
        ticket.is_gift = True
        ticket.gift_from_name = f"{sender.first_name} {sender.last_name}" if sender.first_name else sender.phone
        ticket.gift_message = booking.gift_message
    
    await db.commit()
    
    # Restore original user (sender) for booking record
    booking.user_id = original_user_id
    booking.gift_redeemed = True
    booking.gift_redeemed_at = datetime.utcnow()
    await db.commit()
    
    # Send gift to recipient
    await send_gift_notification(
        recipient_phone=booking.gift_recipient_phone,
        sender_name=f"{sender.first_name} {sender.last_name}" if sender.first_name else "Someone",
        event=event,
        tickets=tickets,
        gift_message=booking.gift_message,
        db=db
    )
    
    # Notify sender
    sender_message = (
        "Gift delivered.\n\n"
        f"Event: {event.title}\n"
        f"Recipient: {booking.gift_recipient_phone}\n"
        f"Tickets: {booking.quantity}x"
    )
    await whatsapp_service.send_message(sender.phone, sender_message)


async def send_gift_notification(
    recipient_phone: str,
    sender_name: str,
    event: Event,
    tickets: List[Ticket],
    gift_message: str,
    db: AsyncSession
):
    """Send gift notification to recipient"""
    message = (
        f"You received tickets from {sender_name}\n"
        f"Event: {event.title}\n"
        f"Date: {event.event_date.strftime('%b %d, %Y at %I:%M %p')}\n"
    )
    
    if gift_message:
        message += f"Message: {gift_message}\n"
    
    message += "\nTickets:\n"
    for ticket in tickets:
        message += f"- {ticket.ticket_code}\n"
    
    message += "\nType My tickets to view QR codes."
    await whatsapp_service.send_message(recipient_phone, message)


async def get_gift_history(
    user_id: str,
    db: AsyncSession,
    sent: bool = True
) -> List[Booking]:
    """Get gift history for a user"""
    if sent:
        result = await db.execute(
            select(Booking).where(
                and_(
                    Booking.gift_sender_id == user_id,
                    Booking.is_gift == True
                )
            ).order_by(Booking.created_at.desc())
        )
        return result.scalars().all()
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return []
    
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.gift_recipient_phone == user.phone,
                Booking.is_gift == True
            )
        ).order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


async def format_gift_summary(
    booking: Booking,
    event: Event,
    is_sender: bool = True
) -> str:
    """Format gift booking summary"""
    if is_sender:
        message = f"Gift to: {booking.gift_recipient_phone}\n"
    else:
        message = "Gift received\n"
    
    message += f"Event: {event.title}\n"
    message += f"Tickets: {booking.quantity}x\n"
    
    if booking.gift_message:
        message += f"Message: {booking.gift_message[:50]}\n"
    
    if booking.gift_redeemed:
        message += "Status: Delivered"
    else:
        message += "Status: Pending"
    
    return message


class GiftTicketFlow:
    """Multi-turn flow for purchasing gift tickets"""
    
    @staticmethod
    async def start_flow(event_id: str, phone: str, db: AsyncSession):
        """Start gift ticket purchase flow"""
        # Get event
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await whatsapp_service.send_message(phone, "Event not found.")
            return
        
        # Check availability
        available = event.capacity - (event.tickets_sold or 0)
        if available <= 0:
            await whatsapp_service.send_message(
                phone,
                f"Sorry, {event.title} is sold out."
            )
            return
        
        message = (
            "Gift tickets\n\n"
            f"Event: {event.title}\n"
            f"Price: NGN {event.ticket_price:,.0f} per ticket\n"
            f"Available: {available} tickets\n\n"
            "How many tickets?"
        )
        
        # Save to conversation state
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)
        
        conversation.current_flow = 'gift_ticket'
        conversation.flow_state = {
            'step': 'quantity',
            'event_id': str(event_id)
        }
        await db.commit()
        
        rows = [
            {"id": "gift_qty:1", "title": "1 ticket", "description": "Single gift"},
            {"id": "gift_qty:2", "title": "2 tickets", "description": "Pair"},
            {"id": "gift_qty:3", "title": "3 tickets", "description": "Small group"},
            {"id": "gift_qty:4", "title": "4 tickets", "description": "Group"},
            {"id": "gift_qty:5", "title": "5 tickets", "description": "Larger group"},
            {"id": "gift_qty:other", "title": "Other", "description": "Type a number"},
            {"id": "action:menu", "title": "Main menu", "description": "Back to menu"}
        ]

        await whatsapp_service.send_list(
            phone=phone,
            message=message,
            button_text="Choose quantity",
            sections=[
                {
                    "title": "Quantity",
                    "rows": rows
                }
            ]
        )
        await _track_interaction(
            db=db,
            phone=phone,
            conversation=conversation,
            kind="list",
            context="gift_quantity",
            options=rows
        )
    
    @staticmethod
    async def process_step(phone: str, message: str, db: AsyncSession):
        """Process gift ticket flow step"""
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation or not conversation.flow_state:
            await whatsapp_service.send_message(
                phone,
                "Session expired. Try: \"Gift ticket\""
            )
            return
        
        step = conversation.flow_state.get('step')
        
        if step == 'quantity':
            await GiftTicketFlow._handle_quantity(
                phone, message, conversation, db
            )
        elif step == 'recipient':
            await GiftTicketFlow._handle_recipient(
                phone, message, conversation, db
            )
        elif step == 'message':
            await GiftTicketFlow._handle_message(
                phone, message, conversation, db
            )
    
    @staticmethod
    async def _handle_quantity(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle quantity input"""
        try:
            raw = message.strip()
            if raw.startswith("gift_qty:"):
                choice = raw.split(":", 1)[1]
                if choice == "other":
                    await whatsapp_service.send_message(
                        phone,
                        "Type the number of tickets you want."
                    )
                    await send_back_to_menu(phone, db)
                    return
                raw = choice
            
            quantity = int(raw)
            
            if quantity < 1:
                await whatsapp_service.send_message(
                    phone,
                    "Enter a valid quantity (1 or more)."
                )
                await send_back_to_menu(phone, db)
                return
            
            # Check availability
            event_id = conversation.flow_state.get('event_id')
            result = await db.execute(
                select(Event).where(Event.id == event_id)
            )
            event = result.scalar_one()
            
            available = event.capacity - (event.tickets_sold or 0)
            if quantity > available:
                await whatsapp_service.send_message(
                    phone,
                    f"Only {available} tickets left. Enter a smaller number."
                )
                await send_back_to_menu(phone, db)
                return
            
            # Save and move to next step
            conversation.flow_state['quantity'] = quantity
            conversation.flow_state['step'] = 'recipient'
            flag_modified(conversation, 'flow_state')
            await db.commit()
            
            total = event.ticket_price * quantity
            
            message = (
                f"Nice. {quantity} ticket(s).\n"
                f"Total: NGN {total:,.0f}\n\n"
                "Who should receive it?\n"
                "Send phone number: +234XXXXXXXXXX or 0XXXXXXXXXX"
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)
            
        except ValueError:
            await whatsapp_service.send_message(
                phone,
                "Enter a valid number."
            )
            await send_back_to_menu(phone, db)
    
    @staticmethod
    async def _handle_recipient(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle recipient phone input"""
        recipient_phone = message.strip()
        
        # Normalize phone
        if not recipient_phone.startswith('+'):
            recipient_phone = '+234' + recipient_phone.lstrip('0')
        
        # Validate format
        if len(recipient_phone) < 13:
            await whatsapp_service.send_message(
                phone,
                "Invalid number. Use +234XXXXXXXXXX or 0XXXXXXXXXX."
            )
            await send_back_to_menu(phone, db)
            return
        
        # Check if gifting to self
        if recipient_phone == phone:
            await whatsapp_service.send_message(
                phone,
                "You cannot gift tickets to yourself. Try a different number."
            )
            await send_back_to_menu(phone, db)
            return
        
        # Save and move to next step
        conversation.flow_state['recipient_phone'] = recipient_phone
        conversation.flow_state['step'] = 'message'
        flag_modified(conversation, 'flow_state')
        await db.commit()
        
        message = (
            f"Sending to: {recipient_phone}\n\n"
            "Add a short message? (optional)"
        )
        await whatsapp_service.send_message(phone, message)

        buttons = [
            {"id": "gift_skip", "title": "Skip message"},
            {"id": "action:menu", "title": "Menu"}
        ]
        await whatsapp_service.send_interactive(
            phone=phone,
            message="You can skip this step.",
            buttons=buttons
        )
        await _track_interaction(
            db=db,
            phone=phone,
            conversation=conversation,
            kind="button",
            context="gift_message_skip",
            options=buttons
        )
    
    @staticmethod
    async def _handle_message(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle gift message input"""
        from app.services.user_registration import check_user_registration_status
        
        gift_message = message.strip()
        
        # Check if skipping
        if gift_message.lower() in ['skip', 'no', 'none'] or gift_message == 'gift_skip':
            gift_message = ""
        
        # Get user
        status = await check_user_registration_status(phone, db)
        if not status['registered']:
            await whatsapp_service.send_message(
                phone,
                "Please register first. Type Hi to get started."
            )
            await send_back_to_menu(phone, db)
            return
        
        user = status['user']
        
        # Create gift booking
        event_id = conversation.flow_state.get('event_id')
        quantity = conversation.flow_state.get('quantity')
        recipient_phone = conversation.flow_state.get('recipient_phone')
        
        try:
            booking = await create_gift_booking(
                sender_id=str(user.id),
                event_id=event_id,
                recipient_phone=recipient_phone,
                quantity=quantity,
                gift_message=gift_message,
                sender_phone=phone,
                db=db
            )
            
            # Get event
            result = await db.execute(
                select(Event).where(Event.id == event_id)
            )
            event = result.scalar_one()
            
            summary = (
                "Gift summary\n\n"
                f"Event: {event.title}\n"
                f"Tickets: {quantity}x\n"
                f"Recipient: {recipient_phone}\n"
            )
            
            if gift_message:
                summary += f"Message: {str(gift_message)[:100]}\n"
            
            summary += f"\nTotal: NGN {booking.total_amount:,.0f}\n\n"
            summary += "Choose payment method:"
            
            buttons = [
                {"id": f"pay_card_{booking.id}", "title": "Card"},
                {"id": f"pay_bank_{booking.id}", "title": "Transfer"},
                {"id": f"pay_ussd_{booking.id}", "title": "USSD"}
            ]
            await whatsapp_service.send_interactive(
                phone=phone,
                message=summary,
                buttons=buttons
            )
            await _track_interaction(
                db=db,
                phone=phone,
                conversation=conversation,
                kind="button",
                context="gift_payment_method",
                options=buttons
            )
            
            # Clear flow
            conversation.current_flow = None
            conversation.flow_state = {
                'booking_id': str(booking.id),
                'step': 'payment_method'
            }
            await db.commit()
            
        except ValueError:
            await whatsapp_service.send_message(phone, "That did not work. Please try again.")
            await send_back_to_menu(phone, db)
        except Exception:
            await whatsapp_service.send_message(
                phone,
                "Something went wrong. Please try again."
            )
            await send_back_to_menu(phone, db)
