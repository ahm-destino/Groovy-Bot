"""
AI-powered event recommendation service
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta

from app.models import Event, Booking, User


async def get_user_preferences(
    phone: str,
    db: AsyncSession
) -> dict:
    """Get user preferences and history for recommendations"""
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {
            'categories': [],
            'price_range': None,
            'locations': []
        }

    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.user_id == user.id,
                Booking.status == 'confirmed'
            )
        ).limit(10)
    )
    bookings = result.scalars().all()

    categories = set()
    price_points = []
    locations = set()

    for booking in bookings:
        result = await db.execute(
            select(Event).where(Event.id == booking.event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            if event.category:
                categories.add(event.category)
            price_points.append(event.ticket_price)
            locations.add(event.venue_name)

    price_range = None
    if price_points:
        avg_price = sum(price_points) / len(price_points)
        price_range = (avg_price * 0.5, avg_price * 1.5)

    return {
        'categories': list(categories),
        'price_range': price_range,
        'locations': list(locations)
    }


async def get_personalized_recommendations(
    phone: str,
    db: AsyncSession,
    limit: int = 5
) -> List[Event]:
    """
    Get personalized recommendations based on user history.
    """
    prefs = await get_user_preferences(phone, db)

    query = select(Event).where(
        and_(
            Event.status == 'active',
            Event.event_date > datetime.now()
        )
    )

    if prefs['categories']:
        query = query.where(Event.category.in_(prefs['categories']))

    if prefs['price_range']:
        price_min, price_max = prefs['price_range']
        query = query.where(
            and_(
                Event.ticket_price >= price_min,
                Event.ticket_price <= price_max
            )
        )

    query = query.order_by(Event.event_date).limit(limit)

    result = await db.execute(query)
    recommended = result.scalars().all()

    if len(recommended) < limit:
        remaining = limit - len(recommended)
        query = select(Event).where(
            and_(
                Event.status == 'active',
                Event.event_date > datetime.now()
            )
        ).order_by(Event.event_date).limit(remaining)

        result = await db.execute(query)
        extra = result.scalars().all()
        recommended.extend(extra)

    return recommended[:limit]


async def get_similar_events(
    event_id: str,
    db: AsyncSession,
    limit: int = 5
) -> List[Event]:
    """Find events similar to a given event."""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return []

    query = select(Event).where(
        and_(
            Event.status == 'active',
            Event.event_date > datetime.now(),
            Event.id != event_id
        )
    )

    if event.category:
        query = query.where(Event.category == event.category)

    price_min = event.ticket_price * 0.7
    price_max = event.ticket_price * 1.3
    query = query.where(
        and_(
            Event.ticket_price >= price_min,
            Event.ticket_price <= price_max
        )
    )

    query = query.order_by(Event.event_date).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_filtered_recommendations(
    phone: str,
    db: AsyncSession,
    category: str = 'other',
    location: str = 'anywhere',
    limit: int = 5
) -> List[Event]:
    """
    Get recommendations filtered by category and location.
    """
    from app.services.location import get_user_location_from_phone, get_events_near_location
    
    # Map category to event categories
    category_map = {
        'music': ['music', 'concert', 'dj', 'live music'],
        'party': ['party', 'nightlife', 'club', 'hangout'],
        'food': ['food', 'drinks', 'brunch', 'festival'],
        'art': ['art', 'theater', 'comedy', 'exhibition'],
        'sports': ['sports', 'fitness', 'workout'],
        'networking': ['networking', 'business', 'career', 'meetup'],
        'other': []  # No filter
    }
    
    # Get base query
    query = select(Event).where(
        and_(
            Event.status == 'active',
            Event.event_date > datetime.now()
        )
    )
    
    # Apply category filter
    if category != 'other' and category in category_map:
        keywords = category_map[category]
        if keywords:
            # Filter by category field or keywords in title/description
            category_conditions = [Event.category.ilike(f'%{kw}%') for kw in keywords]
            query = query.where(or_(*category_conditions))
    
    # Get events
    result = await db.execute(query.order_by(Event.event_date).limit(limit * 2))
    events = result.scalars().all()
    
    # Filter by location if needed
    if location != 'anywhere':
        # Get user location
        user_location = await get_user_location_from_phone(phone, db)
        
        if user_location:
            # Filter events by location keywords
            location_keywords = {
                'lagos': ['lagos', 'island', 'mainland'],
                'lekki': ['lekki', 'ajah', 'victoria island', 'vi'],
                'ikeja': ['ikeja', 'ogba', 'agege'],
                'surulere': ['surulere', 'ojuelegba'],
                'near_me': []
            }
            
            keywords = location_keywords.get(location, [])
            if keywords:
                filtered_events = []
                for event in events:
                    venue = (event.venue_name or '').lower()
                    address = (event.full_address or '').lower()
                    if any(kw in venue or kw in address for kw in keywords):
                        filtered_events.append(event)
                events = filtered_events
    
    return events[:limit]


async def format_recommendations_message(
    events: List[Event],
    reason: str = "recommended for you"
) -> str:
    """Format recommendations for WhatsApp"""
    if not events:
        return "No recommendations available at the moment."

    message = f"Events {reason}\n\n"

    for i, event in enumerate(events, 1):
        message += f"{i}. {event.title}\n"
        message += f"   Date: {event.event_date.strftime('%a, %b %d - %I:%M %p')}\n"
        message += f"   Venue: {event.venue_name}\n"
        message += f"   Ticket: NGN {event.ticket_price:,.0f}\n"

        if event.category:
            message += f"   Category: {event.category.title()}\n"

        remaining = (event.capacity or 0) - (event.tickets_sold or 0)
        if remaining <= 10:
            message += f"   Only {remaining} left.\n"

        message += "\n"

    message += "Reply with a number to see details."

    return message
