"""Adversarial, network-free tests for the Greenlane incident reactor."""
import unittest
from greenlane.common_failure_reaction import classify, react

POLICY = "b" * 40
BASE = "a" * 12

def row(bid, base=BASE, lane="lane/a", gate="dof-gate", outcome="red"):
    return {
        "id": bid, "base": base, "outcome": outcome,
        "reason": f"ci-success failure https://github.com/x/y/actions/runs/42 -- {gate} > refused",
        "members": [lane], "started": 100, "verdict_at": 104,
    }

class ReactorTests(unittest.TestCase):
    def test_distinct_lanes_one_common_cause(self):
        d = classify({"history": [row("b1"), row("b2", lane="lane/b")]}, POLICY)
        self.assertEqual(d.state, "COMMON_MODE")
        self.assertEqual(d.elapsed_batch_minutes, 8)
        self.assertEqual(d.affected_lanes, ("lane/a", "lane/b"))

    def test_one_lane_retried_is_not_cross_lane_evidence(self):
        self.assertEqual(classify({"history": [row("b1"), row("b2")]}, POLICY).state, "INSUFFICIENT")

    def test_candidate_bdd_failure_not_global(self):
        h = [row("b1", gate="bdd"), row("b2", lane="lane/b", gate="bdd")]
        self.assertEqual(classify({"history": h}, POLICY).state, "INSUFFICIENT")

    def test_a_different_main_invalidates_prior_failures(self):
        h = [row("b1"), row("b2", base="c" * 12, lane="lane/b")]
        self.assertEqual(classify({"history": h}, POLICY).state, "INSUFFICIENT")

    def test_a_successful_landing_ends_the_epoch(self):
        h = [row("b1"), row("b2", lane="lane/b"), row("b3", outcome="landed")]
        self.assertEqual(classify({"history": h}, POLICY).state, "INSUFFICIENT")

    def test_missing_state_and_policy_are_blind(self):
        self.assertEqual(classify({}, POLICY).state, "BLIND")
        self.assertEqual(classify({"history": []}, "bad").state, "BLIND")

    def test_repeated_batches_share_one_incident_fingerprint(self):
        h = [row("b1"), row("b2", lane="lane/b")]
        a = classify({"history": h}, POLICY)
        b = classify({"history": h + [row("b3", lane="lane/c")]}, POLICY)
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertNotEqual(a.fingerprint, classify({"history": h}, "c" * 40).fingerprint)

    def test_repeat_event_does_not_write_duplicate_comment(self):
        d = classify({"history": [row("b1"), row("b2", lane="lane/b")]}, POLICY)
        calls = []
        def gh(repo, *args):
            calls.append(args)
            if args[0].endswith("/issues/7800"):
                return {"state": "open"}
            if "comments?" in args[0]:
                return [{"body": "greenlane-common-mode-fingerprint: " + d.fingerprint}]
            raise AssertionError(args)
        self.assertEqual(react(d, "chidionyema/idp", gh=gh), "duplicate event: no write")
        self.assertEqual(len(calls), 2)

    def test_new_epoch_posts_only_to_canonical_incident(self):
        d = classify({"history": [row("b1"), row("b2", lane="lane/b")]}, POLICY)
        calls = []
        def gh(repo, *args):
            calls.append(args)
            if len(args) == 1 and args[0].endswith("/issues/7800"):
                return {"state": "open"}
            if len(args) == 1 and "comments?" in args[0]:
                return []
            if len(args) == 5 and args[0] == "-X":
                return {"id": 1}
            raise AssertionError(args)
        self.assertIn("reaction recorded", react(d, "chidionyema/idp", gh=gh))
        self.assertEqual(len(calls), 3)
        self.assertIn(d.fingerprint, calls[-1][-1])

    def test_closed_or_unknown_incident_refuses_mutation(self):
        d = classify({"history": [row("b1"), row("b2", lane="lane/b")]}, POLICY)
        with self.assertRaises(RuntimeError):
            react(d, "chidionyema/idp", gh=lambda *a: {"state": "closed"})

if __name__ == "__main__":
    unittest.main()
