#!/usr/bin/env python3
"""
Database Migration Orchestrator for Tender Platform
Handles PostgreSQL, MongoDB, and Redis initialization and migration scripts
"""

import os
import sys
import time
import logging
import subprocess
import psycopg2
import pymongo
import redis
from pathlib import Path
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/migrations/migration.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Orchestrates database migrations for PostgreSQL, MongoDB, and Redis"""
    
    def __init__(self):
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password'),
            'database': os.getenv('POSTGRES_DB', 'tender_platform')
        }
        
        self.mongodb_config = {
            'host': os.getenv('MONGODB_HOST', 'localhost'),
            'port': int(os.getenv('MONGODB_PORT', 27017)),
            'username': os.getenv('MONGODB_ROOT_USER', 'admin'),
            'password': os.getenv('MONGODB_ROOT_PASSWORD', 'password'),
            'database': os.getenv('MONGODB_DATABASE', 'tender_platform')
        }
        
        self.redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'password': os.getenv('REDIS_PASSWORD', 'password')
        }
        
        self.migration_paths = {
            'postgresql': Path('/app/postgresql'),
            'mongodb': Path('/app/mongodb'),
            'migrations': Path('/app/migrations')
        }
        
        # Ensure migrations directory exists
        self.migration_paths['migrations'].mkdir(exist_ok=True)

    def wait_for_service(self, service_name: str, check_func, max_attempts: int = 30, delay: int = 2) -> bool:
        """Wait for a service to become available"""
        logger.info(f"Waiting for {service_name} to become available...")
        
        for attempt in range(max_attempts):
            try:
                if check_func():
                    logger.info(f"{service_name} is ready!")
                    return True
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1}/{max_attempts} failed for {service_name}: {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(delay)
        
        logger.error(f"{service_name} failed to become ready after {max_attempts} attempts")
        return False

    def check_postgres_connection(self) -> bool:
        """Check if PostgreSQL is accessible"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            conn.close()
            return True
        except Exception:
            return False

    def check_mongodb_connection(self) -> bool:
        """Check if MongoDB is accessible"""
        try:
            client = pymongo.MongoClient(
                host=self.mongodb_config['host'],
                port=self.mongodb_config['port'],
                username=self.mongodb_config['username'],
                password=self.mongodb_config['password'],
                serverSelectionTimeoutMS=5000
            )
            client.admin.command('ping')
            client.close()
            return True
        except Exception:
            return False

    def check_redis_connection(self) -> bool:
        """Check if Redis is accessible"""
        try:
            client = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                password=self.redis_config['password'],
                socket_connect_timeout=5
            )
            client.ping()
            return True
        except Exception:
            return False

    def run_postgresql_migrations(self) -> bool:
        """Execute PostgreSQL migration scripts"""
        logger.info("Starting PostgreSQL migrations...")
        
        # Get all SQL files and sort them
        sql_files = sorted([f for f in self.migration_paths['postgresql'].glob('*.sql')])
        
        if not sql_files:
            logger.warning("No PostgreSQL migration files found")
            return True
        
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(**self.postgres_config)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create migration tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) UNIQUE NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT FALSE
                );
            """)
            
            for sql_file in sql_files:
                # Check if migration already executed
                cursor.execute(
                    "SELECT success FROM migration_history WHERE filename = %s",
                    (sql_file.name,)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    logger.info(f"PostgreSQL migration {sql_file.name} already executed, skipping")
                    continue
                
                logger.info(f"Executing PostgreSQL migration: {sql_file.name}")
                
                try:
                    # Read and execute SQL file
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # Split by semicolon and execute each statement
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement:
                            cursor.execute(statement)
                    
                    # Record successful migration
                    cursor.execute(
                        "INSERT INTO migration_history (filename, success) VALUES (%s, %s) ON CONFLICT (filename) DO UPDATE SET success = %s, executed_at = CURRENT_TIMESTAMP",
                        (sql_file.name, True, True)
                    )
                    
                    logger.info(f"Successfully executed PostgreSQL migration: {sql_file.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to execute PostgreSQL migration {sql_file.name}: {e}")
                    # Record failed migration
                    cursor.execute(
                        "INSERT INTO migration_history (filename, success) VALUES (%s, %s) ON CONFLICT (filename) DO UPDATE SET success = %s, executed_at = CURRENT_TIMESTAMP",
                        (sql_file.name, False, False)
                    )
                    conn.close()
                    return False
            
            conn.close()
            logger.info("PostgreSQL migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL migration failed: {e}")
            return False

    def run_mongodb_migrations(self) -> bool:
        """Execute MongoDB migration scripts"""
        logger.info("Starting MongoDB migrations...")
        
        # Get all JavaScript files and sort them
        js_files = sorted([f for f in self.migration_paths['mongodb'].glob('*.js')])
        
        if not js_files:
            logger.warning("No MongoDB migration files found")
            return True
        
        try:
            # Connect to MongoDB
            client = pymongo.MongoClient(
                host=self.mongodb_config['host'],
                port=self.mongodb_config['port'],
                username=self.mongodb_config['username'],
                password=self.mongodb_config['password']
            )
            
            db = client[self.mongodb_config['database']]
            
            # Create migration tracking collection
            migration_collection = db.migration_history
            migration_collection.create_index("filename", unique=True)
            
            for js_file in js_files:
                # Check if migration already executed
                existing = migration_collection.find_one({"filename": js_file.name, "success": True})
                
                if existing:
                    logger.info(f"MongoDB migration {js_file.name} already executed, skipping")
                    continue
                
                logger.info(f"Executing MongoDB migration: {js_file.name}")
                
                try:
                    # Execute JavaScript file using mongosh
                    cmd = [
                        "mongosh",
                        f"mongodb://{self.mongodb_config['username']}:{self.mongodb_config['password']}@{self.mongodb_config['host']}:{self.mongodb_config['port']}/{self.mongodb_config['database']}",
                        "--file", str(js_file),
                        "--quiet"
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        # Record successful migration
                        migration_collection.replace_one(
                            {"filename": js_file.name},
                            {
                                "filename": js_file.name,
                                "executed_at": time.time(),
                                "success": True,
                                "output": result.stdout
                            },
                            upsert=True
                        )
                        logger.info(f"Successfully executed MongoDB migration: {js_file.name}")
                    else:
                        logger.error(f"MongoDB migration {js_file.name} failed: {result.stderr}")
                        # Record failed migration
                        migration_collection.replace_one(
                            {"filename": js_file.name},
                            {
                                "filename": js_file.name,
                                "executed_at": time.time(),
                                "success": False,
                                "error": result.stderr
                            },
                            upsert=True
                        )
                        client.close()
                        return False
                    
                except Exception as e:
                    logger.error(f"Failed to execute MongoDB migration {js_file.name}: {e}")
                    # Record failed migration
                    migration_collection.replace_one(
                        {"filename": js_file.name},
                        {
                            "filename": js_file.name,
                            "executed_at": time.time(),
                            "success": False,
                            "error": str(e)
                        },
                        upsert=True
                    )
                    client.close()
                    return False
            
            client.close()
            logger.info("MongoDB migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB migration failed: {e}")
            return False

    def setup_redis(self) -> bool:
        """Initialize Redis with basic configuration"""
        logger.info("Setting up Redis...")
        
        try:
            client = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                password=self.redis_config['password']
            )
            
            # Set basic configuration keys
            config_keys = {
                'migration:completed': 'true',
                'migration:timestamp': str(int(time.time())),
                'cache:default_ttl': '3600',
                'queue:default_priority': '5',
                'system:status': 'initialized'
            }
            
            for key, value in config_keys.items():
                client.set(key, value)
                logger.info(f"Set Redis key: {key} = {value}")
            
            # Test Redis functionality
            test_key = 'test:migration'
            client.set(test_key, 'success', ex=60)
            test_value = client.get(test_key)
            
            if test_value and test_value.decode() == 'success':
                logger.info("Redis setup completed successfully")
                client.delete(test_key)
                return True
            else:
                logger.error("Redis test failed")
                return False
                
        except Exception as e:
            logger.error(f"Redis setup failed: {e}")
            return False

    def create_migration_report(self, postgres_success: bool, mongodb_success: bool, redis_success: bool):
        """Create a comprehensive migration report"""
        report_path = self.migration_paths['migrations'] / 'migration_report.json'
        
        report = {
            'timestamp': time.time(),
            'migration_status': {
                'postgresql': postgres_success,
                'mongodb': mongodb_success,
                'redis': redis_success,
                'overall': postgres_success and mongodb_success and redis_success
            },
            'configuration': {
                'postgres': self.postgres_config,
                'mongodb': {k: v for k, v in self.mongodb_config.items() if k != 'password'},
                'redis': {k: v for k, v in self.redis_config.items() if k != 'password'}
            }
        }
        
        try:
            import json
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Migration report created: {report_path}")
        except Exception as e:
            logger.error(f"Failed to create migration report: {e}")

    def run_all_migrations(self) -> bool:
        """Run all database migrations in sequence"""
        logger.info("Starting complete database migration process...")
        
        # Wait for all services to be ready
        services_ready = (
            self.wait_for_service("PostgreSQL", self.check_postgres_connection) and
            self.wait_for_service("MongoDB", self.check_mongodb_connection) and
            self.wait_for_service("Redis", self.check_redis_connection)
        )
        
        if not services_ready:
            logger.error("Not all database services are ready. Aborting migration.")
            return False
        
        # Run migrations in order
        postgres_success = self.run_postgresql_migrations()
        mongodb_success = self.run_mongodb_migrations()
        redis_success = self.setup_redis()
        
        # Create report
        self.create_migration_report(postgres_success, mongodb_success, redis_success)
        
        overall_success = postgres_success and mongodb_success and redis_success
        
        if overall_success:
            logger.info("🎉 All database migrations completed successfully!")
        else:
            logger.error("❌ Some database migrations failed. Check logs for details.")
        
        return overall_success


def main():
    """Main entry point"""
    logger.info("Database Migration Orchestrator Starting...")
    
    migrator = DatabaseMigrator()
    success = migrator.run_all_migrations()
    
    if success:
        logger.info("Migration process completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration process failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
