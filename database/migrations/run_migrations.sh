#!/bin/bash

# Database Migration and Setup Script
# Handles PostgreSQL, MongoDB, and Redis setup for the tender platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_environment() {
    log "Checking environment variables..."
    
    local required_vars=(
        "POSTGRES_HOST"
        "POSTGRES_PORT"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "MONGO_HOST"
        "MONGO_PORT"
        "MONGO_DB"
        "REDIS_HOST"
        "REDIS_PORT"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Environment variable $var is not set"
            exit 1
        fi
    done
    
    success "All required environment variables are set"
}

# Check if databases are accessible
check_database_connectivity() {
    log "Checking database connectivity..."
    
    # Check PostgreSQL
    log "Testing PostgreSQL connection..."
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        success "PostgreSQL connection successful"
    else
        error "Cannot connect to PostgreSQL"
        exit 1
    fi
    
    # Check MongoDB
    log "Testing MongoDB connection..."
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASSWORD" ]]; then
        MONGO_URI="mongodb://$MONGO_USER:$MONGO_PASSWORD@$MONGO_HOST:$MONGO_PORT"
    else
        MONGO_URI="mongodb://$MONGO_HOST:$MONGO_PORT"
    fi
    
    if mongosh "$MONGO_URI" --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        success "MongoDB connection successful"
    else
        error "Cannot connect to MongoDB"
        exit 1
    fi
    
    # Check Redis
    log "Testing Redis connection..."
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    if $REDIS_CLI_CMD ping > /dev/null 2>&1; then
        success "Redis connection successful"
    else
        error "Cannot connect to Redis"
        exit 1
    fi
}

# Install Python dependencies for migration
install_dependencies() {
    log "Installing migration dependencies..."
    
    # Check if pip is available
    if ! command -v pip &> /dev/null; then
        error "pip is not installed"
        exit 1
    fi
    
    # Install required packages
    pip install psycopg2-binary pymongo redis
    
    success "Dependencies installed"
}

# Run PostgreSQL migrations
run_postgresql_migrations() {
    log "Running PostgreSQL migrations..."
    
    local sql_dir="$(dirname "$0")/../postgresql"
    
    if [[ ! -d "$sql_dir" ]]; then
        error "PostgreSQL migration directory not found: $sql_dir"
        exit 1
    fi
    
    # Create database if it doesn't exist
    log "Creating database if it doesn't exist..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d postgres -c "CREATE DATABASE $POSTGRES_DB;" 2>/dev/null || true
    
    # Run each SQL file in order
    for sql_file in "$sql_dir"/*.sql; do
        if [[ -f "$sql_file" ]]; then
            local filename=$(basename "$sql_file")
            log "Executing: $filename"
            
            if PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$sql_file"; then
                success "Executed: $filename"
            else
                error "Failed to execute: $filename"
                exit 1
            fi
        fi
    done
    
    success "PostgreSQL migrations completed"
}

# Run MongoDB migrations
run_mongodb_migrations() {
    log "Running MongoDB migrations..."
    
    local js_dir="$(dirname "$0")/../mongodb"
    
    if [[ ! -d "$js_dir" ]]; then
        error "MongoDB migration directory not found: $js_dir"
        exit 1
    fi
    
    # Prepare MongoDB URI
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASSWORD" ]]; then
        MONGO_URI="mongodb://$MONGO_USER:$MONGO_PASSWORD@$MONGO_HOST:$MONGO_PORT/$MONGO_DB"
    else
        MONGO_URI="mongodb://$MONGO_HOST:$MONGO_PORT/$MONGO_DB"
    fi
    
    # Run each JavaScript file
    for js_file in "$js_dir"/*.js; do
        if [[ -f "$js_file" ]]; then
            local filename=$(basename "$js_file")
            log "Executing: $filename"
            
            if mongosh "$MONGO_URI" "$js_file"; then
                success "Executed: $filename"
            else
                error "Failed to execute: $filename"
                exit 1
            fi
        fi
    done
    
    success "MongoDB migrations completed"
}

# Setup Redis configuration
setup_redis() {
    log "Setting up Redis configuration..."
    
    local redis_conf="$(dirname "$0")/../redis/redis.conf"
    
    if [[ -f "$redis_conf" ]]; then
        warning "Redis configuration file found at $redis_conf"
        warning "Please manually apply this configuration to your Redis instance"
        warning "Or copy it to your Redis configuration directory"
    fi
    
    # Test Redis with basic operations
    log "Testing Redis functionality..."
    
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    # Set a test key
    $REDIS_CLI_CMD SET migration_test "$(date)" EX 300 > /dev/null
    
    # Get the test key
    if $REDIS_CLI_CMD GET migration_test > /dev/null; then
        success "Redis functionality test passed"
    else
        error "Redis functionality test failed"
        exit 1
    fi
    
    success "Redis setup completed"
}

# Run Python migration script
run_python_migrations() {
    log "Running Python migration script..."
    
    local migrate_script="$(dirname "$0")/migrate.py"
    
    if [[ ! -f "$migrate_script" ]]; then
        error "Migration script not found: $migrate_script"
        exit 1
    fi
    
    if python "$migrate_script"; then
        success "Python migrations completed"
    else
        error "Python migrations failed"
        exit 1
    fi
}

# Create backup before migration
create_backup() {
    log "Creating database backup before migration..."
    
    local backup_dir="$(dirname "$0")/backups"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL
    log "Backing up PostgreSQL..."
    if PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB > "$backup_dir/postgres_backup_$timestamp.sql"; then
        success "PostgreSQL backup created: postgres_backup_$timestamp.sql"
    else
        warning "PostgreSQL backup failed (database might not exist yet)"
    fi
    
    # Backup MongoDB
    log "Backing up MongoDB..."
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASSWORD" ]]; then
        MONGODUMP_AUTH="--username $MONGO_USER --password $MONGO_PASSWORD"
    else
        MONGODUMP_AUTH=""
    fi
    
    if mongodump --host $MONGO_HOST:$MONGO_PORT $MONGODUMP_AUTH --db $MONGO_DB --out "$backup_dir/mongodb_backup_$timestamp" > /dev/null 2>&1; then
        success "MongoDB backup created: mongodb_backup_$timestamp"
    else
        warning "MongoDB backup failed (database might not exist yet)"
    fi
}

# Validate migration results
validate_migration() {
    log "Validating migration results..."
    
    # Check PostgreSQL tables
    log "Checking PostgreSQL tables..."
    local table_count=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    
    if [[ $table_count -gt 0 ]]; then
        success "PostgreSQL tables created: $table_count tables found"
    else
        error "No PostgreSQL tables found"
        exit 1
    fi
    
    # Check MongoDB collections
    log "Checking MongoDB collections..."
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASSWORD" ]]; then
        MONGO_URI="mongodb://$MONGO_USER:$MONGO_PASSWORD@$MONGO_HOST:$MONGO_PORT/$MONGO_DB"
    else
        MONGO_URI="mongodb://$MONGO_HOST:$MONGO_PORT/$MONGO_DB"
    fi
    
    local collection_count=$(mongosh "$MONGO_URI" --quiet --eval "db.adminCommand('listCollections').cursor.firstBatch.length")
    
    if [[ $collection_count -gt 0 ]]; then
        success "MongoDB collections created: $collection_count collections found"
    else
        warning "No MongoDB collections found"
    fi
    
    # Check Redis connectivity
    log "Checking Redis connectivity..."
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
    else
        REDIS_CLI_CMD="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
    fi
    
    if $REDIS_CLI_CMD ping > /dev/null 2>&1; then
        success "Redis is accessible"
    else
        error "Redis is not accessible"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting database migration process..."
    
    # Parse command line arguments
    SKIP_BACKUP=false
    VALIDATE_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-backup    Skip database backup before migration"
                echo "  --validate-only  Only validate existing database setup"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    check_environment
    check_database_connectivity
    
    if [[ "$VALIDATE_ONLY" == true ]]; then
        validate_migration
        exit 0
    fi
    
    if [[ "$SKIP_BACKUP" == false ]]; then
        create_backup
    fi
    
    install_dependencies
    run_postgresql_migrations
    run_mongodb_migrations
    setup_redis
    run_python_migrations
    validate_migration
    
    success "Database migration process completed successfully!"
    log "You can now start your application with the new database schema"
}

# Run main function
main "$@"
