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
        echo=False  # Disable echo for cleaner output
    )
    
    async with engine.begin() as conn:
        print("Enabling PostGIS extension...")
        from sqlalchemy import text
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            print("✅ PostGIS extension enabled.")
        except Exception as e:
            print(f"⚠️  Note: Could not enable extension via script: {e}")
            print("Trying to proceed anyway...")
        
        print("\n🗑️  Dropping existing tables...")
        try:
            await conn.execute(text("DROP TABLE IF EXISTS tickets, bookings, promo_codes, ticket_tiers, events, message_logs, conversations, users, interaction_logs CASCADE;"))
            print("✅ Tables dropped.")
        except Exception as e:
            print(f"⚠️  Note: Error dropping tables: {e}")

        print("\n📊 Creating tables...")
        try:
            # This will create all tables defined in models
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(init_db())
