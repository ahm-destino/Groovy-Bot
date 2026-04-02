"""
Social sharing service for events
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from urllib.parse import quote

from app.models import Event


async def generate_share_links(
    event_id: str,
    db: AsyncSession,
    referrer_code: str = None
) -> Dict[str, str]:
    """
    Generate social media share links for an event

    Args:
        event_id: Event UUID
        db: Database session
        referrer_code: Optional referrer tracking code

    Returns:
        Dictionary of platform: share_url
    """
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one()

    # Base event URL (would be your webapp URL)
    base_url = f"https://grooovy.app/events/{event_id}"
    if referrer_code:
        base_url += f"?ref={referrer_code}"

    # Event details for sharing
    title = event.title
    description = event.description or f"Join us at {event.title}"
    date_str = event.event_date.strftime('%B %d, %Y')

    # Encode for URLs
    encoded_url = quote(base_url)
    encoded_title = quote(title)
    encoded_description = quote(f"{description} - {date_str}")

    return {
        'whatsapp': f"https://wa.me/?text={encoded_title}%20-%20{encoded_description}%0A{encoded_url}",
        'twitter': f"https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}&hashtags=Grooovy,Events",
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        'telegram': f"https://t.me/share/url?url={encoded_url}&text={encoded_title}",
        'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
        'direct': base_url
    }


async def create_share_message(
    event_id: str,
    db: AsyncSession,
    include_booking_link: bool = True
) -> str:
    """
    Create a shareable message for an event

    Args:
        event_id: Event UUID
        db: Database session
        include_booking_link: Include booking instructions

    Returns:
        Formatted share message
    """
    from app.config import settings

    # Get event
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one()

    message = f"{event.title}\n\n"

    if event.description:
        # Truncate description for sharing
        desc = event.description[:200]
        if len(event.description) > 200:
            desc += "..."
        message += f"{desc}\n\n"

    message += f"Date: {event.event_date.strftime('%A, %B %d, %Y')}\n"
    message += f"Time: {event.event_date.strftime('%I:%M %p')}\n"

    if not event.is_anonymous or event.location_revealed:
        message += f"Venue: {event.venue_name}\n"
    else:
        message += "Venue: Hidden (reveals after booking)\n"

    if event.ticket_price > 0:
        message += f"Ticket: NGN {event.ticket_price:,.0f}\n"
    else:
        message += "Ticket: FREE\n"

    remaining = event.capacity - event.tickets_sold
    if remaining <= 20:
        message += f"\nOnly {remaining} tickets left.\n"

    if include_booking_link:
        # Use the configured phone number ID for the wa.me link
        wa_number = settings.WHATSAPP_PHONE_NUMBER_ID
        message += f"\nBook via WhatsApp: wa.me/{wa_number}\n"
        message += f"Say: Book {event.title}"

    message += f"\n#Grooovy #Events #{event.category or 'Event'}"

    return message


async def track_share(
    event_id: str,
    platform: str,
    sharer_phone: str,
    db: AsyncSession
):
    """
    Track event shares for analytics

    Args:
        event_id: Event UUID
        platform: Social platform (whatsapp, twitter, etc.)
        sharer_phone: Phone of person sharing
        db: Database session
    """
    # This would insert into a shares tracking table
    # For now, we'll just log it
    from datetime import datetime
    print(f"Share tracked: {event_id} on {platform} by {sharer_phone} at {datetime.now()}")

    # Could increment a share_count on the event
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event:
        # If you add a share_count column to events table
        # event.share_count = (event.share_count or 0) + 1
        # await db.commit()
        pass


def format_share_options_message(event_title: str, share_links: Dict[str, str]) -> str:
    """Format share options for WhatsApp"""
    message = f"Share: {event_title}\n\n"
    message += "Choose a platform:\n\n"

    platforms = {
        'whatsapp': 'WhatsApp',
        'twitter': 'Twitter',
        'facebook': 'Facebook',
        'telegram': 'Telegram',
        'linkedin': 'LinkedIn'
    }

    for platform, label in platforms.items():
        if platform in share_links:
            message += f"{label}\n{share_links[platform]}\n\n"

    message += f"Copy link:\n{share_links['direct']}"

    return message


async def generate_referral_code(user_id: str, event_id: str) -> str:
    """
    Generate a unique referral code for tracking

    Args:
        user_id: User UUID
        event_id: Event UUID

    Returns:
        Referral code string
    """
    import hashlib

    # Create a short hash from user_id and event_id
    combined = f"{user_id}:{event_id}"
    hash_obj = hashlib.md5(combined.encode())
    code = hash_obj.hexdigest()[:8].upper()

    return f"REF{code}"


async def get_referral_stats(
    user_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Get referral statistics for a user

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Referral statistics
    """
    # This would query a referrals tracking table
    # For now, return placeholder
    return {
        'total_shares': 0,
        'total_referrals': 0,
        'total_bookings_from_referrals': 0,
        'total_earnings': 0  # If you implement referral rewards
    }
