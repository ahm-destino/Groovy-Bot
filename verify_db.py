#!/usr/bin/env python3
"""Quick test to check and demonstrate the exact issue"""
import asyncio
import os
import sys
sys.path.insert(0, '/app')
os.chdir('/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.config import settings
from app.models import User

async def verify_database():
    """Check the actual state of the database"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    async with async_session() as db:
        # Check total users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print(f"Total users in database: {len(users)}")
        for user in users:
            status = "✅ COMPLETE" if (user.first_name and user.last_name) else "❌ INCOMPLETE"
            print(f"  {status} - {user.phone}: {user.first_name} {user.last_name} ({user.email})")
        
        # Now let's test with a specific phone number
        test_phone = "+234901234567"
        result = await db.execute(select(User).where(User.phone == test_phone))
        user = result.scalar_one_or_none()
        
        print(f"\nTest phone '{test_phone}':")
        print(f"  User exists: {user is not None}")
        
        if user:
            print(f"  First name: {user.first_name}")
            print(f"  Last name: {user.last_name}")
            profile_complete = bool(user.first_name and user.last_name)
            print(f"  Profile complete: {profile_complete}")

if __name__ == "__main__":
    asyncio.run(verify_database())
