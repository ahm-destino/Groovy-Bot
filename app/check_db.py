import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def check_db():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    
    async with engine.connect() as conn:
        print("Checking users table...")
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """))
            rows = result.all()
            if not rows:
                print("Table 'users' does not exist.")
            for row in rows:
                print(f"Column: {row.column_name}, Type: {row.data_type}")
        except Exception as e:
            print(f"Error checking users table: {e}")

        print("\nChecking bookings table...")
        try:
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'bookings'
            """))
            rows = result.all()
            if not rows:
                print("Table 'bookings' does not exist.")
            for row in rows:
                print(f"Column: {row.column_name}, Type: {row.data_type}")
        except Exception as e:
            print(f"Error checking bookings table: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
