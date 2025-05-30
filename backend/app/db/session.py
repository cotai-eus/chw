from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import aioredis
from typing import AsyncGenerator, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL Configuration
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# MongoDB Configuration
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database = None

# Redis Configuration  
redis_client: Optional[aioredis.Redis] = None

async def init_mongodb():
    """Initialize MongoDB connection"""
    global mongodb_client, mongodb_database
    try:
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
        mongodb_database = mongodb_client[settings.MONGODB_DATABASE]
        # Test connection
        await mongodb_client.admin.command('ping')
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URI,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

async def close_mongodb():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

# Dependency injection functions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get PostgreSQL database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_mongodb():
    """Get MongoDB database instance"""
    if mongodb_database is None:
        await init_mongodb()
    return mongodb_database

async def get_redis():
    """Get Redis client instance"""
    if redis_client is None:
        await init_redis()
    return redis_client


# MongoDB
mongo_client: AsyncIOMotorClient = None
mongo_db = None


async def connect_to_mongo():
    global mongo_client, mongo_db
    mongo_client = AsyncIOMotorClient(settings.MONGO_DATABASE_URI)
    mongo_db = mongo_client[settings.MONGO_DB]


async def close_mongo_connection():
    global mongo_client
    if mongo_client:
        mongo_client.close()


def get_mongo_db():
    return mongo_db


# Redis
redis_client: aioredis.Redis = None


async def connect_to_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )


async def close_redis_connection():
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis():
    return redis_client
