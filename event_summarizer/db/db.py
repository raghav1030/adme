import asyncpg
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/upperscore"
)

_pool = None


async def get_pool():
    global _pool
    if not _pool:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def mark_event_done(event_id, summary_result):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Store summary_result to event_summary table, mark github_event summary_status = 'done'
        pass


async def mark_event_error(event_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE github_event SET summary_status = 'error' WHERE event_id = $1",
            event_id,
        )
