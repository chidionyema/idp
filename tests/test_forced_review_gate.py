"""The forced-review gate must fail closed, and must be able to fail.

Every test here is a falsifier: each one proves the gate refuses a thing it must refuse, or
accepts exactly one thing it must accept. A gate that cannot fail is not a gate, so the
negative cases are the point of this file.

The fixture is a real git repository, because the gate's facts come from git: the base ref, the
merge base, the changed-file set and the inventory read from the base ref.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "platform" / "estate" / "governance" / "review_gate.py"

INVENTORY = """
version: 1
surfaces:
  - id: fleet-surface
    kind: founder_surface
    reason: the founder reads /fleet
    paths:
      - backstage/packages/app/src/modules/room/**
  - id: executor-door
    kind: critical_service
    reason: every agent's work passes through here
    paths:
      - platform/executor/**
"""


def _load():
    spec = importlib.util.spec_from_file_location("review_gate_under_test", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def gate():
    return _load()


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()


def _make_repo(tmp_path: pathlib.Path, inventory: str = INVENTORY) -> pathlib.Path:
    repo = tmp_path / "repo"
    (repo / "platform" / "estate" / "governance").mkdir(parents=True)
    (repo / "backstage" / "packages" / "app" / "src" / "modules" / "room").mkdir(
        parents=True
    )
    (repo / "platform" / "executor").mkdir(parents=True)
    (repo / "platform" / "estate" / "governance" / "founder-surfaces.yaml").write_text(
        inventory, encoding="utf-8"
    )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "gate@example.invalid")
    _git(repo, "config", "user.name", "gate")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _commit(
    repo: pathlib.Path, path: str, content: str, message: str = "change"
) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _receipt(gate, sha: str, base: str, **overrides) -> str:
    payload = {
        "schema": gate.RECEIPT_SCHEMA,
        "sha": sha,
        "base": base,
        "verdict": "pass",
        "tiers": ["t0", "t1", "t2", "t3"],
        "findings": {"critical": 0, "high": 0, "medium": 2, "low": 5},
        "verified": 0,
        "generated_at": "2026-10-30T00:00:00Z",
    }
    payload.update(overrides)
    payload["digest"] = gate.receipt_digest(payload)
    return json.dumps(payload)


# ----------------------------------------------------------------------------------
# The known-good case: exactly one thing passes.
# ----------------------------------------------------------------------------------


def test_a_guarded_change_with_a_matching_passing_receipt_is_allowed(gate, tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(
        repo, "backstage/packages/app/src/modules/room/ui.tsx", "export const x = 1\n"
    )

    receipt = _receipt(gate, head, base)
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "pass", decision.reason
    assert [m["surface"] for m in decision.matched] == ["fleet-surface"]
    assert decision.matched[0]["kind"] == "founder_surface"


def test_a_change_that_touches_nothing_guarded_needs_no_receipt(gate, tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "docs/notes.md", "a note\n")

    decision = gate.decide(repo, base_ref=base, head_ref=head)

    assert decision.verdict == "pass", decision.reason
    assert decision.matched == []


# ----------------------------------------------------------------------------------
# The known-bad cases: the gate must refuse.
# ----------------------------------------------------------------------------------


def test_a_guarded_change_without_a_receipt_is_refused(gate, tmp_path):
    """THE KNOWN-BAD FIXTURE. Without this, the gate is decorative."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    decision = gate.decide(repo, base_ref=base, head_ref=head)

    assert decision.verdict == "refuse"
    assert "no review receipt" in decision.reason
    assert [m["surface"] for m in decision.matched] == ["executor-door"]


def test_a_receipt_for_another_commit_is_refused(gate, tmp_path):
    """A review of one commit is not a review of another."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    receipt = _receipt(gate, "0" * 40, base)
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "refuse"
    assert "not the commit under judgement" in decision.reason


def test_a_receipt_for_another_base_is_refused(gate, tmp_path):
    """The receipt covered different changes."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    receipt = _receipt(gate, head, "1" * 40)
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "refuse"
    assert "covered different changes" in decision.reason


def test_a_receipt_edited_after_the_fact_is_refused(gate, tmp_path):
    """The digest covers every field, so editing the verdict breaks it."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    payload = json.loads(_receipt(gate, head, base))
    payload["verdict"] = "pass"
    payload["findings"] = {"critical": 0, "high": 0}
    # the digest is deliberately left as it was
    decision = gate.decide(
        repo, base_ref=base, head_ref=head, receipt_text=json.dumps(payload)
    )

    assert decision.verdict == "refuse"
    assert "digest does not match" in decision.reason


def test_a_receipt_that_claims_pass_with_a_high_finding_is_refused(gate, tmp_path):
    """The anti-lie check: a receipt cannot pass while carrying a blocking finding."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    receipt = _receipt(gate, head, base, findings={"critical": 0, "high": 1})
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "refuse"
    assert "blocking findings" in decision.reason


def test_a_receipt_that_claims_pass_with_a_verified_finding_is_refused(gate, tmp_path):
    """Tier 3 verified it, so it is a real finding, whatever the receipt says."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    receipt = _receipt(gate, head, base, verified=1)
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "refuse"
    assert "verified 1 finding" in decision.reason


def test_a_failing_receipt_is_refused(gate, tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    receipt = _receipt(gate, head, base, verdict="fail")
    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text=receipt)

    assert decision.verdict == "refuse"
    assert "failing review" in decision.reason


def test_a_malformed_receipt_is_refused(gate, tmp_path):
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    decision = gate.decide(repo, base_ref=base, head_ref=head, receipt_text="{not json")

    assert decision.verdict == "refuse"
    assert "unusable" in decision.reason


def test_a_missing_inventory_is_refused_not_passed(gate, tmp_path):
    """The difference between 'no guarded path was touched' and 'I could not tell'."""
    repo = _make_repo(tmp_path, inventory="version: 1\nsurfaces: []\n")
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    decision = gate.decide(repo, base_ref=base, head_ref=head)

    assert decision.verdict == "refuse"
    assert "declares no surfaces" in decision.reason


def test_an_unresolvable_base_is_refused_not_passed(gate, tmp_path):
    repo = _make_repo(tmp_path)
    head = _commit(repo, "platform/executor/run.py", "print('x')\n")

    decision = gate.decide(repo, base_ref="origin/does-not-exist", head_ref=head)

    assert decision.verdict == "refuse"
    assert "origin/does-not-exist" in decision.reason


# ----------------------------------------------------------------------------------
# The inventory is read from the BASE ref, so the change cannot weaken it.
# ----------------------------------------------------------------------------------


def test_the_change_cannot_weaken_the_inventory_it_touches(gate, tmp_path):
    """An agent that edits the inventory and the guarded file in one change still gets refused."""
    repo = _make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _commit(
        repo,
        "platform/estate/governance/founder-surfaces.yaml",
        "version: 1\nsurfaces: []\n",
        "weaken the inventory",
    )
    head = _commit(
        repo, "platform/executor/run.py", "print('x')\n", "touch the executor"
    )

    decision = gate.decide(repo, base_ref=base, head_ref=head)

    assert decision.verdict == "refuse"
    assert [m["surface"] for m in decision.matched] == ["executor-door"]


# ----------------------------------------------------------------------------------
# The matcher itself.
# ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        ("platform/executor/**", "platform/executor/run.py", True),
        ("platform/executor/**", "platform/executor/deep/thing.py", True),
        ("platform/executor/**", "platform/executors/run.py", False),
        ("platform/executor", "platform/executor/run.py", True),
        ("factory/surfaces/voice.py", "factory/surfaces/voice.py", True),
        ("factory/surfaces/voice.py", "factory/surfaces/voice.ts", False),
        ("docs/keys/**", "docs/keys/founder.pub", True),
        ("docs/keys/**", "docs/keynote.md", False),
    ],
)
def test_pattern_matching(gate, pattern, path, expected):
    inventory = gate.parse_inventory(
        "version: 1\nsurfaces:\n  - id: s\n    kind: critical_service\n    paths:\n"
        f"      - {pattern}\n"
    )
    matched = inventory.match(path)
    assert (matched is not None) is expected
