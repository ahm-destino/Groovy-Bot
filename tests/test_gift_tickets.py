"""
Tests for gift tickets feature
"""
import pytest
from app.services.gift_tickets import (
    create_gift_booking,
    get_gift_history,
    format_gift_summary
)
from app.models import Booking


@pytest.mark.asyncio
async def test_create_gift_booking(db_session, test_user, test_event):
    """Test creating a gift booking"""
    recipient_phone = "+2348099999999"
    gift_message = "Happy Birthday!"
    
    booking = await create_gift_booking(
        sender_id=str(test_user.id),
        event_id=str(test_event.id),
        recipient_phone=recipient_phone,
        quantity=2,
        gift_message=gift_message,
        sender_phone=test_user.phone,
        db=db_session
    )
    
    assert booking is not None
    assert booking.is_gift == True
    assert booking.gift_sender_id == test_user.id
    assert booking.gift_recipient_phone == recipient_phone
    assert booking.gift_message == gift_message
    assert booking.gift_redeemed == False


@pytest.mark.asyncio
async def test_gift_booking_phone_normalization(db_session, test_user, test_event):
    """Test phone number normalization for gifts"""
    # Test with 0 prefix
    recipient_phone = "08099999999"
    
    booking = await create_gift_booking(
        sender_id=str(test_user.id),
        event_id=str(test_event.id),
        recipient_phone=recipient_phone,
        quantity=1,
        gift_message="Test",
        sender_phone=test_user.phone,
        db=db_session
    )
    
    # Should be normalized to +234
    assert booking.gift_recipient_phone.startswith('+234')


@pytest.mark.asyncio
async def test_get_gift_history_sent(db_session, test_user, test_event):
    """Test getting sent gift history"""
    # Create a gift booking
    booking = await create_gift_booking(
        sender_id=str(test_user.id),
        event_id=str(test_event.id),
        recipient_phone="+2348099999999",
        quantity=2,
        gift_message="Test gift",
        sender_phone=test_user.phone,
        db=db_session
    )
    
    booking.status = 'confirmed'
    await db_session.commit()
    
    # Get sent gifts
    gifts = await get_gift_history(str(test_user.id), db_session, sent=True)
    
    assert len(gifts) > 0
    assert gifts[0].is_gift == True
    assert gifts[0].gift_sender_id == test_user.id


@pytest.mark.asyncio
async def test_gift_booking_reserves_tickets(db_session, test_user, test_event):
    """Test that gift booking reserves tickets"""
    initial_sold = test_event.tickets_sold
    quantity = 3
    
    booking = await create_gift_booking(
        sender_id=str(test_user.id),
        event_id=str(test_event.id),
        recipient_phone="+2348099999999",
        quantity=quantity,
        gift_message="Test",
        sender_phone=test_user.phone,
        db=db_session
    )
    
    await db_session.refresh(test_event)
    assert test_event.tickets_sold == initial_sold + quantity


@pytest.mark.asyncio
async def test_gift_booking_insufficient_capacity(db_session, test_user, test_event):
    """Test gift booking with insufficient capacity"""
    with pytest.raises(ValueError, match="Only .* tickets available"):
        await create_gift_booking(
            sender_id=str(test_user.id),
            event_id=str(test_event.id),
            recipient_phone="+2348099999999",
            quantity=test_event.capacity + 10,
            gift_message="Test",
            sender_phone=test_user.phone,
            db=db_session
        )


print("✅ Gift Tickets Tests Ready")
