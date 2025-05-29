"""
Tests for database migrations and schema validation.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, List

import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from app.db.base import Base
from app.db.session import get_async_db, engine
from app.models.user import UserModel
from app.models.company import CompanyModel
from app.models.tender import TenderModel
from app.models.quote import QuoteModel
from app.models.user_session import UserSessionModel
from app.models.notification import NotificationModel
from app.core.config import get_settings


class TestDatabaseMigrations:
    """Test database migration functionality."""
    
    @pytest.fixture
    def alembic_config(self):
        """Create Alembic configuration for testing."""
        config = Config("alembic.ini")
        config.set_main_option("script_location", "alembic")
        return config
    
    @pytest.mark.asyncio
    async def test_migration_structure_validity(self, alembic_config):
        """Test that all migrations are structurally valid."""
        script = ScriptDirectory.from_config(alembic_config)
        
        # Get all revision IDs
        revisions = list(script.walk_revisions())
        
        # Verify migrations exist
        assert len(revisions) > 0, "No migrations found"
        
        # Verify each migration has required attributes
        for revision in revisions:
            assert revision.revision is not None
            assert revision.down_revision is not None or revision.is_base
            assert revision.module.upgrade is not None
            assert revision.module.downgrade is not None
    
    @pytest.mark.asyncio
    async def test_migration_chain_integrity(self, alembic_config):
        """Test migration chain integrity."""
        script = ScriptDirectory.from_config(alembic_config)
        
        # Get all revisions
        revisions = list(script.walk_revisions())
        
        # Verify chain integrity
        revision_ids = {rev.revision for rev in revisions}
        
        for revision in revisions:
            if not revision.is_base and revision.down_revision:
                # Verify down_revision exists
                assert revision.down_revision in revision_ids, \
                    f"Down revision {revision.down_revision} not found for {revision.revision}"
    
    @pytest.mark.asyncio
    async def test_database_schema_creation(self, test_db_engine):
        """Test database schema creation from scratch."""
        # Drop all tables
        async with test_db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        async with test_db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Verify all tables exist
        async with test_db_engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )
            
            tables = inspector.get_table_names()
            
            expected_tables = [
                "users", "companies", "tenders", "quotes", 
                "user_sessions", "notifications", "quote_items",
                "company_users", "tender_tags", "files"
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not found"
    
    @pytest.mark.asyncio
    async def test_table_constraints_and_indexes(self, test_db):
        """Test database constraints and indexes."""
        async with test_db.bind.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )
            
            # Test users table constraints
            users_indexes = inspector.get_indexes("users")
            users_pk = inspector.get_pk_constraint("users")
            users_fks = inspector.get_foreign_keys("users")
            
            assert users_pk["constrained_columns"] == ["id"]
            
            # Check unique constraints exist
            unique_columns = []
            for idx in users_indexes:
                if idx.get("unique"):
                    unique_columns.extend(idx["column_names"])
            
            assert "email" in unique_columns
            
            # Test companies table
            companies_pk = inspector.get_pk_constraint("companies")
            assert companies_pk["constrained_columns"] == ["id"]
            
            # Test tenders table foreign keys
            tenders_fks = inspector.get_foreign_keys("tenders")
            fk_columns = [fk["constrained_columns"][0] for fk in tenders_fks]
            
            assert "company_id" in fk_columns
            assert "user_id" in fk_columns
    
    @pytest.mark.asyncio
    async def test_data_types_and_columns(self, test_db):
        """Test column data types and nullable constraints."""
        async with test_db.bind.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )
            
            # Test users table columns
            users_columns = {
                col["name"]: col for col in inspector.get_columns("users")
            }
            
            # Verify critical columns exist with correct types
            assert "id" in users_columns
            assert "email" in users_columns
            assert "hashed_password" in users_columns
            assert "is_active" in users_columns
            assert "created_at" in users_columns
            
            # Check nullable constraints
            assert users_columns["email"]["nullable"] is False
            assert users_columns["hashed_password"]["nullable"] is False
            assert users_columns["is_active"]["nullable"] is False
            
            # Test tenders table columns
            tenders_columns = {
                col["name"]: col for col in inspector.get_columns("tenders")
            }
            
            assert "title" in tenders_columns
            assert "description" in tenders_columns
            assert "budget_range_min" in tenders_columns
            assert "deadline" in tenders_columns
            assert "company_id" in tenders_columns
            
            # Verify non-nullable critical fields
            assert tenders_columns["title"]["nullable"] is False
            assert tenders_columns["company_id"]["nullable"] is False


class TestSchemaValidation:
    """Test schema validation and model integrity."""
    
    @pytest.mark.asyncio
    async def test_model_relationships(self, test_db, test_user, test_company):
        """Test model relationships work correctly."""
        # Create tender linked to user and company
        tender = TenderModel(
            id=uuid4(),
            title="Test Relationship Tender",
            description="Testing relationships",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        await test_db.refresh(tender)
        
        # Test lazy loading relationships
        await test_db.refresh(tender, ["company", "user"])
        
        assert tender.company is not None
        assert tender.company.id == test_company.id
        assert tender.user is not None
        assert tender.user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_cascade_delete_behavior(self, test_db, test_user, test_company):
        """Test cascade delete behavior."""
        # Create tender with quotes
        tender = TenderModel(
            id=uuid4(),
            title="Cascade Test Tender",
            description="Testing cascade deletes",
            requirements=["req1"],
            budget_range_min=5000,
            budget_range_max=15000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Create quote for tender
        quote = QuoteModel(
            id=uuid4(),
            tender_id=tender.id,
            supplier_id=test_user.id,
            total_price=10000,
            currency="USD",
            delivery_time_days=30,
            status="pending"
        )
        test_db.add(quote)
        await test_db.commit()
        
        # Delete tender and verify cascade behavior
        await test_db.delete(tender)
        await test_db.commit()
        
        # Verify quote still exists (no cascade) or is deleted (with cascade)
        # This depends on the actual relationship configuration
        remaining_quote = await test_db.get(QuoteModel, quote.id)
        # Test should verify expected behavior based on your schema design
    
    @pytest.mark.asyncio
    async def test_unique_constraints(self, test_db, test_company):
        """Test unique constraints work correctly."""
        # Create first user
        user1 = UserModel(
            id=uuid4(),
            email="unique@example.com",
            hashed_password="hashed_password",
            full_name="Unique User",
            is_active=True
        )
        test_db.add(user1)
        await test_db.commit()
        
        # Try to create second user with same email
        user2 = UserModel(
            id=uuid4(),
            email="unique@example.com",  # Same email
            hashed_password="hashed_password2",
            full_name="Another User",
            is_active=True
        )
        test_db.add(user2)
        
        # Should raise integrity error
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_check_constraints(self, test_db, test_user, test_company):
        """Test check constraints work correctly."""
        # Test budget range constraints
        with pytest.raises(Exception):
            tender = TenderModel(
                id=uuid4(),
                title="Invalid Budget Tender",
                description="Testing budget constraints",
                requirements=["req1"],
                budget_range_min=20000,  # Min greater than max
                budget_range_max=10000,  # Max less than min
                deadline=datetime.utcnow() + timedelta(days=30),
                category="software",
                company_id=test_company.id,
                user_id=test_user.id
            )
            test_db.add(tender)
            await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_enum_constraints(self, test_db, test_user, test_company):
        """Test enum field constraints."""
        # Test valid enum values
        tender = TenderModel(
            id=uuid4(),
            title="Enum Test Tender",
            description="Testing enum constraints",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",  # Valid category
            status="draft",  # Valid status
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Test invalid enum values would be caught by Pydantic validation
        # before reaching the database
    
    @pytest.mark.asyncio
    async def test_json_field_validation(self, test_db, test_user, test_company):
        """Test JSON field validation and storage."""
        # Create tender with JSON requirements
        requirements_data = [
            "Python development",
            "React frontend",
            "PostgreSQL database"
        ]
        
        tender = TenderModel(
            id=uuid4(),
            title="JSON Field Test",
            description="Testing JSON fields",
            requirements=requirements_data,
            budget_range_min=15000,
            budget_range_max=25000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        await test_db.refresh(tender)
        
        # Verify JSON data integrity
        assert tender.requirements == requirements_data
        assert len(tender.requirements) == 3
        assert "Python development" in tender.requirements


class TestDataIntegrity:
    """Test data integrity and validation."""
    
    @pytest.mark.asyncio
    async def test_timestamp_fields(self, test_db, test_user, test_company):
        """Test timestamp fields are set correctly."""
        before_creation = datetime.utcnow()
        
        tender = TenderModel(
            id=uuid4(),
            title="Timestamp Test",
            description="Testing timestamps",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        await test_db.refresh(tender)
        
        after_creation = datetime.utcnow()
        
        # Verify timestamps
        assert tender.created_at is not None
        assert before_creation <= tender.created_at <= after_creation
        assert tender.updated_at is not None
        
        # Test update timestamp
        original_updated = tender.updated_at
        await asyncio.sleep(0.1)  # Small delay
        
        tender.title = "Updated Timestamp Test"
        await test_db.commit()
        await test_db.refresh(tender)
        
        assert tender.updated_at > original_updated
    
    @pytest.mark.asyncio
    async def test_soft_delete_functionality(self, test_db, test_user):
        """Test soft delete functionality if implemented."""
        # Create user session
        session = UserSessionModel(
            id=uuid4(),
            user_id=test_user.id,
            session_token="test_session_token",
            device_fingerprint="test_device",
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            last_activity=datetime.utcnow()
        )
        test_db.add(session)
        await test_db.commit()
        
        # Soft delete (deactivate)
        session.is_active = False
        await test_db.commit()
        
        # Verify soft delete
        await test_db.refresh(session)
        assert session.is_active is False
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_tables(self, test_db, test_user, test_company):
        """Test data consistency across related tables."""
        # Create tender
        tender = TenderModel(
            id=uuid4(),
            title="Consistency Test",
            description="Testing data consistency",
            requirements=["req1"],
            budget_range_min=10000,
            budget_range_max=20000,
            deadline=datetime.utcnow() + timedelta(days=30),
            category="software",
            company_id=test_company.id,
            user_id=test_user.id
        )
        test_db.add(tender)
        await test_db.commit()
        
        # Create multiple quotes
        quotes = []
        for i in range(3):
            quote = QuoteModel(
                id=uuid4(),
                tender_id=tender.id,
                supplier_id=test_user.id,
                total_price=12000 + (i * 1000),
                currency="USD",
                delivery_time_days=30 + (i * 5),
                status="pending"
            )
            quotes.append(quote)
            test_db.add(quote)
        
        await test_db.commit()
        
        # Verify consistency
        for quote in quotes:
            await test_db.refresh(quote)
            assert quote.tender_id == tender.id
            assert quote.supplier_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, test_db, test_user, test_company):
        """Test transaction rollback behavior."""
        initial_count = await test_db.scalar(
            text("SELECT COUNT(*) FROM tenders")
        )
        
        try:
            # Start transaction that will fail
            tender = TenderModel(
                id=uuid4(),
                title="Transaction Test",
                description="Testing transactions",
                requirements=["req1"],
                budget_range_min=10000,
                budget_range_max=20000,
                deadline=datetime.utcnow() + timedelta(days=30),
                category="software",
                company_id=test_company.id,
                user_id=test_user.id
            )
            test_db.add(tender)
            
            # Force an error (e.g., constraint violation)
            duplicate_tender = TenderModel(
                id=tender.id,  # Same ID will cause error
                title="Duplicate ID Test",
                description="This should fail",
                requirements=["req1"],
                budget_range_min=5000,
                budget_range_max=15000,
                deadline=datetime.utcnow() + timedelta(days=30),
                category="software",
                company_id=test_company.id,
                user_id=test_user.id
            )
            test_db.add(duplicate_tender)
            
            await test_db.commit()
        except Exception:
            await test_db.rollback()
        
        # Verify rollback worked
        final_count = await test_db.scalar(
            text("SELECT COUNT(*) FROM tenders")
        )
        assert final_count == initial_count


class TestPerformanceAndOptimization:
    """Test database performance and optimization."""
    
    @pytest.mark.asyncio
    async def test_index_effectiveness(self, test_db, test_user, test_company):
        """Test that indexes improve query performance."""
        # Create multiple tenders for testing
        tenders = []
        for i in range(50):
            tender = TenderModel(
                id=uuid4(),
                title=f"Performance Test Tender {i}",
                description=f"Description {i}",
                requirements=[f"req{i}"],
                budget_range_min=10000 + (i * 100),
                budget_range_max=20000 + (i * 100),
                deadline=datetime.utcnow() + timedelta(days=30 + i),
                category="software",
                company_id=test_company.id,
                user_id=test_user.id
            )
            tenders.append(tender)
            test_db.add(tender)
        
        await test_db.commit()
        
        # Test indexed query performance
        start_time = asyncio.get_event_loop().time()
        
        # Query by company_id (should be indexed)
        result = await test_db.execute(
            text("SELECT * FROM tenders WHERE company_id = :company_id"),
            {"company_id": str(test_company.id)}
        )
        tenders_found = result.fetchall()
        
        end_time = asyncio.get_event_loop().time()
        query_time = end_time - start_time
        
        # Should be fast due to index
        assert query_time < 1.0
        assert len(tenders_found) == 50
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, test_db, test_user, test_company):
        """Test bulk operations performance."""
        # Prepare bulk data
        tenders_data = []
        for i in range(100):
            tender = TenderModel(
                id=uuid4(),
                title=f"Bulk Test Tender {i}",
                description=f"Bulk description {i}",
                requirements=[f"bulk_req{i}"],
                budget_range_min=5000,
                budget_range_max=15000,
                deadline=datetime.utcnow() + timedelta(days=30),
                category="software",
                company_id=test_company.id,
                user_id=test_user.id
            )
            tenders_data.append(tender)
        
        # Test bulk insert performance
        start_time = asyncio.get_event_loop().time()
        
        test_db.add_all(tenders_data)
        await test_db.commit()
        
        end_time = asyncio.get_event_loop().time()
        bulk_time = end_time - start_time
        
        # Bulk operations should be efficient
        assert bulk_time < 5.0
        
        # Verify all records inserted
        count = await test_db.scalar(
            text("SELECT COUNT(*) FROM tenders WHERE title LIKE 'Bulk Test Tender%'")
        )
        assert count == 100
    
    @pytest.mark.asyncio
    async def test_connection_pool_behavior(self):
        """Test database connection pool behavior."""
        # Test multiple concurrent connections
        tasks = []
        
        async def query_task():
            async with get_async_db() as db:
                result = await db.execute(text("SELECT 1"))
                return result.scalar()
        
        # Create multiple concurrent tasks
        for _ in range(10):
            tasks.append(query_task())
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # All tasks should complete successfully
        assert all(result == 1 for result in results)
        assert end_time - start_time < 2.0  # Should handle concurrency well
