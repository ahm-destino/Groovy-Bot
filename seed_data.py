"""
Seed database with test data for development/testing

Run with: python seed_data.py
"""

import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.models import User, Event


async def seed_database():
    """Create test users and events"""
    async with AsyncSessionLocal() as db:
        print("🌱 Seeding database...")
        
        # Create test users
        users = [
            User(
                phone="+2348012345678",
                whatsapp_name="Test User 1",
                first_name="John",
                last_name="Doe",
                email="john@example.com"
            ),
            User(
                phone="+2348087654321",
                whatsapp_name="Test Organizer",
                first_name="Jane",
                last_name="Smith",
                email="jane@example.com"
            )
        ]
        
        for user in users:
            db.add(user)
        
        await db.commit()
        print(f"✅ Created {len(users)} test users")
        
        # Refresh to get IDs
        for user in users:
            await db.refresh(user)
        
        # Create test events
        now = datetime.now()
        
        events = [
            # Public concert
            Event(
                host_id=users[1].id,
                title="Davido Live in Concert",
                description="Amazing concert featuring Davido, Tiwa Savage, and Rema. Don't miss this epic night!",
                category="concert",
                event_date=now + timedelta(days=7),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="Eko Convention Centre, Eko Atlantic City, Victoria Island, Lagos",
                venue_name="Eko Convention Centre",
                capacity=5000,
                tickets_sold=2347,
                ticket_price=15000,
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
            
            # Secret event with immediate reveal
            Event(
                host_id=users[1].id,
                title="Burna Boy Intimate Acoustic Session",
                description="Exclusive acoustic performance for 50 lucky fans. Includes drinks and light bites.",
                category="concert",
                event_date=now + timedelta(days=5),
                location_lat=6.4474,
                location_lng=3.4700,
                full_address="The Citadel, 21 Adeola Odeku Street, Victoria Island, Lagos",
                venue_name="The Citadel",
                capacity=50,
                tickets_sold=42,
                ticket_price=25000,
                currency="NGN",
                is_anonymous=True,
                anonymous_mode="location_hidden",
                location_reveal_trigger="immediate",
                entry_code_format="shared",
                shared_entry_code="BURNA2026",
                status="active"
            ),
            
            # VIP event with code required
            Event(
                host_id=users[1].id,
                title="Tech Founders Exclusive Dinner",
                description="Intimate dinner for tech founders and investors. Network with Lagos' top startup ecosystem players.",
                category="networking",
                event_date=now + timedelta(days=10),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="The Citadel, 21 Adeola Odeku Street, Victoria Island, Lagos",
                venue_name="The Citadel",
                capacity=50,
                tickets_sold=15,
                ticket_price=35000,
                currency="NGN",
                is_anonymous=True,
                anonymous_mode="code_required",
                secret_code="TECH2026",
                location_reveal_trigger="time_based",
                location_reveal_hours_before=1,
                entry_code_format="unique_per_ticket",
                status="active"
            ),
            
            # Wedding
            Event(
                host_id=users[1].id,
                title="Chidi & Amaka's Wedding",
                description="Join us as we celebrate the union of Chidi and Amaka. Dress code: Traditional attire.",
                category="wedding",
                event_date=now + timedelta(days=14),
                location_lat=6.5244,
                location_lng=3.3792,
                full_address="Oriental Hotel, 3 Lekki-Epe Expressway, Victoria Island, Lagos",
                venue_name="Oriental Hotel",
                capacity=300,
                tickets_sold=0,
                ticket_price=0,  # Free
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
            
            # Conference
            Event(
                host_id=users[1].id,
                title="Lagos Tech Summit 2026",
                description="Annual tech conference featuring speakers from Google, Microsoft, and local startups. Includes lunch and networking.",
                category="conference",
                event_date=now + timedelta(days=21),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="Landmark Event Centre, Water Corporation Drive, Victoria Island, Lagos",
                venue_name="Landmark Event Centre",
                capacity=1000,
                tickets_sold=456,
                ticket_price=20000,
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
            
            # Party
            Event(
                host_id=users[1].id,
                title="Afrobeats Night at Quilox",
                description="The hottest Afrobeats party in Lagos. DJ Spinall on the decks. VIP tables available.",
                category="party",
                event_date=now + timedelta(days=3),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="Quilox Nightclub, Ozumba Mbadiwe Avenue, Victoria Island, Lagos",
                venue_name="Quilox Nightclub",
                capacity=500,
                tickets_sold=234,
                ticket_price=10000,
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
            
            # Event happening soon (for testing 1hr reminder)
            Event(
                host_id=users[1].id,
                title="Test Event - Happening Soon",
                description="Test event for reminder testing",
                category="other",
                event_date=now + timedelta(hours=1, minutes=30),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="Test Venue, Lagos",
                venue_name="Test Venue",
                capacity=10,
                tickets_sold=0,
                ticket_price=1000,
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
            
            # Event tomorrow (for testing 24hr reminder)
            Event(
                host_id=users[1].id,
                title="Test Event - Tomorrow",
                description="Test event for 24hr reminder testing",
                category="other",
                event_date=now + timedelta(hours=24, minutes=30),
                location_lat=6.4281,
                location_lng=3.4219,
                full_address="Test Venue, Lagos",
                venue_name="Test Venue",
                capacity=10,
                tickets_sold=0,
                ticket_price=1000,
                currency="NGN",
                is_anonymous=False,
                status="active"
            ),
        ]
        
        for event in events:
            db.add(event)
        
        await db.commit()
        print(f"✅ Created {len(events)} test events")
        
        print("\n🎉 Database seeded successfully!")
        print("\n📝 Test Data Summary:")
        print(f"   Users: {len(users)}")
        print(f"   Events: {len(events)}")
        print("\n🔐 Secret Codes:")
        print("   TECH2026 - Tech Founders Dinner")
        print("\n📱 Test Phone Numbers:")
        print("   +2348012345678 - Test User")
        print("   +2348087654321 - Test Organizer")
        print("\n💡 Try these commands in WhatsApp:")
        print("   'Hi' - Welcome message")
        print("   'Concerts in Lagos' - See events")
        print("   'TECH2026' - Unlock secret event")
        print("   'Create event' - Start event creation")


if __name__ == "__main__":
    asyncio.run(seed_database())
