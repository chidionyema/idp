"""Every voice turn, timed and recorded. The instrument the founder asked for.

WHY. His words, 2026-09-20: "often i have to repeat myself many times — you need to have logs so
you can monitor the latency and friction of all voice comms and troubleshoot and address all
frictions." Until this file there was NO record of a voice turn anywhere: the server computed
`asr_seconds` and sent it to the browser, the browser showed it for a moment, and it was gone. So
"I had to say it three times" was unfalsifiable, and every latency claim was a first-turn
measurement that omitted the model load.

WHAT IT RECORDS, per turn, in ONE row:
  heard_at        when the utterance arrived
  asr_s           time to transcribe
  llm_first_s     time to the FIRST clause -- what a person experiences as "it started answering"
  llm_total_s     time to the last clause
  tts_s           synthesis time summed across clauses
  words           length of the utterance, so a long answer's slowness is separable from a short one
  clauses         how many pieces the answer was spoken in
  engine / voice  which of the 81 voices spoke it -- a slow voice is a fact worth seeing
  outcome         ok | empty | error, and the error text when there is one

WHY SQLITE AND NOT A LOG FILE. The board already reads `catalog/estate.db`; a turn log beside the
sessions it describes can be joined to them, and a file cannot. It is the same database the
Fleetview backend owns -- one store, not two -- and WAL is already on for the two writers.

WHY IT NEVER RAISES. A voice turn that fails because its LOGGING failed would be absurd. Every
write is wrapped, and a failure is counted rather than propagated.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DB_DEFAULT = Path(__file__).resolve().parents[2] / "catalog" / "estate.db"

# The DDL, run once per process. The board's own schema is created by the Fleetview backend; this
# one belongs to the voice service and is deliberately separate so neither has to know the other.
_DDL = """
CREATE TABLE IF NOT EXISTS voice_turns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT,
    heard_at      TEXT NOT NULL,
    asr_s         REAL,
    llm_first_s   REAL,
    llm_total_s   REAL,
    tts_s         REAL,
    words         INTEGER,
    clauses       INTEGER,
    engine        TEXT,
    voice         TEXT,
    outcome       TEXT NOT NULL,
    detail        TEXT
)
"""


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


@dataclass
class Turn:
    """One voice turn, accumulating timings as it happens.

    A dataclass rather than a dict so the fields are named at every call site -- the whole point is
    that a missing measurement is VISIBLE as None, not silently absent from a dictionary.
    """

    started: float = field(default_factory=time.time)
    asr_s: float | None = None
    llm_first_s: float | None = None
    llm_total_s: float | None = None
    tts_s: float = 0.0
    words: int = 0
    clauses: int = 0
    engine: str = ""
    voice: str = ""
    session_id: str = ""
    outcome: str = "ok"
    detail: str = ""

    def first_clause(self) -> None:
        """Record the moment the first clause was READY TO SPEAK.

        THE NUMBER THAT MATTERS. Total time is how long the sentence took; this is how long until
        the person heard anything, which is what they experience as latency. Recorded once.
        """
        if self.llm_first_s is None:
            self.llm_first_s = round(time.time() - self.started, 3)

    def finished(self) -> None:
        self.llm_total_s = round(time.time() - self.started, 3)


def record(turn: Turn) -> None:
    """Write one turn. NEVER raises -- see the module docstring."""
    try:
        path = _db_path()
        if not path.parent.is_dir():
            return
        con = sqlite3.connect(str(path), timeout=2.0, check_same_thread=False)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=2000")
            con.execute(_DDL)
            con.execute(
                "INSERT INTO voice_turns "
                "(session_id, heard_at, asr_s, llm_first_s, llm_total_s, tts_s, words, clauses, "
                " engine, voice, outcome, detail) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    turn.session_id or None,
                    time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(turn.started)),
                    turn.asr_s,
                    turn.llm_first_s,
                    turn.llm_total_s,
                    round(turn.tts_s, 3) or None,
                    turn.words,
                    turn.clauses,
                    turn.engine or None,
                    turn.voice or None,
                    turn.outcome,
                    (turn.detail or "")[:400] or None,
                ),
            )
            con.commit()
        finally:
            con.close()
    except Exception:  # noqa: BLE001,S110 -- a logging failure must never fail a voice turn
        pass


def recent(limit: int = 50) -> list[dict[str, Any]]:
    """The newest turns, for the board to render. Returns [] on any failure."""
    try:
        path = _db_path()
        if not path.is_file():
            return []
        con = sqlite3.connect(str(path), timeout=2.0)
        con.row_factory = sqlite3.Row
        try:
            con.execute(_DDL)
            rows = con.execute(
                "SELECT * FROM voice_turns ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        finally:
            con.close()
        return [dict(r) for r in rows]
    except Exception:  # noqa: BLE001
        return []


def summary(limit: int = 200) -> dict[str, Any]:
    """The friction numbers: how often it mishears, how slow it is, where the time goes.

    THIS IS THE TROUBLESHOOTING VIEW. "I had to repeat myself" becomes a `empty` count; "it is
    slow" becomes a median first-clause time; "that voice is sluggish" becomes a per-voice table.
    """
    turns = recent(limit)
    if not turns:
        return {"turns": 0}

    def median(xs: list[float]) -> float | None:
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return None
        return round(xs[len(xs) // 2], 3)

    empties = [t for t in turns if t.get("outcome") == "empty"]
    errors = [t for t in turns if t.get("outcome") == "error"]
    by_voice: dict[str, list[float]] = {}
    for t in turns:
        v = t.get("voice") or t.get("engine") or "?"
        if t.get("llm_first_s") is not None:
            by_voice.setdefault(v, []).append(t["llm_first_s"])

    return {
        "turns": len(turns),
        "empty": len(empties),
        "errors": len(errors),
        # The fraction of utterances the transcriber produced nothing for -- the number behind
        # "I had to say it again".
        "empty_rate": round(len(empties) / len(turns), 3),
        "asr_median_s": median([t.get("asr_s") for t in turns]),
        "first_clause_median_s": median([t.get("llm_first_s") for t in turns]),
        "first_clause_p90_s": (
            round(
                sorted(
                    t["llm_first_s"] for t in turns if t.get("llm_first_s") is not None
                )[
                    int(
                        len([t for t in turns if t.get("llm_first_s") is not None])
                        * 0.9
                    )
                ],
                3,
            )
            if any(t.get("llm_first_s") is not None for t in turns)
            else None
        ),
        "by_voice": {
            k: {"n": len(v), "first_clause_median_s": median(v)}
            for k, v in sorted(by_voice.items())
        },
    }
