from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from decimal import Decimal

from app.database import Base


class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='CASCADE'))
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)  # percentage, fixed_amount
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    max_uses = Column(Integer)
    current_uses = Column(Integer, default=0)
    valid_from = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    valid_until = Column(TIMESTAMP(timezone=True))
    min_tickets = Column(Integer, default=1)
    max_discount_amount = Column(DECIMAL(10, 2))
    status = Column(String(20), default='active')
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="promo_codes")
    bookings = relationship("Booking", back_populates="promo_code")
    creator = relationship("User")
    
    def is_valid(self, quantity: int = 1) -> tuple[bool, str]:
        """
        Check if promo code is valid
        
        Returns:
            (is_valid, error_message)
        """
        if self.status != 'active':
            return False, "Promo code is not active"
        
        now = datetime.utcnow()
        
        if now < self.valid_from:
            return False, "Promo code not yet valid"
        
        if self.valid_until and now > self.valid_until:
            return False, "Promo code has expired"
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Promo code has reached maximum uses"
        
        if quantity < self.min_tickets:
            return False, f"Minimum {self.min_tickets} tickets required"
        
        return True, ""
    
    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """Calculate discount amount"""
        if self.discount_type == 'percentage':
            discount = subtotal * (self.discount_value / Decimal('100'))
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:  # fixed_amount
            discount = self.discount_value
        
        # Don't exceed subtotal
        return min(discount, subtotal)
