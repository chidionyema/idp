"""idp#7391: bin/idp-estate-db-backup grades the receipt the estate-db CronJob writes."""

import json
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GRADER = ROOT / "bin" / "idp-estate-db-backup"


def grade(tmp_path, receipt, last_modified, now, max_hours="26"):
    head = tmp_path / "head.json"
    body = tmp_path / "body.json"
    head.write_text(json.dumps({"last-modified": last_modified, "date": now}))
    body.write_text(json.dumps(receipt))
    env = dict(
        os.environ,
        ESTATE_DB_BACKUP_HEAD_FILE=str(head),
        ESTATE_DB_BACKUP_BODY_FILE=str(body),
        ESTATE_DB_BACKUP_MAX_AGE_HOURS=max_hours,
    )
    return subprocess.run([str(GRADER)], capture_output=True, text=True, env=env)


GOOD = {
    "stamp": "20261029T034100Z", "bytes": 1000, "complete": True,
    "mode": "restored-from-surviving-dump",
    "source": "db/2026-10-29/estate-db-estate.sql.gz",
    "data_as_of": "2026-10-29T03:41:00+00:00",
}
T0 = "Thu, 29 Oct 2026 03:41:00 GMT"


def test_fresh_complete_receipt_is_ok(tmp_path):
    r = grade(tmp_path, GOOD, T0, "Thu, 29 Oct 2026 10:41:00 GMT")
    assert r.returncode == 0 and r.stdout.startswith("ok"), r.stdout + r.stderr


def test_stale_receipt_fails(tmp_path):
    r = grade(tmp_path, GOOD, T0, "Sat, 31 Oct 2026 10:41:00 GMT")
    assert r.returncode == 1 and "FAIL" in r.stdout and "old" in r.stdout


def test_incomplete_dump_fails(tmp_path):
    r = grade(tmp_path, dict(GOOD, complete=False), T0, "Thu, 29 Oct 2026 04:41:00 GMT")
    assert r.returncode == 1 and "not marked complete" in r.stdout


def test_empty_dump_fails(tmp_path):
    r = grade(tmp_path, dict(GOOD, bytes=0), T0, "Thu, 29 Oct 2026 04:41:00 GMT")
    assert r.returncode == 1 and "empty" in r.stdout


def test_receipt_without_stamp_is_blind(tmp_path):
    r = grade(
        tmp_path, {"bytes": 5, "complete": True}, T0, "Thu, 29 Oct 2026 04:41:00 GMT"
    )
    assert r.returncode != 0 and "BLIND" in r.stdout + r.stderr



def test_recent_copy_cannot_certify_two_month_old_data(tmp_path):
    receipt = dict(GOOD, stamp="20261106T193738Z",
                   source="db/2026-09-08/estate-db-estate-2.sql.gz",
                   data_as_of="2026-09-08T12:35:08.967000+00:00")
    r = grade(tmp_path, receipt, "Fri, 06 Nov 2026 19:37:45 GMT",
              "Fri, 06 Nov 2026 19:40:00 GMT")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "recovery point is" in r.stdout and "copy is 0.0 h old" in r.stdout
    assert "2026-09-08T12:35:08.967000+00:00" in r.stdout
    assert "db/2026-09-08/estate-db-estate-2.sql.gz" in r.stdout


def test_age_uses_object_store_date_not_local_rtc(tmp_path):
    receipt = dict(GOOD)
    receipt["data_as_of"] = "2027-02-01T01:00:00+00:00"
    r = grade(tmp_path, receipt, "Mon, 01 Feb 2027 01:00:00 GMT",
              "Mon, 01 Feb 2027 02:00:00 GMT")
    assert r.returncode == 0 and "recovery point 1.0 h old" in r.stdout


def test_unknown_original_source_fails_blind_not_green(tmp_path):
    missing = dict(GOOD, source=None)
    r = grade(tmp_path, missing, T0, "Thu, 29 Oct 2026 04:41:00 GMT")
    assert r.returncode == 2 and "BLIND" in r.stdout
    bad_clock = dict(GOOD, data_as_of="yesterday")
    r = grade(tmp_path, bad_clock, T0, "Thu, 29 Oct 2026 04:41:00 GMT")
    assert r.returncode == 2 and "cannot measure" in r.stdout


def test_future_source_time_is_untrustworthy(tmp_path):
    receipt = dict(GOOD, data_as_of="2026-10-30T03:41:00+00:00")
    r = grade(tmp_path, receipt, T0, "Thu, 29 Oct 2026 04:41:00 GMT")
    assert r.returncode == 2 and "future" in r.stdout


def test_live_cluster_dump_proves_its_own_timestamp(tmp_path):
    live = dict(GOOD, mode="dump-from-running-cluster",
                source=None, data_as_of=None)
    r = grade(tmp_path, live, T0, "Thu, 29 Oct 2026 05:41:00 GMT")
    assert r.returncode == 0 and "recovery point 2.0 h old" in r.stdout


def test_cronjob_is_wired_and_uses_no_block_volume():
    docs = list(
        yaml.safe_load_all(
            (ROOT / "platform/estate-db/backup/cronjob.yaml").read_text()
        )
    )
    spec = docs[0]["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert all("persistentVolumeClaim" not in v for v in spec["volumes"])
    flux = yaml.safe_load_all((ROOT / "clusters/oke/estate-db.yaml").read_text())
    assert any(d and d["metadata"]["name"] == "estate-db-backup" for d in flux)
