import uuid
from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


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


class TenderItemBase(BaseModel):
    item_number: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_of_measure: str = Field(..., min_length=1, max_length=20)
    specifications: Optional[Dict] = {}
    technical_requirements: Optional[str] = None
    reference_price: Optional[Decimal] = Field(None, ge=0)


class TenderItemCreate(TenderItemBase):
    product_id: Optional[uuid.UUID] = None


class TenderItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_of_measure: Optional[str] = Field(None, min_length=1, max_length=20)
    specifications: Optional[Dict] = None
    technical_requirements: Optional[str] = None
    reference_price: Optional[Decimal] = Field(None, ge=0)
    product_id: Optional[uuid.UUID] = None


class TenderItemInDBBase(TenderItemBase):
    id: uuid.UUID
    tender_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    estimated_total: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenderItem(TenderItemInDBBase):
    pass


class TenderBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    tender_number: Optional[str] = Field(None, max_length=100)
    type: TenderType = TenderType.PRIVATE
    publication_date: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    opening_date: Optional[datetime] = None
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    budget_available: Optional[Decimal] = Field(None, ge=0)
    is_public: bool = False
    requires_documentation: bool = True
    allows_partial_quotes: bool = False
    evaluation_criteria: Optional[Dict] = {}


class TenderCreate(TenderBase):
    items: List[TenderItemCreate] = []


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    tender_number: Optional[str] = Field(None, max_length=100)
    type: Optional[TenderType] = None
    status: Optional[TenderStatus] = None
    publication_date: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    opening_date: Optional[datetime] = None
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    budget_available: Optional[Decimal] = Field(None, ge=0)
    is_public: Optional[bool] = None
    requires_documentation: Optional[bool] = None
    allows_partial_quotes: Optional[bool] = None
    evaluation_criteria: Optional[Dict] = None


class TenderInDBBase(TenderBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_by_id: uuid.UUID
    status: TenderStatus
    original_file_url: Optional[str] = None
    document_urls: List[str] = []
    processed_data: Dict = {}
    risk_score: Optional[Decimal] = None
    ai_analysis: Dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Tender(TenderInDBBase):
    pass


class TenderWithItems(Tender):
    items: List[TenderItem] = []


class TenderInDB(TenderInDBBase):
    pass


# Schema para upload de edital
class TenderUpload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    type: TenderType = TenderType.PRIVATE


# Schema para análise de IA
class TenderAnalysis(BaseModel):
    tender_id: uuid.UUID
    processed_data: Dict
    risk_score: Optional[Decimal] = None
    ai_analysis: Dict
    items_extracted: List[TenderItemCreate] = []
