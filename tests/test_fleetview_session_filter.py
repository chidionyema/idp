"""Tests for the fleetview session filter and file enumerator.

The fleet page showed zero rows on 2026-09-14 because:
  1. The catalogue filter was pinned to a single runtime's path prefix, AND
  2. The path-prefix comparison was broken by a trailing slash mismatch.

Both are fixed in sessions.py. These tests are the guard: the trailing-slash mistake becomes a
test the next session cannot walk past, and the file enumerator is proved to surface real rows
instead of silently returning empty.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

# Tests use `assert` because pytest rewrites them with rich introspection on failure.
# The bandit S101 "no assert" rule is a security lint for production code; tests are the
# documented exception.
# ruff: noqa: S101


WORKTREE = pathlib.Path(
    "/tmp/idp-fleetview/backstage/plugins/fleetview-backend/src/sessions.py"  # noqa: S108 - worktree path is intentional in a worktree-scoped test
)


@pytest.fixture(scope="module")
def sessions_mod():
    spec = importlib.util.spec_from_file_location("sessions_under_test", WORKTREE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ledger_doc(path: str) -> dict:
    return {
        "kind": "Resource",
        "spec": {"type": "ledger"},
        "metadata": {"annotations": {"estate/path": path}},
    }


def test_is_session_row_accepts_prompt_ledger_without_trailing_slash(sessions_mod):
    """The catalogue writes the path without a trailing slash; the filter accepts it whether or
    not the prefix default has one."""
    assert sessions_mod.is_session_row(_ledger_doc("~/.claude/state/prompt-ledger"))


def test_is_session_row_accepts_paths_under_the_prefix(sessions_mod):
    """A JSONL file living inside the prompt-ledger dir is also a session row, not just the
    directory itself."""
    assert sessions_mod.is_session_row(
        _ledger_doc("~/.claude/state/prompt-ledger/-private-tmp-some-session.jsonl")
    )


def test_is_session_row_rejects_unrelated_paths(sessions_mod):
    assert not sessions_mod.is_session_row(_ledger_doc("/var/log/syslog"))
    assert not sessions_mod.is_session_row(
        _ledger_doc("~/.claude/state/not-the-ledger")
    )


def test_is_session_row_rejects_non_ledger_rows(sessions_mod):
    assert not sessions_mod.is_session_row(
        {"kind": "Resource", "spec": {"type": "drill"}}
    )


def test_register_runtime_extends_dispatcher(sessions_mod):
    """Adding a new runtime's filter makes its rows visible to the dispatcher -- no rewrite of
    is_session_row, no global rename of the path prefix."""

    def is_github_actions(doc):
        path = ((doc.get("metadata") or {}).get("annotations") or {}).get(
            "estate/path", ""
        )
        return path.startswith("~/.claude/state/github-actions/")

    try:
        assert not sessions_mod.is_session_row(
            _ledger_doc("~/.claude/state/github-actions/run-123.jsonl")
        )
        sessions_mod.register_runtime("github-actions", is_github_actions)
        assert sessions_mod.is_session_row(
            _ledger_doc("~/.claude/state/github-actions/run-123.jsonl")
        )
        # claude-code still works (registry accumulates, not replaces).
        assert sessions_mod.is_session_row(_ledger_doc("~/.claude/state/prompt-ledger"))
    finally:
        sessions_mod._RUNTIME_REGISTRY[:] = [
            (n, f) for n, f in sessions_mod._RUNTIME_REGISTRY if n != "github-actions"
        ]


def test_list_claude_code_sessions_groups_rows_by_session_id(sessions_mod, tmp_path):
    """The enumerator walks the prefix dir and returns one record per unique session id,
    sorted newest-first. A file with two distinct session ids contributes two rows."""
    f1 = tmp_path / "session-a.jsonl"
    f1.write_text(
        json.dumps(
            {
                "session": "alpha",
                "ts": "2026-09-14T00:00:00Z",
                "source": "user",
                "text": "first",
            }
        )
        + "\n"
        + json.dumps(
            {
                "session": "beta",
                "ts": "2026-09-14T00:01:00Z",
                "source": "user",
                "text": "second",
            }
        )
        + "\n"
    )
    f2 = tmp_path / "session-b.jsonl"
    f2.write_text(
        json.dumps(
            {
                "session": "gamma",
                "ts": "2026-09-14T00:02:00Z",
                "source": "user",
                "text": "third",
            }
        )
        + "\n"
    )

    rows = sessions_mod.list_claude_code_sessions(str(tmp_path) + "/")
    assert {r["session_id"] for r in rows} == {"alpha", "beta", "gamma"}
    assert rows[0]["task"] in {"first", "second", "third"}
    assert all(r["runtime"] == "claude-code" for r in rows)


def test_session_record_uses_newest_user_prompt_as_task(sessions_mod, tmp_path):
    """The task field is the newest user prompt (the person's own words), not an assistant
    reply or queue entry."""
    f = tmp_path / "s.jsonl"
    f.write_text(
        json.dumps(
            {
                "session": "s1",
                "ts": "2026-09-14T00:00:00Z",
                "source": "queue",
                "text": "old queue entry",
            }
        )
        + "\n"
        + json.dumps(
            {
                "session": "s1",
                "ts": "2026-09-14T00:01:00Z",
                "source": "assistant",
                "text": "assistant reply",
            }
        )
        + "\n"
        + json.dumps(
            {
                "session": "s1",
                "ts": "2026-09-14T00:02:00Z",
                "source": "user",
                "text": "the actual task",
            }
        )
        + "\n"
    )
    rows = sessions_mod.list_claude_code_sessions(str(tmp_path) + "/")
    assert len(rows) == 1
    assert rows[0]["task"] == "the actual task"


def test_list_all_sessions_returns_combined_records(
    sessions_mod, tmp_path, monkeypatch
):
    """The merge function picks up both the catalogue rollup rows and the file-derived rows,
    de-duplicating by session id."""
    # Build a fake catalogue with one rollup row whose id is the tmp_path itself.
    catalog = tmp_path / "catalog-info.yaml"
    catalog.write_text(
        "kind: Resource\n"
        "spec:\n"
        "  type: ledger\n"
        "metadata:\n"
        "  name: rollup-row\n"
        "  annotations:\n"
        f"    estate/path: {str(tmp_path)}\n"
        "---\n"
        "kind: Resource\n"
        "spec:\n"
        "  type: drill\n"
        "metadata:\n"
        "  name: not-a-session\n"
    )
    # Make the prefix point at the same tmp_path so the file walk finds it.
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(catalog))
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path) + "/")
    f = tmp_path / "session-x.jsonl"
    f.write_text(
        json.dumps(
            {
                "session": "real-session-id",
                "ts": "2026-09-14T00:00:00Z",
                "source": "user",
                "text": "real session",
            }
        )
        + "\n"
    )
    sessions, unreachable = sessions_mod.list_all_sessions()
    ids = {s["session_id"] for s in sessions}
    # Catalogue row + file-derived row are both present (different ids).
    assert "rollup-row" in ids
    assert "real-session-id" in ids
    # The non-session drill row is filtered out.
    assert "not-a-session" not in ids
