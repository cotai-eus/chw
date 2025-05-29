#!/bin/bash
# Backup script for the tender platform

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "🔄 Starting backup process at $(date)"

# Create backup directories
mkdir -p $BACKUP_DIR/postgres
mkdir -p $BACKUP_DIR/mongodb
mkdir -p $BACKUP_DIR/redis

# PostgreSQL Backup
echo "📊 Backing up PostgreSQL..."
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
    -h postgres \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    -f $BACKUP_DIR/postgres/backup_$TIMESTAMP.sql

# Compress PostgreSQL backup
gzip $BACKUP_DIR/postgres/backup_$TIMESTAMP.sql
echo "✅ PostgreSQL backup completed: backup_$TIMESTAMP.sql.gz"

# MongoDB Backup
echo "🍃 Backing up MongoDB..."
mongodump \
    --host mongodb:27017 \
    --username $MONGO_USER \
    --password $MONGO_PASSWORD \
    --db $MONGO_DB \
    --out $BACKUP_DIR/mongodb/backup_$TIMESTAMP

# Compress MongoDB backup
tar -czf $BACKUP_DIR/mongodb/backup_$TIMESTAMP.tar.gz -C $BACKUP_DIR/mongodb backup_$TIMESTAMP
rm -rf $BACKUP_DIR/mongodb/backup_$TIMESTAMP
echo "✅ MongoDB backup completed: backup_$TIMESTAMP.tar.gz"

# Redis Backup
echo "🔴 Backing up Redis..."
redis-cli -h redis --rdb $BACKUP_DIR/redis/backup_$TIMESTAMP.rdb
echo "✅ Redis backup completed: backup_$TIMESTAMP.rdb"

# Cleanup old backups
echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."

# PostgreSQL cleanup
find $BACKUP_DIR/postgres -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# MongoDB cleanup
find $BACKUP_DIR/mongodb -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Redis cleanup
find $BACKUP_DIR/redis -name "backup_*.rdb" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup process completed at $(date)"
echo "📁 Backup location: $BACKUP_DIR"

# List current backups
echo "📋 Current backups:"
echo "PostgreSQL:"
ls -lh $BACKUP_DIR/postgres/ | tail -5
echo "MongoDB:"
ls -lh $BACKUP_DIR/mongodb/ | tail -5
echo "Redis:"
ls -lh $BACKUP_DIR/redis/ | tail -5
