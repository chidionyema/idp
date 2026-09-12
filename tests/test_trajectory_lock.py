# tests/test_trajectory_lock.py — the Teleological Firewall: an agent may not wander off the ticket.
#
# Why this exists (founder 2026-09-12, and measured the same day). Teleology is the study of goals.
# The failure this gate stops is cognitive drift, not dishonesty: an agent told to "add a button to
# the UI" sees a deprecation warning, tries to fix the hook, breaks a test, tries to fix the test
# framework, needs a Node upgrade -- and forty-five minutes and 80,000 tokens later the button was
# never added.
#
# It is measured, not hypothesised. On 2026-09-12 this session's stated goal was "fix the gates,
# fix the class they exposed, do no more than that". A grep of its own transcript (1,727,505 bytes)
# counts treewalk 169 references (the actual work) against rule-guard 51, pi/agent/extensions 39 and
# addopts/-n auto 66 -- all drift. The founder stopped it twice by hand:
# "dont drift into things nonya business" and "stop driftih".
#
# A prompt cannot fix this. Attention is weighted toward the most recent tokens, so the most recent
# error message out-competes the original objective by construction. The harness must refuse.
#
# The spec is checkpoints/EPISTEMIC-GATE-TICKET.md Part 2. Four mechanisms, one test class each.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "bin"))


@pytest.fixture
def lock():
    import trajectory_lock

    return trajectory_lock


# ---------------------------------------------------------------------------
# 1. The bounded goal stack: no declared plan, no work.
# ---------------------------------------------------------------------------


class TestTheBoundedGoalStack:
    def test_a_session_with_no_declared_plan_may_not_run_a_tool(self, lock):
        loc = lock.TrajectoryLock()
        verdict = loc.authorize("bash", {"command": "ls"}, session_id="s1")
        assert verdict["allowed"] is False
        assert verdict["code"] == 403
        assert "plan" in verdict["reason"].lower()

    def test_declaring_a_plan_enables_work(self, lock):
        """A declared plan is what unlocks work -- and every call is still bound to a goal.

        Binding is not optional: an unbound call is drift by definition, which is the whole
        mechanism. Before the plan, nothing is authorised; after it, only calls naming a goal on
        the plan are.
        """
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan(
            "s1",
            goal="add a button to the settings page",
            subgoals=[{"id": "goal_1", "text": "add the button component"}],
        )
        assert plan["accepted"] is True
        assert (
            loc.authorize("bash", {"command": "ls"}, session_id="s1")["allowed"]
            is False
        )
        assert (
            loc.authorize(
                "bash", {"command": "ls"}, session_id="s1", target_goal_id="goal_1"
            )["allowed"]
            is True
        )

    def test_a_plan_with_no_subgoals_is_refused(self, lock):
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan("s1", goal="something", subgoals=[])
        assert plan["accepted"] is False
        assert "subgoal" in plan["reason"].lower()

    def test_a_plan_with_no_goal_is_refused(self, lock):
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan("s1", goal="", subgoals=[{"id": "goal_1", "text": "x"}])
        assert plan["accepted"] is False


# ---------------------------------------------------------------------------
# 2. Tool-to-goal binding: an action that serves no active goal is refused.
# ---------------------------------------------------------------------------


class TestToolToGoalBinding:
    def test_an_action_bound_to_the_active_goal_is_allowed(self, lock):
        loc = lock.TrajectoryLock()
        loc.declare_plan(
            "s1", "add a button", [{"id": "goal_1", "text": "add the button"}]
        )
        v = loc.authorize(
            "bash",
            {"command": "touch button.tsx"},
            session_id="s1",
            target_goal_id="goal_1",
        )
        assert v["allowed"] is True

    def test_an_action_naming_an_unknown_goal_is_refused(self, lock):
        """The React-hook rabbit hole: work bound to a goal that is not on the plan."""
        loc = lock.TrajectoryLock()
        loc.declare_plan(
            "s1", "add a button", [{"id": "goal_1", "text": "add the button"}]
        )
        v = loc.authorize(
            "bash",
            {"command": "npm i -g node@20"},
            session_id="s1",
            target_goal_id="goal_9",
        )
        assert v["allowed"] is False
        assert v["code"] == 403
        assert "goal_1" in v["reason"], "the refusal must name the goal to return to"

    def test_an_action_with_no_goal_binding_is_refused_once_planned(self, lock):
        loc = lock.TrajectoryLock()
        loc.declare_plan(
            "s1", "add a button", [{"id": "goal_1", "text": "add the button"}]
        )
        v = loc.authorize("bash", {"command": "rm -rf node_modules"}, session_id="s1")
        assert v["allowed"] is False
        assert v["code"] == 403

    def test_the_refusal_says_trajectory_drift(self, lock):
        loc = lock.TrajectoryLock()
        loc.declare_plan(
            "s1", "add a button", [{"id": "goal_1", "text": "add the button"}]
        )
        v = loc.authorize(
            "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_9"
        )
        assert "Trajectory Drift" in v["reason"]


# ---------------------------------------------------------------------------
# 3. The micro-budget kill switch: a budget per sub-goal, not per session.
# ---------------------------------------------------------------------------


class TestTheMicroBudgetKillSwitch:
    def test_a_goal_is_halted_after_its_budget_of_calls(self, lock):
        loc = lock.TrajectoryLock(budget_per_goal=3)
        loc.declare_plan(
            "s1", "add a button", [{"id": "goal_1", "text": "add the button"}]
        )
        for i in range(3):
            v = loc.authorize(
                "bash",
                {"command": f"attempt {i}"},
                session_id="s1",
                target_goal_id="goal_1",
            )
            assert v["allowed"] is True, f"attempt {i} should be inside the budget"
        v = loc.authorize(
            "bash", {"command": "attempt 4"}, session_id="s1", target_goal_id="goal_1"
        )
        assert v["allowed"] is False
        assert v["halt"] is True
        assert "revise_plan" in v["reason"] or "escalate" in v["reason"]

    def test_the_budget_is_per_goal_not_per_session(self, lock):
        """Two goals each get their own budget; one goal's exhaustion does not stop the other."""
        loc = lock.TrajectoryLock(budget_per_goal=2)
        loc.declare_plan(
            "s1",
            "two things",
            [{"id": "goal_1", "text": "a"}, {"id": "goal_2", "text": "b"}],
        )
        for _ in range(2):
            loc.authorize(
                "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
            )
        assert (
            loc.authorize(
                "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
            )["allowed"]
            is False
        )
        assert (
            loc.authorize(
                "bash", {"command": "y"}, session_id="s1", target_goal_id="goal_2"
            )["allowed"]
            is True
        )

    def test_completing_a_goal_frees_the_agent_to_the_next(self, lock):
        loc = lock.TrajectoryLock(budget_per_goal=1)
        loc.declare_plan(
            "s1",
            "two things",
            [{"id": "goal_1", "text": "a"}, {"id": "goal_2", "text": "b"}],
        )
        loc.authorize(
            "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
        )
        assert (
            loc.authorize(
                "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
            )["allowed"]
            is False
        )
        assert loc.complete_goal("s1", "goal_1") is True
        assert (
            loc.authorize(
                "bash", {"command": "y"}, session_id="s1", target_goal_id="goal_2"
            )["allowed"]
            is True
        )


# ---------------------------------------------------------------------------
# 4. Forced context pruning: the amnesia cure, and its fence.
# ---------------------------------------------------------------------------


class TestForcedContextPruning:
    def _turns(self, n_failed: int, goal: str = "add a button to the settings page"):
        turns = [
            {
                "role": "user",
                "content": [{"type": "text", "text": f"the goal is: {goal}"}],
            },
        ]
        for i in range(n_failed):
            turns.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "bash",
                            "input": {"command": f"fail {i}"},
                        }
                    ],
                }
            )
            turns.append(
                {"role": "tool", "content": [{"type": "text", "text": f"error {i}"}]}
            )
        return turns

    def test_three_consecutive_failures_triggers_pruning(self, lock):
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan(
            "s1",
            "add a button to the settings page",
            [{"id": "goal_1", "text": "add it"}],
        )
        turns = self._turns(3)
        out = loc.prune("s1", turns, goal=plan["goal"])
        assert out["pruned"] is True
        assert out["removed"] >= 3

    def test_the_objective_is_reinjected_at_the_bottom_of_the_window(self, lock):
        """The original goal must sit in the freshest position, not the oldest."""
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan(
            "s1",
            "add a button to the settings page",
            [{"id": "goal_1", "text": "add it"}],
        )
        out = loc.prune("s1", self._turns(3), goal=plan["goal"])
        assert out["pruned"] is True
        last_text = str(out["messages"][-1])
        assert "add a button to the settings page" in last_text
        assert "Trajectory Drift Detected" in last_text

    def test_two_failures_does_not_prune(self, lock):
        """Below the threshold the agent may still be solving it. Pruning is not free."""
        loc = lock.TrajectoryLock()
        loc.declare_plan("s1", "add a button", [{"id": "goal_1", "text": "add it"}])
        out = loc.prune("s1", self._turns(2), goal="add a button")
        assert out["pruned"] is False
        assert out["messages"] == self._turns(2)

    def test_pruning_never_removes_successful_tool_calls(self, lock):
        """The fence: only turns recorded as failed may be pruned, so evidence survives."""
        loc = lock.TrajectoryLock()
        loc.declare_plan("s1", "add a button", [{"id": "goal_1", "text": "add it"}])
        turns = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "bash",
                        "input": {"command": "git log --oneline -3"},
                    }
                ],
            },
            {
                "role": "tool",
                "content": [{"type": "text", "text": "abc123 did the thing"}],
            },
        ] + self._turns(3)
        out = loc.prune("s1", turns, goal="add a button")
        joined = str(out["messages"])
        assert "git log --oneline -3" in joined, (
            "a successful call is evidence and must survive"
        )


# ---------------------------------------------------------------------------
# R38: a guard that refuses correct work is an outage. These must all be allowed.
# ---------------------------------------------------------------------------


class TestTheLockDoesNotRefuseCorrectWork:
    def test_a_plan_declaration_is_always_allowed(self, lock):
        loc = lock.TrajectoryLock()
        plan = loc.declare_plan("s1", "do a thing", [{"id": "goal_1", "text": "it"}])
        assert plan["accepted"] is True

    def test_revise_plan_is_always_allowed_even_when_halted(self, lock):
        """The escape hatch must not itself be blocked, or the agent is trapped."""
        loc = lock.TrajectoryLock(budget_per_goal=1)
        loc.declare_plan("s1", "x", [{"id": "goal_1", "text": "y"}])
        loc.authorize(
            "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
        )
        assert (
            loc.authorize(
                "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
            )["allowed"]
            is False
        )
        v = loc.authorize("revise_plan", {}, session_id="s1")
        assert v["allowed"] is True

    def test_escalate_is_always_allowed_even_when_halted(self, lock):
        loc = lock.TrajectoryLock(budget_per_goal=1)
        loc.declare_plan("s1", "x", [{"id": "goal_1", "text": "y"}])
        loc.authorize(
            "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
        )
        loc.authorize(
            "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
        )
        assert (
            loc.authorize("escalate", {"why": "stuck"}, session_id="s1")["allowed"]
            is True
        )

    def test_an_unplanned_session_is_not_halted_explained(self, lock):
        """The refusal must tell the agent what to do, not just say no."""
        loc = lock.TrajectoryLock()
        v = loc.authorize("bash", {"command": "ls"}, session_id="s1")
        assert v["allowed"] is False
        assert "declare_plan" in v["reason"]

    def test_sessions_are_independent(self, lock):
        loc = lock.TrajectoryLock()
        loc.declare_plan("s1", "a", [{"id": "goal_1", "text": "x"}])
        assert (
            loc.authorize(
                "bash", {"command": "x"}, session_id="s1", target_goal_id="goal_1"
            )["allowed"]
            is True
        )
        assert (
            loc.authorize("bash", {"command": "x"}, session_id="s2")["allowed"] is False
        )


# ---------------------------------------------------------------------------
# CLI: grade a transcript after the fact, the way the epistemic gate does.
# ---------------------------------------------------------------------------


class TestExitCodes:
    def test_clean_is_exit_0(self, lock, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(
            '{"type":"message","role":"assistant","content":[{"type":"tool_use","name":"declare_plan",'
            '"input":{"goal":"add a button","subgoals":[{"id":"goal_1","text":"add it"}]}}]}\n'
        )
        assert lock.main([str(p)]) == 0

    def test_drift_is_exit_1(self, lock, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(
            '{"type":"message","role":"assistant","content":[{"type":"text","text":"I need to upgrade '
            'Node to fix the React hook."}]}\n'
        )
        assert lock.main([str(p)]) == 1

    def test_blind_is_exit_2(self, lock, tmp_path):
        assert lock.main([str(tmp_path / "nope.jsonl")]) == 2
