"""FleetView CP7: src/ledger_tail.py unit tests.

No live filesystem state needed — every test that touches disk uses tmp_path.
Follows the pattern of test_fleetview_signals.py and test_fleetview_check_receipts.py:
load the module by path, inject stubs/fixtures, grade the contract.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
LEDGER_TAIL_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "ledger_tail.py"
)
ROUTES_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "routes.py"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    return _load(LEDGER_TAIL_MODULE, "fleetview_ledger_tail_under_test")


def _write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


# ---------------------------------------------------------------------------
# session_id splitting
# ---------------------------------------------------------------------------


def test_raw_session_id_strips_repo_prefix(ledger):
    assert ledger._raw_session_id("myrepo:abc-123") == "abc-123"


def test_raw_session_id_no_colon_returns_as_is(ledger):
    assert ledger._raw_session_id("abc-123") == "abc-123"


def test_raw_session_id_splits_on_last_colon(ledger):
    assert ledger._raw_session_id("a:b:c") == "c"


# ---------------------------------------------------------------------------
# Missing directory / empty state
# ---------------------------------------------------------------------------


def test_missing_ledger_dir_returns_empty_list(ledger, monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path / "does-not-exist"))
    result = ledger.ledger_tail("repo:uuid-1")
    assert result == []


def test_blank_session_id_returns_empty_list(ledger):
    assert ledger.ledger_tail("") == []


# ---------------------------------------------------------------------------
# Basic row extraction
# ---------------------------------------------------------------------------


def test_rows_matching_uuid_are_returned(ledger, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    rows = [
        {
            "session": "uuid-abc",
            "ts": "2026-09-09T10:00:00Z",
            "source": "user",
            "text": "hi",
        },
        {
            "session": "other-uuid",
            "ts": "2026-09-09T10:00:01Z",
            "source": "user",
            "text": "other",
        },
    ]
    _write_rows(tmp_path / "project.jsonl", rows)
    result = ledger.ledger_tail("project:uuid-abc")
    assert len(result) == 1
    assert result[0]["source"] == "user"
    assert result[0]["text"] == "hi"


def test_text_is_trimmed_to_500_chars(ledger, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    long_text = "x" * 1000
    rows = [
        {
            "session": "u1",
            "ts": "2026-09-09T10:00:00Z",
            "source": "assistant",
            "text": long_text,
        }
    ]
    _write_rows(tmp_path / "p.jsonl", rows)
    result = ledger.ledger_tail("repo:u1")
    assert len(result[0]["text"]) == 500


def test_last_n_rows_returned(ledger, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    rows = [
        {
            "session": "uid",
            "ts": f"2026-09-09T10:00:0{i}Z",
            "source": "user",
            "text": f"msg{i}",
        }
        for i in range(10)
    ]
    _write_rows(tmp_path / "p.jsonl", rows)
    result = ledger.ledger_tail("repo:uid", n=3)
    assert len(result) == 3
    assert result[-1]["text"] == "msg9"


def test_rows_from_multiple_files_are_combined(ledger, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    _write_rows(
        tmp_path / "a.jsonl",
        [
            {
                "session": "uid",
                "ts": "2026-09-09T10:00:00Z",
                "source": "user",
                "text": "from-a",
            },
        ],
    )
    _write_rows(
        tmp_path / "b.jsonl",
        [
            {
                "session": "uid",
                "ts": "2026-09-09T10:00:01Z",
                "source": "assistant",
                "text": "from-b",
            },
        ],
    )
    result = ledger.ledger_tail("repo:uid", n=20)
    texts = {r["text"] for r in result}
    assert "from-a" in texts
    assert "from-b" in texts


def test_malformed_lines_are_skipped(ledger, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    with (tmp_path / "p.jsonl").open("w") as fh:
        fh.write("not-json\n")
        fh.write(
            json.dumps(
                {
                    "session": "uid",
                    "ts": "2026-09-09T10:00:00Z",
                    "source": "user",
                    "text": "ok",
                }
            )
            + "\n"
        )
    result = ledger.ledger_tail("repo:uid")
    assert len(result) == 1
    assert result[0]["text"] == "ok"


# ---------------------------------------------------------------------------
# routes.py envelope
# ---------------------------------------------------------------------------


def test_ledger_route_always_returns_200(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    routes = _load(ROUTES_MODULE, "fleetview_routes_ledger_test")
    body, status = routes.ledger_tail_envelope("repo:no-such-session")
    assert status == 200
    assert body["rows"] == []


def test_ledger_route_returns_rows_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path))
    rows = [
        {
            "session": "sid",
            "ts": "2026-09-09T10:00:00Z",
            "source": "user",
            "text": "hello",
        }
    ]
    _write_rows(tmp_path / "proj.jsonl", rows)
    routes = _load(ROUTES_MODULE, "fleetview_routes_ledger_rows_test")
    body, status = routes.ledger_tail_envelope("proj:sid")
    assert status == 200
    assert len(body["rows"]) == 1
    assert body["rows"][0]["text"] == "hello"
