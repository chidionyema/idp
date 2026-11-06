#!/usr/bin/env python3
"""Reject cluster dumps that would restore zero user tables in the target database.

This is a *prefilter*, not proof of a successful restore. The existing post-restore
pg_class assertion remains mandatory. Only SQL syntax is inspected, never row data.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import shlex
import sys
from datetime import datetime, timedelta, timezone
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



def verified_copy_provenance(
    archive: str | Path, receipt_path: str | Path, object_name: str
) -> tuple[str, str]:
    """A re-dumped copy inherits its ORIGINAL data age, never its upload date.

    The receipt must describe the exact bytes fetched; a plausible date or a
    recent Object Storage modification timestamp is not provenance.
    """
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("receipt is not an object")
    if receipt.get("object") != object_name or receipt.get("complete") is not True:
        raise ValueError("receipt does not attest this complete copy")
    expected_size = receipt.get("bytes")
    expected_hash = receipt.get("sha256")
    if (
        isinstance(expected_size, bool) or not isinstance(expected_size, int)
        or expected_size <= 0
        or not isinstance(expected_hash, str)
        or re.fullmatch(r"[a-f0-9]{64}", expected_hash) is None
    ):
        raise ValueError("receipt missing trustworthy size or sha256")
    if Path(archive).stat().st_size != expected_size:
        raise ValueError("source copy size disagrees with receipt")
    digest = hashlib.sha256()
    with Path(archive).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_hash:
        raise ValueError("source copy sha256 disagrees with receipt")

    mode = receipt.get("mode")
    source = receipt.get("source")
    data_as_of = receipt.get("data_as_of")
    stamp = receipt.get("stamp")
    try:
        created_at = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError("receipt lacks a valid source-copy stamp") from exc
    if mode == "dump-from-running-cluster" and not data_as_of:
        # This was the ORIGINAL live dump; its stamp is a defensible RPO
        # witness, provided its bytes and metadata were verified above.
        data_as_of = created_at.isoformat()
        source = source or object_name
    elif mode != "restored-from-surviving-dump":
        raise ValueError("unrecognised copy lineage mode")
    if (
        not isinstance(source, str) or not source.endswith(".sql.gz")
        or not source.strip() or any(c.isspace() for c in source)
        or not isinstance(data_as_of, str) or not data_as_of.strip()
    ):
        raise ValueError("copy has no unambiguous original source and data age")
    try:
        data_time = datetime.fromisoformat(data_as_of.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("copy lineage has malformed data_as_of") from exc
    if data_time.tzinfo is None or data_time > created_at + timedelta(minutes=5):
        raise ValueError("copy data age is absent or newer than its provenance")
    if created_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError("copy stamp is in the future")
    return source, data_as_of


def main(argv: list[str]) -> int:
    if len(argv) == 5 and argv[1] == "--copy-provenance":
        try:
            source, as_of = verified_copy_provenance(argv[2], argv[3], argv[4])
        except (OSError, ValueError, TypeError) as error:
            print(f"untrusted source-copy receipt: {error}", file=sys.stderr)
            return 1
        print(source)
        print(as_of)
        return 0
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
