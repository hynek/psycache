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


aengine = create_async_engine(
    "postgresql+psycopg://psycache@127.0.0.1/psycache"
)
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


## ... or an elected *pgbg* service { #pgbg }

Both helpers above run the cleanup in *every* process that starts them.
That's harmless, because deleting expired rows is idempotent.
But if you run many instances of your application, it's wasteful, because all of them delete the same rows at the same interval, and most of them find nothing to do.

[*pgbg*](https://pgbg.hynek.me/) solves this with PostgreSQL-based **leader election**:
many processes can start the same service, but only one of them runs it at a time.
On top of that, *pgbg* supervises the thread and restarts it after a crash.

Wrap [`PostgresCache.cleanup_expired()`][psycache.PostgresCache.cleanup_expired] in a work unit and start it as an elected service (example requires `pgbg[sqlalchemy]`, but works with raw Psycopg, too):

```python
import pgbg

from pgbg.sqlalchemy import start_elected_service
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))

# *pgbg* requires a lease database; you only do this once.
with engine.connect() as conn:
    pgbg.init_db(conn.connection.driver_connection)


def cleanup_cache() -> bool:
    cache.cleanup_expired()

    return False  # done until the next interval


with start_elected_service(
    pgbg.as_work_factory(cleanup_cache),
    engine,
    name="psycache-cleanup",
    worker_id="worker-01.example.internal",  # unique per process
    wakeup=pgbg.IntervalOnlyWakeup(),
    interval=60,
):
    ...  # your application runs here

engine.dispose()
```

*pgbg* is thread-based and runs plain, non-async functions.
So pair it with the synchronous [`PostgresCache`][psycache.PostgresCache], even if the rest of your application is async.
