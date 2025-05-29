import uuid
from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserRole(str, Enum):
    MASTER = "MASTER"
    ADMIN = "ADMIN_EMPRESA"
    MANAGER = "MANAGER"
    USER = "USER"
    VIEWER = "VIEWER"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.USER
    avatar_url: Optional[str] = None
    permissions: Optional[Dict[str, List[str]]] = {}


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    company_id: uuid.UUID


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None
    permissions: Optional[Dict[str, List[str]]] = None
    status: Optional[UserStatus] = None
    must_change_password: Optional[bool] = None


class UserInDBBase(UserBase):
    id: uuid.UUID
    company_id: uuid.UUID
    status: UserStatus
    email_verified: bool
    must_change_password: bool
    is_active: bool
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    password_hash: str


# Schemas para login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# Schema de resposta para perfil completo
class UserProfile(BaseModel):
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    birth_date: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
    notification_email: Optional[str] = None

    class Config:
        from_attributes = True


class UserWithProfile(User):
    profile: Optional[UserProfile] = None
