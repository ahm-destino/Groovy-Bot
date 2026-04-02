#!/usr/bin/env python3
"""Check user location and create test event nearby"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.config import settings
from app.models import User, Event
from datetime import datetime, timedelta
from geoalchemy2 import WKTElement

async def check_and_create_event():
    """Check user location and create nearby event"""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    async with async_session() as db:
        # Get all registered users
        result = await db.execute(select(User).where(User.first_name.isnot(None)))
        users = result.scalars().all()
        
        print("=" * 70)
        print("USERS IN DATABASE:")
        print("=" * 70)
        
        if not users:
            print("❌ No registered users found!")
            return
        
        for user in users:
            print(f"\n👤 User: {user.first_name} {user.last_name}")
            print(f"   Phone: {user.phone}")
            print(f"   Email: {user.email}")
            
            if user.location_preference:
                # Extract coordinates from PostGIS point
                result = await db.execute(
                    text("SELECT ST_X(location_preference::geometry) as lng, ST_Y(location_preference::geometry) as lat FROM users WHERE id = :id"),
                    {"id": user.id}
                )
                coords = result.fetchone()
                if coords:
                    lng, lat = coords
                    print(f"   📍 Location: Lat {lat:.6f}, Lng {lng:.6f}")
                    
                    # Create event at user's location
                    print(f"\n   Creating test event near this location...")
                    
                    event = Event(
                        title="🎉 Stefan's Test Party - Right by you!",
                        description="A test event created right near your location to verify notifications work!",
                        category="party",
                        event_date=datetime.now() + timedelta(hours=2),
                        location_name="Near You",
                        location_point=WKTElement(f'POINT({lng} {lat})', srid=4326),
                        start_time=datetime.now() + timedelta(hours=2),
                        end_time=datetime.now() + timedelta(hours=4),
                        is_public=True,
                        ticket_limit=50
                    )
                    
                    db.add(event)
                    await db.commit()
                    
                    print(f"   ✅ Event created!")
                    print(f"      - Title: {event.title}")
                    print(f"      - Location: Same as yours (Lat {lat:.6f}, Lng {lng:.6f})")
                    print(f"      - Time: {event.event_date.strftime('%Y-%m-%d %H:%M')}")
                    print(f"      - Event ID: {event.id}")
                    
                else:
                    print(f"   ❌ Could not extract coordinates from location_preference")
            else:
                print(f"   ❌ No location preference saved")

if __name__ == "__main__":
    asyncio.run(check_and_create_event())
