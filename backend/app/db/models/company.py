import uuid
from sqlalchemy import Column, String, Boolean, Integer, JSON, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class CompanyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class PlanType(str, Enum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class Company(Base):
    __tablename__ = "companies"
    
    name = Column(String(255), nullable=False, index=True)
    cnpj = Column(String(18), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Endereço
    address_street = Column(String(255), nullable=True)
    address_number = Column(String(10), nullable=True)
    address_complement = Column(String(100), nullable=True)
    address_neighborhood = Column(String(100), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(2), nullable=True)
    address_zip_code = Column(String(10), nullable=True)
    
    # Status e configurações
    status = Column(SAEnum(CompanyStatus), default=CompanyStatus.PENDING_APPROVAL)
    plan_type = Column(SAEnum(PlanType), default=PlanType.BASIC)
    is_verified = Column(Boolean, default=False)
    
    # Configurações do plano
    max_users = Column(Integer, default=5)
    max_concurrent_sessions = Column(Integer, default=3)
    max_storage_gb = Column(Integer, default=10)
    
    # Configurações específicas
    settings = Column(JSON, default={})
    features_enabled = Column(JSON, default={})
    
    # Campos de auditoria
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    # Relacionamentos
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    tenders = relationship("Tender", back_populates="company", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="company", cascade="all, delete-orphan")
    kanban_boards = relationship("KanbanBoard", back_populates="company", cascade="all, delete-orphan")
