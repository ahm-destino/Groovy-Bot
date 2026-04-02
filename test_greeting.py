#!/usr/bin/env python3
import asyncio
import sys
from app.services.ai_engine import quick_intent_detection, Intent

def test_greetings():
    test_messages = [
        "idan mi",
        "idan",
        "hi",
        "hello",
        "bawo ni",
        "how are you",
        "how dey",
        "pele",
        "bawo",
        "hi there",
    ]

    print("Testing quick_intent_detection():")
    print("-" * 60)
    for msg in test_messages:
        result = quick_intent_detection(msg)
        status = "✓" if result == Intent.GREETING else "✗"
        print(f"{status} '{msg}' -> {result}")
    print("-" * 60)

if __name__ == "__main__":
    test_greetings()
