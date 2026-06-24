# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import secrets

import pytest

from psycopg_pool import AsyncConnectionPool, ConnectionPool

from psycache import AsyncPostgresCache, PostgresCache
from psycache.psycopg_pool import (
    AsyncPsycopgCachePool,
    PsycopgCachePool,
)


def test_sync_cache(db_dsn):
    """
    PsycopgCachePool round-trips through the whole cache API.
    """
    cp = ConnectionPool(db_dsn, open=False)
    cp.open()
    cache = PostgresCache(PsycopgCachePool(cp))

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

    cp.close()


def test_sync_restores_autocommit():
    """
    The sync pool adapter leaves borrowed connections as it found them.
    """

    class FakeConnection:
        autocommit = False

    class FakePoolConnection:
        def __init__(self, conn):
            self.conn = conn

        def __enter__(self):
            return self.conn

        def __exit__(self, *args):
            return None

    class FakePool:
        def __init__(self, conn):
            self.conn = conn

        def connection(self):
            return FakePoolConnection(self.conn)

    conn = FakeConnection()
    pool = PsycopgCachePool(FakePool(conn))

    with pool.connect() as borrowed_conn:
        assert conn is borrowed_conn
        assert borrowed_conn.autocommit is True

    assert conn.autocommit is False

    with pytest.raises(RuntimeError), pool.connect():
        assert conn.autocommit is True
        raise RuntimeError

    assert conn.autocommit is False


@pytest.mark.asyncio
async def test_async_cache(db_dsn):
    """
    AsyncPsycopgCachePool round-trips through the cache API.
    """

    pool = AsyncConnectionPool(db_dsn, open=False)
    await pool.open()
    cache = AsyncPostgresCache(AsyncPsycopgCachePool(pool))

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

    await pool.close()


@pytest.mark.asyncio
async def test_async_restores_autocommit():
    """
    The async pool adapter leaves borrowed connections as it found them.
    """

    class FakeConnection:
        autocommit = False

        async def set_autocommit(self, value):
            self.autocommit = value

    class FakePoolConnection:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *args):
            return None

    class FakePool:
        def __init__(self, conn):
            self.conn = conn

        def connection(self):
            return FakePoolConnection(self.conn)

    conn = FakeConnection()
    pool = AsyncPsycopgCachePool(FakePool(conn))

    async with pool.connect() as borrowed_conn:
        assert conn is borrowed_conn
        assert borrowed_conn.autocommit is True

    assert conn.autocommit is False

    with pytest.raises(RuntimeError):
        async with pool.connect():
            assert conn.autocommit is True
            raise RuntimeError

    assert conn.autocommit is False
