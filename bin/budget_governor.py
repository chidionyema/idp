#!/usr/bin/env python3
"""The Test-Time Compute Budget: a governor that ends a reasoning loop before it becomes a bill.

Why this exists (founder essay 2026-09-14, "PhD cold military surgeon"): "Test-Time Compute
Budgeting... Per-query budget... Expected Information Gain threshold... Budget exhaustion ->
forced termination -- the agent stops thinking and executes the best-so-far plan when the
budget runs out."

Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D2. The ticket names what
already covers two of the three controls -- this governor unifies them, it does not rebuild them
(R43):

  bin/idp-trajectory        -- a per-goal branch budget (budget_per_goal, founder-fixed at 5;
                                the ticket's own default of "5 tree branches" IS this constant).
  bin/idp-execution-boundary -- the 60-second wall-clock ceiling, applied outside this process.

What this governor adds, deterministically, no model:

  cost ceiling      -- a running sum of each step's own declared cost_usd (never fabricated; a
                        step that names no cost costs 0), refused once it would cross
                        --max-cost-usd (default 0.50, the ticket's own number).
  information gain  -- a branch that repeats a (tool, target) pair already run this session
                        proves zero information gain by construction (the same normalisation
                        epistemic_firewall and the PRM sidecar use for independence). This is
                        the honest floor the ticket's own risk register names: "Information-gain
                        math needs an actual Bayesian engine. Without one, the threshold degrades
                        to 'looks plausible'." Repeat-vs-novel is provable; anything richer is
                        the open Bayesian-engine question the ticket leaves open.

The first of the three ceilings to trip halts the run. What survives is the best-so-far plan:
the declared goal, which subgoals are done, and how many steps and dollars it cost to get there
-- never a claim the run finished when it did not.

  bin/idp-budget --max-steps 5 --run <session.jsonl>   exit 0 plan complete, 1 halted, 2 BLIND
  bin/idp-budget --explain <session.jsonl>             names the ceiling that halted the run

The honest limit: this governs a fixed, recorded transcript, not a live decode loop -- there is
no second scheduler or bus here (THE HEADLINE). Wiring it to halt an in-flight agent takes the
identical decision this file already computes; it is not a second design.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from epistemic_firewall import (  # noqa: E402
    _estate_sessions,
    _is_tool_call_block,
    _target_of,
    _tool_input,
    _unwrap,
)
from trajectory_lock import ESCAPE_HATCHES, TrajectoryLock  # noqa: E402

DEFAULT_MAX_STEPS = 5
DEFAULT_MAX_COST_USD = 0.50
_SESSION_ID = "budget"


def _step_tool_calls(turn: dict) -> list[dict]:
    msg = _unwrap(turn)
    content = msg.get("content")
    blocks = content if isinstance(content, list) else []
    calls = [b for b in blocks if isinstance(b, dict) and _is_tool_call_block(b)]
    if not calls and _is_tool_call_block(msg):
        calls = [msg]
    return calls


def run_budget(
    turns: list[dict],
    max_steps: int = DEFAULT_MAX_STEPS,
    max_cost_usd: float = DEFAULT_MAX_COST_USD,
) -> dict:
    """Replay a transcript against the budget. Returns the best-so-far plan either way."""
    lock = TrajectoryLock(budget_per_goal=max_steps)
    evidence: set[str] = set()
    active_goal_id: str | None = None
    goal: str = ""
    subgoals: list[dict] = []
    done: set[str] = set()

    spent_steps = 0
    spent_usd = 0.0
    halted_at: int | None = None
    cause: str | None = None
    detail: str = ""

    for i, turn in enumerate(turns, start=1):
        if halted_at is not None:
            break
        if not isinstance(turn, dict):
            continue
        calls = _step_tool_calls(turn)

        plan_call = next(
            (
                c
                for c in calls
                if str(c.get("name", "")) in ("declare_plan", "revise_plan")
            ),
            None,
        )
        if plan_call is not None:
            inp = _tool_input(plan_call)
            result = lock.declare_plan(
                _SESSION_ID, inp.get("goal", ""), inp.get("subgoals", [])
            )
            if result.get("accepted"):
                goal = result["goal"]
                subgoals = inp.get("subgoals") or []
                active_goal_id = str(subgoals[0]["id"]) if subgoals else None
                done = set()
            continue

        complete_call = next(
            (c for c in calls if str(c.get("name", "")) == "complete_goal"),
            None,
        )
        if complete_call is not None:
            gid = str(_tool_input(complete_call).get("goal_id", ""))
            if lock.complete_goal(_SESSION_ID, gid):
                done.add(gid)
                active_goal_id = next(
                    (str(s["id"]) for s in subgoals if str(s["id"]) not in done), None
                )
            continue

        real_calls = [c for c in calls if str(c.get("name", "")) not in ESCAPE_HATCHES]
        for c in real_calls:
            piece = f"{c.get('name', '?')}:{_target_of(c)}"
            step_cost = float(_tool_input(c).get("cost_usd", 0.0) or 0.0)

            # -- information gain: a repeated (tool, target) pair proves zero new evidence.
            if piece in evidence:
                halted_at = i
                cause = "zero_information_gain"
                detail = f"{piece} already ran this session; the branch proves no new evidence"
                break

            # -- cost ceiling: a running sum of each step's own declared cost.
            if spent_usd + step_cost > max_cost_usd:
                halted_at = i
                cause = "cost_ceiling"
                detail = (
                    f"step would spend ${spent_usd + step_cost:.2f}, over the "
                    f"${max_cost_usd:.2f} per-query ceiling"
                )
                break

            # -- branch budget: bin/idp-trajectory's own per-goal count (the ticket's "5 tree
            # branches" IS budget_per_goal, imported rather than re-implemented -- R43).
            target_goal_id = _tool_input(c).get("target_goal_id") or active_goal_id
            result = lock.authorize(
                str(c.get("name", "")),
                _tool_input(c),
                _SESSION_ID,
                target_goal_id,
            )
            if not result["allowed"]:
                halted_at = i
                cause = "branch_budget" if result.get("halt") else "off_plan"
                detail = result["reason"]
                break

            evidence.add(piece)
            spent_usd += step_cost
            spent_steps += 1

        if halted_at is not None:
            break

    plan_complete = bool(subgoals) and done == {str(s["id"]) for s in subgoals}
    return {
        "goal": goal,
        "subgoals": [
            {"id": str(s["id"]), "done": str(s["id"]) in done} for s in subgoals
        ],
        "steps_spent": spent_steps,
        "usd_spent": round(spent_usd, 4),
        "max_steps": max_steps,
        "max_cost_usd": max_cost_usd,
        "halted": halted_at is not None,
        "halted_at_step": halted_at,
        "cause": cause,
        "detail": detail,
        "plan_complete": plan_complete,
    }


def _blind(why: str) -> dict:
    return {"blind": why}


def load_run(path: Path | str) -> tuple[list[dict] | None, dict | None]:
    p = Path(path)
    if not p.exists():
        return None, _blind(f"{p} does not exist")
    try:
        raw = p.read_text(errors="replace")
    except OSError as exc:
        return None, _blind(f"{p} could not be read: {exc}")
    turns: list[dict] = []
    for n, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            turns.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            return None, _blind(f"{p}:{n} is not valid JSON")
    return turns, None


def _sweep_estate(limit: int = 25) -> int:
    """The live case bin/idp-rules requires: replay the estate's own sessions, not only a fixture.

    Mirrors epistemic_firewall._grade_estate and prm_grader._grade_estate (R43): a session
    recorded before this governor existed had no budget applied live, so it is reported, never
    failed, on a bare sweep. Naming one session with --run/--explain still halts for real.
    """
    sessions = _estate_sessions()[:limit]
    if not sessions:
        print("ok    budget no session transcripts on this machine; nothing to sweep")
        return 0
    would_halt = 0
    for path in sessions:
        turns, blind = load_run(path)
        if blind:
            continue
        verdict = run_budget(turns)
        if verdict["halted"]:
            would_halt += 1
    print(
        f"ok    budget {len(sessions)} recent session(s) swept; {would_halt} would have halted "
        "under the default budget. Historical, reported not failed -- --run one by name to act on it."
    )
    return 0


def _usage() -> str:
    return (
        "usage: idp-budget --max-steps <n> [--max-cost-usd <f>] --run <session.jsonl>\n"
        "       idp-budget --explain <session.jsonl>\n"
        "       idp-budget --self-test\n"
        "       idp-budget --help"
    )


def _print_plan(verdict: dict, prefix: str) -> None:
    subs = (
        ", ".join(f"{s['id']}{'*' if s['done'] else ''}" for s in verdict["subgoals"])
        or "none"
    )
    print(
        f"{prefix} goal={verdict['goal'] or '(none declared)'} subgoals=[{subs}] "
        f"steps={verdict['steps_spent']}/{verdict['max_steps']} "
        f"cost=${verdict['usd_spent']:.2f}/${verdict['max_cost_usd']:.2f}"
    )


def _self_test() -> int:
    """LAW 45: this script has not run until --self-test proves it, against its own fixtures."""
    root = Path(__file__).resolve().parent.parent
    exhausted = root / "tests/fixtures/budget/exhausted/session.jsonl"
    complete = root / "tests/fixtures/budget/complete/session.jsonl"
    if not exhausted.exists() or not complete.exists():
        print(
            f"SKIP budget --self-test: fixtures not found under {root}/tests/fixtures/budget"
        )
        return 0
    turns_a, err_a = load_run(exhausted)
    turns_b, err_b = load_run(complete)
    if err_a or err_b:
        print(f"FAIL budget --self-test: {err_a or err_b}")
        return 1
    v_a = run_budget(
        turns_a, max_steps=DEFAULT_MAX_STEPS, max_cost_usd=DEFAULT_MAX_COST_USD
    )
    v_b = run_budget(
        turns_b, max_steps=DEFAULT_MAX_STEPS, max_cost_usd=DEFAULT_MAX_COST_USD
    )
    if not v_a["halted"]:
        print(f"FAIL budget --self-test: {exhausted} should have halted and did not")
        return 1
    if v_b["halted"]:
        print(
            f"FAIL budget --self-test: {complete} should have completed and halted instead"
        )
        return 1
    print(
        "ok   budget --self-test: exhausted fixture halts, complete fixture finishes clean"
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("--help", "-h"):
        print(_usage())
        return 0
    if len(argv) > 1 and argv[1] == "--self-test":
        return _self_test()

    max_steps = DEFAULT_MAX_STEPS
    max_cost_usd = DEFAULT_MAX_COST_USD
    mode: str | None = None
    path: str | None = None

    args = argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--max-steps":
            i += 1
            max_steps = int(args[i])
        elif a == "--max-cost-usd":
            i += 1
            max_cost_usd = float(args[i])
        elif a == "--run":
            i += 1
            mode = "run"
            path = args[i]
        elif a == "--explain":
            i += 1
            mode = "explain"
            path = args[i]
        else:
            path = path or a
        i += 1

    if not mode or not path:
        if not args:
            # No mode named at all: sweep the estate's own sessions (the live case
            # bin/idp-rules requires), matching prm/epistemic's bare-invocation convention.
            return _sweep_estate()
        print(_usage(), file=sys.stderr)
        return 2

    turns, blind = load_run(path)
    if blind:
        print(f"BLIND budget {blind['blind']}", file=sys.stderr)
        return 2

    verdict = run_budget(turns, max_steps=max_steps, max_cost_usd=max_cost_usd)

    if mode == "explain":
        if verdict["halted"]:
            print(
                f"halted at step {verdict['halted_at_step']}: {verdict['cause']} -- {verdict['detail']}"
            )
        else:
            print(
                "not halted: the plan completed inside its budget"
                if verdict["plan_complete"]
                else "not halted: budget was never reached"
            )
        _print_plan(verdict, "      best-so-far:")
        return 0

    if verdict["halted"]:
        print(
            f"FAIL  budget halted at step {verdict['halted_at_step']} ({verdict['cause']}): "
            f"{verdict['detail']}",
            file=sys.stderr,
        )
        _print_plan(verdict, "      best-so-far:")
        return 1

    print(
        f"ok    budget plan {'complete' if verdict['plan_complete'] else 'ran clean'} inside budget"
    )
    _print_plan(verdict, "      ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
