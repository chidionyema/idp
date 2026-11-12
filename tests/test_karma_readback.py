"""KARMA's falsifiers: no fake cost, model version, custody or yield."""

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / rel))
    spec = importlib.util.spec_from_loader(name, loader)
    obj = importlib.util.module_from_spec(spec)
    loader.exec_module(obj)
    return obj


readback = load("karma_readback_tests", "platform/estate/karma/readback.py")
router = load("karma_router_tests", "platform/llm/action_ledger.py")


def run(run_id=71, conclusion="failure"):
    return {
        "repo": "idp",
        "workflow": "ci",
        "id": run_id,
        "conclusion": conclusion,
        "sha": "a" * 40,
        "created_at": "2026-11-12T12:00:00Z",
    }


def test_ci_green_cannot_settle_production_debt():
    r = readback.reconcile([run(conclusion="success")])
    assert r["ci"]["observed_runs"] == 1
    assert r["ci"]["verified_production_yield"] is None
    assert r["quad"]["verified_obligation_settlements"] is None
    assert r["investor"]["safe_to_assert_live_verified_KARMA"] is False


def test_missing_ids_and_duplicates_are_observable_not_accepted_as_success():
    r = readback.reconcile([run(), run(), {"repo": "idp", "conclusion": "failure"}])
    assert r["ci"]["observed_runs"] == 2
    assert r["ci"]["duplicates"] == 1
    assert r["ci"]["missing_run_ids"] == 1
    assert r["ci"]["missing_or_invalid_times"] == 1


def test_unknown_cost_remains_unknown_not_free():
    r = readback.reconcile([run()])
    assert r["ci"]["billable_cost"] is None
    assert r["ci"]["cost_quality"] == "UNKNOWN_NOT_ZERO"
    assert r["quad"]["token_count_observed"] is None


def test_provider_group_uses_returned_model_but_cannot_claim_opaque_version():
    events = [
        {
            "karma": {
                "schema": "estate.karma.call.v1",
                "provider": "vendor",
                "returned_model": "fast",
                "model_revision": "v9",
                "instruction_id": None,
                "total_tokens": 17,
            }
        },
        {
            "karma": {
                "schema": "estate.karma.call.v1",
                "provider": "vendor",
                "returned_model": "fast",
                "model_revision": "UNKNOWN",
                "instruction_id": "FLOW-42",
                "total_tokens": 5,
            }
        },
    ]
    r = readback.reconcile([], events)
    assert r["quad"]["model_calls_observed"] == 2
    assert r["quad"]["token_count_observed"] == 22
    assert r["quad"]["missing_instruction_link"] == 1
    assert r["quad"]["group_by_provider_model_revision"]["vendor/fast/UNKNOWN"] == 2
    assert r["quad"]["verified_obligation_settlements"] is None


def test_router_captures_usage_provider_and_instruction_without_fake_attestation():
    class Answer:
        model = "returned-model"
        usage = {"prompt_tokens": 120, "completion_tokens": 33, "total_tokens": 153}

    kwargs = {
        "model": "requested-model",
        "litellm_params": {
            "custom_llm_provider": "provider-x",
            "proxy_server_request": {
                "body": {"metadata": {"instruction_id": "FLOW-17"}}
            },
        },
    }
    k = router.karma_call(kwargs, Answer())
    assert k["provider"] == "provider-x"
    assert k["instruction_id"] == "FLOW-17"
    assert k["requested_model"] == "requested-model"
    assert k["returned_model"] == "returned-model"
    assert k["total_tokens"] == 153
    assert k["model_revision"] == "UNKNOWN"
    assert k["billed_cost"] is None
    assert k["yield_verdict"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert k["metadata_integrity"] == "NOT_SIGNED_BY_LEGACY_ELPIS_ENVELOPE"


def test_malicious_instruction_text_never_becomes_a_bound_identity():
    kwargs = {
        "model": "model-x",
        "litellm_params": {
            "proxy_server_request": {
                "body": {"metadata": {"instruction_id": "<unsafe>"}}
            }
        },
    }
    k = router.karma_call(kwargs, {}, outcome="failure")
    assert k["instruction_id"] is None
    assert k["instruction_link"] == "MISSING"
    assert k["outcome"] == "failure"
    assert k["total_tokens"] is None
    assert k["cost_status"] == "UNKNOWN_NOT_ZERO"


def test_unreadable_run_source_is_an_error_not_a_clean_snapshot():
    import pytest

    with pytest.raises(ValueError):
        readback.reconcile({"status": "BLIND"})


def test_router_persists_karmas_usage_in_signed_action_and_existing_fleet_outbox(
    tmp_path, monkeypatch
):
    import json
    import sqlite3

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key = tmp_path / "agent.pem"
    key.write_bytes(pem)
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(key))
    monkeypatch.setenv("ESTATE_ACTION_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))
    router._KEY = None
    kwargs = {
        "model": "requested-v1",
        "litellm_params": {
            "custom_llm_provider": "experimental-vendor",
            "proxy_server_request": {
                "body": {"metadata": {"instruction_id": "FLOW-00013"}},
                "headers": {"user-agent": "claude-code/2.0"},
            },
        },
    }
    response = {
        "model": "returned-v1",
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }
    first = router.record(kwargs, response)
    assert first["karma"]["total_tokens"] == 14
    assert first["karma"]["instruction_id"] == "FLOW-00013"
    assert first["karma"]["metadata_integrity"] == "NOT_SIGNED_BY_LEGACY_ELPIS_ENVELOPE"
    assert router.verify() == (1, "")
    con = sqlite3.connect(tmp_path / "outbox.db")
    try:
        outbox = [json.loads(x[0]) for x in con.execute("select payload from outbox")]
    finally:
        con.close()
    assert len(outbox) == 1
    assert outbox[0]["tool"]["karma"]["provider"] == "experimental-vendor"
    assert outbox[0]["tool"]["karma"]["returned_model"] == "returned-v1"
    assert outbox[0]["tool"]["karma"]["yield_verdict"] == "NOT_INDEPENDENTLY_VERIFIED"

    second = router.record(kwargs, {}, outcome="failure")
    assert second["karma"]["outcome"] == "failure"
    assert router.verify() == (2, "")


def test_legacy_signature_must_not_be_misrepresented_as_authenticating_karma(
    tmp_path, monkeypatch
):
    import json

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    secret_file = tmp_path / "agent.pem"
    secret_file.write_bytes(pem)
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(secret_file))
    monkeypatch.setenv("ESTATE_ACTION_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))
    router._KEY = None
    router.record({"model": "requested", "litellm_params": {}}, {})
    path = tmp_path / "ledger.jsonl"
    lines = path.read_text().splitlines()
    original = json.loads(lines[0])
    original["karma"]["total_tokens"] = 999999
    path.write_text(json.dumps(original, sort_keys=True, separators=(",", ":")) + "\n")
    # The legacy signature covers METHOD/URI/TS/BODY-HASH/AGENT/SESSION ONLY.
    # On the final row the parent chain also has no successor to expose edit.
    # This test establishes the vulnerability; the evaluator MUST NOT reward it.
    assert router.verify() == (1, "")
    evaluated = readback.reconcile([], [original])
    assert evaluated["quad"]["source"] == "ROUTER_SOURCE_UNVERIFIED"
    assert evaluated["quad"]["verified_obligation_settlements"] is None
