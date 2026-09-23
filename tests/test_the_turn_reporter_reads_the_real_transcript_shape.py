"""The Stop reporter counts what is actually in a Claude Code transcript.

Until 2026-09-21 this hook read `entry["type"] == "tool_use"` at the top level of each
transcript line. Claude Code never writes that: tool_use blocks are nested inside
`message.content[]` under a line whose top-level type is "assistant". Measured on one
real 3,029,574-byte transcript: 0 top-level tool_use entries, 56 nested ones. The
compliance line therefore printed `bash_calls=0 ... -> PASS` for every session ever run,
and the cache hit-rate printed 0.0% against 104 entries carrying `message.usage`.

Every case below feeds the real nested shape and asserts on the counts the report prints.
No case asserts on a docstring, a comment or a substring of the report text: the estate
has been burned by guards that graded a proxy instead of the thing itself.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_HOOK = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "after_agent_turn.py"
)
# Quarantine gate: same `.claude/hooks/` infrastructure gap as test_the_token_gate_*.
# See that file's skip-reason block for the rationale. The hook is loaded at module top
# (before any test function), so a missing file is an error not a failure -- skip whole
# module with an explicit reason rather than letting CI turn red on a gap unrelated to
# this PR's diff.
if not _HOOK.exists():
    pytest.skip(
        f"claude session hook {_HOOK.name} is not materialised in this checkout",
        allow_module_level=True,
    )
_spec = importlib.util.spec_from_file_location("after_agent_turn", _HOOK)
assert _spec and _spec.loader
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def fresh() -> dict:
    return {
        "turns": 0,
        "bash_calls": 0,
        "idp_exec_calls": 0,
        "mcp_calls": 0,
        "total_input_tokens": 0,
        "total_cache_read": 0,
        "compactions": 0,
        "proxy_refused": 0,
        "seen": [],
    }


def assistant(uuid: str, blocks: list, usage: dict | None = None) -> dict:
    """One real Claude Code assistant line: tool_use nested under message.content."""
    message: dict = {"role": "assistant", "content": blocks}
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "uuid": uuid, "message": message}


def bash_block(command: str) -> dict:
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def test_a_nested_bash_call_is_counted() -> None:
    state = fresh()
    hook._count_entry(assistant("u1", [bash_block("cat huge.log")]), state)
    assert state["bash_calls"] == 1
    assert state["idp_exec_calls"] == 0


def test_the_wrapped_form_is_counted_as_compliant() -> None:
    state = fresh()
    hook._count_entry(assistant("u1", [bash_block("bin/idp-exec cat huge.log")]), state)
    assert (state["bash_calls"], state["idp_exec_calls"]) == (1, 1)


def test_a_top_level_tool_use_line_is_not_what_claude_code_writes() -> None:
    """The old parser's shape. If this ever starts counting, the fix has been reverted
    to a parser that reads a shape Claude Code does not emit."""
    state = fresh()
    hook._count_entry(
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}, state
    )
    assert state["bash_calls"] == 0


def test_raw_calls_make_the_report_fail() -> None:
    """A gate that cannot fail is not a gate — so prove this one fails."""
    state = fresh()
    hook._count_entry(assistant("u1", [bash_block("ls -la")]), state)
    report = hook._format_report(state, "sess-123456789012")
    assert "-> FAIL" in report
    assert "bash_calls=1 idp_exec=0 raw=1" in report


def test_a_fully_wrapped_session_passes() -> None:
    state = fresh()
    hook._count_entry(assistant("u1", [bash_block("bin/idp-exec ls")]), state)
    report = hook._format_report(state, "sess-123456789012")
    assert "-> PASS" in report


def test_usage_is_read_from_message_not_the_top_level() -> None:
    state = fresh()
    hook._count_entry(
        assistant("u1", [], usage={"input_tokens": 40, "cache_read_input_tokens": 960}),
        state,
    )
    assert (state["total_input_tokens"], state["total_cache_read"]) == (40, 960)
    assert "hit_rate=96.0%" in hook._format_report(state, "sess-123456789012")


def test_a_top_level_usage_key_is_not_what_claude_code_writes() -> None:
    state = fresh()
    hook._count_entry(
        {"type": "assistant", "uuid": "u1", "usage": {"input_tokens": 99}}, state
    )
    assert state["total_input_tokens"] == 0


def test_mcp_calls_are_counted_separately_from_bash() -> None:
    state = fresh()
    hook._count_entry(
        assistant("u1", [{"type": "tool_use", "name": "mcp__estate__recall"}]), state
    )
    assert (state["mcp_calls"], state["bash_calls"]) == (1, 0)


def test_a_compact_boundary_is_counted() -> None:
    state = fresh()
    hook._count_entry(
        {"type": "system", "subtype": "compact_boundary", "uuid": "u1"}, state
    )
    assert state["compactions"] == 1


def test_a_ceiling_refusal_in_a_tool_result_is_counted() -> None:
    state = fresh()
    entry = {
        "type": "user",
        "uuid": "u1",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "content": "Refused before it was sent: 200K"}
            ],
        },
    }
    hook._count_entry(entry, state)
    assert state["proxy_refused"] == 1


def test_the_same_line_is_not_counted_twice_across_turns(
    tmp_path: pathlib.Path,
) -> None:
    """The hook re-reads the transcript tail on every Stop. Without a dedupe key the
    counts would inflate every turn and the report would be fiction."""
    import json

    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps(assistant("u1", [bash_block("ls")]))
        + "\n"
        + json.dumps(assistant("u2", [bash_block("bin/idp-exec ls")]))
        + "\n"
    )
    state = fresh()
    hook._measure_transcript(str(transcript), state)
    hook._measure_transcript(str(transcript), state)
    hook._measure_transcript(str(transcript), state)
    assert state["turns"] == 3
    assert state["bash_calls"] == 2, "transcript lines were counted more than once"
    assert state["idp_exec_calls"] == 1


def test_a_missing_transcript_still_advances_the_turn_counter(
    tmp_path: pathlib.Path,
) -> None:
    state = fresh()
    hook._measure_transcript(str(tmp_path / "nope.jsonl"), state)
    assert state["turns"] == 1
    assert state["bash_calls"] == 0


def test_a_state_file_written_before_the_dedupe_key_existed_still_loads() -> None:
    """Older state files have no "seen" key; the hook must not KeyError on them."""
    state = fresh()
    del state["seen"]
    hook._measure_transcript("", state)
    assert state["seen"] == []


@pytest.mark.parametrize("missing", ["/nonexistent/ledger.jsonl"])
def test_the_gateway_line_says_so_when_the_ledger_is_absent(
    missing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It used to print "all 8 mechanisms active" unconditionally — an assertion where a
    measurement belongs."""
    monkeypatch.setattr(hook, "LEDGER", missing)
    line = hook._gateway_line()
    assert "has not run" in line
    assert "all 8 mechanisms active" not in line


def test_the_gateway_line_reports_what_the_ledger_holds(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"at": "2026-09-18T18:51:19Z", "bytes_saved": 14522})
        + "\n"
        + json.dumps({"at": "2026-09-18T18:51:20Z", "bytes_saved": 101189})
        + "\n"
    )
    monkeypatch.setattr(hook, "LEDGER", str(ledger))
    line = hook._gateway_line()
    assert "2 proxied calls" in line
    assert "115,711 bytes saved" in line
    assert "2026-09-18T18:51:20Z" in line
