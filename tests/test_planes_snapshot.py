"""CP5 planes-snapshot tests: three rings, each reading the right table."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "bin" / "estate-planes-snapshot"


def _load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


snap = _load(SNAP, "estate_planes_snapshot")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    con = sqlite3.connect(str(tmp_path / "estate.db"))
    # Schema for deploy_journeys so the env-path lookup doesn't crash first.
    con.execute(
        "CREATE TABLE deploy_journeys (sha TEXT PRIMARY KEY,"
        " branch TEXT, pr_number INTEGER, title TEXT, state TEXT,"
        " started_at TIMESTAMP, merged_at TIMESTAMP,"
        " metadata_json TEXT)"
    )
    con.execute(
        "CREATE TABLE jev_decisions (id TEXT, repo TEXT, layer TEXT,"
        " decision_id TEXT, question TEXT, answer TEXT,"
        " confidence REAL, probabilities TEXT, escalated INTEGER,"
        " latency_ms REAL, created_at TEXT)"
    )
    con.execute(
        "CREATE TABLE assets (declared_in TEXT, id TEXT, name TEXT,"
        " plane TEXT, type TEXT, verdict TEXT, why TEXT,"
        " licence_file TEXT)"
    )
    con.executemany(
        "INSERT INTO jev_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "j1",
                "idp",
                "llm",
                "d1",
                "q1?",
                "a1",
                0.9,
                "{}",
                0,
                12.0,
                "2026-09-23T08:00:00Z",
            ),
            (
                "j2",
                "idp",
                "routing",
                "d2",
                "q2?",
                "a2",
                0.7,
                "{}",
                1,
                8.0,
                "2026-09-23T08:01:00Z",
            ),
        ],
    )
    con.executemany(
        "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                "judges.yaml",
                "redteam:1",
                "red-team #1",
                "adversarial",
                "redteam",
                "pass",
                "no payload triggered",
                "LICENSE",
            ),
            (
                "payloads.yaml",
                "payload:1",
                "payload:1",
                "adversarial",
                "payload",
                "fail",
                "triggered",
                "LICENSE",
            ),
            (
                "seals.yaml",
                "seal:1",
                "aevum seal #1",
                "physics",
                "seal",
                "pass",
                "Ed25519 verified",
                "LICENSE",
            ),
            (
                "crystals.yaml",
                "z3:1",
                "Z3 crystal #1",
                "physics",
                "crystal",
                "pass",
                "Z3 sat",
                "LICENSE",
            ),
        ],
    )
    con.commit()
    con.close()
    return tmp_path / "estate.db"


def test_snapshot_blind_when_ledger_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    s = snap.snapshot()
    assert s["available"] is False


def test_snapshot_has_three_rings(db):
    s = snap.snapshot()
    assert s["available"] is True
    assert set(s["rings"].keys()) == {"jev", "judges", "physics"}


def test_jev_ring_reads_jev_decisions(db):
    s = snap.snapshot()
    assert len(s["rings"]["jev"]) == 2
    assert s["rings"]["jev"][0]["id"] in {"j1", "j2"}


def test_judges_ring_reads_only_adversarial_assets(db):
    s = snap.snapshot()
    judges = s["rings"]["judges"]
    assert {j["type"] for j in judges} <= {"redteam", "payload", "judge", "mutation"}


def test_physics_ring_reads_only_physics_assets(db):
    s = snap.snapshot()
    phys = s["rings"]["physics"]
    assert {p["type"] for p in phys} <= {
        "seal",
        "aevum",
        "crystal",
        "z3",
        "attestation",
    }
    assert len(phys) == 2


def test_snapshot_is_byte_identical(db):
    a = snap.snapshot()
    b = snap.snapshot()
    assert a == b


def test_snapshot_does_not_mix_rings(db):
    s = snap.snapshot()
    judge_ids = {j["id"] for j in s["rings"]["judges"]}
    phys_ids = {p["id"] for p in s["rings"]["physics"]}
    assert judge_ids.isdisjoint(phys_ids)
