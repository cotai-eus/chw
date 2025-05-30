"""
Database Migration Manager
Handles PostgreSQL, MongoDB, and Redis setup and migrations
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pymongo
import redis
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrationManager:
    """Manages database migrations for multi-database architecture"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.migration_path = Path(__file__).parent.parent  # Go up one level to database/
        self.postgresql_scripts = sorted((self.migration_path / 'postgresql').glob('*.sql'))
        self.mongodb_scripts = sorted((self.migration_path / 'mongodb').glob('*.js'))
        
    async def run_all_migrations(self):
        """Run all database migrations in order"""
        try:
            logger.info("Starting database migration process...")
            
            # 1. Setup PostgreSQL
            await self.setup_postgresql()
            
            # 2. Setup MongoDB
            await self.setup_mongodb()
            
            # 3. Setup Redis
            await self.setup_redis()
            
            # 4. Create migration record
            await self.record_migration()
            
            logger.info("All database migrations completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise
    
    async def setup_postgresql(self):
        """Setup PostgreSQL database and run SQL migrations"""
        logger.info("Setting up PostgreSQL...")
        
        # Create database if it doesn't exist
        await self._create_postgresql_database()
        
        # Run SQL migration scripts
        conn = psycopg2.connect(
            host=self.config['postgresql']['host'],
            port=self.config['postgresql']['port'],
            user=self.config['postgresql']['user'],
            password=self.config['postgresql']['password'],
            database=self.config['postgresql']['database']
        )
        
        try:
            cursor = conn.cursor()
            
            # Create migration tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL,
                    migration_type VARCHAR(50) NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );
            """)
            
            # Run each SQL script
            for script_path in self.postgresql_scripts:
                script_name = script_path.name
                
                # Check if already executed
                cursor.execute(
                    "SELECT id FROM migration_history WHERE migration_name = %s AND migration_type = 'postgresql'",
                    (script_name,)
                )
                
                if cursor.fetchone():
                    logger.info(f"Skipping {script_name} (already executed)")
                    continue
                
                logger.info(f"Executing PostgreSQL script: {script_name}")
                
                try:
                    with open(script_path, 'r') as f:
                        sql_content = f.read()
                    
                    cursor.execute(sql_content)
                    
                    # Record successful migration
                    cursor.execute(
                        "INSERT INTO migration_history (migration_name, migration_type) VALUES (%s, %s)",
                        (script_name, 'postgresql')
                    )
                    
                    conn.commit()
                    logger.info(f"Successfully executed {script_name}")
                    
                except Exception as e:
                    # Record failed migration
                    cursor.execute(
                        "INSERT INTO migration_history (migration_name, migration_type, success, error_message) VALUES (%s, %s, %s, %s)",
                        (script_name, 'postgresql', False, str(e))
                    )
                    conn.commit()
                    raise
        
        finally:
            conn.close()
    
    async def setup_mongodb(self):
        """Setup MongoDB collections and indexes"""
        logger.info("Setting up MongoDB...")
        
        client = pymongo.MongoClient(
            host=self.config['mongodb']['host'],
            port=self.config['mongodb']['port'],
            username=self.config['mongodb']['user'],
            password=self.config['mongodb']['password']
        )
        
        try:
            db = client[self.config['mongodb']['database']]
            
            # Create migration tracking collection
            if 'migration_history' not in db.list_collection_names():
                db.create_collection('migration_history')
            
            # Run each MongoDB script
            for script_path in self.mongodb_scripts:
                script_name = script_path.name
                
                # Check if already executed
                existing = db.migration_history.find_one({
                    'migration_name': script_name,
                    'migration_type': 'mongodb'
                })
                
                if existing:
                    logger.info(f"Skipping {script_name} (already executed)")
                    continue
                
                logger.info(f"Executing MongoDB script: {script_name}")
                
                try:
                    with open(script_path, 'r') as f:
                        js_content = f.read()
                    
                    # Execute JavaScript code
                    # Note: This is a simplified approach. In production, you might want to use
                    # a more robust method to execute MongoDB scripts
                    exec_result = db.command('eval', js_content)
                    
                    # Record successful migration
                    db.migration_history.insert_one({
                        'migration_name': script_name,
                        'migration_type': 'mongodb',
                        'executed_at': datetime.utcnow(),
                        'success': True
                    })
                    
                    logger.info(f"Successfully executed {script_name}")
                    
                except Exception as e:
                    # Record failed migration
                    db.migration_history.insert_one({
                        'migration_name': script_name,
                        'migration_type': 'mongodb',
                        'executed_at': datetime.utcnow(),
                        'success': False,
                        'error_message': str(e)
                    })
                    raise
        
        finally:
            client.close()
    
    async def setup_redis(self):
        """Setup Redis configuration"""
        logger.info("Setting up Redis...")
        
        r = redis.Redis(
            host=self.config['redis']['host'],
            port=self.config['redis']['port'],
            password=self.config['redis'].get('password'),
            decode_responses=True
        )
        
        try:
            # Test connection
            r.ping()
            
            # Load Redis configuration
            redis_config_path = self.migration_path / 'redis' / 'redis_config.conf'
            if redis_config_path.exists():
                logger.info("Redis configuration file found, apply manually if needed")
            
            # Set up basic cache structure validation
            r.set('migration:redis:setup', datetime.utcnow().isoformat(), ex=86400)
            
            logger.info("Redis setup completed")
            
        except Exception as e:
            logger.error(f"Redis setup failed: {str(e)}")
            raise
    
    async def _create_postgresql_database(self):
        """Create PostgreSQL database if it doesn't exist"""
        # Connect to default postgres database first
        conn = psycopg2.connect(
            host=self.config['postgresql']['host'],
            port=self.config['postgresql']['port'],
            user=self.config['postgresql']['user'],
            password=self.config['postgresql']['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        try:
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.config['postgresql']['database'],)
            )
            
            if not cursor.fetchone():
                # Create database
                cursor.execute(f"CREATE DATABASE {self.config['postgresql']['database']}")
                logger.info(f"Created database: {self.config['postgresql']['database']}")
            else:
                logger.info(f"Database {self.config['postgresql']['database']} already exists")
        
        finally:
            conn.close()
    
    async def record_migration(self):
        """Record overall migration completion"""
        logger.info("Recording migration completion...")
        
        # Record in PostgreSQL
        conn = psycopg2.connect(
            host=self.config['postgresql']['host'],
            port=self.config['postgresql']['port'],
            user=self.config['postgresql']['user'],
            password=self.config['postgresql']['password'],
            database=self.config['postgresql']['database']
        )
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO migration_history (migration_name, migration_type) VALUES (%s, %s)",
                ('complete_migration', 'system')
            )
            conn.commit()
        finally:
            conn.close()
    
    async def rollback_migration(self, migration_name: str):
        """Rollback a specific migration (PostgreSQL only for now)"""
        logger.warning(f"Rolling back migration: {migration_name}")
        
        # This is a placeholder for rollback functionality
        # In a production system, you would implement proper rollback scripts
        logger.warning("Rollback functionality not implemented yet")

def load_config() -> Dict:
    """Load database configuration from environment variables"""
    return {
        'postgresql': {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'database': os.getenv('POSTGRES_DB', 'tender_platform')
        },
        'mongodb': {
            'host': os.getenv('MONGO_HOST', 'localhost'),
            'port': int(os.getenv('MONGO_PORT', 27017)),
            'user': os.getenv('MONGO_USER'),
            'password': os.getenv('MONGO_PASSWORD'),
            'database': os.getenv('MONGO_DB', 'tender_platform_flexible')
        },
        'redis': {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'password': os.getenv('REDIS_PASSWORD')
        }
    }

async def main():
    """Main migration entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        migration_name = sys.argv[2] if len(sys.argv) > 2 else None
        if not migration_name:
            logger.error("Please specify migration name to rollback")
            sys.exit(1)
        
        config = load_config()
        manager = DatabaseMigrationManager(config)
        await manager.rollback_migration(migration_name)
    else:
        config = load_config()
        manager = DatabaseMigrationManager(config)
        await manager.run_all_migrations()

if __name__ == "__main__":
    asyncio.run(main())
