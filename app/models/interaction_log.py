from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    kind = Column(String(20))  # button or list
    context = Column(String(100))
    options = Column(JSONB)
    selected_id = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    selected_at = Column(TIMESTAMP(timezone=True))
