from sqlalchemy import Column, String, Text, Integer, DECIMAL, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class Event(Base):
    """
    Event model - Shared with Grooovy webapp
    
    Webapp fields (existing):
    - id, host_id, title, description, category, event_date, location_lat, location_lng,
      full_address, venue_name, capacity, tickets_sold, ticket_price, currency,
      banner_image_url, status, created_at, updated_at
    
    Bot additions:
    - is_anonymous, anonymous_mode, secret_code, location_reveal_trigger,
      location_reveal_hours_before, entry_code_format, shared_entry_code,
      location_revealed, location_revealed_at, created_via
    """
    __tablename__ = "events"
    
    # Shared fields (webapp + bot)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    event_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    location_lat = Column(DECIMAL(10, 8))
    location_lng = Column(DECIMAL(11, 8))
    full_address = Column(Text)
    venue_name = Column(String(255))
    capacity = Column(Integer)
    tickets_sold = Column(Integer, default=0)
    ticket_price = Column(DECIMAL(10, 2))
    currency = Column(String(3), default='NGN')
    banner_image_url = Column(Text)
    status = Column(String(20), default='active', index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Bot-specific fields (anonymous events)
    is_anonymous = Column(Boolean, default=False, index=True)
    anonymous_mode = Column(String(20))  # 'code_required', 'location_hidden', 'hybrid'
    secret_code = Column(String(50), unique=True, index=True)
    location_reveal_trigger = Column(String(20))  # 'immediate', 'time_based', 'manual'
    location_reveal_hours_before = Column(Integer)
    entry_code_format = Column(String(20))  # 'shared', 'unique_per_ticket'
    shared_entry_code = Column(String(50))
    location_revealed = Column(Boolean, default=False)
    location_revealed_at = Column(TIMESTAMP(timezone=True))
    created_via = Column(String(20), default='webapp')  # 'webapp' or 'whatsapp'
