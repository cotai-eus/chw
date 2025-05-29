from sqlalchemy import Column, String, Text, Date, DateTime, Numeric, Boolean, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class TenderStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    QUOTE_PHASE = "QUOTE_PHASE"
    EVALUATION = "EVALUATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TenderType(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    INVITATION = "INVITATION"


class Tender(Base):
    __tablename__ = "tenders"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Informações básicas
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tender_number = Column(String(100), nullable=True, index=True)
    type = Column(SAEnum(TenderType), default=TenderType.PRIVATE)
    status = Column(SAEnum(TenderStatus), default=TenderStatus.DRAFT)
    
    # Datas importantes
    publication_date = Column(DateTime(timezone=True), nullable=True)
    submission_deadline = Column(DateTime(timezone=True), nullable=True)
    opening_date = Column(DateTime(timezone=True), nullable=True)
    
    # Valores
    estimated_value = Column(Numeric(15, 2), nullable=True)
    budget_available = Column(Numeric(15, 2), nullable=True)
    
    # Documentos e arquivos
    original_file_url = Column(String(500), nullable=True)
    document_urls = Column(JSON, default=[])
    
    # Dados processados pela IA
    processed_data = Column(JSON, default={})
    risk_score = Column(Numeric(3, 2), nullable=True)  # 0.00 a 1.00
    ai_analysis = Column(JSON, default={})
    
    # Configurações
    is_public = Column(Boolean, default=False)
    requires_documentation = Column(Boolean, default=True)
    allows_partial_quotes = Column(Boolean, default=False)
    
    # Critérios de avaliação
    evaluation_criteria = Column(JSON, default={})
    
    # Relacionamentos
    company = relationship("Company", back_populates="tenders")
    created_by = relationship("User", back_populates="created_tenders")
    items = relationship("TenderItem", back_populates="tender", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="tender")
