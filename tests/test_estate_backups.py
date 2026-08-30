"""bin/estate-backups: every backup source in the bucket, newest stamp first, or BLIND.

Founder, 2026-08-30: "I would like to see all of our backups are in backoffice with timestamp".
Pinned here: the grouping follows the offsite declaration's layout, the newest object wins,
stalest source sorts first, and an unreadable listing is BLIND with a reason, never an empty
table (silent-green).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-backups"

spec = importlib.util.spec_from_loader("estate_backups", loader=None)
eb = importlib.util.module_from_spec(spec)
eb.__file__ = str(BIN)
exec(compile(BIN.read_text(), str(BIN), "exec"), eb.__dict__)  # noqa: S102 - the script under test, no other input

LISTING = [
    {"Path": "offsite", "IsDir": True, "ModTime": "2026-08-29T02:50:19Z", "Size": -1},
    {
        "Path": "offsite/money-db/store-20260828T025019Z.db",
        "Size": 4700000,
        "ModTime": "2026-08-28T02:50:19.123456789Z",
        "IsDir": False,
    },
    {
        "Path": "offsite/money-db/store-20260829T025019Z.db",
        "Size": 4702208,
        "ModTime": "2026-08-29T02:50:19.000000000Z",
        "IsDir": False,
    },
    {
        "Path": "offsite/agent-estate/claude-20260829T025326Z.tgz",
        "Size": 10,
        "ModTime": "2026-08-29T02:53:26Z",
        "IsDir": False,
    },
    {
        "Path": "db/prospector-2026-08-23.db.gz",
        "Size": 5,
        "ModTime": "2026-08-23T00:00:00Z",
        "IsDir": False,
    },
    {
        "Path": "repo/2026-08-30T024107Z.bundle",
        "Size": 7,
        "ModTime": "2026-08-30T02:41:07Z",
        "IsDir": False,
    },
]
TAKEN = "2026-08-30T10:30Z"


def test_sources_group_by_the_offsite_layout_and_the_newest_object_wins():
    doc = eb.document(LISTING, "prospector-backup", TAKEN)
    assert doc["state"] == "ok"
    by = {r["name"]: r for r in doc["sources"]}
    assert set(by) == {"money-db", "agent-estate", "engine-db", "engine-repo"}
    assert by["money-db"]["copies"] == 2
    assert by["money-db"]["newest"].endswith("store-20260829T025019Z.db")
    assert by["money-db"]["newest_at"] == "2026-08-29T02:50:19Z"
    assert by["money-db"]["bytes"] == 4700000 + 4702208


def test_oldest_newest_copy_sorts_first_so_the_page_leads_with_the_risk():
    doc = eb.document(LISTING, "prospector-backup", TAKEN)
    assert [r["name"] for r in doc["sources"]] == [
        "engine-db",
        "money-db",
        "agent-estate",
        "engine-repo",
    ]


def test_no_listing_is_blind_with_a_reason_never_an_empty_table():
    doc = eb.document(
        None,
        "prospector-backup",
        TAKEN,
        "rclone lsjson exit 3: AccessDenied",
    )
    assert doc["state"] == "BLIND"
    assert "AccessDenied" in doc["reason"]
    assert doc["sources"] == []


def test_cli_writes_the_sidecar_from_a_listing_file(tmp_path):
    listing = tmp_path / "l.json"
    listing.write_text(json.dumps(LISTING))
    out = tmp_path / "docs" / "backups.json"
    p = subprocess.run(
        [
            sys.executable,
            str(BIN),
            "--listing",
            str(listing),
            "--out",
            str(out),
            "--taken",
            TAKEN,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, p.stderr
    assert "ok    estate-backups: 4 source(s)" in p.stdout
    doc = json.loads(out.read_text())
    # no age anywhere: the page measures it against the viewer's clock (crew#583)
    assert all("age_hours" not in r for r in doc["sources"])
    assert doc["taken"] == "2026-08-30T10:30Z"
    assert doc["bucket"] == "prospector-backup"


def test_cli_with_no_listing_and_no_credentials_is_blind_and_exit_0(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("RCLONE_S3_ACCESS_KEY_ID", raising=False)
    out = tmp_path / "backups.json"
    p = subprocess.run(
        [sys.executable, str(BIN), "--out", str(out), "--taken", TAKEN],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert p.returncode == 0
    assert p.stdout.startswith("BLIND")
    assert json.loads(out.read_text())["state"] == "BLIND"


def test_the_script_never_reads_this_machines_clock():
    assert "datetime.now" not in BIN.read_text()


def test_rclone_nanosecond_stamps_parse():
    assert (
        eb.parse_stamp("2026-08-29T02:50:19.123456789Z").strftime("%H:%M:%S.%f")
        == "02:50:19.123456"
    )
    assert (
        eb.parse_stamp("2026-08-29T02:50:19+01:00").strftime("%H:%M:%SZ") == "01:50:19Z"
    )
    assert eb.parse_stamp("not a stamp") is None
