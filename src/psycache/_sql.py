# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

GET = """\
SELECT value, pg_column_size(value)
FROM psycache
WHERE key = %s
  AND expires_at > statement_timestamp()
"""

PUT = """\
INSERT INTO psycache (key, value, expires_at)
VALUES (%s, %s, %s)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    expires_at = EXCLUDED.expires_at
RETURNING pg_column_size(value)
"""

REMOVE = """\
DELETE FROM psycache
WHERE key = %s
"""

CLEANUP_EXPIRED = """\
DELETE FROM psycache
WHERE expires_at < statement_timestamp()
"""

FLUSH = """\
DELETE FROM psycache
"""
