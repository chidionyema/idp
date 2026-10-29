"""The epistemic firewall's THIRD LEG: proof of progress, and the loop breaker.

These tests are the falsifier for the claim that the estate can now tell the difference between
"working on a hard problem" and "repeating an identical no-op forever". Every test here is a way
that claim could be wrong, and is made to fail if it is.

The estate measured the failure this closes on 2026-10-29: the reclaim guardian repeated one
useless step for thirty minutes while the volume fell from 2361 MB to 396 MB, reporting
`freed=?M` because the child was SIGKILLed before it could print its RESULT line.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIBEXEC = REPO / "platform" / "estate" / "libexec"
WATCH = REPO / "bin" / "idp-disk-watch"


def _load(name: str, path: Path):
    """Load a script by path, whatever it is called.

    importlib refuses a file with no .py suffix (bin/idp-disk-watch), so the loader is named
    explicitly. This is the same thing a launchd job does: it runs the file, it does not import a
    package.
    """
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


ep = _load("estate_epistemic_loop", LIBEXEC / "epistemic_loop.py")


# -- the ledger ------------------------------------------------------------------------------------


def test_the_ledger_is_append_only_and_readable(tmp_path):
    ledger = ep.LoopLedger(tmp_path / "progress.jsonl")
    ledger.append({"subject": "s", "action": "a", "verdict": ep.NO_PROGRESS})
    ledger.append({"subject": "s", "action": "a", "verdict": ep.NO_PROGRESS})
    rows = ledger.history()
    assert len(rows) == 2
    assert all("at" in r for r in rows), "every row is stamped"


def test_a_missing_ledger_is_an_empty_history_not_an_error(tmp_path):
    ledger = ep.LoopLedger(tmp_path / "nope.jsonl")
    assert ledger.history() == []


# -- the gate --------------------------------------------------------------------------------------


def test_progress_is_measured_from_the_world_not_from_the_worker(tmp_path):
    gate = ep.ProgressGate("t", "free_mb", ep.LoopLedger(tmp_path / "l.jsonl"))
    row = gate.judge("step-1", {"free_mb": 100}, {"free_mb": 140})
    assert row["verdict"] == ep.PROGRESS
    assert row["delta"] == 40


def test_no_progress_is_not_progress(tmp_path):
    gate = ep.ProgressGate("t", "free_mb", ep.LoopLedger(tmp_path / "l.jsonl"))
    row = gate.judge("step-1", {"free_mb": 100}, {"free_mb": 100})
    assert row["verdict"] == ep.NO_PROGRESS
    assert row["next"] == ep.BOUNDED


def test_a_regression_is_its_own_verdict(tmp_path):
    gate = ep.ProgressGate("t", "free_mb", ep.LoopLedger(tmp_path / "l.jsonl"))
    row = gate.judge("step-1", {"free_mb": 100}, {"free_mb": 60})
    assert row["verdict"] == ep.REGRESSION
    assert row["next"] == ep.CHANGE_ACTION


def test_a_lower_metric_can_be_the_goal(tmp_path):
    gate = ep.ProgressGate(
        "t", "latency_ms", ep.LoopLedger(tmp_path / "l.jsonl"), direction="lower"
    )
    row = gate.judge("step-1", {"latency_ms": 900}, {"latency_ms": 400})
    assert row["verdict"] == ep.PROGRESS


def test_blind_is_not_zero(tmp_path):
    """A measurement that could not be taken is not a measurement of nothing.

    This is the exact defect in the 2026-10-29 log: `freed=?M` was printed as if it were a
    number, and the guardian read its own unreadable field as "no progress" rather than
    "no knowledge".
    """
    gate = ep.ProgressGate("t", "free_mb", ep.LoopLedger(tmp_path / "l.jsonl"))
    row = gate.judge("step-1", {"free_mb": 100}, {"free_mb": None})
    assert row["verdict"] == ep.BLIND
    assert row["next"] == ep.ESCALATE
    row2 = gate.judge("step-2", {}, {"free_mb": 100})
    assert row2["verdict"] == ep.BLIND


def test_the_same_action_that_never_moves_becomes_a_loop(tmp_path):
    """The measurement that ends eight hours of looping: three no-progress attempts at one
    action is a LOOP, and the loop's answer is escalation, never a fourth identical attempt."""
    gate = ep.ProgressGate(
        "disk-guardian",
        "free_mb",
        ep.LoopLedger(tmp_path / "l.jsonl"),
        no_progress_limit=3,
    )
    verdicts = [
        gate.judge("cleaner phases=caches", {"free_mb": 100}, {"free_mb": 100})[
            "verdict"
        ]
        for _ in range(3)
    ]
    assert verdicts == [ep.NO_PROGRESS, ep.NO_PROGRESS, ep.LOOP]


def test_a_different_action_gets_its_own_budget(tmp_path):
    """Escalation must be possible: the new action is judged on its own history."""
    gate = ep.ProgressGate(
        "disk-guardian",
        "free_mb",
        ep.LoopLedger(tmp_path / "l.jsonl"),
        no_progress_limit=2,
    )
    for _ in range(2):
        gate.judge("action-a", {"free_mb": 100}, {"free_mb": 100})
    row = gate.judge("action-b", {"free_mb": 100}, {"free_mb": 100})
    assert row["verdict"] == ep.NO_PROGRESS, "a new action starts with its own budget"


def test_the_loop_count_is_derived_from_history_not_from_memory(tmp_path):
    """The gate reads the ledger, so a worker that restarts with a fresh memory still sees the
    loop it was in."""
    path = tmp_path / "l.jsonl"
    first = ep.ProgressGate("s", "free_mb", ep.LoopLedger(path), no_progress_limit=2)
    first.judge("a", {"free_mb": 1}, {"free_mb": 1})
    second = ep.ProgressGate("s", "free_mb", ep.LoopLedger(path), no_progress_limit=2)
    row = second.judge("a", {"free_mb": 1}, {"free_mb": 1})
    assert row["verdict"] == ep.LOOP
    assert second.times_tried("a") == 2


def test_the_gate_ignores_another_subjects_history(tmp_path):
    path = tmp_path / "l.jsonl"
    a = ep.ProgressGate("a", "free_mb", ep.LoopLedger(path), no_progress_limit=2)
    a.judge("x", {"free_mb": 1}, {"free_mb": 1})
    b = ep.ProgressGate("b", "free_mb", ep.LoopLedger(path), no_progress_limit=2)
    row = b.judge("x", {"free_mb": 1}, {"free_mb": 1})
    assert row["verdict"] == ep.NO_PROGRESS


# -- the escalation ladder --------------------------------------------------------------------------


def test_the_ladder_escalates_and_never_says_try_again():
    table = {
        v: ep.escalation_for(v)
        for v in (ep.PROGRESS, ep.NO_PROGRESS, ep.REGRESSION, ep.LOOP, ep.BLIND)
    }
    assert table[ep.LOOP]["next"] == ep.ESCALATE
    assert table[ep.LOOP]["invoke"] is True
    assert table[ep.BLIND]["invoke"] is True
    assert "try again" not in table[ep.LOOP]["action"].lower()
    assert table[ep.PROGRESS]["next"] == ep.CONTINUE


# -- the evidence fan-out ---------------------------------------------------------------------------


def test_correlated_probes_are_not_counted_twice():
    """One source that answers five times is ONE piece of evidence (arXiv 2610.17869, 2608.19701)."""
    probes = [
        ep.Probe("a", ["true"], "file:/tmp/x"),
        ep.Probe("b", ["true"], "file:/tmp/x"),
        ep.Probe("c", ["true"], "file:/tmp/y"),
    ]
    out = ep.fan_out(probes, budget_s=20)
    assert out["independent_sources"] == 2
    assert len(out["skipped_correlated"]) == 1
    assert out["skipped_correlated"][0]["name"] == "b"


def test_the_fan_out_counts_independent_sources_that_answered():
    probes = [
        ep.Probe("a", ["true"], "s1"),
        ep.Probe("b", ["true"], "s2"),
        ep.Probe("c", ["false"], "s3"),
    ]
    out = ep.fan_out(probes, budget_s=20)
    assert out["independent_sources"] == 3
    assert out["answered"] == 2
    assert out["failed"] == 1


def test_a_fan_out_with_nothing_answered_is_blind_not_negative():
    out = ep.fan_out([ep.Probe("a", ["false"], "s1")], budget_s=20)
    assert out["verdict"] == ep.BLIND


def test_the_fan_out_respects_its_budget():
    probes = [ep.Probe("slow", ["sleep", "5"], "s1", timeout_s=5)]
    out = ep.fan_out(probes, budget_s=0.01)
    assert out["budget_exhausted"] is True
    assert out["results"][0]["status"] == "budget"


def test_parallel_is_only_chosen_when_it_is_cheaper():
    """SquidAgent (arXiv 2610.08647): parallelise only when the critical path plus alignment
    costs less than the serial path."""
    cheap = [
        ep.Probe("a", ["true"], "s1", timeout_s=1),
        ep.Probe("b", ["true"], "s2", timeout_s=1),
        ep.Probe("c", ["true"], "s3", timeout_s=1),
    ]
    assert ep.fan_out(cheap, budget_s=20)["order"] == "parallel"
    one = [ep.Probe("a", ["true"], "s1", timeout_s=1)]
    assert ep.fan_out(one, budget_s=20)["order"] == "serial"


def test_a_probe_that_raises_does_not_kill_the_fan_out():
    def boom(p):
        raise RuntimeError("probe exploded")

    out = ep.fan_out(
        [ep.Probe("a", ["true"], "s1"), ep.Probe("b", ["true"], "s2")],
        budget_s=20,
        runner=boom,
    )
    assert out["failed"] == 2
    assert out["verdict"] == ep.BLIND


# -- the guardian's use of it ------------------------------------------------------------------------


def test_the_guardian_loads_the_gate_from_either_layout():
    """Installed, the guardian lives at ~/.estate/bin and the gate at ~/.estate/libexec; in a
    checkout they are bin/ and platform/estate/libexec. Both must work."""
    assert WATCH.exists()
    out = subprocess.run(
        [sys.executable, str(WATCH), "--print-gate"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "epistemic_loop" in out.stdout


def test_the_guardian_reports_the_delta_it_measured_itself():
    """The guardian owns the measurement: `freed=?M` was a field it never measured."""
    mod = _load("estate_disk_watch", WATCH)
    own = mod.synth_result(100, 180)
    assert own["freed_mb"] == "80"
    assert own["met"] == "no"
    assert own["free_after_mb"] == "180"
    blind = mod.synth_result(100, None)
    assert blind["freed_mb"] == "blind"
    assert blind["met"] == "blind"


def test_the_guardian_terminates_before_it_kills():
    """SIGKILL cannot be trapped, so the cleaner never printed its RESULT line. SIGTERM can."""
    src = WATCH.read_text()
    assert "proc.terminate()" in src, (
        "the guardian must TERM the step before it kills it"
    )
    assert src.index("proc.terminate()") < src.index("proc.kill()")


def test_the_guardian_escalates_instead_of_repeating():
    src = WATCH.read_text()
    assert "PHASE_LADDER" in src
    assert "escalate_incident" in src
    # the ladder must include the tier that holds the measured gigabytes
    assert "worktrees" in src


def test_the_escalation_state_survives_a_restart(tmp_path):
    mod = _load("estate_disk_watch_escalation", WATCH)
    mod.ESCALATION_STATE = tmp_path / "esc.json"
    mod.save_escalation({"rung": 2, "last_alert": 123.0})
    state = mod.load_escalation()
    assert state["rung"] == 2
    assert state["last_alert"] == 123.0
