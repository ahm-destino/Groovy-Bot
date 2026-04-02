"""
Event editing service for modifying event details
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime

from app.models import Event, Booking
from app.services.whatsapp import whatsapp_service
from app.services.menu import send_back_to_menu


class EventEditingFlow:
    """Multi-turn flow for editing events"""

    @staticmethod
    async def start_flow(event_id: str, phone: str, db: AsyncSession):
        """Start event editing flow"""
        from app.models import Conversation

        # Get event
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await whatsapp_service.send_message(phone, "Event not found.")
            await send_back_to_menu(phone, db)
            return

        message = (
            "Edit event\n\n"
            f"Event: {event.title}\n\n"
            "What would you like to edit?\n"
            "1. Title\n"
            "2. Description\n"
            "3. Date and time\n"
            "4. Location\n"
            "5. Capacity\n"
            "6. Ticket price\n"
            "7. Category\n"
            "8. Cancel\n\n"
            "Reply with number (1-8)"
        )

        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)

        conversation.current_flow = 'event_editing'
        conversation.flow_state = {
            'event_id': str(event_id),
            'step': 'select_field'
        }
        await db.commit()

        await whatsapp_service.send_message(phone, message)
        await send_back_to_menu(phone, db)

    @staticmethod
    async def process_step(phone: str, message: str, db: AsyncSession):
        """Process editing flow step"""
        from app.models import Conversation

        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation or not conversation.flow_state:
            await whatsapp_service.send_message(phone, "Session expired. Try Manage event.")
            await send_back_to_menu(phone, db)
            return

        event_id = conversation.flow_state.get('event_id')
        step = conversation.flow_state.get('step')

        # Get event
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await whatsapp_service.send_message(phone, "Event not found.")
            conversation.current_flow = None
            conversation.flow_state = {}
            await db.commit()
            await send_back_to_menu(phone, db)
            return

        if step == 'select_field':
            await EventEditingFlow._handle_field_selection(
                event, message, phone, conversation, db
            )
        elif step == 'enter_value':
            await EventEditingFlow._handle_value_entry(
                event, message, phone, conversation, db
            )

    @staticmethod
    async def _handle_field_selection(
        event: Event,
        message: str,
        phone: str,
        conversation,
        db: AsyncSession
    ):
        """Handle field selection"""
        choice = message.strip()

        field_map = {
            '1': ('title', 'Title', event.title),
            '2': ('description', 'Description', event.description),
            '3': ('event_date', 'Date and time', event.event_date.strftime('%Y-%m-%d %H:%M')),
            '4': ('venue_name', 'Location', event.venue_name),
            '5': ('capacity', 'Capacity', str(event.capacity)),
            '6': ('ticket_price', 'Ticket price', f"NGN {event.ticket_price:,.0f}"),
            '7': ('category', 'Category', event.category or 'None'),
            '8': ('cancel', 'Cancel', None)
        }

        if choice == '8':
            await whatsapp_service.send_message(phone, "Edit cancelled.")
            conversation.current_flow = None
            conversation.flow_state = {}
            await db.commit()
            await send_back_to_menu(phone, db)
            return

        if choice not in field_map:
            await whatsapp_service.send_message(
                phone,
                "Invalid choice. Reply with 1-8."
            )
            await send_back_to_menu(phone, db)
            return

        field_name, field_label, current_value = field_map[choice]

        prompt_message = f"Edit {field_label}\n\n"
        prompt_message += f"Current: {current_value}\n\n"

        if field_name == 'event_date':
            prompt_message += "Enter new date and time:\nFormat: YYYY-MM-DD HH:MM\nExample: 2026-03-15 19:00"
        elif field_name == 'capacity':
            prompt_message += "Enter new capacity (number)."
        elif field_name == 'ticket_price':
            prompt_message += "Enter new price in NGN."
        elif field_name == 'category':
            prompt_message += "Enter category: concert, party, conference, sports, wedding, crusade, other"
        else:
            prompt_message += f"Enter new {field_label.lower()}."

        conversation.flow_state['step'] = 'enter_value'
        conversation.flow_state['field_name'] = field_name
        conversation.flow_state['field_label'] = field_label
        flag_modified(conversation, 'flow_state')
        await db.commit()

        await whatsapp_service.send_message(phone, prompt_message)
        await send_back_to_menu(phone, db)

    @staticmethod
    async def _handle_value_entry(
        event: Event,
        message: str,
        phone: str,
        conversation,
        db: AsyncSession
    ):
        """Handle new value entry"""
        field_name = conversation.flow_state.get('field_name')
        field_label = conversation.flow_state.get('field_label')
        new_value = message.strip()

        try:
            if field_name == 'event_date':
                new_value = datetime.strptime(new_value, '%Y-%m-%d %H:%M')
                if new_value < datetime.now():
                    await whatsapp_service.send_message(
                        phone,
                        "Event date must be in the future. Try again or type Cancel."
                    )
                    await send_back_to_menu(phone, db)
                    return
            elif field_name == 'capacity':
                new_value = int(new_value)
                if new_value < event.tickets_sold:
                    await whatsapp_service.send_message(
                        phone,
                        f"Capacity cannot be less than tickets sold ({event.tickets_sold}). Try again or type Cancel."
                    )
                    await send_back_to_menu(phone, db)
                    return
            elif field_name == 'ticket_price':
                new_value = float(new_value.replace('NGN', '').replace(',', '').strip())
                if new_value < 0:
                    await whatsapp_service.send_message(
                        phone,
                        "Price cannot be negative. Try again or type Cancel."
                    )
                    await send_back_to_menu(phone, db)
                    return

            setattr(event, field_name, new_value)
            await db.commit()

            if field_name in ['event_date', 'venue_name']:
                await EventEditingFlow._notify_attendees(event, field_name, new_value, db)

            display_value = new_value
            if field_name == 'event_date' and isinstance(new_value, datetime):
                display_value = new_value.strftime('%Y-%m-%d %H:%M')
            elif field_name == 'ticket_price':
                display_value = f"NGN {new_value:,.0f}"

            message = (
                f"{field_label} updated.\n\n"
                f"Event: {event.title}\n"
                f"New {field_label}: {display_value}\n\n"
            )

            if field_name in ['event_date', 'venue_name']:
                message += "All attendees have been notified.\n\n"

            message += "Edit another field? Type Edit. Or type Done to finish."

            await whatsapp_service.send_message(phone, message)
            await send_back_to_menu(phone, db)

            conversation.current_flow = None
            conversation.flow_state = {}
            await db.commit()

        except ValueError:
            await whatsapp_service.send_message(
                phone,
                "Invalid format. Try again or type Cancel."
            )
            await send_back_to_menu(phone, db)
        except Exception:
            await whatsapp_service.send_message(
                phone,
                "Something went wrong. Please try again."
            )
            await send_back_to_menu(phone, db)

    @staticmethod
    async def _notify_attendees(
        event: Event,
        field_name: str,
        new_value: Any,
        db: AsyncSession
    ):
        """Notify attendees of event changes"""
        result = await db.execute(
            select(Booking).where(
                Booking.event_id == event.id,
                Booking.status == 'confirmed'
            )
        )
        bookings = result.scalars().all()

        if field_name == 'event_date':
            change_text = f"Date changed to: {new_value.strftime('%A, %B %d, %Y at %I:%M %p')}"
        elif field_name == 'venue_name':
            change_text = f"Location changed to: {new_value}"
        else:
            change_text = f"{field_name} updated"

        notification = (
            "Event update\n\n"
            f"Event: {event.title}\n\n"
            f"{change_text}\n\n"
            "Your tickets remain valid.\n"
            "Type My tickets to view."
        )

        for booking in bookings:
            try:
                await whatsapp_service.send_message(booking.phone, notification)
            except Exception as e:
                print(f"Failed to notify {booking.phone}: {e}")
