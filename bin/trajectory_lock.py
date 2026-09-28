#!/usr/bin/env python3
"""The Teleological Firewall (the Trajectory Lock): an agent may not wander off the ticket.

Teleology is the study of goals. The failure this stops is cognitive drift, not dishonesty: an agent
told to "add a button to the UI" sees a deprecation warning, tries to fix the hook, breaks a test,
tries to fix the test framework, needs a Node upgrade -- and forty-five minutes and 80,000 tokens
later the button was never added.

Why this exists (founder 2026-09-12). It is measured in this estate, not hypothesised. On
2026-09-12 this session's stated goal was "fix the gates, fix the class they exposed, do no more
than that". A grep of its own transcript (1,727,505 bytes) counts treewalk 169 references -- the
actual work -- against rule-guard 51, pi/agent/extensions 39 and addopts/-n auto 66: all drift. The
founder stopped it twice by hand ("dont drift into things nonya business", "stop driftih").

A prompt cannot fix this. Attention is weighted toward the most recent tokens, so the most recent
error message out-competes the original objective by construction. The harness must refuse. This is
the second half of the pair begun in bin/epistemic_firewall.py:

  epistemic   -- the agent cannot lie about what it sees
  teleological -- the agent cannot forget what it was told to do

Both read the same transcript, and the fence between them is real: forced context pruning edits the
agent's memory, so it may prune only turns recorded as FAILED, and never one the epistemic gate
would need to grade a claim.

  bin/trajectory_lock.py <session.jsonl>   exit 0 clean, 1 drift, 2 BLIND

The honest limit: this bounds the corridor, it does not choose the goal. A plan that is itself wrong
is followed faithfully; the lock ensures the agent reaches the end of what it declared, not that what
it declared was right.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# The escape hatches. These must NEVER be blocked, or a halted agent is trapped with no way to say
# so -- a guard that refuses correct work is an outage (AGENTS.md R38).
ESCAPE_HATCHES = frozenset({"declare_plan", "revise_plan", "escalate"})

# Three consecutive failures is the threshold at which an agent is looping rather than solving.
# Below it, the failures may still be progress, and pruning is not free.
DRIFT_THRESHOLD = 3

DRIFT_MARKER = "[SYSTEM: Trajectory Drift Detected."


class TrajectoryLock:
    """The state machine for one or more sessions, each locked to a declared plan."""

    def __init__(self, budget_per_goal: int = 5) -> None:
        self.budget_per_goal = budget_per_goal
        self._plans: dict[str, dict[str, Any]] = {}
        self._spent: dict[str, dict[str, int]] = {}
        self._done: dict[str, set[str]] = {}

    # -- 1. The bounded goal stack -------------------------------------------------------------

    def declare_plan(self, session_id: str, goal: str, subgoals: list[dict]) -> dict:
        """A plan is a goal and at least one sub-goal. Without one, no tool call is authorised."""
        if not goal or not str(goal).strip():
            return {"accepted": False, "reason": "a plan needs a goal"}
        if not subgoals:
            return {"accepted": False, "reason": "a plan needs at least one subgoal"}
        ids = [str(s.get("id", "")).strip() for s in subgoals]
        if any(not i for i in ids):
            return {"accepted": False, "reason": "every subgoal needs an id"}
        if len(set(ids)) != len(ids):
            return {"accepted": False, "reason": "subgoal ids must be unique"}

        self._plans[session_id] = {"goal": str(goal).strip(), "subgoals": subgoals}
        self._spent[session_id] = {i: 0 for i in ids}
        self._done[session_id] = set()
        return {
            "accepted": True,
            "goal": self._plans[session_id]["goal"],
            "subgoals": subgoals,
        }

    def revise_plan(self, session_id: str, goal: str, subgoals: list[dict]) -> dict:
        """Re-declaring replaces the plan and clears its budgets. The escape hatch."""
        return self.declare_plan(session_id, goal, subgoals)

    def _active_goal(self, session_id: str) -> str | None:
        """The first uncompleted sub-goal, or None when the plan is done."""
        plan = self._plans.get(session_id)
        if not plan:
            return None
        done = self._done.get(session_id, set())
        for s in plan["subgoals"]:
            if str(s["id"]) not in done:
                return str(s["id"])
        return None

    # -- 2 and 3. Binding, and the per-goal budget ---------------------------------------------

    def authorize(
        self,
        tool: str,
        args: dict | None,
        session_id: str,
        target_goal_id: str | None = None,
    ) -> dict:
        """Decide whether this tool call serves the active goal. The choke point."""
        args = args or {}

        # The escape hatches are never blocked. A trapped agent cannot report being trapped.
        if tool in ESCAPE_HATCHES:
            return {"allowed": True, "code": 200, "reason": ""}

        plan = self._plans.get(session_id)
        if not plan:
            return {
                "allowed": False,
                "code": 403,
                "reason": (
                    "no plan declared. Call declare_plan first: a goal and at least one subgoal. "
                    "An agent may not begin work without a contract."
                ),
            }

        active = self._active_goal(session_id)
        if active is None:
            return {
                "allowed": False,
                "code": 403,
                "reason": "every subgoal is complete. Call revise_plan to declare what is next.",
            }

        # Binding: the action must name a goal that is ON the plan. Required always -- an unbound
        # call is drift by definition, which is the mechanism, not an inconvenience to smooth over.
        known = {str(s["id"]) for s in plan["subgoals"]}
        if target_goal_id is None:
            return {
                "allowed": False,
                "code": 403,
                "reason": (
                    f"Trajectory Drift: {tool} names no target_goal_id. Bind the call to "
                    f"`{active}` or return to it. The objective is: {plan['goal']}"
                ),
            }
        if target_goal_id not in known:
            return {
                "allowed": False,
                "code": 403,
                "reason": (
                    f"Trajectory Drift: {target_goal_id} is not on this plan. Return to `{active}`. "
                    f"The objective is: {plan['goal']}"
                ),
            }

        # The budget, counted per goal. This is what stops a loop becoming a bill.
        spent = self._spent.setdefault(session_id, {}).get(target_goal_id, 0)
        if spent >= self.budget_per_goal:
            return {
                "allowed": False,
                "code": 403,
                "halt": True,
                "reason": (
                    f"budget exhausted for {target_goal_id} ({spent}/{self.budget_per_goal}). "
                    "You are spinning. Execute revise_plan, or escalate to a human."
                ),
            }

        self._spent[session_id][target_goal_id] = spent + 1
        return {"allowed": True, "code": 200, "reason": ""}

    def complete_goal(self, session_id: str, goal_id: str) -> bool:
        plan = self._plans.get(session_id)
        if not plan or goal_id not in {str(s["id"]) for s in plan["subgoals"]}:
            return False
        self._done.setdefault(session_id, set()).add(goal_id)
        return True

    # -- 4. Forced context pruning --------------------------------------------------------------

    def prune(self, session_id: str, messages: list[dict], goal: str) -> dict:
        """Erase the failed turns and re-inject the objective at the bottom of the window.

        The fence: only turns recorded as FAILED may be removed. A successful tool call is
        evidence -- the epistemic gate grades claims against it (bin/epistemic_firewall.py) -- so
        it is never pruned, however old it is.
        """
        failures = self._failed_turns(session_id)
        consecutive = self._trailing_failures(messages, failures)
        if consecutive < DRIFT_THRESHOLD:
            return {"pruned": False, "removed": 0, "messages": messages}

        failed_indices, kept = self._drop_trailing_failures(
            messages, failures, consecutive
        )
        kept = kept + [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"{DRIFT_MARKER} Your recent attempts failed and have been erased to "
                            f"clear your context. The original objective is: {goal}. Re-evaluate "
                            "your approach from first principles.]"
                        ),
                    }
                ],
            }
        ]
        return {"pruned": True, "removed": len(failed_indices), "messages": kept}

    def _failed_turns(self, session_id: str) -> set[int]:
        """Indices this lock recorded as failed for the session. Empty unless recorded."""
        return (
            self._failures.get(session_id, set())
            if hasattr(self, "_failures")
            else set()
        )

    def record_failure(self, session_id: str, index: int) -> None:
        """Record that turn `index` failed. Only recorded turns are ever prunable."""
        if not hasattr(self, "_failures"):
            self._failures: dict[str, set[int]] = {}
        self._failures.setdefault(session_id, set()).add(index)

    def _trailing_failures(self, messages: list[dict], failures: set[int]) -> int:
        """How many failed ATTEMPTS sit at the end of the window, consecutively.

        One attempt is a tool call plus its output. Counting turns instead of attempts is the bug
        that fired the threshold two attempts early: a run of three failures is six turns, and
        three-of-six is not three consecutive failures. Only the turn whose own text carries the
        failure -- the output, or an index the lock recorded -- advances the count; a call in
        front of it belongs to the same attempt and does not.
        """
        n = 0
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if i in failures or self._is_error_output(msg):
                n += 1
            elif self._is_tool_call(msg):
                # The companion call of an attempt already counted. Not a failure of its own.
                continue
            else:
                break
        return n

    def _is_tool_call(self, msg: dict) -> bool:
        content = msg.get("content")
        if isinstance(content, list):
            return any(isinstance(b, dict) and _is_tool_call_block(b) for b in content)
        return False

    def _is_error_output(self, msg: dict) -> bool:
        text = str(msg).lower()
        return any(
            m in text
            for m in (
                "error",
                "failed",
                "traceback",
                "exit code 1",
                "not found",
                "cannot find",
            )
        )

    def _drop_trailing_failures(
        self, messages: list[dict], failures: set[int], consecutive: int
    ) -> tuple[list[int], list[dict]]:
        """Remove the trailing failed turns, never a successful tool call.

        Walks backwards over the trailing run the counter just measured, so the set removed and the
        count reported cannot disagree. A successful tool call -- one whose own text carries no
        error marker -- is kept wherever it sits, because the epistemic gate grades claims against
        exactly that evidence (bin/epistemic_firewall.py).
        """
        removed: list[int] = []
        kept = list(messages)
        idx = len(messages) - 1
        while len(removed) < consecutive and idx >= 0:
            msg = kept[idx]
            if self._is_successful_evidence(msg):
                idx -= 1
                continue
            kept.pop(idx)
            removed.append(idx)
            idx -= 1
        return removed, kept

    def _is_successful_evidence(self, msg: dict) -> bool:
        """A call or output with no error marker. Evidence: never pruned."""
        if self._is_error_output(msg):
            return False
        return self._is_tool_call(msg) or str(msg.get("content", "")).strip() != ""


# ---------------------------------------------------------------------------
# CLI: grade a transcript after the fact, as bin/epistemic_firewall.py does.
# ---------------------------------------------------------------------------


def _declared_subjects(turns: list[dict]) -> set[str]:
    """The words the agent's OWN declared plan is about.

    The lock does not need a list of known rabbit holes -- enumerating them is the guessing this
    gate exists to remove, and it only catches drift somebody already thought of. It needs the
    goal the agent wrote down and the subjects in it. Anything the session then acts on that shares
    no subject with that goal is, by construction, outside the plan.
    """
    subjects: set[str] = set()
    for turn in turns:
        for block in _blocks(turn):
            if _is_tool_call_block(block) and block.get("name") in ESCAPE_HATCHES:
                inp = _tool_input(block)
                text = f"{inp.get('goal', '')} " + " ".join(
                    str(s.get("text", "")) + " " + str(s.get("id", ""))
                    for s in (inp.get("subgoals") or [])
                )
                subjects |= _words(text)
    return subjects


_STOPWORDS = frozenset(
    """a an the and or of to in on for with by is are was were be been it its this that these
    those i my me we our you your they their then than so as at from into over under
    will shall going plan intend need want must should can could may might""".split()
)

# Verbs of action, not subjects. "wire treewalk into the gates" and "wire rule-guard into pi's
# extensions" share the verb `wire` and nothing else -- and that shared verb made this gate pass a
# real drift. Measured: the BDD scenario "an agent acts outside the plan it declared" graded PASS
# because both sentences contained `wire`. What a plan is ABOUT is its nouns: the things being
# changed. Matching on verbs is the same mistake as the phrase list this detector replaced.
_VERBS = frozenset(
    """wire wired wiring fix fixed fixing add added adding build built building make made making
    run ran running use used using write wrote written create created creating update updated
    updating verify verified verifying check checked checking test tested testing
    implement implemented implementing remove removed removing delete deleted deleting
    ensure ensured ensuring prove proved proving show showed showing""".split()
)


def _words(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z0-9_]+", text.lower())
        if w not in _STOPWORDS and w not in _VERBS and len(w) > 2
    }


_TOOL_CALL_TYPES = ("tool_use", "tool_call", "toolCall")


def _is_tool_call_block(block: dict) -> bool:
    return block.get("type") in _TOOL_CALL_TYPES


def _tool_input(block: dict) -> dict:
    """A tool call's arguments, whichever runtime wrote them.

    Claude Code writes {"type": "tool_use", "input": {...}}. Pi writes
    {"type": "toolCall", "arguments": {...}} -- a distinct field name, not just a distinct type
    string. Measured 2026-09-15: every pi session on this machine has 0 declare_plan/revise_plan
    hits and 0 extracted actions for exactly this reason -- this gate read Claude Code's transcript
    shape only, so it was structurally blind to every pi session, the same class of bug _unwrap
    exists to fix for the turn-nesting shape.
    """
    return block.get("input") or block.get("arguments") or {}


def _unwrap(turn: dict) -> dict:
    """Pi's transcript nests the turn under a `message` key; the test fixtures do not.

    Real shape:  {"type":"message","message":{"role":"assistant","content":[...]}}
    Fixture:     {"role":"assistant","content":[...]}
    Reading `turn["content"]` on the real shape finds nothing, which is how this gate parsed 1475
    turns of a real session and extracted zero actions -- a clean pass on a transcript it never
    actually read. Accept both shapes.
    """
    inner = turn.get("message")
    return inner if isinstance(inner, dict) else turn


def _blocks(turn: dict) -> list[dict]:
    content = _unwrap(turn).get("content")
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _actions(turns: list[dict]) -> list[str]:
    """Every command and file path the session actually intended to touch."""
    out: list[str] = []
    for turn in turns:
        msg = _unwrap(turn)
        for block in _blocks(turn):
            if _is_tool_call_block(block):
                inp = _tool_input(block)
                if block.get("name") in ESCAPE_HATCHES:
                    continue
                out.append(str(inp.get("command", "")) or str(inp.get("path", "")))
        content = msg.get("content")
        if isinstance(content, str):
            out.append(content)
        elif isinstance(content, list):
            out.extend(
                str(b.get("text", "")) for b in _blocks(turn) if b.get("type") == "text"
            )
    return [a for a in out if a.strip()]


def grade(turns: list[dict]) -> dict:
    """Grade a transcript for drift: did the agent act outside the plan it declared?

    Structural, not a phrase list. The agent declared a plan; the subjects in that goal are the
    corridor. An action sharing no subject with it is outside the corridor, whether or not anyone
    anticipated it -- which is the difference between a guard and a list of remembered blunders.
    """
    declared = _declared_subjects(turns)
    has_plan = bool(declared)
    for action in _actions(turns):
        words = _words(action)
        if not words:
            continue
        if not has_plan:
            return {
                "drift": True,
                "verdict": "FAIL 403 Trajectory Drift",
                "why": "work began with no declared plan",
                "declared_plan": False,
            }
        if not (words & declared):
            return {
                "drift": True,
                "verdict": "FAIL 403 Trajectory Drift",
                "why": f"an action outside the declared plan: {action[:80]}",
                "declared_plan": True,
            }
    return {"drift": False, "verdict": "PASS", "why": "", "declared_plan": has_plan}


def _blind(why: str) -> dict:
    return {"drift": True, "verdict": "BLIND", "why": why, "declared_plan": False}


def grade_file(path: Path | str) -> dict:
    p = Path(path)
    if not p.exists():
        return _blind(f"{p} does not exist")
    try:
        raw = p.read_text(errors="replace")
    except OSError as exc:
        return _blind(f"{p} could not be read: {exc}")
    turns: list[dict] = []
    for n, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            turns.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            return _blind(f"{p}:{n} is not valid JSON")
    return grade(turns)


def _estate_sessions() -> list[Path]:
    """The session transcripts this machine's agents actually wrote, newest first.

    Mirrors bin/epistemic_firewall.py's own fix (same defect, same two duplicated defs):
    ``~/.pi/agent/sessions`` alone stopped being written months ago, so this swept nothing
    a real idp session ever produced. ``~/.claude/projects`` is where the Claude Code CLI
    itself writes one line per turn, verbatim, for every session.
    """
    roots = (
        Path.home() / ".pi" / "agent" / "sessions",
        Path.home() / ".claude" / "projects",
    )
    found: list[Path] = []
    for home in roots:
        if home.is_dir():
            found.extend(home.glob("*/*.jsonl"))
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def _grade_estate(limit: int = 25) -> int:
    """Grade the most recent real sessions. The live case: no fixture is involved."""
    sessions = _estate_sessions()[:limit]
    if not sessions:
        # Same reasoning as bin/epistemic_firewall.py: a runner has no ~/.pi, and no transcripts
        # means nothing to grade rather than a blind check. Grading one named session still fails.
        print(
            "ok    trajectory no session transcripts on this machine; nothing to grade "
            "(a named session is still graded, and a missing one is still BLIND)"
        )
        return 0
    drifted = 0
    for path in sessions:
        verdict = grade_file(path)
        if verdict["verdict"] == "BLIND":
            continue
        if verdict["drift"]:
            drifted += 1
            print(f"      {path.name}: {verdict['why']}", file=sys.stderr)
    # Reported, not failed. The live case exists so this rule is graded against the estate rather
    # than only its own fixture, and the finding is real: measured 2026-09-12, 25 of 25 recent
    # sessions began work with no declared plan. But that is history -- a gate that fails the build
    # until no agent ever drifts again would be switched off within a day and protect nothing
    # (AGENTS.md R38, a guard that refuses correct work is an outage). Grade ONE session by name to
    # act on it; the sweep prints the count so the number is never hidden.
    print(
        f"ok    trajectory {len(sessions)} recent session(s) swept; {drifted} left their declared "
        f"plan. Historical, reported not failed -- grade one session by name to act on it."
    )
    return 0


def _selftest() -> int:
    """Drive the four mechanisms and print one line each. A process, not an import.

    The BDD scenario set grades the gate the way a person does: by running it. The four
    mechanisms live behind a library API that no CLI verb reaches, and a test that imports the
    module to reach them asserts the repository's own code back at itself and runs nothing --
    the class bin/test-executes-gate refuses, and the class this repository deleted 322 copies of
    on 2026-09-04. So the gate exposes them itself, and the test runs the gate.

    Prints `ok <mechanism>` per line and exits 0; any mechanism that does not behave exits 1.
    """
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"ok    {name}")
        else:
            failures.append(name)
            print(f"FAIL  {name} {detail}")

    lock = TrajectoryLock()
    v = lock.authorize("bash", {"command": "ls"}, session_id="s")
    check(
        "bounded-goal-stack",
        v["allowed"] is False and v["code"] == 403,
        v.get("reason", ""),
    )

    lock.declare_plan("s", "add a button", [{"id": "goal_1", "text": "add the button"}])
    ok = lock.authorize(
        "bash", {"command": "touch b.tsx"}, session_id="s", target_goal_id="goal_1"
    )
    off = lock.authorize(
        "bash", {"command": "npm i -g node@20"}, session_id="s", target_goal_id="goal_9"
    )
    check(
        "tool-to-goal-binding",
        ok["allowed"] is True and off["allowed"] is False,
        off.get("reason", ""),
    )

    b = TrajectoryLock(budget_per_goal=2)
    b.declare_plan("s", "x", [{"id": "g1", "text": "a"}, {"id": "g2", "text": "b"}])
    for _ in range(2):
        b.authorize("bash", {"command": "a"}, session_id="s", target_goal_id="g1")
    halt = b.authorize("bash", {"command": "a"}, session_id="s", target_goal_id="g1")
    other = b.authorize("bash", {"command": "y"}, session_id="s", target_goal_id="g2")
    check(
        "micro-budget-kill-switch",
        halt["allowed"] is False
        and halt.get("halt") is True
        and other["allowed"] is True,
        halt.get("reason", ""),
    )
    check(
        "escape-hatches-never-blocked",
        b.authorize("revise_plan", {}, session_id="s")["allowed"] is True
        and b.authorize("escalate", {"why": "stuck"}, session_id="s")["allowed"]
        is True,
    )

    p = TrajectoryLock()
    p.declare_plan("s", "add a button", [{"id": "g1", "text": "add it"}])
    turns = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "the goal is: add a button"}],
        }
    ]
    for i in range(3):
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
    out = p.prune("s", turns, goal="add a button")
    check(
        "forced-context-pruning",
        out["pruned"] is True
        and "Trajectory Drift Detected" in str(out["messages"][-1])
        and "add a button" in str(out["messages"][-1]),
    )
    low = p.prune("s", turns[:5], goal="add a button")
    check("pruning-below-threshold", low["pruned"] is False)

    keep = [
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
        {"role": "tool", "content": [{"type": "text", "text": "abc123 did the thing"}]},
    ] + turns[1:]
    kept = p.prune("s", keep, goal="add a button")
    check(
        "successful-evidence-never-pruned",
        "git log --oneline -3" in str(kept["messages"]),
    )

    print(
        f"selftest {len(failures)} failure(s)"
        if failures
        else "selftest all mechanisms behave"
    )
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    # Two callers, one entry point. The CLI passes sys.argv, so argv[0] is the script's own path;
    # the tests pass [path], so argv[0] IS the transcript. Guessing from the name got this wrong
    # in both directions. The honest test is whether the file is there: a path that exists is a
    # transcript, and the script's own path exists but is not JSON -- so require the suffix too.
    flags = [a for a in argv[1:] if a.startswith("--")] if len(argv) > 1 else []
    if "--selftest" in flags:
        return _selftest()
    args = [a for a in argv[1:] if not a.startswith("-")] if len(argv) > 1 else []
    if not args and argv and not argv[0].startswith("-") and argv[0].endswith(".jsonl"):
        args = [argv[0]]

    # No argument: grade the estate's own session transcripts. This is the live case the rule
    # registry requires -- a rule whose every case names a fixture has never seen the platform.
    if not args:
        return _grade_estate()

    verdict = grade_file(args[0])
    if verdict["verdict"] == "BLIND":
        print(f"BLIND trajectory {verdict['why']}", file=sys.stderr)
        return 2
    if verdict["drift"]:
        print("FAIL  trajectory the agent left its declared plan", file=sys.stderr)
        print(f"      {verdict['why']}", file=sys.stderr)
        return 1
    print("ok    trajectory the agent stayed inside its declared plan")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
