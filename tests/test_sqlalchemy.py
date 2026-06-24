# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import importlib.util
import secrets

import pytest

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache, PostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool, SQLAlchemyCachePool


@pytest.fixture(name="sqla_url")
def _sqla_url(db_dsn):
    return db_dsn.replace("postgresql", "postgresql+psycopg")


def test_sync_cache(sqla_url):
    """
    SQLAlchemyCachePool round-trips through the whole cache API.
    """
    engine = create_engine(sqla_url)
    cache = PostgresCache(SQLAlchemyCachePool(engine))

    key = secrets.token_urlsafe()

    assert cache.get_raw(key) is None

    cache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert {"foo": "bar"} == cache.get_raw(key)

    cache.remove(key)

    assert cache.get_raw(key) is None

    cache.put_raw("gone", {"v": 1}, ttl=-1)

    assert 1 == cache.cleanup_expired()

    cache.put_raw("here", {"v": 2}, ttl=10)

    assert 1 == cache.flush()

    engine.dispose()


@pytest.mark.skipif(
    not importlib.util.find_spec("greenlet") is not None,
    reason="sqlalchemy asyncio support requires greenlet",
)
@pytest.mark.asyncio
async def test_async_cache(sqla_url):
    """
    AsyncSQLAlchemyCachePool round-trips through the cache API.
    """

    engine = create_async_engine(sqla_url)
    cache = AsyncPostgresCache(AsyncSQLAlchemyCachePool(engine))

    key = secrets.token_urlsafe()

    assert await cache.get_raw(key) is None

    await cache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert {"foo": "bar"} == await cache.get_raw(key)

    await cache.remove(key)

    assert await cache.get_raw(key) is None

    await cache.put_raw("gone", {"v": 1}, ttl=-1)

    assert 1 == await cache.cleanup_expired()

    await cache.put_raw("here", {"v": 2}, ttl=10)

    assert 1 == await cache.flush()

    await engine.dispose()
