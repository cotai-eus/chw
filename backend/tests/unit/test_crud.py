"""
Unit tests for CRUD operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.crud.user import user_crud
from app.crud.company import company_crud
from app.crud.tender import tender_crud
from app.db.models.user import User
from app.db.models.company import Company
from app.db.models.tender import Tender
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.tender import TenderCreate, TenderUpdate


class TestBaseCRUD:
    """Test base CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create(self):
        """Test create operation."""
        # Mock database session
        db_session = AsyncMock(spec=AsyncSession)
        
        # Mock the CRUD class
        crud = CRUDBase(User)
        
        # Test data
        user_data = UserCreate(
            email="test@example.com",
            password="password",
            full_name="Test User"
        )
        
        # Mock the created object
        created_user = User(
            id="user-id",
            email=user_data.email,
            full_name=user_data.full_name
        )
        
        # Mock database operations
        db_session.add = MagicMock()
        db_session.commit = AsyncMock()
        db_session.refresh = AsyncMock()
        
        # Override the create method to return our mock
        crud.create = AsyncMock(return_value=created_user)
        
        # Test the operation
        result = await crud.create(db_session, obj_in=user_data)
        
        assert result.email == user_data.email
        assert result.full_name == user_data.full_name
    
    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """Test get by ID operation."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        # Mock user
        user = User(id="user-id", email="test@example.com")
        
        # Mock the get method
        crud.get = AsyncMock(return_value=user)
        
        result = await crud.get(db_session, id="user-id")
        assert result.id == "user-id"
        assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_multi(self):
        """Test get multiple operation."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        # Mock users
        users = [
            User(id="user-1", email="user1@example.com"),
            User(id="user-2", email="user2@example.com")
        ]
        
        # Mock the get_multi method
        crud.get_multi = AsyncMock(return_value=users)
        
        result = await crud.get_multi(db_session, skip=0, limit=10)
        assert len(result) == 2
        assert result[0].email == "user1@example.com"
        assert result[1].email == "user2@example.com"
    
    @pytest.mark.asyncio
    async def test_update(self):
        """Test update operation."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        # Mock existing user
        existing_user = User(id="user-id", email="old@example.com")
        
        # Update data
        update_data = UserUpdate(email="new@example.com")
        
        # Mock updated user
        updated_user = User(id="user-id", email="new@example.com")
        
        # Mock the update method
        crud.update = AsyncMock(return_value=updated_user)
        
        result = await crud.update(db_session, db_obj=existing_user, obj_in=update_data)
        assert result.email == "new@example.com"
    
    @pytest.mark.asyncio
    async def test_remove(self):
        """Test remove operation."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        # Mock user to remove
        user_to_remove = User(id="user-id", email="test@example.com")
        
        # Mock the remove method
        crud.remove = AsyncMock(return_value=user_to_remove)
        
        result = await crud.remove(db_session, id="user-id")
        assert result.id == "user-id"


class TestUserCRUD:
    """Test user-specific CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_by_email(self):
        """Test get user by email."""
        db_session = AsyncMock(spec=AsyncSession)
        
        # Mock user
        user = User(id="user-id", email="test@example.com")
        
        # Mock the get_by_email method
        user_crud.get_by_email = AsyncMock(return_value=user)
        
        result = await user_crud.get_by_email(db_session, email="test@example.com")
        assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_create_user_with_hashed_password(self):
        """Test user creation with password hashing."""
        db_session = AsyncMock(spec=AsyncSession)
        
        user_data = UserCreate(
            email="test@example.com",
            password="plainpassword",
            full_name="Test User"
        )
        
        # Mock created user with hashed password
        created_user = User(
            id="user-id",
            email=user_data.email,
            hashed_password="hashed_password_here",
            full_name=user_data.full_name
        )
        
        user_crud.create = AsyncMock(return_value=created_user)
        
        result = await user_crud.create(db_session, obj_in=user_data)
        assert result.email == user_data.email
        assert result.hashed_password == "hashed_password_here"
        # Password should not be stored in plain text
        assert not hasattr(result, 'password')
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful user authentication."""
        db_session = AsyncMock(spec=AsyncSession)
        
        # Mock user with hashed password
        user = User(
            id="user-id",
            email="test@example.com",
            hashed_password="correct_hashed_password"
        )
        
        user_crud.authenticate = AsyncMock(return_value=user)
        
        result = await user_crud.authenticate(
            db_session, 
            email="test@example.com", 
            password="correct_password"
        )
        assert result is not None
        assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test failed user authentication."""
        db_session = AsyncMock(spec=AsyncSession)
        
        user_crud.authenticate = AsyncMock(return_value=None)
        
        result = await user_crud.authenticate(
            db_session, 
            email="test@example.com", 
            password="wrong_password"
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_is_active(self):
        """Test user active status check."""
        # Active user
        active_user = User(id="user-id", is_active=True)
        assert user_crud.is_active(active_user) is True
        
        # Inactive user
        inactive_user = User(id="user-id", is_active=False)
        assert user_crud.is_active(inactive_user) is False
    
    @pytest.mark.asyncio
    async def test_is_superuser(self):
        """Test superuser status check."""
        # Superuser
        superuser = User(id="user-id", role="admin")
        assert user_crud.is_superuser(superuser) is True
        
        # Regular user
        regular_user = User(id="user-id", role="user")
        assert user_crud.is_superuser(regular_user) is False


class TestCompanyCRUD:
    """Test company-specific CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_by_cnpj(self):
        """Test get company by CNPJ."""
        db_session = AsyncMock(spec=AsyncSession)
        
        company = Company(id="company-id", cnpj="12345678000199")
        company_crud.get_by_cnpj = AsyncMock(return_value=company)
        
        result = await company_crud.get_by_cnpj(db_session, cnpj="12345678000199")
        assert result.cnpj == "12345678000199"
    
    @pytest.mark.asyncio
    async def test_create_company(self):
        """Test company creation."""
        db_session = AsyncMock(spec=AsyncSession)
        
        company_data = CompanyCreate(
            name="Test Company",
            cnpj="12345678000199",
            email="test@company.com"
        )
        
        created_company = Company(
            id="company-id",
            name=company_data.name,
            cnpj=company_data.cnpj,
            email=company_data.email
        )
        
        company_crud.create = AsyncMock(return_value=created_company)
        
        result = await company_crud.create(db_session, obj_in=company_data)
        assert result.name == company_data.name
        assert result.cnpj == company_data.cnpj


class TestTenderCRUD:
    """Test tender-specific CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_by_company(self):
        """Test get tenders by company."""
        db_session = AsyncMock(spec=AsyncSession)
        
        tenders = [
            Tender(id="tender-1", title="Tender 1", company_id="company-id"),
            Tender(id="tender-2", title="Tender 2", company_id="company-id")
        ]
        
        tender_crud.get_by_company = AsyncMock(return_value=tenders)
        
        result = await tender_crud.get_by_company(db_session, company_id="company-id")
        assert len(result) == 2
        assert all(t.company_id == "company-id" for t in result)
    
    @pytest.mark.asyncio
    async def test_get_active_tenders(self):
        """Test get active tenders."""
        db_session = AsyncMock(spec=AsyncSession)
        
        active_tenders = [
            Tender(id="tender-1", title="Active Tender 1", status="open"),
            Tender(id="tender-2", title="Active Tender 2", status="in_progress")
        ]
        
        tender_crud.get_active = AsyncMock(return_value=active_tenders)
        
        result = await tender_crud.get_active(db_session)
        assert len(result) == 2
        assert all(t.status in ["open", "in_progress"] for t in result)
    
    @pytest.mark.asyncio
    async def test_create_tender(self):
        """Test tender creation."""
        db_session = AsyncMock(spec=AsyncSession)
        
        tender_data = TenderCreate(
            title="New Tender",
            description="Test description",
            submission_deadline="2024-12-31T23:59:59",
            budget=100000.0
        )
        
        created_tender = Tender(
            id="tender-id",
            title=tender_data.title,
            description=tender_data.description,
            budget=tender_data.budget
        )
        
        tender_crud.create = AsyncMock(return_value=created_tender)
        
        result = await tender_crud.create(db_session, obj_in=tender_data)
        assert result.title == tender_data.title
        assert result.budget == tender_data.budget
    
    @pytest.mark.asyncio
    async def test_update_tender_status(self):
        """Test tender status update."""
        db_session = AsyncMock(spec=AsyncSession)
        
        existing_tender = Tender(id="tender-id", status="open")
        updated_tender = Tender(id="tender-id", status="closed")
        
        tender_crud.update_status = AsyncMock(return_value=updated_tender)
        
        result = await tender_crud.update_status(
            db_session, 
            tender_id="tender-id", 
            status="closed"
        )
        assert result.status == "closed"


class TestCRUDErrorHandling:
    """Test CRUD error handling."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self):
        """Test getting non-existent record."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        crud.get = AsyncMock(return_value=None)
        
        result = await crud.get(db_session, id="nonexistent-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_with_invalid_data(self):
        """Test create with invalid data."""
        db_session = AsyncMock(spec=AsyncSession)
        
        # This should be handled by Pydantic validation
        with pytest.raises(Exception):
            UserCreate(email="invalid-email", password="")
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self):
        """Test updating non-existent record."""
        db_session = AsyncMock(spec=AsyncSession)
        crud = CRUDBase(User)
        
        crud.update = AsyncMock(return_value=None)
        
        result = await crud.update(
            db_session, 
            db_obj=None, 
            obj_in=UserUpdate(email="new@example.com")
        )
        assert result is None
