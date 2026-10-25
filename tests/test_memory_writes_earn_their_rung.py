"""A memory earns its rung, or it says it did not.

The defect this pins (2026-10-23, docs/research/2026-10-23-claims-carry-their-checker.md):
`remember` stamped every write `trust_tier: raw_source` whatever the claim was, so a measured
number and a guess arrived at recall identical, and the brief's SELECT read a trust column the
adapter then threw away -- every row rendered under a header that said VERIFIED. Nothing had
measured anything.

Now the door asks the one checker (`bin/estate-claim-check probe`) before the store is touched:
`verified_internal` only when a command re-produced the claim (R1) or the named bytes are there
(R2), `raw_source` with the rung kept otherwise. A judgment is attributed, never verified.

The gate rung that grades this is `bin/memory-gate` (--check rungs 6 and 7). It is proven able
to fail here: `test_a_lying_checker_flips_the_tier_the_gate_grades` shows the exact input that
makes it print UNGRADED, so the rung is not one that cannot go red.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "bin" / "estate-claim-check"
PLUGIN = ROOT / "mcp" / "plugins" / "estate_memory.py"
HARNESS = ROOT / "platform" / "unified-memory-server" / "harness.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their string annotations through sys.modules[cls.__module__], so a
    # module loaded by path must be registered before it executes (harness.py is 3.9 in CI).
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def memory():
    return load("estate_memory_under_test", PLUGIN)


def probe(*args: str) -> tuple[int, dict]:
    p = subprocess.run(  # noqa: S603 - fixed argv, the claim is data
        [sys.executable, str(CHECKER), "probe", "--json", *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return p.returncode, json.loads(p.stdout or "{}")


# --------------------------------------------------------------------------- the one checker


def test_probe_verifies_a_reproducible_claim():
    rc, body = probe("--instrument", "echo 3")
    assert (rc, body["rung"], body["verified"]) == (0, "R1-exec", True)
    assert body["verdict"] == "PASS"


@pytest.mark.parametrize(
    "instrument, why",
    [
        ("false", "an instrument that fails"),  # exits non-zero
        ("true", "an instrument that prints nothing"),  # measured nothing
    ],
)
def test_probe_never_verifies_a_claim_nothing_measured(instrument, why):
    rc, body = probe("--instrument", instrument)
    assert body["verified"] is False, why
    assert body["verdict"] != "PASS", why
    assert rc == 1, "probe must exit 0 only when the claim is verified now"


def test_probe_contradicts_an_expectation_the_instrument_refutes():
    rc, body = probe("--instrument", "echo 3", "--expect", "4")
    assert (rc, body["verdict"], body["verified"]) == (1, "CONTRADICTED", False)


def test_probe_attributes_a_judgment_without_verifying_it():
    rc, body = probe("--authority", "founder, 2026-09-30, AGENTS.md section 5")
    assert body["rung"] == "R3-attributed"
    assert body["verdict"] == "PASS"
    assert body["verified"] is False, "a judgment is attributed; nothing measured it"
    assert rc == 1


def test_probe_refuses_a_claim_with_no_rung():
    rc, body = probe()
    assert (rc, body["verdict"], body["rung"]) == (1, "UNWITNESSED", "")


def test_probe_binds_an_artefact_only_while_its_bytes_are_there(tmp_path):
    art = tmp_path / "evidence.txt"
    art.write_text("the bytes\n")
    rc, body = probe("--evidence", str(art))
    assert (rc, body["rung"], body["verified"]) == (0, "R2-evidence", True)
    art.unlink()
    rc, body = probe("--evidence", str(art))
    assert (rc, body["verdict"], body["verified"]) == (1, "UNWITNESSED", False)


# ------------------------------------------------------------------------------- the door


@pytest.fixture
def store(monkeypatch, memory):
    """An in-process store: do_remember's rung is computed before it, so the write path can be
    graded with no Postgres and no cluster."""
    seen = {}

    def fake_call(cfg, method, key, payload=None, **_kw):
        seen["payload"] = payload
        return {"version": 1}, None

    monkeypatch.setattr(memory, "call", fake_call)
    monkeypatch.setattr(memory, "_harness_call", lambda *a, **k: None)
    monkeypatch.setenv(
        "ESTATE_CLAIM_CHECK", str(CHECKER)
    )  # the checker this tree ships, not a stray one
    cfg = {
        "url": "http://memory.invalid",
        "host": "",
        "token_file": "",
        "namespace": "estate",
        "timeout_s": 1.0,
        "byte_ceiling": 8000,
    }
    return cfg, seen


def test_the_door_stores_verified_internal_only_with_evidence(store, memory):
    cfg, seen = store
    out = memory.do_remember(
        "the estate runs 3 replicas",
        "memverify",
        "measurement",
        ["gate"],
        "test",
        cfg,
        instrument="echo 3",
    )
    assert out["written"] is True
    assert (out["trust_tier"], out["rung"]) == ("verified_internal", "R1-exec")
    assert seen["payload"]["trust_tier"] == "verified_internal"
    assert seen["payload"]["provenance"]["rung"] == "R1-exec"
    assert seen["payload"]["provenance"]["evidence"]


@pytest.mark.parametrize(
    "kwargs, want_rung",
    [
        ({"instrument": "false"}, "R1-exec"),
        ({"instrument": "true"}, "R1-exec"),  # prints nothing: nothing measured
        ({"authority": "an agent's opinion"}, "R3-attributed"),
        ({}, ""),
    ],
)
def test_the_door_labels_an_unbacked_write_raw_source(store, memory, kwargs, want_rung):
    cfg, seen = store
    out = memory.do_remember("a claim", "memverify", "fact", [], "test", cfg, **kwargs)
    assert out["trust_tier"] == "raw_source"
    assert out["rung"] == want_rung
    assert seen["payload"]["trust_tier"] == "raw_source"


def test_the_door_grades_the_claim_even_when_the_store_is_unreachable(
    memory, monkeypatch
):
    monkeypatch.setenv("ESTATE_CLAIM_CHECK", str(CHECKER))
    cfg = {"url": "", "namespace": "estate", "timeout_s": 1.0, "byte_ceiling": 8000}
    out = memory.do_remember(
        "measured", "memverify", "measurement", [], "test", cfg, instrument="echo 3"
    )
    assert out["written"] is False and out["error"]
    assert (out["trust_tier"], out["rung"]) == ("verified_internal", "R1-exec")


def test_a_lying_checker_flips_the_tier_the_gate_grades(
    tmp_path, store, memory, monkeypatch
):
    """The memory-gate rung that fails when a false claim comes back verified, reproduced.

    With the checker this repo ships, `instrument=false` is raw_source (above). Point the door
    at a checker that always says verified and the false claim comes back verified_internal --
    which is exactly the row `bin/memory-gate --check` rung 7 prints as UNGRADED and fails on.
    If this test ever stops flipping, that gate rung has stopped being able to fail.
    """
    liar = tmp_path / "liar"
    liar.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        'print(json.dumps({"verdict": "PASS", "rung": "R1-exec", "verified": True,'
        ' "detail": "trust me"}))\n'
    )
    liar.chmod(0o755)
    monkeypatch.setenv("ESTATE_CLAIM_CHECK", str(liar))
    cfg, _ = store
    out = memory.do_remember(
        "a false claim", "memverify", "fact", [], "test", cfg, instrument="false"
    )
    assert out["trust_tier"] == "verified_internal", "the gate rung would never fire"
    assert out["rung"] == "R1-exec"


def test_a_missing_checker_is_unwitnessed_never_verified(store, memory, monkeypatch):
    monkeypatch.setenv("ESTATE_CLAIM_CHECK", str(ROOT / "bin" / "no-such-checker"))
    cfg, _ = store
    out = memory.do_remember(
        "a claim", "memverify", "fact", [], "test", cfg, instrument="echo 3"
    )
    assert out["verified"] if "verified" in out else out["trust_tier"] == "raw_source"
    assert out["rung"] == "unwitnessed"
    assert out["trust_tier"] == "raw_source"


# ------------------------------------------------------------------------------- the brief


class _Fact:
    def __init__(self, trust_tier, content="a fact"):
        self.id = "1"
        self.tenant_id = "t"
        self.scope = "project_fact"
        self.project_id = None
        self.subject = "probe"
        self.predicate = ""
        self.object = content
        self.artifact_uri = None
        self.artifact_version_hash = None
        self.source_event_at = 0
        self.ingested_at = 0
        self.provenance = "user_direct"
        self.confidence = 1.0
        self.recurrence_count = 1
        self.version = 1
        self.status = "active"
        self.superseded_by_id = None
        self.trust_tier = trust_tier


class _Cortex:
    def __init__(self, facts):
        self._facts = facts

    def search_associative_facts(self, **_kw):
        return self._facts


class _Scratchpad:
    def get_working_scratchpad(self, *_a, **_k):
        return None


class _Telemetry:
    def record_prefetch(self, *_a, **_k):
        return None


def test_the_brief_header_does_not_claim_verification_it_did_not_measure():
    h = load("harness_under_test", HARNESS)
    engine = h.ActiveMemoryEngine(
        _Cortex([_Fact("raw_source"), _Fact("verified_internal")]),
        _Scratchpad(),
        _Telemetry(),
    )
    brief, _tokens = engine.build_active_context_brief(None, "t", None, "run", "probe")
    assert "VERIFIED & EVENT-TIME ORDERED" not in brief
    assert "each row labelled by its own evidence state" in brief
    # Every row states its own tier, so a guess cannot render as a measurement.
    for line in (ln for ln in brief.splitlines() if ln.startswith("- [")):
        assert any(tier in line for tier in ("raw_source", "verified_internal")), line
    assert "| raw_source |" in brief and "| verified_internal |" in brief


def test_the_adapter_carries_the_trust_column_it_already_selects():
    """The SELECT read trust_tier and _rows_to_facts dropped it: the brief could not have
    labelled a row even if it had wanted to."""
    text = HARNESS.read_text()
    assert 'trust_tier=str(row.get("trust_tier") or "raw_source")' in text
    assert 'trust_tier: str = "raw_source"' in text
