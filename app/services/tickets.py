from typing import List
import qrcode
from io import BytesIO
import cloudinary
import cloudinary.uploader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import string

from app.config import settings
from app.models import Ticket, Booking, Event

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


def generate_unique_code(length: int = 8) -> str:
    """Generate a random alphanumeric code"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def generate_qr_code(data: str) -> str:
    """
    Generate QR code and upload to Cloudinary
    
    Args:
        data: Data to encode in QR code (ticket code)
    
    Returns:
        URL of uploaded QR code image
    """
    # Check if Cloudinary is configured
    if not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
        # Return a placeholder URL for testing (skip QR code upload)
        return f"https://via.placeholder.com/150x150.png?text={data}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Generate image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Upload to Cloudinary
    result = cloudinary.uploader.upload(
        buffer,
        folder="grooovy/tickets",
        public_id=f"ticket_{data}",
        overwrite=True
    )
    
    return result['secure_url']


async def generate_tickets_for_booking(
    booking: Booking,
    db: AsyncSession
) -> List[Ticket]:
    """
    Generate tickets after successful payment
    
    Args:
        booking: Booking object
        db: Database session
    
    Returns:
        List of generated Ticket objects
    """
    # Get event details
    result = await db.execute(
        select(Event).where(Event.id == booking.event_id)
    )
    event = result.scalar_one()
    
    tickets = []
    
    for i in range(booking.quantity):
        # Generate unique ticket code
        ticket_code = f"GRV-{booking.id.hex[:8].upper()}-{chr(65+i)}"
        
        # Generate QR code
        qr_url = await generate_qr_code(ticket_code)
        
        # Determine entry code for anonymous events
        entry_code = None
        if event.is_anonymous:
            if event.entry_code_format == 'unique_per_ticket':
                entry_code = generate_unique_code(6)
            elif event.entry_code_format == 'shared':
                entry_code = event.shared_entry_code
        
        # Create ticket
        ticket = Ticket(
            booking_id=booking.id,
            event_id=event.id,
            user_id=booking.user_id,
            ticket_code=ticket_code,
            qr_code_url=qr_url,
            entry_code=entry_code,
            location_revealed=event.location_revealed or not event.is_anonymous
        )
        
        db.add(ticket)
        tickets.append(ticket)
    
    await db.commit()
    
    # Refresh to get IDs
    for ticket in tickets:
        await db.refresh(ticket)
    
    return tickets


async def get_ticket_by_code(ticket_code: str, db: AsyncSession) -> Ticket:
    """Get ticket by code"""
    result = await db.execute(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    return result.scalar_one_or_none()


async def validate_ticket(ticket_code: str, db: AsyncSession) -> dict:
    """
    Validate ticket for check-in
    
    Returns:
        {
            'valid': bool,
            'message': str,
            'ticket': Ticket or None
        }
    """
    ticket = await get_ticket_by_code(ticket_code, db)
    
    if not ticket:
        return {
            'valid': False,
            'message': 'Invalid ticket code',
            'ticket': None
        }
    
    if ticket.status == 'used':
        return {
            'valid': False,
            'message': 'Ticket already used',
            'ticket': ticket
        }
    
    if ticket.status == 'cancelled':
        return {
            'valid': False,
            'message': 'Ticket cancelled',
            'ticket': ticket
        }
    
    if ticket.status == 'refunded':
        return {
            'valid': False,
            'message': 'Ticket refunded',
            'ticket': ticket
        }
    
    return {
        'valid': True,
        'message': 'Valid ticket',
        'ticket': ticket
    }


async def check_in_ticket(ticket_code: str, db: AsyncSession) -> dict:
    """
    Check in a ticket at venue
    
    Returns:
        {
            'success': bool,
            'message': str
        }
    """
    from datetime import datetime
    
    validation = await validate_ticket(ticket_code, db)
    
    if not validation['valid']:
        return {
            'success': False,
            'message': validation['message']
        }
    
    ticket = validation['ticket']
    ticket.status = 'used'
    ticket.checked_in_at = datetime.now()
    
    await db.commit()
    
    return {
        'success': True,
        'message': 'Check-in successful'
    }
