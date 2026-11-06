"""Prove the pre-token filter never loses a required verdict event."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from greenlane.event_filter import (  # noqa: E402
    RULESET, decision_from_files, judge_decision, required_contexts,
)


class GreenlaneEventEconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(RULESET.read_text(encoding="utf-8"))

    @staticmethod
    def event(name="ci-success", status="completed"):
        return {"check_run": {"name": name, "status": status, "head_branch": "queue/b1"}}

    def test_all_required_check_completions_invoke_judge(self):
        contexts = required_contexts(self.policy)
        self.assertGreaterEqual(len(contexts), 1)
        for context in contexts:
            with self.subTest(context=context):
                self.assertTrue(judge_decision("check_run", self.event(context), self.policy)[0])

    def test_failed_and_cancelled_required_checks_are_not_skipped(self):
        for status in ("completed", "in_progress", "queued"):
            for context in required_contexts(self.policy):
                with self.subTest(status=status, context=context):
                    invoke, _ = judge_decision("check_run", self.event(context, status), self.policy)
                    self.assertTrue(invoke)

    def test_optional_check_completion_skips_privileged_token(self):
        for context in ("security-scan", "offline-gate", "greenlane", "optional/new"):
            self.assertNotIn(context, required_contexts(self.policy))
            invoke, why = judge_decision("check_run", self.event(context), self.policy)
            self.assertFalse(invoke)
            self.assertIn("optional", why)

    def test_all_other_events_preserve_formation_and_adjudication(self):
        for event_name in ("push", "schedule", "workflow_dispatch", "pull_request_target", ""):
            invoke, _ = judge_decision(event_name, {}, self.policy)
            self.assertTrue(invoke)

    def test_corrupt_event_never_silently_drops_possible_required_check(self):
        for event in (None, {}, [], {"check_run": {}},
                      {"check_run": {"status": "completed"}},
                      {"check_run": {"status": "queued", "name": "optional"}}):
            with self.subTest(event=event):
                self.assertTrue(judge_decision("check_run", event, self.policy)[0])

    def test_unreadable_or_malformed_required_contexts_invoke_the_real_judge(self):
        for policy in (None, {}, [], {"rules": []},
                       {"rules": [{"type": "required_status_checks",
                                   "parameters": {"required_status_checks": []}}]}):
            self.assertTrue(judge_decision("check_run", self.event("optional"), policy)[0])

    def test_rule_changes_take_effect_without_editing_filter(self):
        modified = json.loads(json.dumps(self.policy))
        required = next(r for r in modified["rules"] if r["type"] == "required_status_checks")
        required["parameters"]["required_status_checks"].append(
            {"context": "new-required-guard", "integration_id": 15368}
        )
        self.assertTrue(judge_decision("check_run", self.event("new-required-guard"), modified)[0])
        self.assertFalse(judge_decision("check_run", self.event("new-required-guard"), self.policy)[0])

    def test_unreadable_json_file_preserves_judge_trigger(self):
        with tempfile.TemporaryDirectory() as d:
            e, p = Path(d) / "event", Path(d) / "ruleset"
            e.write_text('{"check_run":', encoding="utf8")
            p.write_text(json.dumps(self.policy), encoding="utf8")
            self.assertTrue(decision_from_files("check_run", e, p)[0])

    def test_cli_emits_exact_github_output_without_any_network(self):
        script = ROOT / "bin/idp-greenlane-check-trigger"
        with tempfile.TemporaryDirectory() as d:
            event = Path(d) / "event.json"
            output = Path(d) / "output"
            event.write_text(json.dumps(self.event("security-scan")), encoding="utf8")
            env = {**os.environ, "GITHUB_EVENT_NAME": "check_run",
                   "GITHUB_EVENT_PATH": str(event), "GITHUB_OUTPUT": str(output)}
            p = subprocess.run([sys.executable, str(script)], env=env,
                               text=True, capture_output=True, check=False)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(output.read_text(encoding="utf8"), "needs_judge=false\n")
            event.write_text(json.dumps(self.event("ci-success")), encoding="utf8")
            q = subprocess.run([sys.executable, str(script)], env=env,
                               text=True, capture_output=True, check=False)
            self.assertEqual(q.returncode, 0, q.stderr)
            self.assertEqual(output.read_text(encoding="utf8"),
                             "needs_judge=false\nneeds_judge=true\n")


if __name__ == "__main__":
    unittest.main()
