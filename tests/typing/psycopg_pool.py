from psycopg_pool import AsyncConnectionPool, ConnectionPool

from psycache import AsyncPostgresCache, PostgresCache
from psycache.psycopg_pool import AsyncPsycopgCachePool, PsycopgCachePool


dsn = "postgresql://psycache@127.0.0.1/psycache"

pool = ConnectionPool(dsn)
apool = AsyncConnectionPool(dsn)

cache = PostgresCache(PsycopgCachePool(pool))
acache = AsyncPostgresCache(AsyncPsycopgCachePool(apool))


cache.put_raw("user:alice", {"score": 42}, ttl=300)


async def f() -> None:
    await acache.get_raw("user:alice")
