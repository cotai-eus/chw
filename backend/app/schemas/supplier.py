import uuid
from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal


class SupplierStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLACKLISTED = "BLACKLISTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    cnpj: Optional[str] = Field(None, max_length=18)
    cpf: Optional[str] = Field(None, max_length=14)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    
    # Endereço
    address_street: Optional[str] = Field(None, max_length=255)
    address_number: Optional[str] = Field(None, max_length=10)
    address_complement: Optional[str] = Field(None, max_length=100)
    address_neighborhood: Optional[str] = Field(None, max_length=100)
    address_city: Optional[str] = Field(None, max_length=100)
    address_state: Optional[str] = Field(None, max_length=2)
    address_zip_code: Optional[str] = Field(None, max_length=10)
    
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    certifications: Optional[List[str]] = []
    specialties: Optional[List[str]] = []
    payment_terms: Optional[Dict] = {}


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    cnpj: Optional[str] = Field(None, max_length=18)
    cpf: Optional[str] = Field(None, max_length=14)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    
    # Endereço
    address_street: Optional[str] = Field(None, max_length=255)
    address_number: Optional[str] = Field(None, max_length=10)
    address_complement: Optional[str] = Field(None, max_length=100)
    address_neighborhood: Optional[str] = Field(None, max_length=100)
    address_city: Optional[str] = Field(None, max_length=100)
    address_state: Optional[str] = Field(None, max_length=2)
    address_zip_code: Optional[str] = Field(None, max_length=10)
    
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    status: Optional[SupplierStatus] = None
    is_verified: Optional[bool] = None
    is_preferred: Optional[bool] = None
    rating: Optional[str] = None
    delivery_time_avg: Optional[str] = None
    quality_score: Optional[str] = None
    certifications: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    payment_terms: Optional[Dict] = None


class SupplierInDBBase(SupplierBase):
    id: uuid.UUID
    company_id: uuid.UUID
    status: SupplierStatus
    rating: Optional[str] = None
    delivery_time_avg: Optional[str] = None
    quality_score: Optional[str] = None
    is_verified: bool
    is_preferred: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Supplier(SupplierInDBBase):
    pass


class SupplierInDB(SupplierInDBBase):
    pass


# Schema para produto do fornecedor
class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    minimum_quantity: Optional[Decimal] = Field(None, ge=0)
    lead_time_days: Optional[str] = None
    specifications: Optional[Dict] = {}
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    image_urls: Optional[List[str]] = []
    document_urls: Optional[List[str]] = []


class ProductCreate(ProductBase):
    supplier_id: uuid.UUID


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    minimum_quantity: Optional[Decimal] = Field(None, ge=0)
    status: Optional[ProductStatus] = None
    is_available: Optional[bool] = None
    lead_time_days: Optional[str] = None
    specifications: Optional[Dict] = None
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    image_urls: Optional[List[str]] = None
    document_urls: Optional[List[str]] = None


class ProductInDBBase(ProductBase):
    id: uuid.UUID
    supplier_id: uuid.UUID
    status: ProductStatus
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Product(ProductInDBBase):
    pass


class ProductInDB(ProductInDBBase):
    pass
