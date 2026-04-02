import asyncio
from sqlalchemy import text
from app.database import engine, Base
from app.models import * # Ensure all models are imported for metadata

async def reset_database():
    print("Resetting database...")
    async with engine.begin() as conn:
        tables = [
            "tickets", "bookings", "ticket_tiers", "promo_codes", 
            "events", "conversations", "message_logs", "users"
        ]
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        print("Tables dropped.")
        
        # Recreate everything
        await conn.run_sync(Base.metadata.create_all)
        print("Database schema recreated.")

if __name__ == "__main__":
    asyncio.run(reset_database())
