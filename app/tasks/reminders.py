from app.celery_app import celery_app
from app.database import AsyncSessionLocal


@celery_app.task(name='app.tasks.reminders.send_24h_reminders_task')
def send_24h_reminders_task():
    """
    Send 24-hour event reminders
    Runs daily at 9 AM
    """
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    from app.models import Event, Ticket, User
    from app.services.whatsapp import whatsapp_service

    async def run():
        async with AsyncSessionLocal() as db:
            now = datetime.now()
            target_time_start = now + timedelta(hours=23, minutes=30)
            target_time_end = now + timedelta(hours=24, minutes=30)

            result = await db.execute(
                select(Event).where(
                    and_(
                        Event.event_date >= target_time_start,
                        Event.event_date <= target_time_end,
                        Event.status == 'active'
                    )
                )
            )
            events = result.scalars().all()

            reminder_count = 0

            for event in events:
                result = await db.execute(
                    select(Ticket).where(
                        and_(
                            Ticket.event_id == event.id,
                            Ticket.status == 'valid'
                        )
                    )
                )
                tickets = result.scalars().all()

                for ticket in tickets:
                    result = await db.execute(
                        select(User).where(User.id == ticket.user_id)
                    )
                    user = result.scalar_one()

                    message = "Reminder: event tomorrow.\n\n"
                    message += f"{event.title}\n"
                    message += f"Date: {event.event_date.strftime('%A, %B %d at %I:%M %p')}\n"

                    if event.is_anonymous and not event.location_revealed:
                        message += f"Location reveals {event.location_reveal_hours_before}hr before\n"
                    else:
                        message += f"Venue: {event.venue_name}\n"

                    message += f"\nTicket: {ticket.ticket_code}\n"
                    message += "\nSee you tomorrow."

                    await whatsapp_service.send_message(user.phone, message)
                    reminder_count += 1

            return reminder_count

    count = asyncio.run(run())
    return f"Sent {count} 24-hour reminders"


@celery_app.task(name='app.tasks.reminders.send_1h_reminders_task')
def send_1h_reminders_task():
    """
    Send 1-hour event reminders
    Runs every hour
    """
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    from app.models import Event, Ticket, User
    from app.services.whatsapp import whatsapp_service

    async def run():
        async with AsyncSessionLocal() as db:
            now = datetime.now()
            target_time_start = now + timedelta(minutes=50)
            target_time_end = now + timedelta(minutes=70)

            result = await db.execute(
                select(Event).where(
                    and_(
                        Event.event_date >= target_time_start,
                        Event.event_date <= target_time_end,
                        Event.status == 'active'
                    )
                )
            )
            events = result.scalars().all()

            reminder_count = 0

            for event in events:
                result = await db.execute(
                    select(Ticket).where(
                        and_(
                            Ticket.event_id == event.id,
                            Ticket.status == 'valid'
                        )
                    )
                )
                tickets = result.scalars().all()

                for ticket in tickets:
                    result = await db.execute(
                        select(User).where(User.id == ticket.user_id)
                    )
                    user = result.scalar_one()

                    message = "Event starts in 1 hour.\n\n"
                    message += f"{event.title}\n"
                    message += f"Time: {event.event_date.strftime('%I:%M %p')}\n"
                    message += f"Venue: {event.venue_name}\n"

                    if event.full_address:
                        message += f"\n{event.full_address}\n"

                    if ticket.entry_code:
                        message += f"\nEntry code: {ticket.entry_code}\n"

                    message += "\nHave your QR code ready."

                    await whatsapp_service.send_message(user.phone, message)
                    reminder_count += 1

            return reminder_count

    count = asyncio.run(run())
    return f"Sent {count} 1-hour reminders"
