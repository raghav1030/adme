import asyncio
import asyncpg
from app.api.core.config import settings
import os


async def init_db():
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)

    migration_dir = "app/db/migrations"
    sql_files = sorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])

    for sql_file in sql_files:
        with open(os.path.join(migration_dir, sql_file), "r") as f:
            sql = f.read()
            print(f"Executing {sql_file}...")
            await conn.execute(sql)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(init_db())
