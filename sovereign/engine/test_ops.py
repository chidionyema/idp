"""unittest for sovereign/engine/ops.py (R9). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_ops -v

Rungs: property (every op in the tables classifies, and the unknown branch
fails closed) and one incident case (fs_commit -- spec 2.3 L108 -- is
classified and budget-checked, which is the requirement itself).
"""
from __future__ import annotations

import unittest

from sovereign import config
from sovereign.engine import ops


class OpsPropertyTest(unittest.TestCase):
    def test_property_every_configured_op_classifies_and_costs_something_knowable(self) -> None:
        for name in list(config.OPS_NONDESTRUCTIVE) + list(config.OPS_DESTRUCTIVE):
            spec = ops.classify(name)
            self.assertIn(spec.classification, (ops.NONDESTRUCTIVE, ops.DESTRUCTIVE))
            self.assertGreaterEqual(spec.tokens, 0)

    def test_property_an_unknown_op_fails_closed(self) -> None:
        """The estate's own scar: "a bare return on the unknown branch
        dropped 10 criticals in 18 hours and no test failed"."""
        for name in ("", "rm_rf", "not_a_real_op", "fs_commit_v2"):
            spec = ops.classify(name)
            self.assertTrue(spec.destructive, f"{name!r} must be treated as destructive")
            self.assertTrue(spec.needs_quorum)
            self.assertEqual(spec.classification, ops.UNKNOWN_CLASS)

    def test_an_op_name_is_matched_without_case_or_padding(self) -> None:
        """A caller that upper-cases or pads a name must not fall into the
        unknown branch and be refused work it is allowed to do (LAW 38)."""
        self.assertEqual(ops.classify(" FS_COMMIT ").classification, ops.NONDESTRUCTIVE)


class FsCommitIncidentTest(unittest.TestCase):
    def test_incident_fs_commit_is_classified_and_budget_checked(self) -> None:
        spec = ops.classify("fs_commit")
        self.assertEqual(spec.classification, ops.NONDESTRUCTIVE)
        self.assertFalse(spec.needs_quorum)
        self.assertFalse(spec.needs_hardware_signature)

        rich = ops.check("fs_commit", spec.tokens)
        self.assertTrue(rich.allowed)
        self.assertEqual(rich.verdict, ops.ALLOW)
        self.assertEqual(rich.remaining_after, 0)

        broke = ops.check("fs_commit", spec.tokens - 1)
        self.assertFalse(broke.allowed)
        self.assertEqual(broke.verdict, ops.REFUSE_BUDGET)
        self.assertTrue(broke.reason, "a refusal without a reason cannot be written into a receipt")

    def test_a_destructive_op_needs_more_than_budget(self) -> None:
        spec = ops.classify("git_push_force")
        self.assertTrue(spec.destructive)
        self.assertTrue(spec.needs_quorum)
        self.assertTrue(spec.needs_hardware_signature)


if __name__ == "__main__":
    unittest.main(verbosity=2)
