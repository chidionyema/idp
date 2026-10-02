"""The approvals adapter reads the real ledger and classifies a vanished ledger before it vanishes.

crew#1013: FleetView's approvals stream must say "approved" when a proposal stops being pending
*and* its staged patch is gone. That is the case the first implementation could not see: an
approved ledger has left every current set, so a detection that reads only the current snapshot
never observes the departure.

These tests do not assert the adapter's text back at it. They load the real module by path -- the
same way `run_approvals_adapter` loads its `nats_adapter` sibling -- point it at a real ledger on
disk, let it read that ledger with its own `_snapshot()`, and assert on the events it computes.
The snapshot half is graded against a filesystem the test builds; the transition half is graded
against what the adapter saw, so a regression in either the reader or the classifier is caught.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    ROOT
    / "backstage"
    / "plugins"
    / "fleetview-backend"
    / "src"
    / "fleetview_backend"
    / "approvals_adapter.py"
)

# Load the real module by path, as the adapter loads its own sibling at runtime.
_spec = importlib.util.spec_from_file_location("fv_approvals_under_test", ADAPTER)
assert _spec is not None and _spec.loader is not None, f"cannot load {ADAPTER}"
aa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aa)


def _write_ledger(root: Path, *, proposals: list[str], staged: list[str]) -> None:
    """Build a real mutations ledger on disk: proposals/<id>.json and staged/<id>.patch."""
    pd = root / "proposals"
    sd = root / "staged"
    pd.mkdir(parents=True, exist_ok=True)
    sd.mkdir(parents=True, exist_ok=True)
    for lid in proposals:
        (pd / f"{lid}.json").write_text(json.dumps({"claim": f"mutate {lid}"}))
    for lid in staged:
        (sd / f"{lid}.patch").write_text(f"--- {lid}\n")


def test_snapshot_reads_a_real_ledger_from_disk(tmp_path, monkeypatch):
    # The reader is graded against a filesystem, not against its own source.
    monkeypatch.setenv("IDP_EXECUTOR_RUNS", str(tmp_path))
    _write_ledger(tmp_path, proposals=["L1", "L2"], staged=["L2"])
    proposals, staged = aa._snapshot()
    assert proposals == {"L1", "L2"}
    assert staged == {"L2"}


def test_a_real_ledger_that_vanishes_after_staging_is_approved(tmp_path, monkeypatch):
    # Build the ledger, READ IT with the adapter, then remove it the way an approval does --
    # both the proposal and the staged patch are gone by the time the next poll looks.
    monkeypatch.setenv("IDP_EXECUTOR_RUNS", str(tmp_path))
    _write_ledger(tmp_path, proposals=["L1"], staged=["L1"])

    # First poll: the adapter reads the real ledger and records L1 as pending+staged.
    proposals, staged = aa._snapshot()
    assert proposals == {"L1"} and staged == {"L1"}
    prev = {"L1": frozenset({"pending", "staged"})}

    # Approval removes both files; the next poll must still report the departure.
    (tmp_path / "proposals" / "L1.json").unlink()
    (tmp_path / "staged" / "L1.patch").unlink()
    proposals, staged = aa._snapshot()

    assert aa._transitions(prev, proposals, staged) == [("L1", "approved")]


def test_a_real_ledger_that_vanishes_before_staging_is_withdrawn(tmp_path, monkeypatch):
    monkeypatch.setenv("IDP_EXECUTOR_RUNS", str(tmp_path))
    _write_ledger(tmp_path, proposals=["L1"], staged=[])
    prev = {"L1": frozenset({"pending"})}

    (tmp_path / "proposals" / "L1.json").unlink()
    proposals, staged = aa._snapshot()

    assert aa._transitions(prev, proposals, staged) == [("L1", "withdrawn")]


def test_a_ledger_still_on_disk_publishes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("IDP_EXECUTOR_RUNS", str(tmp_path))
    _write_ledger(tmp_path, proposals=["L1"], staged=[])
    prev = {"L1": frozenset({"pending"})}
    proposals, staged = aa._snapshot()
    assert aa._transitions(prev, proposals, staged) == []


def test_approval_is_not_also_reported_as_withdrawn():
    # The two detections overlap on a staged ledger; exactly one event may be emitted.
    prev = {"L1": frozenset({"pending", "staged"})}
    kinds = [k for _, k in aa._transitions(prev, proposals=set(), staged=set())]
    assert kinds == ["approved"]


def test_each_independent_ledger_is_classified_once():
    prev = {
        "approved": frozenset({"pending", "staged"}),
        "withdrawn": frozenset({"pending"}),
        "still-here": frozenset({"pending"}),
    }
    got = dict(aa._transitions(prev, proposals={"still-here"}, staged=set()))
    assert got == {"approved": "approved", "withdrawn": "withdrawn"}


def test_a_ledger_seen_for_the_first_time_publishes_nothing():
    # First poll: prev_state is empty, so nothing can have transitioned.
    assert aa._transitions({}, proposals={"L1"}, staged={"L2"}) == []
