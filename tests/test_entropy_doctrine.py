"""Anti-entropy laws must be able to REFUSE plausible but false closure."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "platform/estate/governance/entropy.py"
SPEC = importlib.util.spec_from_file_location("genesis_entropy", SOURCE)
entropy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entropy)


def good():
    return {
        "known_class": True,
        "recurrence_observed": False,
        "class_id": "fault:cloud-edge-loss",
        "root_cause": "common backend absent and client retries cannot recover",
        "fcr_ref": "fcr://edge-loss",
        "control_version": "2.1.0",
        "failing_reproducer_ref": "https://github.com/chidionyema/idp/actions/runs/100",
        "passing_regression_ref": "https://github.com/chidionyema/idp/actions/runs/101",
        "independent_witness_ref": "receipt://independent-verify",
        "independent_witness_id": "security-reviewer",
        "implementer_id": "worker-executor",
        "real_effect_ref": "receipt://real-caller",
        "scope_inventory": ["argon", "idp", "relay"],
        "scope_adoption": ["relay", "argon", "idp"],
        "cross_agent_probe_ref": "receipt://second-agent-probe",
        "residual_risk": "new failure paths remain UNKNOWN",
        "regression_failed_before": True,
        "regression_passed_after": True,
        "founder_visible": True,
    }


class AntiEntropyDoctrineTests(unittest.TestCase):
    def state(self, r):
        return entropy.evaluate_prevention(r)

    def test_full_candidate_still_does_not_grant_release_or_verify_signatures(self):
        out = self.state(good())
        self.assertEqual(out["state"], "CANDIDATE_READY_FOR_INDEPENDENT_VERIFICATION")
        self.assertFalse(out["release_authority"])
        self.assertFalse(out["independently_verified"])

    def test_new_class_is_investigated_once(self):
        self.assertEqual(self.state({"known_class": False})["state"], "INVESTIGATE_ONCE")

    def test_unknown_class_is_blind_not_an_excuse_to_rediagnose(self):
        self.assertEqual(self.state({"cause": "guess"})["state"], "BLIND")

    def test_recurrence_is_prevention_gap_even_with_perfect_other_fields(self):
        r = good()
        r["recurrence_observed"] = True
        out = self.state(r)
        self.assertEqual(out["state"], "PREVENTION_GAP")
        self.assertEqual(out["next_action"], "OPEN_PREVENTION_GAP_AND_SELECT_NEW_HYPOTHESIS")

    def test_unobserved_recurrence_status_is_blind(self):
        r = good()
        del r["recurrence_observed"]
        self.assertEqual(self.state(r)["state"], "BLIND")

    def test_no_root_cause_or_no_independent_proof_refused(self):
        for field in ("class_id", "root_cause", "independent_witness_ref",
                      "passing_regression_ref", "real_effect_ref", "fcr_ref"):
            with self.subTest(field=field):
                r = good()
                r[field] = ""
                out = self.state(r)
                self.assertEqual(out["state"], "PREVENTION_GAP")

    def test_regression_must_precede_and_follow_fix(self):
        for field in ("regression_failed_before", "regression_passed_after"):
            r = good()
            r[field] = False
            self.assertEqual(self.state(r)["state"], "PREVENTION_GAP")

    def test_all_affected_surfaces_must_be_adopted(self):
        r = good()
        r["scope_adoption"] = ["argon"]
        self.assertEqual(self.state(r)["state"], "PREVENTION_GAP")
        self.assertIn("unadopted cross-estate surfaces", self.state(r)["missing"])

    def test_malformed_or_duplicate_scope_does_not_crash_or_close(self):
        for changed in (["argon", "argon"], ["argon", 4], [], "argon"):
            r = good()
            r["scope_inventory"] = changed
            self.assertEqual(self.state(r)["state"], "PREVENTION_GAP")

    def test_same_implementer_and_witness_is_not_independent(self):
        r = good()
        r["independent_witness_id"] = r["implementer_id"]
        self.assertEqual(self.state(r)["state"], "PREVENTION_GAP")

    def test_untrusted_locator_and_invisible_founder_cannot_close(self):
        r = good()
        r["real_effect_ref"] = "agent said yes"
        r["founder_visible"] = False
        self.assertEqual(self.state(r)["state"], "PREVENTION_GAP")

    def test_reminders_are_versioned_but_never_authorize(self):
        self.assertEqual(entropy.REMINDER_SECONDS, 600)
        for boundary in ("SESSION_START", "FLOW_TRANSITION", "DOF_LEASE", "GREENLANE",
                         "RECOVERY", "PEER_WATCH"):
            banner = entropy.doctrine_banner(boundary)
            self.assertIn("HOW TO MANAGE ENTROPY", banner)
            self.assertIn(entropy.VERSION, banner)
            self.assertIn(boundary, banner)


if __name__ == "__main__":
    unittest.main()
