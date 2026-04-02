from app.celery_app import celery_app
from app.database import AsyncSessionLocal


@celery_app.task(name='app.tasks.bookings.cleanup_expired_bookings_task')
def cleanup_expired_bookings_task():
    """
    Cleanup expired bookings (pending for > 15 minutes)
    Runs every 5 minutes
    """
    import asyncio
    from app.services.bookings import cleanup_expired_bookings
    
    async def run():
        async with AsyncSessionLocal() as db:
            count = await cleanup_expired_bookings(db)
            return count
    
    count = asyncio.run(run())
    return f"Cleaned up {count} expired bookings"
