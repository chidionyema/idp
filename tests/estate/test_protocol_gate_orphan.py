"""Falsifiers for the protocol gate's self-lock defects (AGENTS.md section 9 R2, R6).

A gate that cannot fail is not a gate, and a recovery path that depends on what it recovers is a
deadlock. Both defects below were observed in production on 2026-10-31 and trapped the estate for
nine days: the founder ran `thaw`, the gate printed "resumed 0 process(es)", and every tool call
was still denied because the break was still OPEN.

Each test here is written to FAIL before its fix and PASS after it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "platform" / "estate" / "gates" / "protocol_gate.py"


def _load_gate(tmp_path: Path):
    """Load the gate by file path: `platform` is shadowed by the stdlib module of that name."""
    os.environ["ESTATE_BREAKS_DIR"] = str(tmp_path)
    spec = importlib.util.spec_from_file_location("protocol_gate_under_test", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["protocol_gate_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _write_break(tmp_path: Path, **fields) -> str:
    break_id = fields.pop("id", "test-break-20260101T000000")
    body = {
        "id": break_id,
        "protocol": fields.pop("protocol", "founder-pause"),
        "state": fields.pop("state", "OPEN"),
        "opened_at": "2026-01-01T00:00:00Z",
        "error": fields.pop("error", "test break"),
    }
    body.update(fields)
    (tmp_path / (break_id + ".json")).write_text(json.dumps(body), encoding="utf-8")
    return break_id


def test_prose_probe_is_recognised_as_unprovable(tmp_path):
    """A sentence is not a probe. Before the fix, probe_defects() was only called at open_break, so a
    break opened before that guard existed carried prose forever and prove could never pass."""
    gate = _load_gate(tmp_path)
    prose = "all agent session processes report state T (stopped) via ps -Ao pid=,stat=,command="
    defects = gate.probe_defects([prose])
    assert defects, (
        "a prose sentence must be reported as a defective probe, not run as a command"
    )


def test_real_command_is_not_a_defective_probe(tmp_path):
    """The falsifier's other half: a genuine command must pass, or the guard rejects valid breaks."""
    gate = _load_gate(tmp_path)
    assert gate.probe_defects(["python3 /bin/true"]) == []


def test_prove_refuses_a_prose_probe_break(tmp_path, capsys):
    """Known-bad fixture: prove must refuse with exit 2 and name waive, never report a permanent rc=2
    as though it were an unfixed root cause."""
    gate = _load_gate(tmp_path)
    break_id = _write_break(
        tmp_path,
        probes=[
            "all agent session processes report state T (stopped) via ps -Ao pid=,stat=,command="
        ],
        baseline=["same prose"],
    )
    args = _prove_args(break_id)
    with pytest.raises(SystemExit) as exc:
        gate.cmd_prove(args)
    assert exc.value.code == 2, (
        "a structurally unprovable break must exit 2 (BLIND), not 1"
    )
    err = capsys.readouterr().err
    assert "can never be proven closed" in err
    assert "waive" in err, "the refusal must name the one route that actually works"


def test_empty_probes_are_vacuously_ok(tmp_path):
    """BUG: `bool(res) and all(...)` made all_ok([]) False, so a break with no probes could never be
    closed. Empty means 'nothing failed', which is the only reading that lets the break ever end."""
    gate = _load_gate(tmp_path)
    assert gate.all_ok([]) is True, (
        "a break with no probes must be closable (vacuous truth)"
    )
    assert gate.all_ok([{"rc": 0}]) is True
    assert gate.all_ok([{"rc": 0}, {"rc": 1}]) is False


def test_thaw_closes_a_prose_probe_break(tmp_path, capsys):
    """THE founder's deadlock: thaw resumed processes but left the break OPEN, so enforce_physical
    re-froze on the next alarm cycle. Resuming must release the break, or recovery depends on what it
    recovers and the estate cannot escape (R6)."""
    gate = _load_gate(tmp_path)
    break_id = _write_break(
        tmp_path,
        probes=[
            "all agent session processes report state T (stopped) via ps -Ao pid=,stat=,command="
        ],
        baseline=["same prose"],
    )
    assert [b["id"] for b in gate.breaks("OPEN")] == [break_id]

    gate.do_thaw()

    still_open = [b["id"] for b in gate.breaks("OPEN")]
    assert still_open == [], (
        "thaw must leave no OPEN break behind, or the next alarm re-freezes the fleet"
    )
    record = json.loads((tmp_path / (break_id + ".json")).read_text(encoding="utf-8"))
    assert record["state"] == "THAWED"
    assert "thawed" in capsys.readouterr().out


def test_thaw_does_not_release_a_probe_backed_break(tmp_path):
    """The guard on the guard: a real break with a runnable, still-failing probe must NOT be released by
    thaw. Otherwise the fix would let anyone clear a genuine outage by typing 'thaw'."""
    gate = _load_gate(tmp_path)
    break_id = _write_break(
        tmp_path,
        probes=["python3 -c 'import sys; sys.exit(1)'"],
        baseline=["python3 -c 'import sys; sys.exit(1)'"],
    )
    gate.do_thaw()
    assert [b["id"] for b in gate.breaks("OPEN")] == [break_id], (
        "thaw must not clear a break whose real probe still fails"
    )


def _prove_args(break_id: str):
    import argparse

    return argparse.Namespace(
        id=break_id,
        cause="x" * 60,
        guard_cmd="python3 -c 'import sys; sys.exit(0)'",
        evidence=None,
    )
