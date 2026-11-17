"""The pre-push wall has to be able to fail, and it has to cover every required check.

Founder, 2026-11-15: "all this failing checks needs to happen pre-push" and "I don't ever
want to see a red PR ever again". A wall that cannot fail is not a wall (AGENTS.md 9.1), and
a wall that covers 7 of 9 required contexts lets the other 2 go red after the push.

Two invariants, each with a falsifier:
  1. COVERAGE  every required context on main is in lib/pr-checks.json, as a check or a
     derived aggregator with a stated reason. A context added to the ruleset and not to the
     manifest fails this test.
  2. VERDICT   bin/pr-parity passes a good check, and refuses a bad one, a missing one and a
     timeout -- BLIND is never a pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "bin" / "pr-parity"
MANIFEST = ROOT / "lib" / "pr-checks.json"

REQUIRED = [
    "fast-gate / fast-gate",
    "bdd",
    "guarded-paths",
    "test",
    "executes-gate",
    "feature-request-plan",
    "ci-success",
    "portal-app",
    "greenlane",
]
# Contexts GitHub reports on a PR that the estate has refused before; the wall grades them too.
OBSERVED = [
    "gate / fast-gate",
    "claim-gate",
    "deterministic-gate / control-primitive-freeze",
    "deterministic-gate / rust-and-bdd-verify",
    "no-harness-folders",
    "ruff-required",
    "verifier / verifier",
    "verify / verifier",
    "ui-kit",
    "law-gate",
    "dof-gate",
    "scope",
]


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_contexts_are_unique_and_kind_is_declared():
    checks = _manifest()["checks"]
    contexts = [c["context"] for c in checks]
    assert len(contexts) == len(set(contexts)), (
        "a context appears twice in the manifest"
    )
    for c in checks:
        assert c["kind"] in {"check", "derived"}, c
        if c["kind"] == "derived":
            assert c.get("reason"), f"derived context {c['context']} carries no reason"
        else:
            assert c.get("cmd"), f"check {c['context']} carries no command"


def test_every_required_and_observed_context_is_on_the_wall():
    present = {c["context"] for c in _manifest()["checks"]}
    missing = [c for c in REQUIRED + OBSERVED if c not in present]
    assert not missing, f"contexts Graded on PRs but absent from the wall: {missing}"


def test_coverage_detects_an_unmapped_required_context():
    """Falsifier for invariant 1: drop one context and the coverage list must notice."""
    present = {c["context"] for c in _manifest()["checks"]} - {"guardrails-unmapped"}
    missing = [c for c in REQUIRED + ["guardrails-unmapped"] if c not in present]
    assert missing == ["guardrails-unmapped"]


def _run(manifest: dict, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    env = dict(os.environ, PR_PARITY_MANIFEST=str(path))
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "pr",
            "--base",
            "HEAD",
            "--head",
            "HEAD",
            *args,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _manifest_with(cmd: list[str]) -> dict:
    return {
        "version": 1,
        "checks": [
            {
                "context": "synthetic",
                "kind": "check",
                "cmd": cmd,
                "args": [],
                "paths": None,
            }
        ],
    }


def test_good_check_passes(tmp_path):
    proc = _run(_manifest_with(["true"]), tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VERDICT PASS" in proc.stdout


def test_bad_check_refuses(tmp_path):
    proc = _run(_manifest_with(["false"]), tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "VERDICT FAIL" in proc.stdout


def test_missing_command_is_blind_not_pass(tmp_path):
    proc = _run(_manifest_with(["definitely-not-a-command-xyz"]), tmp_path)
    assert proc.returncode == 1, "a missing command must fail closed"
    assert "BLIND synthetic" in proc.stdout


def test_timeout_is_blind_not_pass(tmp_path):
    manifest = _manifest_with(["sleep", "5"])
    path = tmp_path / "slow.json"
    path.write_text(json.dumps(manifest))
    env = dict(os.environ, PR_PARITY_MANIFEST=str(path))
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "pr",
            "--base",
            "HEAD",
            "--head",
            "HEAD",
            "--timeout",
            "1",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "BLIND synthetic" in proc.stdout


def test_derived_aggregators_alone_never_go_red(tmp_path):
    manifest = {
        "version": 1,
        "checks": [
            {
                "context": "ci-success",
                "kind": "derived",
                "reason": "aggregator of the wall",
            },
            {"context": "greenlane", "kind": "derived", "reason": "engine status"},
        ],
    }
    proc = _run(manifest, tmp_path)
    assert proc.returncode == 0
    assert "DERIVED ci-success" in proc.stdout


def test_proof_is_written_and_hashed(tmp_path):
    proof = tmp_path / "proof.json"
    proc = _run(_manifest_with(["true"]), tmp_path, "--proof", str(proof))
    assert proc.returncode == 0
    data = json.loads(proof.read_text())
    assert data["verdict"] == "PASS"
    assert len(data["sha256"]) == 64
    assert data["checks"][0]["sha256"]


def test_ci_success_judges_the_parity_job():
    """The wall is worthless if the aggregator does not read it."""
    import yaml

    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    assert "parity" in workflow["jobs"], "ci.yml has no parity job"
    needs = workflow["jobs"]["ci-success"]["needs"]
    assert "parity" in needs, f"ci-success does not judge parity: {needs}"


def test_pre_push_calls_the_wall():
    hook = (ROOT / ".githooks" / "pre-push").read_text()
    assert "bin/pr-parity" in hook
    assert "--mode prepush" in hook
