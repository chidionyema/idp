"""Every agent's sessions reach the page, not only Claude's.

Founder, 2026-09-13: "look just fix the second defect ... this as
~/.claude/state/prompt-ledger/ should be from all agents no claude only".

The estate runs five agent harnesses. Only one of them -- Claude -- had its
session ledgers discovered, because every layer of the sessions path spelled
`claude` into the string:

  * `bin/catalog-gen` rendered rows whose `estate/path` is
    `~/.claude/state/prompt-ledger/...`;
  * the MCP tool filtered for `{@HOME@}/.claude/state/prompt-ledger/`, a token
    the generator stopped writing, so the prefix matched nothing and the tool
    answered `count: 0` with `available: true`.

This file grades the filter, the one layer that decides what the founder sees.
It is deliberately a behaviour test: it builds real rows and asserts which ones
come back, never that a particular string appears in a file.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = REPO / "mcp" / "plugins" / "estate_sessions.py"


def _plugin():
    """Load the plugin by file path.

    `mcp/` ships no `__init__.py`, so `import mcp.plugins.estate_sessions` is a
    ModuleNotFoundError. The memory plugin's test loads its module the same way.
    """
    spec = importlib.util.spec_from_file_location("estate_sessions_agents", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sessions():
    return _plugin()


def _ledger_row(path: str) -> dict:
    """One catalogue ledger row, shaped exactly as bin/catalog-gen emits it."""
    name = path.replace("/", "-").replace(".", "")
    return {
        "apiVersion": "backstage.io/v1alpha1",
        "kind": "Resource",
        "metadata": {
            "name": name,
            "annotations": {"estate/kind": "ledger", "estate/path": path},
        },
        "spec": {"type": "ledger"},
    }


# The session stores measured on this machine, 2026-09-13. Claude writes one
# ledger per project; pi writes one transcript per session under a per-project
# directory; gemini writes chats under a per-agent tmp directory. Codex and
# Cursor keep no transcript on disk, so they contribute no rows and are not
# pretended otherwise.
ALL_AGENT_SESSION_PATHS = [
    "~/.claude/state/prompt-ledger/idp.jsonl",
    "~/.pi/agent/sessions/--Users-chidionyema--/2026-08-24T18-11-14-554Z_x.jsonl",
    "~/.gemini/tmp/agent-5/chats/session-2026-05-14T21-11-6bb079c8.jsonl",
]


def test_a_pi_session_is_not_filtered_out(sessions):
    """pi runs sessions on this machine; its rows must reach the founder."""
    row = _ledger_row(
        "~/.pi/agent/sessions/--Users-chidionyema--/2026-08-24T18-11-14-554Z_x.jsonl"
    )
    assert sessions.is_session_row(row), (
        "a pi session ledger is a session; the filter dropped it"
    )


def test_a_gemini_session_is_not_filtered_out(sessions):
    row = _ledger_row(
        "~/.gemini/tmp/agent-5/chats/session-2026-05-14T21-11-6bb079c8.jsonl"
    )
    assert sessions.is_session_row(row), (
        "a gemini session ledger is a session; the filter dropped it"
    )


def test_a_claude_session_still_reaches_the_page(sessions):
    """The agent that already worked must keep working."""
    row = _ledger_row("~/.claude/state/prompt-ledger/idp.jsonl")
    assert sessions.is_session_row(row)


def test_the_rows_the_live_generator_actually_writes_are_sessions(sessions):
    """Graded against the exact string in catalog/catalog-info.yaml.

    The catalogue writes `~/.claude/state/prompt-ledger` (a literal tilde, zero
    `{@HOME@}` tokens). The shipped default filter expected `{@HOME@}/...`, so
    this assertion failed and the page read zero sessions while the estate ran
    hundreds.
    """
    row = _ledger_row("~/.claude/state/prompt-ledger")
    assert sessions.is_session_row(row), (
        "the prefix bin/catalog-gen writes is not the prefix this filter accepts"
    )


def test_an_estate_state_ledger_is_still_not_a_session(sessions):
    """A ledger that is not a transcript never becomes a session row.

    `~/.claude/state/tickets` and the other canonical op boards are ledgers of
    estate state, not conversations. Widening the filter to every agent must
    not drag them in.
    """
    for path in (
        "~/.claude/state/tickets",
        "~/.claude/state/hook-outcomes",
        "~/.claude/ESTATE_BOARD.jsonl",
    ):
        assert not sessions.is_session_row(_ledger_row(path)), path


def test_a_non_ledger_is_never_a_session(sessions):
    row = _ledger_row("~/.pi/agent/sessions/whatever.jsonl")
    row["spec"]["type"] = "database"
    assert not sessions.is_session_row(row)


def test_every_agent_store_is_discovered_from_a_declared_root(sessions):
    """The roots are one declared list, not a literal per call site.

    LAW 46: the store layout is data the estate declares, and adding a sixth
    harness is a row in that list rather than an edit to a filter expression.
    """
    roots = sessions.SESSION_STORE_ROOTS
    joined = " ".join(roots)
    for agent in (".claude", ".pi", ".gemini"):
        assert agent in joined, f"{agent} is not among the declared session roots"
    assert all(r.startswith("~/") for r in roots), roots
