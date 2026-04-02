import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import MessageLog

async def check_logs():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(MessageLog).order_by(MessageLog.created_at.desc()).limit(20)
        )
        logs = result.scalars().all()
        
        print(f"{'Time':<25} | {'Phone':<15} | {'Type':<10} | {'Content'}")
        print("-" * 80)
        for log in logs:
            print(f"{str(log.created_at):<25} | {log.phone:<15} | {log.message_type:<10} | {log.content}")

if __name__ == "__main__":
    asyncio.run(check_logs())
