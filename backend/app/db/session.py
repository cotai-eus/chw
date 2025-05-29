from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import aioredis
from typing import AsyncGenerator
from app.core.config import settings

# PostgreSQL
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


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
