"""DoF closure regressions: incident loss is never proof of production recovery.

Tests deliberately exercise the real bin/idp-estate-homes module, without HTTP,
GH CLI, or OCI credentials. These are safety tests, not operational receipts.
"""
import importlib.machinery
import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE = ROOT / "bin" / "idp-estate-homes"
loader = importlib.machinery.SourceFileLoader("idp_estate_homes_recovery", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
door = importlib.util.module_from_spec(spec)
loader.exec_module(door)


def row(verdict, provider="oracle", *, role="default",
        probe_kind="functional", service="llm-router"):
    return {
        "service": service, "leg": "leg-"+provider, "provider": provider,
        "role": role, "url": "https://example.invalid/healthz",
        "verdict": verdict, "detail": "hermetic probe",
        "probe_kind": probe_kind,
    }


class FakeGitHub:
    def __init__(self, title="[lane] llm-router: a lane is down"):
        self.calls = []
        self.title = title

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["issue", "list"]:
            return 0, json.dumps([{"number": 7332, "title": self.title}]), ""
        return 0, "", ""

    @property
    def closed(self):
        return any(c[:2] == ["issue", "close"] for c in self.calls)

    @property
    def commented(self):
        return any(c[:2] == ["issue", "comment"] for c in self.calls)


class RecoveryClosureTests(unittest.TestCase):
    def verdict(self, rows):
        gh = FakeGitHub()
        with patch.object(door, "_gh", gh):
            actions = door.file_issues(rows)
        return gh, actions

    def test_unknown_probe_cannot_clear_down_incident(self):
        gh, acts = self.verdict([row(door.OK), row(door.UNKNOWN, "cloudflare")])
        self.assertFalse(gh.closed)
        self.assertIn("HELD #7332", str(acts))

    def test_not_here_probe_cannot_clear_down_incident(self):
        gh, acts = self.verdict([row(door.OK), row(door.NOT_HERE, "laptop")])
        self.assertFalse(gh.closed)
        self.assertIn("MISSING_MEASURED_OK_OR_UNOBSERVABLE", str(acts))

    def test_http_404_reachability_is_not_functional_restoration(self):
        gh, acts = self.verdict([
            row(door.OK, probe_kind="reachability_only"),
            row(door.OK, "cloudflare"),
        ])
        self.assertFalse(gh.closed)
        self.assertIn("REACHABILITY_ONLY_NOT_FUNCTIONAL_RECOVERY", str(acts))

    def test_http_500_reachability_is_not_functional_restoration(self):
        service = {"service": "estate-doors", "legs": [
            {"name": "api", "provider": "oracle-oke",
             "url": "https://api.invalid/", "expect_any": True},
        ]}
        with patch.object(door, "probe", return_value=(door.OK, "HTTP 500")):
            seen = door.grade_service(service, {}, 1)
        self.assertEqual(seen[0]["verdict"], door.OK)
        self.assertEqual(seen[0]["probe_kind"], "reachability_only")
        self.assertEqual(
            door._auto_closure_proof("estate-doors", seen)[1],
            "REACHABILITY_ONLY_NOT_FUNCTIONAL_RECOVERY",
        )

    def test_partial_failure_cannot_close_incident(self):
        gh, _ = self.verdict([row(door.OK), row(door.FAIL, "cloudflare")])
        self.assertFalse(gh.closed)

    def test_all_success_single_provider_cannot_close_incident(self):
        gh, acts = self.verdict([
            row(door.OK, "oracle"), row(door.OK, "oracle"),
        ])
        self.assertFalse(gh.closed)
        self.assertIn("FAILURE_DOMAIN_REDUNDANCY_UNPROVEN", str(acts))

    def test_unknown_functional_quality_cannot_close_incident(self):
        gh, acts = self.verdict([
            row(door.OK, "oracle", probe_kind="health_status"),
            row(door.OK, "cloudflare"),
        ])
        self.assertFalse(gh.closed)
        self.assertIn("FUNCTIONAL_RECOVERY_PROBE_NOT_CONFIGURED", str(acts))

    def test_single_point_of_failure_ticket_is_not_unsigned_closure(self):
        gh = FakeGitHub(title="[lane] llm-router: single point of failure")
        with patch.object(door, "_gh", gh):
            actions = door.file_issues([
                row(door.OK, "oracle"),
                row(door.OK, "cloudflare"),
            ])
        self.assertFalse(gh.closed)
        self.assertIn("INDEPENDENT_RECOVERY_TRUST_NOT_CONFIGURED", str(actions))

    def test_unsigned_redundant_functional_probes_still_cannot_close(self):
        gh, acts = self.verdict([row(door.OK), row(door.OK, "cloudflare")])
        self.assertFalse(gh.closed)
        self.assertIn("INDEPENDENT_RECOVERY_TRUST_NOT_CONFIGURED", str(acts))

    def test_valid_signed_recovery_receipt_allows_closure_in_fixture_only(self):
        import base64
        import os
        import tempfile
        import time
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        records = [row(door.OK), row(door.OK, "cloudflare")]
        key = Ed25519PrivateKey.generate()
        pub = base64.b64encode(key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )).decode("ascii")
        moment = time.time()
        payload = {
            "schema": "genesis.recovery.v1",
            "service": "llm-router",
            "observer": "independent:test-fixture-only",
            "deployment_sha": "a" * 40,
            "run_id": "123456",
            "issued_at": moment - 4,
            "expires_at": moment + 150,
            "observations": [
                {"leg": r["leg"], "provider": r["provider"],
                 "url": r["url"], "check": "authenticated-functional:model-inference",
                 "result": "FUNCTIONAL_READY", "evidence_sha256": "b" * 64,
                 "observed_at": moment - age}
                for r in records for age in (80, 30)
            ],
        }
        source = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        envelope = {
            "format": "genesis.recovery.ed25519.v1",
            "payload_b64": base64.b64encode(source).decode(),
            "signature_b64": base64.b64encode(key.sign(source)).decode(),
        }
        with tempfile.TemporaryDirectory() as path:
            (pathlib.Path(path) / "llm-router.json").write_text(json.dumps(envelope))
            with patch.dict(os.environ, {
                "ESTATE_RECOVERY_CERTIFIER_ED25519_PUB": pub,
                "ESTATE_RECOVERY_RECEIPTS_DIR": path,
            }):
                gh, actions = self.verdict(records)
        self.assertTrue(gh.closed)
        self.assertIn("closed #7332", str(actions))

    def test_legacy_dof_gate_remains_issue_state_only(self):
        gate = (ROOT / "bin" / "dof-gate").read_text()
        self.assertIn("if not incidents:", gate)
        self.assertIn('"L0: no critical incident open"', gate)


if __name__ == "__main__":
    unittest.main()
