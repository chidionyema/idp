"""KARMA negative-space and causal custody falsifiers: never self-award yield."""
import importlib.util
import importlib.machinery
import io
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "platform/estate/karma/observer.py"
spec = importlib.util.spec_from_file_location("karma_kernel", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NOW = "2026-11-12T14:00:00+00:00"
SHA = "a" * 40


def run(**kwargs):
    row = {"id": 123, "name": "ci", "head_sha": SHA, "status": "completed",
            "conclusion": "success", "created_at": "2026-11-12T13:00:00Z",
            "run_started_at": "2026-11-12T13:00:01Z",
            "updated_at": "2026-11-12T13:01:00Z", "event": "push",
            "actor": {"login": "agent"}, "run_attempt": 1,
            "html_url": "https://github.com/chidionyema/idp/actions/runs/123",
            }
    row.update(kwargs)
    return row


class KarmaTests(unittest.TestCase):
    def test_real_ci_success_does_not_settle_debt_or_grant_reward(self):
        result = mod.observe_runs("chidionyema/idp", [run()], NOW)
        row = result["runs"][0]
        self.assertEqual(row["verdict"], "EXECUTION_REPORTED_SUCCESS_NOT_YIELD")
        self.assertIsNone(row["obligation_id"])
        self.assertIsNone(row["verified_yield"])
        self.assertIsNone(row["resource_cost"])
        self.assertEqual(result["coverage"]["unlinked_to_obligation"], 1)
        self.assertEqual(result["coverage"]["yield_coverage"],
                         "UNKNOWN_NO_INDEPENDENT_OBLIGATION_JOINS")

    def test_pending_or_skipped_never_becomes_positive_yield(self):
        a = run(id=33, conclusion=None, status="queued")
        b = run(id=34, conclusion="skipped")
        result = mod.observe_runs("chidionyema/idp", [a, b], NOW)
        self.assertEqual([row["verdict"] for row in result["runs"]],
                         ["PENDING_NOT_YIELD", "NO_EXECUTION_YIELD"])

    def test_actor_does_not_magically_provide_quad_or_model_version(self):
        result = mod.observe_runs("chidionyema/idp", [run()], NOW)
        self.assertEqual(result["runs"][0]["model_revision"], "UNKNOWN")
        self.assertIn("QUAD_IDENTITY_UNOBSERVED", result["runs"][0]["gaps"])

    def test_missing_and_future_timestamps_are_not_trusted(self):
        a = run(id=22, created_at=None)
        b = run(id=23, updated_at="2030-01-01T00:00:00Z")
        result = mod.observe_runs("chidionyema/idp", [a, b], NOW)
        self.assertIn("EVENT_TIME_MISSING", result["runs"][0]["gaps"])
        self.assertIn("CLOCK_ORDER_UNTRUSTED", result["runs"][1]["gaps"])

    def test_invalid_sha_counted_as_missing(self):
        result = mod.observe_runs("chidionyema/idp", [run(head_sha="fake")], NOW)
        self.assertIn("SOURCE_SHA_UNKNOWN", result["runs"][0]["gaps"])
        self.assertEqual(result["runs"][0]["source_sha"], "UNKNOWN")

    def test_duplicate_is_not_double_accounted(self):
        result = mod.observe_runs("chidionyema/idp", [run(), run()], NOW)
        self.assertEqual(result["coverage"]["invalid_or_duplicate"], 1)
        self.assertEqual(result["coverage"]["runs_accepted"], 1)

    def test_reruns_are_observed_but_never_assumed_to_be_waste(self):
        result = mod.observe_runs("chidionyema/idp", [run(run_attempt=2)], NOW)
        self.assertEqual(result["rerun_attempts_observed"], 1)
        self.assertNotIn("wasted", result["note"])

    def test_missing_observation_source_fails_blind_not_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "missing.json"
            result = subprocess.run([sys.executable, str(ROOT / "bin/idp-karma-observe"),
                                     "--runs-json", str(p), "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["state"], "BLIND")

    def test_offline_cli_replays_through_actual_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "runs.json"
            p.write_text(json.dumps({"workflow_runs": [run()]}), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "bin/idp-karma-observe"),
                                     "--runs-json", str(p), "--now", NOW, "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["coverage"]["runs_accepted"], 1)

    def test_naive_unknown_utc_rejected(self):
        with self.assertRaises(ValueError):
            mod.observe_runs("chidionyema/idp", [run()], "2026-11-12T14:00:00")

    def test_public_idp_uses_credentialless_chronos_fallback_when_gh_is_absent(self):
        path = ROOT / "bin/idp-karma-observe"
        loader = importlib.machinery.SourceFileLoader("karma_live_cli", str(path))
        spec = importlib.util.spec_from_loader("karma_live_cli", loader)
        cli = importlib.util.module_from_spec(spec)
        loader.exec_module(cli)

        class Response(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *_):
                self.close()

        payload = json.dumps({"workflow_runs": [run()]}).encode()
        with patch.object(cli.subprocess, "run", side_effect=FileNotFoundError), \
             patch.object(cli.urllib.request, "urlopen", return_value=Response(payload)) as opening:
            self.assertEqual(len(cli.live_runs("chidionyema/idp")), 1)
            self.assertEqual(opening.call_count, 1)
            self.assertIn("api.github.com/repos/chidionyema/idp", opening.call_args.args[0].full_url)

    def test_private_repo_is_never_silently_assumed_public_or_free(self):
        path = ROOT / "bin/idp-karma-observe"
        loader = importlib.machinery.SourceFileLoader("karma_private_cli", str(path))
        spec = importlib.util.spec_from_loader("karma_private_cli", loader)
        cli = importlib.util.module_from_spec(spec)
        loader.exec_module(cli)
        with patch.object(cli.subprocess, "run", side_effect=FileNotFoundError), \
             patch.object(cli.urllib.request, "urlopen") as opening:
            with self.assertRaises(RuntimeError):
                cli.live_runs("chidionyema/argon")
            opening.assert_not_called()


if __name__ == "__main__":
    unittest.main()
