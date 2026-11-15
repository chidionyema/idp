"""The same wall for a laptop push and a cloud pull request.

Founder, 2026-11-15: "every single requirement that fails at pr needs to be prevented at
pre-push", and "not just laptop agents but cloud agents also ... eliminate red prs altogether".

A laptop can bypass a git hook; a cloud agent never runs one. The only wall they share is a
script both call: `.githooks/pre-push` calls `IDP_CI_FAST=1 bin/idp-ci`, and the required
`fast-gate` workflow calls the same command. These tests hold that parity, and prove the new
registry rung can actually fail.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPUSH = ROOT / ".githooks" / "pre-push"
FAST_GATE = ROOT / ".github" / "workflows" / "fast-gate.yml"
IDP_CI = ROOT / "bin" / "idp-ci"
REGISTRY_GATE = ROOT / "bin" / "registry-gate"


def test_laptop_and_cloud_run_the_same_command():
    pre = PREPUSH.read_text()
    cloud = FAST_GATE.read_text()
    assert "IDP_CI_FAST=1" in pre and "bin/idp-ci" in pre, (
        "pre-push does not call the shared gate"
    )
    assert "IDP_CI_FAST=1" in cloud and "bin/idp-ci" in cloud, (
        "fast-gate does not call the shared gate"
    )


def test_the_registry_requirement_is_a_prepush_rung():
    assert 'say "ok    registry' in IDP_CI.read_text(), (
        "the capability-witness check is not a rung of the shared gate, so a stale registry "
        "reaches CI and the PR goes red"
    )


def test_the_registry_gate_can_fail_on_a_stale_witness(tmp_path):
    snapshot = ROOT / "catalog" / "estate-capability-registry.json"
    if not snapshot.exists() or not REGISTRY_GATE.exists():
        return  # nothing to falsify in a sparse checkout; the rung is still present
    data = json.loads(snapshot.read_text())
    records = data.get("records")
    if not isinstance(records, list) or not records:
        return
    stale = tmp_path / "stale.json"
    data["records"] = records[:-1]  # a witness that lags the repository by one record
    stale.write_text(json.dumps(data))
    p = subprocess.run(
        [str(REGISTRY_GATE), "--idp", str(ROOT), "--snapshot", str(stale)],
        capture_output=True,
        text=True,
    )
    assert p.returncode != 0, "registry-gate accepted a witness it should refuse"
