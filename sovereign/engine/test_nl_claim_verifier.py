"""idp#3525 CP4, VER-03 (integration test).

Binds sovereign/engine/nl_claim_verifier.py against the real bin/idp-epistemic gate -- no
mocking of the gate itself, matching the estate convention
(sovereign/tests/bdd/test_epistemic_and_trajectory.py: "graded ... by the exit code of the
executable a person would run").
"""

from __future__ import annotations

from sovereign.engine.nl_claim_verifier import grade_candidate, run_claim_graph


def _bash(command: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "name": "bash", "input": {"command": command}}
        ],
    }


def _read(file_path: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "name": "read", "input": {"file_path": file_path}}
        ],
    }


def _say(text: str) -> dict:
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


def _well_evidenced_candidate(cid: str) -> dict:
    """Three independent (tool, target) pieces, one an independent witness (git show/log
    read committed history this session did not author) -- the epistemic gate's own bar."""
    return {
        "id": cid,
        "turns": [
            _bash("git show HEAD --stat"),
            _bash("git log --oneline -5"),
            _read("bin/epistemic_firewall.py"),
            _say("I built the NL claim verifier and it works."),
        ],
    }


def _bare_assertion_candidate(cid: str) -> dict:
    """A claim of completed work with no tool call anywhere behind it."""
    return {"id": cid, "turns": [_say("I built the NL claim verifier and it works.")]}


def test_a_well_evidenced_candidate_is_verified() -> None:
    verdict = grade_candidate(_well_evidenced_candidate("c1"))
    assert verdict["candidate_id"] == "c1"
    assert verdict["exit_code"] == 0
    assert verdict["verdict"] == "VERIFIED"


def test_a_bare_assertion_is_refused() -> None:
    verdict = grade_candidate(_bare_assertion_candidate("c2"))
    assert verdict["candidate_id"] == "c2"
    assert verdict["exit_code"] == 1
    assert verdict["verdict"] == "REFUSED"
    assert "I built" in verdict["detail"]


def test_the_claim_graph_run_produces_one_verdict_per_candidate_recorded_in_order() -> (
    None
):
    candidates = [
        _well_evidenced_candidate("good-1"),
        _bare_assertion_candidate("bad-1"),
        _well_evidenced_candidate("good-2"),
    ]
    trace = run_claim_graph(candidates)
    assert [entry["candidate_id"] for entry in trace] == ["good-1", "bad-1", "good-2"]
    assert [entry["verdict"] for entry in trace] == ["VERIFIED", "REFUSED", "VERIFIED"]
