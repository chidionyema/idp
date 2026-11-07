"""Mission preflight prevents predictable red PRs while preserving a viable repair route."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "bin" / "legion-mission-preflight"
loader = importlib.machinery.SourceFileLoader("legion_mission_preflight", str(path))
spec = importlib.util.spec_from_loader("legion_mission_preflight", loader)
mission = importlib.util.module_from_spec(spec)
loader.exec_module(mission)

REG = {"components": {"llm-router": {"repairScope": ["@substrate"]}},
       "substrateScope": ["k3s/**", "platform/llm/**"]}
RED = [{"id": "llm-router", "issue": 7332}]

class SuccessFirstTest(unittest.TestCase):
    def test_precise_live_incident_not_fake_pr(self):
        inp = [{"number": 7332, "title": "[lane] llm-router: a lane is down"},
               {"number": 100, "title": "[lane] fake: a lane is down", "pull_request": {}}]
        self.assertEqual(mission.collect(inp), RED)

    def test_no_oke_recovery_route_is_suggested(self):
        brief = mission.packet(REG, RED, "restore service")
        self.assertNotIn("oke", str(brief).lower())
        self.assertEqual(brief["level"], "L2")

    def test_safe_repair_is_explicitly_possible(self):
        self.assertTrue(mission.decision(REG, RED, ["k3s/router.yaml"], "llm-router")["admitted"])

    def test_invalid_and_protected_paths_are_refused_before_model_spend(self):
        for paths in [["../leak"], ["/root/.ssh/key"], [".github/workflows/agent-sandbox.yml"],
                      [".githooks/pre-commit"], [], ["k3sx/router.yaml"]]:
            self.assertFalse(mission.decision(REG, RED, paths, "llm-router")["admitted"], paths)

    def test_unrelated_work_cannot_claim_a_repair_without_real_incident(self):
        self.assertFalse(mission.decision(REG, RED, ["README.md"], "llm-router")["admitted"])
        self.assertFalse(mission.decision(REG, RED, ["k3s/router.yaml"], None)["admitted"])
        self.assertFalse(mission.decision(REG, [], ["src/app.py"], "llm-router")["admitted"])
        self.assertTrue(mission.decision(REG, [], ["src/app.py"])["admitted"])

    def test_unobservability_is_research_only_not_fake_l0(self):
        brief = mission.packet(REG, None, "find real health")
        self.assertEqual(brief["level"], "L2")
        self.assertFalse(brief["health_proven"])
        self.assertFalse(mission.decision(REG, None, ["src/a.py"])["admitted"])
        self.assertTrue(brief["first_actions"])

    def test_success_packet_is_harness_agnostic_and_bounded(self):
        b = mission.packet(REG, RED, "prevent recurring red")
        self.assertEqual(b["limits"]["slice_seconds"], 100)
        self.assertEqual(b["limits"]["identical_retry_cap"], 2)
        self.assertIn("greenlane", b["final_gates"])
        self.assertTrue(b["this_is_not_a_capability"])
        self.assertEqual(b["repair_scopes"]["llm-router"], ["k3s/**", "platform/llm/**"])

    def test_missing_registry_does_not_mint_success(self):
        self.assertFalse(mission.decision({}, RED, ["k3s/router.yaml"], "llm-router")["admitted"])
