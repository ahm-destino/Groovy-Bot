from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models import User, Event
from app.services.whatsapp import whatsapp_service
from geoalchemy2.functions import ST_Distance
from geoalchemy2.elements import WKTElement


class NotificationService:
    """Service for sending proximity-based event notifications"""

    @staticmethod
    async def notify_nearby_users(event: Event, db: AsyncSession):
        """Find users within 50 miles of the event and notify them"""
        if not event.location_lat or not event.location_lng:
            print(f"Skipping notifications for event {event.id}: No coordinates")
            return

        # Create point for the event
        event_point = f'POINT({event.location_lng} {event.location_lat})'

        query = select(User).where(
            text("ST_DWithin(location_preference, ST_GeographyFromText(:point), :radius)")
        ).params(point=f'SRID=4326;{event_point}', radius=80467)  # 50 miles in meters

        result = await db.execute(query)
        nearby_users = result.scalars().all()

        print(f"Found {len(nearby_users)} users near event '{event.title}'")

        for user in nearby_users:
            # Skip the host
            if user.id == event.host_id:
                continue

            await NotificationService.send_event_alert(user, event)

    @staticmethod
    async def send_event_alert(user: User, event: Event):
        """Send a WhatsApp message about the new event"""
        message = (
            "New event near you.\n\n"
            f"{event.title}\n"
            f"Date: {event.event_date.strftime('%a, %b %d - %I:%M %p')}\n"
            f"Venue: {event.venue_name}\n"
            f"Ticket: NGN {event.ticket_price:,.0f}\n\n"
            "Type Events near me to see details."
        )

        try:
            await whatsapp_service.send_message(user.phone, message)
            print(f"Sent notification to {user.phone} for event {event.id}")
        except Exception as e:
            print(f"Failed to send notification to {user.phone}: {e}")
