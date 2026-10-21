"""The plan contract for every agent runtime that is not pi (idp#6675).

    declare_plan -> add_bdd (before any work on the sub-goal)
                 -> address_edgecases + address_2nd_order_effects -> complete_goal
    revise_plan  the escape hatch when the work changes

The same rules as extensions/pi-plan-lock/plan.ts, in Python because the bridge and the hooks are
Python. extensions/pi-plan-lock/cases.json is the contract between the two copies: both test
suites replay it, so neither can drift alone.

State is never shared between processes. The bridge (bin/estate-memory-mcp) applies each call as it
is made and answers the agent; the hook (bin/estate-memory-enforce plan) replays the plan-tool
calls it finds in the transcript through the same `apply`. The rules are deterministic, so a call
the bridge refused is refused again on replay, and both reach the same plan.

A runtime whose bridge did not load can still comply: `estate-plan <plan_tool> '<json>'` run as
one shell command counts as that plan-tool call (shell_plan_call). pi needs no such door -- its
extension registers the plan tools in-process -- so this part has no plan.ts twin.

    python3 plan.py authorize <tool> [args-json]   calls as JSON [[tool, args], ...] on stdin;
                                                   prints {"ok": bool, "reason": str}
"""

from __future__ import annotations

import copy
import json
import os
import re
import shlex
import sys

MIN_GOAL_CHARS = 8
MIN_SUBGOAL_CHARS = 4

PLAN_TOOLS = (
    "declare_plan",
    "revise_plan",
    "add_bdd",
    "address_edgecases",
    "address_2nd_order_effects",
    "complete_goal",
)

# Never refused: a trapped agent must be able to say it is trapped (trajectory-lock.md, "Never
# blocked"); memory reads are how a plan is made from context; and a runtime's own bookkeeping --
# loading a deferred tool's schema (which is how Claude Code reaches declare_plan at all), asking
# the human, a todo list -- is not work.
NEVER_BLOCKED = frozenset({*PLAN_TOOLS, "escalate"})
MEMORY_READS = frozenset({"brief", "recall", "remember"})
HOUSEKEEPING = frozenset(
    {
        "toolsearch",
        "askuserquestion",
        "todowrite",
        "todoread",
        "enterplanmode",
        "exitplanmode",
    }
)


# By absolute path in the refusal: bin/ is on no runtime's PATH, and the door must work anywhere.
ESTATE_PLAN = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
    "bin",
    "estate-plan",
)


def shell_plan_call(command) -> list | None:
    """[tool, args] when a shell command is exactly `estate-plan <plan_tool> '<json object>'`, else
    None. This is the door that never depends on the bridge: a session whose estate-memory tools
    did not load can still declare its plan through the shell, so the lock can never trap an agent
    with no way to comply. Exactly one command and nothing else -- a `;`, `&&`, pipe, newline or
    substitution makes it ordinary work, refused like any other before a plan."""
    if not isinstance(command, str) or re.search(r"[`\n]|\$\(", command):
        return None
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None
    if len(tokens) != 3 or os.path.basename(tokens[0]) != "estate-plan":
        return None
    if tokens[1] not in PLAN_TOOLS:
        return None
    try:
        args = json.loads(tokens[2])
    except ValueError:
        return None
    return [tokens[1], args] if isinstance(args, dict) else None


def as_plan_call(tool: str, args) -> list | None:
    """The plan-tool call a tool call makes, if any: the tool itself, or a shell estate-plan."""
    if bare(tool) in PLAN_TOOLS:
        return [tool, args]
    if tool.lower() == "bash" and isinstance(args, dict):
        return shell_plan_call(args.get("command"))
    return None


def bare(name: str) -> str:
    """A tool's name without the MCP prefix a runtime adds: Claude Code's
    mcp__estate-memory__declare_plan, opencode's estate-memory_declare_plan."""
    name = re.sub(r"^mcp__.+?__", "", name)
    return re.sub(r"^estate[-_]memory(?:__|[._-])", "", name)


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _refuse(reason: str) -> dict:
    return {"ok": False, "reason": reason}


def validate_plan(args) -> dict:
    a = args if isinstance(args, dict) else {}
    goal = _s(a.get("goal"))
    if len(goal) < MIN_GOAL_CHARS:
        return _refuse(
            f"goal must be a sentence of at least {MIN_GOAL_CHARS} characters"
        )
    raw = a.get("subgoals")
    if not isinstance(raw, list) or not raw:
        return _refuse("declare at least one sub-goal; a goal with no steps is a wish")
    seen, subgoals = set(), []
    for s in raw:
        s = s if isinstance(s, dict) else {}
        sid, text = _s(s.get("id")), _s(s.get("text"))
        if not sid or sid in seen:
            return _refuse(f'sub-goal ids must be unique and non-empty (got "{sid}")')
        if len(text) < MIN_SUBGOAL_CHARS:
            return _refuse(
                f"sub-goal {sid} needs text of at least {MIN_SUBGOAL_CHARS} characters"
            )
        seen.add(sid)
        subgoals.append({"id": sid, "text": text})
    return {"ok": True, "goal": goal, "subgoals": subgoals}


def apply(plan: dict | None, tool: str, args) -> dict:
    """One plan-tool call against the current plan: {"ok", "plan", "message"} or {"ok": False,
    "reason"}. Never mutates `plan`."""
    name = bare(tool)
    a = args if isinstance(args, dict) else {}
    if name in ("declare_plan", "revise_plan"):
        v = validate_plan(a)
        if not v["ok"]:
            return v
        # A revision keeps what was recorded about the sub-goals it keeps: an escape hatch, not a
        # reset button for evidence.
        ids = {s["id"] for s in v["subgoals"]}
        old = plan or {}
        keep = lambda rec: {k: x for k, x in (rec or {}).items() if k in ids}  # noqa: E731
        nxt = {
            "goal": v["goal"],
            "subgoals": v["subgoals"],
            "done": [d for d in old.get("done", []) if d in ids],
            "bdd": keep(old.get("bdd")),
            "edgecases": keep(old.get("edgecases")),
            "effects": keep(old.get("effects")),
        }
        first = next(
            (s for s in nxt["subgoals"] if s["id"] not in nxt["done"]),
            nxt["subgoals"][0],
        )
        verb = "declared" if name == "declare_plan" else "revised"
        msg = f"Plan {verb}: {nxt['goal']}\n" + "\n".join(
            f"  {s['id']}: {s['text']}" for s in nxt["subgoals"]
        )
        if first["id"] not in nxt["bdd"]:
            msg += f"\nNext: add_bdd for {first['id']} before any work on it."
        return {"ok": True, "plan": nxt, "message": msg}
    if name not in PLAN_TOOLS:
        return _refuse(f"{tool} is not a plan tool")
    if not plan:
        return _refuse("no plan declared; call declare_plan first")
    gid = _s(a.get("goal_id"))
    ids = [s["id"] for s in plan["subgoals"]]
    if gid not in ids:
        return _refuse(
            f"{gid or '(no goal_id)'} is not on this plan ({', '.join(ids)})"
        )
    nxt = copy.deepcopy(plan)

    if name == "add_bdd":
        b = {k: _s(a.get(k)) for k in ("given", "when", "then")}
        short = [k for k in ("given", "when", "then") if len(b[k]) < MIN_SUBGOAL_CHARS]
        if short:
            return _refuse(
                f"the scenario for {gid} needs {', '.join(short)}: each a clause of at least "
                f"{MIN_SUBGOAL_CHARS} characters"
            )
        nxt["bdd"][gid] = b
        return {
            "ok": True,
            "plan": nxt,
            "message": f"Scenario for {gid}: Given {b['given']}, When {b['when']}, Then {b['then']}",
        }

    if name in ("address_edgecases", "address_2nd_order_effects"):
        field = "edgecases" if name == "address_edgecases" else "effects"
        what = "edge case" if field == "edgecases" else "second-order effect"
        if gid not in plan["bdd"]:
            return _refuse(
                f"{gid} has no BDD scenario yet. add_bdd comes first: the {what}s are of the "
                "behaviour it pins down"
            )
        raw = a.get(field)
        items = [
            x
            for x in map(_s, raw if isinstance(raw, list) else [])
            if len(x) >= MIN_SUBGOAL_CHARS
        ]
        if not items:
            return _refuse(
                f'list at least one {what} for {gid} in `{field}` ("none, because <reason>" '
                "counts; silence does not)"
            )
        nxt[field][gid] = items
        return {
            "ok": True,
            "plan": nxt,
            "message": f"{len(items)} {what}(s) recorded for {gid}",
        }

    # complete_goal
    missing = [
        t
        for t, rec in (
            ("add_bdd", "bdd"),
            ("address_edgecases", "edgecases"),
            ("address_2nd_order_effects", "effects"),
        )
        if gid not in plan[rec]
    ]
    if missing:
        return _refuse(
            f"{gid} cannot be marked done yet: call {', then '.join(missing)} first"
        )
    if gid not in nxt["done"]:
        nxt["done"].append(gid)
    remaining = [i for i in ids if i not in nxt["done"]]
    msg = (
        f"{gid} done. Remaining: {', '.join(remaining)}"
        if remaining
        else f"{gid} done. All sub-goals complete."
    )
    return {"ok": True, "plan": nxt, "message": msg}


def replay(calls) -> dict | None:
    """The plan a sequence of [tool, args] calls leaves. A refused call changes nothing, exactly as
    it changed nothing when it was made."""
    plan = None
    for tool, args in calls:
        call = as_plan_call(tool, args)
        if call:
            r = apply(plan, *call)
            if r["ok"]:
                plan = r["plan"]
    return plan


def authorize(tool: str, plan: dict | None, args=None) -> dict:
    name = bare(tool)
    if name in NEVER_BLOCKED or name in MEMORY_READS or name.lower() in HOUSEKEEPING:
        return {"ok": True}
    call = as_plan_call(tool, args)
    if call and bare(call[0]) == bare(tool):
        return {"ok": True}  # the plan tool itself: the bridge answers it
    if call:
        # The shell door: nothing else will check it, so check it here. A refused call would be
        # skipped on replay anyway; refusing it now tells the agent why.
        r = apply(plan, *call)
        return {"ok": True} if r["ok"] else r
    if not plan:
        return _refuse(
            f"No plan declared, so {tool} is refused. Call declare_plan first with a goal and at "
            'least one sub-goal: declare_plan({goal: "<what done looks like>", subgoals: '
            '[{id: "goal_1", text: "<first step>"}]}). Nothing else runs until you do. If the '
            "plan tools are not in your tool list, run the same call as one shell command: "
            + ESTATE_PLAN
            + ' declare_plan \'{"goal": "...", "subgoals": [{"id": "goal_1", '
            '"text": "..."}]}\' (every plan tool works this way).'
        )
    active = next((s for s in plan["subgoals"] if s["id"] not in plan["done"]), None)
    if active is None:
        return _refuse(
            f'Every sub-goal of "{plan["goal"]}" is done, so {tool} is refused. Call revise_plan '
            "to declare what is next."
        )
    if active["id"] not in plan["bdd"]:
        return _refuse(
            f'{active["id"]} ("{active["text"]}") has no BDD scenario, so {tool} is refused. Pin '
            f'the behaviour down before building it: add_bdd({{goal_id: "{active["id"]}", given: '
            '"<state>", when: "<action>", then: "<observable result>"}).'
        )
    return {"ok": True}


def transcript_calls(text: str) -> list:
    """Every [tool, args] call in a Claude Code transcript (one JSON object per line), in order."""
    out = []
    for line in text.splitlines():
        if '"tool_use"' not in line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("isSidechain"):
            continue  # a subagent's calls are its own session, not this one's plan
        content = (msg.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                out.append([str(block.get("name", "")), block.get("input") or {}])
    return out


# The tool schemas the bridge lists. One place, so every runtime is told the same contract.
_GOAL_ID = {
    "type": "string",
    "description": "The sub-goal id from your plan, e.g. goal_1.",
}
_PLAN = {
    "type": "object",
    "properties": {
        "goal": {
            "type": "string",
            "description": "What 'done' looks like for this task, one sentence.",
        },
        "subgoals": {
            "type": "array",
            "description": "At least one. Each needs add_bdd before work starts on it.",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Short unique id, e.g. goal_1",
                    },
                    "text": {"type": "string", "description": "One verifiable step."},
                },
                "required": ["id", "text"],
            },
        },
    },
    "required": ["goal", "subgoals"],
}


def _items(field: str, what: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "goal_id": _GOAL_ID,
            field: {
                "type": "array",
                "items": {"type": "string"},
                "description": f'At least one {what}. "none, because <reason>" counts; an empty list does not.',
            },
        },
        "required": ["goal_id", field],
    }


TOOL_SCHEMAS = [
    {
        "name": "declare_plan",
        "description": "Declare the goal and sub-goals for this task. REQUIRED before any other tool: "
        "nothing else runs until a plan exists. Then, per sub-goal in order: add_bdd before any work "
        "on it; address_edgecases and address_2nd_order_effects; complete_goal with proof.",
        "inputSchema": _PLAN,
    },
    {
        "name": "revise_plan",
        "description": "Replace the plan when the work has changed. Sub-goals that keep their id keep "
        "their recorded BDD, edge cases, effects and done state.",
        "inputSchema": _PLAN,
    },
    {
        "name": "add_bdd",
        "description": "Pin down one sub-goal's behaviour as Given/When/Then BEFORE any work on it. "
        "Work tools stay refused until the active sub-goal has a scenario.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal_id": _GOAL_ID,
                "given": {"type": "string", "description": "The starting state."},
                "when": {"type": "string", "description": "The action."},
                "then": {
                    "type": "string",
                    "description": "The observable result that proves it works.",
                },
            },
            "required": ["goal_id", "given", "when", "then"],
        },
    },
    {
        "name": "address_edgecases",
        "description": "Record the edge cases of a sub-goal's BDD scenario and how each is handled. "
        "Needs add_bdd first; needed before complete_goal.",
        "inputSchema": _items("edgecases", "edge case and how it is handled"),
    },
    {
        "name": "address_2nd_order_effects",
        "description": "Record a sub-goal's knock-on effects on the rest of the system (callers, other "
        "runtimes, cost, operations). Needs add_bdd first; needed before complete_goal.",
        "inputSchema": _items(
            "effects", "second-order effect and what was done about it"
        ),
    },
    {
        "name": "complete_goal",
        "description": "Mark one sub-goal done after proving it (a command and its output, not a "
        "belief). Refused until add_bdd, address_edgecases and address_2nd_order_effects are recorded.",
        "inputSchema": {
            "type": "object",
            "properties": {"goal_id": _GOAL_ID},
            "required": ["goal_id"],
        },
    },
]


def main(argv: list) -> int:
    if len(argv) not in (2, 3) or argv[0] != "authorize":
        print(__doc__.split("\n\n")[-1], file=sys.stderr)
        return 2
    try:
        calls = json.load(sys.stdin)
        args = json.loads(argv[2]) if len(argv) == 3 else None
        print(
            json.dumps(
                authorize(
                    argv[1], replay(calls if isinstance(calls, list) else []), args
                )
            )
        )
    except (
        Exception
    ) as e:  # fail open: a broken rule must not take a session down (R38)
        print(
            json.dumps(
                {"ok": True, "reason": f"plan check failed open: {type(e).__name__}"}
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
