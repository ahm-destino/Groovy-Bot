#!/usr/bin/env python
"""Quick database state check"""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Conversation

async def main():
    engine = create_async_engine(
        settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
        echo=False
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        user_count = await session.scalar(select(func.count()).select_from(User))
        convo_count = await session.scalar(select(func.count()).select_from(Conversation))
        
        print(f"\n=== DATABASE STATE ===")
        print(f"Users: {user_count}")
        print(f"Conversations: {convo_count}")
        print(f"====================\n")
        
        if user_count == 0 and convo_count == 0:
            print("✅ DATABASE IS CLEAN - READY FOR TESTING")
        else:
            print("⚠️  DATABASE STILL HAS DATA")

if __name__ == "__main__":
    asyncio.run(main())
