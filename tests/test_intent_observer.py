"""The Observer: a spoken request becomes a tracked contract, in the estate's own database.

WHY THESE TESTS EXIST, and what they would have caught. The first version of this feature was
specified as a script that read Server-Sent Events from `http://127.0.0.1:8770/stream`, inserted
into `fleetview_signals` with four columns, and reported latency as `latency_ms`. Every one of those
is false against the code that exists:

  * `sovereign/voice/server.py` serves the ingress as a WebSocket at `/voice/stream`, not SSE. An
    SSE client gets a 404, and the failure looks like "the voice ingress is down".
  * `fleetview_signals.kind`, `.by`, `.ok` and `.created_at` are all NOT NULL. The four-column
    insert raises `IntegrityError` on the first real utterance.
  * the transcript frame carries `asr_seconds`, and the latency is already recorded in
    `voice_turns` by `sovereign/voice/turnlog.py` -- so a `latency_ms` column would be the second
    copy of a number that already has an owner.

These tests drive the module's own functions against a real SQLite file, so they fail for the same
reasons the running system would. None of them touches a network or a model.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OBSERVER = REPO / "platform" / "intent" / "observer.py"


def _load_observer(monkeypatch, tmp_path: Path):
    """The module, pointed at a throwaway database.

    `ESTATE_DB` is set BEFORE the load because `_db_path()` reads the environment at call time --
    and setting it is also the check that the variable the running backend honours is the one this
    module honours, so an Observer and a backend cannot silently address different files.
    """
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.setenv("LITELLM_OBSERVER_MODEL", "observer-test-model")
    spec = importlib.util.spec_from_file_location("observer_under_test", OBSERVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["observer_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_migration_is_idempotent_and_creates_the_contract_table(monkeypatch, tmp_path):
    """Running it twice must not raise. The boot path runs on every connection."""
    mod = _load_observer(monkeypatch, tmp_path)
    con = mod._connect()
    mod._migrate(con)
    mod._migrate(con)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(action_contracts)")}
    assert {"contract_id", "bdd_json", "status", "voice_turn_id"} <= cols
    con.close()


def test_an_addressed_utterance_becomes_a_contract_with_a_real_signal_row(monkeypatch, tmp_path):
    """The load-bearing path: address -> synthesise -> commit.

    The signal insert is asserted in full because a partial insert is the defect this test exists
    for: `kind`, `by`, `ok` and `created_at` are NOT NULL, so anything less raises at runtime.
    """
    mod = _load_observer(monkeypatch, tmp_path)
    con = mod._connect()
    mod._migrate(con)

    bdd = mod.normalise(
        json.dumps(
            {
                "feature": "API resilience monitoring",
                "given": "the swarm is querying an external API",
                "when": "latency exceeds 500ms or a 5XX is returned",
                "then": "requests route to the fallback proxy and the founder is told by voice",
                "agents_required": 3,
            }
        )
    )
    contract_id = mod.commit(
        con,
        command="check the external APIs and build a fallback",
        transcript="agents check the external APIs and build a fallback",
        bdd=bdd,
        trigger="agents",
        session_id="s-1",
        source_surface="voice",
        asr_seconds=0.42,
        model="observer-test-model",
    )
    assert contract_id.startswith("aac_")

    row = con.execute(
        "SELECT * FROM action_contracts WHERE contract_id = ?", (contract_id,)
    ).fetchone()
    assert row["status"] == "PENDING"
    assert row["address_phrase"] == "agents"
    assert json.loads(row["bdd_json"])["agents_required"] == 3
    # The stored transcript is what was SAID, and the contract is what was ASKED FOR -- the
    # distinction the spec's section 5 needs in order to prove the agent understood.
    assert row["raw_transcript"].startswith("agents ")
    assert "agents " not in row["bdd_json"]

    signal = con.execute(
        "SELECT * FROM fleetview_signals WHERE kind = 'contract'", ()
    ).fetchall()
    assert len(signal) == 1
    assert signal[0]["ok"] == 1
    assert signal[0]["runtime"] == "observer"
    assert contract_id in signal[0]["text"]
    con.close()


def test_an_unaddressed_utterance_is_recorded_and_never_becomes_a_contract(monkeypatch, tmp_path):
    """The negative case, which is the whole point of the address phrase.

    A remark ABOUT the fleet must not fire a contract; but it must still be recorded, or the
    founder is firing into a black box and cannot see what was misheard.
    """
    mod = _load_observer(monkeypatch, tmp_path)
    con = mod._connect()
    mod._migrate(con)

    assert mod.address("the agents are all down again", "agents") is None
    mod._record_transcript_signal(
        con, session_id="s-1", transcript="the agents are all down again"
    )

    assert con.execute("SELECT COUNT(*) c FROM action_contracts").fetchone()["c"] == 0
    kinds = {r["kind"] for r in con.execute("SELECT kind FROM fleetview_signals")}
    assert kinds == {"transcript"}
    con.close()


@pytest.mark.parametrize(
    "utterance,expected",
    [
        ("agents, research competitor pricing", "research competitor pricing"),
        ("Agents: research competitor pricing", "research competitor pricing"),
        ("agents", None),
        ("agents   ", None),
        ("my agents are slow, check them", None),
    ],
)
def test_addressing_is_a_prefix_and_the_command_is_stripped(
    monkeypatch, tmp_path, utterance, expected
):
    mod = _load_observer(monkeypatch, tmp_path)
    assert mod.address(utterance, "agents") == expected


def test_a_contract_without_a_model_is_refused_not_defaulted(monkeypatch, tmp_path):
    """AGENTS.md 0.1. A silent default model is how a feature works on one desk and nowhere else."""
    mod = _load_observer(monkeypatch, tmp_path)
    monkeypatch.setenv("LITELLM_OBSERVER_MODEL", "")
    with pytest.raises(mod.Refused) as exc:
        mod._model()
    assert "LITELLM_OBSERVER_MODEL" in str(exc.value)


def test_over_ceiling_agent_counts_are_refused(monkeypatch, tmp_path):
    """The ceiling is real hardware: OKE always-free, 4 A1 instances, 24GB."""
    mod = _load_observer(monkeypatch, tmp_path)
    for n in (0, 6, 40):
        with pytest.raises(mod.Refused):
            mod.normalise(
                {"feature": "f", "given": "g", "when": "w", "then": "t", "agents_required": n}
            )


def test_a_then_that_is_missing_is_refused(monkeypatch, tmp_path):
    """A BDD contract whose outcome cannot be checked is not a contract (AGENTS.md 3)."""
    mod = _load_observer(monkeypatch, tmp_path)
    with pytest.raises(mod.Refused) as exc:
        mod.normalise({"feature": "f", "given": "g", "when": "w", "agents_required": 1})
    assert "then" in str(exc.value)


def test_non_json_model_output_is_refused(monkeypatch, tmp_path):
    """A model that answers in prose must not become a tracked contract."""
    mod = _load_observer(monkeypatch, tmp_path)
    with pytest.raises(mod.Refused):
        mod.normalise("Sure! Here is your contract:")


def test_contracts_for_reports_a_broken_database_rather_than_an_empty_list(
    monkeypatch, tmp_path
):
    """The distinction the HUD depends on: quiet fleet vs broken database.

    THE FILE IS CORRUPT, NOT THE TABLE DROPPED. An earlier version of this test dropped
    `action_contracts` and expected a raise -- but `contracts_for` runs the migration first, so it
    recreated the table and returned `[]`, which is CORRECT and means the test asserted the wrong
    thing. A dropped table is a schema that has not been migrated yet; a corrupt file is a database
    that cannot be read, and only the second is the failure the envelope must report.

    An implementation that swallowed this would return `[]`, and the board would show a calm, empty
    fleet while the database was unreadable (AGENTS.md section 8).
    """
    mod = _load_observer(monkeypatch, tmp_path)
    db = tmp_path / "estate.db"
    db.write_bytes(b"this is not a sqlite database" * 32)

    with pytest.raises(sqlite3.Error):
        mod.contracts_for(10)


def test_contracts_for_returns_the_fields_the_hud_renders(monkeypatch, tmp_path):
    mod = _load_observer(monkeypatch, tmp_path)
    con = mod._connect()
    mod._migrate(con)
    bdd = mod.normalise(
        {"feature": "F", "given": "G", "when": "W", "then": "T", "agents_required": 2}
    )
    mod.commit(
        con,
        command="do the thing",
        transcript="agents do the thing",
        bdd=bdd,
        trigger="agents",
        session_id="s-9",
        source_surface="voice",
        asr_seconds=None,
        model="observer-test-model",
    )
    con.close()

    rows = mod.contracts_for(10)
    assert len(rows) == 1
    assert rows[0]["bdd"]["feature"] == "F"
    assert rows[0]["agents_required"] == 2
    assert rows[0]["surface"] == "voice"
