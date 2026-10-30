"""The estate database's copy service must actually copy, and must say how old the data is.

MEASURED 2026-10-30 (idp#7391). The estate's PostgreSQL cluster is gone -- OKE's free trial ended
on 2026-10-28 -- but its data survived as logical dumps in Object Storage:

    estate-db-backups/db/2026-09-08/estate-db-estate-1.sql.gz   39987605 bytes
    estate-db-backups/db/2026-09-08/estate-db-estate-2.sql.gz   39993684 bytes
    estate-db-backups/db/2026-09-08/temporal-temporal-db-0.sql.gz    82684 bytes

and no `estate-db/latest.json` anywhere, so bin/idp-estate-db-backup answered "the CronJob has
never completed a verified copy". The CronJob cannot run: it copies a cluster that is not there.
platform/estate-db/backup/estate-db-backup.sh is the copy service that runs against the data that
survived -- restore the newest dump into PostgreSQL 18, re-dump it, publish the copy and its
receipt.

So the falsifier here runs that script against a fake `oci` and checks the bytes that came out the
other end. Nothing is mocked above the OCI CLI boundary: the script's own argument handling, its
completion-marker check, its size-ratio refusal, its upload ordering and the receipt it writes are
all the real ones.

What each test is for:
  * select-source picks the NEWEST surviving dump, not the first, and not a non-dump;
  * the copy is uploaded BEFORE the receipt, and the receipt is written LAST, so the receipt's
    presence means the copy above it landed;
  * a dump without pg_dumpall's completion marker is never published;
  * a copy that collapsed against the previous receipt is refused;
  * a failed copy upload writes NO receipt -- a receipt without a copy is a lie;
  * the receipt says how old the data is, so a fresh stamp cannot pass for fresh data;
  * the workflow is thin, governed, and runs the script rather than reimplementing it.

These fail against a script that uploads the receipt first, publishes a truncated dump, ignores
the previous receipt's size, or writes the receipt after a failed upload.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "platform" / "estate-db" / "backup" / "estate-db-backup.sh"
WORKFLOW = REPO / ".github" / "workflows" / "estate-db-backup.yml"

DUMP_MARKER = "PostgreSQL database cluster dump complete"

FAKE_OCI = '''#!/usr/bin/env python3
"""A fake `oci` that records what it was asked to do, and keeps what it was given."""
import json, os, shutil, sys

args = sys.argv[1:]
if args[:1] == ["--auth"]:
    args = args[2:]


def opt(name, default=None):
    if name in args:
        return args[args.index(name) + 1]
    return default


bucket_dir = os.environ["FAKE_BUCKET_DIR"]
log_path = os.environ["FAKE_LOG"]
listing = os.environ.get("FAKE_LISTING", "")


def record(line):
    with open(log_path, "a") as fh:
        fh.write(line + "\\n")


if args[:2] == ["os", "ns"]:
    print(os.environ.get("FAKE_NAMESPACE", "lr7j97fk6nor"))
    sys.exit(0)

if args[:3] == ["os", "object", "list"]:
    print(listing)
    sys.exit(0)

if args[:3] == ["os", "object", "get"]:
    name = opt("--name")
    previous = os.environ.get("FAKE_PREVIOUS_RECEIPT")
    if name == os.environ.get("FAKE_PREVIOUS_NAME", "estate-db/latest.json") and previous:
        sys.stdout.write(previous)
        sys.exit(0)
    sys.stderr.write("NotFound\\n")
    sys.exit(1)

if args[:3] == ["os", "object", "put"]:
    name = opt("--name")
    source = opt("--file")
    fail_on = os.environ.get("FAKE_FAIL_PUT")
    if fail_on and fail_on in name:
        record("put-FAILED " + name)
        sys.stderr.write("ObjectStorageException: the copy did not land\\n")
        sys.exit(1)
    target = os.path.join(bucket_dir, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)
    record("put " + name)
    sys.exit(0)

sys.stderr.write("fake oci: unsupported call %r\\n" % (args,))
sys.exit(2)
'''


def _fake_oci(tmp_path: Path) -> Path:
    binary = tmp_path / "oci"
    binary.write_text(FAKE_OCI)
    binary.chmod(0o755)
    return binary


def _dump_bytes(marker: bool = True) -> bytes:
    body = b"-- PostgreSQL database cluster dump\n-- a line of data\n"
    if marker:
        body += ("-- " + DUMP_MARKER + "\n").encode()
    else:
        body += b"-- truncated\n"
    return gzip.compress(body, mtime=0)


def _listing(entries: list[tuple[str, str, int]]) -> str:
    return json.dumps(
        {
            "data": [
                {"name": name, "time-created": created, "size": size}
                for name, created, size in entries
            ]
        }
    )


def _run(
    tmp_path: Path,
    args: list[str],
    *,
    listing: str = "",
    previous: str = "",
    fail_put: str = "",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    _fake_oci(tmp_path)
    bucket_dir = tmp_path / "bucket"
    bucket_dir.mkdir(exist_ok=True)
    log = tmp_path / "oci.log"
    full_env = dict(os.environ)
    full_env.update(
        {
            "PATH": f"{tmp_path}:{full_env['PATH']}",
            "FAKE_BUCKET_DIR": str(bucket_dir),
            "FAKE_LOG": str(log),
            "FAKE_LISTING": listing,
            "FAKE_PREVIOUS_RECEIPT": previous,
            "FAKE_FAIL_PUT": fail_put,
            "ESTATE_DB_BACKUP_STAMP": "20261030T120000Z",
        }
    )
    full_env.update(env or {})
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full_env,
        timeout=120,
    )


def test_select_source_picks_the_newest_surviving_dump(tmp_path: Path) -> None:
    listing = _listing(
        [
            (
                "db/2026-09-08/estate-db-estate-1.sql.gz",
                "2026-09-08T12:34:57.359000+00:00",
                39987605,
            ),
            (
                "db/2026-09-08/temporal-temporal-db-0.sql.gz",
                "2026-09-08T12:35:10.524000+00:00",
                82684,
            ),
            (
                "estate-db/estate-20260909T030000Z.sql.gz",
                "2026-09-09T03:00:00.000000+00:00",
                41,
            ),
            ("estate-db/latest.json", "2026-09-09T03:00:01.000000+00:00", 12),
        ]
    )
    result = _run(tmp_path, ["select-source"], listing=listing)
    assert result.returncode == 0, result.stderr
    name, created, size = result.stdout.strip().split("\t")
    assert name == "estate-db/estate-20260909T030000Z.sql.gz"
    assert created == "2026-09-09T03:00:00.000000+00:00"
    assert size == "41"


def test_select_source_refuses_when_nothing_survived(tmp_path: Path) -> None:
    result = _run(tmp_path, ["select-source"], listing=_listing([]))
    assert result.returncode != 0
    assert "no surviving dump" in (result.stderr + result.stdout)


def test_publish_uploads_the_copy_then_the_receipt(tmp_path: Path) -> None:
    dump = tmp_path / "estate.sql.gz"
    payload = _dump_bytes()
    dump.write_bytes(payload)
    result = _run(tmp_path, ["publish", str(dump)])
    assert result.returncode == 0, result.stderr + result.stdout
    log = (tmp_path / "oci.log").read_text().splitlines()
    assert log == [
        "put estate-db/estate-20261030T120000Z.sql.gz",
        "put estate-db/latest.json",
    ], log
    receipt = json.loads(
        (tmp_path / "bucket" / "estate-db" / "latest.json").read_text()
    )
    assert receipt["stamp"] == "20261030T120000Z"
    assert receipt["object"] == "estate-db/estate-20261030T120000Z.sql.gz"
    assert receipt["bytes"] == len(payload)
    assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["complete"] is True


def test_the_receipt_says_how_old_the_data_is(tmp_path: Path) -> None:
    dump = tmp_path / "estate.sql.gz"
    payload = _dump_bytes()
    dump.write_bytes(payload)
    source = tmp_path / "source.sql.gz.source"
    source.write_text(
        "db/2026-09-08/estate-db-estate-1.sql.gz\n2026-09-08T12:34:57.359000+00:00\n"
    )
    result = _run(
        tmp_path,
        ["publish", str(dump)],
        env={"ESTATE_DB_SOURCE_FILE": str(source)},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    receipt = json.loads(
        (tmp_path / "bucket" / "estate-db" / "latest.json").read_text()
    )
    assert receipt["source"] == "db/2026-09-08/estate-db-estate-1.sql.gz"
    assert receipt["data_as_of"] == "2026-09-08T12:34:57.359000+00:00"
    assert receipt["mode"] == "restored-from-surviving-dump"


def test_publish_refuses_a_dump_without_the_completion_marker(tmp_path: Path) -> None:
    dump = tmp_path / "estate.sql.gz"
    dump.write_bytes(_dump_bytes(marker=False))
    result = _run(tmp_path, ["publish", str(dump)])
    assert result.returncode != 0
    assert "completion marker" in (result.stderr + result.stdout)
    assert not (tmp_path / "oci.log").exists()


def test_publish_refuses_a_copy_that_collapsed(tmp_path: Path) -> None:
    dump = tmp_path / "estate.sql.gz"
    dump.write_bytes(_dump_bytes())
    previous = json.dumps(
        {
            "stamp": "20261029T120000Z",
            "object": "estate-db/estate-20261029T120000Z.sql.gz",
            "bytes": 100000,
            "sha256": "x",
            "complete": True,
        }
    )
    result = _run(tmp_path, ["publish", str(dump)], previous=previous)
    assert result.returncode != 0
    assert "REFUSED" in (result.stderr + result.stdout)
    log = (tmp_path / "oci.log").read_text() if (tmp_path / "oci.log").exists() else ""
    assert "latest.json" not in log


def test_a_failed_copy_upload_writes_no_receipt(tmp_path: Path) -> None:
    dump = tmp_path / "estate.sql.gz"
    dump.write_bytes(_dump_bytes())
    result = _run(
        tmp_path, ["publish", str(dump)], fail_put="estate-20261030T120000Z.sql.gz"
    )
    assert result.returncode != 0
    log = (tmp_path / "oci.log").read_text() if (tmp_path / "oci.log").exists() else ""
    assert "latest.json" not in log
    assert not (tmp_path / "bucket" / "estate-db" / "latest.json").exists()


def test_the_workflow_is_thin_governed_and_orders_the_steps() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    job = workflow["jobs"]["backup"]
    steps = job["steps"]
    uses = [step.get("uses", "") for step in steps]
    assert any("oci-token-exchange-action" in use for use in uses), uses
    assert workflow["permissions"]["id-token"] == "write"
    assert job["services"]["postgres"]["image"].startswith(
        "ghcr.io/chidionyema/postgres-partman:18.1-postgres-partman"
    )
    names = [step.get("name", "") for step in steps]
    ordered = [
        name
        for name in names
        if name.startswith(("fetch", "restore", "dump", "publish", "the receipt"))
    ]
    assert ordered == [
        "fetch the newest surviving dump",
        "restore it into PostgreSQL 18",
        "dump it again",
        "publish the copy, then the receipt",
        "the receipt, graded from the backend",
    ], ordered
    for step in steps:
        run = step.get("run", "")
        if "estate-db-backup.sh" in run:
            assert "pg_dumpall" not in run, (
                "the workflow must not reimplement the copy in YAML"
            )


def test_the_script_owns_the_copy_contract() -> None:
    script = SCRIPT.read_text()
    for stage in ("select-source", "fetch-source", "restore", "dump", "publish"):
        assert f"\n{stage})" in script, stage
    assert DUMP_MARKER in script
    assert "estate-db/latest.json" in script
