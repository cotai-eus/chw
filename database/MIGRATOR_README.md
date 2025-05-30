# Docker Migrator - Usage Guide

## Overview
The `tender-migrator` Docker image is a standalone database migration tool that handles PostgreSQL, MongoDB, and Redis initialization and migration scripts for the Tender Platform.

## Features
- ✅ PostgreSQL migrations with SQL scripts
- ✅ MongoDB migrations with JavaScript scripts  
- ✅ Redis configuration and setup
- ✅ Migration history tracking
- ✅ Comprehensive logging
- ✅ Service availability checks
- ✅ Error handling and rollback support

## Image Details
- **Image Name**: `tender-migrator`
- **Base Image**: `python:3.11-slim`
- **Size**: ~636MB
- **Architecture**: amd64, arm64

## Included Tools
- PostgreSQL client (`psql`)
- MongoDB shell (`mongosh`) 
- MongoDB database tools (`mongodump`, `mongorestore`)
- Python packages: `psycopg2-binary`, `pymongo`, `redis`, `python-dotenv`, `requests`

## Directory Structure
```
/app/
├── migrate_standalone.py      # Main migration script
├── postgresql/                # PostgreSQL migration files (.sql)
├── mongodb/                   # MongoDB migration files (.js)
└── migrations/                # Migration logs and reports
```

## Environment Variables

### PostgreSQL Configuration
- `POSTGRES_HOST` - PostgreSQL server hostname (default: localhost)
- `POSTGRES_PORT` - PostgreSQL server port (default: 5432)
- `POSTGRES_USER` - PostgreSQL username (default: postgres)
- `POSTGRES_PASSWORD` - PostgreSQL password (default: password)
- `POSTGRES_DB` - PostgreSQL database name (default: tender_platform)

### MongoDB Configuration  
- `MONGODB_HOST` - MongoDB server hostname (default: localhost)
- `MONGODB_PORT` - MongoDB server port (default: 27017)
- `MONGODB_ROOT_USER` - MongoDB username (default: admin)
- `MONGODB_ROOT_PASSWORD` - MongoDB password (default: password)
- `MONGODB_DATABASE` - MongoDB database name (default: tender_platform)

### Redis Configuration
- `REDIS_HOST` - Redis server hostname (default: localhost)
- `REDIS_PORT` - Redis server port (default: 6379)
- `REDIS_PASSWORD` - Redis password (default: password)

## Usage Examples

### Basic Usage
```bash
docker run --rm tender-migrator
```

### With Custom Environment Variables
```bash
docker run --rm \
  -e POSTGRES_HOST=db.example.com \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=secretpass \
  -e MONGODB_HOST=mongo.example.com \
  -e REDIS_HOST=redis.example.com \
  tender-migrator
```

### With Docker Compose
```yaml
version: '3.8'
services:
  migrator:
    image: tender-migrator
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secretpass
      MONGODB_HOST: mongodb
      REDIS_HOST: redis
    depends_on:
      - postgres
      - mongodb
      - redis
```

### Extract Migration Logs
```bash
# Run with volume mount to persist logs
docker run --rm \
  -v $(pwd)/logs:/app/migrations \
  -e POSTGRES_HOST=your_db_host \
  tender-migrator
```

## Migration Process
1. **Service Availability Check**: Waits for PostgreSQL, MongoDB, and Redis to become available
2. **PostgreSQL Migrations**: Executes `.sql` files in alphabetical order
3. **MongoDB Migrations**: Executes `.js` files using `mongosh`
4. **Redis Setup**: Configures basic Redis keys and tests functionality
5. **Report Generation**: Creates `migration_report.json` with results

## Migration Files

### PostgreSQL (.sql files in /app/postgresql/)
- `001_initial_schema.sql` - Initial database schema
- `002_ai_system.sql` - AI system tables
- `003_business_system.sql` - Business logic tables
- `004_messaging_audit.sql` - Messaging and audit system
- `005_indexes_optimization.sql` - Database indexes
- `006_triggers_functions.sql` - Triggers and functions

### MongoDB (.js files in /app/mongodb/)
- `001_notifications.js` - Notification collections
- `002_activity_history.js` - Activity tracking
- `003_dynamic_settings.js` - Dynamic configuration

## Exit Codes
- `0` - All migrations completed successfully
- `1` - Migration failed (check logs for details)

## Troubleshooting

### Common Issues
1. **Connection Timeouts**: Ensure database services are running and accessible
2. **Permission Errors**: Check database user permissions
3. **Migration Conflicts**: Review migration history tables

### Debugging
```bash
# Run with interactive shell for debugging
docker run --rm -it tender-migrator /bin/bash

# Check logs
docker run --rm tender-migrator cat /app/migrations/migration.log
```

## Building the Image
```bash
cd /path/to/database
docker build -f Dockerfile.migrator -t tender-migrator .
```

## Testing
Run the validation test:
```bash
python3 test_migrator.py
```

## Security Notes
- Environment variables containing passwords are not logged
- Migration history excludes sensitive configuration data
- Use secure networks for database connections in production

## Support
For issues or questions about the migrator, check the migration logs at `/app/migrations/migration.log` and the migration report at `/app/migrations/migration_report.json`.
