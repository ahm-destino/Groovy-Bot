"""
Tests for booking system
"""
import pytest
from decimal import Decimal
from app.services.bookings import (
    create_booking,
    cancel_booking,
    cleanup_expired_bookings
)
from app.models import Booking, Event


@pytest.mark.asyncio
async def test_create_booking_success(db_session, test_user, test_event):
    """Test successful booking creation"""
    booking = await create_booking(
        user_id=str(test_user.id),
        event_id=str(test_event.id),
        phone=test_user.phone,
        quantity=2,
        db=db_session
    )
    
    assert booking is not None
    assert booking.user_id == test_user.id
    assert booking.event_id == test_event.id
    assert booking.quantity == 2
    assert booking.total_amount == test_event.ticket_price * 2
    assert booking.status == 'pending'
    assert booking.booking_source == 'whatsapp'


@pytest.mark.asyncio
async def test_create_booking_insufficient_capacity(db_session, test_user, test_event):
    """Test booking with insufficient capacity"""
    # Try to book more than available
    with pytest.raises(ValueError, match="Only .* tickets available"):
        await create_booking(
            user_id=str(test_user.id),
            event_id=str(test_event.id),
            phone=test_user.phone,
            quantity=test_event.capacity + 10,
            db=db_session
        )


@pytest.mark.asyncio
async def test_booking_reserves_tickets(db_session, test_user, test_event):
    """Test that booking reserves tickets"""
    initial_sold = test_event.tickets_sold
    quantity = 3
    
    booking = await create_booking(
        user_id=str(test_user.id),
        event_id=str(test_event.id),
        phone=test_user.phone,
        quantity=quantity,
        db=db_session
    )
    
    await db_session.refresh(test_event)
    assert test_event.tickets_sold == initial_sold + quantity


@pytest.mark.asyncio
async def test_cancel_booking_success(db_session, test_user, test_event):
    """Test successful booking cancellation"""
    # Create and confirm booking
    booking = await create_booking(
        user_id=str(test_user.id),
        event_id=str(test_event.id),
        phone=test_user.phone,
        quantity=2,
        db=db_session
    )
    
    booking.status = 'confirmed'
    booking.payment_reference = 'TEST_REF_123'
    await db_session.commit()
    
    # Cancel booking
    result = await cancel_booking(
        booking_id=str(booking.id),
        reason="Test cancellation",
        db=db_session
    )
    
    assert result['success'] == True
    await db_session.refresh(booking)
    assert booking.status == 'cancelled'


@pytest.mark.asyncio
async def test_cancel_booking_not_confirmed(db_session, test_user, test_event):
    """Test cancelling non-confirmed booking"""
    booking = await create_booking(
        user_id=str(test_user.id),
        event_id=str(test_event.id),
        phone=test_user.phone,
        quantity=2,
        db=db_session
    )
    
    result = await cancel_booking(
        booking_id=str(booking.id),
        reason="Test cancellation",
        db=db_session
    )
    
    assert result['success'] == False
    assert 'Only confirmed bookings' in result['message']


@pytest.mark.asyncio
async def test_booking_total_calculation(db_session, test_user, test_event):
    """Test booking total amount calculation"""
    quantity = 5
    booking = await create_booking(
        user_id=str(test_user.id),
        event_id=str(test_event.id),
        phone=test_user.phone,
        quantity=quantity,
        db=db_session
    )
    
    expected_total = test_event.ticket_price * quantity
    assert booking.total_amount == expected_total


print("✅ Booking Tests Ready")
