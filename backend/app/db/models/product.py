from sqlalchemy import Column, String, Text, Numeric, Boolean, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class Product(Base):
    __tablename__ = "products"
    
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    
    # Informações básicas
    name = Column(String(255), nullable=False, index=True)
    sku = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    
    # Preços e unidades
    unit_price = Column(Numeric(10, 2), nullable=True)
    unit_of_measure = Column(String(20), nullable=True)
    minimum_quantity = Column(Numeric(10, 2), nullable=True)
    
    # Status e disponibilidade
    status = Column(SAEnum(ProductStatus), default=ProductStatus.ACTIVE)
    is_available = Column(Boolean, default=True)
    lead_time_days = Column(String(10), nullable=True)
    
    # Especificações técnicas
    specifications = Column(JSON, default={})
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    
    # Imagens e documentos
    image_urls = Column(JSON, default=[])
    document_urls = Column(JSON, default=[])
    
    # Relacionamentos
    supplier = relationship("Supplier", back_populates="products")
    tender_items = relationship("TenderItem", back_populates="product")
    quote_items = relationship("QuoteItem", back_populates="product")
