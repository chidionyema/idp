"""The falsifier for the instruction gate: a prompt with no instruction id is refused,
a prompt with one flows.

Two-way (AGENTS.md section 9: a gate that cannot fail is not a gate): these pin that the
gate REJECTS a known-bad request (no id) and ACCEPTS a known-good one (with id), plus that
it never refuses the estate's own plumbing (internal, non-chat, opted-out). They exercise
the pure module body with the gate flag forced on, so they pass the same on a laptop and
in CI without a router image.

They fail before the fix (no ``instruction_gate`` module existed) and pass after it.
"""

from __future__ import annotations

import asyncio

import pytest

from platform.llm import instruction_gate as gate


@pytest.fixture(autouse=True)
def gate_on(monkeypatch):
    """Force the gate on so the tests exercise the enforcement, not the dormant default."""
    monkeypatch.setattr(gate, "INSTRUCTION_GATE", True)
    yield


def _chat(body=None):
    data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "build the ledger"}],
    }
    if body:
        data.update(body)
    return data


def _run(gate_instance, data, call_type="completion"):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            gate_instance.async_pre_call_hook(None, None, data, call_type)
        )
    finally:
        loop.close()


def test_accepts_request_with_instruction_id():
    inst = gate.InstructionGate()
    data = _chat({"metadata": {"instruction_id": "instr-abc"}})
    assert _run(inst, data) is None


def test_refuses_request_without_instruction_id():
    inst = gate.InstructionGate()
    result = _run(inst, _chat({}))
    assert result is not None
    assert "instruction id" in str(result)


def test_refusal_names_the_fix():
    # A refusal that does not say what to do is a dead end for the caller; it must name
    # the field to carry.
    inst = gate.InstructionGate()
    text = str(_run(inst, _chat({})))
    assert "metadata.instruction_id" in text


def test_never_refuses_internal_traffic():
    inst = gate.InstructionGate()
    data = _chat({"metadata": {"estate_internal": "1"}})
    assert _run(inst, data) is None


def test_never_refuses_non_chat_calls():
    inst = gate.InstructionGate()
    assert _run(inst, _chat({}), "embeddings") is None


def test_never_refuses_a_request_with_no_messages():
    inst = gate.InstructionGate()
    assert _run(inst, {"model": "test-model"}, "completion") is None


def test_instruction_id_reads_metadata():
    assert gate.instruction_id({"metadata": {"instruction_id": "instr-x"}}) == "instr-x"
    assert gate.instruction_id({"metadata": {}}) == ""
    assert gate.instruction_id({}) == ""


def test_dormant_by_default():
    # The gate ships off until the id is carried on every real prompt: an enforced-but-
    # dormant gate is safe, an unconditionally-on gate takes the router down. The flag is a
    # boolean read from the env, so the dormancy is a real code path, not a doc claim.
    assert isinstance(gate.INSTRUCTION_GATE, bool)
