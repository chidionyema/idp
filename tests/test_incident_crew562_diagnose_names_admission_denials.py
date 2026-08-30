"""crew#562 / crew#516, 2026-08-28: two things hid the Tailscale operator break.

Run 33210647434's warnings table printed `admission webhook "validate.kyverno.svc-fail" denied
the request: ...` for replicaset tailscale/operator with the policy name cut off by the events
column, while bin/idp-kyverno-render passed the same manifest locally -- nobody could name the
drift. Meanwhile Flux's notification-controller re-sent the same broken-workload event to the
founder's Telegram every ~10 min (founder: "ur drowning my telegram channel with repeated").
The fixes: a diagnose row that reads FailedCreate events in full, and a 1h rate limit on the
controller the estate already runs. These tests hold both.
"""
import os
import stat
import subprocess
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
FLUX_SYSTEM = IDP / "clusters" / "oke" / "flux-system" / "kustomization.yaml"


def _run_diagnose(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux", "helm"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    return log.read_text().splitlines() if log.exists() else []


def test_diagnose_reads_admission_denials_in_full(tmp_path):
    calls = _run_diagnose(tmp_path)
    denials = [c for c in calls if "reason=FailedCreate" in c]
    assert denials, "diagnose never read the FailedCreate events that carry admission denials"
    assert any("{.message}" in c for c in denials), "the row must print the full message, not the events column"


def test_notification_controller_is_rate_limited_to_one_hour():
    doc = yaml.safe_load(FLUX_SYSTEM.read_text())
    hits = [
        op
        for p in doc.get("patches", [])
        if p.get("target", {}).get("kind") == "Deployment"
        and p["target"].get("name") == "notification-controller"
        for op in yaml.safe_load(p["patch"])
    ]
    assert any(op.get("op") == "add" and op.get("value") == "--rate-limit-interval=1h" for op in hits), hits
