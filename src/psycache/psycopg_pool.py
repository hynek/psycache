# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Integration with [`psycopg_pool`](https://www.psycopg.org/psycopg3/docs/api/pool.html).
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import attrs
import psycopg

from psycopg_pool import AsyncConnectionPool, ConnectionPool


@attrs.frozen
class PsycopgCachePool:
    """
    A cache pool based on `psycopg_pool.ConnectionPool`.
    """

    _pool: ConnectionPool[Any] = attrs.field(alias="pool")

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with self._pool.connection() as conn:
            autocommit = conn.autocommit
            conn.autocommit = True

            try:
                yield conn
            finally:
                conn.autocommit = autocommit


@attrs.frozen
class AsyncPsycopgCachePool:
    """
    A cache pool based on `psycopg_pool.AsyncConnectionPool`.
    """

    _pool: AsyncConnectionPool[Any] = attrs.field(alias="pool")

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[psycopg.AsyncConnection]:
        async with self._pool.connection() as conn:
            autocommit = conn.autocommit
            await conn.set_autocommit(True)

            try:
                yield conn
            finally:
                await conn.set_autocommit(autocommit)
