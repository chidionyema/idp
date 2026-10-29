import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "science"))
from science.core import Registry, digest  # noqa: E402
from science.cycle import run_cycle  # noqa: E402

P = {
    "question": "Can the small model do the task?",
    "hypothesis": "Harness improves verified completion",
    "null_hypothesis": "No improvement",
    "falsifier": "No positive delta on held-out tests",
    "primary_metric": "verified_completion_rate",
    "analysis_plan": "paired differences with bootstrap CI",
    "fixture_digest": "a" * 64,
    "verifier": "independent-test-suite",
    "budget_usd": 2,
    "max_seconds": 120,
    "risk_tier": "sandboxed",
}

FIXTURE = {
    "baseline": [0.4, 0.5, 0.45, 0.5, 0.42, 0.48, 0.51, 0.44],
    "treatment": [0.6, 0.62, 0.58, 0.66, 0.59, 0.63, 0.7, 0.61],
}


class Kernel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name + "/science.db"
        self.r = Registry(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def _to_analysed(self, actor="researcher"):
        i = self.r.register(P)["programme_id"]
        for s in ("preregistered", "running", "analysed"):
            self.r.transition(i, s, {"actor": actor, "evidence_id": s})
        return i

    def test_register_and_digest(self):
        p = self.r.register(P)
        self.assertEqual(self.r.get(p["programme_id"])["protocol_sha256"], digest(P))

    def test_rejects_bad_protocols(self):
        for bad in (
            {"question": "x"},
            dict(P, risk_tier="production"),
            dict(P, budget_usd=101),
            dict(P, max_seconds=0),
            dict(P, fixture_digest="zz"),
        ):
            with self.assertRaises(ValueError):
                self.r.register(bad)

    def test_illegal_transition(self):
        i = self.r.register(P)["programme_id"]
        with self.assertRaises(ValueError):
            self.r.transition(
                i, "independently_verified", {"actor": "a", "evidence_id": "e"}
            )

    def test_self_verification_read_from_log(self):
        i = self._to_analysed("researcher")
        self.r.append(i, "audit", {"ok": True}, "aud1")
        # the caller does not get to name the experimenter: omitting it must not bypass the check
        with self.assertRaises(ValueError):
            self.r.transition(
                i,
                "independently_verified",
                {
                    "actor": "researcher",
                    "evidence_id": "aud1",
                    "verifier_receipt_sha256": "b" * 64,
                },
            )

    def test_verification_must_cite_real_audit(self):
        i = self._to_analysed()
        with self.assertRaises(ValueError):
            self.r.transition(
                i,
                "independently_verified",
                {
                    "actor": "audit",
                    "evidence_id": "ghost",
                    "verifier_receipt_sha256": "b" * 64,
                },
            )

    def test_independent_verification(self):
        i = self._to_analysed()
        self.r.append(i, "audit", {"ok": True}, "aud1")
        self.assertEqual(
            self.r.transition(
                i,
                "independently_verified",
                {
                    "actor": "audit",
                    "evidence_id": "aud1",
                    "verifier_receipt_sha256": "b" * 64,
                },
            ),
            "independently_verified",
        )

    def test_evidence_immutable(self):
        i = self.r.register(P)["programme_id"]
        self.r.append(i, "measurement", {"x": 1}, "m1")
        db = sqlite3.connect(self.path)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE evidence SET payload='{}' WHERE id='m1'")
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM evidence WHERE id='m1'")
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE programmes SET protocol='{}' WHERE id=?", (i,))

    def test_append_idempotent_and_conflict(self):
        i = self.r.register(P)["programme_id"]
        self.r.append(i, "measurement", {"x": 1}, "same")
        self.assertTrue(self.r.append(i, "measurement", {"x": 1}, "same")["duplicate"])
        with self.assertRaises(ValueError):
            self.r.append(i, "measurement", {"x": 2}, "same")

    def test_concurrent_transition_exactly_one_wins(self):
        i = self.r.register(P)["programme_id"]
        results = []

        def go(n):
            r = Registry(self.path)
            try:
                results.append(
                    r.transition(
                        i, "preregistered", {"actor": f"w{n}", "evidence_id": f"e{n}"}
                    )
                )
            except ValueError as e:
                results.append(str(e))

        ts = [threading.Thread(target=go, args=(n,)) for n in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results.count("preregistered"), 1)
        transitions = [e for e in self.r.events(i) if e["kind"] == "state_transition"]
        self.assertEqual(
            len(transitions), 1
        )  # a lost race leaves no orphan evidence row

    def test_autonomous_cycle_verifies_independently(self):
        out = run_cycle(self.r, dict(P, fixture_digest=digest(FIXTURE)), FIXTURE)
        self.assertEqual(out["state"], "independently_verified")
        self.assertEqual(out["finding"]["conclusion"], "reject_null")
        self.assertNotEqual(
            self.r._experimenter(out["programme_id"]), "science-verifier"
        )

    def test_cycle_refuses_a_swapped_fixture(self):
        with self.assertRaises(ValueError):
            run_cycle(
                self.r,
                dict(P, fixture_digest=digest(FIXTURE)),
                dict(FIXTURE, treatment=[1] * 8),
            )


if __name__ == "__main__":
    unittest.main()
