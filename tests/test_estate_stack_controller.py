"""Falsifiers for the one estate stack controller.

The controller is accepted only if it refuses more convincingly than it succeeds:
an intent without a live claim lease, a stale fencing token, a replay, a mutation
outside cloud, a partial door board, an unsigned receipt or an unmeasured stage
must never close yield.
"""

from __future__ import annotations

import base64
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "bin" / "estate-stack-controller"


def _load_controller():
    loader = SourceFileLoader("estate_stack_controller", str(CONTROLLER))
    spec = importlib.util.spec_from_loader("estate_stack_controller", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_stack_controller"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def controller():
    return _load_controller()


CONTROLLER_MODULE = _load_controller()


def _intent(controller, *, mode="verify", idempotency="stack-verify-20261109-001"):
    body = {
        "schema": "estate.stack-intent.v1",
        "intent_id": "stack-recovery-20261109",
        "claim": {
            "repo": "chidionyema/idp",
            "issue": 7826,
            "agent": "estate-agent",
            "fencing_token": "a" * 64,
        },
        "idempotency_key": idempotency,
        "mode": mode,
        "scope": ["stack", "router", "dsh"],
        "resolves": ["estate-doors"],
        "budget_usd": 0,
        "targets": {
            "substrate": "oracle-always-free",
            "router_url": "https://llm.mumchimp.com",
            "router_models_url": "https://llm.mumchimp.com/v1/models",
            "dsh_health_url": "https://chidionyema--estate-dsh-web-web.us-east.modal.run/healthz",
            "opentofu_targets": [
                "oci_core_instance.recovery",
                "oci_core_volume_attachment.surviving",
                "oci_identity_policy.recovery",
                "oci_core_network_security_group_security_rule.recovery_egress",
            ],
        },
        "approval": {
            "scheme": "ed25519-founder",
            "signature": "not-needed-in-verify-mode",
        },
    }
    body["intent_sha256"] = controller.intent_digest(body)
    return body


class Runtime:
    """A deterministic observation source, never a fake of the system under test."""

    def __init__(self, *, doors_ok=14, plan_ok=True, policy_ok=True):
        self.calls = []
        self.doors_ok = doors_ok
        self.plan_ok = plan_ok
        self.policy_ok = policy_ok
        self.replays = set()

    def claim_lease(self, claim, intent_sha):
        self.calls.append(("claim_lease", claim["issue"], intent_sha))
        return {
            "ok": True,
            "issue": claim["issue"],
            "agent": claim["agent"],
            "heartbeat": "2026-11-09T02:55:00Z",
            "expires_at": "2026-11-09T04:55:00Z",
            "fencing_token": claim["fencing_token"],
            "paths": "bin/estate-stack-controller,tests/test_estate_stack_controller.py",
        }

    def dof_lease(self):
        self.calls.append(("dof_lease",))
        return {
            "ok": True,
            "level": "L2",
            "open_incidents": [{"id": "estate-doors", "issue": 7334}],
        }

    def approve(self, intent):
        self.calls.append(("approve", intent["intent_sha256"]))
        return CONTROLLER_MODULE.Outcome(
            True, "founder approval signature verified", "approved"
        )

    def reserve(self, intent):
        self.calls.append(("reserve", intent["idempotency_key"]))
        key = (intent["idempotency_key"], intent["intent_sha256"], intent["mode"])
        if key in self.replays:
            return CONTROLLER_MODULE.Outcome(
                False, "replay refused: idempotency key already used", "replay"
            )
        self.replays.add(key)
        return CONTROLLER_MODULE.Outcome(True, "idempotency lease reserved", "reserved")

    def plan(self, intent):
        self.calls.append(("plan", intent["intent_sha256"]))
        line = "Plan: 0 to add, 0 to change, 0 to destroy"
        return CONTROLLER_MODULE.Outcome(self.plan_ok, line, "Plan: 0")

    def policy(self, intent):
        self.calls.append(("policy", intent["intent_sha256"]))
        return CONTROLLER_MODULE.Outcome(
            self.policy_ok,
            "ok declared infrastructure fits the node budget",
            "fit",
        )

    def mutate(self, operation, intent):
        self.calls.append(("mutate", operation, intent["idempotency_key"]))
        return CONTROLLER_MODULE.Outcome(True, f"{operation} dispatched", operation)

    def probe_router(self, intent):
        self.calls.append(("probe_router", intent["targets"]["router_models_url"]))
        return CONTROLLER_MODULE.Outcome(
            True, "router catalogue and completion measured", "models"
        )

    def probe_dsh(self, intent):
        self.calls.append(("probe_dsh", intent["targets"]["dsh_health_url"]))
        return CONTROLLER_MODULE.Outcome(
            True, "DSH health contract and auth challenge measured", "dsh"
        )

    def doors(self):
        self.calls.append(("doors",))
        return [
            {
                "service": "estate-doors",
                "leg": f"door-{i:02d}",
                "verdict": "MEASURED_OK" if i < self.doors_ok else "MEASURED_FAIL",
                "detail": "HTTP 200" if i < self.doors_ok else "TLS EOF",
            }
            for i in range(14)
        ]

    def publish(self, receipt):
        self.calls.append(("publish", receipt["receipt_id"]))
        return CONTROLLER_MODULE.Outcome(
            True, f"published {receipt['receipt_id']}", receipt["receipt_id"]
        )


def _signer():
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private, public


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _oidc_signer():
    key = generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }

    def token(audience: str) -> str:
        header = _b64url(
            json.dumps(
                {"alg": "RS256", "kid": "test-key", "typ": "JWT"},
                separators=(",", ":"),
            ).encode()
        )
        now = int(time.time())
        claims = _b64url(
            json.dumps(
                {
                    "iss": "https://token.actions.githubusercontent.com",
                    "aud": audience,
                    "sub": "repo:chidionyema/idp:ref:refs/heads/main",
                    "repository": "chidionyema/idp",
                    "ref": "refs/heads/main",
                    "sha": "a" * 40,
                    "workflow_ref": "chidionyema/idp/.github/workflows/estate-stack-controller.yml@refs/heads/main",
                    "iat": now,
                    "exp": now + 3600,
                },
                separators=(",", ":"),
            ).encode()
        )
        signing_input = f"{header}.{claims}".encode()
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return f"{header}.{claims}.{_b64url(signature)}"

    return token, {"keys": [jwk]}


def _run(controller, tmp_path, intent, runtime, *, mode="verify"):
    path = tmp_path / "intent.json"
    path.write_text(json.dumps(intent))
    private, public = _signer()
    receipt = tmp_path / "receipt.json"
    doc = controller.execute(
        path,
        mode=mode,
        receipt_path=receipt,
        runtime=runtime,
        signing_key=private,
        clock=lambda: 1794193200.0,
    )
    return doc, receipt, public


def test_intent_contract_is_versioned_and_rejects_an_unknown_schema(controller):
    intent = _intent(controller)
    assert controller.validate_intent(intent) == []
    intent["schema"] = "estate.stack-intent.v0"
    assert any("schema" in problem for problem in controller.validate_intent(intent))


def test_lease_is_bound_to_the_live_claim_and_a_stale_fencing_token_is_refused(
    controller, tmp_path
):
    intent = _intent(controller)
    runtime = Runtime()
    runtime.claim_lease = lambda claim, digest: {
        "ok": True,
        "issue": 7826,
        "agent": "estate-agent",
        "heartbeat": "2026-11-09T02:55:00Z",
        "expires_at": "2026-11-09T04:55:00Z",
        "fencing_token": "b" * 64,
        "paths": "bin/estate-stack-controller",
    }
    doc, _, _ = _run(controller, tmp_path, intent, runtime)
    assert doc["yield"]["verdict"] == "OPEN"
    assert "fencing" in doc["yield"]["reason"].lower()
    assert not [call for call in runtime.calls if call[0] == "mutate"]


def test_fencing_token_is_derivable_before_the_intent_digest(controller):
    first = controller.claim_fencing_token(
        "chidionyema/idp",
        7826,
        6730720553,
        "estate-agent",
        "2026-11-09T02:24:02Z",
        "bin/estate-stack-controller,tests/test_estate_stack_controller.py",
    )
    second = controller.claim_fencing_token(
        "chidionyema/idp",
        7826,
        6730720553,
        "estate-agent",
        "2026-11-09T02:24:02Z",
        "bin/estate-stack-controller,tests/test_estate_stack_controller.py",
    )
    assert first == second
    assert len(first) == 64
    assert first != controller.claim_fencing_token(
        "chidionyema/idp",
        7826,
        6730720553,
        "estate-agent",
        "2026-11-09T02:24:03Z",
        "bin/estate-stack-controller,tests/test_estate_stack_controller.py",
    )


def test_real_plan_uses_only_declared_targets_and_not_the_retired_oke_door(
    controller, tmp_path
):
    runtime = controller.RealRuntime(plan_dir=tmp_path)
    calls = []

    def measured(argv, timeout=300, cwd=None):
        calls.append((list(argv), cwd))
        if argv[0] == "tofu" and "plan" in argv:
            out = next(
                (arg.split("=", 1)[1] for arg in argv if arg.startswith("-out=")),
                "",
            )
            if out:
                Path(out).write_text("saved plan\n")
        return subprocess.CompletedProcess(argv, 0, "ok measured\n", "")

    runtime._run = measured
    outcome = runtime.plan(_intent(controller))
    assert outcome.ok
    flattened = " ".join(part for argv, _cwd in calls for part in argv)
    assert "idp-oke-rebuild" not in flattened
    for target in _intent(controller)["targets"]["opentofu_targets"]:
        assert f"-target={target}" in flattened
    assert any("tofu" in argv[0] and "plan" in argv for argv, _cwd in calls)


def test_router_health_accepts_the_real_plain_text_liveliness_body(
    controller, tmp_path, monkeypatch
):
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    runtime = controller.RealRuntime(plan_dir=tmp_path)
    replies = iter(
        [
            (200, "I'm alive!"),
            (200, {"data": [{"id": "estate.model-router"}]}),
        ]
    )
    runtime._get_json = lambda url, timeout=20: next(replies)
    outcome = runtime.probe_router(_intent(controller))
    assert outcome.measured is False
    assert "catalogue has 1 models" in outcome.line
    assert "authenticated completion BLIND" in outcome.line


def test_verify_mode_never_applies_or_deploys(controller, tmp_path):
    runtime = Runtime(doors_ok=14)
    doc, _, _ = _run(controller, tmp_path, _intent(controller), runtime)
    assert doc["mode"] == "verify"
    assert not [call for call in runtime.calls if call[0] == "mutate"]
    assert doc["yield"]["verdict"] == "CLOSED"


def test_receipts_for_repository_intents_do_not_capture_a_local_machine_path(
    controller, tmp_path
):
    private, _public = _signer()
    doc = controller.execute(
        ROOT / "platform/estate/stack-intents/stack-recovery-20261109.json",
        mode="verify",
        receipt_path=tmp_path / "receipt.json",
        runtime=Runtime(),
        signing_key=private,
        clock=lambda: 1794193200.0,
    )
    assert doc["intent"]["path"] == (
        "platform/estate/stack-intents/stack-recovery-20261109.json"
    )


def test_apply_mode_requires_cloud_execution_history(controller, tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    intent = _intent(controller, mode="apply")
    runtime = Runtime()
    doc, _, _ = _run(controller, tmp_path, intent, runtime, mode="apply")
    assert doc["yield"]["verdict"] == "OPEN"
    assert "github actions" in doc["yield"]["reason"].lower()
    assert not [call for call in runtime.calls if call[0] == "mutate"]


def test_a_partial_door_board_is_open_even_when_router_and_dsh_are_healthy(
    controller, tmp_path
):
    doc, _, _ = _run(controller, tmp_path, _intent(controller), Runtime(doors_ok=1))
    assert doc["verification"]["doors"] == {
        "measured_ok": 1,
        "total": 14,
        "required": 14,
    }
    assert doc["yield"]["verdict"] == "OPEN"
    assert "door" in doc["yield"]["reason"].lower()


def test_no_stage_is_pass_when_its_measurement_failed(controller, tmp_path):
    runtime = Runtime(policy_ok=False)
    doc, _, _ = _run(controller, tmp_path, _intent(controller), runtime)
    policy = next(stage for stage in doc["stages"] if stage["stage"] == "policy")
    assert policy["verdict"] == "FAILED"
    assert policy["measured"] is True
    assert doc["yield"]["verdict"] == "OPEN"


def test_receipt_is_signed_and_any_field_tamper_is_refused(controller, tmp_path):
    doc, receipt, public = _run(
        controller, tmp_path, _intent(controller), Runtime(doors_ok=1)
    )
    assert doc["yield"]["verdict"] == "OPEN"
    assert controller.verify_receipt(doc, public)["ok"] is True
    tampered = json.loads(receipt.read_text())
    tampered["yield"]["verdict"] = "CLOSED"
    verdict = controller.verify_receipt(tampered, public)
    assert verdict["ok"] is False
    assert "signature" in verdict["reason"].lower()


def test_github_oidc_signature_binds_the_exact_receipt_payload(controller):
    token, jwks = _oidc_signer()
    unsigned = {
        "schema": controller.RECEIPT_SCHEMA,
        "receipt_id": "a" * 64,
        "controller": {
            "version": controller.CONTROLLER_VERSION,
            "contract_schema": controller.CONTRACT_SCHEMA,
            "contract_sha256": controller.contract_digest(),
        },
        "intent": {
            "path": "platform/estate/stack-intents/example.json",
            "id": "example",
            "sha256": "b" * 64,
            "claim": {
                "repo": "chidionyema/idp",
                "issue": 7826,
                "agent": "estate-agent",
                "fencing_token": "c" * 64,
            },
            "idempotency_key": "estate-stack-verify-20261109-001",
            "resolves": ["estate-doors"],
        },
        "mode": "verify",
        "lease": {},
        "stages": [
            {
                "stage": name,
                "command": name,
                "exit": 0,
                "line": "measured",
                "sha256": "d" * 64,
                "measured": True,
                "verdict": "MEASURED_OK",
            }
            for name in controller.VERIFY_STAGES
        ],
        "verification": {"doors": {"measured_ok": 14, "total": 14, "required": 14}},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "yield": {"verdict": "CLOSED", "reason": "all stages measured"},
    }
    signed = controller.sign_receipt_oidc(unsigned, token)
    assert signed["signature"]["algorithm"] == "github-oidc"
    receipt_schema = json.loads(
        (ROOT / "catalog/schemas/estate.stack-receipt.v1.schema.json").read_text()
    )
    Draft202012Validator(receipt_schema).validate(signed)
    verdict = controller.verify_receipt(signed, b"", jwks=jwks)
    assert verdict["ok"] is True, verdict
    signed["yield"]["reason"] = "tampered after signing"
    verdict = controller.verify_receipt(signed, b"", jwks=jwks)
    assert verdict["ok"] is False


def test_a_signed_receipt_cannot_claim_closed_with_a_partial_door_board(
    controller, tmp_path
):
    intent_path = tmp_path / "intent.json"
    intent_path.write_text(json.dumps(_intent(controller)))
    private, public = _signer()
    receipt_path = tmp_path / "receipt.json"
    doc = controller.execute(
        intent_path,
        mode="verify",
        receipt_path=receipt_path,
        runtime=Runtime(doors_ok=1),
        signing_key=private,
        clock=lambda: 1794193200.0,
    )
    assert doc["yield"]["verdict"] == "OPEN"
    doc["yield"]["verdict"] = "CLOSED"
    fraud = controller.sign_receipt(doc, private)
    verdict = controller.verify_receipt(fraud, public)
    assert verdict["ok"] is False
    assert "yield" in verdict["reason"].lower()


def test_secret_shaped_output_is_redacted_before_it_reaches_the_receipt(controller):
    text = (
        "Authorization: Bearer sk-live-abcdefghijklmnopqrstuvwxyz "
        "token=ghp_abcdefghijklmnopqrstuvwxyz0123456789 "
        "-----BEGIN PRIVATE KEY-----not-a-real-key-----END PRIVATE KEY-----"
    )
    safe = controller.redact(text)
    assert "sk-live" not in safe
    assert "ghp_" not in safe
    assert "BEGIN PRIVATE KEY" not in safe
    assert "<redacted>" in safe


def test_same_idempotency_key_cannot_run_a_second_cloud_mutation(
    controller, tmp_path, monkeypatch
):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    intent = _intent(controller, mode="apply")
    runtime = Runtime()
    first, _, _ = _run(controller, tmp_path, intent, runtime, mode="apply")
    second, _, _ = _run(controller, tmp_path, intent, runtime, mode="apply")
    assert first["yield"]["verdict"] == "CLOSED"
    assert second["yield"]["verdict"] == "OPEN"
    assert "replay" in second["yield"]["reason"].lower()
    assert len([call for call in runtime.calls if call[0] == "mutate"]) == 3


def test_the_exact_stage_order_is_machine_checkable(controller):
    assert controller.REQUIRED_STAGE_ORDER == (
        "gate",
        "plan",
        "lease",
        "cost",
        "policy",
        "apply",
        "publish",
        "router-deploy",
        "dsh-deploy",
        "verify-router",
        "verify-dsh",
        "verify-doors",
        "publish-receipt",
    )
    assert controller.CONTRACT_SCHEMA == "estate.stack-controller-contract.v1"
    assert len(controller.contract_digest()) == 64


def test_the_intent_and_receipt_are_published_as_versioned_schemas(
    controller, tmp_path
):
    intent_schema = json.loads(
        (ROOT / "catalog/schemas/estate.stack-intent.v1.schema.json").read_text()
    )
    receipt_schema = json.loads(
        (ROOT / "catalog/schemas/estate.stack-receipt.v1.schema.json").read_text()
    )
    Draft202012Validator.check_schema(intent_schema)
    Draft202012Validator.check_schema(receipt_schema)
    Draft202012Validator(intent_schema).validate(_intent(controller))
    doc, _, _ = _run(controller, tmp_path, _intent(controller), Runtime())
    Draft202012Validator(receipt_schema).validate(doc)


def test_the_executable_contract_has_an_explicit_bdd_specification():
    feature = ROOT / "tests/bdd/estate_stack_controller.feature"
    text = feature.read_text()
    assert "Scenario: an unmeasured stage never closes yield" in text
    assert "Scenario: exactly fourteen measured doors are required" in text
    assert "Scenario: apply is cloud-only and lease-bound" in text
    assert "Scenario: a signed receipt cannot bless a false closed yield" in text


def test_cloud_workflow_uses_the_one_controller_and_oidc_signing():
    workflow = (ROOT / ".github/workflows/estate-stack-controller.yml").read_text()
    assert "id-token: write" in workflow
    assert "actions: write" in workflow
    assert "issues: write" in workflow
    assert "bin/estate-stack-controller" in workflow
    assert "--verify-receipt" in workflow
    assert "gtrevorrow/oci-token-exchange-action" in workflow
    assert "modal deploy" not in workflow
    assert "kubectl apply" not in workflow
