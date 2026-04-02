#!/usr/bin/env python3
"""Query Supabase for user locations"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models import User

# Supabase connection
DATABASE_URL = "postgresql+asyncpg://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

async def check_users():
    """Query users from Supabase"""
    engine = create_async_engine(DATABASE_URL, echo=False, ssl=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    async with async_session() as db:
        # Get all registered users
        result = await db.execute(select(User).where(User.first_name.isnot(None)).order_by(User.created_at.desc()).limit(10))
        users = result.scalars().all()
        
        print("=" * 80)
        print("REGISTERED USERS IN SUPABASE:")
        print("=" * 80)
        
        if not users:
            print("No users found!")
            return
        
        for i, user in enumerate(users, 1):
            print(f"\n{i}. {user.first_name} {user.last_name}")
            print(f"   Phone: {user.phone}")
            print(f"   Email: {user.email}")
            print(f"   Created: {user.created_at}")
            
            # Try to extract coordinates
            if user.location_preference:
                try:
                    coords_result = await db.execute(
                        text("SELECT ST_AsText(location_preference) as location_text FROM users WHERE id = :id"),
                        {"id": user.id}
                    )
                    coords = coords_result.fetchone()
                    if coords and coords[0]:
                        print(f"   📍 Location (WKT): {coords[0]}")
                    
                    # Try to get X, Y coordinates
                    coords_result2 = await db.execute(
                        text("SELECT ST_X(location_preference::geometry) as lng, ST_Y(location_preference::geometry) as lat FROM users WHERE id = :id"),
                        {"id": user.id}
                    )
                    coords2 = coords_result2.fetchone()
                    if coords2:
                        lng, lat = coords2
                        print(f"   📍 Coordinates: Lat {lat:.6f}, Lng {lng:.6f}")
                except Exception as e:
                    print(f"   ❌ Error extracting coordinates: {str(e)}")
            else:
                print(f"   📍 Location: Not set")
        
        print(f"\n{'=' * 80}")

asyncio.run(check_users())
