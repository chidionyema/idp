"""OPA fleet policy adapter: disobedient commands never execute on DENY/UNKNOWN."""
import io
import json
import pathlib
import sys

import pytest

POLICY = pathlib.Path(__file__).resolve().parents[1] / "platform" / "estate" / "policy"
sys.path.insert(0, str(POLICY))
import fleet_opa


class Reply:
    status = 200

    def __init__(self, obj):
        self.bytes = json.dumps(obj).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.bytes[:size]


def reply(value):
    def opener(request, timeout):
        assert timeout == 1.0
        assert request.get_method() == "POST"
        sent = json.loads(request.data)
        assert sent["input"]["contract_version"] == "estate.effect.v1"
        assert "command" not in sent["input"]
        return Reply({"result": value})
    return opener


def test_denied_action_never_executes(monkeypatch):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://127.0.0.1:8181/v1/data/estate/fleet/decision")
    effects = []
    with pytest.raises(fleet_opa.FleetPolicyRefusal) as err:
        fleet_opa.run_shell(
            intent="git.push", step="push", command="printf forbidden",
            session="claimed", timeout=3, open_url=reply({
                "allow": False, "revision": "signed-2", "reason": "founder-halt"
            }), run=lambda *a, **k: effects.append(a))
    assert effects == []
    assert err.value.verdict.status == "ENFORCED"
    assert err.value.verdict.revision == "signed-2"


@pytest.mark.parametrize("response", [
    {},
    {"allow": "true", "revision": "r2"},
    {"allow": True},
    {"allow": False, "revision": ""},
    {"allow": True, "revision": 42},
])
def test_malformed_or_missing_policy_is_denied(monkeypatch, response):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://127.0.0.1:8181/v1/data/estate/fleet/decision")
    result = fleet_opa.evaluate(intent="git.push", step="push",
                                command="echo x", session="", open_url=reply(response))
    assert not result.allowed
    assert result.status == "UNKNOWN_DENY"


def test_policy_outage_denies_effect(monkeypatch):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://127.0.0.1:8181/v1/data/estate/fleet/decision")
    def broken(*args, **kw):
        raise OSError("offline")
    assert fleet_opa.evaluate(intent="deploy", step="apply", command="echo x",
                              session="", open_url=broken).status == "UNKNOWN_DENY"


def test_enrolled_allowed_uses_existing_executor(monkeypatch):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://127.0.0.1:8181/v1/data/estate/fleet/decision")
    effects = []
    verdict, result = fleet_opa.run_shell(
        intent="status", step="status", command="printf allowed",
        session="", timeout=4, open_url=reply({
            "allow": True, "revision": "signed-4", "reason": "allowed"
        }), run=lambda command, **kw: effects.append((command, kw)) or "executed")
    assert verdict.status == "ENFORCED"
    assert result == "executed"
    assert len(effects) == 1
    assert effects[0][1]["timeout"] == 4


def test_unenrolled_is_not_misreported_as_enforced(monkeypatch):
    monkeypatch.delenv("ESTATE_OPA_DECISION_URL", raising=False)
    result = fleet_opa.evaluate(intent="status", step="show", command="echo x", session="")
    assert result.status == "UNENROLLED"


def test_reject_cleartext_remote_policy_endpoint(monkeypatch):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://example.org/v1/data/estate/fleet/decision")
    result = fleet_opa.evaluate(intent="deploy", step="apply", command="echo x", session="")
    assert not result.allowed
    assert result.status == "INVALID_CONFIG"


def test_decision_input_never_contains_raw_command(monkeypatch):
    monkeypatch.setenv("ESTATE_OPA_DECISION_URL", "http://127.0.0.1:8181/v1/data/estate/fleet/decision")
    secret = "an-unlogged-secret"
    def assert_safe(request, timeout):
        assert secret.encode() not in request.data
        return Reply({"result": {"allow": False, "revision": "v2"}})
    result = fleet_opa.evaluate(intent="x", step="y", command=secret,
                                session="", open_url=assert_safe)
    assert result.status == "ENFORCED"
