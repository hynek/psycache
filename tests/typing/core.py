import datetime as dt

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from psycache import PostgresCache, init_db


dsn = "postgresql://psycache@127.0.0.1/psycache"

with psycopg.connect(dsn, autocommit=True) as conn:
    init_db(conn)


class RawCachePool:
    dsn: str

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            yield conn


cache = PostgresCache(RawCachePool(dsn))

cache.put_raw("user:alice", {"score": 42}, ttl=300)
cache.put_raw("other-key", {"data": "value"}, ttl=dt.timedelta(hours=1))

value = cache.get_raw("user:alice")
cache.put_raw(
    "user:alice", {"name": "alice"}, ttl=300, span_name="store user score"
)
value = cache.get_raw("user:alice", span_name="look up user score")
