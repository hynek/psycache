# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import psycopg

from . import _sql


def init_db(conn: psycopg.Connection, table: str = "psycache") -> None:
    """
    Create the *psycache* table if it doesn't exist.

    Args:
        conn: A psycopg connection.

        table:
            The name of the cache table, optionally schema-qualified with a
            dot (for example, `"app_cache.psycache"`).

    Changes:
        - **26.3.0**: added *schema* parameter
        - **26.4.0**: replaced *schema* with *table*
    """
    conn.execute(_sql.create_table(table))
    conn.execute(_sql.create_index(table))
