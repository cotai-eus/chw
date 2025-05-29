from sqlalchemy import Column, String, Text, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class QuoteItem(Base):
    __tablename__ = "quote_items"
    
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    tender_item_id = Column(UUID(as_uuid=True), ForeignKey("tender_items.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    
    # Informações do item cotado
    item_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    
    # Quantidade e preços
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(15, 2), nullable=False)
    
    # Especificações oferecidas
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    specifications = Column(Text, nullable=True)
    
    # Condições específicas do item
    delivery_time_days = Column(Integer, nullable=True)
    warranty_months = Column(Integer, nullable=True)
    
    # Observações
    notes = Column(Text, nullable=True)
    
    # Relacionamentos
    quote = relationship("Quote", back_populates="items")
    tender_item = relationship("TenderItem", back_populates="quote_items")
    product = relationship("Product", back_populates="quote_items")
