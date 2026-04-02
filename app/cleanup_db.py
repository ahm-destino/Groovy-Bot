import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def cleanup():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        print("Forcing drop of all tables...")
        tables = ["tickets", "bookings", "promo_codes", "ticket_tiers", "events", "message_logs", "conversations", "users", "test_users"]
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
            print(f"Dropped {table} (if it existed)")
            
        print("\nChecking remaining tables in public schema...")
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        for row in result:
            print(f"Remaining Table: {row[0]}")

if __name__ == "__main__":
    asyncio.run(cleanup())
