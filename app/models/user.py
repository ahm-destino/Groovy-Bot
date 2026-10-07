from sqlalchemy import Column, String, ARRAY, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from geoalchemy2 import Geography
from app.database import Base


class User(Base):
    """
    User model - Shared with Grooovy webapp
    
    Webapp fields (existing):
    - id, email, password_hash, first_name, last_name, created_at, updated_at
    
    Bot additions:
    - phone, whatsapp_name, location_preference, preferred_categories, language
    """
    __tablename__ = "users"
    
    # Shared fields (webapp + bot)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True)  # Webapp field
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Bot-specific fields
    phone = Column(String(20), unique=True, index=True)  # Primary identifier for bot
    whatsapp_name = Column(String(255))
    location_preference = Column(Geography(geometry_type='POINT', srid=4326))
    preferred_categories = Column(ARRAY(String))
    language = Column(String(10), default='en')

    @property
    def name(self) -> "str | None":
        """
        Human-friendly display name.

        The model stores names as first_name/last_name (shared with the webapp),
        but several call sites expect a single `name` attribute. Compose it here
        so those paths render a real name instead of raising AttributeError.
        """
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return " ".join(parts)
        return self.whatsapp_name or None
