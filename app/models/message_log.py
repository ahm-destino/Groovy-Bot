from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class MessageLog(Base):
    __tablename__ = "message_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    direction = Column(String(10))  # 'inbound', 'outbound'
    message_type = Column(String(20))
    content = Column(Text)
    whatsapp_message_id = Column(String(255), index=True)
    intent_detected = Column(String(50))
    entities = Column(JSONB)
    response_time_ms = Column(Integer)
    error = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
