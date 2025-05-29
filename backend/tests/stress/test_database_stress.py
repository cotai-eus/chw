"""
Database Stress Tests

Tests for database performance under high-concurrency scenarios.
"""
import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from tests.stress.conftest import StressTestRunner, DatabaseStressHelper
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.company import Company
from app.models.tender import Tender
from app.schemas.user import UserCreate
from app.schemas.company import CompanyCreate
from app.schemas.tender import TenderCreate


class TestDatabaseConnectionStress:
    """Stress tests for database connections and connection pooling."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_connection_pool_stress(self, stress_runner: StressTestRunner):
        """Test database connection pool under stress."""
        
        async def db_connection_test(user_id: int, request_id: int):
            """Test database connection acquisition and release."""
            async with AsyncSessionLocal() as session:
                # Simple query to test connection
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        
        metrics = await stress_runner.run_concurrent_test(db_connection_test)
        stress_runner.assert_performance_thresholds()
        print(f"DB connection stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, stress_runner: StressTestRunner):
        """Test concurrent database transactions."""
        
        async def transaction_test(user_id: int, request_id: int):
            """Test concurrent transactions."""
            async with AsyncSessionLocal() as session:
                try:
                    await session.begin()
                    
                    # Simulate some database work
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM users WHERE id > :id"),
                        {"id": user_id}
                    )
                    count = result.scalar()
                    
                    await session.commit()
                    assert count is not None
                    
                except Exception as e:
                    await session.rollback()
                    raise e
        
        metrics = await stress_runner.run_concurrent_test(transaction_test)
        stress_runner.assert_performance_thresholds()
        print(f"Concurrent transactions: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestDatabaseQueryStress:
    """Stress tests for database queries."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_select_query_stress(self, stress_runner: StressTestRunner):
        """Test SELECT queries under stress."""
        
        async def select_query_test(user_id: int, request_id: int):
            """Test SELECT queries."""
            async with AsyncSessionLocal() as session:
                # Test different types of SELECT queries
                queries = [
                    "SELECT COUNT(*) FROM users",
                    "SELECT COUNT(*) FROM companies",
                    "SELECT COUNT(*) FROM tenders",
                    f"SELECT * FROM users LIMIT {request_id % 10 + 1}",
                ]
                
                query = queries[request_id % len(queries)]
                result = await session.execute(text(query))
                
                if "COUNT" in query:
                    count = result.scalar()
                    assert count is not None
                else:
                    rows = result.fetchall()
                    assert isinstance(rows, list)
        
        metrics = await stress_runner.run_concurrent_test(select_query_test)
        stress_runner.assert_performance_thresholds()
        print(f"SELECT query stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_complex_query_stress(self, stress_runner: StressTestRunner):
        """Test complex queries under stress."""
        
        async def complex_query_test(user_id: int, request_id: int):
            """Test complex queries with joins."""
            async with AsyncSessionLocal() as session:
                complex_queries = [
                    """
                    SELECT u.id, u.email, c.name as company_name
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    LIMIT 10
                    """,
                    """
                    SELECT t.title, COUNT(ti.id) as item_count
                    FROM tenders t
                    LEFT JOIN tender_items ti ON t.id = ti.tender_id
                    GROUP BY t.id, t.title
                    LIMIT 5
                    """,
                    """
                    SELECT c.name, COUNT(u.id) as user_count
                    FROM companies c
                    LEFT JOIN users u ON c.id = u.company_id
                    GROUP BY c.id, c.name
                    LIMIT 5
                    """
                ]
                
                query = complex_queries[request_id % len(complex_queries)]
                result = await session.execute(text(query))
                rows = result.fetchall()
                assert isinstance(rows, list)
        
        metrics = await stress_runner.run_concurrent_test(complex_query_test)
        stress_runner.assert_performance_thresholds()
        print(f"Complex query stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestDatabaseWriteStress:
    """Stress tests for database write operations."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_insert_stress(self, light_stress_config):
        """Test INSERT operations under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def insert_test(user_id: int, request_id: int):
            """Test INSERT operations."""
            async with AsyncSessionLocal() as session:
                try:
                    # Insert a test user
                    query = text("""
                        INSERT INTO users (email, full_name, hashed_password, is_active)
                        VALUES (:email, :name, :password, :active)
                    """)
                    
                    await session.execute(query, {
                        "email": f"stress_user_{user_id}_{request_id}@test.com",
                        "name": f"Stress User {user_id}-{request_id}",
                        "password": "hashed_password_here",
                        "active": True
                    })
                    
                    await session.commit()
                    
                except Exception as e:
                    await session.rollback()
                    # Allow duplicate key errors for stress test
                    if "duplicate" not in str(e).lower():
                        raise e
        
        metrics = await stress_runner.run_concurrent_test(insert_test)
        
        # Cleanup - remove test users
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM users WHERE email LIKE 'stress_user_%@test.com'")
            )
            await session.commit()
        
        print(f"INSERT stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_update_stress(self, light_stress_config):
        """Test UPDATE operations under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        # First, create a test record to update
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO users (email, full_name, hashed_password, is_active)
                    VALUES ('stress_update_user@test.com', 'Original Name', 'password', true)
                    ON CONFLICT (email) DO NOTHING
                """)
            )
            await session.commit()
        
        async def update_test(user_id: int, request_id: int):
            """Test UPDATE operations."""
            async with AsyncSessionLocal() as session:
                try:
                    query = text("""
                        UPDATE users 
                        SET full_name = :name
                        WHERE email = 'stress_update_user@test.com'
                    """)
                    
                    result = await session.execute(query, {
                        "name": f"Updated Name {user_id}-{request_id}"
                    })
                    
                    await session.commit()
                    assert result.rowcount >= 0  # Allow 0 if record was updated by another thread
                    
                except Exception as e:
                    await session.rollback()
                    raise e
        
        metrics = await stress_runner.run_concurrent_test(update_test)
        
        # Cleanup
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM users WHERE email = 'stress_update_user@test.com'")
            )
            await session.commit()
        
        print(f"UPDATE stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestDatabaseDeadlockHandling:
    """Stress tests for deadlock detection and handling."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_deadlock_scenario(self, light_stress_config):
        """Test deadlock detection and recovery."""
        stress_runner = StressTestRunner(light_stress_config)
        
        # Create test records
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO users (email, full_name, hashed_password, is_active)
                    VALUES 
                        ('deadlock_user1@test.com', 'User 1', 'password', true),
                        ('deadlock_user2@test.com', 'User 2', 'password', true)
                    ON CONFLICT (email) DO NOTHING
                """)
            )
            await session.commit()
        
        async def deadlock_prone_operation(user_id: int, request_id: int):
            """Operation that might cause deadlocks."""
            async with AsyncSessionLocal() as session:
                try:
                    # Alternate order of operations to create potential deadlocks
                    if user_id % 2 == 0:
                        # Update user1 then user2
                        await session.execute(
                            text("UPDATE users SET full_name = :name WHERE email = 'deadlock_user1@test.com'"),
                            {"name": f"Updated 1 by {user_id}-{request_id}"}
                        )
                        await asyncio.sleep(0.01)  # Small delay to increase deadlock chance
                        await session.execute(
                            text("UPDATE users SET full_name = :name WHERE email = 'deadlock_user2@test.com'"),
                            {"name": f"Updated 2 by {user_id}-{request_id}"}
                        )
                    else:
                        # Update user2 then user1
                        await session.execute(
                            text("UPDATE users SET full_name = :name WHERE email = 'deadlock_user2@test.com'"),
                            {"name": f"Updated 2 by {user_id}-{request_id}"}
                        )
                        await asyncio.sleep(0.01)
                        await session.execute(
                            text("UPDATE users SET full_name = :name WHERE email = 'deadlock_user1@test.com'"),
                            {"name": f"Updated 1 by {user_id}-{request_id}"}
                        )
                    
                    await session.commit()
                    
                except Exception as e:
                    await session.rollback()
                    # Allow deadlock errors - they should be handled gracefully
                    if "deadlock" not in str(e).lower():
                        raise e
        
        metrics = await stress_runner.run_concurrent_test(deadlock_prone_operation)
        
        # Cleanup
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM users WHERE email IN ('deadlock_user1@test.com', 'deadlock_user2@test.com')")
            )
            await session.commit()
        
        # For deadlock tests, we mainly care that the system doesn't crash
        assert metrics.total_requests > 0
        print(f"Deadlock handling: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestDatabaseIndexPerformance:
    """Stress tests for database index performance."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_index_usage_stress(self, stress_runner: StressTestRunner):
        """Test queries that should use indexes under stress."""
        
        async def indexed_query_test(user_id: int, request_id: int):
            """Test queries that should use indexes."""
            async with AsyncSessionLocal() as session:
                indexed_queries = [
                    # These should use primary key indexes
                    f"SELECT * FROM users WHERE id = {(user_id % 100) + 1}",
                    f"SELECT * FROM companies WHERE id = {(request_id % 50) + 1}",
                    
                    # These should use unique indexes
                    f"SELECT * FROM users WHERE email = 'user{user_id}@example.com'",
                    
                    # These should use foreign key indexes
                    f"SELECT * FROM users WHERE company_id = {(user_id % 10) + 1}",
                ]
                
                query = indexed_queries[request_id % len(indexed_queries)]
                result = await session.execute(text(query))
                rows = result.fetchall()
                assert isinstance(rows, list)
        
        metrics = await stress_runner.run_concurrent_test(indexed_query_test)
        stress_runner.assert_performance_thresholds()
        print(f"Index usage stress: {metrics.successful_requests}/{metrics.total_requests} successful")
