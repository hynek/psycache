# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import secrets

import pytest

from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool


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
