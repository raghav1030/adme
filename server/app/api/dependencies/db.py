from fastapi import Depends
from app.api.core.database import get_db_session, get_redis_client
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis


async def get_db() -> AsyncSession:
    async for session in get_db_session():
        yield session


async def get_redis() -> redis.Redis:
    async for client in get_redis_client():
        yield client
