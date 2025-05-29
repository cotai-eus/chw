from sqlalchemy import Column, String, Boolean, ForeignKey, JSON, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class SupplierStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLACKLISTED = "BLACKLISTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class Supplier(Base):
    __tablename__ = "suppliers"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Dados básicos
    name = Column(String(255), nullable=False, index=True)
    cnpj = Column(String(18), nullable=True, index=True)
    cpf = Column(String(14), nullable=True, index=True)
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
    
    # Status e categoria
    status = Column(SAEnum(SupplierStatus), default=SupplierStatus.PENDING_VERIFICATION)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    
    # Avaliação e histórico
    rating = Column(String(10), nullable=True)  # JSON para múltiplos critérios
    delivery_time_avg = Column(String(50), nullable=True)
    quality_score = Column(String(10), nullable=True)
    
    # Flags
    is_verified = Column(Boolean, default=False)
    is_preferred = Column(Boolean, default=False)
    
    # Dados adicionais
    description = Column(Text, nullable=True)
    certifications = Column(JSON, default=[])
    specialties = Column(JSON, default=[])
    payment_terms = Column(JSON, default={})
    
    # Relacionamentos
    company = relationship("Company", back_populates="suppliers")
    products = relationship("Product", back_populates="supplier", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="supplier")
