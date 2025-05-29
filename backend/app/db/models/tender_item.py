from sqlalchemy import Column, String, Text, Numeric, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class TenderItem(Base):
    __tablename__ = "tender_items"
    
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    
    # Informações do item
    item_number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Quantidade e unidade
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_of_measure = Column(String(20), nullable=False)
    
    # Especificações
    specifications = Column(JSON, default={})
    technical_requirements = Column(Text, nullable=True)
    
    # Preço de referência
    reference_price = Column(Numeric(10, 2), nullable=True)
    estimated_total = Column(Numeric(15, 2), nullable=True)
    
    # Relacionamentos
    tender = relationship("Tender", back_populates="items")
    product = relationship("Product", back_populates="tender_items")
    quote_items = relationship("QuoteItem", back_populates="tender_item")
