"""
Check-in service for ticket validation at venue
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models import Ticket, Event, Booking, User


async def check_in_ticket(
    ticket_code: str,
    db: AsyncSession,
    entry_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check in a ticket at venue
    
    Args:
        ticket_code: Ticket code (e.g., GRV-ABC123)
        db: Database session
        entry_code: Optional entry code for anonymous events
    
    Returns:
        {
            'success': bool,
            'message': str,
            'ticket': Ticket (if successful),
            'event': Event (if successful)
        }
    """
    # Get ticket
    result = await db.execute(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return {
            'success': False,
            'message': 'Invalid ticket code',
            'ticket': None,
            'event': None
        }
    
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == ticket.event_id)
    )
    event = result.scalar_one()
    
    # Check ticket status
    if ticket.status != 'valid':
        return {
            'success': False,
            'message': f'Ticket is {ticket.status}',
            'ticket': ticket,
            'event': event
        }
    
    # Check if already checked in
    if ticket.checked_in_at:
        return {
            'success': False,
            'message': f'Already checked in at {ticket.checked_in_at.strftime("%I:%M %p")}',
            'ticket': ticket,
            'event': event
        }
    
    # Verify entry code for anonymous events
    if event.is_anonymous and event.entry_code_format == 'unique':
        if not entry_code or entry_code != ticket.entry_code:
            return {
                'success': False,
                'message': 'Invalid entry code',
                'ticket': ticket,
                'event': event
            }
    elif event.is_anonymous and event.entry_code_format == 'shared':
        if not entry_code or entry_code != event.secret_code:
            return {
                'success': False,
                'message': 'Invalid entry code',
                'ticket': ticket,
                'event': event
            }
    
    # Check in ticket
    ticket.checked_in_at = datetime.now()
    await db.commit()
    
    # Get user info
    result = await db.execute(
        select(User).where(User.id == ticket.user_id)
    )
    user = result.scalar_one_or_none()
    
    return {
        'success': True,
        'message': 'Check-in successful',
        'ticket': ticket,
        'event': event,
        'user': user
    }


async def validate_ticket(
    ticket_code: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Validate ticket without checking in
    
    Args:
        ticket_code: Ticket code
        db: Database session
    
    Returns:
        Ticket validation info
    """
    # Get ticket
    result = await db.execute(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return {
            'valid': False,
            'message': 'Invalid ticket code'
        }
    
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == ticket.event_id)
    )
    event = result.scalar_one()
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == ticket.user_id)
    )
    user = result.scalar_one_or_none()
    
    # Get booking
    result = await db.execute(
        select(Booking).where(Booking.id == ticket.booking_id)
    )
    booking = result.scalar_one_or_none()
    
    return {
        'valid': ticket.status == 'valid',
        'status': ticket.status,
        'checked_in': ticket.checked_in_at is not None,
        'checked_in_at': ticket.checked_in_at.isoformat() if ticket.checked_in_at else None,
        'event': {
            'title': event.title,
            'date': event.event_date.isoformat(),
            'venue': event.venue_name
        },
        'holder': {
            'name': f"{user.first_name or ''} {user.last_name or ''}".strip() if user else 'Guest',
            'phone': booking.phone if booking else 'N/A'
        },
        'requires_entry_code': event.is_anonymous
    }


async def get_checkin_stats(
    event_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Get check-in statistics for an event
    
    Args:
        event_id: Event UUID
        db: Database session
    
    Returns:
        Check-in statistics
    """
    # Get all tickets
    result = await db.execute(
        select(Ticket).where(Ticket.event_id == event_id)
    )
    tickets = result.scalars().all()
    
    total_tickets = len(tickets)
    checked_in = len([t for t in tickets if t.checked_in_at])
    valid_tickets = len([t for t in tickets if t.status == 'valid'])
    
    return {
        'total_tickets': total_tickets,
        'checked_in': checked_in,
        'not_checked_in': total_tickets - checked_in,
        'valid_tickets': valid_tickets,
        'checkin_rate': round(checked_in / total_tickets * 100, 1) if total_tickets > 0 else 0
    }
