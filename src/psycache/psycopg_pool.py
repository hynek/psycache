# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Integration with [`psycopg_pool`](https://www.psycopg.org/psycopg3/docs/api/pool.html).
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import psycopg

from psycopg_pool import AsyncConnectionPool, ConnectionPool


class PsycopgCachePool:
    """
    A cache pool based on `psycopg_pool.ConnectionPool`.
    """

    __slots__ = ("_pool",)

    _pool: ConnectionPool[Any]

    def __init__(self, pool: ConnectionPool[Any]) -> None:
        self._pool = pool

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with self._pool.connection() as conn:
            autocommit = conn.autocommit
            conn.autocommit = True

            try:
                yield conn
            finally:
                conn.autocommit = autocommit


class AsyncPsycopgCachePool:
    """
    A cache pool based on `psycopg_pool.AsyncConnectionPool`.
    """

    __slots__ = ("_pool",)

    _pool: AsyncConnectionPool[Any]

    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self._pool = pool

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[psycopg.AsyncConnection]:
        async with self._pool.connection() as conn:
            autocommit = conn.autocommit
            await conn.set_autocommit(True)

            try:
                yield conn
            finally:
                await conn.set_autocommit(autocommit)
