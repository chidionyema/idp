"""unittest for sovereign/engine/fsm.py (R28, R30). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_fsm -v

Rungs: property (no reachable path leaves the declared state set; the
cycle counter halts at exactly max_cycles) and one differential case
(engine/workflow.py's inline advance must agree with this module, so the
workflow and the machine cannot drift apart).
"""
from __future__ import annotations

import random
import unittest

from sovereign import config
from sovereign.engine import fsm


class FsmPropertyTest(unittest.TestCase):
    def test_property_no_sequence_of_legal_moves_leaves_the_declared_states(self) -> None:
        rng = random.Random(20260825)
        for _ in range(200):
            m = fsm.FSM(max_cycles=rng.randint(1, 8))
            for _ in range(rng.randint(1, 40)):
                target = rng.choice(list(fsm.STATES) + list(fsm.ALIASES) + ["nonsense"])
                try:
                    m.transition(target)
                except (fsm.IllegalTransition, fsm.CyclePause):
                    pass
                self.assertIn(m.state, fsm.STATES)
                self.assertLessEqual(m.cycles, m.max_cycles)

    def test_property_the_machine_halts_after_exactly_max_cycles(self) -> None:
        """R30: cycle detection halts after 5 repeats. 5 is
        config.fsm.max_cycles, not a literal in the code, so the property
        is stated over any limit."""
        for limit in range(1, 7):
            m = fsm.FSM(max_cycles=limit)
            m.advance()  # init -> planning
            completed = 0
            while True:
                try:
                    m.advance()
                except fsm.CyclePause:
                    break
                if m.state == fsm.CYCLE_PATH[0]:
                    completed = m.cycles
            self.assertEqual(completed, limit)
            self.assertTrue(m.paused)
            self.assertEqual(m.state, fsm.CYCLE_PATH[-1], "a paused machine waits where it stopped")

    def test_the_default_limit_is_the_spec_number(self) -> None:
        self.assertEqual(config.FSM_MAX_CYCLES, 5)
        self.assertEqual(fsm.STATES, ("init", "planning", "tool_use", "synthesis", "terminal"))

    def test_aliases_resolve_the_older_names(self) -> None:
        """The crew#200 table calls the middle states executing/verifying;
        spec line 299 and the cp31 feature call them tool_use/synthesis.
        Both dialects resolve to one machine rather than two."""
        self.assertEqual(fsm.canonical("executing"), "tool_use")
        self.assertEqual(fsm.canonical("verifying"), "synthesis")

    def test_terminal_is_terminal(self) -> None:
        m = fsm.FSM()
        m.advance()
        m.finish()
        self.assertEqual(m.state, fsm.TERMINAL)
        with self.assertRaises(fsm.IllegalTransition):
            m.transition("planning")


class FsmDifferentialTest(unittest.TestCase):
    """The workflow advances its own fsm_state field so that the Temporal
    sandbox never has to import this module's config. That duplication is
    exactly how two state machines drift, so this pins them together."""

    def test_workflow_state_order_matches_the_module(self) -> None:
        from sovereign.engine import workflow

        self.assertEqual(tuple(workflow.FSM_STATES), fsm.STATES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
