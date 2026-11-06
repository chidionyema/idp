"""Adversarial evidence: a verdict cannot authenticate itself.

No keys, network, external services or deployment permissions needed.
This test applies to the actual shipped verdict and freshness-gate code.
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from probes import verdict as V

ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader(
    "verdict_fresh_under_test", str(ROOT / "bin" / "idp-verdict-fresh")
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
FRESH = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(FRESH)
SHA = "a" * 40
RUN_ID = 15371
REPO = "chidionyema/idp"
EVENT = "schedule"
PATH = ".github/workflows/verdict-langfuse.yml"


def fake_verdict(*, passing=True):
    v = V.build(
        "langfuse.l1-l3.cold_sso",
        "langfuse@example",
        SHA,
        "sha256:" + "b" * 64,
        "release-1",
        [V.assertion("live-health", "healthy", "healthy" if passing else "down", passing)],
        prover_run_id=str(RUN_ID),
        prover_id="github-actions/verdict-langfuse",
        evidence_ref=f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
        started_at=time.time() - 1,
        ttl_seconds=3600,
    )
    return V.sign(v, "real-secret-only-prover-knows")


def fake_run(**overrides):
    return {
        "id": RUN_ID, "status": "completed", "conclusion": "success",
        "head_sha": SHA, "head_branch": "main", "path": PATH,
        "event": EVENT, "updated_at": "2026-11-06T15:40:00Z",
        **overrides,
    }


class ExternalVerdictTests(unittest.TestCase):
    def invoke(self, *, verdict=None, run=None, attestation='[{"verificationResult": {}}]',
               attestation_error=None):
        verdict = fake_verdict() if verdict is None else verdict
        run = fake_run() if run is None else run
        calls = []

        def gh(*args):
            calls.append(args)
            if args[0] == "repo":
                return REPO
            if args[0] == "api":
                return json.dumps(run)
            if args[:2] == ("run", "download"):
                target = Path(args[args.index("-D") + 1]) / "verdict.json"
                target.write_text(json.dumps(verdict), encoding="utf8")
                return ""
            if args[:2] == ("attestation", "verify"):
                if attestation_error:
                    raise RuntimeError(attestation_error)
                return attestation
            raise AssertionError("unrecognized GitHub API call: " + repr(args))

        with patch.object(FRESH, "gh", side_effect=gh), patch.dict(
            os.environ, {"GITHUB_REPOSITORY": REPO}
        ), contextlib.redirect_stdout(io.StringIO()) as out:
            result = FRESH.main(
                ["langfuse", "--changed", "platform/observability/langfuse-values.yaml"]
            )
        return result, out.getvalue(), calls

    def test_valid_hmac_verdict_authenticates_only_with_its_secret(self):
        v = fake_verdict()
        self.assertEqual(V.grade(v, "real-secret-only-prover-knows")[0], "PASS")
        self.assertEqual(V.grade(v, "wrong")[0], "UNVERIFIED")
        self.assertEqual(V.grade(v, None)[0], "UNVERIFIED")
        self.assertEqual(V.grade(v, "")[0], "UNVERIFIED")

    def test_nonempty_fake_hmac_never_grades_green_without_key(self):
        v = fake_verdict()
        v["sig"] = "deadbeef" * 8
        self.assertEqual(V.grade(v)[0], "UNVERIFIED")

    def test_signed_pass_with_failed_assertion_is_rejected(self):
        v = fake_verdict(passing=False)
        v["outcome"] = "PASS"
        v = V.sign(v, "real-secret-only-prover-knows")
        state, reason = V.grade(v, "real-secret-only-prover-knows")
        self.assertEqual(state, "UNVERIFIED")
        self.assertIn("contradicted", reason)

    def test_signed_pass_without_assertions_is_rejected(self):
        v = fake_verdict()
        v["assertions"] = []
        v = V.sign(v, "real-secret-only-prover-knows")
        self.assertEqual(V.grade(v, "real-secret-only-prover-knows")[0], "UNVERIFIED")

    def test_bad_ttl_rejected_even_if_validly_signed(self):
        for ttl in (0, 3601, -1, "999999999"):
            with self.subTest(ttl=ttl):
                v = fake_verdict()
                v["ttl_seconds"] = ttl
                v = V.sign(v, "real-secret-only-prover-knows")
                self.assertEqual(V.grade(v, "real-secret-only-prover-knows")[0],
                                 "UNVERIFIED")

    def test_verified_attestation_is_required_for_a_pass(self):
        status, message, calls = self.invoke()
        self.assertEqual(status, 0, message)
        self.assertIn("PASS", message)
        args = next(c for c in calls if c[:2] == ("attestation", "verify"))
        for pair in (
            ("--repo", REPO),
            ("--source-ref", "refs/heads/main"),
            ("--source-digest", SHA),
            ("--signer-workflow", f"{REPO}/{PATH}"),
            ("--format", "json"),
        ):
            self.assertEqual(args[args.index(pair[0]) + 1], pair[1])

    def test_no_attestation_is_not_a_green_run(self):
        for data in ("[]", "garbage"):
            with self.subTest(data=data):
                rc, text, _ = self.invoke(attestation=data)
                self.assertEqual(rc, 1)
                self.assertIn("no valid GitHub OIDC/Sigstore attestation", text)

    def test_attestation_verifier_failure_is_not_a_green_run(self):
        rc, text, _ = self.invoke(attestation_error="invalid signature")
        self.assertEqual(rc, 1)
        self.assertIn("invalid signature", text)

    def test_verdict_about_a_different_run_or_commit_is_refused_before_attestation(self):
        for key, value in (("commit_sha", "f" * 40), ("prover_run_id", "22"),
                           ("prover_id", "agent"), ("evidence_ref", "attacker")):
            with self.subTest(key=key):
                v = fake_verdict()
                v[key] = value
                rc, text, calls = self.invoke(verdict=v)
                self.assertEqual(rc, 1)
                self.assertIn("subject/issuer/run", text)
                self.assertFalse(any(c[:2] == ("attestation", "verify") for c in calls))

    def test_untrusted_run_metadata_is_refused_before_any_verdict_download(self):
        for key, value in (("head_branch", "evil"), ("head_sha", "f"),
                           ("path", "evil.yml"), ("status", "in_progress"),
                           ("conclusion", "cancelled"), ("event", "pull_request")):
            with self.subTest(key=key):
                rc, text, calls = self.invoke(run=fake_run(**{key: value}))
                self.assertEqual(rc, 1)
                self.assertIn("unexpected or untrusted", text)
                self.assertFalse(any(c[:2] == ("run", "download") for c in calls))

    def test_signed_failure_allows_repair_only_with_attested_provenance(self):
        v = fake_verdict(passing=False)
        rc, _, _ = self.invoke(verdict=v, run=fake_run(conclusion="failure"))
        self.assertEqual(rc, 0)
        rc, _, _ = self.invoke(verdict=v, run=fake_run(conclusion="failure"),
                               attestation_error="signature invalid")
        self.assertEqual(rc, 1)

    def test_self_contradictory_pass_rejected_even_after_attestation_verification(self):
        v = fake_verdict(passing=False)
        v["outcome"] = "PASS"
        rc, msg, _ = self.invoke(verdict=v)
        self.assertEqual(rc, 1, msg)
        self.assertIn("contradicted", msg)

    def test_no_silent_degrade_of_signature_or_repository_authority(self):
        workflow = (ROOT / ".github/workflows/verdict-langfuse.yml").read_text()
        gate = (ROOT / "bin/idp-verdict-fresh").read_text()
        self.assertIn("attestations: write", workflow)
        self.assertIn("artifact-metadata: write", workflow)
        self.assertIn("uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6", workflow)
        self.assertIn("subject-path: ${{ runner.temp }}/verdict.json", workflow)
        self.assertIn("--signer-workflow", gate)
        self.assertIn("--source-digest", gate)
        self.assertIn("--source-ref", gate)
        self.assertNotIn("V.grade(v, None)", gate)


if __name__ == "__main__":
    unittest.main()
