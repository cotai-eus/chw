import uuid
from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class CompanyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class PlanType(str, Enum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    cnpj: str = Field(..., min_length=14, max_length=18)
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
    
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)


class CompanyCreate(CompanyBase):
    plan_type: PlanType = PlanType.BASIC


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
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
    
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    status: Optional[CompanyStatus] = None
    plan_type: Optional[PlanType] = None
    max_users: Optional[int] = Field(None, gt=0)
    max_concurrent_sessions: Optional[int] = Field(None, gt=0)
    max_storage_gb: Optional[int] = Field(None, gt=0)
    settings: Optional[Dict] = None
    features_enabled: Optional[Dict] = None


class CompanyInDBBase(CompanyBase):
    id: uuid.UUID
    status: CompanyStatus
    plan_type: PlanType
    is_verified: bool
    max_users: int
    max_concurrent_sessions: int
    max_storage_gb: int
    settings: Dict
    features_enabled: Dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Company(CompanyInDBBase):
    pass


class CompanyInDB(CompanyInDBBase):
    pass


# Schema para estatísticas da empresa
class CompanyStats(BaseModel):
    total_users: int
    active_users: int
    total_tenders: int
    active_tenders: int
    total_quotes: int
    pending_quotes: int
