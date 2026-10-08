"""
Flow Interceptor Service for Grooovy WhatsApp bot.

Prevents active step-by-step form flows (user registration, event creation,
gift tickets, event editing) from blindly swallowing side questions or conversational
turns as form field inputs.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.whatsapp import whatsapp_service
from app.services.ai_engine import classify_intent, quick_intent_detection, Intent

logger = logging.getLogger(__name__)

# Question starters and conversational markers
_QUESTION_STARTERS = (
    "what", "why", "how", "when", "where", "who", "which", "can i", "could i",
    "should i", "would i", "is it", "are you", "do you", "does it", "tell me",
    "explain", "help", "wetin", "abi", "how far", "who be", "wait", "hold on",
    "please explain", "what if", "how much"
)

_CONVERSATIONAL_PHRASES = {
    "who are you", "what is this", "how does this work", "can i edit later",
    "is this free", "how much is it", "why do you need this", "hold on",
    "wait a sec", "wait a minute", "give me a sec", "let me think",
    "what do you mean", "i don't understand", "idk", "not sure",
}

# Button actions or navigation commands that must NEVER be intercepted as questions
_NAVIGATION_COMMANDS = {
    "cancel", "restart", "reset", "menu", "main menu", "back", "home",
    "action:start_registration", "action:menu", "action:cancel_broadcast",
}


def should_intercept_flow(message: str, current_flow: str, flow_state: dict) -> bool:
    """
    Determine if a message during an active flow is a side-question or chat turn.
    Returns True if the message should be answered conversationally without
    advancing/corrupting the active flow step.
    """
    if not message:
        return False
    
    cleaned = message.strip()
    lowered = cleaned.lower()
    
    # 1. Never intercept explicit navigation or button actions
    if lowered in _NAVIGATION_COMMANDS or cleaned.startswith("action:"):
        return False
        
    step = flow_state.get("step") if isinstance(flow_state, dict) else None
    
    # 2. If the current step expects a numeric choice (e.g. category 1-8, location_type 1-3)
    # and the user sent a single digit, it's a form input, not a question.
    if step in ("category", "location_type", "reveal_timing", "entry_code_type") and cleaned.isdigit():
        return False

    # 3. Direct question signals
    if cleaned.endswith("?"):
        return True
        
    if any(lowered.startswith(starter + " ") or lowered == starter for starter in _QUESTION_STARTERS):
        return True
        
    if any(phrase in lowered for phrase in _CONVERSATIONAL_PHRASES):
        return True
        
    # 4. Fast-path intent check: if quick_intent_detection spots a greeting/help/navigation
    fast_intent = quick_intent_detection(cleaned)
    if fast_intent in (Intent.GREETING, Intent.HELP):
        return True
        
    return False


def get_step_reminder(current_flow: str, flow_state: dict) -> str:
    """Return a short, natural prompt reminding the user of their current form step."""
    step = flow_state.get("step") if isinstance(flow_state, dict) else ""
    
    if current_flow == "user_registration":
        reminders = {
            "greeting": "Whenever you're ready, tap Proceed or reply 'Ok' to begin registration.",
            "first_name": "Whenever you're ready, what is your first name?",
            "last_name": "Whenever you're ready, what is your last name?",
            "email": "Whenever you're ready, what is your email address?",
            "location": "Whenever you're ready, what city or area are you in?",
        }
        return reminders.get(step, "Whenever you're ready, let's continue registration.")

    if current_flow == "event_creation":
        reminders = {
            "title": "Whenever you're ready, what is the title of your event?",
            "category": "Whenever you're ready, reply with a category number (1-8).",
            "date": "Whenever you're ready, what date and time is your event? (e.g. 20/02/2026 at 7:00 PM)",
            "location_type": "Whenever you're ready, pick location visibility (1-3).",
            "address": "Whenever you're ready, what is the event venue address?",
            "capacity": "Whenever you're ready, how many total tickets/capacity for this event?",
            "price": "Whenever you're ready, how much is the ticket price (or 0 for free)?",
            "description": "Whenever you're ready, send a short description for your event.",
        }
        return reminders.get(step, "Whenever you're ready, let me know to continue setting up your event.")

    if current_flow == "gift_ticket":
        return "Whenever you're ready, let's continue with sending your ticket gift."

    if current_flow == "event_editing":
        return "Whenever you're ready, let me know how you'd like to update your event."

    return "Whenever you're ready, let's pick up where we left off!"


async def handle_flow_intercept(
    phone: str,
    user_message: str,
    current_flow: str,
    flow_state: dict,
    db: AsyncSession
) -> None:
    """
    Handle a conversational side-question while maintaining the active flow.
    Answers the user's question via AI and appends a step reminder.
    """
    logger.info("Flow interceptor triggered during %s (step=%s) for message: '%s'",
                current_flow, flow_state.get('step'), user_message)

    # Ask AI engine to answer the user's question
    ai_response = await classify_intent(user_message)
    reply_text = ai_response.user_message

    # Get reminder for active step
    reminder = get_step_reminder(current_flow, flow_state)

    combined_response = f"{reply_text}\n\n💡 *Note:* {reminder}"
    await whatsapp_service.send_message(phone, combined_response)
