import uuid
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class QuoteItemBase(BaseModel):
    item_number: int
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    specifications: Optional[str] = None
    delivery_time_days: Optional[int] = Field(None, ge=0)
    warranty_months: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class QuoteItemCreate(QuoteItemBase):
    tender_item_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None


class QuoteItemUpdate(BaseModel):
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    specifications: Optional[str] = None
    delivery_time_days: Optional[int] = Field(None, ge=0)
    warranty_months: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    product_id: Optional[uuid.UUID] = None


class QuoteItemInDBBase(QuoteItemBase):
    id: uuid.UUID
    quote_id: uuid.UUID
    tender_item_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    total_price: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteItem(QuoteItemInDBBase):
    pass


class QuoteBase(BaseModel):
    quote_number: Optional[str] = Field(None, max_length=100)
    valid_until: Optional[datetime] = None
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_value: Optional[Decimal] = Field(None, ge=0)
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    delivery_time_days: Optional[int] = Field(None, ge=0)
    warranty_terms: Optional[str] = None
    notes: Optional[str] = None
    document_urls: Optional[List[str]] = []


class QuoteCreate(QuoteBase):
    tender_id: uuid.UUID
    supplier_id: uuid.UUID
    items: List[QuoteItemCreate] = []


class QuoteUpdate(BaseModel):
    quote_number: Optional[str] = Field(None, max_length=100)
    status: Optional[QuoteStatus] = None
    valid_until: Optional[datetime] = None
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_value: Optional[Decimal] = Field(None, ge=0)
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    delivery_time_days: Optional[int] = Field(None, ge=0)
    warranty_terms: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    document_urls: Optional[List[str]] = None
    is_winning_quote: Optional[bool] = None


class QuoteInDBBase(QuoteBase):
    id: uuid.UUID
    tender_id: uuid.UUID
    supplier_id: uuid.UUID
    created_by_id: uuid.UUID
    status: QuoteStatus
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    total_value: Optional[Decimal] = None
    final_value: Optional[Decimal] = None
    internal_notes: Optional[str] = None
    is_winning_quote: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Quote(QuoteInDBBase):
    pass


class QuoteWithItems(Quote):
    items: List[QuoteItem] = []


class QuoteInDB(QuoteInDBBase):
    pass


# Schema para resposta de cotação
class QuoteResponse(BaseModel):
    quote_id: uuid.UUID
    response: str  # "accept" or "reject"
    feedback: Optional[str] = None
