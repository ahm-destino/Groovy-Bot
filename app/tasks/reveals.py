from app.celery_app import celery_app
from app.database import AsyncSessionLocal


@celery_app.task(name='app.tasks.reveals.process_location_reveals_task')
def process_location_reveals_task():
    """
    Process location reveals for anonymous events
    Runs every hour
    """
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    from app.models import Event, Ticket, User
    from app.services.whatsapp import whatsapp_service

    async def run():
        async with AsyncSessionLocal() as db:
            current_time = datetime.now()

            result = await db.execute(
                select(Event).where(
                    and_(
                        Event.is_anonymous == True,
                        Event.location_reveal_trigger == 'time_based',
                        Event.location_revealed == False,
                        Event.status == 'active'
                    )
                )
            )
            events = result.scalars().all()

            revealed_count = 0

            for event in events:
                reveal_time = event.event_date - timedelta(hours=event.location_reveal_hours_before)

                if current_time >= reveal_time:
                    await reveal_event_location(event, db)
                    revealed_count += 1

            return revealed_count

    async def reveal_event_location(event, db):
        """Send location reveal to all ticket holders"""
        result = await db.execute(
            select(Ticket).where(
                and_(
                    Ticket.event_id == event.id,
                    Ticket.status == 'valid'
                )
            )
        )
        tickets = result.scalars().all()

        user_tickets = {}
        for ticket in tickets:
            if ticket.user_id not in user_tickets:
                result = await db.execute(
                    select(User).where(User.id == ticket.user_id)
                )
                user = result.scalar_one()
                user_tickets[user.phone] = []
            user_tickets[user.phone].append(ticket)

        for phone, user_ticket_list in user_tickets.items():
            await send_location_reveal(event, user_ticket_list, phone)

        event.location_revealed = True
        event.location_revealed_at = datetime.now()

        for ticket in tickets:
            ticket.location_revealed = True
            ticket.location_revealed_at = datetime.now()

        await db.commit()

    async def send_location_reveal(event, tickets, phone):
        """Send location reveal message to user"""
        hours_until = (event.event_date - datetime.now()).total_seconds() / 3600

        message = f"{event.title}\n"
        message += f"Starts in {int(hours_until)} hour(s).\n\n"
        message += "Location revealed:\n"
        message += f"{event.full_address}\n"
        message += f"Venue: {event.venue_name}\n\n"

        if event.entry_code_format == 'shared':
            message += f"Entry code: {event.shared_entry_code}\n"
            message += "Show at entrance.\n\n"
        elif event.entry_code_format == 'unique_per_ticket':
            message += "Your entry codes:\n"
            for i, ticket in enumerate(tickets, 1):
                message += f"Ticket {i}: {ticket.entry_code}\n"
            message += "\n"

        message += "Show your QR ticket and entry code at the door.\n"
        message += "Support: +234 XXX XXX XXXX\n\n"
        message += "See you soon."

        await whatsapp_service.send_message(phone, message)

        if event.location_lat and event.location_lng:
            await whatsapp_service.send_location(
                phone=phone,
                latitude=float(event.location_lat),
                longitude=float(event.location_lng),
                name=event.venue_name,
                address=event.full_address
            )

    count = asyncio.run(run())
    return f"Revealed location for {count} events"
