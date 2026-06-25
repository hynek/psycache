---
icon: material/raw
---


# Raw Queries

[`PostgresCache`][psycache.PostgresCache] speaks plain dictionaries: you hand it JSON-serializable values and it stores them as [JSONB](https://www.postgresql.org/docs/current/datatype-json.html).
This page covers the low-level methods.

All examples below use this cache:

```python
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))
```


## Storing and retrieving

[`put_raw()`][psycache.PostgresCache.put_raw] stores a value under a key with a time-to-live.
[`get_raw()`][psycache.PostgresCache.get_raw] reads it back and returns `None` if the key is missing or has expired:

```python
cache.put_raw("user:alice", {"score": 42}, ttl=300)

value = cache.get_raw("user:alice")
# {"score": 42}
```

The TTL can be an `int` number of seconds or a [`datetime.timedelta`][datetime.timedelta]:

```python
import datetime as dt


cache.put_raw("other-key", {"data": "value"}, ttl=dt.timedelta(hours=1))
```


## Span names

Both `get_raw()` and `put_raw()` accept an optional *span_name* argument that is passed to [instrumentation](instrumentation/index.md).
Sentry uses it as the span name; Prometheus adds it as a label.

```python
cache.put_raw(
    "user:alice", {"name": "alice"}, ttl=300, span_name="store user score"
)
value = cache.get_raw("user:alice", span_name="look up user score")
```


## Removing entries

*psycache* ignores expired keys on read, but you still need ways to delete keys explicitly:

```python
# Remove a single key.
cache.remove("user:alice")

# Delete all currently-expired entries and return how many were removed.
num_deleted = cache.cleanup_expired()

# Delete everything and return how many were removed.
num_flushed = cache.flush()

engine.dispose()
```

To delete expired entries continuously in the background instead of calling [`cleanup_expired()`][psycache.PostgresCache.cleanup_expired] yourself, see [Background Cleanup](cleanup.md).

---

Now all of this is a bit tedious, so let's go for a more ergonomic, typed interface, in [Quality of Life](quality-of-life.md).
