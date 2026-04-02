from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.id'), index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    qr_code_url = Column(Text)

    # Anonymous event fields
    entry_code = Column(String(50))
    location_revealed = Column(Boolean, default=False)
    location_revealed_at = Column(TIMESTAMP(timezone=True))

    status = Column(String(20), default='valid', index=True)
    checked_in_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Gift ticket fields (matches add_gift_tickets.sql migration)
    is_gift = Column(Boolean, default=False, index=True)
    gift_from_name = Column(String(255), nullable=True)
    gift_message = Column(Text, nullable=True)
