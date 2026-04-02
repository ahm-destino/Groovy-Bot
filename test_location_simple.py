#!/usr/bin/env python3
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

async def main():
    output = []
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.first_name.isnot(None)))
        users = result.scalars().all()
        
        output.append("=" * 70)
        output.append("USERS WITH LOCATIONS:")
        output.append("=" * 70)
        
        if not users:
            output.append("No users found")
        else:
            for user in users:
                output.append(f"\nUser: {user.first_name} {user.last_name} ({user.phone})")
                
                if user.location_preference:
                    coords_result = await db.execute(
                        text("SELECT ST_X(location_preference::geometry) as lng, ST_Y(location_preference::geometry) as lat FROM users WHERE id = :id"),
                        {"id": user.id}
                    )
                    coords = coords_result.fetchone()
                    if coords:
                        lng, lat = coords
                        output.append(f"  📍 Location: Lat {lat:.6f}, Lng {lng:.6f}")
                        
                        # Create event
                        event = Event(
                            title="🎉 Stefan Test Event - Near You!",
                            description="Test event at your location",
                            category="party",
                            event_date=datetime.now() + timedelta(hours=1),
                            location_name="Your Location",
                            location_point=WKTElement(f'POINT({lng} {lat})', srid=4326),
                            start_time=datetime.now() + timedelta(hours=1),
                            end_time=datetime.now() + timedelta(hours=3),
                            is_public=True,
                            ticket_limit=100
                        )
                        
                        db.add(event)
                        await db.commit()
                        
                        output.append(f"  ✅ Event created: {event.title}")
                        output.append(f"     Event ID: {event.id}")
                        output.append(f"     Time: {event.event_date.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        output.append(f"  ❌ Could not extract coordinates")
                else:
                    output.append(f"  ❌ No location saved")
    
    # Write to file
    with open('/app/location_check.txt', 'w') as f:
        f.write('\n'.join(output))
    
    # Also print
    for line in output:
        print(line)

asyncio.run(main())
