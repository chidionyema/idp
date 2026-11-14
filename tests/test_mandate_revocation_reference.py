"""Isolated reference oracle, NOT evidence of estate effect-door enforcement."""
import unittest
from dataclasses import dataclass

@dataclass(frozen=True)
class Mandate:
    version: int
    epoch: int

class ReferenceDoor:
    def __init__(self):
        self.current = Mandate(7, 7)
        self.effects = []
        self.denied = []

    def activate(self, nxt):
        if nxt.epoch <= self.current.epoch:
            raise ValueError("nonmonotonic epoch")
        self.current = nxt

    def commit(self, mandate, effect_id, *, enforce=True):
        # Real implementation must enforce authority atomically with actual effect.
        if enforce and mandate != self.current:
            self.denied.append(effect_id)
            return False
        if effect_id not in self.effects:
            self.effects.append(effect_id)
        return True

class MandateRevocationReferenceTests(unittest.TestCase):
    def test_revoked_worker_denied_and_successor_allowed(self):
        door = ReferenceDoor()
        old = door.current
        door.activate(Mandate(8, 8))
        self.assertFalse(door.commit(old, "delayed-A"))
        self.assertEqual(door.effects, [])
        self.assertEqual(door.denied, ["delayed-A"])
        self.assertTrue(door.commit(door.current, "authorised-B"))
        self.assertEqual(door.effects, ["authorised-B"])

    def test_replay_and_epoch_regression_rejected(self):
        door = ReferenceDoor()
        old = door.current
        door.activate(Mandate(8, 8))
        with self.assertRaises(ValueError):
            door.activate(old)
        self.assertFalse(door.commit(old, "replay"))

    def test_effect_idempotency(self):
        door = ReferenceDoor()
        self.assertTrue(door.commit(door.current, "once"))
        self.assertTrue(door.commit(door.current, "once"))
        self.assertEqual(door.effects, ["once"])

    def test_mutation_exposes_missing_fence(self):
        door = ReferenceDoor()
        old = door.current
        door.activate(Mandate(8, 8))
        self.assertTrue(door.commit(old, "forbidden", enforce=False))
        self.assertIn("forbidden", door.effects)
        self.assertFalse(door.commit(old, "blocked", enforce=True))
        self.assertNotIn("blocked", door.effects)

if __name__ == "__main__":
    unittest.main()
