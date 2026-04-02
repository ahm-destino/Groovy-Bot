from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.database import Base


class TicketTier(Base):
    __tablename__ = "ticket_tiers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=False)
    capacity = Column(Integer, nullable=False)
    tickets_sold = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    available_from = Column(TIMESTAMP(timezone=True))
    available_until = Column(TIMESTAMP(timezone=True))
    status = Column(String(20), default='active')
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="ticket_tiers")
    bookings = relationship("Booking", back_populates="tier")
    tickets = relationship("Ticket", back_populates="tier")
    
    def is_available(self) -> bool:
        """Check if tier is currently available for purchase"""
        if self.status != 'active':
            return False
        
        if (self.tickets_sold or 0) >= self.capacity:
            return False
        
        now = datetime.utcnow()
        
        if self.available_from and now < self.available_from:
            return False
        
        if self.available_until and now > self.available_until:
            return False
        
        return True
    
    def remaining_capacity(self) -> int:
        """Get remaining tickets for this tier"""
        return max(0, self.capacity - (self.tickets_sold or 0))
