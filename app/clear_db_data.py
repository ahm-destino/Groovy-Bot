"""
Clear all data from database tables WITHOUT dropping the tables.
This allows fresh registration flow while preserving schema.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings


async def clear_data():
    """Clear all data from tables while preserving schema"""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        print("🔄 Clearing all data from tables (schema preserved)...\n")
        
        # List of tables to clear - order matters due to foreign keys
        tables_to_clear = [
            "message_logs",
            "interaction_logs",
            "tickets",
            "bookings",
            "promo_codes",
            "ticket_tiers",
            "events",
            "conversations",
            "users",
        ]
        
        for table in tables_to_clear:
            try:
                result = await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                print(f"✅ Cleared {table}")
            except Exception as e:
                print(f"⚠️  Could not clear {table}: {str(e)}")
        
        print("\n🔍 Verifying tables still exist...\n")
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        if tables:
            print("✅ Tables present in database:")
            for table in tables:
                print(f"   - {table}")
        else:
            print("❌ No tables found!")
        
        print("\n✨ Database cleared! Ready for fresh registration flow.\n")


if __name__ == "__main__":
    asyncio.run(clear_data())
