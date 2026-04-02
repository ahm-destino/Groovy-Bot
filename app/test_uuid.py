import asyncio
from sqlalchemy import text, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
import uuid
from app.config import settings

Base = declarative_base()

class TestUser(Base):
    __tablename__ = "test_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50))

async def test_uuid():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS test_users CASCADE;"))
        await conn.run_sync(Base.metadata.create_all)
        
        print("Checking test_users table...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'test_users'
        """))
        for row in result:
            print(f"Column: {row.column_name}, Type: {row.data_type}")

if __name__ == "__main__":
    asyncio.run(test_uuid())
