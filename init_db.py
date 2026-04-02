import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.config import settings
import app.models  # Import models to ensure they are registered with Base

async def init_db():
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        print("Enabling PostGIS extension...")
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        
        print("Dropping existing tables with CASCADE...")
        await conn.execute(text("DROP TABLE IF EXISTS tickets, bookings, promo_codes, ticket_tiers, events, message_logs, conversations, users CASCADE;"))
        
        print("Creating tables...")
        # This will create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
