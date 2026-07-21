from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache, PostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool, SQLAlchemyCachePool


dsn = "postgresql://psycache@127.0.0.1/psycache"

engine = create_engine(dsn)
aengine = create_async_engine(dsn)

cache = PostgresCache(SQLAlchemyCachePool(engine))
acache = AsyncPostgresCache(AsyncSQLAlchemyCachePool(aengine))


cache.put_raw("user:alice", {"score": 42}, ttl=300)


async def f() -> None:
    await acache.get_raw("user:alice")
