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
        
        print(f"{'Time':<25} | {'Intent':<20} | {'Content':<30} | {'Entities'}")
        print("-" * 120)
        for log in logs:
            print(f"{str(log.created_at):<25} | {str(log.intent_detected):<20} | {str(log.content)[:30]:<30} | {log.entities}")

if __name__ == "__main__":
    asyncio.run(check_logs())
