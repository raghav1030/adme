from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis.asyncio as redis

# PostgreSQL
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# ✅  new alias both FastAPI and Celery can use
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_client():
    yield redis_client
