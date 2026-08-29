"""crew#584 CP-C (LAW 45): a lint red never boots k3s or builds four images.

Founder playbook 2026-08-29, Phase 2: "Configure ci-k8s-deploy to needs: [ci-fast-gate]. The
13-minute cluster boot will only trigger if the 60-second fast gate passes completely."
Incident: idp#659 ran 11 min of drills and four image builds for a commit with a shellcheck
warning that the offline gate reported after 5 min.
"""
from __future__ import annotations

import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")

HEAVY = {
    "ci.yml": ["offline-gate", "bdd-suites", "security-scan", "spec-gate", "no-toil-gate", "operating-model-gate"],
    "build-multiarch.yml": ["discover"],
    "portability-drill.yml": ["hydrate", "k3s"],
}


def _jobs(name):
    with open(os.path.join(WF, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["jobs"]


def test_fast_gate_is_a_reusable_workflow_that_runs_the_fast_rungs():
    with open(os.path.join(WF, "fast-gate.yml"), encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    assert "workflow_call" in d[True] if True in d else d["on"], "fast-gate must be callable"
    steps = d["jobs"]["fast-gate"]["steps"]
    assert any("IDP_CI_FAST=1 bin/idp-ci" in (st.get("run") or "") for st in steps)


def test_every_heavy_job_needs_the_fast_gate():
    for wf, heavy in HEAVY.items():
        jobs = _jobs(wf)
        assert jobs.get("fast-gate", {}).get("uses") == "./.github/workflows/fast-gate.yml", wf
        for job in heavy:
            needs = jobs[job].get("needs")
            needs = [needs] if isinstance(needs, str) else (needs or [])
            assert "fast-gate" in needs, f"{wf}: {job} does not need fast-gate"


def test_fast_mode_exits_before_the_docker_rungs():
    text = open(os.path.join(ROOT, "bin", "idp-ci"), encoding="utf-8").read()
    assert 'FAST="${IDP_CI_FAST:-0}"' in text
    # tab-indented (shfmt, crew#620): `exit "$fail"` sits inside the `if [ "$FAST" = 1 ]` block.
    assert text.index('\texit "$fail"\nfi\n\n# 2. Compose files') > text.index("# 1d. ruff")
    # fast mode must not demand docker/conftest: those needs are behind the FAST guard.
    # shfmt (crew#620) breaks a `[ cond ] || { a; b; }` one-liner onto separate lines, so the
    # guard is graded as a block (starts the FAST test, contains need docker, closes) rather
    # than one exact string.
    guard_start = text.index('[ "$FAST" = 1 ] || {')
    guard_end = text.index("\n}", guard_start)
    guard_block = text[guard_start:guard_end]
    assert "need docker" in guard_block


def test_fast_gate_is_green_on_this_tree_in_under_60s():
    """The gate proves itself on the repo it guards: green, and inside the founder's 60 s."""
    import time
    t0 = time.monotonic()
    out = subprocess.run(["bin/idp-ci"], cwd=ROOT, env=dict(os.environ, IDP_CI_FAST="1"),
                         capture_output=True, text=True, timeout=180)
    secs = time.monotonic() - t0
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-500:]
    assert "ok    fast-gate" in out.stdout
    assert secs < 60, f"fast gate took {secs:.0f}s"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
