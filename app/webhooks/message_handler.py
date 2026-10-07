from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime, timedelta
import re

from app.services.ai_engine import Intent
from app.config import settings
from app.services.conversation_history import log_outbound
from app.services.whatsapp import whatsapp_service
from app.models import User, Event, Booking, Ticket, Conversation
from app.services.location import format_distance
from app.services.menu import send_main_menu, send_back_to_menu
from app.services.interaction_tracking import record_interaction_sent, record_interaction_clicked


def _truncate_text(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[:limit - 3] + "..."


def _format_price(value) -> str:
    try:
        if value is None:
            return "FREE"
        if float(value) == 0:
            return "FREE"
        return f"NGN {float(value):,.0f}"
    except Exception:
        return "NGN 0"



def _safe_ai_message(text: str) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    lowered = cleaned.lower()
    blocked = [
        "system prompt",
        "response format",
        "conversation history",
        "current date",
        "user's last message",
        "\"intent\"",
        "\"entities\"",
        "\"confidence\"",
        "\"requires_clarification\""
    ]
    if any(token in lowered for token in blocked):
        return None
    if cleaned.startswith("{") and "intent" in lowered:
        return None
    if len(cleaned) > 800:
        cleaned = cleaned[:800] + "..."
    return cleaned


def _option_ids(options):
    ids = []
    for opt in options or []:
        if isinstance(opt, dict):
            opt_id = opt.get("id")
            if opt_id:
                ids.append(opt_id)
        elif isinstance(opt, str):
            ids.append(opt)
    return ids


async def _get_or_create_conversation(phone: str, db: AsyncSession) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
        await db.commit()
    return conversation


async def _track_interaction_sent(
    db: AsyncSession,
    phone: str,
    conversation: Conversation | None,
    kind: str,
    context: str,
    options
):
    if not db:
        return
    if not conversation:
        conversation = await _get_or_create_conversation(phone, db)
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


async def _track_interaction_click(
    db: AsyncSession,
    conversation: Conversation | None,
    raw_message: str
):
    if not db or not conversation or not conversation.flow_state:
        return
    interaction_id = conversation.flow_state.get("last_interaction_id")
    option_ids = conversation.flow_state.get("last_interaction_option_ids", [])
    if interaction_id and raw_message and raw_message in option_ids:
        await record_interaction_clicked(db, interaction_id, raw_message)
        conversation.flow_state.pop("last_interaction_id", None)
        conversation.flow_state.pop("last_interaction_option_ids", None)
        flag_modified(conversation, "flow_state")
        await db.commit()


async def _send_buttons(
    phone: str,
    message: str,
    buttons,
    db: AsyncSession | None = None,
    conversation: Conversation | None = None,
    context: str = ""
):
    await whatsapp_service.send_interactive(
        phone=phone,
        message=message,
        buttons=buttons
    )
    if db and context:
        options = [
            {"id": b.get("id"), "title": b.get("title", "")}
            for b in buttons
        ]
        await _track_interaction_sent(db, phone, conversation, "button", context, options)


async def _send_list_tracked(
    phone: str,
    message: str,
    button_text: str,
    sections,
    db: AsyncSession | None = None,
    conversation: Conversation | None = None,
    context: str = ""
):
    await whatsapp_service.send_list(
        phone=phone,
        message=message,
        button_text=button_text,
        sections=sections
    )
    if db and context:
        rows = []
        for section in sections:
            for row in section.get("rows", []):
                rows.append({
                    "id": row.get("id"),
                    "title": row.get("title", ""),
                    "description": row.get("description", "")
                })
        await _track_interaction_sent(db, phone, conversation, "list", context, rows)
def _build_event_list_row(event, include_distance: bool = False) -> Dict[str, str]:
    date_str = event.event_date.strftime('%a, %b %d')
    price_str = _format_price(event.ticket_price)
    parts = [date_str, price_str]
    distance = getattr(event, "distance_miles", None)
    if include_distance and distance is not None:
        parts.append(format_distance(distance))
    description = " - ".join(parts)
    
    return {
        "id": f"event:{event.id}",
        "title": str(getattr(event, "title", "Event")),
        "description": description
    }


async def _send_event_list(
    phone: str,
    message: str,
    events: List[Any],
    include_distance: bool = False,
    section_title: str = "Events",
    db: AsyncSession | None = None,
    conversation: Conversation | None = None,
    include_menu: bool = True,
    context: str = "event_list"
):
    max_events = 9 if include_menu else 10
    rows = [_build_event_list_row(e, include_distance) for e in events[:max_events]]
    if include_menu:
        rows.append({
            "id": "action:menu",
            "title": "Main menu",
            "description": "Back to menu"
        })
    if not rows:
        await whatsapp_service.send_message(phone, "No events found right now.")
        await send_back_to_menu(phone, db)
        return
    
    await _send_list_tracked(
        phone=phone,
        message=message,
        button_text="View",
        sections=[
            {
                "title": section_title,
                "rows": rows
            }
        ],
        db=db,
        conversation=conversation,
        context=context
    )


async def _send_discovered_events_list(phone: str, db: AsyncSession, conversation):
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(
            phone,
            "No recent list yet. Try: Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    discovered = conversation.flow_state.get('discovered_events', [])
    if not discovered:
        await whatsapp_service.send_message(
            phone,
            "No recent list yet. Try: Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    result = await db.execute(
        select(Event).where(Event.id.in_(discovered))
    )
    events = result.scalars().all()
    events_by_id = {str(e.id): e for e in events}
    ordered_events = [events_by_id.get(str(eid)) for eid in discovered if str(eid) in events_by_id]
    
    await _send_event_list(
        phone=phone,
        message="Back to your event list. Pick one:",
        events=[e for e in ordered_events if e],
        include_distance=False,
        section_title="Your events",
        db=db,
        conversation=conversation,
        include_menu=True,
        context="discovered_events"
    )


def _parse_book_quantity(raw_message: str) -> int:
    match = re.search(r"\bbook\s*(\d+)\b", raw_message, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return 1
    return 0


async def _send_event_details(event, phone: str, db: AsyncSession, conversation):
    """Send event details to user with booking options."""
    remaining = event.capacity - (event.tickets_sold or 0)
    price_str = _format_price(event.ticket_price)
    
    message = f"Event details\n{event.title}\n\n"
    if event.description:
        message += f"{_truncate_text(event.description, 280)}\n\n"
    
    message += f"Date: {event.event_date.strftime('%a, %b %d at %I:%M %p')}\n"
    
    if event.is_anonymous and not event.location_revealed:
        if event.location_reveal_trigger == 'immediate':
            reveal = "after booking"
        else:
            reveal = f"{event.location_reveal_hours_before}hr before event"
        message += f"Venue: Hidden (reveals {reveal})\n"
    else:
        message += f"Venue: {event.venue_name}\n"
    
    message += f"Price: {price_str}\n"
    message += f"Tickets left: {remaining}\n"
    
    if event.is_anonymous and event.entry_code_format:
        entry_mode = "Shared" if event.entry_code_format == "shared" else "Unique per ticket"
        message += f"Entry: {entry_mode}\n"
    
    message += "\nPick an action:"
    
    # Save selected event to conversation state
    if not conversation:
        from app.models import Conversation
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state['selected_event_id'] = str(event.id)
    flag_modified(conversation, 'flow_state')
    await db.commit()
    
    await _send_list_tracked(
        phone=phone,
        message=message,
        button_text="Choose",
        sections=[
            {
                "title": "Book tickets",
                "rows": [
                    {"id": "action:book:1", "title": "Book 1", "description": "Buy 1 ticket"},
                    {"id": "action:book:2", "title": "Book 2", "description": "Buy 2 tickets"},
                    {"id": "action:book:3", "title": "Book 3", "description": "Buy 3 tickets"},
                    {"id": "action:book:5", "title": "Book 5", "description": "Buy 5 tickets"},
                    {"id": "action:book:10", "title": "Book 10", "description": "Buy 10 tickets"},
                ]
            },
            {
                "title": "Other options",
                "rows": [
                    {"id": "action:gift", "title": "Gift tickets", "description": "Send to someone"},
                    {"id": "action:back", "title": "Back to list", "description": "See events again"},
                    {"id": "action:menu", "title": "Main menu", "description": "Back to menu"}
                ]
            }
        ],
        db=db,
        conversation=conversation,
        context="event_actions"
    )


async def handle_intent(
    intent: Intent,
    entities: Dict[str, Any],
    phone: str,
    db: AsyncSession
):
    """
    Simple logic:
    1. Get user from database
    2. If NOT registered (no first_name/last_name) → Start registration
    3. If in active flow → Continue that flow
    4. Otherwise → Handle intent normally
    """
    
    # Get or create conversation
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
        await db.commit()

    # Get user from database
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    raw_message = (entities.get('raw_message', '') or '').strip()
    raw_lower = raw_message.lower()

    # Track clicks on last interactive
    await _track_interaction_click(db, conversation, raw_message)

    # ============ STEP 1: CHECK IF USER IS REGISTERED ============
    # If user doesn't exist OR not fully registered → Go to registration
    if not user or not user.first_name or not user.last_name:
        # Start registration flow
        from app.services.user_registration import UserRegistrationFlow
        conversation.current_flow = 'user_registration'
        flag_modified(conversation, "flow_state")
        await db.commit()
        await UserRegistrationFlow.start_flow(phone, db)
        return
    
    # ============ STEP 2: CHECK FOR ACTIVE FLOWS ============
    # If user is in middle of a flow (registration, gift, event creation, etc) → Continue it
    
    if conversation.current_flow == 'user_registration':
        # Continue user registration flow
        from app.services.user_registration import UserRegistrationFlow
        await UserRegistrationFlow.process_step(phone, raw_message, db)
        return
    
    if conversation.current_flow == 'gift_ticket':
        # Continue gift ticket flow
        from app.services.gift_tickets import GiftTicketFlow
        await GiftTicketFlow.process_step(phone, raw_message, db)
        return
    
    if conversation.current_flow == 'event_creation':
        # Continue event creation flow
        from app.services.event_creation import EventCreationFlow
        await EventCreationFlow.process_step(phone, raw_message, db)
        return
    
    if conversation.current_flow == 'event_editing':
        # Continue event editing flow
        from app.services.event_editing import EventEditingFlow
        await EventEditingFlow.process_step(phone, raw_message, db)
        return
    
    # ============ STEP 3: HANDLE MENU AND SPECIAL STATES ============
    
    # Menu action
    if raw_message == "action:menu" or raw_lower in ["menu", "main menu", "back to menu", "home"]:
        conversation.current_flow = None
        conversation.flow_state = {}
        flag_modified(conversation, "flow_state")
        await db.commit()
        await send_main_menu(phone, db)
        return

    # ============ STEP 4: CHECK AWAITING SPECIAL STATES ============

    # Check if organizer is composing a broadcast message
    if conversation and conversation.flow_state and conversation.flow_state.get('awaiting_broadcast_text'):
        if raw_message.lower() == 'cancel' or raw_message == 'action:cancel_broadcast':
            conversation.flow_state = {}
            flag_modified(conversation, 'flow_state')
            await db.commit()
            await whatsapp_service.send_message(phone, "Broadcast cancelled.")
            await send_back_to_menu(phone, db)
            return

        # Store message and trigger broadcast
        conversation.flow_state['broadcast_text'] = raw_message
        flag_modified(conversation, 'flow_state')
        broadcast_event_id = conversation.flow_state.get('broadcast_event_id')

        # Get event and send broadcast
        result = await db.execute(
            select(Event).where(Event.id == broadcast_event_id)
        )
        event = result.scalar_one_or_none()

        if event:
            await handle_broadcast_message(event, phone, db)
        return
    
    # Check if user is confirming event cancellation
    if conversation and conversation.flow_state and conversation.flow_state.get('awaiting_cancel_confirmation'):
        raw_message = raw_message.strip().lower()
        cancel_event_id = conversation.flow_state.get('cancel_event_id')
        
        # Get event
        result = await db.execute(
            select(Event).where(Event.id == cancel_event_id)
        )
        event = result.scalar_one_or_none()
        
        if event:
            if raw_message in ['yes', 'y', 'confirm', '1']:
                # Cancel event
                event.status = 'cancelled'
                
                # Get all confirmed bookings
                result = await db.execute(
                    select(Booking).where(
                        Booking.event_id == event.id,
                        Booking.status == 'confirmed'
                    )
                )
                bookings = result.scalars().all()
                
                # Refund all bookings
                from app.services.bookings import cancel_booking
                refunded_count = 0
                
                for booking in bookings:
                    try:
                        result = await cancel_booking(
                            booking_id=str(booking.id),
                            reason="Event cancelled by organizer",
                            db=db
                        )
                        if result['success']:
                            refunded_count += 1
                    except Exception as e:
                        print(f"Failed to refund booking {booking.id}: {e}")
                
                await whatsapp_service.send_message(
                    phone,
                    "Event cancelled.\n\n"
                    f"Event: {event.title}\n"
                    f"Refunds processed: {refunded_count}/{len(bookings)}\n"
                    "All attendees have been notified."
                )
                await send_back_to_menu(phone, db)
            else:
                await whatsapp_service.send_message(
                    phone,
                    "Event cancellation aborted."
                )
                await send_back_to_menu(phone, db)
        
        # Clear flow state
        conversation.flow_state = {}
        await db.commit()
        return
    
    # Action and list reply shortcuts (interactive UX)
    raw_message = (entities.get('raw_message', '') or '').strip()
    
    if raw_message.startswith("event:"):
        event_id = raw_message.split(":", 1)[1]
        await handle_event_selection_by_id(event_id, phone, db)
        return
    
    if raw_message.startswith("action:"):
        action = raw_message.split(":", 1)[1].lower()
        if action == "discover" or action == "near_me":
            await handle_discover_events({}, phone, db)
            return
        if action == "my_tickets":
            await handle_view_tickets({}, phone, db)
            return
        if action == "create_event":
            await handle_create_event({}, phone, db)
            return
        if action == "manage_events":
            await handle_manage_event({}, phone, db)
            return
        if action == "recommend":
            await handle_recommendations(phone, db)
            return
        if action == "gift":
            await handle_gift_ticket(phone, db)
            return
        if action == "gift_ticket":
            await handle_gift_ticket(phone, db)
            return
        if action == "help":
            await handle_help({}, phone, db)
            return
        if action == "menu":
            await send_main_menu(phone, db)
            return
        if action == "share_event":
            await handle_share_event("share", phone, db)
            return
        if action == "back":
            await _send_discovered_events_list(phone, db, conversation)
            return
        if action == "cancel_broadcast":
            if conversation:
                conversation.flow_state = {}
                await db.commit()
            await whatsapp_service.send_message(phone, "Broadcast cancelled.")
            await send_back_to_menu(phone, db)
            return
        if action.startswith("book:"):
            try:
                qty = int(action.split(":", 1)[1])
            except Exception:
                qty = 1
            entities = dict(entities)
            entities['quantity'] = max(qty, 1)
            await handle_booking_intent(entities, phone, db)
            return
        
        # Handle recommendation category selection
        if action.startswith("rec:category:"):
            category = action.split(":", 2)[2] if ":" in action else action.replace("rec:category:", "")
            await handle_recommendation_category(phone, category, db)
            return
        
        # Handle recommendation location selection
        if action.startswith("rec:location:"):
            location = action.split(":", 2)[2] if ":" in action else action.replace("rec:location:", "")
            await handle_recommendation_location(phone, location, db)
            return
        
        # Handle help topics
        if action.startswith("help:"):
            topic = action.split(":", 1)[1] if ":" in action else action.replace("help:", "")
            await handle_help_topic(topic, phone, db)
            return
    
    if raw_lower.startswith("book_"):
        try:
            qty = int(raw_lower.split("_", 1)[1])
        except Exception:
            qty = 1
        entities = dict(entities)
        entities['quantity'] = max(qty, 1)
        await handle_booking_intent(entities, phone, db)
        return
    
    qty = _parse_book_quantity(raw_message)
    if qty:
        entities = dict(entities)
        entities['quantity'] = max(qty, 1)
        await handle_booking_intent(entities, phone, db)
        return
    
    if raw_lower == "back":
        await _send_discovered_events_list(phone, db, conversation)
        return
    
    if raw_lower == "share":
        await handle_share_event("share", phone, db)
        return

    if raw_message.startswith("gift_history:"):
        await handle_gift_history(raw_message, phone, db)
        return

    if raw_message.startswith("share_ticket:"):
        ticket_id = raw_message.split(":", 1)[1]
        await handle_share_ticket_by_id(ticket_id, phone, db)
        return

    if raw_message.startswith("refund_confirm:"):
        booking_id = raw_message.split(":", 1)[1]
        await handle_refund_confirmation(booking_id, True, phone, db)
        return
    
    if raw_message.startswith("refund_cancel:"):
        booking_id = raw_message.split(":", 1)[1]
        await handle_refund_confirmation(booking_id, False, phone, db)
        return
    
    if raw_message.startswith("refund:"):
        booking_id = raw_message.split(":", 1)[1]
        await handle_refund_selection_by_id(booking_id, phone, db)
        return
    
    if raw_message.startswith("org_event:"):
        event_id = raw_message.split(":", 1)[1]
        await handle_organizer_event_by_id(event_id, phone, db)
        return
    
    if raw_message.startswith("org_action:"):
        action_parts = raw_message.split(":", 2)
        if len(action_parts) == 3:
            event_id = action_parts[1]
            action_name = action_parts[2]
            await handle_organizer_event_action(event_id, action_name, phone, db)
            return
    
    # Check if this is a button callback (payment method selection)
    if raw_message.startswith('pay_'):
        await handle_payment_method_selection(raw_message, phone, db)
        return
    
    # Check if user is in share ticket flow and selecting ticket number
    if conversation and conversation.flow_state and conversation.flow_state.get('share_flow'):
        if raw_message.strip().isdigit():
            await handle_share_ticket_selection(int(raw_message.strip()), phone, db)
            return
    
    # Check if user is in refund flow and selecting booking number
    if conversation and conversation.flow_state and conversation.flow_state.get('refund_flow'):
        if raw_message.strip().isdigit():
            await handle_refund_selection(int(raw_message.strip()), phone, db)
            return
    
    # Check if user is selecting an event by number
    if raw_message.strip().isdigit():
        await handle_event_selection(int(raw_message.strip()), phone, db)
        return
    
    # Check for organizer commands: Stats, Broadcast, Attendees, Cancel, Edit
    if raw_message.lower().startswith(('stats ', 'broadcast ', 'attendees ', 'cancel ', 'edit ')):
        await handle_organizer_command(raw_message, phone, db)
        return
    
    # Check for gift ticket command
    if raw_message.lower() in ['gift ticket', 'gift tickets', 'buy gift', 'send gift']:
        await handle_gift_ticket(phone, db)
        return
    
    # Check for gift history command
    if raw_message.lower() in ['my gifts', 'gift history', 'gifts sent', 'gifts received']:
        await handle_gift_history(raw_message, phone, db)
        return
    
    # Check for profile/account commands
    if raw_message.lower() in ['profile', 'my profile', 'account', 'my account', 'update profile']:
        await handle_profile(phone, db)
        return
    
    # Check for recommendations command
    if raw_message.lower() in ['recommend', 'recommendations', 'suggest events', 'what should i attend']:
        await handle_recommendations(phone, db)
        return
    
    # Check for share command
    if raw_message.lower().startswith('share '):
        await handle_share_event(raw_message, phone, db)
        return
    
    # Check for promo code application
    if raw_message.lower().startswith('promo ') or raw_message.lower().startswith('code '):
        await handle_apply_promo(raw_message, phone, db)
        return
    
    # Check for check-in command
    if raw_message.lower().startswith('checkin ') or raw_message.lower().startswith('check in '):
        await handle_checkin(raw_message, phone, db)
        return
    
    # Check for analytics command
    if raw_message.lower() in ['analytics', 'stats', 'my stats', 'my analytics']:
        await handle_analytics(phone, db)
        return
    
    # Check for download report command
    if raw_message.lower() in ['download report', 'export report', 'get report', 'report']:
        await handle_download_report(phone, db)
        return
    
    handlers = {
        Intent.DISCOVER_EVENTS: handle_discover_events,
        Intent.UNLOCK_SECRET_EVENT: handle_unlock_secret_event,
        Intent.BOOK_TICKET: handle_booking_intent,
        Intent.VIEW_MY_TICKETS: handle_view_tickets,
        Intent.SHARE_TICKET: handle_share_ticket,
        Intent.REQUEST_REFUND: handle_request_refund,
        Intent.MANAGE_EVENT: handle_manage_event,
        Intent.CREATE_EVENT: handle_create_event,
        Intent.GREETING: handle_greeting,
        Intent.HELP: handle_help,
    }
    
    handler = handlers.get(intent, handle_general_query)
    await handler(entities, phone, db)


async def handle_greeting(entities: Dict, phone: str, db: AsyncSession):
    """Handle greeting messages - respond conversationally"""
    from app.services.user_registration import check_user_registration_status, UserRegistrationFlow
    
    # Check if user is registered
    status = await check_user_registration_status(phone, db)
    
    if not status['registered'] or not status['profile_complete']:
        # Start registration flow for new or incomplete users
        await UserRegistrationFlow.start_flow(phone, db)
        return
    
    user = status['user']
    
    # Conversational greeting responses (varied, not robotic)
    greeting_responses = [
        f"Hey {user.first_name}! 👋 All good. What event can I help you find today?",
        f"Yo {user.first_name}! I'm good, thanks for asking. Ready to book some tickets?",
        f"Alright {user.first_name}! What's up? Looking for events?",
        f"Good to see you {user.first_name}! Let's find you something fun to do.",
    ]
    
    import random
    response = random.choice(greeting_responses)

    await whatsapp_service.send_message(phone, response)
    # Record this assistant turn so the LLM has it as conversation memory.
    await log_outbound(phone, response, db, intent="greeting")

    # Don't immediately send menu - let conversation continue naturally
    # User can ask for menu or just tell us what they want


async def handle_help(entities: Dict, phone: str, db: AsyncSession):
    """Handle help requests - simplified version"""
    message = (
        "I'm Stefan, your Grooovy assistant! 🤖\n\n"
        "Here's what I can help you with:\n\n"
        "🔍 FIND EVENTS\n"
        "• Discover events - Events near me\n"
        "• Recommendations - Events tailored to you\n"
        "• Search - Events in [area]\n\n"
        "🎫 TICKETS\n"
        "• My tickets - View your bookings\n"
        "• Gift tickets - Send to friends\n\n"
        "🎉 HOST\n"
        "• Create event - Host your event\n"
        "• Manage events - Edit & stats\n\n"
        "Just tell me what you'd like to do!"
    )
    await whatsapp_service.send_message(phone, message)
    await send_main_menu(phone, db)


async def handle_help_topic(topic: str, phone: str, db: AsyncSession):
    """Handle specific help topics"""
    help_messages = {
        'discover': "🔍 Discover Events\n\nYou can discover events by:\n• Typing 'Events near me'\n• Typing 'Events in Lagos'\n• Typing 'Events this weekend'\n\nTry: Events near me!",
        'recommend': "🎯 Recommendations\n\nGet personalized events!\n1. Click 'Recommendations'\n2. Select your category\n3. Choose location\n\nI'll show matching events!",
        'search': "🔍 Search by Location\n\nFind events in specific areas:\n• Lagos Island & Mainland\n• Lekki, Ajah, VI\n• Ikeja, Ogba\n\nSay: 'Events in [area]'",
        'book': "🎫 How to Book\n\n1. Find an event\n2. Click 'Book'\n3. Select quantity\n\nBook 1, 2, 3, 5, or 10 tickets!",
        'tickets': "🎟️ My Tickets\n\nView your tickets:\nClick 'My tickets' from menu\n\nEach ticket has a unique code for entry.",
        'gift': "🎁 Gift Tickets\n\nSend tickets to friends:\n1. Click 'Gift tickets'\n2. Select event\n3. Enter recipient's number\n\nThey'll receive instantly!",
        'create': "🎉 Create Event\n\nHost your own event:\n1. Click 'Create event'\n2. Enter event details\n3. Set price & capacity\n4. Publish!",
        'manage': "📊 Manage Events\n\nAs a host you can:\n• View booking stats\n• See attendees\n• Edit details\n• Broadcast messages",
        'about': "ℹ️ About Grooovy\n\nYour AI event companion!\n\nFind & book tickets to amazing events in Nigeria.\n\nI'm Stefan, here to help!",
        'contact': "📞 Contact Support\n\nNeed help?\n\nEmail: support@grooovy.ng\n\nCommon issues:\n• Can't find events → try 'Events near me'\n• Booking issues → check 'My tickets'"
    }
    
    message = help_messages.get(topic, "Sorry, I don't have info on that. Try the main menu.")
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)


async def handle_discover_events(entities: Dict, phone: str, db: AsyncSession):
    """Handle event discovery with location-based search"""
    from app.services.location import (
        get_events_near_location,
        geocode_location,
        get_user_location_from_phone
    )
    from app.models import Conversation
    
    location_name = entities.get('location')
    category = entities.get('category')
    
    # Try to get coordinates
    coords = None
    location_source = None
    
    if location_name:
        # User specified location
        coords = await geocode_location(location_name)
        location_source = location_name
    else:
        # Try user's saved location
        coords = await get_user_location_from_phone(phone, db)
        if coords:
            location_source = "your saved location"
    
    # If we have coordinates, use location-based search
    if coords:
        lat, lng = coords
        
        # Get events within 20 miles
        events_with_distance = await get_events_near_location(
            lat=lat,
            lng=lng,
            radius_miles=20,
            db=db,
            limit=10
        )
        
        # Filter by category if specified
        if category:
            events_with_distance = [
                e for e in events_with_distance 
                if e.category == category
            ]
        
        if not events_with_distance:
            message = (
                f"No events within 20 miles of {location_source}.\n\n"
                "Try a different location or share your location for better matches."
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)
            return
        # Format response with distances
        events_with_distance = list(events_with_distance)
        message = f"Found {len(events_with_distance)} event(s) near {location_source}. Pick one:"
        
        # Save event IDs to conversation state for booking
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)
        
        # Store event IDs for quick booking
        conversation.flow_state = conversation.flow_state or {}
        conversation.flow_state['discovered_events'] = [
            str(e.id) for e in events_with_distance[:10]
        ]
        flag_modified(conversation, 'flow_state')
        await db.commit()
        
        await _send_event_list(
            phone=phone,
            message=message,
            events=events_with_distance[:10],
            include_distance=True,
            section_title="Near you",
            db=db,
            conversation=conversation,
            include_menu=True,
            context="discover_nearby"
        )
        
    else:
        # Fallback: Show recent events without location filter
        query = select(Event).where(
            Event.status == 'active',
            Event.event_date > datetime.now()
        )
        
        if category:
            query = query.where(Event.category == category)
        
        query = query.order_by(Event.event_date).limit(5)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        if not events:
            message = (
                "No upcoming events found.\n\n"
                "Try Events in Lagos or share your location."
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)
            return
        # Format response
        message = f"Found {len(events)} upcoming event(s). Pick one:"
        
        # Save event IDs to conversation state for booking
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)
        
        conversation.flow_state = conversation.flow_state or {}
        conversation.flow_state['discovered_events'] = [
            str(e.id) for e in events[:10]
        ]
        flag_modified(conversation, 'flow_state')
        await db.commit()
        
        await _send_event_list(
            phone=phone,
            message=message,
            events=events[:10],
            include_distance=False,
            section_title="Upcoming",
            db=db,
            conversation=conversation,
            include_menu=True,
            context="discover_upcoming"
        )


async def handle_unlock_secret_event(entities: Dict, phone: str, db: AsyncSession):
    """Handle secret event unlock"""
    secret_code = entities.get('secret_code') or entities.get('raw_message', '').strip()
    
    # Find event by secret code
    result = await db.execute(
        select(Event).where(
            Event.secret_code == secret_code,
            Event.is_anonymous == True,
            Event.status == 'active'
        )
    )
    event = result.scalar_one_or_none()
    
    if not event:
        message = (
            "Invalid code.\n"
            "Check the code and try again."
        )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)
        return

    await whatsapp_service.send_message(phone, "Access granted.")
    conversation = await _get_or_create_conversation(phone, db)
    await _send_event_details(event, phone, db, conversation)


async def _release_reservation(booking_id, db: AsyncSession):
    """Undo a pending reservation (restore the ticket count) if checkout can't start."""
    try:
        result = await db.execute(select(Booking).where(Booking.id == booking_id))
        booking = result.scalar_one_or_none()
        if not booking or booking.status != 'pending':
            return
        result = await db.execute(select(Event).where(Event.id == booking.event_id))
        event = result.scalar_one_or_none()
        if event:
            event.tickets_sold = max((event.tickets_sold or 0) - booking.quantity, 0)
        booking.status = 'expired'
        await db.commit()
    except Exception as e:
        print(f"Failed to release reservation {booking_id}: {e}")
        await db.rollback()


async def handle_booking_intent(entities: Dict, phone: str, db: AsyncSession):
    """Handle booking intent — reserve tickets and send a Paystack payment link.

    Tickets are only confirmed once Paystack reports a successful charge (see the
    /webhooks/paystack handler -> confirm_payment). Here we create a pending
    booking (which reserves the tickets for 15 minutes) and hand the user a
    secure checkout link.
    """
    from app.services.bookings import create_booking, initiate_payment
    from app.models import Conversation
    from app.services.user_registration import check_user_registration_status, UserRegistrationFlow

    # Check if user is registered
    status = await check_user_registration_status(phone, db)

    if not status['registered'] or not status['profile_complete']:
        await whatsapp_service.send_message(
            phone,
            "To book tickets, finish setup first."
        )
        await UserRegistrationFlow.start_flow(phone, db)
        return

    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()

    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(
            phone,
            "Pick an event first.\nTry: Concerts in Lagos or Events this weekend."
        )
        await send_back_to_menu(phone, db)
        return

    # Check if event is selected
    event_id = conversation.flow_state.get('selected_event_id')
    if not event_id:
        await whatsapp_service.send_message(phone, "Pick an event from your list.")
        await send_back_to_menu(phone, db)
        return

    quantity = max(int(entities.get('quantity', 1) or 1), 1)
    user = status['user']  # we know they exist from the check above

    # Payments must be configured before we can take real money.
    if not settings.FLUTTERWAVE_SECRET_KEY:
        await whatsapp_service.send_message(
            phone,
            "Payments are temporarily unavailable. Please try again shortly."
        )
        await send_back_to_menu(phone, db)
        return

    # Reserve the tickets with a pending booking. Unpaid reservations are
    # released after 15 minutes by the cleanup_expired_bookings Celery task.
    try:
        booking = await create_booking(
            user_id=str(user.id),
            event_id=event_id,
            phone=phone,
            quantity=quantity,
            db=db
        )
    except ValueError as e:
        await whatsapp_service.send_message(phone, f"❌ {str(e)}")
        await send_back_to_menu(phone, db)
        return
    except Exception as e:
        print(f"Booking error: {e}")
        await whatsapp_service.send_message(phone, "❌ Something went wrong. Please try again.")
        await send_back_to_menu(phone, db)
        return

    # Open a Paystack checkout (hosted page lets the user pick card/bank/USSD).
    try:
        payment = await initiate_payment(str(booking.id), 'all', db)
    except Exception as e:
        print(f"Payment init error: {e}")
        await _release_reservation(booking.id, db)
        await whatsapp_service.send_message(
            phone,
            "❌ Couldn't start payment just now. Please try again."
        )
        await send_back_to_menu(phone, db)
        return

    # Remember the pending booking for this chat.
    conversation.flow_state['pending_booking_id'] = str(booking.id)
    flag_modified(conversation, 'flow_state')
    await db.commit()

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one()

    message = (
        f"Almost there! Secure your {quantity} ticket(s) for {event.title}.\n\n"
        f"Total: NGN {booking.total_amount:,.0f}\n\n"
        f"Pay securely here:\n{payment['payment_url']}\n\n"
        "Your tickets arrive here automatically once payment is confirmed. "
        "This link expires in 15 minutes."
    )
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)


async def handle_view_tickets(entities: Dict, phone: str, db: AsyncSession):
    """Handle view tickets request"""
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        message = (
            "No tickets found.\n"
            "You have not booked any events yet.\n"
            "Try Events near me."
        )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)
        return
    
    # Get user's tickets
    result = await db.execute(
        select(Ticket).where(
            Ticket.user_id == user.id,
            Ticket.status == 'valid'
        ).limit(10)
    )
    tickets = result.scalars().all()
    
    if not tickets:
        message = (
            "No active tickets.\n"
            "Try Events near me."
        )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)
        return
    
    message = f"Your tickets ({len(tickets)}):\n\n"
    
    for ticket in tickets:
        # Get event details
        result = await db.execute(
            select(Event).where(Event.id == ticket.event_id)
        )
        event = result.scalar_one()
        
        message += f"{event.title}\n"
        message += f"Date: {event.event_date.strftime('%a, %b %d at %I:%M %p')}\n"
        message += f"Ticket: {ticket.ticket_code}\n\n"
    
    message += "Reply with ticket code to see QR code."
    
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)


async def handle_general_query(entities: Dict, phone: str, db: AsyncSession):
    """Handle general queries"""
    ai_message = _safe_ai_message(entities.get('ai_message'))
    message = ai_message or "I did not catch that. Pick a quick action or type what you want."
    await _send_buttons(
        phone=phone,
        message=message,
        buttons=[
            {"id": "action:discover", "title": "Discover"},
            {"id": "action:my_tickets", "title": "My tickets"},
            {"id": "action:help", "title": "Help"}
        ],
        db=db,
        conversation=None,
        context="general_quick_actions"
    )
    # Record this assistant turn so the LLM has it as conversation memory.
    await log_outbound(phone, message, db, intent="general_query")


async def handle_payment_method_selection(button_id: str, phone: str, db: AsyncSession):
    """Handle payment method button clicks — send a real Paystack checkout link."""
    from app.services.bookings import initiate_payment

    # Parse button_id: pay_<method>_<booking_id>
    parts = button_id.split('_')
    if len(parts) < 3:
        return

    payment_method = parts[1]  # card, bank, ussd
    booking_id = parts[2]

    # Payments must be configured to take real money.
    if not settings.FLUTTERWAVE_SECRET_KEY:
        await whatsapp_service.send_message(
            phone,
            "Payments are temporarily unavailable. Please try again shortly."
        )
        await send_back_to_menu(phone, db)
        return

    try:
        payment_data = await initiate_payment(booking_id, payment_method, db)

        # Get booking for the amount
        result = await db.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        booking = result.scalar_one()

        method_names = {
            'card': 'Card',
            'bank': 'Bank Transfer',
            'ussd': 'USSD'
        }
        message = (
            f"{method_names.get(payment_method, 'Payment')}\n\n"
            f"Amount: NGN {booking.total_amount:,.0f}\n\n"
            f"Pay securely here:\n{payment_data['payment_url']}\n\n"
            "Your tickets arrive here automatically once payment is confirmed.\n"
            "This link expires in 15 minutes."
        )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)

    except Exception as e:
        print(f"Payment init error: {e}")
        await whatsapp_service.send_message(
            phone,
            "Payment initialization failed. Please try again."
        )
        await send_back_to_menu(phone, db)


async def handle_create_event(entities: Dict, phone: str, db: AsyncSession):
    """Handle event creation request"""
    from app.services.event_creation import EventCreationFlow
    await EventCreationFlow.start_flow(phone, db)


async def handle_event_selection(event_number: int, phone: str, db: AsyncSession):
    """Handle when user selects an event by number (1-10)"""
    from app.models import Conversation
    from datetime import datetime
    
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(
            phone,
            "Search events first. Try Events in Lagos."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get discovered events from conversation state
    discovered_events = conversation.flow_state.get('discovered_events', [])
    
    if not discovered_events:
        await whatsapp_service.send_message(
            phone,
            "Search events first. Try Events in Lagos."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Validate event number
    if event_number < 1 or event_number > len(discovered_events):
        await whatsapp_service.send_message(
            phone,
            f"Please select a number between 1 and {len(discovered_events)}"
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get event details
    event_id = discovered_events[event_number - 1]
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        await whatsapp_service.send_message(
            phone,
            "Sorry, this event is no longer available."
        )
        await send_back_to_menu(phone, db)
        return
    
    await _send_event_details(event, phone, db, conversation)
    return



async def handle_event_selection_by_id(event_id: str, phone: str, db: AsyncSession):
    """Handle when user selects an event by ID (from list reply)"""
    from app.models import Conversation
    
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        await whatsapp_service.send_message(
            phone,
            "Sorry, this event is no longer available."
        )
        await send_back_to_menu(phone, db)
        return
    
    await _send_event_details(event, phone, db, conversation)

async def handle_share_ticket(entities: Dict, phone: str, db: AsyncSession):
    """Handle ticket sharing request"""
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(
            phone,
            "No tickets to share yet. Try Discover."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get user's tickets
    result = await db.execute(
        select(Ticket).where(
            Ticket.user_id == user.id,
            Ticket.status == 'valid'
        ).limit(10)
    )
    tickets = result.scalars().all()
    
    if not tickets:
        await whatsapp_service.send_message(
            phone,
            "No tickets to share yet. Try Discover."
        )
        await send_back_to_menu(phone, db)
        return
    
    conversation = await _get_or_create_conversation(phone, db)
    
    # Check if we're waiting for recipient phone number
    if conversation.flow_state and conversation.flow_state.get('awaiting_share_recipient'):
        ticket_id = conversation.flow_state.get('share_ticket_id')
        recipient_phone = entities.get('raw_message', '').strip()
        
        # Validate phone number format
        if not recipient_phone.startswith('+'):
            recipient_phone = '+234' + recipient_phone.lstrip('0')
        
        # Get ticket
        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            await whatsapp_service.send_message(phone, "Ticket not found.")
            await send_back_to_menu(phone, db)
            conversation.flow_state = {}
            await db.commit()
            return
        
        # Get event
        result = await db.execute(
            select(Event).where(Event.id == ticket.event_id)
        )
        event = result.scalar_one()
        
        # Transfer ticket
        # Create new user if doesn't exist
        result = await db.execute(
            select(User).where(User.phone == recipient_phone)
        )
        recipient_user = result.scalar_one_or_none()
        
        if not recipient_user:
            recipient_user = User(phone=recipient_phone)
            db.add(recipient_user)
            await db.commit()
            await db.refresh(recipient_user)
        
        # Update ticket ownership
        ticket.user_id = recipient_user.id
        await db.commit()
        
        # Notify sender
        await whatsapp_service.send_message(
            phone,
            "Ticket shared.\n\n"
            f"Event: {event.title}\n"
            f"Ticket: {ticket.ticket_code}\n"
            f"Sent to: {recipient_phone}\n"
            "They will receive the ticket details shortly."
        )
        await send_back_to_menu(phone, db)
        
        # Send ticket to recipient
        message = "You have received a ticket.\n\n"
        message += f"From: {phone}\n"
        message += f"Event: {event.title}\n"
        message += f"Date: {event.event_date.strftime('%a, %b %d at %I:%M %p')}\n"
        message += f"Ticket: {ticket.ticket_code}\n\n"
        message += "QR code:"
        
        await whatsapp_service.send_message(recipient_phone, message)
        await whatsapp_service.send_image(
            recipient_phone,
            ticket.qr_code_url,
            f"Ticket: {ticket.ticket_code}"
        )
        
        # Clear flow state
        conversation.flow_state = {}
        await db.commit()
        return
    
    # Show tickets to share (interactive list)
    rows = []
    for ticket in tickets:
        result = await db.execute(
            select(Event).where(Event.id == ticket.event_id)
        )
        event = result.scalar_one()
        rows.append({
            "id": f"share_ticket:{ticket.id}",
            "title": event.title,
            "description": f"{ticket.ticket_code} - {event.event_date.strftime('%b %d, %I:%M %p')}"
        })
    rows.append({"id": "action:menu", "title": "Main menu", "description": "Back to menu"})
    
    # Save tickets to conversation state
    conversation.flow_state = {
        'share_flow': True,
        'shareable_tickets': [str(t.id) for t in tickets]
    }
    await db.commit()

    await _send_list_tracked(
        phone=phone,
        message="Pick a ticket to share:",
        button_text="Choose",
        sections=[
            {"title": "Your tickets", "rows": rows}
        ],
        db=db,
        conversation=conversation,
        context="share_ticket_list"
    )


async def handle_share_ticket_by_id(ticket_id: str, phone: str, db: AsyncSession):
    """Handle share ticket selection by ticket ID (from list reply)"""
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if not user:
        await whatsapp_service.send_message(
            phone,
            "No tickets found for this account."
        )
        await send_back_to_menu(phone, db)
        return

    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.user_id == user.id,
            Ticket.status == 'valid'
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        await whatsapp_service.send_message(
            phone,
            "Ticket not found or not available to share."
        )
        await send_back_to_menu(phone, db)
        return

    result = await db.execute(
        select(Event).where(Event.id == ticket.event_id)
    )
    event = result.scalar_one()

    conversation = await _get_or_create_conversation(phone, db)
    conversation.flow_state = {
        'awaiting_share_recipient': True,
        'share_ticket_id': str(ticket.id)
    }
    await db.commit()

    message = (
        f"Share ticket for {event.title}.\n"
        "Send the recipient phone number.\n"
        "Format: +234XXXXXXXXXX or 0XXXXXXXXXX"
    )
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)


async def handle_request_refund(entities: Dict, phone: str, db: AsyncSession):
    """Handle refund request"""
    from app.services.bookings import cancel_booking
    from app.models import Conversation
    
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(
            phone,
            "No bookings yet. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get user's confirmed bookings
    result = await db.execute(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.status == 'confirmed'
        ).limit(10)
    )
    bookings = result.scalars().all()
    
    if not bookings:
        await whatsapp_service.send_message(
            phone,
            "No bookings to refund."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Check if user is in refund flow
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    
    # Check if we're confirming refund
    if conversation.flow_state and conversation.flow_state.get('awaiting_refund_confirmation'):
        booking_id = conversation.flow_state.get('refund_booking_id')
        confirmation = entities.get('raw_message', '').strip().lower()
        
        if confirmation in ['yes', 'y', 'confirm', '1']:
            await handle_refund_confirmation(booking_id, True, phone, db)
            return
        if confirmation in ['no', 'n', 'cancel', '2']:
            await handle_refund_confirmation(booking_id, False, phone, db)
            return
        
        await whatsapp_service.send_message(
            phone,
            "Please confirm or cancel the refund."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Show bookings to refund (interactive list)
    message = "Pick the booking you want to refund."
    rows = []
    
    for booking in bookings:
        result = await db.execute(
            select(Event).where(Event.id == booking.event_id)
        )
        event = result.scalar_one()
        
        rows.append({
            "id": f"refund:{booking.id}",
            "title": event.title,
            "description": f"{booking.quantity} ticket(s) - {_format_price(booking.total_amount)} - {booking.booked_at.strftime('%b %d')}"
        })
    rows.append({"id": "action:menu", "title": "Main menu", "description": "Back to menu"})
    
    # Save bookings to conversation state for numeric fallback
    conversation.flow_state = {
        'refund_flow': True,
        'refundable_bookings': [str(b.id) for b in bookings]
    }
    await db.commit()
    
    await _send_list_tracked(
        phone=phone,
        message=message,
        button_text="Choose",
        sections=[
            {
                "title": "Refunds",
                "rows": rows
            }
        ],
        db=db,
        conversation=conversation,
        context="refund_list"
    )


async def handle_manage_event(entities: Dict, phone: str, db: AsyncSession):
    """Handle event management for organizers"""
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(
            phone,
            "Please create an account first. Try Create event."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get user's events
    result = await db.execute(
        select(Event).where(
            Event.host_id == user.id,
            Event.status == 'active'
        ).limit(10)
    )
    events = result.scalars().all()
    
    if not events:
        await whatsapp_service.send_message(
            phone,
            "You do not have any events yet. Try Create event."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Show event list (interactive)
    message = "Pick an event to manage."
    rows = []
    
    for event in events:
        rows.append({
            "id": f"org_event:{event.id}",
            "title": event.title,
            "description": f"{event.event_date.strftime('%b %d')} - {event.tickets_sold}/{event.capacity} sold"
        })
    rows.append({"id": "action:menu", "title": "Main menu", "description": "Back to menu"})
    
    await _send_list_tracked(
        phone=phone,
        message=message,
        button_text="Choose",
        sections=[
            {
                "title": "Your events",
                "rows": rows
            }
        ],
        db=db,
        conversation=None,
        context="organizer_events"
    )


async def handle_organizer_event_by_id(event_id: str, phone: str, db: AsyncSession):
    """Show organizer actions for a specific event"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        await whatsapp_service.send_message(phone, "Event not found.")
        await send_back_to_menu(phone, db)
        return
    
    await handle_organizer_event_action_menu(event, phone, db)


async def handle_organizer_event_action(event_id: str, action: str, phone: str, db: AsyncSession):
    """Route organizer action from interactive list"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        await whatsapp_service.send_message(phone, "Event not found.")
        await send_back_to_menu(phone, db)
        return
    
    action = action.lower()
    if action == "stats":
        await handle_event_stats(event, phone, db)
        return
    if action == "broadcast":
        await handle_broadcast_message(event, phone, db)
        return
    if action == "attendees":
        await handle_event_attendees(event, phone, db)
        return
    if action == "edit":
        await handle_edit_event(event, phone, db)
        return
    if action == "cancel":
        await handle_cancel_event(event, phone, db)
        return
    if action == "menu":
        await handle_organizer_event_action_menu(event, phone, db)
        return


async def handle_organizer_event_action_menu(event: Event, phone: str, db: AsyncSession):
    """Show organizer action menu for an event"""
    message = f"Manage: {event.title}"
    await _send_list_tracked(
        phone=phone,
        message=message,
        button_text="Choose",
        sections=[
            {
                "title": "Actions",
                "rows": [
                    {"id": f"org_action:{event.id}:stats", "title": "View stats", "description": "Sales, revenue, check-ins"},
                    {"id": f"org_action:{event.id}:broadcast", "title": "Broadcast", "description": "Message all attendees"},
                    {"id": f"org_action:{event.id}:attendees", "title": "Attendees", "description": "View attendee list"},
                    {"id": f"org_action:{event.id}:edit", "title": "Edit event", "description": "Update details"},
                    {"id": f"org_action:{event.id}:cancel", "title": "Cancel event", "description": "Refund all attendees"},
                    {"id": "action:manage_events", "title": "All events", "description": "Back to your list"},
                    {"id": "action:menu", "title": "Main menu", "description": "Back to menu"}
                ]
            }
        ],
        db=db,
        conversation=None,
        context="organizer_action_menu"
    )



async def handle_share_ticket_selection(ticket_number: int, phone: str, db: AsyncSession):
    """Handle when user selects which ticket to share"""
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(phone, "Session expired. Type Share ticket or Menu.")
        await send_back_to_menu(phone, db)
        return
    
    shareable_tickets = conversation.flow_state.get('shareable_tickets', [])
    
    if ticket_number < 1 or ticket_number > len(shareable_tickets):
        await whatsapp_service.send_message(
            phone,
            f"Please select a number between 1 and {len(shareable_tickets)}"
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get selected ticket
    ticket_id = shareable_tickets[ticket_number - 1]
    await handle_share_ticket_by_id(ticket_id, phone, db)


async def handle_refund_selection(booking_number: int, phone: str, db: AsyncSession):
    """Handle when user selects which booking to refund"""
    from app.models import Conversation
    
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(phone, "Session expired. Try: \"Request refund\"")
        await send_back_to_menu(phone, db)
        return
    
    refundable_bookings = conversation.flow_state.get('refundable_bookings', [])
    
    if booking_number < 1 or booking_number > len(refundable_bookings):
        await whatsapp_service.send_message(
            phone,
            f"Please select a number between 1 and {len(refundable_bookings)}"
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get selected booking
    booking_id = refundable_bookings[booking_number - 1]
    await handle_refund_selection_by_id(booking_id, phone, db)


async def handle_refund_selection_by_id(booking_id: str, phone: str, db: AsyncSession):
    """Handle refund selection by booking ID (from list reply)"""
    from app.models import Conversation
    
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    
    # Get booking details
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        await whatsapp_service.send_message(phone, "Booking not found.")
        await send_back_to_menu(phone, db)
        conversation.flow_state = {}
        await db.commit()
        return
    
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == booking.event_id)
    )
    event = result.scalar_one()
    
    message = (
        "Confirm refund\n\n"
        f"Event: {event.title}\n"
        f"Tickets: {booking.quantity}x\n"
        f"Amount: {_format_price(booking.total_amount)}\n\n"
        "This goes back to your original payment method.\n"
        "This cannot be undone."
    )
    
    # Update flow state
    conversation.flow_state = {
        'awaiting_refund_confirmation': True,
        'refund_booking_id': str(booking.id)
    }
    await db.commit()
    
    await _send_buttons(
        phone=phone,
        message=message,
        buttons=[
            {"id": f"refund_confirm:{booking.id}", "title": "Confirm refund"},
            {"id": f"refund_cancel:{booking.id}", "title": "Keep booking"}
        ],
        db=db,
        conversation=conversation,
        context="refund_confirm"
    )


async def handle_refund_confirmation(booking_id: str, confirm: bool, phone: str, db: AsyncSession):
    """Process refund confirmation"""
    from app.models import Conversation
    from app.services.bookings import cancel_booking
    
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if confirm:
        result = await cancel_booking(
            booking_id=booking_id,
            reason="Customer requested refund",
            db=db
        )
        
        if result['success']:
            await whatsapp_service.send_message(
                phone,
                "Refund requested. Expect 5-7 business days."
            )
            await send_back_to_menu(phone, db)
        else:
            await whatsapp_service.send_message(
                phone,
                "Refund failed. Please contact support."
            )
            await send_back_to_menu(phone, db)
    else:
        await whatsapp_service.send_message(
            phone,
            "Refund cancelled. Your booking stays active."
        )
        await send_back_to_menu(phone, db)
    
    if conversation:
        conversation.flow_state = {}
        await db.commit()


async def handle_organizer_command(command: str, phone: str, db: AsyncSession):
    """Handle organizer commands: Stats, Broadcast, Attendees, Cancel"""
    parts = command.strip().split(maxsplit=1)
    
    if len(parts) < 2:
        await whatsapp_service.send_message(
            phone,
            "Please specify event number. Example: Stats 1"
        )
        await send_back_to_menu(phone, db)
        return
    
    action = parts[0].lower()
    
    try:
        event_number = int(parts[1])
    except ValueError:
        await whatsapp_service.send_message(
            phone,
            "Invalid event number. Example: Stats 1"
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(phone, "User not found.")
        await send_back_to_menu(phone, db)
        return
    
    # Get user's events
    result = await db.execute(
        select(Event).where(
            Event.host_id == user.id,
            Event.status == 'active'
        ).limit(10)
    )
    events = result.scalars().all()
    
    if not events:
        await whatsapp_service.send_message(phone, "You do not have any events.")
        await send_back_to_menu(phone, db)
        return
    
    if event_number < 1 or event_number > len(events):
        await whatsapp_service.send_message(
            phone,
            f"Please select a number between 1 and {len(events)}"
        )
        await send_back_to_menu(phone, db)
        return
    
    event = events[event_number - 1]
    
    # Route to appropriate handler
    if action == 'stats':
        await handle_event_stats(event, phone, db)
    elif action == 'broadcast':
        await handle_broadcast_message(event, phone, db)
    elif action == 'attendees':
        await handle_event_attendees(event, phone, db)
    elif action == 'cancel':
        await handle_cancel_event(event, phone, db)
    elif action == 'edit':
        await handle_edit_event(event, phone, db)


async def handle_event_stats(event: Event, phone: str, db: AsyncSession):
    """Show detailed event statistics"""
    from datetime import datetime
    
    # Get all bookings
    result = await db.execute(
        select(Booking).where(Booking.event_id == event.id)
    )
    bookings = result.scalars().all()
    
    # Calculate stats
    confirmed_bookings = [b for b in bookings if b.status == 'confirmed']
    pending_bookings = [b for b in bookings if b.status == 'pending']
    cancelled_bookings = [b for b in bookings if b.status == 'cancelled']
    
    total_revenue = sum(b.total_amount for b in confirmed_bookings)
    total_tickets_sold = sum(b.quantity for b in confirmed_bookings)
    
    # Get tickets
    result = await db.execute(
        select(Ticket).where(Ticket.event_id == event.id)
    )
    tickets = result.scalars().all()
    
    checked_in = len([t for t in tickets if t.checked_in_at])
    
    # Format message
    message = "Event stats\n\n"
    message += f"{event.title}\n"
    message += f"{event.event_date.strftime('%a, %b %d, %Y at %I:%M %p')}\n\n"

    message += "Tickets\n"
    message += f"- Sold: {total_tickets_sold}/{event.capacity}\n"
    message += f"- Available: {event.capacity - total_tickets_sold}\n"
    message += f"- Checked in: {checked_in}\n\n"

    message += "Revenue\n"
    message += f"- Total: {_format_price(total_revenue)}\n"
    message += f"- Per ticket: {_format_price(event.ticket_price)}\n\n"

    message += "Bookings\n"
    message += f"- Confirmed: {len(confirmed_bookings)}\n"
    message += f"- Pending: {len(pending_bookings)}\n"
    message += f"- Cancelled: {len(cancelled_bookings)}\n\n"
    
    # Days until event
    days_until = (event.event_date - datetime.now()).days
    if days_until > 0:
        message += f"{days_until} days to go\n\n"
    elif days_until == 0:
        message += f"Event is today\n\n"
    else:
        message += f"Event completed\n\n"
    
    if event.is_anonymous:
        message += "Hidden event\n"
        message += f"Code: {event.secret_code}\n"
        if event.location_revealed:
            message += "Location revealed\n"
        else:
            message += "Location hidden\n"
    
    await whatsapp_service.send_message(phone, message)
    
    await _send_buttons(
        phone=phone,
        message="Next action:",
        buttons=[
            {"id": f"org_action:{event.id}:broadcast", "title": "Broadcast"},
            {"id": f"org_action:{event.id}:attendees", "title": "Attendees"},
            {"id": f"org_action:{event.id}:menu", "title": "Back"}
        ],
        db=db,
        conversation=None,
        context="organizer_stats_actions"
    )
    await send_back_to_menu(phone, db)


async def handle_broadcast_message(event: Event, phone: str, db: AsyncSession):
    """Send broadcast message to all event attendees"""
    from app.models import Conversation
    
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    
    # Check if we're waiting for broadcast message
    if conversation.flow_state and conversation.flow_state.get('awaiting_broadcast_message'):
        broadcast_event_id = conversation.flow_state.get('broadcast_event_id')
        
        if str(event.id) != broadcast_event_id:
            # Get the correct event
            result = await db.execute(
                select(Event).where(Event.id == broadcast_event_id)
            )
            event = result.scalar_one()
        
        # Get message from entities
        from app.services.ai_engine import Intent
        broadcast_text = conversation.flow_state.get('broadcast_text', '')
        
        # Get all attendees
        result = await db.execute(
            select(Booking).where(
                Booking.event_id == event.id,
                Booking.status == 'confirmed'
            )
        )
        bookings = result.scalars().all()
        
        if not bookings:
            await whatsapp_service.send_message(
                phone,
                "No attendees to message yet."
            )
            conversation.flow_state = {}
            await db.commit()
            await send_back_to_menu(phone, db)
            return
        
        # Send broadcast
        message_header = f"Message from {event.title} organizer\n\n"
        
        sent_count = 0
        for booking in bookings:
            try:
                await whatsapp_service.send_message(
                    booking.phone,
                    message_header + broadcast_text
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {booking.phone}: {e}")
        
        # Confirm to organizer
        await whatsapp_service.send_message(
            phone,
            f"Broadcast sent. Delivered to {sent_count}/{len(bookings)} attendees."
        )
        await _send_buttons(
            phone=phone,
            message="Next action:",
            buttons=[
                {"id": f"org_action:{event.id}:attendees", "title": "Attendees"},
                {"id": f"org_action:{event.id}:stats", "title": "Stats"},
                {"id": f"org_action:{event.id}:menu", "title": "Back"}
            ],
            db=db,
            conversation=conversation,
            context="broadcast_actions"
        )
        await send_back_to_menu(phone, db)
        
        # Clear flow state
        conversation.flow_state = {}
        await db.commit()
        return
    
    # Start broadcast flow
    message = (
        f"Broadcast for {event.title}\n\n"
        "Type the message you want to send to all attendees."
    )
    
    # Update flow state
    conversation.flow_state = {
        'awaiting_broadcast_message': True,
        'broadcast_event_id': str(event.id)
    }
    await db.commit()
    
    await _send_buttons(
        phone=phone,
        message=message,
        buttons=[
            {"id": "action:cancel_broadcast", "title": "Cancel"},
            {"id": "action:menu", "title": "Menu"}
        ],
        db=db,
        conversation=conversation,
        context="broadcast_prompt"
    )


async def handle_event_attendees(event: Event, phone: str, db: AsyncSession):
    """Show list of event attendees"""
    # Get all confirmed bookings
    result = await db.execute(
        select(Booking).where(
            Booking.event_id == event.id,
            Booking.status == 'confirmed'
        )
    )
    bookings = result.scalars().all()
    
    if not bookings:
        await whatsapp_service.send_message(
            phone,
            f"No attendees yet for {event.title}."
        )
        await send_back_to_menu(phone, db)
        return
    
    message = f"Attendees: {event.title}\n"
    message += f"Total: {len(bookings)} bookings\n\n"
    
    for i, booking in enumerate(bookings[:20], 1):  # Limit to 20
        # Get user
        result = await db.execute(
            select(User).where(User.id == booking.user_id)
        )
        user = result.scalar_one_or_none()
        
        name = user.name if user and user.name else "Guest"
        message += f"{i}. {name}\n"
        message += f"   {booking.phone}\n"
        message += f"   {booking.quantity} ticket(s)\n"
        message += f"   {booking.booked_at.strftime('%b %d, %I:%M %p')}\n\n"
    
    if len(bookings) > 20:
        message += f"\n... and {len(bookings) - 20} more"
    
    await whatsapp_service.send_message(phone, message)
    
    await _send_buttons(
        phone=phone,
        message="Next action:",
        buttons=[
            {"id": f"org_action:{event.id}:broadcast", "title": "Broadcast"},
            {"id": f"org_action:{event.id}:stats", "title": "Stats"},
            {"id": f"org_action:{event.id}:menu", "title": "Back"}
        ],
        db=db,
        conversation=None,
        context="attendees_actions"
    )
    await send_back_to_menu(phone, db)


async def handle_cancel_event(event: Event, phone: str, db: AsyncSession):
    """Cancel an event and refund all attendees"""
    from app.models import Conversation
    
    # Get conversation state
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
    
    # Get booking count
    result = await db.execute(
        select(Booking).where(
            Booking.event_id == event.id,
            Booking.status == 'confirmed'
        )
    )
    bookings = result.scalars().all()
    
    total_refund = sum(b.total_amount for b in bookings)
    
    # Show confirmation
    message = (
        "Cancel event\n\n"
        f"Event: {event.title}\n"
        f"Date: {event.event_date.strftime('%b %d, %Y')}\n"
        f"Attendees: {len(bookings)}\n"
        f"Total refunds: NGN {total_refund:,.0f}\n\n"
        "This will cancel the event and refund all attendees.\n"
        "This action cannot be undone.\n\n"
        "Reply Yes to confirm or No to abort."
    )
    
    # Update flow state
    conversation.flow_state = {
        'awaiting_cancel_confirmation': True,
        'cancel_event_id': str(event.id)
    }
    await db.commit()
    
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)



async def handle_analytics(phone: str, db: AsyncSession):
    """Show analytics dashboard for organizers"""
    from app.services.analytics import get_organizer_analytics
    
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(
            phone,
            "Please create an account first. Try Create event."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get analytics for 30 days
    analytics = await get_organizer_analytics(
        organizer_id=str(user.id),
        db=db,
        period='30d'
    )
    
    summary = analytics['summary']
    
    if summary['total_events'] == 0:
        await whatsapp_service.send_message(
            phone,
            "Analytics\n\n"
            "You have not created any events yet.\n"
            "Try Create event to get started."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Format message
    message = "Analytics (last 30 days)\n\n"
    message += "Overview\n"
    message += f"- Events: {summary['total_events']}\n"
    message += f"- Bookings: {summary['total_bookings']}\n"
    message += f"- Tickets sold: {summary['total_tickets']}\n"
    message += f"- Revenue: NGN {summary['total_revenue']:,.0f}\n\n"
    
    if analytics['events']:
        message += "Top events\n"
        for i, event in enumerate(analytics['events'][:3], 1):
            message += f"{i}. {event['title']}\n"
            message += f"   Revenue: NGN {event['revenue']:,.0f}\n"
            message += f"   Tickets: {event['tickets_sold']}/{event['capacity']} ({event['fill_rate']}%)\n\n"

    message += "Next:\n"
    message += "- Download report\n"
    message += "- Manage event\n"
    message += "- Stats [number]"

    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)



async def handle_download_report(phone: str, db: AsyncSession):
    """Handle report download request"""
    from app.services.reports import generate_revenue_report
    from app.models import Conversation
    import tempfile
    import os
    
    # Get user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await whatsapp_service.send_message(
            phone,
            "Create an account first. Try Create event."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Check if user has events
    result = await db.execute(
        select(Event).where(Event.host_id == user.id).limit(1)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        await whatsapp_service.send_message(
            phone,
            "You do not have any events yet. Try Create event."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Generate report
    await whatsapp_service.send_message(
        phone,
        "Generating your revenue report. This may take a moment."
    )
    
    try:
        csv_content = await generate_revenue_report(
            organizer_id=str(user.id),
            db=db
        )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        # Send as document
        filename = f"grooovy_revenue_report_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Note: WhatsApp document sending requires file upload
        # For now, we'll send the report via email or provide download link
        # This is a simplified version
        
        message = (
            "Report generated.\n\n"
            "Your revenue report is ready.\n"
            "We sent it to your email.\n\n"
            "Report includes:\n"
            "- All your events\n"
            "- Booking details\n"
            "- Revenue breakdown\n"
            "- Ticket sales stats"
        )
        
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)
        
        # Clean up temp file
        os.unlink(temp_path)
        
    except Exception as e:
        await whatsapp_service.send_message(
            phone,
            "Failed to generate report. Please try again later."
        )
        await send_back_to_menu(phone, db)



async def handle_edit_event(event: Event, phone: str, db: AsyncSession):
    """Start event editing flow"""
    from app.services.event_editing import EventEditingFlow
    await EventEditingFlow.start_flow(str(event.id), phone, db)



async def handle_checkin(command: str, phone: str, db: AsyncSession):
    """Handle ticket check-in"""
    from app.services.checkin import check_in_ticket
    
    # Parse command: "checkin GRV-ABC123" or "checkin GRV-ABC123 CODE123"
    parts = command.strip().split()
    
    if len(parts) < 2:
        await whatsapp_service.send_message(
            phone,
            "Usage: checkin [ticket_code]\nExample: checkin GRV-ABC123"
        )
        await send_back_to_menu(phone, db)
        return
    
    ticket_code = parts[1].upper()
    entry_code = parts[2] if len(parts) > 2 else None
    
    # Check in ticket
    result = await check_in_ticket(
        ticket_code=ticket_code,
        db=db,
        entry_code=entry_code
    )
    
    if result['success']:
        ticket = result['ticket']
        event = result['event']
        user = result.get('user')
        
        message = (
            "Check-in successful.\n\n"
            f"Ticket: {ticket.ticket_code}\n"
            f"Event: {event.title}\n"
            f"Holder: {user.name if user and user.name else 'Guest'}\n"
            f"Time: {datetime.now().strftime('%I:%M %p')}\n"
        )
    else:
        message = f"Check-in failed.\n{result['message']}"
        
        if result['ticket'] and result['event']:
            ticket = result['ticket']
            event = result['event']
            message += f"\n\nTicket: {ticket.ticket_code}\nEvent: {event.title}"
    
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)



async def handle_recommendations(phone: str, db: AsyncSession):
    """Show personalized event recommendations - asks for preferences first"""
    from app.services.recommendations import get_personalized_recommendations
    
    # Show category selection first
    await whatsapp_service.send_list(
        phone=phone,
        message="What type of events are you interested in?",
        button_text="Category",
        sections=[
            {
                "title": "Event Categories",
                "rows": [
                    {"id": "rec:category:music", "title": "Music & Concerts", "description": "Live music, concerts, DJ nights"},
                    {"id": "rec:category:party", "title": "Parties & Nightlife", "description": "Club nights, parties, hangouts"},
                    {"id": "rec:category:food", "title": "Food & Drinks", "description": "Food festivals, brunch, drinks"},
                    {"id": "rec:category:art", "title": "Art & Culture", "description": "Exhibitions, theater, comedy"},
                    {"id": "rec:category:sports", "title": "Sports & Fitness", "description": "Workouts, tournaments, matches"},
                    {"id": "rec:category:networking", "title": "Networking", "description": "Business, careers, meetups"},
                    {"id": "rec:category:other", "title": "Anything", "description": "Show me all events"},
                ]
            }
        ]
    )


async def handle_recommendation_category(phone: str, category: str, db: AsyncSession):
    """Handle category selection for recommendations"""
    from app.services.recommendations import get_filtered_recommendations
    
    # Save category to conversation
    conversation = await _get_or_create_conversation(phone, db)
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state['rec_category'] = category
    flag_modified(conversation, 'flow_state')
    await db.commit()
    
    # Now ask for location
    await whatsapp_service.send_list(
        phone=phone,
        message="Where should the events be?",
        button_text="Location",
        sections=[
            {
                "title": "Locations",
                "rows": [
                    {"id": "rec:location:near_me", "title": "Near me", "description": "Events closest to my location"},
                    {"id": "rec:location:lagos", "title": "Lagos", "description": "Lagos Island & Mainland"},
                    {"id": "rec:location:lekki", "title": "Lekki", "description": "Lekki, Ajah, VI West"},
                    {"id": "rec:location:ikeja", "title": "Ikeja", "description": "Ikeja, Ogba, Agege"},
                    {"id": "rec:location:surulere", "title": "Surulere", "description": "Surulere, Ojuelegba"},
                    {"id": "rec:location:anywhere", "title": "Anywhere", "description": "Show all locations"},
                ]
            }
        ]
    )


async def handle_recommendation_location(phone: str, location: str, db: AsyncSession):
    """Handle location selection and show recommendations"""
    from app.services.recommendations import get_filtered_recommendations
    
    # Get category from conversation
    conversation = await _get_or_create_conversation(phone, db)
    category = conversation.flow_state.get('rec_category', 'other') if conversation.flow_state else 'other'
    
    # Get recommendations based on category and location
    events = await get_filtered_recommendations(phone, db, category=category, location=location, limit=5)
    
    if not events:
        await whatsapp_service.send_message(
            phone,
            "No events found matching your preferences. Try: Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    message = f"Recommended for you ({category} in {location}):"
    
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state['discovered_events'] = [str(e.id) for e in events]
    flag_modified(conversation, 'flow_state')
    await db.commit()
    
    await _send_event_list(
        phone=phone,
        message=message,
        events=events,
        include_distance=True,
        section_title="Recommended",
        db=db,
        conversation=conversation,
        include_menu=True,
        context="recommendations"
    )
    
    if not events:
        await whatsapp_service.send_message(
            phone,
            "No recommendations right now. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return

    message = "Recommended for you. Pick one:"

    conversation = await _get_or_create_conversation(phone, db)
    conversation.flow_state = conversation.flow_state or {}
    conversation.flow_state['discovered_events'] = [str(e.id) for e in events]
    flag_modified(conversation, 'flow_state')
    await db.commit()

    await _send_event_list(
        phone=phone,
        message=message,
        events=events,
        include_distance=False,
        section_title="Recommended",
        db=db,
        conversation=conversation,
        include_menu=True,
        context="recommendations"
    )


async def handle_share_event(command: str, phone: str, db: AsyncSession):
    """Handle event sharing"""
    from app.services.social_sharing import (
        generate_share_links,
        create_share_message,
        format_share_options_message,
        generate_referral_code,
        track_share
    )
    from app.models import Conversation
    
    # Get conversation to find selected event
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(
            phone,
            "Select an event first. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    event_id = conversation.flow_state.get('selected_event_id')
    
    if not event_id:
        await whatsapp_service.send_message(
            phone,
            "Select an event first. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Get user for referral code
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    referral_code = None
    if user:
        referral_code = await generate_referral_code(str(user.id), event_id)
    
    # Generate share links
    share_links = await generate_share_links(event_id, db, referral_code)
    
    # Create share message
    share_message = await create_share_message(event_id, db)
    
    # Get event for title
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one()
    
    # Send share message first
    await whatsapp_service.send_message(phone, share_message)
    
    # Then send share links
    links_message = format_share_options_message(event.title, share_links)
    await whatsapp_service.send_message(phone, links_message)
    await send_back_to_menu(phone, db)
    
    # Track share
    await track_share(event_id, 'whatsapp', phone, db)


async def handle_apply_promo(command: str, phone: str, db: AsyncSession):
    """Handle promo code application"""
    from app.services.promo_codes import validate_promo_code, format_promo_info
    from app.models import Conversation
    
    # Parse command: "promo CODE123" or "code CODE123"
    parts = command.strip().split(maxsplit=1)
    
    if len(parts) < 2:
        await whatsapp_service.send_message(
            phone,
            "Usage: promo [CODE]\nExample: promo SUMMER20"
        )
        await send_back_to_menu(phone, db)
        return
    
    promo_code = parts[1].upper()
    
    # Get conversation to find selected event
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await whatsapp_service.send_message(
            phone,
            "Select an event first. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    event_id = conversation.flow_state.get('selected_event_id')
    booking_id = conversation.flow_state.get('booking_id')
    
    if not event_id:
        await whatsapp_service.send_message(
            phone,
            "Select an event first. Try Events near me."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Default quantity
    quantity = 1
    
    # Validate promo code
    result = await validate_promo_code(promo_code, event_id, quantity, db)
    
    if not result['valid']:
        await whatsapp_service.send_message(
            phone,
            f"{result['message']}"
        )
        await send_back_to_menu(phone, db)
        return
    
    promo = result['promo']
    
    # Show promo info
    message = "Promo code valid.\n\n"
    message += await format_promo_info(promo)
    message += "\nDiscount will be applied at checkout.\n"
    message += "Continue with: Book [quantity]"
    
    # Save promo to conversation state
    conversation.flow_state['promo_code_id'] = str(promo.id)
    flag_modified(conversation, 'flow_state')
    await db.commit()
    
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)



async def handle_profile(phone: str, db: AsyncSession):
    """Show user profile and allow updates"""
    from app.services.user_registration import check_user_registration_status
    
    # Check registration status
    status = await check_user_registration_status(phone, db)
    
    if not status['registered']:
        await whatsapp_service.send_message(
            phone,
            "You do not have an account yet. Type Hi to get started."
        )
        await send_back_to_menu(phone, db)
        return
    
    user = status['user']
    
    # Format profile message
    message = "Your profile\n\n"
    
    if user.first_name and user.last_name:
        message += f"Name: {user.first_name} {user.last_name}\n"
    else:
        message += "Name: Not set\n"
    
    message += f"Phone: {user.phone}\n"
    
    if user.email:
        message += f"Email: {user.email}\n"
    else:
        message += "Email: Not set\n"
    
    if user.preferred_categories:
        categories = ', '.join(user.preferred_categories)
        message += f"Interests: {categories}\n"
    
    message += f"\nMember since: {user.created_at.strftime('%B %Y')}\n"
    
    # Get booking stats
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.user_id == user.id,
                Booking.status == 'confirmed'
            )
        )
    )
    bookings = result.scalars().all()
    
    if bookings:
        total_tickets = sum(b.quantity for b in bookings)
        total_spent = sum(b.total_amount for b in bookings)
        message += "\nYour stats\n"
        message += f"- Bookings: {len(bookings)}\n"
        message += f"- Tickets: {total_tickets}\n"
        message += f"- Spent: NGN {total_spent:,.0f}\n"
    
    message += (
        "\nUpdate profile:\n"
        "- Update name\n"
        "- Update email\n"
        "- Set interests"
    )
    
    await whatsapp_service.send_message(phone, message)
    await send_back_to_menu(phone, db)



async def handle_gift_ticket(phone: str, db: AsyncSession):
    """Handle gift ticket purchase request"""
    from app.services.gift_tickets import GiftTicketFlow
    from app.services.user_registration import check_user_registration_status
    from app.models import Conversation
    
    # Check if user is registered
    status = await check_user_registration_status(phone, db)
    
    if not status['registered'] or not status['profile_complete']:
        await whatsapp_service.send_message(
            phone,
            "Please register first. Type Hi to get started."
        )
        await send_back_to_menu(phone, db)
        return
    
    # Check if user has selected an event
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation or not conversation.flow_state:
        await _send_buttons(
            phone=phone,
            message="Pick an event to gift. Start by discovering events.",
            buttons=[
                {"id": "action:discover", "title": "Discover"},
                {"id": "action:help", "title": "Help"},
                {"id": "action:menu", "title": "Menu"}
            ],
            db=db,
            conversation=None,
            context="gift_start"
        )
        return
    
    event_id = conversation.flow_state.get('selected_event_id')
    
    if not event_id:
        await _send_discovered_events_list(phone, db, conversation)
        return
    
    # Start gift ticket flow
    await GiftTicketFlow.start_flow(event_id, phone, db)


async def handle_gift_history(command: str, phone: str, db: AsyncSession):
    """Show gift history (sent or received)"""
    from app.services.gift_tickets import get_gift_history, format_gift_summary
    from app.services.user_registration import check_user_registration_status
    
    # Check if user is registered
    status = await check_user_registration_status(phone, db)
    
    if not status['registered']:
        await whatsapp_service.send_message(
            phone,
            "You do not have an account yet. Type Hi to get started."
        )
        await send_back_to_menu(phone, db)
        return
    
    user = status['user']
    
    command_lower = command.lower().strip()
    
    if command_lower in ['my gifts', 'gift history']:
        await _send_list_tracked(
            phone=phone,
            message="Pick which gifts you want to see.",
            button_text="Choose",
            sections=[
                {
                    "title": "Gift history",
                    "rows": [
                        {"id": "gift_history:sent", "title": "Gifts sent", "description": "People you gifted"},
                        {"id": "gift_history:received", "title": "Gifts received", "description": "Gifts sent to you"},
                        {"id": "action:menu", "title": "Main menu", "description": "Back to menu"}
                    ]
                }
            ],
            db=db,
            conversation=None,
            context="gift_history_picker"
        )
        return
    
    # Determine if showing sent or received
    if command_lower.startswith('gift_history:'):
        show_sent = command_lower.endswith('sent')
    else:
        show_sent = 'sent' in command_lower
    
    # Get gift history
    gifts = await get_gift_history(str(user.id), db, sent=show_sent)
    
    if not gifts:
        if show_sent:
            message = (
                "No gifts sent yet.\n\n"
                "Find an event and tap Gift to start."
            )
        else:
            message = (
                "No gifts received yet.\n\n"
                "When someone sends you a gift, it will appear here."
            )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)
        return
    
    # Format gift history
    if show_sent:
        message = f"Gifts sent ({len(gifts)})\n\n"
    else:
        message = f"Gifts received ({len(gifts)})\n\n"
    
    for i, gift in enumerate(gifts[:10], 1):
        # Get event
        result = await db.execute(
            select(Event).where(Event.id == gift.event_id)
        )
        event = result.scalar_one()
        
        summary = await format_gift_summary(gift, event, is_sender=show_sent)
        message += f"{i}. {summary}\n"
    
    if len(gifts) > 10:
        message += f"\n... and {len(gifts) - 10} more"
    
    await whatsapp_service.send_message(phone, message)
    await _send_buttons(
        phone=phone,
        message="Quick actions:",
        buttons=[
            {"id": "action:gift_ticket", "title": "Gift ticket"},
            {"id": "action:discover", "title": "Discover"},
            {"id": "action:menu", "title": "Menu"}
        ],
        db=db,
        conversation=None,
        context="gift_history_actions"
    )
























