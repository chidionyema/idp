import tempfile, unittest
from pathlib import Path
from stewardship import Ledger, Refused, authorize, compare


class StewardshipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Ledger(Path(self.tmp.name) / "s.db")

    def tearDown(self):
        self.db.db.close()
        self.tmp.cleanup()

    def test_append_verify(self):
        self.db.append("c1", "observed", "agent", {"evidence": ["trace:abc"]})
        self.db.append("c1", "researched", "agent", {"options": 2})
        self.assertTrue(self.db.verify())

    def test_tamper_detected(self):
        self.db.append("c1", "observed", "agent", {})
        self.db.db.execute("UPDATE events SET actor='intruder'")
        self.db.db.commit()
        self.assertFalse(self.db.verify())

    def test_no_secrets(self):
        with self.assertRaises(Refused):
            self.db.append("c1", "observed", "agent", {"nested": {"token": "bad"}})

    def test_invalid_kind(self):
        with self.assertRaises(Refused):
            self.db.append("c1", "invented", "agent", {})

    def test_separate_cases(self):
        self.db.append("c1", "observed", "a", {})
        self.db.append("c2", "observed", "a", {})
        self.assertEqual(len(self.db.events("c1")), 1)

    def test_clearance(self):
        self.db.append("c1", "observed", "a", {}, "restricted")
        self.assertEqual(self.db.events("c1", "public"), [])

    def test_case_summary(self):
        self.db.append("c1", "observed", "a", {})
        self.assertEqual(self.db.cases()[0]["last_kind"], "observed")

    def test_research_allowed(self):
        self.assertTrue(
            authorize(
                {
                    "risk": "high",
                    "reversible": False,
                    "blast_radius": "estate",
                    "estimated_cost": 0,
                    "claim_valid": False,
                    "independent_verification": False,
                    "mode": "research",
                },
                {},
            ).allowed
        )

    def base(self):
        return dict(
            risk="low",
            reversible=True,
            blast_radius="isolated",
            estimated_cost=0,
            claim_valid=True,
            independent_verification=True,
            mode="execute",
            baseline_evidence="trace:1",
            rollback_plan="revert",
        )

    def test_low_risk(self):
        self.assertTrue(authorize(self.base(), {"max_autonomous_cost": 0}).allowed)

    def test_no_claim(self):
        x = self.base()
        x["claim_valid"] = False
        self.assertFalse(authorize(x, {}).allowed)

    def test_no_verification(self):
        x = self.base()
        x["independent_verification"] = False
        self.assertFalse(authorize(x, {}).allowed)

    def test_new_infrastructure_blocked(self):
        x = self.base()
        x["new_infrastructure"] = True
        self.assertFalse(authorize(x, {}).allowed)

    def test_high_risk_blocked(self):
        x = self.base()
        x["risk"] = "high"
        self.assertFalse(authorize(x, {}).allowed)

    def test_shared_requires_delegation(self):
        x = self.base()
        x["blast_radius"] = "shared"
        self.assertFalse(authorize(x, {}).allowed)
        self.assertTrue(authorize(x, {"allow_shared_changes": True}).allowed)

    def test_budget(self):
        x = self.base()
        x["estimated_cost"] = 5
        self.assertFalse(authorize(x, {"max_autonomous_cost": 0}).allowed)

    def test_missing_baseline(self):
        x = self.base()
        x["baseline_evidence"] = ""
        self.assertFalse(authorize(x, {}).allowed)

    def test_compare_regression(self):
        a = [{"success": True, "latency_ms": 100, "cost": 1}]
        b = [{"success": False, "latency_ms": 20, "cost": 0.1}]
        self.assertFalse(compare(a, b)["accepted"])

    def test_compare_empty(self):
        with self.assertRaises(Refused):
            compare([], [])


if __name__ == "__main__":
    unittest.main()
