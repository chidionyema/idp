"""crew#292 CP2: the drills row (are the scheduled drills firing?) is printed by something
scheduled. It lived only as a heredoc inside bin/idp-verify, which no workflow runs and which exits
before the row whenever Backstage is not on 7107 - the last 30 verify-drill runs never printed the
word `drills`. Now bin/idp-drills-row is its own script, bin/idp-verify calls it unchanged, and
bin/idp-verify-drill grades it as a fifth row every hour on the machine identity."""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-verify-drill"


def _fake(b: Path, name: str, body: str) -> None:
    (b / name).write_text("#!/bin/sh\n" + body + "\n")
    (b / name).chmod((b / name).stat().st_mode | stat.S_IEXEC)


def _bin(tmp: Path, drills_body: str) -> Path:
    b = tmp / "bin"
    b.mkdir()
    _fake(b, "oci", "echo '{\"data\": []}'")
    _fake(b, "idp-cloud", "case \"$1 $2\" in 'cluster list') echo 'oke ocid1.cluster.fake.abc';; 'cluster nodepools') echo 'pool ACTIVE';; esac")
    _fake(b, "kubectl", "echo '{\"items\": [{\"metadata\": {\"name\": \"n\"}, \"status\": {\"conditions\": [{\"type\": \"Ready\", \"status\": \"True\"}]}}]}'")
    _fake(b, "idp-cluster-state", "echo 'ok      cluster-state nodes=1 ready=1 (3 min ago)'")
    _fake(b, "idp-drills-row", drills_body)
    (b / "idp-verify-drill").write_text(SCRIPT.read_text())
    (b / "idp-verify-drill").chmod(0o755)
    return b


def _run(tmp: Path, b: Path) -> subprocess.CompletedProcess:
    env = {"PATH": f"{b}:/usr/bin:/bin", "TMPDIR": str(tmp), "HOME": str(tmp), "OCI_CLI_AUTH": "security_token"}
    return subprocess.run([str(b / "idp-verify-drill")], env=env, capture_output=True, text=True, timeout=60)


def test_a_stale_drill_is_a_red_row_and_a_failed_verify_drill(tmp_path: Path) -> None:
    b = _bin(tmp_path, "echo 'FAIL      drills    trace-drill  trace-drill.yml last green 9.0h ago, older than 3h'; exit 1")
    r = _run(tmp_path, b)
    assert "FAIL      drills    trace-drill" in r.stdout, r.stdout + r.stderr
    assert re.search(r"^FAIL +drills +a catalogued drill is stale", r.stdout, re.M), r.stdout
    assert r.returncode == 1 and "verify-drill" in r.stdout


def test_no_github_is_a_blind_row_never_a_green_one(tmp_path: Path) -> None:
    b = _bin(tmp_path, "echo 'BLIND     drills    gh is not on the PATH'; exit 2")
    r = _run(tmp_path, b)
    assert re.search(r"^BLIND +drills +cannot ask GitHub", r.stdout, re.M), r.stdout + r.stderr
    assert r.returncode == 2


def test_the_row_is_a_script_of_its_own_that_both_verifiers_call() -> None:
    row = ROOT / "bin" / "idp-drills-row"
    assert row.exists() and os.access(row, os.X_OK)
    assert "<<'DRILLPY'" not in (ROOT / "bin" / "idp-verify").read_text()
    assert 'idp-drills-row" "$IDP/drills/catalogue.yaml" "$IDP"' in (ROOT / "bin" / "idp-verify").read_text()
    assert 'idp-drills-row" "$IDP/drills/catalogue.yaml" "$IDP"' in SCRIPT.read_text()


def test_the_hourly_workflow_can_ask_github_for_drill_runs() -> None:
    """The row lists workflow runs, which needs actions: read and a token on the drill step."""
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "verify-drill.yml").read_text())
    assert wf["permissions"]["actions"] == "read"
    steps = wf["jobs"]["verify-drill"]["steps"]
    drill = next(s for s in steps if "bin/idp-verify-drill" in s.get("run", ""))
    assert drill["env"]["GH_TOKEN"] == "${{ github.token }}"
