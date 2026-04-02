from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime
from app.models import Event, User, Conversation
from app.services.whatsapp import whatsapp_service
from sqlalchemy import select
from app.services.location import geocode_address
from app.services.notifications import NotificationService
from app.services.menu import send_back_to_menu


class EventCreationFlow:
    """Multi-turn conversation flow for event creation"""

    STEPS = [
        'title',
        'category',
        'date',
        'location_type',
        'reveal_timing',
        'address',
        'entry_code_type',
        'entry_code',
        'capacity',
        'price',
        'description',
        'confirm'
    ]

    CATEGORIES = {
        '1': 'concert',
        '2': 'wedding',
        '3': 'conference',
        '4': 'party',
        '5': 'crusade',
        '6': 'sports',
        '7': 'networking',
        '8': 'other'
    }

    @staticmethod
    async def start_flow(phone: str, db: AsyncSession):
        """Start event creation flow"""
        # Get or create conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(phone=phone)
            db.add(conversation)

        conversation.current_flow = 'event_creation'
        conversation.flow_state = {
            'step': 'title',
            'data': {}
        }
        await db.commit()

        message = (
            "Lets create your event.\n"
            "Type cancel anytime to stop.\n\n"
            "First, what is the event name?\n"
            "Example: Sip and Paint Lagos, Tech Founders Dinner"
        )
        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)

    @staticmethod
    async def process_step(phone: str, user_input: str, db: AsyncSession):
        """Process user input for current step"""
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one()

        if user_input.lower() == 'cancel':
            conversation.current_flow = None
            conversation.flow_state = {}
            await db.commit()
            await whatsapp_service.send_message(phone, "Event creation cancelled.")
            await send_back_to_menu(phone, db)
            return

        current_step = conversation.flow_state['step']
        data = conversation.flow_state['data']

        if current_step == 'title':
            data['title'] = user_input
            conversation.flow_state['step'] = 'category'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            message = (
                "Great. What type of event is this?\n"
                "1. Concert or Music\n"
                "2. Wedding\n"
                "3. Conference or Seminar\n"
                "4. Party\n"
                "5. Crusade or Religious\n"
                "6. Sports\n"
                "7. Networking\n"
                "8. Other\n\n"
                "Reply with number (1-8)"
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

        elif current_step == 'category':
            category = EventCreationFlow.CATEGORIES.get(user_input)
            if not category:
                await whatsapp_service.send_message(phone, "Reply with a number 1-8.")
                await send_back_to_menu(phone, db)
                return

            data['category'] = category
            conversation.flow_state['step'] = 'date'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            message = (
                f"{category.title()} event. Nice.\n\n"
                "When is the event?\n"
                "Format: DD/MM/YYYY at HH:MM AM/PM\n"
                "Example: 20/02/2026 at 7:00 PM"
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

        elif current_step == 'date':
            try:
                event_date = datetime.strptime(user_input, "%d/%m/%Y at %I:%M %p")
                data['event_date'] = event_date.isoformat()
                conversation.flow_state['step'] = 'location_type'
                flag_modified(conversation, 'flow_state')
                await db.commit()

                message = (
                    f"Date set: {event_date.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
                    "Location visibility:\n"
                    "1. Public (location visible to everyone)\n"
                    "2. Hidden (location after ticket purchase)\n"
                    "3. VIP (secret code to discover)\n\n"
                    "Reply with number (1-3)"
                )
                await whatsapp_service.send_message(phone, message)
                await send_back_to_menu(phone, db)
            except ValueError:
                await whatsapp_service.send_message(
                    phone,
                    "Invalid date format. Use: DD/MM/YYYY at HH:MM AM/PM"
                )
                await send_back_to_menu(phone, db)

        elif current_step == 'location_type':
            location_types = {
                '1': 'public',
                '2': 'location_hidden',
                '3': 'code_required'
            }
            location_type = location_types.get(user_input)

            if not location_type:
                await whatsapp_service.send_message(phone, "Reply with 1, 2, or 3.")
                await send_back_to_menu(phone, db)
                return

            data['is_anonymous'] = location_type != 'public'
            data['anonymous_mode'] = location_type if location_type != 'public' else None

            if location_type == 'location_hidden':
                conversation.flow_state['step'] = 'reveal_timing'
                flag_modified(conversation, 'flow_state')
                await db.commit()

                message = (
                    "When should the location reveal?\n"
                    "1. Immediately after purchase\n"
                    "2. 24 hours before event\n"
                    "3. 6 hours before event\n"
                    "4. 1 hour before event\n\n"
                    "Reply with number (1-4)"
                )
                await whatsapp_service.send_message(phone, message)
                await send_back_to_menu(phone, db)
            else:
                conversation.flow_state['step'] = 'address'
                flag_modified(conversation, 'flow_state')
                await db.commit()
                await whatsapp_service.send_message(
                    phone,
                    "What is the full venue address?"
                )
                await send_back_to_menu(phone, db)

        elif current_step == 'reveal_timing':
            timings = {
                '1': ('immediate', 0),
                '2': ('time_based', 24),
                '3': ('time_based', 6),
                '4': ('time_based', 1)
            }
            timing = timings.get(user_input)

            if not timing:
                await whatsapp_service.send_message(phone, "Reply with 1-4.")
                await send_back_to_menu(phone, db)
                return

            data['location_reveal_trigger'] = timing[0]
            data['location_reveal_hours_before'] = timing[1]
            conversation.flow_state['step'] = 'address'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            message = "Location will reveal "
            if timing[0] == 'immediate':
                message += "immediately after purchase.\n\n"
            else:
                message += f"{timing[1]} hour(s) before the event.\n\n"
            message += "What is the full venue address?"

            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

        elif current_step == 'address':
            data['full_address'] = user_input
            data['venue_name'] = user_input.split(',')[0]
            conversation.flow_state['step'] = 'entry_code_type'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            message = (
                f"Venue saved: {data['venue_name']}\n\n"
                "Entry code?\n"
                "1. Same code for all attendees\n"
                "2. Unique code per ticket\n"
                "3. No entry code\n\n"
                "Reply with number (1-3)"
            )
            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

        elif current_step == 'entry_code_type':
            if user_input == '1':
                data['entry_code_format'] = 'shared'
                conversation.flow_state['step'] = 'entry_code'
                flag_modified(conversation, 'flow_state')
                await db.commit()
                await whatsapp_service.send_message(
                    phone,
                    "Enter the entry code (6-12 characters, uppercase letters or numbers)."
                )
                await send_back_to_menu(phone, db)
            elif user_input == '2':
                data['entry_code_format'] = 'unique_per_ticket'
                conversation.flow_state['step'] = 'capacity'
                flag_modified(conversation, 'flow_state')
                await db.commit()
                await whatsapp_service.send_message(
                    phone,
                    "Unique codes will be generated per ticket.\n"
                    "How many tickets are available?"
                )
                await send_back_to_menu(phone, db)
            elif user_input == '3':
                data['entry_code_format'] = None
                conversation.flow_state['step'] = 'capacity'
                flag_modified(conversation, 'flow_state')
                await db.commit()
                await whatsapp_service.send_message(
                    phone,
                    "How many tickets are available?"
                )
                await send_back_to_menu(phone, db)
            else:
                await whatsapp_service.send_message(phone, "Reply with 1, 2, or 3.")
                await send_back_to_menu(phone, db)

        elif current_step == 'entry_code':
            if len(user_input) < 6 or len(user_input) > 12:
                await whatsapp_service.send_message(phone, "Code must be 6-12 characters.")
                await send_back_to_menu(phone, db)
                return

            data['shared_entry_code'] = user_input.upper()
            conversation.flow_state['step'] = 'capacity'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            await whatsapp_service.send_message(
                phone,
                f"Entry code set: {user_input.upper()}\n"
                "How many tickets are available?"
            )
            await send_back_to_menu(phone, db)

        elif current_step == 'capacity':
            try:
                capacity = int(user_input)
                data['capacity'] = capacity
                conversation.flow_state['step'] = 'price'
                flag_modified(conversation, 'flow_state')
                await db.commit()

                await whatsapp_service.send_message(
                    phone,
                    f"Capacity: {capacity}\n"
                    "Ticket price in NGN (e.g., 25000)"
                )
                await send_back_to_menu(phone, db)
            except ValueError:
                await whatsapp_service.send_message(phone, "Enter a valid number.")
                await send_back_to_menu(phone, db)

        elif current_step == 'price':
            try:
                price = float(user_input)
                data['ticket_price'] = price
                conversation.flow_state['step'] = 'description'
                flag_modified(conversation, 'flow_state')
                await db.commit()

                await whatsapp_service.send_message(
                    phone,
                    f"Ticket price: NGN {price:,.0f}\n"
                    "Add a short description (2-3 sentences)."
                )
                await send_back_to_menu(phone, db)
            except ValueError:
                await whatsapp_service.send_message(phone, "Enter a valid amount.")
                await send_back_to_menu(phone, db)

        elif current_step == 'description':
            data['description'] = user_input
            conversation.flow_state['step'] = 'confirm'
            flag_modified(conversation, 'flow_state')
            await db.commit()

            message = "Event summary\n\n"
            message += f"Title: {data['title']}\n"
            message += f"Category: {data['category'].title()}\n"
            event_date = datetime.fromisoformat(data['event_date'])
            message += f"Date: {event_date.strftime('%a, %b %d, %Y at %I:%M %p')}\n"
            message += f"Venue: {data['venue_name']}\n"

            if data.get('is_anonymous'):
                if data.get('location_reveal_trigger') == 'immediate':
                    message += "Location reveals immediately\n"
                else:
                    message += f"Location reveals {data.get('location_reveal_hours_before')}hr before\n"

            if data.get('entry_code_format') == 'shared':
                message += f"Entry code: {data['shared_entry_code']}\n"
            elif data.get('entry_code_format') == 'unique_per_ticket':
                message += "Entry code: Unique per ticket\n"

            message += f"Tickets: {data['capacity']} at NGN {data['ticket_price']:,.0f} each\n\n"
            message += f"Description: {data['description']}\n\n"
            message += "Everything look good?\n"
            message += "1. Yes, create event\n"
            message += "2. Cancel"

            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

        elif current_step == 'confirm':
            if user_input == '1':
                event = await EventCreationFlow.create_event(phone, data, db)

                conversation.current_flow = None
                conversation.flow_state = {}
                await db.commit()

                message = (
                    "Event created.\n\n"
                    f"Event ID: GRV-EVT-{event.id.hex[:8].upper()}\n"
                    "Status: Live\n\n"
                    "Dashboard:\n"
                    f"- Tickets sold: 0/{event.capacity}\n"
                    "- Revenue: NGN 0\n\n"
                    "Manage anytime:\n"
                    "- Event stats\n"
                    "- Edit event\n\n"
                    "Start selling."
                )
                await whatsapp_service.send_message(phone, message)
                await send_back_to_menu(phone, db)
            else:
                conversation.current_flow = None
                conversation.flow_state = {}
                await db.commit()
                await whatsapp_service.send_message(phone, "Event creation cancelled.")
                await send_back_to_menu(phone, db)

    @staticmethod
    async def create_event(phone: str, data: Dict, db: AsyncSession) -> Event:
        """Create event from collected data"""
        # Get or create user
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(phone=phone)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Geocode address to get coordinates
        lat, lng = await geocode_address(data['full_address'])

        # Create event
        event = Event(
            host_id=user.id,
            title=data['title'],
            description=data['description'],
            category=data['category'],
            event_date=datetime.fromisoformat(data['event_date']),
            full_address=data['full_address'],
            venue_name=data['venue_name'],
            location_lat=lat,
            location_lng=lng,
            capacity=data['capacity'],
            ticket_price=data['ticket_price'],
            is_anonymous=data.get('is_anonymous', False),
            anonymous_mode=data.get('anonymous_mode'),
            location_reveal_trigger=data.get('location_reveal_trigger'),
            location_reveal_hours_before=data.get('location_reveal_hours_before'),
            entry_code_format=data.get('entry_code_format'),
            shared_entry_code=data.get('shared_entry_code'),
            status='active',
            created_via='whatsapp'
        )

        if data.get('anonymous_mode') == 'code_required':
            from app.services.tickets import generate_unique_code
            event.secret_code = generate_unique_code(8)

        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Trigger proximity notifications
        await NotificationService.notify_nearby_users(event, db)

        return event
