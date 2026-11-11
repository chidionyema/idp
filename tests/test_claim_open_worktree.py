"""bin/claim-open must claim the tree you are standing in, not the tree it lives in.

2026-10-22. Every git call in `bin/claim-open` ran with `cwd=` the checkout the script lives in.
From a worktree that is a different tree, so the command reported and claimed the DEV checkout:

    $ cd ~/.estate/worktrees/epic-090 && bin/claim-open --issue 6859 --paths …
    claim-open  change touches 13 file(s): web/app/case-studies/page.tsx, web/app/consulting/page.tsx, …
    FAIL    claim-open  this commit already claims #6698 as estate-agent, not #6859 as pi-epic-090.

None of those files were in the branch, and #6698 was another agent's claim, read off the dev
tree's HEAD. No worktree lane could declare itself, so the workaround was to hand-post the CLAIM
comment and run bin/claim-gate with GITHUB_REPOSITORY exported — the escape hatch this file
outlaws by existing.

These tests execute the resolution rather than reading the source for `cwd=REPO`: a worktree made
for real with `git worktree add`, the override, and the fallback when the cwd is not a checkout.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLAIM_OPEN = ROOT / "bin" / "claim-open"


def _load() -> ModuleType:
    """Import bin/claim-open as a module (it has no .py suffix, so the loader is explicit --
    spec_from_file_location answers None for a file with no known suffix)."""
    loader = SourceFileLoader("claim_open_under_test", str(CLAIM_OPEN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture()
def in_dir():
    """Run part of a test from another directory, and come back even when it fails."""
    old = os.getcwd()

    def _go(path: Path | str) -> None:
        os.chdir(path)

    yield _go
    os.chdir(old)


@pytest.fixture(scope="module")
def linked_worktree(tmp_path_factory) -> Path:
    """A real linked worktree of this repository, off HEAD, detached so no branch is claimed."""
    dest = tmp_path_factory.mktemp("wt") / "lane-probe"
    p = subprocess.run(  # noqa: S603, S607 -- fixed argv, no shell
        ["git", "worktree", "add", "--detach", str(dest), "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        pytest.skip(f"cannot make a worktree here: {p.stderr.strip()[:200]}")
    try:
        yield dest
    finally:
        subprocess.run(  # noqa: S603, S607
            ["git", "worktree", "remove", "--force", str(dest)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )


def test_from_a_worktree_the_claim_is_about_the_worktree(
    linked_worktree: Path, in_dir
) -> None:
    in_dir(linked_worktree)
    mod = _load()
    assert Path(mod.REPO).resolve() == linked_worktree.resolve(), (
        "claim-open measured "
        f"{mod.REPO} while standing in {linked_worktree} — the defect this file was written for"
    )
    # And it must be a tree the claim can actually be gated in.
    assert (Path(mod.REPO) / "bin" / "claim-gate").exists()
    assert (Path(mod.REPO) / "bin" / "claim-open").exists()


def test_the_gate_it_runs_belongs_to_the_same_tree(
    linked_worktree: Path, in_dir
) -> None:
    in_dir(linked_worktree)
    mod = _load()
    gate = Path(mod.GATE).resolve()
    assert gate == (linked_worktree.resolve() / "bin" / "claim-gate"), (
        f"claim-open would judge {gate}, not the tree it just claimed"
    )


def test_the_override_wins_for_a_caller_that_is_not_in_a_tree(tmp_path, in_dir) -> None:
    in_dir(tmp_path)
    mod = _load()
    other = ROOT / "platform"
    os.environ["ESTATE_CLAIM_REPO"] = str(other)
    try:
        assert Path(mod.resolve_repo()).resolve() == other.resolve()
    finally:
        del os.environ["ESTATE_CLAIM_REPO"]


def test_a_directory_that_is_not_a_checkout_falls_back(tmp_path, in_dir) -> None:
    """Fail closed, not silent: a cwd with no repository (or one that cannot gate a claim) must
    land back on this script's own repo rather than claiming against a tree it cannot judge."""
    in_dir(tmp_path)
    mod = _load()
    assert Path(mod.REPO).resolve() == ROOT.resolve()


def test_the_dev_checkout_is_still_its_own_answer(in_dir) -> None:
    """The single-checkout case is what the script was written for; it must not regress."""
    in_dir(ROOT)
    mod = _load()
    assert Path(mod.REPO).resolve() == ROOT.resolve()


def test_python_can_still_syntax_check_it() -> None:
    p = subprocess.run(  # noqa: S603, S607 -- fixed argv, no shell
        [sys.executable, "-m", "py_compile", str(CLAIM_OPEN)],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr


def _plan_ledger(tmp_path: Path, instruction_id: str, *, complete: bool = True) -> Path:
    plans = tmp_path / "plans"
    plans.mkdir(parents=True)
    events = [
        {
            "tool": "declare_plan",
            "session": "session-1",
            "args": {
                "goal": "Bind every claim to one instruction and one complete plan",
                "subgoals": [{"id": "g1", "text": "validate the claim contract"}],
                "instruction_id": instruction_id,
                "prompt": "founder-a",
            },
        }
    ]
    if complete:
        events.extend(
            [
                {
                    "tool": "add_bdd",
                    "session": "session-1",
                    "args": {
                        "goal_id": "g1",
                        "given": "a claimed change",
                        "when": "claim-open runs",
                        "then": "the claim carries the instruction and plan digest",
                    },
                },
                {
                    "tool": "address_edgecases",
                    "session": "session-1",
                    "args": {
                        "goal_id": "g1",
                        "edgecases": ["an incomplete plan is refused"],
                    },
                },
                {
                    "tool": "address_2nd_order_effects",
                    "session": "session-1",
                    "args": {
                        "goal_id": "g1",
                        "effects": ["the gate and broker consume one parser"],
                    },
                },
            ]
        )
    (plans / "session-1.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n"
    )
    return plans


def test_claim_open_requires_a_complete_plan_and_returns_its_digest(tmp_path):
    mod = _load()
    complete = _plan_ledger(tmp_path / "complete", "INS-00004")
    plan, digest = mod.claim_plan("session-1", "INS-00004", ledger_dir=complete)
    assert plan["instruction_id"] == "INS-00004"
    assert len(digest) == 64

    incomplete = _plan_ledger(tmp_path / "incomplete", "INS-00004", complete=False)
    with pytest.raises(mod.ClaimPreconditionError, match="BDD|edge case|second-order"):
        mod.claim_plan("session-1", "INS-00004", ledger_dir=incomplete)


def test_the_claim_comment_renders_the_full_plan(tmp_path):
    mod = _load()
    plans = _plan_ledger(tmp_path, "INS-00004")
    plan, digest = mod.claim_plan("session-1", "INS-00004", ledger_dir=plans)

    body = mod.claim_body(
        agent="codex",
        instruction="INS-00004",
        plan=plan,
        digest=digest,
        paths=["bin/claim-open", "tests/test_claim_open_worktree.py"],
        heartbeat="2026-11-11T00:00:00Z",
    )

    assert "CLAIM agent=codex instruction=INS-00004 plan=" + digest in body
    assert "Goal: Bind every claim" in body
    assert "Subgoal g1: validate the claim contract" in body
    assert "Edge case: an incomplete plan is refused" in body
    assert "Second-order effect: the gate and broker consume one parser" in body


def test_commit_trailers_carry_the_same_instruction_and_plan():
    mod = _load()
    digest = "a" * 64
    message = mod.with_trailers(
        "fix(claims): bind the plan",
        num=7901,
        agent="codex",
        instruction="INS-00004",
        digest=digest,
    )
    assert "Claim: #7901" in message
    assert "Agent: codex" in message
    assert "Instruction: INS-00004" in message
    assert f"Plan: {digest}" in message


def test_claim_open_refreshes_and_imports_the_current_sessions_prompts(
    monkeypatch,
):
    mod = _load()
    calls: list[list[str]] = []
    timeouts: list[int] = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        timeouts.append(kwargs.get("timeout", 0))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(mod, "run", fake_run)
    mod.collect_current_session("session-1")

    assert calls[0][1].endswith("bin/founder-prompt-collector")
    assert calls[0][2:] == ["collect"]
    assert calls[1][1].endswith("bin/instruction")
    assert calls[1][2:] == [
        "import-prompts",
        "--session",
        "session-1",
    ]
    assert timeouts == [60, 60]


def test_a_stalled_subprocess_is_bounded_and_named(monkeypatch):
    """A claim door that can hang forever is a claim door every session learns to bypass.

    Measured 2026-11-10: bin/claim-open blocked in select() for 45s with subprocess.run and no
    `timeout=`, printed nothing, and answered only when an external alarm killed it -- at which
    point the real error surfaced. The session that hits that learns to hand-post CLAIM comments,
    which is the duplication the claim exists to prevent (AGENTS.md section 5, ADR 0044 D-Pin 2).

    This test executes the bound: a command that never reads to completion must raise a
    ClaimPreconditionError, within the budget, naming the command that stalled.
    """
    import subprocess as sp
    import time

    mod = _load()
    monkeypatch.setattr(mod, "SUBPROCESS_BUDGET_S", 2, raising=False)

    started = time.monotonic()
    with pytest.raises(mod.ClaimPreconditionError) as caught:
        mod.run(["/bin/sh", "-c", "read x < /dev/zero"])
    elapsed = time.monotonic() - started

    assert elapsed < 8, f"the bound did not hold: took {elapsed:.1f}s"
    message = str(caught.value)
    # The refusal must name what stalled, or it is indistinguishable from a bug.
    assert "/bin/sh" in message
    assert "2s" in message
    assert "no claim was posted" in message
    # And it must be the door's own refusal type, not a raw TimeoutExpired escaping as a traceback.
    assert not isinstance(caught.value, sp.TimeoutExpired)


def test_the_stall_budget_is_defined_before_it_is_used():
    """A NameError on import is the same defect one layer down.

    SUBPROCESS_BUDGET_S is read inside resolve_repo(), which runs at module import (REPO =
    resolve_repo()). Defining the constant below that call made every invocation die with
    `NameError: name 'SUBPROCESS_BUDGET_S' is not defined` -- caught by running it, not by
    parsing it. This test makes that ordering a contract.
    """
    mod = _load()
    assert isinstance(mod.SUBPROCESS_BUDGET_S, int)
    assert mod.SUBPROCESS_BUDGET_S > 0
    # resolve_repo() already ran at import and used the constant; reaching here proves ordering.
    assert mod.REPO
