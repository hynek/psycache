# Background Cleanup

*psycache* ignores expired keys when reading, but their rows stick around until something deletes them.
You can call [`PostgresCache.cleanup_expired()`][psycache.PostgresCache.cleanup_expired] yourself, or let *psycache* do it for you in the background.


## A cleanup thread

For synchronous pools, [`PostgresCache.start_cleanup_thread()`][psycache.PostgresCache.start_cleanup_thread] starts a daemon thread that periodically deletes expired entries.
Use it as a context manager to stop the thread automatically:

```python
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))


with cache.start_cleanup_thread(interval=60):
    ...  # your application runs here
```

Or manage its lifecycle manually through the returned [`CleanupService`][psycache.CleanupService]:

```python
svc = cache.start_cleanup_thread(interval=60)
try:
    ...  # your application runs here
finally:
    svc.stop()

engine.dispose()
```

## ... or a cleanup task

For async pools, use [`AsyncPostgresCache.start_cleanup_task()`][psycache.AsyncPostgresCache.start_cleanup_task] inside a running event loop.
It starts an [`asyncio.Task`][] that periodically deletes expired entries and can be used as an async context manager.

Otherwise, it mirrors the behavior of [`PostgresCache.start_cleanup_thread()`][psycache.PostgresCache.start_cleanup_thread]:

```python
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool


aengine = create_async_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
acache = AsyncPostgresCache(AsyncSQLAlchemyCachePool(aengine))

async def main():
    async with acache.start_cleanup_task(interval=60):
        ...  # your application runs here

    svc = acache.start_cleanup_task(interval=60)
    try:
        ...  # your application runs here
    finally:
        await svc.stop()

asyncio.run(main())
```
