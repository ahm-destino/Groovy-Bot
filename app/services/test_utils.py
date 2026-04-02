import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Event, User
import uuid


async def create_mock_event_near_user(phone: str, delay_mins: int, lat: float, lng: float):
    """
    Background task to create a mock event near a user after a delay.
    """
    print(f"Mock event timer started for {phone}: {delay_mins} minutes...")
    await asyncio.sleep(delay_mins * 60)

    async with AsyncSessionLocal() as db:
        # Get user
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()

        if not user:
            print(f"User {phone} not found.")
            return

        # Create mock event
        event = Event(
            id=uuid.uuid4(),
            title=f"Test Event ({delay_mins}m Delay)",
            description=f"This is an automatically generated event for testing proximity notifications. Created {delay_mins} minutes after you shared your location.",
            event_date=datetime.now() + timedelta(days=2),
            venue_name="Testing Grounds, Lagos",
            full_address="123 Test Street, Victoria Island, Lagos",
            ticket_price=2500.0,
            capacity=100,
            tickets_sold=0,
            status='active',
            category='concert',
            location_lat=lat,
            location_lng=lng,
            host_id=user.id
        )

        db.add(event)
        await db.commit()
        print(f"Mock event created for {phone} after {delay_mins}m")

        # Trigger notification
        from app.services.notifications import NotificationService
        await NotificationService.notify_nearby_users(event, db)


async def bypass_payment(booking_id: str, db):
    """Force confirm a booking without Paystack"""
    from app.models import Booking
    from app.services.tickets import generate_tickets_for_booking
    from app.services.bookings import send_booking_confirmation

    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if booking:
        booking.status = 'confirmed'
        booking.confirmed_at = datetime.now()
        booking.payment_reference = f"MOCK-{uuid.uuid4().hex[:8]}"
        await db.commit()

        tickets = await generate_tickets_for_booking(booking, db)
        await send_booking_confirmation(booking, tickets, db)
        return True
    return False
