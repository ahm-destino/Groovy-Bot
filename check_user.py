"""Check if a user exists and view their details by phone number."""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings


async def check_user(phone: str):
    """Check user details by phone number."""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    
    async with engine.connect() as conn:
        try:
            result = await conn.execute(
                text("""
                    SELECT id, phone, first_name, last_name, email, whatsapp_name, created_at
                    FROM users 
                    WHERE phone = :phone
                """),
                {"phone": phone}
            )
            row = result.fetchone()
            
            if row:
                print(f"✅ User found!")
                print(f"   Phone: {row.phone}")
                print(f"   Name: {row.first_name} {row.last_name}")
                print(f"   WhatsApp Name: {row.whatsapp_name}")
                print(f"   Email: {row.email}")
                print(f"   Created: {row.created_at}")
                return True
            else:
                print(f"❌ User not found with phone: {phone}")
                return False
                
        except Exception as e:
            print(f"Error checking user: {e}")
            return False


if __name__ == "__main__":
    # Get phone from command line or use default test number
    phone = sys.argv[1] if len(sys.argv) > 1 else "2347039919574"
    asyncio.run(check_user(phone))
