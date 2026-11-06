"""Prevent the CI provisioning budget from becoming an unbounded blind spot."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


class InstallerBudgetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKFLOW.read_text(encoding="utf-8")
        start = cls.content.index("  offline-gate:\n")
        stop = cls.content.index("  # crew#219 R39", start)
        cls.offline = cls.content[start:stop]

    def test_job_and_dependency_steps_have_explicit_hard_budgets(self):
        self.assertIn("    timeout-minutes: 45", self.offline)
        self.assertIn("      - name: tools\n", self.offline)
        self.assertIn("        timeout-minutes: 15\n", self.offline)
        self.assertIn("timeout -k 10s", self.offline)

    def test_all_original_apt_and_python_dependency_classes_remain(self):
        for required in (
            "budget apt-index 180 sudo apt-get update",
            "budget apt-tools 180 sudo apt-get install",
            "shellcheck jq sqlite3 age",
            "budget science-deps 420 python -m pip install",
            "dagster dagster-webserver yamllint==1.37.1",
            "budget acceptance-deps 360 python -m pip install",
            "-r sovereign/requirements-dev.txt",
            "budget docs-deps 180 python -m pip install",
            '"mkdocs<2" mkdocs-techdocs-core',
        ):
            self.assertIn(required, self.offline, required)

    def test_failure_stays_failure_and_is_diagnosed_by_substep(self):
        self.assertIn("if timeout -k 10s", self.offline)
        self.assertIn("rc=$?", self.offline)
        self.assertIn('exit "${rc}"', self.offline)
        self.assertIn("::error::offline-gate dependency install", self.offline)
        self.assertNotIn("|| true", self.offline)

    def test_all_required_offline_validation_runs_after_installation(self):
        tools = self.offline.index("      - name: tools")
        command = self.offline.index("      - run: bin/idp-ci")
        self.assertLess(tools, command)
        self.assertIn("      - uses: ./.github/actions/estate-tools", self.offline)
        self.assertNotIn("if: success()", self.offline)

    def test_no_manual_production_policy_override(self):
        self.assertIn("needs: [fast-gate, verifier]", self.offline)
        self.assertIn('IDP_CI_SKIP_PYTEST: "1"', self.offline)
        self.assertIn("IDP_CI_BASE:", self.offline)


if __name__ == "__main__":
    unittest.main()
