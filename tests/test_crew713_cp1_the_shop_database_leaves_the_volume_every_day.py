"""crew#713 CP1: the shop's database is copied off its volume every day, by the cluster.

The whole shop is one SQLite file on one ReadWriteOnce block volume. Census taken inside the
running pod on 2026-08-31: 23 tables, 202 packs, 76 price-history rows, 41,035 analytics events,
3 orders, 2 entitlements, 1 account, 5,324,800 bytes. Nothing copied it anywhere; the offsite
sources the estate declares for it are written by Mac launchd jobs that are not loaded.

These are properties of the copy, not of the manifest's wording. The refusal rules are proved by
running the job's own embedded script against fixture databases and watching it refuse, because a
backup job that reports success while copying an empty database is the failure this row exists to
stop, and a test that greps for the word "REFUSED" would pass on a job that never refuses.
"""

import datetime
import json
import pathlib
import re
import sqlite3
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/prospector/store-db-backup.yaml"
TERRAFORM = ROOT / "platform/oci/shop-backups.tf"
BUCKET = "estate-shop-backups"


def _cronjob():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    jobs = [d for d in docs if d["kind"] == "CronJob"]
    assert len(jobs) == 1, [d["kind"] for d in docs]
    return jobs[0]


def _pod():
    return _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _script():
    return _pod()["containers"][0]["args"][0]


def _embedded_python():
    """The python the job runs, lifted out of its shell heredoc."""
    lines = _script().splitlines()
    start = next(i for i, l in enumerate(lines) if l.endswith("<<'PY'"))
    end = next(i for i, l in enumerate(lines) if i > start and l == "PY")
    # The terminator sits at column 0 after YAML strips the block indent, which is the only way
    # the shell ends a quoted heredoc; if that ever stops being true the slice below is empty.
    body = "\n".join(lines[start + 1 : end])
    assert "sqlite3.connect" in body, body[:200]
    return body


def _fixture_db(path, packs, rows=1):
    db = sqlite3.connect(path)
    db.execute("create table Packs (Id integer primary key)")
    for table in ("AspNetUsers", "Orders", "Entitlements", "AnalyticsEvents"):
        db.execute(f"create table {table} (Id integer primary key)")
        db.executemany(
            f"insert into {table} (Id) values (?)",  # noqa: S608 -- table names are this file's own fixtures
            [(i,) for i in range(rows)],
        )
    db.executemany("insert into Packs (Id) values (?)", [(i,) for i in range(packs)])
    db.commit()
    db.close()


def _run(tmp_path, packs, previous=None, ratio="0.5", pad=0):
    """Run the job's own script against a fixture, with only its four paths redirected."""
    source = tmp_path / "source.db"
    _fixture_db(source, packs, rows=1 + pad)
    code = (
        _embedded_python()
        .replace("/data/store.db", str(source))
        # noqa lines: these four are the paths INSIDE the pod, which this test redirects at
        # its own temporary directory. Nothing here opens a file on the machine running the test.
        .replace("/tmp/store.db", str(tmp_path / "copy.db"))  # noqa: S108
        .replace("/tmp/previous.json", str(tmp_path / "previous.json"))  # noqa: S108
        .replace("/tmp/receipt.json", str(tmp_path / "receipt.json"))  # noqa: S108
    )
    (tmp_path / "previous.json").write_text(json.dumps(previous) if previous else "")
    done = subprocess.run(
        [sys.executable, "-c", code, "20260831T000000Z"],
        capture_output=True,
        text=True,
        env={"MIN_SIZE_RATIO": ratio, "PATH": "/usr/bin:/bin"},
    )
    return done


def test_a_verified_copy_is_made_and_leaves_a_receipt(tmp_path):
    done = _run(tmp_path, packs=202)
    assert done.returncode == 0, done.stderr
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["integrity"] == "ok"
    assert receipt["packs"] == 202
    assert receipt["object"] == "shop/store-20260831T000000Z.db"
    assert len(receipt["sha256"]) == 64
    assert receipt["bytes"] == (tmp_path / "copy.db").stat().st_size
    # The copy is a real database, not a truncated file: it opens and answers.
    assert (
        sqlite3.connect(tmp_path / "copy.db")
        .execute("select count(*) from Packs")
        .fetchone()[0]
        == 202
    )


def test_an_empty_catalogue_is_refused_rather_than_uploaded(tmp_path):
    """The 2026-08-25 restore: a stale write-ahead log replayed over the file and /catalog
    answered [] with 78 packs on disk. An empty catalogue reads as a successful copy."""
    done = _run(tmp_path, packs=0)
    assert done.returncode != 0
    assert "REFUSED" in done.stderr and "catalogue is empty" in done.stderr
    assert not (tmp_path / "receipt.json").exists()


def test_a_collapsed_file_is_refused_against_yesterdays_receipt(tmp_path):
    done = _run(
        tmp_path, packs=1, previous={"bytes": 5_324_800, "stamp": "20260830T031700Z"}
    )
    assert done.returncode != 0
    assert "REFUSED" in done.stderr and "5324800" in done.stderr
    assert not (tmp_path / "receipt.json").exists()


def test_the_first_run_has_no_previous_receipt_and_that_is_not_a_failure(tmp_path):
    assert _run(tmp_path, packs=202, previous=None).returncode == 0


def test_the_shrink_floor_is_a_setting_not_a_constant(tmp_path):
    """Founder 2026-08-31, "configurable obvs": a verification threshold is configuration."""
    body = _embedded_python()
    assert 'os.environ["MIN_SIZE_RATIO"]' in body, (
        "the floor is read, not written into the code"
    )
    assert not re.search(r"floor\s*=\s*[0-9.]", body), (
        "a threshold spelled as a number is not a setting"
    )
    env = {e["name"]: e["value"] for e in _pod()["containers"][0]["env"]}
    assert 0 < float(env["MIN_SIZE_RATIO"]) < 1
    assert env["BUCKET"] == BUCKET


def test_the_copy_cannot_write_to_the_shop_volume():
    pod = _pod()
    data = [v for v in pod["volumes"] if v["name"] == "data"][0]
    assert data["persistentVolumeClaim"] == {
        "claimName": "prospector-store-api-data",
        "readOnly": True,
    }
    mount = [m for m in pod["containers"][0]["volumeMounts"] if m["name"] == "data"][0]
    assert mount["readOnly"] is True
    security = pod["containers"][0]["securityContext"]
    assert security["readOnlyRootFilesystem"] is True
    assert security["allowPrivilegeEscalation"] is False
    assert security["capabilities"]["drop"] == ["ALL"]
    assert pod["securityContext"]["runAsNonRoot"] is True
    # The image declares its user by name, and a kubelet refuses runAsNonRoot without a number.
    assert isinstance(pod["securityContext"]["runAsUser"], int)


def test_the_copy_follows_the_volume_rather_than_pinning_a_machine():
    """ReadWriteOnce means the pod must land on the node holding it. Naming the node would pin the
    backup to a machine the autoscaler can replace."""
    pod = _pod()
    assert "nodeName" not in pod and "nodeSelector" not in pod
    rule = pod["affinity"]["podAffinity"][
        "requiredDuringSchedulingIgnoredDuringExecution"
    ][0]
    assert rule["topologyKey"] == "kubernetes.io/hostname"
    assert (
        rule["labelSelector"]["matchLabels"]["app.kubernetes.io/name"]
        == "prospector-store-api"
    )


def test_it_runs_at_least_daily_because_the_grader_calls_it_stale_past_a_day():
    minute, hour, dom, month, dow = _cronjob()["spec"]["schedule"].split()
    assert dom == "*" and month == "*" and dow == "*", (
        "a copy that skips days is a stale source"
    )
    assert "*" not in (minute, hour), (
        "the shop database is copied once a day, not every minute"
    )
    assert _cronjob()["spec"]["concurrencyPolicy"] == "Forbid"


def test_no_credential_reaches_the_pod():
    """The node's own identity is authorised for one bucket. Nothing is mounted, nothing is set."""
    container = _pod()["containers"][0]
    assert "envFrom" not in container
    assert all("valueFrom" not in e for e in container["env"])
    assert {v["name"] for v in _pod()["volumes"]} == {"data", "tmp"}
    assert "--auth instance_principal" in _script()


@pytest.mark.parametrize(
    "needle",
    [
        'name           = "${var.cluster_name}-shop-backups"',
        'access_type    = "NoPublicAccess"',
        'versioning = "Enabled"',
    ],
)
def test_the_bucket_is_private_and_keeps_history(needle):
    assert needle in TERRAFORM.read_text()


def test_retention_is_declared_and_configurable():
    body = TERRAFORM.read_text()
    assert "oci_objectstorage_object_lifecycle_policy" in body
    assert "time_amount = var.shop_backup_retention_days" in body
    variables = (ROOT / "platform/oci/variables.tf").read_text()
    assert 'variable "shop_backup_retention_days"' in variables


def test_the_nodes_may_touch_this_bucket_and_no_other():
    statements = [
        l for l in TERRAFORM.read_text().splitlines() if l.strip().startswith('"Allow ')
    ]
    assert len(statements) == 1, statements
    assert "manage objects" in statements[0]
    assert (
        "target.bucket.name='${oci_objectstorage_bucket.shop_backups.name}'"
        in statements[0]
    )


# --- CP3: the copy is graded from the backend, and the grade is read ------------------------

GRADER = ROOT / "bin/idp-shop-backup"


def _grade(tmp_path, receipt, hours="26"):
    """Run the grader's own judgement against a receipt, without a cloud session.

    The shell half fetches shop/latest.json; this is the half that decides, and it is the half
    that can be wrong in a way nobody notices until a restore.
    """
    lines = GRADER.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.endswith("<<'PY'"))
    end = next(i for i, l in enumerate(lines) if i > start and l == "PY")
    body = "\n".join(lines[start + 1 : end])
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(receipt))
    return subprocess.run(
        [sys.executable, "-c", body, str(path), hours, ""],
        capture_output=True,
        text=True,
    )


def _receipt(age_hours=1.0, **overrides):
    stamp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=age_hours
    )
    return {
        "stamp": stamp.strftime("%Y%m%dT%H%M%SZ"),
        "integrity": "ok",
        "bytes": 5_324_800,
        "packs": 202,
        "orders": 3,
        "accounts": 1,
        **overrides,
    }


def test_a_fresh_verified_copy_grades_ok(tmp_path):
    done = _grade(tmp_path, _receipt())
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("ok      shop-backup")
    assert "202 packs" in done.stdout


@pytest.mark.parametrize(
    "receipt,because",
    [
        (_receipt(age_hours=48), "the last copy is"),
        (_receipt(integrity="*** in database main"), "integrity_check answered"),
        (_receipt(packs=0), "the copied catalogue is empty"),
    ],
)
def test_a_copy_that_would_not_restore_grades_red(tmp_path, receipt, because):
    done = _grade(tmp_path, receipt)
    assert done.returncode == 1, done.stdout
    assert done.stdout.startswith("FAIL    shop-backup") and because in done.stdout


def test_the_drill_is_named_and_owned_and_runs_daily():
    """crew#684 CP3: a drill with no owner is refused. The founder reads this row on the Ops page."""
    catalogue = yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())
    row = [d for d in catalogue["drills"] if d["name"] == "shop-backup"]
    assert len(row) == 1
    row = row[0]
    assert row["owner"] and row["proves"].strip()
    assert row["max_age_hours"] <= 26
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows" / row["workflow"]).read_text()
    )
    job = workflow["jobs"][row["job"]]
    assert row["schedule"] in [s["cron"] for s in workflow[True]["schedule"]]
    assert any(
        step.get("run", "").strip() == "bin/idp-shop-backup" for step in job["steps"]
    )


def test_the_runbook_and_the_job_cannot_drift_apart():
    """R54: a runbook per change, and a test that pins it to what the change actually does."""
    runbook = (ROOT / "docs/how-to/restore-the-shop-database.md").read_text()
    for needle in (
        BUCKET,  # the bucket the job writes
        "shop/latest.json",  # the receipt the job writes last
        "prospector-store-api-data",  # the claim being restored
        _cronjob()["spec"]["schedule"],  # when the copy is made
        "store.db-wal",  # the 2026-08-25 trap
        "shop_backup_retention_days",  # how long a copy is kept
    ):
        assert needle in runbook, needle
    # Restoring is destructive and stops for a person; a runbook that lost that line is wrong.
    assert "needs the founder's word first" in runbook


def test_the_row_is_applied_by_flux_and_not_by_a_hand():
    kustomization = yaml.safe_load(
        (ROOT / "platform/prospector/kustomization.yaml").read_text()
    )
    assert "store-db-backup.yaml" in kustomization["resources"]
