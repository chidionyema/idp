"""unittest for sovereign/engine/budget.py (R29). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_budget -v

Rungs: property (cp31's own words -- "the final balance equals start minus
both spends, and is never negative" -- over many random spend sequences,
including concurrent ones from real threads) and one incident case (a
spend larger than the balance halts at exactly zero instead of going
negative).
"""
from __future__ import annotations

import random
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import budget


class BudgetTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        p = patch.object(config, "BUDGET_DB", Path(self._tmp.name) / "budget.db")
        p.start()
        self.addCleanup(p.stop)


class BudgetPropertyTest(BudgetTestBase):
    def test_property_balance_is_start_minus_spends_and_never_negative(self) -> None:
        rng = random.Random(20260825)
        for i in range(60):
            sid = f"s{i}"
            start = rng.randint(0, 5000)
            budget.allocate(sid, start)
            taken = 0
            for _ in range(rng.randint(1, 15)):
                want = rng.randint(0, 900)
                res = budget.spend(sid, want)
                taken += res.spent
                self.assertGreaterEqual(res.remaining, 0)
                self.assertEqual(res.remaining, start - taken)
            self.assertEqual(budget.read(sid).remaining, max(start - taken, 0))

    def test_property_two_threads_spending_at_once_lose_nothing_and_invent_nothing(self) -> None:
        """Optimistic locking is only interesting under contention: two
        writers reading the same version, one of them losing the swap and
        retrying. Without the retry loop this test double-spends."""
        for trial in range(5):
            sid = f"race{trial}"
            start = 1000
            budget.allocate(sid, start)
            results: list[budget.Spend] = []
            lock = threading.Lock()

            def worker(amount: int) -> None:
                r = budget.spend(sid, amount)
                with lock:
                    results.append(r)

            threads = [threading.Thread(target=worker, args=(a,)) for a in (300, 400, 250, 200)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            total_taken = sum(r.spent for r in results)
            self.assertEqual(budget.read(sid).remaining, start - total_taken)
            self.assertEqual(total_taken, min(start, 300 + 400 + 250 + 200))
            self.assertGreaterEqual(budget.read(sid).remaining, 0)


class BudgetIncidentTest(BudgetTestBase):
    def test_incident_a_spend_larger_than_the_balance_halts_at_zero(self) -> None:
        budget.allocate("s", 10)
        res = budget.spend("s", 999)
        self.assertEqual(res.spent, 10)
        self.assertEqual(res.remaining, 0)
        self.assertTrue(res.halted, "hard halt at zero is the spec's word, not a warning")
        again = budget.spend("s", 1)
        self.assertEqual(again.spent, 0)
        self.assertEqual(again.remaining, 0)

    def test_allocate_is_idempotent_so_a_replay_cannot_refill(self) -> None:
        budget.allocate("s", 100)
        budget.spend("s", 60)
        budget.allocate("s", 100)
        self.assertEqual(budget.read("s").remaining, 40)

    def test_refill_raises_the_balance_and_lifts_the_halt(self) -> None:
        budget.allocate("s", 5)
        budget.spend("s", 5)
        self.assertTrue(budget.read("s").halted)
        budget.refill("s", 50)
        self.assertFalse(budget.read("s").halted)
        self.assertEqual(budget.read("s").remaining, 50)

    def test_an_unknown_session_is_halted_not_infinite(self) -> None:
        res = budget.spend("never-allocated", 10)
        self.assertEqual(res.spent, 0)
        self.assertTrue(res.halted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
