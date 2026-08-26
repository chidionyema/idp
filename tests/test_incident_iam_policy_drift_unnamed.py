"""Incident test (rung 4), crew#301 / crew#311, 2026-08-26: idp#196 added `manage buckets` to the
bootstrap list, the live tenancy-root policy never got it, and three applies failed 409 with no
row naming the missing statement. bin/idp-iam-policy-drift grades live statements against the file.
Both ways in one run: a matching policy is ok; a missing statement is FAIL and names it; an
unreadable policy is BLIND, never a verdict."""
import json, os, stat, subprocess
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "bin" / "idp-iam-policy-drift"
FILE = Path(__file__).resolve().parents[1] / "platform" / "oci" / "policy" / "estate-operators.statements.json"


def _run(tmp: Path, live, rc_list: int = 0) -> subprocess.CompletedProcess:
    b = tmp / "bin"; b.mkdir(exist_ok=True)
    fake = b / "oci"
    fake.write_text(f"#!/usr/bin/env bash\ncase \"$*\" in *\"iam policy list\"*) printf '%s' '{json.dumps(live)}'; exit {rc_list};; *) echo unexpected >&2; exit 9;; esac\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "OCI_TENANCY_OCID": "ocid1.tenancy.oc1..test"}
    return subprocess.run(["bash", str(GUARD)], env=env, capture_output=True, text=True)


def test_incident_missing_statement_is_named(tmp_path: Path) -> None:
    want = json.loads(FILE.read_text())
    ok = _run(tmp_path, want)
    assert ok.returncode == 0 and ok.stdout.startswith("ok      iam-policy"), ok.stdout + ok.stderr
    short = [s for s in want if "manage buckets" not in s]
    assert len(short) == len(want) - 1
    r = _run(tmp_path, short)
    assert r.returncode == 1 and "FAIL    iam-policy  1 missing" in r.stdout and "manage buckets" in r.stdout, r.stdout
    assert "bin/idp-oci-bootstrap" in r.stdout


def test_unreadable_policy_is_blind_not_a_verdict(tmp_path: Path) -> None:
    r = _run(tmp_path, {"code": "NotAuthorizedOrNotFound"}, rc_list=1)
    assert r.returncode == 2 and r.stdout.startswith("BLIND   iam-policy"), r.stdout
