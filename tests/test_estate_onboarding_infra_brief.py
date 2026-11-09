"""Failing first-turn conditions for cross-estate architecture and memory admission.

The tests call the REAL bin/estate-brief main without any network request.
A green source unit test is not a live fleet adoption receipt.
"""
from __future__ import annotations

import importlib.util
import json
import runpy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "platform/estate/onboarding/pack.py"
MODEL = ROOT / "platform/estate/onboarding/operating_model.json"
BRIEF = ROOT / "bin/estate-brief"
INSTALLER = ROOT / "bin/estate-memory-install"


@pytest.fixture
def pack():
    spec = importlib.util.spec_from_file_location("estate_onboarding_pack_test", PACK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def brief(monkeypatch):
    # Script is evaluated as a module, not executed as a main process.
    ns = runpy.run_path(str(BRIEF))
    monkeypatch.setitem(ns["main"].__globals__, "state_section", lambda: "")
    monkeypatch.setattr(ns["focus"], "live_focus", lambda: [])
    return ns


def test_model_identifies_two_complementary_domains_and_current_infra(pack):
    model, digest = pack.load()
    assert len(digest) == 64
    assert model["systems"]["idp"]["repo"] == "chidionyema/idp"
    assert model["systems"]["genesis"]["repo"] == "chidionyema/argon"
    assert "TARGET NOT PROOF" in model["infrastructure"]["target"]
    assert "E2.1.Micro" in model["infrastructure"]["recovery_candidate"]
    assert model["infrastructure"]["live_verdict"].startswith("UNKNOWN")
    assert model["fleet_policy"]["state"] == "UNVERIFIED_BY_STATIC_PACK"
    text = pack.render()
    assert "Genesis" in text and "IDP:" in text and "GENESIS:" in text
    assert "LIVE HEALTH: UNKNOWN" in text


def test_missing_or_invalid_pack_never_becomes_green(pack, tmp_path):
    file = tmp_path / "model.json"
    file.write_text('{"schema_version": "estate.onboarding.v1"}')
    with pytest.raises(pack.OnboardingUnavailable):
        pack.load(file)
    assert 'status="UNKNOWN"' in pack.render(file)
    file.write_text('{"schema_version":"old"}')
    with pytest.raises(pack.OnboardingUnavailable):
        pack.load(file)


def test_real_installer_copies_pack_and_model_with_brief():
    ns = runpy.run_path(str(INSTALLER))
    files = ns["home_files"]()
    assert "bin/estate-brief" in files
    assert "platform/estate/onboarding/pack.py" in files
    assert "platform/estate/onboarding/operating_model.json" in files
    assert "docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md" in files
    assert "docs/decisions/0048-the-estate-runs-on-one-node-with-an-admission-list.md" in files
    assert "docs/onboarding/estate-idp-genesis-and-infrastructure.md" in files


def test_memory_unavailable_is_explicit_and_refuses_mission_admission(brief, monkeypatch, capsys):
    monkeypatch.setattr(brief["door"], "key", lambda: "")
    rc = brief["main"](["--require-memory"])
    out = capsys.readouterr()
    assert rc == 2
    assert "IDP:" in out.out and "GENESIS:" in out.out
    assert 'state="UNKNOWN"' in out.out
    assert "NO_AUTHENTICATED_MEMORY_CREDENTIAL" in out.out
    assert "CRITICAL_MEMORY_DEPENDENCY" in out.err


def test_memory_down_does_not_kill_safe_read_only_start(brief, monkeypatch, capsys):
    monkeypatch.setattr(brief["door"], "key", lambda: "")
    rc = brief["main"]([])
    out = capsys.readouterr()
    assert rc == 0
    assert "safe-action=\"READ_ONLY_RECOVERY\"" in out.out
    assert 'state="UNKNOWN"' in out.out


def test_actual_memory_brief_does_not_override_missing_architecture(brief, monkeypatch, capsys):
    monkeypatch.setitem(brief["main"].__globals__, "_onboarding_module", lambda: None)
    monkeypatch.setattr(brief["door"], "key", lambda: "test-only")
    monkeypatch.setattr(brief["door"], "call", lambda *args, **kwargs: {"recent": [], "relevant": []})
    rc = brief["main"](["--require-memory"])
    out = capsys.readouterr()
    assert rc == 2
    assert 'privileged-admission="UNVERIFIED"' in out.out


def test_invalid_memory_reply_cannot_authorise_mission(brief, monkeypatch, capsys):
    monkeypatch.setattr(brief["door"], "key", lambda: "test-only")
    monkeypatch.setattr(brief["door"], "call", lambda *args, **kwargs: [])
    rc = brief["main"](["--require-memory"])
    out = capsys.readouterr()
    assert rc == 2
    assert "INVALID_MEMORY_BRIEF" in out.out


def test_live_memory_read_is_only_read_proof(brief, monkeypatch, capsys):
    monkeypatch.setattr(brief["door"], "key", lambda: "test-only")
    monkeypatch.setattr(brief["door"], "call", lambda *args, **kwargs: {"recent": [], "relevant": []})
    rc = brief["main"](["--require-memory"])
    out = capsys.readouterr()
    assert rc == 0
    assert 'state="LIVE_READ_OK"' in out.out
    assert "independent read-write-recall proof still required" in out.out


def test_versioned_model_lists_no_agent_provisioning_rights():
    data = json.loads(MODEL.read_text())
    assert "Agents are governed subjects" in data["authority"]["agents"]
    assert data["session_contract"]["missing_or_conflicting"].startswith("UNKNOWN")
    assert "AGENTS.md" in data["sources"]


def test_stale_or_missing_authoritative_adr_blocks_pack_admission(pack, tmp_path):
    model_file = tmp_path / "platform/estate/onboarding/operating_model.json"
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(MODEL.read_bytes())
    meta = json.loads(MODEL.read_text())
    for source in meta["canonical_source_blobs"]:
        source_file = tmp_path / source
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_bytes((ROOT / source).read_bytes())
    assert pack.load(model_file)[0]["schema_version"] == "estate.onboarding.v1"
    first = next(iter(meta["canonical_source_blobs"]))
    (tmp_path / first).write_text("obsolete infrastructure assumption")
    with pytest.raises(pack.OnboardingUnavailable, match="changed"):
        pack.load(model_file)
    (tmp_path / first).unlink()
    with pytest.raises(pack.OnboardingUnavailable, match="unavailable"):
        pack.load(model_file)
