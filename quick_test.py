import asyncio
import sys
import json
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.config import settings
from app.models import User, Event
from datetime import datetime, timedelta
from geoalchemy2 import WKTElement

async def check_and_create():
    results = []
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.first_name.isnot(None)))
        users = result.scalars().all()
        
        results.append(f"Found {len(users)} registered users\n")
        
        for user in users:
            results.append(f"User: {user.first_name} {user.last_name} ({user.phone})")
            
            if user.location_preference:
                coords_result = await db.execute(
                    text("SELECT ST_X(location_preference::geometry) as lng, ST_Y(location_preference::geometry) as lat FROM users WHERE id = :id"),
                    {"id": user.id}
                )
                coords = coords_result.fetchone()
                if coords:
                    lng, lat = coords
                    results.append(f"  Location: Lat {lat:.6f}, Lng {lng:.6f}")
                    
                    # Create event at exact location
                    event = Event(
                        title="🎉 Test Event - Right at Your Location!",
                        description="This event was created at your exact location to test notifications.",
                        category="party",
                        event_date=datetime.now() + timedelta(minutes=30),
                        location_name="Your Location",
                        location_point=WKTElement(f'POINT({lng} {lat})', srid=4326),
                        start_time=datetime.now() + timedelta(minutes=30),
                        end_time=datetime.now() + timedelta(hours=2),
                        is_public=True,
                        ticket_limit=100
                    )
                    
                    db.add(event)
                    await db.commit()
                    
                    results.append(f"  ✅ Created test event!")
                    results.append(f"     Title: {event.title}")
                    results.append(f"     Event ID: {event.id}")
                    results.append(f"     Starts: {event.event_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    results.append(f"     Distance: 0 miles (AT YOUR LOCATION)")
                    results.append("")
            else:
                results.append(f"  ❌ No location saved")
    
    # Write to file
    output_text = '\n'.join(results)
    with open('/app/test_results.txt', 'w') as f:
        f.write(output_text)
    
    print(output_text)

asyncio.run(check_and_create())

