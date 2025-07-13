import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine
from app.models.user import Base


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
