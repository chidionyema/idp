"""Falsify the exact preflight seams against the canonical existing DoF engine."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "agent_admission_test", str(ROOT / "bin/idp-agent-admission")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
admission = importlib.util.module_from_spec(spec)
loader.exec_module(admission)


class AgentAdmissionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "catalog/dof-registry.json").read_text())
        cls.incidents = [{"id": "estate-doors", "issue": 8042}]

    def decision(self, paths, incidents=None):
        return admission.decide(
            paths, root=ROOT, registry=self.registry,
            incidents=self.incidents if incidents is None else incidents
        )

    def test_known_8105_failure_refused_before_model(self):
        result = self.decision([
            "AGENTS.md", "docs/standards/estate-adversarial-assurance.md"
        ])
        self.assertEqual(result["verdict"], "REFUSED")

    def test_ordinary_independent_test_allowed(self):
        result = self.decision(["tests/test_agent_admission.py"])
        self.assertEqual(result["verdict"], "ADMISSIBLE_FOR_FURTHER_CHECKS")

    def test_protected_dof_test_never_allowed_as_safe(self):
        result = self.decision(["tests/test_dof_gate.py"])
        self.assertEqual(result["verdict"], "REFUSED")

    def test_mixed_safe_and_unsafe_must_refuse_whole_candidate(self):
        result = self.decision(["tests/test_agent_admission.py", "AGENTS.md"])
        self.assertEqual(result["verdict"], "REFUSED")

    def test_recovery_blind_incident_cannot_generate_a_grant(self):
        result = self.decision(["tests/test_agent_admission.py"],
                               incidents=[{"id": "dof-probe", "issue": None}])
        self.assertEqual(result["verdict"], "BLIND")

    def test_empty_scope_is_blind_not_success(self):
        self.assertEqual(self.decision([])["verdict"], "BLIND")

    def test_unsafe_path_refused_before_authority_query(self):
        self.assertEqual(self.decision(["../secret"])["verdict"], "REFUSED")

    def test_dof_resumption_allows_scope_under_no_open_incidents(self):
        result = self.decision(["AGENTS.md"], incidents=[])
        self.assertEqual(result["verdict"], "ADMISSIBLE_FOR_FURTHER_CHECKS")

    def test_workflow_runs_gate_before_provider_install(self):
        text = (ROOT / ".github/workflows/agent-sandbox.yml").read_text()
        self.assertLess(text.index("Admit declared paths before any provider spending"),
                        text.index("Install the harness and age"))
        self.assertLess(text.index("Verify staged effect scope before issue claim or commit"),
                        text.index("Claim the work on an issue"))
        self.assertLess(text.index("Claim the work on an issue"),
                        text.index("Commit through the estate's own hooks"))

    def test_plan_parsing(self):
        self.assertEqual(admission.parse_plan("Mission\nPlanned-Paths: tests/a.py,README.md\n"),
                         ["tests/a.py", "README.md"])


if __name__ == "__main__":
    unittest.main()
