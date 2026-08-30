"""Incident test (rung 4), crew#301 / crew#311, 2026-08-26: idp#196 added `manage buckets` to the
bootstrap list, the live tenancy-root policy never got it, and three applies failed 409 with no
row naming the missing statement. bin/idp-iam-policy-drift grades live statements against the file.
Both ways in one run: a matching policy is ok; a missing statement is FAIL and names it; an
unreadable policy is BLIND, never a verdict.

Second incident, run 32988930880 (first apply after idp#227): the compartment policy carried
`manage buckets`, the tenancy policy carried a stale `read buckets`, and the grader read only the
tenancy policy, so it failed a grant that was live. The union test below is that run's exact shape."""

import json, os, stat, subprocess
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "bin" / "idp-iam-policy-drift"
FILE = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "oci"
    / "policy"
    / "estate-operators.statements.json"
)
COMP = "ocid1.compartment.oc1..test"


def _run(tmp: Path, live, rc_list: int = 0, comp=None) -> subprocess.CompletedProcess:
    b = tmp / "bin"
    b.mkdir(exist_ok=True)
    fake = b / "oci"
    (b / "comp.json").write_text(json.dumps(comp))
    (b / "live.json").write_text(json.dumps(live))
    fake.write_text(
        '#!/usr/bin/env bash\ncase "$*" in '
        f"*\"--name estate-operators-compartment\"*) cat '{b / 'comp.json'}'; exit 0;; "
        f"*\"iam policy list\"*) cat '{b / 'live.json'}'; exit {rc_list};; "
        "*) echo unexpected >&2; exit 9;; esac\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "OCI_TENANCY_OCID": "ocid1.tenancy.oc1..test",
        "OCI_COMPARTMENT_OCID": COMP if comp is not None else "",
    }
    return subprocess.run(["bash", str(GUARD)], env=env, capture_output=True, text=True)


def test_incident_missing_statement_is_named(tmp_path: Path) -> None:
    want = json.loads(FILE.read_text())
    ok = _run(tmp_path, want)
    assert ok.returncode == 0 and ok.stdout.startswith("ok      iam-policy"), (
        ok.stdout + ok.stderr
    )
    short = [s for s in want if "manage buckets" not in s]
    assert len(short) == len(want) - 1
    r = _run(tmp_path, short)
    assert (
        r.returncode == 1
        and "FAIL    iam-policy  1 missing" in r.stdout
        and "manage buckets" in r.stdout
    ), r.stdout
    assert "bin/idp-oci-bootstrap" in r.stdout


def test_incident_run_32988930880_compartment_policy_counts_as_live(
    tmp_path: Path,
) -> None:
    want = json.loads(FILE.read_text())
    tenancy = [
        s.replace("manage buckets", "read buckets") for s in want
    ]  # stale bootstrap line
    comp = [
        s.replace(" in compartment estate", f" in compartment id {COMP}")
        for s in want
        if s.endswith(" in compartment estate")
    ]  # what iam.tf applies
    r = _run(tmp_path, tenancy, comp=comp)
    assert r.returncode == 0 and r.stdout.startswith("ok      iam-policy"), (
        r.stdout + r.stderr
    )
    assert "1 stale tenancy line(s)" in r.stdout and "read buckets" in r.stdout, (
        r.stdout
    )
    # the other way: a live line with no stronger wanted twin is still drift
    r2 = _run(
        tmp_path,
        tenancy + ["Allow group estate-operators to manage users in tenancy"],
        comp=comp,
    )
    assert r2.returncode == 1 and "manage users in tenancy" in r2.stdout, r2.stdout
    # and a compartment policy not applied yet does not hide a missing grant
    r3 = _run(tmp_path, tenancy, comp=[])
    assert (
        r3.returncode == 1
        and "manage buckets" in r3.stdout
        and "oke-check apply" in r3.stdout
    ), r3.stdout


def test_unreadable_policy_is_blind_not_a_verdict(tmp_path: Path) -> None:
    r = _run(tmp_path, {"code": "NotAuthorizedOrNotFound"}, rc_list=1)
    assert r.returncode == 2 and r.stdout.startswith("BLIND   iam-policy"), r.stdout
