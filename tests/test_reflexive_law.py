"""Reflexive Integrity / Law-Establishment self-application falsifiers.

Tests were committed BEFORE the implementation to prove the proposed law is
also exercised during its own creation. An author-provided trace can NEVER
establish law or mint authority even when structurally complete.
"""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "platform/estate/governance/reflexive_law.py"
SPEC = importlib.util.spec_from_file_location("genesis_reflexive_law", FILE)
law = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(law)
START = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)


def event(kind, step="", actor="law-author", minute=0, **other):
    d = {"kind": kind, "step": step, "actor": actor,
         "law_sha": "a" * 64,
         "at": (START + timedelta(minutes=minute)).isoformat(),
         "evidence_ref": "https://github.com/chidionyema/idp/commit/" + "b" * 40}
    d.update(other)
    return d


def trace():
    return [
        event("PROPOSED", minute=0),
        event("SELF_ADOPTED", minute=1),
        event("PREMORTEM", minute=2),
        event("STEP_PRECHECK", step="test", minute=3),
        event("FALSIFIER_COMMIT", step="test", minute=4),
        event("STEP_POSTCHECK", step="test", minute=5),
        event("BASELINE_FALSIFIER_FAILED", minute=6),
        event("STEP_PRECHECK", step="implementation", minute=7),
        event("IMPLEMENTATION_COMMIT", step="implementation", minute=8),
        event("STEP_POSTCHECK", step="implementation", minute=9),
        event("TESTS_PASSED", minute=10),
        event("INDEPENDENT_REVIEW", actor="independent-reviewer", minute=11),
        event("OPERATIONAL_PROBE", actor="independent-observer", minute=12),
    ]


class ReflexiveLawTests(unittest.TestCase):
    def evaluate(self, events):
        return law.evaluate(events, expected_law_sha="a" * 64)

    def test_complete_trace_is_candidate_not_authority(self):
        result = self.evaluate(trace())
        self.assertEqual(result["state"], "CANDIDATE_FOR_TRUSTED_ESTABLISHMENT")
        self.assertFalse(result["release_authority"])
        self.assertFalse(result["independently_verified"])

    def test_late_or_absent_self_adoption_cannot_be_cured_after_commit(self):
        for variant in ("absent", "late"):
            with self.subTest(variant=variant):
                t = trace()
                adopted = next(e for e in t if e["kind"] == "SELF_ADOPTED")
                t.remove(adopted)
                if variant == "late":
                    t.insert(8, adopted)
                self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_falsifier_must_exist_and_fail_before_implementation(self):
        for kind in ("FALSIFIER_COMMIT", "BASELINE_FALSIFIER_FAILED"):
            with self.subTest(kind=kind):
                t = [e for e in trace() if e["kind"] != kind]
                self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_every_mutation_requires_before_and_during_checkpoints(self):
        for kind in ("STEP_PRECHECK", "STEP_POSTCHECK"):
            with self.subTest(kind=kind):
                t = [e for e in trace() if not
                     (e["kind"] == kind and e["step"] == "implementation")]
                self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_second_unguarded_change_refused(self):
        t = trace()
        t.insert(10, event("IMPLEMENTATION_COMMIT", step="unobserved", minute=9.5))
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_self_review_is_not_independent(self):
        t = trace()
        next(e for e in t if e["kind"] == "INDEPENDENT_REVIEW")["actor"] = "law-author"
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_no_operational_witness_is_not_establishment(self):
        t = [e for e in trace() if e["kind"] != "OPERATIONAL_PROBE"]
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_recited_law_or_posthoc_tests_without_baseline_are_insufficient(self):
        t = [e for e in trace() if e["kind"] not in
             ("PREMORTEM", "BASELINE_FALSIFIER_FAILED")]
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_malformed_and_unsourced_events_are_refused(self):
        for field, value in (("law_sha", "wrong"), ("evidence_ref", ""),
                             ("at", "not-a-time"), ("actor", "")):
            t = trace()
            t[3][field] = value
            self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_nonmonotonic_timeline_refused(self):
        t = trace()
        t[8]["at"] = t[4]["at"]
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_duplicate_or_replayed_event_refused(self):
        t = trace()
        t.append(dict(t[-1]))
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_unknown_event_type_is_not_silently_ignored(self):
        t = trace()
        t.insert(7, event("AUTHOR_SAYS_APPROVED", minute=6.5))
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")

    def test_no_implementation_mutation_is_not_a_shipped_law(self):
        t = [e for e in trace() if e["kind"] != "IMPLEMENTATION_COMMIT"]
        self.assertEqual(self.evaluate(t)["state"], "NOT_ESTABLISHED")


if __name__ == "__main__":
    unittest.main()
