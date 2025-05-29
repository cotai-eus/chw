from sqlalchemy import Column, String, Text, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Informações pessoais
    phone = Column(String(20), nullable=True)
    mobile_phone = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    
    # Informações profissionais
    position = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Configurações de notificação
    notification_email = Column(String(255), nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="profile")
