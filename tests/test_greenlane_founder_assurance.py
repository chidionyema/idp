"""Founder UX is a verdict over observed state, not a flattering proxy.

These tests exercise the existing shared /fleet brief and candidate check reader.
No generated telemetry or GitHub credentials enter the fixtures.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from greenlane.brief import brief, candidate_check_index  # noqa: E402


def snapshot(**overrides):
    s = {
        "now_min": 1_000,
        "alarm": False,
        "main": {"required": {"ci-success": "success"}},
        "state": {
            "available": True,
            "lanes": {},
            "batch": None,
            "latency": {
                "queue_to_land_min": {"n": 2, "p50": 12, "p90": 32},
                "batch_cycle_min": {"n": 4, "p50": 8, "p90": 44},
                "outcomes": {"landed": 2, "timeout/retried": 1, "red/bisected": 1},
            },
        },
        "open_prs": [], "invariants": {"work_lost": 0},
        "candidate_checks": {},
    }
    s.update(overrides)
    return s


class FounderAssuranceTests(unittest.TestCase):
    def test_healthy_idle_stays_quiet_with_real_sample_counts(self):
        b = brief(snapshot())
        self.assertFalse(b["loud"])
        self.assertEqual(b["summary"], "nothing landing. all clear.")
        v = b["assurance"]
        self.assertEqual(v["state"], "IDLE")
        self.assertEqual(v["batch_outcome_sample"]["n"], 4)
        self.assertEqual(v["batch_outcome_sample"]["landed_batch_pct"], 50.0)
        self.assertEqual(v["batch_outcome_sample"]["timeouts"], 1)
        self.assertEqual(v["batch_outcome_sample"]["bisected"], 1)
        self.assertIsNone(v["cost_per_accepted_change_gbp"])

    def test_missing_state_never_yields_an_all_clear(self):
        s = snapshot()
        s["state"]["available"] = False
        b = brief(s)
        self.assertTrue(b["loud"])
        self.assertEqual(b["assurance"]["state"], "UNKNOWN")
        self.assertEqual(b["assurance"]["next_action"]["code"], "restore-state-read")
        self.assertNotIn("all clear", b["summary"])

    def test_claim_held_lane_is_visible_and_actionable(self):
        s = snapshot()
        s["state"]["lanes"] = {
            "lane/a": {"status": "pending", "reason": "no live claim: issue not open",
                       "arrived": 990}
        }
        b = brief(s)
        self.assertTrue(b["loud"])
        self.assertEqual(b["assurance"]["next_action"]["code"], "renew-claim")
        self.assertEqual(b["assurance"]["oldest_pending_or_testing_age_min"], 10)

    def test_check_bottleneck_is_visible_after_30min(self):
        s = snapshot()
        s["state"]["batch"] = {"started": 968, "members": [["lane/a", "h", "tip"]]}
        s["state"]["lanes"] = {"lane/a": {"status": "testing", "arrived": 900}}
        s["candidate_checks"] = {
            "ci-success": {"result": "success", "url": "https://example.test/1"},
            "test": {"result": "in_progress", "url": "https://example.test/2"},
        }
        b = brief(s)
        self.assertTrue(b["loud"])
        self.assertEqual(b["assurance"]["state"], "RED")
        self.assertEqual(b["assurance"]["next_action"]["check"], "test")
        self.assertEqual(b["assurance"]["next_action"]["url"], "https://example.test/2")
        self.assertEqual(b["assurance"]["batch_age_min"], 32)

    def test_90min_timeout_is_explicit_without_fabricating_a_verdict(self):
        s = snapshot()
        s["state"]["batch"] = {"started": 909, "members": [["lane/a", "h", "tip"]]}
        s["state"]["lanes"] = {"lane/a": {"status": "testing", "arrived": 905}}
        b = brief(s)
        self.assertTrue(b["assurance"]["batch_overdue"])
        self.assertEqual(b["assurance"]["batch_age_min"], 91)
        self.assertNotEqual(b["assurance"]["state"], "IDLE")

    def test_unknown_check_read_becomes_very_visible_not_green(self):
        s = snapshot()
        s["state"]["batch"] = {"started": 996, "members": [["lane/a", "h", "tip"]]}
        s["candidate_checks"] = {
            "test": {"result": "unreadable: HTTP 403", "url": None}
        }
        b = brief(s)
        self.assertTrue(b["loud"])
        self.assertEqual(b["assurance"]["state"], "UNKNOWN")
        self.assertEqual(b["assurance"]["next_action"]["check"], "test")

    def test_candidate_check_reader_tracks_latest_of_same_name(self):
        payload = {
            "total_count": 3,
            "check_runs": [
                {"name": "test", "id": 100, "status": "completed",
                 "conclusion": "failure", "html_url": "https://example.test/old"},
                {"name": "test", "id": 101, "status": "completed",
                 "conclusion": "success", "html_url": "https://example.test/new"},
                {"name": "optional", "id": 102, "status": "completed",
                 "conclusion": "success"},
            ]
        }
        out = candidate_check_index(payload, ["test", "ci-success"])
        self.assertEqual(out["test"]["result"], "success")
        self.assertEqual(out["test"]["url"], "https://example.test/new")
        self.assertEqual(out["ci-success"]["result"], "absent")

    def test_candidate_check_reader_fails_closed_on_unreadable_or_truncated_evidence(self):
        self.assertIn("unreadable", candidate_check_index(None, ["test"], "403")
                      ["test"]["result"])
        truncated = {"total_count": 180, "check_runs": []}
        self.assertIn("unreadable", candidate_check_index(truncated, ["test"])
                      ["test"]["result"])

    def test_unreviewed_lane_cannot_replace_privileged_engine_source(self):
        workflow = (ROOT / ".github/workflows/greenlane.yml").read_text()
        # A GitHub Actions push workflow executes the YAML from the pushed
        # branch. A privileged lane-push event is therefore a code-injection
        # path even when it initially checks out main.
        self.assertNotIn("  push:\n    branches: [lane/**", workflow)
        self.assertIn("  workflow_run:\n    workflows: [no-harness-folders]", workflow)
        self.assertIn("github.event.workflow_run.head_branch", workflow)
        self.assertIn("          ref: main", workflow)
        self.assertNotIn("git reset --hard", workflow)
        self.assertNotIn("git checkout", workflow)
        self.assertIn('trusted_main_sha="$(git rev-parse HEAD)"', workflow)
        # The fallback schedule and explicit founder dispatch must survive
        # a malicious or broken lane-side wakeup.
        self.assertIn('cron: "*/15 * * * *"', workflow)
        self.assertIn("  workflow_dispatch:", workflow)

    def test_event_filter_is_before_app_token_in_live_workflow(self):
        workflow = (ROOT / ".github/workflows/greenlane.yml").read_text()
        check = workflow.index("id: check_relevance")
        app = workflow.index("uses: ./.github/actions/github-app-token")
        tick = workflow.index("- name: one tick of the lane")
        self.assertTrue(check < app < tick)
        self.assertEqual(workflow.count("if: steps.check_relevance.outputs.needs_judge == 'true'"), 2)
        self.assertIn("python3 bin/idp-greenlane-check-trigger", workflow)


if __name__ == "__main__":
    unittest.main()
