"""main's own CI run is never cancelled by the next commit.

Measured 2026-09-05, `gh run list --branch main --workflow ci.yml -L 12`: nine cancelled, two
failures, one success. `concurrency.cancel-in-progress: true` applied to every ref, so each merge
and each image-update commit cancelled the run that was grading the commit before it. main is the
only place `offline-gate` runs (it carries `if: github.event_name != 'pull_request'`), so the whole
AGENTS.md rule table was graded once in twelve pushes.

A superseded run on a pull request is waste and should still be cancelled; a superseded run on main
is the estate's only grade of the merged state.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))


def _concurrency(doc: dict) -> dict | None:
    c = doc.get("concurrency")
    return c if isinstance(c, dict) else None


def test_no_workflow_cancels_a_run_on_main_unconditionally() -> None:
    offenders = []
    for f in WORKFLOWS:
        doc = yaml.safe_load(f.read_text()) or {}
        c = _concurrency(doc)
        if not c:
            continue
        # `on:` parses to the boolean True as a yaml key; the branches a push grades are under it.
        on = doc.get(True) or doc.get("on") or {}
        push = (on or {}).get("push") or {}
        branches = push.get("branches") or []
        if "main" not in branches:
            continue
        cancel = c.get("cancel-in-progress")
        group = str(c.get("group", ""))
        if cancel is True and "github.ref" in group:
            offenders.append(f.name)
    assert not offenders, offenders


def test_ci_still_cancels_superseded_runs_off_main() -> None:
    """The cheap half of the trade is kept: a pull request's stale run is still cancelled."""
    doc = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    cancel = str(_concurrency(doc)["cancel-in-progress"])
    assert "github.ref" in cancel and "refs/heads/main" in cancel, cancel
