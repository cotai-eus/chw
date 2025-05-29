"""
Test configuration and fixtures for the tender platform backend.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import asyncpg
import motor.motor_asyncio
import redis.asyncio as aioredis
from unittest.mock import AsyncMock, MagicMock

from main_simple import app
# Simplified imports for testing
# from app.core.config import settings
# from app.db.session import get_db, get_mongo_db, get_redis
# from app.db.base_class import Base
# from app.db.models.user import User
# from app.db.models.company import Company
# from app.db.models.tender import Tender
# from app.db.models.supplier import Supplier
# from app.db.models.quote import Quote
# from app.core.security import create_access_token
# from app.schemas.user import UserCreate
# from app.schemas.company import CompanyCreate

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def mock_mongo_db():
    """Mock MongoDB database for testing."""
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_db.__getattr__.return_value = mock_collection
    return mock_db


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()
    return mock_redis


@pytest.fixture
def client(db_session: AsyncSession, mock_mongo_db, mock_redis) -> Generator[TestClient, None, None]:
    """Create a test client with overridden dependencies."""
    
    def override_get_db():
        return db_session
    
    def override_get_mongo_db():
        return mock_mongo_db
    
    def override_get_redis():
        return mock_redis
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_mongo_db] = override_get_mongo_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_company(db_session: AsyncSession) -> Company:
    """Create a test company."""
    company_data = CompanyCreate(
        name="Test Company",
        cnpj="12345678000199",
        email="test@company.com",
        phone="11999999999",
        address="Test Address, 123",
        city="Test City",
        state="SP",
        zip_code="12345-678"
    )
    
    company = Company(**company_data.dict())
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_company: Company) -> User:
    """Create a test user."""
    from app.core.security import get_password_hash
    
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword",
        full_name="Test User",
        role="user"
    )
    
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        company_id=test_company.id,
        is_active=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, test_company: Company) -> User:
    """Create a test admin user."""
    from app.core.security import get_password_hash
    
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        full_name="Admin User",
        role="admin",
        company_id=test_company.id,
        is_active=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create an access token for the test user."""
    return create_access_token(subject=test_user.id)


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create an access token for the admin user."""
    return create_access_token(subject=admin_user.id)


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """Create authorization headers for the test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Create authorization headers for the admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def test_tender(db_session: AsyncSession, test_company: Company) -> Tender:
    """Create a test tender."""
    tender = Tender(
        title="Test Tender",
        description="Test tender description",
        submission_deadline="2024-12-31T23:59:59",
        company_id=test_company.id,
        status="open",
        budget=100000.0
    )
    
    db_session.add(tender)
    await db_session.commit()
    await db_session.refresh(tender)
    return tender


@pytest_asyncio.fixture
async def test_supplier(db_session: AsyncSession, test_company: Company) -> Supplier:
    """Create a test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        cnpj="98765432000199",
        email="supplier@test.com",
        phone="11888888888",
        address="Supplier Address, 456",
        city="Supplier City",
        state="RJ",
        zip_code="87654-321",
        company_id=test_company.id
    )
    
    db_session.add(supplier)
    await db_session.commit()
    await db_session.refresh(supplier)
    return supplier


@pytest_asyncio.fixture
async def test_quote(
    db_session: AsyncSession, 
    test_tender: Tender, 
    test_supplier: Supplier
) -> Quote:
    """Create a test quote."""
    quote = Quote(
        tender_id=test_tender.id,
        supplier_id=test_supplier.id,
        total_value=50000.0,
        status="pending",
        valid_until="2024-12-30T23:59:59"
    )
    
    db_session.add(quote)
    await db_session.commit()
    await db_session.refresh(quote)
    return quote


# Mock external services
@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    mock_service = MagicMock()
    mock_service.process_document.return_value = {
        "status": "completed",
        "extracted_text": "Test extracted text",
        "analysis": {"risk_score": 0.3, "confidence": 0.9}
    }
    return mock_service


@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    mock_service = MagicMock()
    mock_service.send_email.return_value = True
    return mock_service


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    mock_task = MagicMock()
    mock_task.delay.return_value.id = "test-task-id"
    mock_task.delay.return_value.status = "PENDING"
    return mock_task


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def company_create_data(overrides: dict = None) -> dict:
        """Create company creation data."""
        data = {
            "name": "Test Company",
            "cnpj": "12345678000199",
            "email": "test@company.com",
            "phone": "11999999999",
            "address": "Test Address, 123",
            "city": "Test City",
            "state": "SP",
            "zip_code": "12345-678"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def user_create_data(overrides: dict = None) -> dict:
        """Create user creation data."""
        data = {
            "email": "test@example.com",
            "password": "testpassword",
            "full_name": "Test User",
            "role": "user"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def tender_create_data(overrides: dict = None) -> dict:
        """Create tender creation data."""
        data = {
            "title": "Test Tender",
            "description": "Test tender description",
            "submission_deadline": "2024-12-31T23:59:59",
            "status": "open",
            "budget": 100000.0
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def supplier_create_data(overrides: dict = None) -> dict:
        """Create supplier creation data."""
        data = {
            "name": "Test Supplier",
            "cnpj": "98765432000199",
            "email": "supplier@test.com",
            "phone": "11888888888",
            "address": "Supplier Address, 456",
            "city": "Supplier City",
            "state": "RJ",
            "zip_code": "87654-321"
        }
        if overrides:
            data.update(overrides)
        return data


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
