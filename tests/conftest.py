"""
Pytest configuration and fixtures for testing
"""
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base
from app.config import settings


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_grooovy"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Create database session for each test"""
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "phone": "+2348012345678",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com"
    }


@pytest.fixture
def sample_event_data():
    """Sample event data for testing"""
    from datetime import datetime, timedelta
    
    return {
        "title": "Test Concert",
        "description": "A test concert event",
        "event_date": datetime.now() + timedelta(days=30),
        "venue_name": "Test Venue",
        "full_address": "123 Test Street, Lagos",
        "latitude": 6.5244,
        "longitude": 3.3792,
        "category": "concert",
        "ticket_price": 10000,
        "capacity": 100,
        "status": "active"
    }


@pytest_asyncio.fixture
async def test_user(db_session, sample_user_data):
    """Create a test user"""
    from app.models import User
    
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_event(db_session, test_user, sample_event_data):
    """Create a test event"""
    from app.models import Event
    
    event = Event(
        host_id=test_user.id,
        **sample_event_data
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)
    
    return event
