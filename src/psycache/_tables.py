# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import psycopg


_CREATE_TABLE = """\
CREATE UNLOGGED TABLE IF NOT EXISTS psycache (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    expires_at timestamptz NOT NULL
)
"""

_CREATE_INDEX = """\
CREATE INDEX IF NOT EXISTS ix_psycache_expires_at
    ON psycache (expires_at)
"""


def init_db(conn: psycopg.Connection) -> None:
    """
    Create the *psycache* table if it doesn't exist.

    Args:
        conn: A psycopg connection.
    """
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_INDEX)
