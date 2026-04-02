#!/usr/bin/env python3
"""Debug script to trace registration check logic"""
import asyncio
import os
import sys

# Set up path
sys.path.insert(0, '/app')
os.chdir('/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.user_registration import check_user_registration_status
from app.services.ai_engine import quick_intent_detection, Intent

async def test_registration_check():
    """Test if registration check works correctly"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_delete=False
    )
    
    async with async_session() as db:
        # Test with a phone number that doesn't exist
        test_phone = "+234901234567"
        
        status = await check_user_registration_status(test_phone, db)
        
        print("🔍 Test: Unregistered user check")
        print(f"Phone: {test_phone}")
        print(f"Status: {status}")
        print()
        print("Expected: registered=False, profile_complete=False")
        print(f"Actual: registered={status['registered']}, profile_complete={status['profile_complete']}")
        
        if not status['registered'] or not status['profile_complete']:
            print("✅ Registration check correctly identified unregistered user")
        else:
            print("❌ ERROR: Registration check thinks user is registered!")
        
        print("\n" + "="*60 + "\n")
        
        # Test greeting detection
        print("🔍 Test: Greeting intent detection")
        test_messages = [
            "idan mi",
            "idan",
            "hi",
            "hello",
            "bawo ni",
            "how are you",
            "what is this",
            "book concert"
        ]
        
        for msg in test_messages:
            intent = quick_intent_detection(msg)
            is_greeting = intent == Intent.GREETING
            status_mark = "✅" if is_greeting else "❌"
            print(f"{status_mark} '{msg}' -> {intent}")

if __name__ == "__main__":
    asyncio.run(test_registration_check())
