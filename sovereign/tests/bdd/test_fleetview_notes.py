"""FleetView notes mailbox: leave a note for a session, any runtime, read later.

No feature file: this is infrastructure behind CP1-4's board, not a new customer-facing
checkpoint, so it is graded as a plain unit suite against `src/notes.py` and `src/routes.py`
directly, the same way `test_fleetview_cp4.py` grades `validate_record` outside any scenario.

Every test points `ESTATE_DB` at a throwaway sqlite file (`tmp_path`) so this suite never reads or
writes the real `catalog/estate.db` -- the module creates its own table there via
`CREATE TABLE IF NOT EXISTS`, additive to whatever else already lives in that file (THE HEADLINE:
extend the one store, never a second one).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
NOTES_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "notes.py"
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
def notes(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate-test.db"))
    return _load(NOTES_MODULE, "fleetview_notes_under_test")


@pytest.fixture()
def routes(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate-test.db"))
    return _load(ROUTES_MODULE, "fleetview_routes_under_test")


def test_a_note_can_be_left_and_read_back(notes):
    written = notes.add_note(
        "sb-1", "sovereign", "check the budget before you retry", "chidi"
    )
    assert written["session_id"] == "sb-1"
    assert written["runtime"] == "sovereign"
    assert written["note"] == "check the budget before you retry"
    assert written["author"] == "chidi"
    assert written["read_at"] is None

    thread = notes.notes_for("sb-1")
    assert [n["note"] for n in thread] == ["check the budget before you retry"]


def test_notes_are_returned_oldest_first(notes):
    notes.add_note("sb-1", "sovereign", "first", "chidi")
    notes.add_note("sb-1", "sovereign", "second", "chidi")
    thread = notes.notes_for("sb-1")
    assert [n["note"] for n in thread] == ["first", "second"]


def test_a_session_with_no_notes_is_an_empty_list_not_an_error(notes):
    assert notes.notes_for("never-seen") == []


def test_the_mailbox_is_not_claude_code_specific(notes):
    # The founder's own correction: "we are model agnostic and this is enterprise wide, not repo
    # wide". A runtime that does not exist yet in RUNTIME_ADAPTERS can still receive a note.
    written = notes.add_note("c-9", "some-future-runtime", "hello", "chidi")
    assert written["runtime"] == "some-future-runtime"
    assert notes.notes_for("c-9", runtime="some-future-runtime")[0]["note"] == "hello"


def test_narrowing_by_runtime_excludes_other_runtimes_on_the_same_session_id(notes):
    notes.add_note("shared-id", "pi", "for pi", "chidi")
    notes.add_note("shared-id", "gemini", "for gemini", "chidi")
    assert [n["note"] for n in notes.notes_for("shared-id", runtime="pi")] == ["for pi"]
    assert [n["note"] for n in notes.notes_for("shared-id")] == ["for pi", "for gemini"]


@pytest.mark.parametrize(
    "field",
    ["session_id", "runtime", "note", "author"],
)
def test_a_blank_required_field_is_rejected(notes, field):
    kwargs = {
        "session_id": "sb-1",
        "runtime": "sovereign",
        "note": "hello",
        "author": "chidi",
    }
    kwargs[field] = "  "
    with pytest.raises(notes.InvalidNote):
        notes.add_note(**kwargs)


def test_an_oversized_note_is_rejected(notes):
    with pytest.raises(notes.InvalidNote):
        notes.add_note("sb-1", "sovereign", "x" * (notes.MAX_NOTE_LENGTH + 1), "chidi")


def test_post_route_writes_and_returns_201(routes):
    body, status = routes.add_note(
        {"session_id": "sb-2", "runtime": "sovereign", "note": "hi", "author": "chidi"}
    )
    assert status == 201
    assert body["note"] == "hi"


def test_post_route_rejects_a_malformed_body_with_400_not_500(routes):
    body, status = routes.add_note({"session_id": "sb-2"})
    assert status == 400
    assert "runtime" in body["error"]


def test_get_route_is_always_200_even_when_empty(routes):
    body, status = routes.notes_envelope("no-such-session")
    assert status == 200
    assert body == {"notes": []}


def test_get_route_after_a_post_sees_the_same_note(routes):
    routes.add_note(
        {
            "session_id": "sb-3",
            "runtime": "claude-code",
            "note": "reroute",
            "author": "chidi",
        }
    )
    body, status = routes.notes_envelope("sb-3")
    assert status == 200
    assert [n["note"] for n in body["notes"]] == ["reroute"]
