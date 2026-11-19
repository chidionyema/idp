#!/usr/bin/env python3
"""I-8107 certification: the wall, the differential falsifier and the epistemic gate.

Every test builds a throwaway git repo, copies the real executables into it, and runs them as
subprocesses -- the same invocation pre-push and CI use. Nothing is mocked.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "platform" / "llm" / "callbacks"))
import aei_observer  # noqa: E402


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def fixture(tmp):
    repo = tmp / "fixture"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "certifier@meridianlabs.cloud")
    git(repo, "config", "user.name", "Genesis Certifier")
    (repo / "bin").mkdir()
    for name in ("pre-push-wall.py", "idp-differential-falsifier"):
        shutil.copy2(REPO_ROOT / "bin" / name, repo / "bin" / name)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "name: ci\njobs:\n  t:\n    runs-on: ubuntu-latest\n"
    )
    (repo / ".github" / "workflows" / "shadow-verify.yml").write_text(
        "name: shadow\n# git merge-base fallback\n"
    )
    (repo / "platform" / "brain-hub").mkdir(parents=True)
    (repo / "platform" / "brain-hub" / "worker.ts").write_text("export const v = 1;\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "base")
    git(repo, "branch", "origin-main-ref")
    return repo


def artefacts(repo, subsystems):
    ci = repo / ".ci"
    ci.mkdir(exist_ok=True)
    (ci / "intent-manifest.json").write_text(
        json.dumps(
            {
                "instruction_id": "I-8107",
                "owner": "genesis-certifier",
                "target_subsystems": subsystems,
                "failure_modes_mapped": [
                    "FC_ZONE_A_DARWIN_REGRESSION",
                    "FC_PROOF_FORMAT_WITHOUT_FALSIFICATION",
                ],
                "existing_assets_checked": True,
                "schema_strict": True,
            }
        )
    )
    (ci / "proof-receipt.json").write_text(
        json.dumps(
            {
                "tested_subsystems": subsystems,
                "falsifiers": [
                    {"test_name": "t", "base_exit_code": 1, "head_exit_code": 0}
                ],
                "mutations_killed": [{"guard": "darwin_thin_client", "killed": True}],
            }
        )
    )


def wall(repo, env_extra=None):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"GENESIS_SURFACE_INGEST_URL", "GENESIS_SURFACE_TOKEN"}
    }
    env.update(env_extra or {})
    return subprocess.run(
        [
            sys.executable,
            str(repo / "bin" / "pre-push-wall.py"),
            "ci",
            "origin-main-ref",
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def commit(repo, path, text, msg):
    t = repo / path
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(text)
    git(repo, "add", path)
    git(repo, "commit", "-m", msg)


def test_clean_change_passes_six_gates_and_emits_microscope(tmp_path):
    repo = fixture(tmp_path)
    commit(repo, "platform/brain-hub/worker.ts", "export const v = 2;\n", "feat: clean")
    artefacts(repo, ["platform/brain-hub"])
    p = wall(repo)
    assert p.returncode == 0, p.stderr
    lines = (repo / ".ci" / "ci-microscope.jsonl").read_text().splitlines()
    assert len(lines) == 6
    assert all(json.loads(x)["advisory"] is False for x in lines)


def test_advisory_continue_on_error_is_refused(tmp_path):
    repo = fixture(tmp_path)
    commit(
        repo,
        ".github/workflows/ci.yml",
        "name: ci\njobs:\n  t:\n    continue-on-error: true\n",
        "bad",
    )
    artefacts(repo, [".github/workflows"])
    p = wall(repo)
    assert p.returncode != 0 and "ADVISORY_GATE_FORBIDDEN" in p.stderr


def test_darwin_launchctl_regression_is_refused(tmp_path):
    repo = fixture(tmp_path)
    commit(
        repo,
        "platform/brain-hub/worker.ts",
        "// launchctl list Library/LaunchAgents\n",
        "bad",
    )
    artefacts(repo, ["platform/brain-hub"])
    p = wall(repo)
    assert p.returncode != 0 and "DARWIN_THIN_CLIENT_VIOLATION" in p.stderr


def test_non_falsifying_proof_is_refused(tmp_path):
    repo = fixture(tmp_path)
    commit(repo, "platform/brain-hub/worker.ts", "export const v = 3;\n", "weak")
    artefacts(repo, ["platform/brain-hub"])
    (repo / ".ci" / "proof-receipt.json").write_text(
        json.dumps(
            {
                "tested_subsystems": ["platform/brain-hub"],
                "falsifiers": [
                    {"test_name": "fake", "base_exit_code": 0, "head_exit_code": 0}
                ],
                "mutations_killed": [{"guard": "darwin", "killed": True}],
            }
        )
    )
    p = wall(repo)
    assert p.returncode != 0 and "NON_FALSIFYING_TEST" in p.stderr


def test_moratorium_blocks_governance_only_change(tmp_path):
    repo = fixture(tmp_path)
    commit(repo, "cage/rule.rs", "// meta\n", "meta")
    artefacts(repo, ["cage"])
    p = wall(repo, {"ESTATE_DEPLOY_PIPELINE_RED": "true"})
    assert p.returncode != 0 and "FC_GOVERNANCE_WITHOUT_EXECUTION_YIELD" in p.stderr


def test_epistemic_gate_requires_three_independent_proofs():
    p1 = aei_observer.EpistemicProof(
        "github_actions", "2026-11-19T05:24:33Z", "44447062648"
    )
    p2 = aei_observer.EpistemicProof(
        "git_commit", "2026-11-19T05:24:33Z", "4c4cb22ba67538f8"
    )
    p3 = aei_observer.EpistemicProof(
        "cloudflare_edge", "2026-11-19T05:48:18Z", "a" * 64
    )
    ok, why = aei_observer.verify_operational_claim(
        aei_observer.OperationalClaim("dup", ("x",), True, (p1, p1, p2))
    )
    assert not ok and "NON_INDEPENDENT_PROOFS" in why
    ok, why = aei_observer.verify_operational_claim(
        aei_observer.OperationalClaim("good", ("x",), True, (p1, p2, p3))
    )
    assert ok, why


def test_removing_the_darwin_guard_makes_the_refusal_disappear(tmp_path):
    repo = fixture(tmp_path)
    w = repo / "bin" / "pre-push-wall.py"
    w.write_text(w.read_text().replace('r"\\blaunchctl\\b",', ""))
    commit(repo, "platform/brain-hub/worker.ts", "// launchctl list\n", "probe")
    artefacts(repo, ["platform/brain-hub"])
    p = wall(repo)
    assert p.returncode == 0, p.stderr
