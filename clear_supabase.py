#!/usr/bin/env python
"""Clear Supabase database - the REAL database the app uses"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres.hwwzbsppzwcyvambeade:GKQEla5wds9ydyRQ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

async def main():
    print("\n🔴 CLEARING SUPABASE DATABASE\n")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            tables = [
                "message_logs",
                "interaction_logs",
                "tickets",
                "bookings",
                "events",
                "conversations",
                "users",
                "promo_codes",
                "ticket_tiers"
            ]
            
            for table in tables:
                try:
                    await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                    print(f"✅ {table} cleared")
                except Exception as e:
                    print(f"⚠️  {table}: {str(e)}")
            
            print("\n✅ SUPABASE CLEARED!\n")
            
            # Verify
            result = await conn.execute(text("SELECT COUNT(*) FROM users;"))
            user_count = result.scalar()
            
            result = await conn.execute(text("SELECT COUNT(*) FROM conversations;"))
            convo_count = result.scalar()
            
            print(f"Users: {user_count}")
            print(f"Conversations: {convo_count}")
            
            if user_count == 0 and convo_count == 0:
                print("\n✅ SUPABASE IS NOW CLEAN!\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
