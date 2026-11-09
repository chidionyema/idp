"""The PoBR verifier must gate state-changing actions, not just outbound messages.

ADR 0042 D6 measured that the PoBR stack was built (`pobr_schema.py`, `pobr_gate.py`) but
"no config loads any of them" -- the only live wiring gated `send_/emit_/reply_/notify_/message_`
tool names, and even that only checked that a grant FILE existed, never that a structured
reasoning receipt was actually admitted by the verifier.

These are falsifiers: before the fix they FAIL (a `class: mutate` intent ran with no reasoning
receipt; a rejected receipt still consumed a grant), after it they PASS.

The gate must:
  1. refuse a `class: mutate` intent from a LIVE session that has no admitted grant;
  2. refuse a `class: mutate` intent when the grant exists but was never admitted by the verifier;
  3. allow a `class: mutate` intent once an admitted grant is on record;
  4. leave ANONYMOUS automation alone -- a fence a correct machine cannot satisfy is an outage
     (the greenlane and scheduled jobs have no ledger and must pass, as the plan gate already
     encodes with ledger_exists);
  5. run the deterministic verifier on submit, and refuse to consume a grant for a receipt the
     verifier rejects;
  6. keep receipt-building tools (pobr_submit / pobr_status / pobr-gate / pobr-admit) and reads
     available -- a gate that refuses the tools for building the receipt deadlocks reasoning.
"""

import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GRANT_MODULE_PATH = REPO / "mcp" / "plugins" / "pobr_grant.py"
PLUGIN_PATH = REPO / "mcp" / "plugins" / "estate_mcp.py"


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# --- pobr_grant module: classification and admission ----------------------
@pytest.fixture()
def grant_mod(tmp_path, monkeypatch):
    module = _load("pobr_grant_under_test", GRANT_MODULE_PATH)
    monkeypatch.setattr(module, "GRANT_DIR", tmp_path / "pobr")
    module.GRANT_DIR.mkdir(parents=True, exist_ok=True)
    return module


def _issue(grant_mod, session_id):
    """Write an unconsumed, unadmitted grant exactly as the CLI `issue` command does."""
    grant_mod._ensure_grant_dir()
    now = time.time()
    grant = {
        "session_id": session_id,
        "tool": "probe",
        "created_at": now,
        "expires_at": now + grant_mod.GRANT_TTL_SECONDS,
        "used": False,
    }
    grant_mod._grant_file(session_id).write_text(json.dumps(grant))
    return grant


def test_mutate_class_is_gated(grant_mod):
    assert grant_mod.requires_grant("probe", intent_class="mutate") is True


def test_read_class_is_not_gated(grant_mod):
    assert grant_mod.requires_grant("probe", intent_class="read") is False


def test_outbound_messaging_still_gated(grant_mod):
    assert grant_mod.requires_grant("send_message") is True


def test_receipt_building_tools_are_never_gated(grant_mod):
    for name in ("pobr_submit", "pobr_status", "pobr-gate", "pobr-admit"):
        assert grant_mod.requires_grant(name) is False
        assert grant_mod.requires_grant(name, intent_class="mutate") is False


def test_check_grant_refuses_unadmitted_grant(grant_mod):
    _issue(grant_mod, "sess-1")
    check = grant_mod.check_grant("sess-1")
    assert check["valid"] is False
    assert "not admitted" in check["reason"]


def test_check_grant_refuses_missing_grant(grant_mod):
    assert grant_mod.check_grant("sess-none")["valid"] is False


def test_check_grant_accepts_admitted_grant(grant_mod):
    _issue(grant_mod, "sess-1")
    path = grant_mod._grant_file("sess-1")
    grant = json.loads(path.read_text())
    grant["admitted"] = True
    path.write_text(json.dumps(grant))
    assert grant_mod.check_grant("sess-1")["valid"] is True


def test_submit_refuses_a_receipt_without_counterfactual(grant_mod):
    """A receipt missing a counterfactual commitment must be REJECTED by the verifier and the
    grant stays unconsumed. This is the falsifier that proves submit runs the gate, not just
    the old grant-file existence check."""

    _issue(grant_mod, "sess-1")
    receipt = {
        "receipt_id": "r-1",
        "schema": "pobr/v1",
        "agent_id": "estate-agent",
        "session_id": "sess-1",
        "task": "diagnose a thing",
        "issued_at": time.time(),
        "exhaustiveness_claim": "consulted all reachable state",
        "posterior": {"HEALTHY": 0.5, "CRASH": 0.5},
        "posterior_method": "bayesian",
        "calibration": {"expected_calibration_error": 0.01, "brier_score": 0.05},
        "prior_sweep": {},
        "rank_stable": True,
        "merkle_root": "0" * 64,
        "signature": "",
        "external_anchor": "",
        "verification_instructions": "recompute the product",
        "data_points_consulted": [],
        "data_points_excluded": [],
        "hypotheses": [
            {"id": "h1", "description": "crash", "prior": 0.5, "posterior": 0.5},
            {"id": "h2", "description": "healthy", "prior": 0.5, "posterior": 0.5},
        ],
        "likelihoods": [],
        "reasoning_steps": [],
        # counterfactual intentionally omitted
        "faithfulness": {"rank_consistent": True, "divergence_flagged": False},
    }
    result = grant_mod.pobr_submit_tool("sess-1", receipt)
    assert result["ok"] is False
    assert "REJECTED" in result["reason"]

    # The grant must remain unconsumed, so the refusal is durable and re-tryable.
    grant = json.loads(grant_mod._grant_file("sess-1").read_text())
    assert grant["used"] is False


# --- estate_mcp plugin: the action gate at _estate_invoke -----------------
@pytest.fixture()
def plugin(tmp_path, monkeypatch):
    """Load the MCP plugin with a temp intents dir containing one mutate and one read intent,
    and a plan contract that reports liveness on demand."""

    intents = tmp_path / ".estate" / "intents"
    intents.mkdir(parents=True, exist_ok=True)
    (intents / "danger.yaml").write_text(
        "name: danger\ndescription: changes state\nclass: mutate\ndoor_s: 20\n"
        "steps:\n  - name: do\n    cmd: touch marker\n"
    )
    (intents / "safe.yaml").write_text(
        "name: safe\ndescription: reads only\nclass: read\ndoor_s: 20\n"
        "steps:\n  - name: read\n    cmd: git --version\n"
    )
    monkeypatch.setenv("ESTATE_INTENTS_DIR", str(intents))
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    module = _load("estate_mcp_under_test", PLUGIN_PATH)

    # Control liveness deterministically.
    class _Plan:
        def __init__(self):
            self.live = set()

        def ledger_exists(self, session_id):
            return session_id in self.live

        def resolve_session_id(self):
            return ""

    plan = _Plan()
    monkeypatch.setattr(module, "_PLAN_CONTRACT", plan)
    monkeypatch.setattr(module, "_PLAN_CONTRACT_TRIED", True)

    # Point the grant store at a temp dir too.
    grant_mod_loaded = _load("pobr_grant_for_plugin", GRANT_MODULE_PATH)
    monkeypatch.setattr(grant_mod_loaded, "GRANT_DIR", tmp_path / "pobr")
    grant_mod_loaded.GRANT_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, "pobr_grant", grant_mod_loaded)

    # The executor binary will not exist at a fixed path; stub it so the gate is the only
    # thing under test (the subprocess run is asserted elsewhere).
    monkeypatch.setattr(module, "_local_executor", lambda: tmp_path / "estate-execute")
    (tmp_path / "estate-execute").write_text("#!/bin/sh\nexit 0\n")

    return module, plan, grant_mod_loaded


def _mutate(plugin, session_id):
    module, _plan, _grant = plugin
    return module._estate_invoke(
        {"intent": "danger", "session_id": session_id, "args": {}}
    )


def test_live_mutate_without_grant_is_refused(plugin):
    module, plan, _grant = plugin
    plan.live.add("sess-live")
    out = module._estate_invoke(
        {"intent": "danger", "session_id": "sess-live", "args": {}}
    )
    assert out.startswith("ERROR: PoBR grant check failed"), out


def test_live_mutate_with_admitted_grant_is_allowed(plugin):
    module, plan, grant = plugin
    plan.live.add("sess-live")
    _issue(grant, "sess-live")
    path = grant._grant_file("sess-live")
    rec = json.loads(path.read_text())
    rec["admitted"] = True
    path.write_text(json.dumps(rec))
    out = module._estate_invoke(
        {"intent": "danger", "session_id": "sess-live", "args": {}}
    )
    assert not out.startswith("ERROR: PoBR grant check failed"), out


def test_anonymous_mutate_is_not_gated(plugin):
    """Anonymous automation has no live ledger and must pass -- a fence a correct machine
    cannot satisfy is an outage (the greenlane, scheduled jobs run anonymously)."""
    module, plan, _grant = plugin
    out = module._estate_invoke({"intent": "danger", "args": {}})
    assert not out.startswith("ERROR: PoBR grant check failed"), out


def test_read_intent_from_live_session_is_not_gated(plugin):
    module, plan, _grant = plugin
    plan.live.add("sess-live")
    out = module._estate_invoke(
        {"intent": "safe", "session_id": "sess-live", "args": {}}
    )
    assert not out.startswith("ERROR: PoBR grant check failed"), out
