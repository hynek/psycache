# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Integration with SQLAlchemy.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

import attrs
import psycopg

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine


@attrs.frozen
class SQLAlchemyCachePool:
    """
    A cache pool based on a SQLAlchemy engine.
    """

    engine: Engine

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with self.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            yield conn.connection  # type: ignore[misc]  # ty: ignore[invalid-yield]


@attrs.frozen
class AsyncSQLAlchemyCachePool:
    """
    A cache pool based on a SQLAlchemy async engine.
    """

    engine: AsyncEngine

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[psycopg.AsyncConnection]:
        async with self.engine.connect() as sa_conn:
            conn = await sa_conn.execution_options(
                isolation_level="AUTOCOMMIT"
            )
            raw = await conn.get_raw_connection()

            yield raw.driver_connection  # type: ignore[misc]  # ty: ignore[invalid-yield]
