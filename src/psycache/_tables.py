# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import psycopg

from . import _sql


def init_db(conn: psycopg.Connection, *, schema: str | None = None) -> None:
    """
    Create the *psycache* table if it doesn't exist.

    Args:
        conn: A psycopg connection.

        schema:
            The PostgreSQL schema in which to create the cache table. If
            `None`, the table is created using the connection's current
            default schema.

    Changes:
        - **26.3.0**: added *schema* parameter
    """
    conn.execute(_sql.create_table(schema))
    conn.execute(_sql.create_index(schema))
