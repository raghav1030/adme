from fastapi import Depends
from app.core.database import get_db, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis


async def get_db_session() -> AsyncSession:
    async for session in get_db():
        yield session


async def get_redis_client() -> redis.Redis:
    async for client in get_redis():
        yield client
