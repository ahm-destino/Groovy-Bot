"""
User registration service for WhatsApp bot
Collects user details and stores in database for use across bot and webapp
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from datetime import datetime
import re

from app.models import User, Conversation
from app.services.whatsapp import whatsapp_service
from app.services.menu import send_main_menu, send_back_to_menu


def _split_profile_name(name: str) -> tuple[Optional[str], Optional[str]]:
    if not name:
        return None, None
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return None, None
    parts = cleaned.split(" ")
    first = parts[0]
    last = " ".join(parts[1:]) if len(parts) > 1 else None
    return first, last


class UserRegistrationFlow:
    """Multi-turn flow for user registration"""

    @staticmethod
    async def start_flow(phone: str, db: AsyncSession):
        """Start registration flow for new user"""
        # Check if user already exists and is complete
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()

        if user and user.first_name and user.last_name:
            await whatsapp_service.send_message(
                phone,
                f"Welcome back, {user.first_name}! I'm Stefan, your Grooovy AI assistant. What would you like to do?"
            )
            await send_main_menu(phone, db)
            return
        
        # Get or create conversation state
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(phone=phone, flow_state={})
            db.add(conversation)

        # ALWAYS reset to greeting step (force fresh start)
        conversation.current_flow = 'user_registration'
        conversation.flow_state = {
            'step': 'greeting',
            'phone': phone
        }
        await db.commit()

        intro_message = (
            "🎉 Hi! I'm Stefan, your AI assistant.\n\n"
            "I'm here to help you discover and book amazing events on Grooovy.\n\n"
            "To get started, I need a bit of information about you. "
            "It's just 4 quick steps to personalize your experience.\n\n"
            "Ready to begin?"
        )
        
        await whatsapp_service.send_interactive(
            phone,
            intro_message,
            buttons=[
                {"id": "action:start_registration", "title": "Proceed to Registration"}
            ]
        )

    @staticmethod
    async def process_step(phone: str, message: str, db: AsyncSession):
        """Process registration flow step"""
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()

        if not conversation or not conversation.flow_state:
            await whatsapp_service.send_message(
                phone,
                "Session expired. Type Hi or Menu to start again."
            )
            return

        step = conversation.flow_state.get('step')

        if step == 'greeting':
            # User clicked "Proceed to Registration" button
            # Move to first step
            conversation.flow_state['step'] = 'first_name'
            flag_modified(conversation, 'flow_state')
            await db.commit()
            
            first_step_message = (
                "Great! Let's begin.\n\n"
                "Step 1 of 4: What is your first name?"
            )
            await whatsapp_service.send_message(phone, first_step_message)
        elif step == 'first_name':
            await UserRegistrationFlow._handle_first_name(
                phone, message, conversation, db
            )
        elif step == 'last_name':
            await UserRegistrationFlow._handle_last_name(
                phone, message, conversation, db
            )
        elif step == 'email':
            await UserRegistrationFlow._handle_email(
                phone, message, conversation, db
            )
        elif step == 'location':
            await UserRegistrationFlow._handle_location(
                phone, message, conversation, db
            )

    @staticmethod
    async def _handle_first_name(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle first name input"""
        first_name = message.strip()

        # Reject keywords and commands (exact match only to avoid false positives with names like James or Michelle)
        blocked_keywords = {'near', 'me', 'hi', 'hello', 'menu', 'help', 'back', 'cancel', 'discover', 'search', 'book', 'ticket', 'my'}
        if first_name.lower() in blocked_keywords:
            await whatsapp_service.send_message(
                phone,
                "❌ That looks like a command, not a name. Please enter your actual first name."
            )
            return

        # Validate name
        if len(first_name) < 2:
            await whatsapp_service.send_message(
                phone,
                "❌ Invalid. First name must be 2+ characters. Try again."
            )
            return

        if not re.search(r'[a-zA-Z]', first_name):
            await whatsapp_service.send_message(
                phone,
                "❌ Invalid. Include at least one letter. Try again."
            )
            return

        # Save and move to next step
        conversation.flow_state['first_name'] = first_name
        conversation.flow_state['step'] = 'last_name'
        flag_modified(conversation, 'flow_state')
        await db.commit()

        message = (
            f"✅ Got it, {first_name}.\n\n"
            "Step 2 of 4: What is your last name?"
        )
        await whatsapp_service.send_message(phone, message)

    @staticmethod
    async def _handle_last_name(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle last name input"""
        last_name = message.strip()

        # Reject keywords and commands (exact match only)
        blocked_keywords = {'near', 'me', 'hi', 'hello', 'menu', 'help', 'back', 'cancel', 'discover', 'search', 'book', 'ticket', 'my'}
        if last_name.lower() in blocked_keywords:
            await whatsapp_service.send_message(
                phone,
                "❌ That looks like a command, not a name. Please enter your actual last name."
            )
            return

        # Validate name
        if len(last_name) < 2:
            await whatsapp_service.send_message(
                phone,
                "❌ Invalid. Last name must be 2+ characters. Try again."
            )
            return

        if not re.search(r'[a-zA-Z]', last_name):
            await whatsapp_service.send_message(
                phone,
                "❌ Invalid. Include at least one letter. Try again."
            )
            return

        # Save and move to email
        conversation.flow_state['last_name'] = last_name
        conversation.flow_state['step'] = 'email'
        flag_modified(conversation, 'flow_state')
        await db.commit()

        message = (
            f"✅ Got it, {last_name}.\n\n"
            "Step 3 of 4: What is your email address?\n"
            "(Required for receipts and updates)"
        )
        await whatsapp_service.send_message(phone, message)

    @staticmethod
    async def _handle_email(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Handle email input"""
        email_input = message.strip().lower()

        # Email is now required
        # Validate email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_input):
            await whatsapp_service.send_message(
                phone,
                "❌ Invalid email format. Please send a valid email address."
            )
            return

        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == email_input)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            await whatsapp_service.send_message(
                phone,
                "❌ That email is already registered. Please send a different one."
            )
            return

        email = email_input

        # Save email and move to location
        conversation.flow_state['email'] = email
        conversation.flow_state['step'] = 'location'
        flag_modified(conversation, 'flow_state')
        await db.commit()

        message = (
            f"✅ Got it, {email_input}.\n\n"
            "Step 4 of 4 (Final): Please share your current location.\n\n"
            "How to share:\n"
            "1. Tap + or the attachment icon\n"
            "2. Choose Location\n"
            "3. Send your current location"
        )
        await whatsapp_service.send_message(phone, message)

    @staticmethod
    async def _handle_location(
        phone: str,
        message: str,
        conversation: Conversation,
        db: AsyncSession
    ):
        """Finalize registration after location (if skipped)"""
        # Location is now required
        # You may want to add actual location validation here if available
        if not message or message.strip().lower() in ['skip', 'later', 'no']:
            await whatsapp_service.send_message(
                phone,
                "❌ Location is required. Please share your current location.\n\nTap + or attachment icon > Location > Send current location."
            )
            return
        # Save location (for now, just store the message; in production, parse/validate coordinates)
        conversation.flow_state['location'] = message.strip()
        flag_modified(conversation, 'flow_state')
        await db.commit()
        await UserRegistrationFlow.complete_registration(phone, db, conversation)

    @staticmethod
    async def complete_registration(phone: str, db: AsyncSession, conversation: Conversation):
        """Create or update user account and finish flow"""
        import asyncio
        from app.services.test_utils import create_mock_event_near_user
        
        first_name = conversation.flow_state.get('first_name')
        last_name = conversation.flow_state.get('last_name')
        email = conversation.flow_state.get('email')
        location = conversation.flow_state.get('location')

        # Get existing user or create new
        user = await get_or_create_user(phone, db, auto_create=True)

        # Update details
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.whatsapp_name = f"{first_name} {last_name}"

        # Clear registration flow
        conversation.current_flow = None
        conversation.flow_state = {}
        flag_modified(conversation, 'flow_state')

        await db.commit()
        await db.refresh(user)

        message = (
            f"✅ All set, {first_name}!\n\n"
            "I'm Stefan, your Grooovy AI assistant. I'm here to help you discover and book amazing events.\n\n"
            "Here's what you can do with me:\n"
            "• Discover events near you\n"
            "• Book tickets\n"
            "• View your tickets\n"
            "• Get personalized recommendations\n"
            "• Create your own events\n\n"
            "Pick an option below to get started! 🚀"
        )

        await whatsapp_service.send_message(phone, message)
        await send_main_menu(phone, db)
        print(f"New user registered: {first_name} {last_name} ({phone})")
        
        # Create mock events after registration (5 minutes delay)
        # Run in background - create simple events near user's location
        if location:
            try:
                # Extract coordinates from location (format: "latitude,longitude" or similar)
                # For testing, use Lagos coordinates
                lat, lng = 6.613739, 3.355257  # Default Lagos area
                
                # Create 5 mock events
                asyncio.create_task(create_mock_event_near_user(phone, 1, lat, lng))
                asyncio.create_task(create_mock_event_near_user(phone, 3, lat, lng))
                asyncio.create_task(create_mock_event_near_user(phone, 5, lat, lng))
                asyncio.create_task(create_mock_event_near_user(phone, 7, lat, lng))
                asyncio.create_task(create_mock_event_near_user(phone, 10, lat, lng))
                
                print(f"Mock events queued for creation: {phone}")
            except Exception as e:
                print(f"Failed to create mock events: {e}")


async def get_or_create_user(
    phone: str,
    db: AsyncSession,
    auto_create: bool = False
) -> Optional[User]:
    """
    Get existing user or optionally create a basic account

    Args:
        phone: User phone number
        db: Database session
        auto_create: Create basic account if user doesn't exist

    Returns:
        User object or None
    """
    # Try to get existing user
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    if auto_create:
        # Create basic user account
        user = User(phone=phone)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    return None


async def update_user_profile(
    phone: str,
    db: AsyncSession,
    **updates
) -> User:
    """
    Update user profile fields

    Args:
        phone: User phone number
        db: Database session
        **updates: Fields to update (first_name, last_name, email, etc.)

    Returns:
        Updated User object
    """
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one()

    # Update allowed fields
    allowed_fields = [
        'first_name', 'last_name', 'email',
        'whatsapp_name', 'preferred_categories', 'language'
    ]

    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    return user


async def check_user_registration_status(
    phone: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Check if user is registered and profile completeness

    Returns:
        {
            'registered': bool,
            'has_name': bool,
            'has_email': bool,
            'profile_complete': bool,
            'user': User or None
        }
    """
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {
            'registered': False,
            'has_name': False,
            'has_email': False,
            'profile_complete': False,
            'user': None
        }

    has_name = bool(user.first_name and user.last_name)
    has_email = bool(user.email)
    profile_complete = has_name  # Email is optional

    return {
        'registered': True,
        'has_name': has_name,
        'has_email': has_email,
        'profile_complete': profile_complete,
        'user': user
    }
