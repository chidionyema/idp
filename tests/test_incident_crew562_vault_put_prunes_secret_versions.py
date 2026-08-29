"""crew#562 (LAW 45): OCI caps a secret at 30 active versions + 30 pending deletion. The hourly
GitHub-App token re-mint (crew#577) filled hermes-agent-env in ~30 h and oke-check apply run
33222486010 (2026-08-29) died on "LimitExceeded" before the founder-screen step ran. The class: a
rotated secret whose old versions nobody retires. `bin/idp-cloud secret put` now prunes deprecated
versions before every update. Proved against a fake `oci` on PATH, not by reading the script."""
from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

FAKE_OCI = r'''#!/usr/bin/env bash
# fake oci: 30 live versions on one secret, records every schedule-deletion
log="$FAKE_LOG"
case "$*" in
  *"vault secret list"*) echo '["ocid1.vaultsecret.oc1..fake"]';;
  *"secret-version list"*) cat "$FAKE_VERSIONS";;
  *"secret-version schedule-deletion"*) echo "$*" >> "$log";;
  *"secret update-base64"*) echo "update $*" >> "$log"; echo '{}';;
  *"secret-bundle get"*) cat "$FAKE_BUNDLE";;
  *) echo "unexpected: $*" >&2; exit 1;;
esac
'''


def _versions(n: int, pending_deletion: int = 0):
    rows = []
    for i in range(1, n + 1):
        stages = ["CURRENT", "LATEST"] if i == n else (["PREVIOUS"] if i == n - 1 else ["DEPRECATED"])
        row = {"version-number": i, "stages": stages, "time-of-deletion": None}
        if i <= pending_deletion:
            row["time-of-deletion"] = "2026-08-30T00:00:00Z"
        rows.append(row)
    return {"data": rows}


def _put(tmp_path, versions, keep=None):
    b = tmp_path / "bin"
    b.mkdir()
    oci = b / "oci"
    oci.write_text(FAKE_OCI)
    oci.chmod(oci.stat().st_mode | stat.S_IEXEC)
    payload = tmp_path / "payload"
    payload.write_text("TOKEN=x\n")
    (tmp_path / "versions.json").write_text(json.dumps(versions))
    import base64
    b64 = base64.b64encode(payload.read_bytes()).decode()
    (tmp_path / "bundle").write_text(b64)
    log = tmp_path / "calls.log"
    env = dict(os.environ, PATH=f"{b}:{os.environ['PATH']}", OCI_CLI_PROFILE="fake",
               OCI_COMPARTMENT_OCID="ocid1.compartment.oc1..fake", FAKE_LOG=str(log),
               FAKE_VERSIONS=str(tmp_path / "versions.json"), FAKE_BUNDLE=str(tmp_path / "bundle"))
    if keep is not None:
        env["IDP_CLOUD_KEEP_VERSIONS"] = str(keep)
    r = subprocess.run([str(ROOT / "bin" / "idp-cloud"), "secret", "put", "hermes-agent-env", "--file", str(payload)],
                       env=env, capture_output=True, text=True, timeout=120)
    lines = log.read_text().splitlines() if log.exists() else []
    return r, lines


def test_at_the_cap_every_deprecated_version_but_the_newest_two_is_scheduled_before_the_update(tmp_path):
    r, lines = _put(tmp_path, _versions(30))
    assert r.returncode == 0, r.stdout + r.stderr
    sched = [ln for ln in lines if "schedule-deletion" in ln]
    nums = sorted(int(ln.split("--secret-version-number ")[1].split()[0]) for ln in sched)
    # 30 versions: CURRENT=30 stays; 29 (PREVIOUS) and 28 are the two kept; 1..27 go
    assert nums == list(range(1, 28)), nums
    assert all("--time-of-deletion 2026-" in ln or "--time-of-deletion 20" in ln for ln in sched)
    assert lines.index(sched[-1]) < lines.index(next(ln for ln in lines if ln.startswith("update "))), \
        "pruning must happen before the update that would hit the cap"
    assert "27 deprecated version(s) scheduled for deletion" in r.stderr


def test_versions_already_pending_deletion_are_not_scheduled_twice(tmp_path):
    r, lines = _put(tmp_path, _versions(30, pending_deletion=20))
    assert r.returncode == 0, r.stdout + r.stderr
    nums = sorted(int(ln.split("--secret-version-number ")[1].split()[0]) for ln in lines if "schedule-deletion" in ln)
    assert nums == list(range(21, 28)), nums


def test_a_young_secret_is_left_alone(tmp_path):
    r, lines = _put(tmp_path, _versions(3))
    assert r.returncode == 0, r.stdout + r.stderr
    assert not [ln for ln in lines if "schedule-deletion" in ln]
    assert "scheduled for deletion" not in r.stderr
