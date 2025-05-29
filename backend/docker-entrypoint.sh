#!/bin/bash
set -e

echo "🚀 Starting FastAPI Backend..."

# Default values
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-tender_platform}

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "✅ PostgreSQL is up and running!"

# Wait for MongoDB
MONGO_HOST=${MONGO_HOST:-mongodb}
MONGO_PORT=${MONGO_PORT:-27017}
echo "⏳ Waiting for MongoDB at $MONGO_HOST:$MONGO_PORT..."
while ! nc -z $MONGO_HOST $MONGO_PORT; do
    echo "MongoDB is unavailable - sleeping"
    sleep 1
done
echo "✅ MongoDB is up and running!"

# Wait for Redis
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}
echo "⏳ Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "✅ Redis is up and running!"

# Run database migrations
echo "🔄 Running database migrations..."
poetry run alembic upgrade head
echo "✅ Database migrations completed!"

# Create initial data if needed
if [ "$CREATE_INITIAL_DATA" = "true" ]; then
    echo "📊 Creating initial data..."
    poetry run python -c "
from app.db.init_db import init_db
from app.db.session import SessionLocal

db = SessionLocal()
try:
    init_db(db)
    print('✅ Initial data created!')
except Exception as e:
    print(f'⚠️ Initial data creation failed: {e}')
finally:
    db.close()
    "
fi

echo "🎉 Backend setup completed! Starting application..."

# Execute the main command
exec poetry run "$@"
