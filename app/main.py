from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import asyncio

from sqlalchemy import select
from geoalchemy2.elements import WKTElement
from app.config import settings
from app.database import get_db
from app.services.ai_engine import quick_intent_detection, classify_intent, Intent
from app.services.whatsapp import whatsapp_service
from app.webhooks.message_handler import handle_intent
from app.models import User, Conversation, MessageLog, Event
from app.services.user_registration import UserRegistrationFlow, get_or_create_user
from app.services.location import get_events_near_location
from app.services.locks import inbound_phone_lock
from app.services.menu import send_main_menu

app = FastAPI(title="Grooovy WhatsApp Bot")


async def create_mock_event_and_notify(phone: str, delay_seconds: int, lat: float, lng: float, db: AsyncSession):
    """
    Wait for specified seconds, then create a mock event at user's location and notify them.
    Used for testing the booking flow.
    """
    try:
        # Wait for the specified delay
        await asyncio.sleep(delay_seconds)
        
        # Create new session for this async task
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as AsyncSessionNew
        from sqlalchemy.orm import sessionmaker
        
        engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSessionNew, expire_on_delete=False)
        
        async with AsyncSessionLocal() as task_db:
            event = Event(
                title="🎉 Stefan's Exclusive Flash Event - JUST FOR YOU!",
                description="This event was created right where you are! Limited time only. Book now to secure your spot!",
                category="party",
                event_date=datetime.now() + timedelta(hours=2),
                location_lat=lat,
                location_lng=lng,
                full_address="Your Location",
                venue_name="Secret Venue",
                capacity=50,
                ticket_price=5000,
                currency="NGN",
                status="active",
                created_via="whatsapp"
            )
            
            task_db.add(event)
            await task_db.commit()
            await task_db.refresh(event)
            
            # Send notification about the new event
            notification_message = (
                f"🎉 BOOM! 🎉\n\n"
                f"An AMAZING event just appeared right at your location!\n\n"
                f"📌 {event.title}\n"
                f"🕐 In 2 hours\n"
                f"📍 Right where you are\n\n"
                f"Type 'Book it' or 'Discover events' to check it out and grab your ticket! ⚡"
            )
            
            await whatsapp_service.send_message(phone, notification_message)
            
            # Also send quick action button
            await whatsapp_service.send_interactive(
                phone,
                "Ready to book?",
                buttons=[
                    {"id": f"action:discover", "title": "View Events Near Me"},
                    {"id": f"action:my_tickets", "title": "My Tickets"}
                ]
            )
    
    except Exception as e:
        print(f"ERROR in create_mock_event_and_notify: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            await whatsapp_service.send_message(
                phone,
                "❌ Something went wrong preparing your surprise event. Try searching for events manually!"
            )
        except:
            pass


@app.get("/")
async def root():
    return {"status": "ok", "service": "Grooovy WhatsApp Bot"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/webhooks/whatsapp")
async def verify_webhook(request: Request):
    """Webhook verification (Meta's challenge-response)"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/whatsapp")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Receive incoming WhatsApp messages"""
    body = await request.json()
    # Avoid logging full webhook payloads to reduce risk of leaking user content.
    
    # Validate signature (important for security)
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_whatsapp_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Process webhook
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Handle incoming message
                if "messages" in value:
                    metadata = value.get("metadata", {})
                    contacts = value.get("contacts", [])
                    contact_map = {}
                    for contact in contacts:
                        wa_id = contact.get("wa_id")
                        name = contact.get("profile", {}).get("name")
                        if wa_id and name:
                            contact_map[wa_id] = name
                    for message in value["messages"]:
                        try:
                            meta = dict(metadata) if metadata else {}
                            contact_name = contact_map.get(message.get("from"))
                            if contact_name:
                                meta["contact_name"] = contact_name
                            await process_incoming_message(message, meta, db)
                        except Exception as e:
                            # Log error but don't fail the webhook
                            import logging
                            logging.error(f"Error processing message: {e}", exc_info=True)
                            # Try to rollback any failed transaction
                            await db.rollback()
    
    return {"status": "ok"}


@app.post("/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Paystack payment webhooks"""
    import hmac
    import hashlib
    
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    # Verify signature — Paystack signs with PAYSTACK_SECRET_KEY using SHA-512
    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse event
    event_data = await request.json()
    event_type = event_data.get("event")
    
    if event_type == "charge.success":
        # Payment successful
        from app.services.bookings import confirm_payment
        
        reference = event_data["data"]["reference"]
        
        try:
            result = await confirm_payment(reference, db)
            if result['success']:
                return {"status": "success", "message": "Payment confirmed"}
        except Exception as e:
            print(f"Payment confirmation error: {e}")
            return {"status": "error", "message": str(e)}
    
    return {"status": "ok"}


def verify_whatsapp_signature(payload: dict, signature: str) -> bool:
    """Verify Meta's webhook signature using the App Secret"""
    if settings.APP_ENV == "development":
        return True  # Skip verification in dev

    if not signature or not signature.startswith("sha256="):
        return False

    # Meta signs with the App Secret, NOT the access token
    app_secret = getattr(settings, 'WHATSAPP_APP_SECRET', None) or settings.WHATSAPP_ACCESS_TOKEN
    expected_signature = hmac.new(
        app_secret.encode(),
        json.dumps(payload, separators=(',', ':')).encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature[7:], expected_signature)


def _split_profile_name(name: str) -> tuple[str | None, str | None]:
    if not name:
        return None, None
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return None, None
    parts = cleaned.split(" ")
    first = parts[0]
    last = " ".join(parts[1:]) if len(parts) > 1 else None
    return first, last


async def _apply_contact_name(
    phone: str,
    contact_name: str,
    db: AsyncSession
) -> None:
    if not contact_name:
        return
    user = await get_or_create_user(phone, db, auto_create=True)
    updated = False
    if user and not user.whatsapp_name:
        user.whatsapp_name = contact_name
        updated = True
    if updated:
        await db.commit()


async def process_incoming_message(
    message: dict,
    metadata: dict,
    db: AsyncSession
):
    """Main message processing logic (serialized per phone)"""
    phone = message["from"]
    async with inbound_phone_lock(phone):
        await _process_incoming_message_locked(message, metadata, db)


async def _process_incoming_message_locked(
    message: dict,
    metadata: dict,
    db: AsyncSession
):
    """Main message processing logic"""
    phone = message["from"]
    message_id = message["id"]
    message_type = message["type"]

    # De-duplicate inbound deliveries (Meta can retry the same message)
    if message_id:
        result = await db.execute(
            select(MessageLog).where(
                MessageLog.whatsapp_message_id == message_id,
                MessageLog.direction == "inbound"
            )
        )
        if result.scalar_one_or_none():
            return

    contact_name = (metadata or {}).get("contact_name")
    if contact_name:
        await _apply_contact_name(phone, contact_name, db)
    
    # Extract message content
    if message_type == "text":
        user_message = message["text"]["body"]
    elif message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = interactive.get("type")
        if interactive_type == "button_reply":
            user_message = interactive["button_reply"]["id"]
        elif interactive_type == "list_reply":
            user_message = interactive["list_reply"]["id"]
        else:
            user_message = ""
    elif message_type == "location":
        # User shared their location
        lat = message["location"]["latitude"]
        lng = message["location"]["longitude"]
        
        # Save user's location preference
        
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(phone=phone)
            db.add(user)
        
        # Save location as PostGIS point
        user.location_preference = WKTElement(f'POINT({lng} {lat})', srid=4326)
        await db.commit()
        
        if settings.ENABLE_MOCK_EVENTS:
            # TRIGGER MOCK EVENTS FOR TESTING (Triggers on every location share)
            from app.services.test_utils import create_mock_event_near_user
            print(f"DEBUG: Starting mock event timers for {phone} (1m, 5m, 15m)")
            asyncio.create_task(create_mock_event_near_user(phone, 1, lat, lng))
            asyncio.create_task(create_mock_event_near_user(phone, 5, lat, lng))
            asyncio.create_task(create_mock_event_near_user(phone, 15, lat, lng))
        
        # Check if user is in registration flow
        from app.services.user_registration import UserRegistrationFlow
        
        result = await db.execute(
            select(Conversation).where(Conversation.phone == phone)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation and conversation.current_flow == 'user_registration' and conversation.flow_state.get('step') == 'location':
            # Complete registration first
            await UserRegistrationFlow.complete_registration(phone, db, conversation)
            
            # Confirm location saved
            await whatsapp_service.send_message(
                phone,
                "📍 Location saved!"
            )
            
            # Schedule mock event creation after 5 minutes (silently for testing)
            # Don't tell user about this - it's for internal testing
            asyncio.create_task(
                create_mock_event_and_notify(phone, 300, lat, lng, db)  # 300 seconds = 5 minutes
            )
            
            # Show main menu without mentioning the mock event
            await send_main_menu(phone, db)
            return
        
        # Location saved - Let's immediately surface events!
        await whatsapp_service.send_message(
            phone,
            "📍 Location captured! Checking for events near you..."
        )
        
        # Route directly to the discovery flow
        await handle_intent(
            Intent.DISCOVER_EVENTS, 
            {"raw_message": "location shared", "lat": lat, "lng": lng}, 
            phone, 
            db
        )
        
        # Update conversation timestamp
        conversation.last_message_at = datetime.now()
        await db.commit()
        return
    else:
        await whatsapp_service.send_message(
            phone,
            "I can only process text messages and locations right now.\n\n"
            "Share your location to find events near you."
        )
        return
    
    # Log message
    message_log = MessageLog(
        phone=phone,
        direction="inbound",
        message_type=message_type,
        content=user_message,
        whatsapp_message_id=message_id
    )
    db.add(message_log)
    await db.commit()
    
    # Mark as read
    try:
        await whatsapp_service.mark_as_read(message_id)
    except:
        pass  # Non-critical
    
    # Get or create conversation context
    result = await db.execute(
        select(Conversation).where(Conversation.phone == phone)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(phone=phone, flow_state={})
        db.add(conversation)
        await db.commit()
    
    # Check if user is registered BEFORE processing any intent
    from app.services.user_registration import check_user_registration_status, UserRegistrationFlow
    registration_status = await check_user_registration_status(phone, db)
    
    # If user is NOT registered OR profile is incomplete, route to registration flow
    if not registration_status['registered'] or not registration_status['profile_complete']:
        # Check if already in registration flow
        if conversation.current_flow == 'user_registration':
            # Continue registration
            await UserRegistrationFlow.process_step(phone, user_message, db)
        else:
            # Start registration flow
            await UserRegistrationFlow.start_flow(phone, db)
        
        conversation.last_message_at = datetime.now()
        await db.commit()
        return
    
    # User is registered - proceed with normal intent processing
    
    # Shortcut for interactive action IDs (skip LLM)
    if user_message.startswith((
        "action:",
        "event:",
        "pay_",
        "gift_qty:",
        "gift_skip",
        "share_ticket:",
        "refund:",
        "refund_confirm:",
        "refund_cancel:",
        "org_event:",
        "org_action:",
        "gift_history:"
    )):
        try:
            await handle_intent(Intent.GENERAL_QUERY, {"raw_message": user_message}, phone, db)
            conversation.last_message_at = datetime.now()
            await db.commit()
            return
        except Exception:
            await db.rollback()
            raise
    
    # Quick intent detection (rule-based fast path)
    quick_intent = quick_intent_detection(user_message)
    
    try:
        if quick_intent:
            # Fast path - no LLM needed
            await handle_intent(quick_intent, {"raw_message": user_message}, phone, db)
        else:
            # LLM path - classify intent
            ai_response = await classify_intent(
                user_message,
                conversation.flow_state or {}
            )
            
            # Update message log with intent (convert entities to JSON-safe dict)
            message_log.intent_detected = ai_response.intent
            # Ensure all values are JSON serializable
            entities_dict = ai_response.entities.dict()
            # Convert any non-serializable types
            for key, value in entities_dict.items():
                if value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                    entities_dict[key] = str(value)
            message_log.entities = entities_dict
            await db.commit()
            
            # Ensure raw_message and ai_message are set for handlers
            entities_for_handler = ai_response.entities.dict()
            entities_for_handler['raw_message'] = user_message
            entities_for_handler['ai_message'] = ai_response.user_message
            
            # Handle based on intent
            await handle_intent(
                ai_response.intent,
                entities_for_handler,
                phone,
                db
            )
        
        # Update conversation timestamp
        conversation.last_message_at = datetime.now()
        await db.commit()
    except Exception as e:
        # Rollback on any error
        await db.rollback()
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



