#!/usr/bin/env python3
"""Manually create a mock event for testing booking flow"""
import asyncpg
import asyncio
from datetime import datetime, timedelta

SUPABASE_URL = 'postgresql://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres'

async def main():
    try:
        print("\n🔌 Connecting to Supabase...")
        conn = await asyncpg.connect(SUPABASE_URL, timeout=10)
        print("✅ Connected!\n")
        
        # Get the most recent user
        user = await conn.fetchrow('''
            SELECT id, phone, ST_Y(location_preference::geometry) as lat, ST_X(location_preference::geometry) as lng,
                   first_name, last_name 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        
        if not user:
            print("❌ No users found in database!")
            await conn.close()
            return
        
        user_id = user['id']
        phone = user['phone']
        first_name = user['first_name']
        last_name = user['last_name']
        lat = user['lat']
        lng = user['lng']
        
        print(f"👤 Found user: {first_name} {last_name} ({phone})")
        print(f"📍 Location: Lat {lat}, Lng {lng}\n")
        
        if not lat or not lng:
            print("❌ User has no location saved!")
            await conn.close()
            return
        
        # Create mock event
        print("🎉 Creating mock event...")
        event_id = __import__('uuid').uuid4()
        
        await conn.execute('''
            INSERT INTO events (
                id, host_id, title, description, category, event_date,
                location_lat, location_lng, full_address, venue_name,
                capacity, ticket_price, currency, status, created_via
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
        ''', 
            event_id,
            user_id,  # host_id
            "🎉 Stefan's Exclusive Flash Event - JUST FOR YOU!",
            "This event was created right where you are! Limited time only. Book now to secure your spot!",
            "party",
            datetime.now() + timedelta(hours=2),  # event_date
            lat,
            lng,
            "Your Location",
            "Secret Venue",
            50,  # capacity
            5000,  # ticket_price
            "NGN",
            "active",
            "whatsapp"
        )
        
        print(f"✅ Mock event created: {event_id}\n")
        
        # Show event details
        event = await conn.fetchrow(
            'SELECT id, title, ticket_price, capacity, created_at FROM events WHERE id = $1',
            event_id
        )
        
        print("📊 Event Details:")
        print(f"  Title: {event['title']}")
        print(f"  Price: NGN {event['ticket_price']}")
        print(f"  Capacity: {event['capacity']} tickets")
        print(f"  Created: {event['created_at']}\n")
        
        await conn.close()
        print("✅ Mock event is ready for booking! Send a message to see it.\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
