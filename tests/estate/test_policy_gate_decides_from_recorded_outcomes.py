"""The executor's policy gate decides from the intent's own recorded outcomes.

ML dept loop A (docs/specs/2026-09-29-machine-learning-dept.md): before a step runs,
estate-execute reads the intent's last-30-day tickets and records allow / hold / refuse in
policy_decisions, and queues one estate.agent gate event on the outbox. Shadow never blocks;
enforce refuses with exit 3. Each case runs the real script against a throwaway HOME.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

EXEC = Path(__file__).resolve().parents[2] / "platform/estate/bin/estate-execute"
INTENT = "name: probe\ndescription: t\ntools: [true]\nsteps:\n  - cmd: 'true'\n"


def _seed(home: Path, intent: str, ok: int, not_ok: int) -> None:
    (home / ".estate" / "intents").mkdir(parents=True)
    (home / ".estate" / "intents" / f"{intent}.yaml").write_text(INTENT)
    conn = sqlite3.connect(str(home / ".estate" / "estate.db"))
    conn.execute(
        "CREATE TABLE intent_tickets (id TEXT PRIMARY KEY, intent TEXT NOT NULL, "
        "harness TEXT NOT NULL, goal TEXT, started_at TEXT NOT NULL, completed_at TEXT, "
        "status TEXT NOT NULL DEFAULT 'running', steps_run INTEGER NOT NULL DEFAULT 0, "
        "steps_failed INTEGER NOT NULL DEFAULT 0, cost_usd REAL DEFAULT 0, error TEXT)"
    )
    started = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rows = [(f"ok{i}", "ok") for i in range(ok)] + [
        (f"bad{i}", "broken") for i in range(not_ok)
    ]
    conn.executemany(
        "INSERT INTO intent_tickets (id,intent,harness,started_at,status) VALUES (?,?,?,?,?)",
        [(rid, intent, "direct", started, st) for rid, st in rows],
    )
    conn.commit()
    conn.close()


def _run(home: Path, intent: str, mode: str | None) -> subprocess.CompletedProcess:
    # HOME moves to the throwaway estate; the interpreter's user site (where pyyaml lives on
    # a laptop) must not move with it.
    user_base = subprocess.run(
        ["/usr/bin/env", "python3", "-c", "import site; print(site.USER_BASE)"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    env = {**os.environ, "HOME": str(home), "PYTHONUSERBASE": user_base}
    env.pop("ESTATE_POLICY", None)
    if mode:
        env["ESTATE_POLICY"] = mode
    # The script's own shebang (`/usr/bin/env python3`), as launchd and the MCP door run it;
    # pytest's interpreter may not carry pyyaml.
    return subprocess.run(
        [str(EXEC), intent], capture_output=True, text=True, env=env, timeout=60
    )


def _decisions(home: Path) -> list[tuple]:
    conn = sqlite3.connect(str(home / ".estate" / "estate.db"))
    return conn.execute(
        "SELECT intent, decision, mode, n, not_ok FROM policy_decisions"
    ).fetchall()


def test_enforce_refuses_an_intent_that_keeps_failing(tmp_path: Path) -> None:
    _seed(tmp_path, "probe", ok=1, not_ok=9)
    r = _run(tmp_path, "probe", "enforce")
    assert r.returncode == 3, r.stderr
    assert "policy refused probe" in r.stderr
    assert _decisions(tmp_path) == [("probe", "refuse", "enforce", 10, 9)]


def test_enforce_passes_an_intent_that_keeps_succeeding(tmp_path: Path) -> None:
    _seed(tmp_path, "probe", ok=9, not_ok=1)
    r = _run(tmp_path, "probe", "enforce")
    assert r.returncode == 0, r.stderr
    assert _decisions(tmp_path) == [("probe", "allow", "enforce", 10, 1)]


def test_shadow_is_the_default_and_never_blocks(tmp_path: Path) -> None:
    _seed(tmp_path, "probe", ok=1, not_ok=9)
    r = _run(tmp_path, "probe", None)
    assert r.returncode == 0, r.stderr
    assert "would refuse probe" in r.stderr
    assert _decisions(tmp_path) == [("probe", "refuse", "shadow", 10, 9)]


def test_too_few_runs_is_allow_not_a_guess(tmp_path: Path) -> None:
    _seed(tmp_path, "probe", ok=0, not_ok=4)
    r = _run(tmp_path, "probe", "enforce")
    assert r.returncode == 0, r.stderr
    assert _decisions(tmp_path)[0][1] == "allow"


def test_every_decision_is_a_gate_event_on_the_outbox(tmp_path: Path) -> None:
    _seed(tmp_path, "probe", ok=1, not_ok=9)
    _run(tmp_path, "probe", None)
    ob = sqlite3.connect(str(tmp_path / ".estate" / "outbox.db"))
    kind, payload = ob.execute("SELECT kind, payload FROM outbox").fetchone()
    assert kind == "gate"
    assert '"verdict": "refuse"' in payload and '"estate-policy:shadow"' in payload


@pytest.mark.parametrize("mode", ["off"])
def test_off_records_nothing(tmp_path: Path, mode: str) -> None:
    _seed(tmp_path, "probe", ok=1, not_ok=9)
    r = _run(tmp_path, "probe", mode)
    assert r.returncode == 0, r.stderr
    assert _decisions(tmp_path) == []
