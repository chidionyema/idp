#!/usr/bin/env python3
"""Reject cluster dumps that would restore zero user tables in the target database.

This is a *prefilter*, not proof of a successful restore. The existing post-restore
pg_class assertion remains mandatory. Only SQL syntax is inspected, never row data.
"""
from __future__ import annotations

import gzip
import re
import shlex
import sys
from pathlib import Path

_TABLE_DDL = re.compile(r"^CREATE\s+(?:UNLOGGED\s+)?TABLE\s", re.IGNORECASE)
_CONNECT = re.compile(r"^\\connect(?:\s|$)")
_CONN_DB = re.compile(r"\bdbname\s*=\s*['\"]?([^'\"\s]+)")


def _connection_database(command: str) -> str | None:
    body = command[len("\\connect"):].strip()
    match = _CONN_DB.search(body)
    if match:
        return match.group(1)
    try:
        tokens = shlex.split(body)
    except ValueError:
        return None
    names = [token for token in tokens if not token.startswith("-")]
    return names[0] if names else None


def count_target_table_definitions(archive: str | Path, database: str) -> int:
    """Count table DDL *after* an explicit \\connect to the requested database."""
    if not database or any(char.isspace() for char in database):
        raise ValueError("database name must be nonblank and contain no whitespace")
    active_database: str | None = None
    count = 0
    with gzip.open(archive, "rt", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if _CONNECT.match(line):
                active_database = _connection_database(line)
            elif active_database == database and _TABLE_DDL.match(line):
                count += 1
    return count


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: verify_source_schema.py ARCHIVE DATABASE", file=sys.stderr)
        return 2
    try:
        count = count_target_table_definitions(argv[1], argv[2])
    except (OSError, EOFError, ValueError, gzip.BadGzipFile) as error:
        print(f"source schema unreadable: {type(error).__name__}", file=sys.stderr)
        return 2
    if count == 0:
        print(f"no target-scoped CREATE TABLE found for database {argv[2]}", file=sys.stderr)
        return 1
    print(f"TARGET_TABLE_DDL_COUNT={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
