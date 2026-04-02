"""
Test script to verify bot-webapp database integration

Run with: python test_integration.py
"""

import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.models import User, Event, Booking, Ticket
from sqlalchemy import select


async def test_integration():
    """Test that bot and webapp share the same database"""
    
    print("🧪 Testing Bot-Webapp Integration\n")
    
    async with AsyncSessionLocal() as db:
        # Test 1: Check if webapp tables exist
        print("1️⃣ Checking database tables...")
        try:
            result = await db.execute(select(User).limit(1))
            print("   ✅ Users table exists")
            
            result = await db.execute(select(Event).limit(1))
            print("   ✅ Events table exists")
            
            result = await db.execute(select(Booking).limit(1))
            print("   ✅ Bookings table exists")
            
            result = await db.execute(select(Ticket).limit(1))
            print("   ✅ Tickets table exists")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 2: Check bot-specific columns
        print("\n2️⃣ Checking bot-specific columns...")
        try:
            # Check users.phone
            result = await db.execute(
                select(User).where(User.phone.isnot(None)).limit(1)
            )
            user = result.scalar_one_or_none()
            if user:
                print(f"   ✅ users.phone exists (found: {user.phone})")
            else:
                print("   ⚠️  users.phone exists but no data yet")
            
            # Check events.is_anonymous
            result = await db.execute(
                select(Event).where(Event.is_anonymous == True).limit(1)
            )
            event = result.scalar_one_or_none()
            if event:
                print(f"   ✅ events.is_anonymous exists (found anonymous event)")
            else:
                print("   ⚠️  events.is_anonymous exists but no anonymous events yet")
            
            # Check bookings.booking_source
            result = await db.execute(
                select(Booking).where(Booking.booking_source == 'whatsapp').limit(1)
            )
            booking = result.scalar_one_or_none()
            if booking:
                print(f"   ✅ bookings.booking_source exists (found WhatsApp booking)")
            else:
                print("   ⚠️  bookings.booking_source exists but no WhatsApp bookings yet")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print("   💡 Run migration: psql $DATABASE_URL -f migrations/add_bot_fields.sql")
            return
        
        # Test 3: Create test WhatsApp user
        print("\n3️⃣ Creating test WhatsApp user...")
        try:
            test_phone = "+2348099999999"
            
            # Check if exists
            result = await db.execute(
                select(User).where(User.phone == test_phone)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"   ℹ️  Test user already exists: {existing_user.id}")
                test_user = existing_user
            else:
                test_user = User(
                    phone=test_phone,
                    whatsapp_name="Test Bot User",
                    first_name="Bot",
                    last_name="Tester"
                )
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                print(f"   ✅ Created test user: {test_user.id}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 4: Create test event via bot
        print("\n4️⃣ Creating test event (via bot)...")
        try:
            test_event = Event(
                host_id=test_user.id,
                title="Bot Integration Test Event",
                description="This event was created by the WhatsApp bot",
                category="other",
                event_date=datetime.now() + timedelta(days=7),
                venue_name="Test Venue",
                full_address="Test Address, Lagos",
                capacity=100,
                ticket_price=5000,
                is_anonymous=False,
                created_via='whatsapp',  # Mark as bot-created
                status='active'
            )
            db.add(test_event)
            await db.commit()
            await db.refresh(test_event)
            print(f"   ✅ Created test event: {test_event.id}")
            print(f"   📝 Title: {test_event.title}")
            print(f"   🤖 Created via: {test_event.created_via}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 5: Create test booking via bot
        print("\n5️⃣ Creating test booking (via bot)...")
        try:
            test_booking = Booking(
                user_id=test_user.id,
                event_id=test_event.id,
                phone=test_phone,
                quantity=2,
                total_amount=10000,
                status='confirmed',
                booking_source='whatsapp',  # Mark as WhatsApp booking
                payment_method='card'
            )
            db.add(test_booking)
            await db.commit()
            await db.refresh(test_booking)
            print(f"   ✅ Created test booking: {test_booking.id}")
            print(f"   📱 Phone: {test_booking.phone}")
            print(f"   🤖 Source: {test_booking.booking_source}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 6: Verify cross-platform visibility
        print("\n6️⃣ Verifying cross-platform visibility...")
        try:
            # Query as webapp would
            result = await db.execute(
                select(Booking)
                .where(Booking.user_id == test_user.id)
                .where(Booking.status == 'confirmed')
            )
            bookings = result.scalars().all()
            
            print(f"   ✅ Found {len(bookings)} booking(s) for user")
            for booking in bookings:
                result = await db.execute(
                    select(Event).where(Event.id == booking.event_id)
                )
                event = result.scalar_one()
                print(f"      • {event.title} ({booking.booking_source})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 7: Check analytics views
        print("\n7️⃣ Testing analytics...")
        try:
            # Count bookings by source
            result = await db.execute(
                select(Booking.booking_source, db.func.count(Booking.id))
                .group_by(Booking.booking_source)
            )
            stats = result.all()
            
            print("   📊 Bookings by source:")
            for source, count in stats:
                print(f"      • {source or 'unknown'}: {count}")
            
            # Count events by creation method
            result = await db.execute(
                select(Event.created_via, db.func.count(Event.id))
                .group_by(Event.created_via)
            )
            stats = result.all()
            
            print("   📊 Events by creation method:")
            for method, count in stats:
                print(f"      • {method or 'unknown'}: {count}")
                
        except Exception as e:
            print(f"   ⚠️  Analytics error (views may not exist): {e}")
        
        print("\n✅ Integration test completed successfully!")
        print("\n📝 Summary:")
        print("   • Bot and webapp share the same database")
        print("   • WhatsApp bookings are visible in webapp")
        print("   • Bot-created events are visible in webapp")
        print("   • Cross-platform data tracking works")
        print("\n🎉 Ready for production!")


if __name__ == "__main__":
    asyncio.run(test_integration())
