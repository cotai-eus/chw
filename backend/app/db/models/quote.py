from sqlalchemy import Column, String, Text, DateTime, Numeric, Boolean, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quote(Base):
    __tablename__ = "quotes"
    
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Informações básicas
    quote_number = Column(String(100), nullable=True, index=True)
    status = Column(SAEnum(QuoteStatus), default=QuoteStatus.DRAFT)
    
    # Datas
    sent_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Valores totais
    total_value = Column(Numeric(15, 2), nullable=True)
    discount_percentage = Column(Numeric(5, 2), nullable=True)
    discount_value = Column(Numeric(15, 2), nullable=True)
    final_value = Column(Numeric(15, 2), nullable=True)
    
    # Condições
    payment_terms = Column(Text, nullable=True)
    delivery_terms = Column(Text, nullable=True)
    delivery_time_days = Column(Integer, nullable=True)
    warranty_terms = Column(Text, nullable=True)
    
    # Documentos
    document_urls = Column(JSON, default=[])
    
    # Observações
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Flags
    is_winning_quote = Column(Boolean, default=False)
    
    # Relacionamentos
    tender = relationship("Tender", back_populates="quotes")
    supplier = relationship("Supplier", back_populates="quotes")
    created_by = relationship("User", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
