"""spire-proof-run passes only on an SVID the pod actually logged, and always deletes its pod.

Runs the repo's platform/estate/libexec/spire-proof-run.sh with a stub kubectl on PATH that
records every call and answers the pod phase / logs / create result the test sets.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/spire-proof-run.sh"
)

STUB = """#!/usr/bin/env bash
printf '%s\\0' "$@" >> "$STUB_DIR/calls"; printf '\\036' >> "$STUB_DIR/calls"
case " $* " in
  *" run "*) [ "${STUB_RUN_RC:-0}" = 0 ] || { echo 'forbidden: violates PodSecurity' >&2; exit 1; } ;;
  *" get pod "*) printf '%s' "$STUB_PHASE" ;;
  *" logs "*) printf '%s\\n' "$STUB_LOGS" ;;
esac
exit 0
"""


def _run(tmp_path: Path, phase: str, logs: str, run_rc: int = 0):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "kubectl").write_text(STUB)
    (bindir / "kubectl").chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "STUB_DIR": str(tmp_path),
        "STUB_PHASE": phase,
        "STUB_LOGS": logs,
        "STUB_RUN_RC": str(run_rc),
        "SPIRE_PROOF_POLL_S": "0",
    }
    r = subprocess.run(
        ["bash", str(SCRIPT), "backstage", "1s"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    calls = [
        c.split("\0")[:-1] for c in (tmp_path / "calls").read_text().split("\x1e") if c
    ]
    return r, calls


def test_an_issued_svid_is_proven_and_the_pod_is_deleted(tmp_path):
    r, calls = _run(
        tmp_path, "Succeeded", "SPIFFE ID:\t\tspiffe://idp/ns/backstage/sa/default"
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (
        "ok SVID issued to backstage/spire-proof-manual: spiffe://idp/ns/backstage/sa/default"
        in r.stdout
    )
    (run,) = [c for c in calls if "run" in c]
    spec = json.loads(
        next(a.split("=", 1)[1] for a in run if a.startswith("--overrides="))
    )["spec"]
    assert {
        "csi": {"driver": "csi.spiffe.io", "readOnly": True},
        "name": "spiffe-workload-api",
    } in spec["volumes"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["restartPolicy"] == "OnFailure"
    assert "delete" in calls[-1], calls[-1]


def test_a_pod_that_logged_no_svid_is_not_proven(tmp_path):
    r, calls = _run(
        tmp_path,
        "Failed",
        "rpc error: code = PermissionDenied desc = no identity issued",
    )
    assert r.returncode == 1, r.stdout
    assert "NOT PROVEN no SVID: phase=Failed" in r.stdout
    assert "delete" in calls[-1]


def test_succeeded_without_a_spiffe_id_is_not_proven(tmp_path):
    r, _ = _run(tmp_path, "Succeeded", "")
    assert r.returncode == 1 and "NOT PROVEN" in r.stdout, r.stdout


def test_a_refused_create_is_not_proven(tmp_path):
    r, calls = _run(tmp_path, "", "", run_rc=1)
    assert r.returncode == 1, r.stdout
    assert "NOT PROVEN could not create" in r.stdout and "PodSecurity" in r.stdout
    assert not [c for c in calls if "logs" in c]
