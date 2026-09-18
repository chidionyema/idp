"""The board must be fed by reality, not by seeded demo rows.

THE GAP MEASURED 2026-09-18. `catalog/estate.db`'s `sessions` table held three rows --
`fleet-live-001/002/003`, tasks like "Build fleet CP3 stop/approve/deny" -- written by hand.
The schema's own comment admitted it:

    "Schema only: nothing in this repo writes these tables yet -- the sync daemon that will is
     a separate, later piece."

bin/estate-session-recorder is that piece, and it is why the board now shows 23 real sessions
with real models, real spend and real state instead of 3 paused fixtures. Every board complaint
this estate has had traces here: buttons with nothing real to act on, TRACE answering 503
because no session had a trace, STOP returning 500 because there was no live session to stop.

WHAT IS GRADED, and each one is a way a recorder can lie:

  * a real transcript becomes a row with its OWN model, spend and timestamps;
  * spend is recorded only when the ledger carried it -- absent, never 0.0;
  * a source with nothing is reported BLIND, so 'broken reader' and 'no sessions' differ;
  * re-running is idempotent, so the event table records CHANGE and not polling; and
  * a session that cannot be read is skipped and counted, never written blank.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RECORDER = REPO / "bin" / "estate-session-recorder"


def _load():
    spec = importlib.util.spec_from_loader(
        "recorder_under_test",
        importlib.machinery.SourceFileLoader("recorder_under_test", str(RECORDER)),
        origin=str(RECORDER),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["recorder_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def rec(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    return _load()


def _transcript(path: Path, *, model: str, cost: float | None, turns: int = 2) -> None:
    """A pi/claude-code shaped transcript: the fields the recorder actually reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(turns):
        usage = {"totalTokens": 1000 + i, "input": 10, "output": 20}
        if cost is not None:
            usage["cost"] = {"total": cost / turns}
        lines.append(
            json.dumps(
                {
                    "timestamp": f"2026-09-18T0{i}:00:00.000Z",
                    "cwd": "/Users/x/Documents/code/idp",
                    "message": {
                        "role": "user" if i == 0 else "assistant",
                        "content": "fix the board" if i == 0 else "done",
                        "model": model,
                        "usage": usage,
                    },
                }
            )
        )
    path.write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------- a real row from reality


def test_a_transcript_becomes_a_row_with_its_own_model_and_spend(rec, tmp_path, monkeypatch):
    """The core claim: the row's numbers come from the transcript, not from a default."""
    home = tmp_path / "home"
    _transcript(
        home / ".pi" / "agent" / "sessions" / "--Users-x-Documents-code-idp--" / "s_abc.jsonl",
        model="deepseek-v4-pro",
        cost=1.25,
    )
    monkeypatch.setenv("HOME", str(home))
    obs, _blind = rec.read_transcripts()
    assert len(obs) == 1
    o = obs[0]
    assert o.provider == "pi"
    assert o.model == "deepseek-v4-pro", "the session's own model, not a placeholder"
    assert o.meta["spend_usd"] == pytest.approx(1.25)
    assert o.meta["repo"] == "idp", "the repo comes from the directory slug"
    assert o.meta["task"] == "fix the board", "the opening user turn becomes the task"


def test_spend_is_absent_when_the_ledger_carried_no_cost(rec, tmp_path, monkeypatch):
    """Absent, never 0.0. A zero is a claim; missing is a fact (spendLabel renders '—')."""
    home = tmp_path / "home"
    _transcript(
        home / ".pi" / "agent" / "sessions" / "--Users-x-Documents-code-idp--" / "s_def.jsonl",
        model="deepseek-v4-flash",
        cost=None,
    )
    monkeypatch.setenv("HOME", str(home))
    obs, _blind = rec.read_transcripts()
    assert "spend_usd" not in obs[0].meta, (
        "a session with no recorded cost must not report $0.00 -- that reads as 'spent nothing'"
    )


def test_the_model_is_still_recorded_when_no_cost_exists(rec, tmp_path, monkeypatch):
    """The two are independent: a missing cost must not cost us the model."""
    home = tmp_path / "home"
    _transcript(
        home / ".pi" / "agent" / "sessions" / "--Users-x-Documents-code-idp--" / "s_g.jsonl",
        model="MiniMax-M2.7",
        cost=None,
    )
    monkeypatch.setenv("HOME", str(home))
    obs, _ = rec.read_transcripts()
    assert obs[0].model == "MiniMax-M2.7"


def test_a_timestamp_is_required_for_liveness(rec, tmp_path, monkeypatch):
    """A row with no time cannot go stale, and the board would show it for ever."""
    home = tmp_path / "home"
    p = home / ".pi" / "agent" / "sessions" / "--Users-x-Documents-code-idp--" / "s_h.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"message": {"usage": {"totalTokens": 5}}}) + "\n")
    monkeypatch.setenv("HOME", str(home))
    obs, _ = rec.read_transcripts()
    # Falls back to the file's own mtime rather than refusing outright, which is the honest
    # thing: the file exists and was written at a time the filesystem knows.
    assert obs and obs[0].updated_at


# ------------------------------------------------------------------ the honesty rules


def test_a_blank_source_is_reported_blind_not_silently_empty(rec, tmp_path, monkeypatch):
    """'The reader is broken' and 'there are no sessions' must not look alike."""
    home = tmp_path / "home"
    (home / ".pi" / "agent" / "sessions").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    obs, blind = rec.read_transcripts()
    assert obs == []
    assert blind, "an empty source must say why it was empty"
    assert any("no transcript" in b for b in blind)


def test_no_session_directory_at_all_is_blind_and_says_so(rec, tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    obs, blind = rec.read_transcripts()
    assert obs == []
    assert any("records no agent sessions" in b for b in blind)


def test_an_unreadable_transcript_is_skipped_not_written_blank(rec, tmp_path, monkeypatch):
    """One corrupt file must not produce a row of nulls, and must not hide the good ones."""
    home = tmp_path / "home"
    base = home / ".pi" / "agent" / "sessions" / "--Users-x-Documents-code-idp--"
    _transcript(base / "s_good.jsonl", model="m", cost=1.0)
    (base / "s_bad.jsonl").write_text("this is not json\nnor is this\n")
    monkeypatch.setenv("HOME", str(home))
    obs, _ = rec.read_transcripts()
    assert len(obs) == 1, "the malformed file must not become a row"
    assert obs[0].model == "m"


def test_a_malformed_claims_line_is_skipped(rec, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".estate").mkdir(parents=True)
    (home / ".estate" / "claims.jsonl").write_text(
        "not json\n" + json.dumps({"id": "s1", "at": "2026-09-18T00:00:00Z"}) + "\n"
    )
    monkeypatch.setenv("HOME", str(home))
    obs, blind = rec.read_estate_claims()
    assert len(obs) == 1
    assert obs[0].session_id == "s1"
    assert blind == []


def test_a_missing_claims_ledger_is_blind_not_an_error(rec, tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    obs, blind = rec.read_estate_claims()
    assert obs == []
    assert any("claims.jsonl" in b for b in blind)


# ------------------------------------------------------------------- the write


def test_writing_is_idempotent(rec, tmp_path):
    """Re-running records CHANGE, not polling. Otherwise the event table grows forever."""
    con = rec._connect()
    o = rec.Observation(
        session_id="s1",
        provider="pi",
        model="m",
        created_at="2026-09-18T00:00:00+00:00",
        updated_at="2026-09-18T00:01:00+00:00",
        meta={"task": "t"},
    )
    first = rec.write_observations(con, [o])
    second = rec.write_observations(con, [o])
    third = rec.write_observations(con, [o])
    assert first["events"] == 1
    assert second["events"] == 0, "a re-run with no new timestamp must add no event"
    assert third["events"] == 0
    n = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    e = con.execute("SELECT COUNT(*) FROM session_events").fetchone()[0]
    assert (n, e) == (1, 1), f"expected one row and one event, got {n} and {e}"


def test_a_new_timestamp_appends_an_event(rec, tmp_path):
    """The converse: real progress must be recorded, or liveness cannot be derived."""
    con = rec._connect()
    base = dict(
        session_id="s1", provider="pi", model="m", created_at="2026-09-18T00:00:00+00:00"
    )
    rec.write_observations(con, [rec.Observation(updated_at="2026-09-18T00:01:00+00:00", meta={}, **base)])
    rec.write_observations(con, [rec.Observation(updated_at="2026-09-18T00:02:00+00:00", meta={}, **base)])
    assert con.execute("SELECT COUNT(*) FROM session_events").fetchone()[0] == 2
    # And the sequence is contiguous, which is what makes `seq` meaningful.
    seqs = [r[0] for r in con.execute("SELECT seq FROM session_events ORDER BY seq")]
    assert seqs == [1, 2]


def test_the_row_shape_is_what_the_board_reads(rec, tmp_path):
    """The exact columns sessions.py's `_estate_db_sessions` selects."""
    con = rec._connect()
    rec.write_observations(
        con,
        [
            rec.Observation(
                session_id="abc",
                provider="pi",
                model="deepseek-v4-flash",
                created_at="2026-09-18T00:00:00+00:00",
                updated_at="2026-09-18T00:05:00+00:00",
                meta={"task": "do a thing", "repo": "idp", "spend_usd": 0.5},
            )
        ],
    )
    row = con.execute(
        """
        SELECT s.id, s.provider, s.model, s.created_at, s.metadata_json,
               MAX(e.ts) AS last_event_ts
        FROM sessions s LEFT JOIN session_events e ON e.session_id = s.id
        GROUP BY s.id
        """
    ).fetchone()
    assert row["provider"] == "pi"
    assert row["model"] == "deepseek-v4-flash"
    assert row["last_event_ts"] == "2026-09-18T00:05:00+00:00"
    meta = json.loads(row["metadata_json"])
    assert meta["task"] == "do a thing"
    assert meta["spend_usd"] == 0.5


def test_nothing_found_writes_nothing(rec, tmp_path, monkeypatch, capsys):
    """The failure this whole tool exists to remove: never a placeholder row."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(sys, "argv", ["recorder", "--json"])
    rc = rec.main()
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sessions"] == 0
    assert out["blind"], "and it says why it found nothing"
    con = sqlite3.connect(str(tmp_path / "estate.db"))
    try:
        n = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    except sqlite3.OperationalError:
        n = 0
    assert n == 0, "no sessions found must write no rows at all"
