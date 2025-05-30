"""
Database Migration Manager for Backend Integration
Integrates with Alembic for PostgreSQL and manages MongoDB/Redis separately
"""

import asyncio
import logging
from typing import Dict, Optional
from pathlib import Path
import subprocess
import os

from sqlalchemy import text
from app.db.session import engine, get_mongodb_client, get_redis_client
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class BackendMigrationManager:
    """Manages database migrations from backend context"""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parents[3]  # Go up to project root
        
    async def run_all_migrations(self):
        """Run all database migrations in proper order"""
        try:
            logger.info("Starting backend database migration process...")
            
            # 1. PostgreSQL via Alembic
            await self.run_alembic_migrations()
            
            # 2. MongoDB collections
            await self.setup_mongodb()
            
            # 3. Redis configuration
            await self.setup_redis()
            
            logger.info("All backend migrations completed successfully!")
            
        except Exception as e:
            logger.error(f"Backend migration failed: {str(e)}")
            raise
    
    async def run_alembic_migrations(self):
        """Run Alembic migrations for PostgreSQL"""
        logger.info("Running Alembic migrations for PostgreSQL...")
        
        try:
            # Run alembic upgrade head
            alembic_dir = self.project_root / "backend"
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=alembic_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("Alembic migrations completed successfully")
            logger.debug(f"Alembic output: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Alembic migration failed: {e.stderr}")
            raise
    
    async def setup_mongodb(self):
        """Setup MongoDB collections and indexes"""
        logger.info("Setting up MongoDB collections...")
        
        client = await get_mongodb_client()
        db = client[self.settings.MONGODB_DATABASE]
        
        try:
            # Create migration tracking collection
            if 'migration_history' not in await db.list_collection_names():
                await db.create_collection('migration_history')
            
            # Run MongoDB setup scripts
            mongodb_scripts_dir = self.project_root / "database" / "mongodb"
            
            if mongodb_scripts_dir.exists():
                for script_path in sorted(mongodb_scripts_dir.glob('*.js')):
                    script_name = script_path.name
                    
                    # Check if already executed
                    existing = await db.migration_history.find_one({
                        'migration_name': script_name,
                        'migration_type': 'mongodb'
                    })
                    
                    if existing:
                        logger.info(f"Skipping MongoDB script {script_name} (already executed)")
                        continue
                    
                    logger.info(f"Executing MongoDB script: {script_name}")
                    
                    try:
                        with open(script_path, 'r') as f:
                            js_content = f.read()
                        
                        # Execute the JavaScript content
                        # Note: Using eval for MongoDB JavaScript execution
                        await db.command('eval', js_content)
                        
                        # Record successful migration
                        await db.migration_history.insert_one({
                            'migration_name': script_name,
                            'migration_type': 'mongodb',
                            'executed_at': 'new Date()',
                            'success': True
                        })
                        
                        logger.info(f"Successfully executed MongoDB script: {script_name}")
                        
                    except Exception as e:
                        # Record failed migration
                        await db.migration_history.insert_one({
                            'migration_name': script_name,
                            'migration_type': 'mongodb',
                            'executed_at': 'new Date()',
                            'success': False,
                            'error_message': str(e)
                        })
                        logger.error(f"MongoDB script failed: {script_name} - {str(e)}")
                        raise
            
            logger.info("MongoDB setup completed")
            
        finally:
            client.close()
    
    async def setup_redis(self):
        """Setup Redis configuration and cache structure"""
        logger.info("Setting up Redis cache structure...")
        
        redis_client = await get_redis_client()
        
        try:
            # Test connection
            await redis_client.ping()
            
            # Set up cache namespaces
            cache_namespaces = [
                'session',
                'rate_limit',
                'ai_cache',
                'perf_cache',
                'chat',
                'presence',
                'notifications',
                'metrics',
                'alerts',
                'task_status',
                'bi_cache'
            ]
            
            for namespace in cache_namespaces:
                await redis_client.set(f'namespace:{namespace}:initialized', 'true', ex=86400)
            
            # Record migration
            await redis_client.set(
                'migration:redis:backend_setup', 
                'completed', 
                ex=86400
            )
            
            logger.info("Redis setup completed")
            
        except Exception as e:
            logger.error(f"Redis setup failed: {str(e)}")
            raise
        finally:
            await redis_client.close()
    
    async def check_migration_status(self) -> Dict[str, bool]:
        """Check status of all database migrations"""
        status = {
            'postgresql': False,
            'mongodb': False,
            'redis': False
        }
        
        try:
            # Check PostgreSQL (via Alembic)
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                if result.fetchone():
                    status['postgresql'] = True
        except:
            pass
        
        try:
            # Check MongoDB
            client = await get_mongodb_client()
            db = client[self.settings.MONGODB_DATABASE]
            if await db.migration_history.find_one({'migration_type': 'mongodb'}):
                status['mongodb'] = True
            client.close()
        except:
            pass
        
        try:
            # Check Redis
            redis_client = await get_redis_client()
            if await redis_client.get('migration:redis:backend_setup'):
                status['redis'] = True
            await redis_client.close()
        except:
            pass
        
        return status

# Convenience function for FastAPI startup
async def initialize_databases():
    """Initialize all databases on application startup"""
    manager = BackendMigrationManager()
    
    # Check if migrations are needed
    status = await manager.check_migration_status()
    
    if not all(status.values()):
        logger.info("Some databases need initialization...")
        await manager.run_all_migrations()
    else:
        logger.info("All databases are already initialized")
    
    return status
