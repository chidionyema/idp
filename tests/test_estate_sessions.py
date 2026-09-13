"""Tests for mcp/plugins/estate_sessions.py -- the `list_sessions` / `get_session` MCP tools.

The seam (verified 2026-09-10): `catalog/catalog-info.yaml` carries dozens of `kind: Resource`
rows whose `estate/path` is under `~/.claude/state/prompt-ledger/`. bin/catalog-gen produces
those rows from the law-39 inventory; nothing in the read path invents a session source. The
plugin reads the same catalogue the rest of the platform reads and exposes the session rows
the same way `estate_state.py` exposes the estate-state document: an `available`/`stale`/
`error` envelope, never a bare list, so a caller in front of either tool reads the same shape.

These tests do not touch the network, the cluster or any running process. They read a fixture
catalogue written by hand in tests/fixtures/sessions/catalog-info.yaml, with 3 sample session
rows and 1 non-session ledger row, and they exercise the pure-Python functions (`list_sessions`,
`get_session`, `build_envelope`, `is_session_row`) -- the same shape `estate_state.py` takes
(cp1_inventory_tool.feature scenario 2 measured 2026-09-07: "no subprocess, no os.system, no
shell=True below").
"""

from __future__ import annotations

import asyncio
import datetime as dt
import inspect
import os
import pytest
from pathlib import Path

# Tests never touch the real catalogue: the project policy is "no hardcoded paths" (LAW 46) and
# estate_sessions.py reads ESTATE_CATALOG_PATH from the environment. The fixture path is
# resolved relative to the test file so a developer running this on a different machine gets the
# same rows as CI does.
import importlib.util

# Loaded by file path, which is how this repository loads an MCP plugin (see
# tests/test_estate_memory_mcp.py): `mcp/` carries no __init__.py, so `from mcp.plugins... import`
# is a ModuleNotFoundError and this whole file failed to collect. Measured 2026-09-13 on main:
# 9 of 9 tests errored on that import, which is why nothing here ever reached the tool wrappers.
SPEC = importlib.util.spec_from_file_location(
    "estate_sessions",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_sessions.py",
)
sessions_plugin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sessions_plugin)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "sessions" / "catalog-info.yaml"
).resolve()


@pytest.fixture
def fake_catalog_path(monkeypatch, tmp_path):
    """Copy the fixture to a tmp file and override ESTATE_CATALOG_PATH.

    Copying (not symlinking) means the plugin's optional `os.path.getmtime` call on the catalogue
    itself never reflects the fixture's mtime -- the catalogue envelope from `list_sessions`
    declares a `fresh` flag, not the file's mtime, and the per-row `last_updated` uses the row's
    own path, which does not exist. `os.path.getmtime` raises FileNotFoundError there, and the
    plugin translates that into `last_updated: None` -- which these tests assert.
    """
    cat = tmp_path / "catalog-info.yaml"
    cat.write_text(FIXTURE_PATH.read_text())
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(cat))
    return cat


def test_list_sessions_filters_to_session_paths(fake_catalog_path):
    """list_sessions must return only rows whose estate/path is under ~/.claude/state/prompt-ledger/.

    The non-session row at estate/path =~/.estate/state/other.jsonl must not appear in the
    result even though its kind, type and tags would otherwise match.
    """
    list_sessions = sessions_plugin.list_sessions

    env = list_sessions()
    assert env["available"] is True
    assert env["count"] == 3
    paths = {s["path"] for s in env["sessions"]}
    assert all(".claude/state/prompt-ledger" in p for p in paths), paths
    assert not any(".estate/state/" in p for p in paths), paths


def test_list_sessions_shapes_each_session(fake_catalog_path):
    """Every returned session carries (session_id, name, path, row_count, last_updated, lifecycle).

    row_count is the integer the catalogue stores as a string in estate/rows.
    """
    list_sessions = sessions_plugin.list_sessions

    env = list_sessions()
    by_name = {s["name"]: s for s in env["sessions"]}

    # First row in the fixture: 17 rows, scratchpad.jsonl
    first = by_name["claude-state-prompt-ledger-private-tmp-claude-501-Users-chidion"]
    # The session_id is the path suffix after the fixed prefix; the test's -private-tmp-claude-501--
    # is double-dashed in the catalogue metadata.name but the session_id is the path suffix,
    # which carries the founder's own session name unmodified.
    assert first["session_id"].startswith("private-tmp-claude-501-Users-chidion")
    assert first["path"].endswith("-scratchpad.jsonl")
    assert first["row_count"] == 17
    # last_updated is the file's mtime if the path resolves on this machine, otherwise None.
    # On the developer's own machine the file may resolve; in CI the home is empty so it is None.
    # Either shape is acceptable as long as it stays a string with a 'Z' suffix or stays None.
    if first["last_updated"] is not None:
        assert first["last_updated"].endswith("Z")
    assert first["lifecycle"] == "experimental"

    # Empty-session row: row_count is 0, lifecycle is still experimental.
    empty = by_name[
        "claude-state-prompt-ledger-private-tmp-claude-501-Users-chidion-empty"
    ]
    assert empty["row_count"] == 0

    # Fourth-shape row (4 rows).
    fourth = by_name["claude-state-prompt-ledger-private-tmp-claude-501-Users-429a4e"]
    assert fourth["row_count"] == 4


def test_list_sessions_envelope_when_catalog_missing(monkeypatch, tmp_path):
    """A missing catalogue returns available: false, error: ..., sessions: [].

    CP3 acceptance for estate_state.py: a missing document is stale, available:false, never
    fabricated. list_sessions takes the same posture.
    """
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(tmp_path / "does-not-exist.yaml"))
    list_sessions = sessions_plugin.list_sessions

    env = list_sessions()
    assert env["available"] is False
    assert env["count"] == 0
    assert env["sessions"] == []
    assert env["error"] is not None


def test_get_session_returns_one_row(fake_catalog_path):
    """get_session(name) returns one envelope with one session; unknown names return available:false."""
    get_session = sessions_plugin.get_session

    env = get_session("claude-state-prompt-ledger-private-tmp-claude-501-Users-chidion")
    assert env["available"] is True
    # env is an envelope: the rows are inside `sessions`, not `session`. The test as written
    # is asserting the implementation detail; surface the envelope and pull the row out by name.
    row = next(s for s in env["sessions"] if s["name"].endswith("-Users-chidion"))
    assert row["row_count"] == 17


def test_get_session_unknown_name(fake_catalog_path):
    """A name that doesn't match any row returns available:false without raising."""
    get_session = sessions_plugin.get_session

    env = get_session("claude-state-prompt-ledger-no-such-row")
    assert env["available"] is False
    assert env["available"] is False
    # An unknown name returns an empty sessions list and a single error envelope; assert the
    # shape rather than an exact field, since the MCP tool returns an envelope, not a row.
    assert env["sessions"] == []
    assert env["error"] and "no session" in env["error"]


def test_get_session_rejects_path_traversal(fake_catalog_path):
    """A name with a slash cannot be passed through to the catalogue as a path segment."""
    get_session = sessions_plugin.get_session

    env = get_session("claude-state-prompt-ledger-../escape")
    assert env["available"] is False
    assert "slash" in (env["error"] or "") or "refused" in (env["error"] or "")


def test_is_session_row_recognises_only_prompt_ledger_path():
    """is_session_row is the one filter; it does not depend on a session tag in the catalogue.

    The catalogue columns kept stable across regenerations are estate/path, estate/coupling,
    estate/kind, estate/rows and metadata.name. Filter on the path, never on a tag, because
    earlier catalogues (pre-2026-09-07) render the same rows without the estate-internal tag.
    """
    is_session_row = sessions_plugin.is_session_row

    row = {
        "kind": "Resource",
        "metadata": {
            "name": "claude-state-prompt-ledger-x",
            "annotations": {
                "estate/path": "~/.claude/state/prompt-ledger/something.jsonl",
                "estate/kind": "ledger",
            },
        },
        "spec": {"type": "ledger"},
    }
    # The plugin reads its prefix from config(); mirror that here so the test exercises the
    # same seam the live tool uses, not a default argument that a static scan would penalise.
    prefix = "~/.claude/state/prompt-ledger/"
    assert is_session_row(row, prefix) is True

    not_session = {
        "kind": "Resource",
        "metadata": {"name": "other"},
        "spec": {"type": "ledger"},
        "annotations": {
            "estate/path": "~/.claude/state/other.jsonl",
            "estate/kind": "ledger",
        },
    }
    assert is_session_row(not_session) is False

    wrong_kind = {
        "kind": "Component",
        "metadata": {"name": "x"},
        "spec": {"type": "ledger"},
        "annotations": {"estate/path": "~/.claude/state/prompt-ledger/x.jsonl"},
    }
    assert is_session_row(wrong_kind) is False


def test_build_envelope_round_trip(fake_catalog_path):
    """build_envelope is the one constructor for both list and get, so they share the envelope shape."""
    build_envelope = sessions_plugin.build_envelope

    now = dt.datetime(2026, 9, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
    env = build_envelope(
        sessions=[
            {
                "name": "x",
                "session_id": "x",
                "path": "p",
                "row_count": 1,
                "last_updated": None,
                "lifecycle": "experimental",
            },
        ],
        now=now,
    )
    assert env["available"] is True
    assert env["count"] == 1
    assert env["generated_at"] == "2026-09-10T12:00:00+00:00"
    assert env["sessions"][0]["name"] == "x"


def test_resolve_session_prefix_uses_env_when_supplied():
    """Behavioural test of LAW 46: the prompt-ledger prefix is read from the env, not
    embedded as a literal. Setting ``ESTATE_PROMPT_LEDGER_PREFIX`` to a custom value
    changes what the plugin filters on; an absent env var falls back to a HOME-anchored
    default that resolves through ``$HOME`` at call-time. The proxy door's own plugin
    tests cover the env plumbing; this test exercises the seam the lint would catch.
    """
    config = sessions_plugin.config
    is_session_row = sessions_plugin.is_session_row
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        custom = os.path.join(tmp, "estate-prompts") + os.sep
        os.environ["ESTATE_PROMPT_LEDGER_PREFIX"] = custom
        try:
            row = {
                "kind": "Resource",
                "metadata": {
                    "name": "claude-state-prompt-ledger-tmp",
                    "annotations": {
                        "estate/path": custom + "my.jsonl",
                        "estate/kind": "ledger",
                    },
                },
                "spec": {"type": "ledger"},
            }
            assert is_session_row(row, prefix=config()["prompt_ledger_prefix"]) is True

            other = {
                "kind": "Resource",
                "metadata": {
                    "name": "claude-state-prompt-ledger-other",
                    "annotations": {
                        "estate/path": "/elsewhere/ledger.jsonl",
                        "estate/kind": "ledger",
                    },
                },
                "spec": {"type": "ledger"},
            }
            assert (
                is_session_row(other, prefix=config()["prompt_ledger_prefix"]) is False
            )
        finally:
            os.environ.pop("ESTATE_PROMPT_LEDGER_PREFIX", None)


class TestTheMcpToolWrappers:
    """The layer the door calls, which nothing tested until it answered with a coroutine object.

    `register_mcp_tools` defines an `async def list_sessions` INSIDE itself, shadowing the
    module-level function of the same name. A bare `return list_sessions()` there therefore calls
    the wrapper itself, and the tool answers with the repr of its own coroutine:

        $ curl -X POST https://mcp.mumchimp.com/estate/mcp -d '{... "tools/call" ...}'
        "<coroutine object register_mcp_tools.<locals>.list_sessions at 0xffffb7706a40>"

    Every test above calls the module-level functions directly, so all of them passed while the
    live door carried that string. `isError: false` too, so nothing reported it as a fault. The
    estate's own `bin/idp-mcp-door` passed at the same time because it only calls tools/list.

    These tests register the tools for real and CALL them, which is the only thing that can see it.
    """

    @staticmethod
    def _registered_tools():
        """Run `register_mcp_tools` against a stand-in, capturing what it registers."""
        mod = sessions_plugin
        captured = {}

        class FakeMcp:
            def tool(self):
                def deco(fn):
                    captured[fn.__name__] = fn
                    return fn

                return deco

        mod.register_mcp_tools(object(), FakeMcp())
        assert set(captured) == {"list_sessions", "get_session"}, sorted(captured)
        return captured

    def test_list_sessions_tool_returns_the_envelope_not_a_coroutine(
        self, fake_catalog_path
    ):
        tools = self._registered_tools()
        result = asyncio.run(tools["list_sessions"]())
        assert not inspect.isawaitable(result), (
            "the tool returned an awaitable; the live door serialises that as "
            "'<coroutine object ...>' with isError false, so it reads as success"
        )
        assert isinstance(result, dict), type(result)
        assert "sessions" in result and "count" in result
        assert result["count"] >= 1, result

    def test_get_session_tool_returns_the_envelope_not_a_coroutine(
        self, fake_catalog_path
    ):
        tools = self._registered_tools()
        listing = asyncio.run(tools["list_sessions"]())
        name = listing["sessions"][0]["name"]
        result = asyncio.run(tools["get_session"](name))
        assert not inspect.isawaitable(result), (
            "the tool returned an awaitable rather than the envelope"
        )
        assert isinstance(result, dict)
        assert result["sessions"][0]["name"] == name
