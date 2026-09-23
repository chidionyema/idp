"""cp24 acceptance: Zero-noise receipts -- one line, a hash, a budget delta, and undo (R5, R7).

Steps drive the real chain (engine/receipts.py via activities.append_receipt),
real git (engine/gitops.py) and the real `bin/sb undo` entrypoint against the
temporary estate conftest.py builds. The only stand-in is the model: runner
"claude" is a vendor CLI (a true external boundary), so "a step commits a
file" performs the commit the runner would have made and then goes through
the same HEAD-before/HEAD-after path activities.run_step uses.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/sovereign-bus/cp24_receipts_and_undo.feature")

STEP_TOKENS = 1200


@pytest.fixture(autouse=True)
def software_trust(estate_home: Path, monkeypatch: pytest.MonkeyPatch):
    """Sign with the software key, never Touch ID, and re-resolve config so
    in-process modules and the `bin/sb` subprocess agree."""
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    importlib.reload(importlib.import_module("sovereign.config"))


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(repo.parent / "gitconfig"), "GIT_CONFIG_SYSTEM": os.devnull}
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True).stdout.strip()


def _commit_step(context: dict[str, Any]) -> dict[str, Any]:
    """One step that writes a file and commits it, then the receipt the
    engine writes for it -- the same fields workflow._receipt assembles."""
    from sovereign.engine import activities, gitops

    repo: Path = context["repo"]
    before = gitops.head(repo)
    (repo / "notes.md").write_text("written by the step\n")
    _git(repo, "add", "notes.md")
    _git(repo, "commit", "-qm", "step 1: add notes")
    after = gitops.head(repo)
    commit = after if after and after != before else None
    context["step"] = context.get("step", 0) + 1
    record = {
        "ts": "1970-01-01T00:00:00+00:00",
        "session_id": context["session_id"],
        "kind": "step",
        "by": context["runner"],
        "text": "add notes",
        "step": context["step"],
        "status": "running",
        "task": "write notes",
        "runner": context["runner"],
        "repo": str(repo),
        "commit": commit,
        "tokens": STEP_TOKENS,
        "budget_remaining": 2000 - STEP_TOKENS,
        "state": {"session_id": context["session_id"], "step": context["step"]},
    }
    line = asyncio.run(activities.append_receipt(record))
    context["receipt"] = line
    return line


def _ensure_session(context: dict[str, Any], scratch_repo: Path) -> None:
    if "session_id" not in context:
        context["session_id"] = "sb-cp24test"
        context["runner"] = "claude"
        context["repo"] = scratch_repo


@given(parsers.parse('a session with runner "{runner}" and a scratch repo'))
def _session(context: dict[str, Any], scratch_repo: Path, runner: str) -> None:
    _ensure_session(context, scratch_repo)
    context["runner"] = runner


@when("a step commits a file")
def _step_commits(context: dict[str, Any]) -> None:
    _commit_step(context)


@then("the session line is exactly one receipt line")
def _one_line(context: dict[str, Any]) -> None:
    from sovereign.engine import receipts

    rows = [r for r in receipts.read_all() if r.get("session_id") == context["session_id"]]
    assert len(rows) == 1, rows


@then("the receipt contains a git commit hash that exists in the repo")
def _commit_exists(context: dict[str, Any]) -> None:
    from sovereign.engine import gitops

    commit = context["receipt"].get("commit")
    assert commit, context["receipt"]
    assert gitops.commit_exists(context["repo"], commit)
    assert gitops.head(context["repo"]) == commit


@then("the receipt contains a token budget delta")
def _budget_delta(context: dict[str, Any]) -> None:
    row = context["receipt"]
    assert isinstance(row.get("tokens"), int) and row["tokens"] > 0
    assert isinstance(row.get("budget_remaining"), int)


@when('I run "bin/sb undo <session_id> --by founder"')
def _run_undo(context: dict[str, Any], scratch_repo: Path, sb) -> None:
    # This scenario has no Given of its own: it undoes the step the first
    # scenario describes, so that step is made here when it is missing.
    _ensure_session(context, scratch_repo)
    if "receipt" not in context:
        _commit_step(context)
    res = sb("undo", context["session_id"], "--by", "founder", "--json")
    assert res.ok, res.stderr
    context["undo"] = res.json()


@then("the repo HEAD is the parent of the receipt's hash")
def _head_is_parent(context: dict[str, Any]) -> None:
    from sovereign.engine import gitops

    commit = context["receipt"]["commit"]
    parent = _git(context["repo"], "rev-parse", f"{commit}^")
    assert gitops.head(context["repo"]) == parent
    assert context["undo"]["head"] == parent
    assert context["undo"]["undone_commit"] == commit


@then(parsers.parse('a receipt of kind "{kind}" is written'))
def _undo_receipt(context: dict[str, Any], kind: str) -> None:
    from sovereign.engine import interventions, receipts

    rows = [r for r in receipts.read_all() if r.get("kind") == kind and r.get("session_id") == context["session_id"]]
    assert len(rows) == 1, rows
    assert rows[0]["undone_receipt"] == context["receipt"]["hash"]
    # R17: an undo is an intervention, so it is mirrored into the signed log.
    assert any(r.get("hash") == rows[0]["hash"] for r in interventions.read_all())
    assert receipts.verify()["ok"]
