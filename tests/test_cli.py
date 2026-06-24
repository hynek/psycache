# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import psycopg
import pytest

from psycache.__main__ import main


def test_init_db_creates_table(db_dsn: str):
    """
    `init-db` creates the psycache table and is idempotent.
    """
    with psycopg.connect(db_dsn, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS psycache")

    assert 0 == main(["init-db", db_dsn])

    with psycopg.connect(db_dsn, autocommit=True) as conn:
        regclass = conn.execute("SELECT to_regclass('psycache')").fetchone()[0]

    assert "psycache" == regclass

    # Running it again against an existing table is a no-op.
    assert 0 == main(["init-db", db_dsn])


def test_init_db_reports_connection_failure(
    capsys: pytest.CaptureFixture[str],
):
    """
    A connection error is reported on stderr and exits non-zero.
    """
    assert 1 == main(["init-db", "postgresql://nope@127.0.0.1:1/nope"])

    assert "init-db failed" in capsys.readouterr().err


def test_requires_a_command():
    """
    Invoking without a subcommand is an argparse usage error.
    """
    with pytest.raises(SystemExit):
        main([])
