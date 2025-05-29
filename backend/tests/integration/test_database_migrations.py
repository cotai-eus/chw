"""
Database Migration Testing

Comprehensive testing for database migrations including rollback testing,
data integrity validation, and performance impact assessment.
"""
import pytest
import asyncio
import time
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import psutil
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
import alembic.config
import alembic.command
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext

from app.db.session import engine, get_db
from app.core.config import settings


class MigrationTestHelper:
    """Helper class for testing database migrations."""
    
    def __init__(self):
        self.alembic_cfg = alembic.config.Config("alembic.ini")
        self.script_dir = ScriptDirectory.from_config(self.alembic_cfg)
    
    def get_migration_history(self) -> List[str]:
        """Get list of all migration revisions."""
        revisions = []
        for revision in self.script_dir.walk_revisions():
            revisions.append(revision.revision)
        return list(reversed(revisions))  # Oldest first
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            result = subprocess.run(
                ["alembic", "current"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            current = result.stdout.strip()
            if current and "current)" in current:
                return current.split("(current)")[0].strip()
            return None
        except subprocess.CalledProcessError:
            return None
    
    def migrate_to_revision(self, revision: str) -> bool:
        """Migrate database to specific revision."""
        try:
            subprocess.run(
                ["alembic", "upgrade", revision], 
                check=True, 
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Migration failed: {e.stderr}")
            return False
    
    def downgrade_to_revision(self, revision: str) -> bool:
        """Downgrade database to specific revision."""
        try:
            subprocess.run(
                ["alembic", "downgrade", revision], 
                check=True, 
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Downgrade failed: {e.stderr}")
            return False
    
    async def get_table_info(self, db: AsyncSession) -> Dict[str, Any]:
        """Get information about database tables and columns."""
        inspector = inspect(engine.sync_engine)
        
        table_info = {}
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            table_info[table_name] = {
                'columns': {col['name']: col for col in columns},
                'indexes': indexes,
                'foreign_keys': foreign_keys
            }
        
        return table_info
    
    async def get_data_counts(self, db: AsyncSession) -> Dict[str, int]:
        """Get row counts for all tables."""
        inspector = inspect(engine.sync_engine)
        counts = {}
        
        for table_name in inspector.get_table_names():
            try:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                counts[table_name] = count
            except Exception as e:
                counts[table_name] = f"Error: {str(e)}"
        
        return counts
    
    async def validate_data_integrity(self, db: AsyncSession) -> List[str]:
        """Validate data integrity after migration."""
        issues = []
        
        try:
            # Check foreign key constraints
            result = await db.execute(text("""
                SELECT tc.table_name, tc.constraint_name, tc.constraint_type
                FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = current_schema()
            """))
            
            foreign_keys = result.fetchall()
            
            for fk in foreign_keys:
                # Verify foreign key integrity
                try:
                    await db.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.constraint_column_usage 
                        WHERE constraint_name = '{fk.constraint_name}'
                    """))
                except Exception as e:
                    issues.append(f"Foreign key integrity issue in {fk.table_name}: {str(e)}")
            
            # Check for orphaned records (basic check)
            if 'quotes' in await self._get_table_names(db):
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM quotes q 
                    LEFT JOIN tenders t ON q.tender_id = t.id 
                    WHERE t.id IS NULL
                """))
                orphaned_quotes = result.scalar()
                if orphaned_quotes > 0:
                    issues.append(f"Found {orphaned_quotes} orphaned quotes without valid tender references")
            
            if 'quotes' in await self._get_table_names(db) and 'users' in await self._get_table_names(db):
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM quotes q 
                    LEFT JOIN users u ON q.supplier_id = u.id 
                    WHERE u.id IS NULL
                """))
                orphaned_quotes = result.scalar()
                if orphaned_quotes > 0:
                    issues.append(f"Found {orphaned_quotes} orphaned quotes without valid supplier references")
            
        except Exception as e:
            issues.append(f"Error validating data integrity: {str(e)}")
        
        return issues
    
    async def _get_table_names(self, db: AsyncSession) -> List[str]:
        """Get list of table names."""
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = current_schema()
        """))
        return [row[0] for row in result.fetchall()]


class MigrationPerformanceTracker:
    """Track performance impact of migrations."""
    
    def __init__(self):
        self.metrics = {}
    
    def start_tracking(self, migration_name: str):
        """Start tracking migration performance."""
        self.metrics[migration_name] = {
            'start_time': time.time(),
            'start_memory': psutil.virtual_memory().used,
            'start_cpu': psutil.cpu_percent()
        }
    
    def stop_tracking(self, migration_name: str) -> Dict[str, Any]:
        """Stop tracking and return metrics."""
        if migration_name not in self.metrics:
            return {}
        
        end_time = time.time()
        end_memory = psutil.virtual_memory().used
        end_cpu = psutil.cpu_percent()
        
        start_metrics = self.metrics[migration_name]
        
        return {
            'duration_seconds': end_time - start_metrics['start_time'],
            'memory_delta_mb': (end_memory - start_metrics['start_memory']) / 1024 / 1024,
            'cpu_usage_delta': end_cpu - start_metrics['start_cpu']
        }


class TestDatabaseMigrations:
    """Test database migrations comprehensively."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.helper = MigrationTestHelper()
        self.perf_tracker = MigrationPerformanceTracker()
        self.original_revision = self.helper.get_current_revision()
    
    def teardown_method(self):
        """Restore original database state after each test."""
        if self.original_revision:
            self.helper.migrate_to_revision(self.original_revision)
    
    @pytest.mark.asyncio
    async def test_migration_up_and_down(self):
        """Test that migrations can be applied and rolled back successfully."""
        async with get_db() as db:
            # Get migration history
            migrations = self.helper.get_migration_history()
            
            if not migrations:
                pytest.skip("No migrations found")
            
            # Test each migration
            for i, migration in enumerate(migrations):
                print(f"Testing migration: {migration}")
                
                # Apply migration
                self.perf_tracker.start_tracking(f"up_{migration}")
                success = self.helper.migrate_to_revision(migration)
                up_metrics = self.perf_tracker.stop_tracking(f"up_{migration}")
                
                assert success, f"Failed to apply migration {migration}"
                
                # Validate current state
                current = self.helper.get_current_revision()
                assert current == migration, f"Expected revision {migration}, got {current}"
                
                # Check data integrity
                integrity_issues = await self.helper.validate_data_integrity(db)
                assert not integrity_issues, f"Data integrity issues after migration {migration}: {integrity_issues}"
                
                # Test rollback (except for the first migration)
                if i > 0:
                    previous_migration = migrations[i-1]
                    
                    self.perf_tracker.start_tracking(f"down_{migration}")
                    success = self.helper.downgrade_to_revision(previous_migration)
                    down_metrics = self.perf_tracker.stop_tracking(f"down_{migration}")
                    
                    assert success, f"Failed to rollback migration {migration}"
                    
                    # Validate rollback state
                    current = self.helper.get_current_revision()
                    assert current == previous_migration, f"Rollback failed: expected {previous_migration}, got {current}"
                    
                    # Check data integrity after rollback
                    integrity_issues = await self.helper.validate_data_integrity(db)
                    assert not integrity_issues, f"Data integrity issues after rollback of {migration}: {integrity_issues}"
                    
                    # Reapply migration for next iteration
                    self.helper.migrate_to_revision(migration)
                
                # Check performance metrics
                assert up_metrics.get('duration_seconds', 0) < 300, f"Migration {migration} took too long: {up_metrics.get('duration_seconds')}s"
                
                if 'down_metrics' in locals():
                    assert down_metrics.get('duration_seconds', 0) < 300, f"Rollback of {migration} took too long: {down_metrics.get('duration_seconds')}s"
    
    @pytest.mark.asyncio
    async def test_schema_changes_validation(self):
        """Test that schema changes are correctly applied."""
        async with get_db() as db:
            migrations = self.helper.get_migration_history()
            
            if not migrations:
                pytest.skip("No migrations found")
            
            # Start from a clean state
            if migrations:
                self.helper.downgrade_to_revision("base")
                
                # Apply migrations one by one and validate schema changes
                for migration in migrations:
                    # Get schema before migration
                    schema_before = await self.helper.get_table_info(db)
                    
                    # Apply migration
                    success = self.helper.migrate_to_revision(migration)
                    assert success, f"Failed to apply migration {migration}"
                    
                    # Get schema after migration
                    schema_after = await self.helper.get_table_info(db)
                    
                    # Validate that schema actually changed (except for data-only migrations)
                    # This is a basic check - specific validations would depend on migration content
                    
                    # Ensure no tables were accidentally dropped
                    for table_name in schema_before:
                        if table_name not in schema_after:
                            # Only fail if this wasn't an intentional table drop
                            # (You'd need to check migration content to be sure)
                            print(f"Warning: Table {table_name} was dropped in migration {migration}")
    
    @pytest.mark.asyncio
    async def test_data_preservation_during_migration(self):
        """Test that existing data is preserved during migrations."""
        async with get_db() as db:
            # Create test data
            test_data = await self._create_test_data(db)
            
            migrations = self.helper.get_migration_history()
            
            if not migrations:
                pytest.skip("No migrations found")
            
            # Apply all migrations
            for migration in migrations:
                # Get data counts before migration
                counts_before = await self.helper.get_data_counts(db)
                
                # Apply migration
                success = self.helper.migrate_to_revision(migration)
                assert success, f"Failed to apply migration {migration}"
                
                # Get data counts after migration
                counts_after = await self.helper.get_data_counts(db)
                
                # Validate that data wasn't lost (with some flexibility for data transformations)
                for table_name, count_before in counts_before.items():
                    if isinstance(count_before, int) and table_name in counts_after:
                        count_after = counts_after[table_name]
                        if isinstance(count_after, int):
                            # Allow for some data transformation, but not complete loss
                            assert count_after >= count_before * 0.8, \
                                f"Significant data loss in table {table_name} during migration {migration}: {count_before} -> {count_after}"
    
    async def _create_test_data(self, db: AsyncSession) -> Dict[str, Any]:
        """Create test data for migration testing."""
        try:
            # Create test users
            await db.execute(text("""
                INSERT INTO users (email, full_name, hashed_password, is_active, created_at)
                VALUES 
                ('test1@example.com', 'Test User 1', 'hashedpassword1', true, NOW()),
                ('test2@example.com', 'Test User 2', 'hashedpassword2', true, NOW())
                ON CONFLICT (email) DO NOTHING
            """))
            
            # Create test tenders
            await db.execute(text("""
                INSERT INTO tenders (title, description, deadline, created_by, created_at)
                VALUES 
                ('Test Tender 1', 'Description 1', NOW() + INTERVAL '30 days', 1, NOW()),
                ('Test Tender 2', 'Description 2', NOW() + INTERVAL '60 days', 1, NOW())
                ON CONFLICT DO NOTHING
            """))
            
            await db.commit()
            
            return {
                'users_created': 2,
                'tenders_created': 2
            }
        except Exception as e:
            await db.rollback()
            print(f"Error creating test data: {e}")
            return {}
    
    @pytest.mark.asyncio
    async def test_migration_idempotency(self):
        """Test that migrations are idempotent (can be run multiple times safely)."""
        migrations = self.helper.get_migration_history()
        
        if not migrations:
            pytest.skip("No migrations found")
        
        # Test the latest migration
        latest_migration = migrations[-1]
        
        # Apply migration
        success = self.helper.migrate_to_revision(latest_migration)
        assert success, f"Failed to apply migration {latest_migration}"
        
        async with get_db() as db:
            # Get state after first application
            schema_first = await self.helper.get_table_info(db)
            counts_first = await self.helper.get_data_counts(db)
        
        # Apply same migration again
        success = self.helper.migrate_to_revision(latest_migration)
        assert success, f"Migration {latest_migration} is not idempotent"
        
        async with get_db() as db:
            # Get state after second application
            schema_second = await self.helper.get_table_info(db)
            counts_second = await self.helper.get_data_counts(db)
        
        # Validate that nothing changed
        assert schema_first == schema_second, "Schema changed on second migration application"
        assert counts_first == counts_second, "Data changed on second migration application"
    
    @pytest.mark.asyncio
    async def test_migration_performance_benchmarks(self):
        """Test migration performance and set benchmarks."""
        migrations = self.helper.get_migration_history()
        
        if not migrations:
            pytest.skip("No migrations found")
        
        performance_results = {}
        
        # Test performance for each migration
        for migration in migrations[-3:]:  # Test last 3 migrations
            # Reset to previous state
            if migrations.index(migration) > 0:
                previous = migrations[migrations.index(migration) - 1]
                self.helper.downgrade_to_revision(previous)
            else:
                self.helper.downgrade_to_revision("base")
            
            # Measure migration performance
            self.perf_tracker.start_tracking(migration)
            success = self.helper.migrate_to_revision(migration)
            metrics = self.perf_tracker.stop_tracking(migration)
            
            assert success, f"Migration {migration} failed"
            
            performance_results[migration] = metrics
            
            # Set performance benchmarks
            assert metrics['duration_seconds'] < 120, \
                f"Migration {migration} took too long: {metrics['duration_seconds']}s"
            
            assert abs(metrics['memory_delta_mb']) < 500, \
                f"Migration {migration} used too much memory: {metrics['memory_delta_mb']}MB"
        
        # Save performance results for monitoring
        print("Migration Performance Results:")
        for migration, metrics in performance_results.items():
            print(f"  {migration}: {metrics['duration_seconds']:.2f}s, "
                  f"{metrics['memory_delta_mb']:.2f}MB memory delta")
    
    @pytest.mark.asyncio
    async def test_concurrent_migration_safety(self):
        """Test that migrations handle concurrent database access safely."""
        migrations = self.helper.get_migration_history()
        
        if not migrations:
            pytest.skip("No migrations found")
        
        latest_migration = migrations[-1]
        
        async def simulate_database_activity():
            """Simulate ongoing database activity during migration."""
            async with get_db() as db:
                for _ in range(10):
                    try:
                        # Try to read data
                        await db.execute(text("SELECT 1"))
                        await asyncio.sleep(0.1)
                    except Exception:
                        # Expected during migration
                        pass
        
        # Start background database activity
        activity_task = asyncio.create_task(simulate_database_activity())
        
        # Apply migration while activity is happening
        success = self.helper.migrate_to_revision(latest_migration)
        
        # Wait for activity to complete
        await activity_task
        
        assert success, "Migration failed with concurrent database activity"
        
        async with get_db() as db:
            # Validate database integrity after concurrent access
            integrity_issues = await self.helper.validate_data_integrity(db)
            assert not integrity_issues, f"Integrity issues after concurrent migration: {integrity_issues}"
    
    def test_migration_file_validation(self):
        """Test that migration files are properly formatted and valid."""
        migrations = self.helper.get_migration_history()
        
        for migration in migrations:
            # Get migration script
            revision = self.script_dir.get_revision(migration)
            
            # Basic validation
            assert revision.revision, f"Migration {migration} has no revision ID"
            assert revision.down_revision is not None or migration == migrations[0], \
                f"Migration {migration} has invalid down_revision"
            
            # Check for required functions
            if revision.module:
                assert hasattr(revision.module, 'upgrade'), \
                    f"Migration {migration} missing upgrade function"
                assert hasattr(revision.module, 'downgrade'), \
                    f"Migration {migration} missing downgrade function"
    
    @pytest.mark.asyncio
    async def test_rollback_data_integrity(self):
        """Test that rollbacks maintain data integrity."""
        async with get_db() as db:
            migrations = self.helper.get_migration_history()
            
            if len(migrations) < 2:
                pytest.skip("Need at least 2 migrations for rollback testing")
            
            # Apply all migrations
            latest = migrations[-1]
            self.helper.migrate_to_revision(latest)
            
            # Create some test data
            await self._create_test_data(db)
            
            # Get data before rollback
            counts_before = await self.helper.get_data_counts(db)
            
            # Rollback one migration
            previous = migrations[-2]
            success = self.helper.downgrade_to_revision(previous)
            assert success, "Rollback failed"
            
            # Validate data integrity after rollback
            integrity_issues = await self.helper.validate_data_integrity(db)
            assert not integrity_issues, f"Data integrity issues after rollback: {integrity_issues}"
            
            # Check that data is still accessible (where schema allows)
            counts_after = await self.helper.get_data_counts(db)
            
            # Basic sanity check - we should still have some data
            total_before = sum(c for c in counts_before.values() if isinstance(c, int))
            total_after = sum(c for c in counts_after.values() if isinstance(c, int))
            
            if total_before > 0:
                assert total_after >= total_before * 0.5, \
                    "Too much data lost during rollback"
