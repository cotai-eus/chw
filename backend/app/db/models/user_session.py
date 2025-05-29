from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    device_fingerprint = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(INET, nullable=True)
    
    # Controle de sessão
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="sessions")
