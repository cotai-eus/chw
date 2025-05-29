import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class UserRole(str, Enum):
    MASTER = "MASTER"
    ADMIN = "ADMIN_EMPRESA"
    MANAGER = "MANAGER"
    USER = "USER"
    VIEWER = "VIEWER"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"


class User(Base):
    __tablename__ = "users"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    
    # Permissões e status
    role = Column(SAEnum(UserRole), default=UserRole.USER, nullable=False)
    permissions = Column(JSON, default={})
    status = Column(SAEnum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Flags de controle
    email_verified = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Campos de auditoria
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(INET, nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    company = relationship("Company", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    created_tenders = relationship("Tender", back_populates="created_by")
    quotes = relationship("Quote", back_populates="created_by")
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
