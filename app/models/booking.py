from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, ForeignKey, func, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class Booking(Base):
    """
    Booking model - Shared with Grooovy webapp

    Webapp fields (existing):
    - id, user_id, event_id, quantity, total_amount, status, created_at

    Bot additions:
    - phone, payment_reference, payment_method, booked_at, confirmed_at,
      cancelled_at, booking_source, gift fields
    """
    __tablename__ = "bookings"

    # Shared fields (webapp + bot)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'), index=True)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default='pending', index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Bot-specific fields
    phone = Column(String(20))  # WhatsApp phone number
    payment_reference = Column(String(100), unique=True, index=True)  # Flutterwave tx_ref
    payment_method = Column(String(50))  # card, bank, ussd, mobile_money
    booked_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    confirmed_at = Column(TIMESTAMP(timezone=True))
    cancelled_at = Column(TIMESTAMP(timezone=True))
    booking_source = Column(String(20), default='webapp')  # 'webapp' or 'whatsapp'

    # Gift ticket fields (matches add_gift_tickets.sql migration)
    is_gift = Column(Boolean, default=False, index=True)
    gift_sender_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    gift_recipient_phone = Column(String(20), nullable=True, index=True)
    gift_message = Column(Text, nullable=True)
    gift_redeemed = Column(Boolean, default=False)
    gift_redeemed_at = Column(TIMESTAMP(timezone=True), nullable=True)
