"""
Analytics service for platform-wide statistics
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from decimal import Decimal

from app.models import Event, Booking, Ticket, User


async def get_platform_analytics(
    db: AsyncSession,
    period: str = '30d'
) -> Dict[str, Any]:
    """
    Get platform-wide analytics
    
    Args:
        db: Database session
        period: Time period ('7d', '30d', '90d', 'all')
    
    Returns:
        Dictionary with analytics data
    """
    # Calculate date range
    if period == '7d':
        start_date = datetime.now() - timedelta(days=7)
    elif period == '30d':
        start_date = datetime.now() - timedelta(days=30)
    elif period == '90d':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime(2020, 1, 1)  # All time
    
    # Total events
    result = await db.execute(
        select(func.count(Event.id)).where(
            Event.created_at >= start_date
        )
    )
    total_events = result.scalar() or 0
    
    # Active events
    result = await db.execute(
        select(func.count(Event.id)).where(
            and_(
                Event.status == 'active',
                Event.event_date > datetime.now()
            )
        )
    )
    active_events = result.scalar() or 0
    
    # Total bookings
    result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.booked_at >= start_date,
                Booking.status == 'confirmed'
            )
        )
    )
    total_bookings = result.scalar() or 0
    
    # Total revenue
    result = await db.execute(
        select(func.sum(Booking.total_amount)).where(
            and_(
                Booking.booked_at >= start_date,
                Booking.status == 'confirmed'
            )
        )
    )
    total_revenue = result.scalar() or Decimal('0')
    
    # Total tickets sold
    result = await db.execute(
        select(func.sum(Booking.quantity)).where(
            and_(
                Booking.booked_at >= start_date,
                Booking.status == 'confirmed'
            )
        )
    )
    total_tickets = result.scalar() or 0
    
    # Total users
    result = await db.execute(
        select(func.count(User.id)).where(
            User.created_at >= start_date
        )
    )
    total_users = result.scalar() or 0
    
    # WhatsApp bookings
    result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.booked_at >= start_date,
                Booking.status == 'confirmed',
                Booking.booking_source == 'whatsapp'
            )
        )
    )
    whatsapp_bookings = result.scalar() or 0
    
    # Average ticket price
    result = await db.execute(
        select(func.avg(Event.ticket_price)).where(
            Event.created_at >= start_date
        )
    )
    avg_ticket_price = result.scalar() or Decimal('0')
    
    # Top events by revenue
    result = await db.execute(
        select(
            Event.id,
            Event.title,
            func.sum(Booking.total_amount).label('revenue'),
            func.count(Booking.id).label('bookings')
        ).join(
            Booking, Event.id == Booking.event_id
        ).where(
            and_(
                Booking.booked_at >= start_date,
                Booking.status == 'confirmed'
            )
        ).group_by(
            Event.id, Event.title
        ).order_by(
            func.sum(Booking.total_amount).desc()
        ).limit(5)
    )
    top_events = result.all()
    
    # Events by category
    result = await db.execute(
        select(
            Event.category,
            func.count(Event.id).label('count')
        ).where(
            Event.created_at >= start_date
        ).group_by(
            Event.category
        ).order_by(
            func.count(Event.id).desc()
        )
    )
    events_by_category = result.all()
    
    return {
        'period': period,
        'start_date': start_date.isoformat(),
        'summary': {
            'total_events': total_events,
            'active_events': active_events,
            'total_bookings': total_bookings,
            'total_revenue': float(total_revenue),
            'total_tickets': total_tickets,
            'total_users': total_users,
            'whatsapp_bookings': whatsapp_bookings,
            'avg_ticket_price': float(avg_ticket_price)
        },
        'top_events': [
            {
                'id': str(e.id),
                'title': e.title,
                'revenue': float(e.revenue),
                'bookings': e.bookings
            }
            for e in top_events
        ],
        'events_by_category': [
            {
                'category': c.category or 'uncategorized',
                'count': c.count
            }
            for c in events_by_category
        ]
    }


async def get_organizer_analytics(
    organizer_id: str,
    db: AsyncSession,
    period: str = '30d'
) -> Dict[str, Any]:
    """
    Get analytics for a specific organizer
    
    Args:
        organizer_id: Organizer user ID
        db: Database session
        period: Time period ('7d', '30d', '90d', 'all')
    
    Returns:
        Dictionary with organizer analytics
    """
    # Calculate date range
    if period == '7d':
        start_date = datetime.now() - timedelta(days=7)
    elif period == '30d':
        start_date = datetime.now() - timedelta(days=30)
    elif period == '90d':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime(2020, 1, 1)
    
    # Total events
    result = await db.execute(
        select(func.count(Event.id)).where(
            and_(
                Event.host_id == organizer_id,
                Event.created_at >= start_date
            )
        )
    )
    total_events = result.scalar() or 0
    
    # Get all events for this organizer
    result = await db.execute(
        select(Event).where(
            and_(
                Event.host_id == organizer_id,
                Event.created_at >= start_date
            )
        )
    )
    events = result.scalars().all()
    event_ids = [e.id for e in events]
    
    if not event_ids:
        return {
            'period': period,
            'summary': {
                'total_events': 0,
                'total_bookings': 0,
                'total_revenue': 0,
                'total_tickets': 0
            },
            'events': []
        }
    
    # Total bookings
    result = await db.execute(
        select(func.count(Booking.id)).where(
            and_(
                Booking.event_id.in_(event_ids),
                Booking.status == 'confirmed'
            )
        )
    )
    total_bookings = result.scalar() or 0
    
    # Total revenue
    result = await db.execute(
        select(func.sum(Booking.total_amount)).where(
            and_(
                Booking.event_id.in_(event_ids),
                Booking.status == 'confirmed'
            )
        )
    )
    total_revenue = result.scalar() or Decimal('0')
    
    # Total tickets
    result = await db.execute(
        select(func.sum(Booking.quantity)).where(
            and_(
                Booking.event_id.in_(event_ids),
                Booking.status == 'confirmed'
            )
        )
    )
    total_tickets = result.scalar() or 0
    
    # Per-event breakdown
    event_stats = []
    for event in events:
        result = await db.execute(
            select(
                func.count(Booking.id).label('bookings'),
                func.sum(Booking.total_amount).label('revenue'),
                func.sum(Booking.quantity).label('tickets')
            ).where(
                and_(
                    Booking.event_id == event.id,
                    Booking.status == 'confirmed'
                )
            )
        )
        stats = result.one()
        
        event_stats.append({
            'id': str(event.id),
            'title': event.title,
            'date': event.event_date.isoformat(),
            'bookings': stats.bookings or 0,
            'revenue': float(stats.revenue or 0),
            'tickets_sold': stats.tickets or 0,
            'capacity': event.capacity,
            'fill_rate': round((stats.tickets or 0) / event.capacity * 100, 1) if event.capacity > 0 else 0
        })
    
    return {
        'period': period,
        'start_date': start_date.isoformat(),
        'summary': {
            'total_events': total_events,
            'total_bookings': total_bookings,
            'total_revenue': float(total_revenue),
            'total_tickets': total_tickets
        },
        'events': sorted(event_stats, key=lambda x: x['revenue'], reverse=True)
    }
