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
import time
from typing import Optional

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


# ---------------------------------------------------------------------------------------------
# THE DURABLE PLAN LEDGER, AND THE DOOR'S GATE (idp#7518)
#
# Why this exists. The plan used to live in ONE PROCESS: pi's extension kept it in memory, and
# every other runtime rebuilt it by replaying a transcript. Nothing survived the session, nothing
# was visible to the founder, and the estate's one door (mcp/plugins/estate_executor.py) never
# heard about a plan at all. So an agent that reached the estate through any other runtime --
# or through the door directly -- worked with no goals and no sub-goals, and nothing in the
# estate could say so (the falsifier: execute_command accepted `echo plan-gate-falsifier` and
# answered {"accepted": true, "job_id": "exec-1793332780-421"}).
#
# The ledger is ONE store: an append-only JSONL of the plan-tool calls a session made. The plan
# is the replay of that ledger -- the same `replay` the hook already uses -- so there is no second
# model of what a plan is, and a plan declared in one runtime is the same plan in another.
#
# The door's gate reads that ledger and refuses WORK without a plan. Reading is how a plan is
# made, so reads are carved out; so are the plan tools themselves, the memory reads, and the
# housekeeping a trapped agent needs to say it is trapped (R38: a gate that traps the estate
# is a worse outage than the defect it reports).
# ---------------------------------------------------------------------------------------------

PLAN_LEDGER_DIR = os.environ.get("ESTATE_PLAN_LEDGER_DIR") or os.path.join(
    os.path.expanduser("~"), ".estate", "plans"
)

# Where the door writes what it saw without a plan, so the founder can SEE the gap instead of
# inferring it from a missing declaration.
PLAN_OBSERVE_FILE = "observe.jsonl"

# Commands that only read. Everything else is work. This list is deliberately small and
# deliberately conservative in the other direction: an unknown command is WORK, because a gate
# that passes what it cannot classify is a gate that cannot fail (R1).
#
# `echo`, `printf`, `seq`, `true`, `false` and `test` are NOT in it: they invent output rather
# than observe the estate, so they are work. pi's own gate refuses them the same way (a bash
# call is work), and the falsifier for idp#7518 was exactly `echo plan-gate-falsifier` being
# accepted by the door.
_READ_ONLY_CMDS = frozenset(
    {
        "cat",
        "ls",
        "head",
        "tail",
        "wc",
        "grep",
        "egrep",
        "rg",
        "ag",
        "find",
        "fd",
        "stat",
        "file",
        "which",
        "type",
        "pwd",
        "date",
        "whoami",
        "hostname",
        "uname",
        "env",
        "printenv",
        "jq",
        "yq",
        "tree",
        "du",
        "df",
        "diff",
        "cmp",
        "readlink",
        "realpath",
        "basename",
        "dirname",
        "id",
        "ps",
        "top",
        "lsof",
        "open",
    }
)

# git subcommands that only read.
_GIT_READ = frozenset(
    {
        "status",
        "log",
        "diff",
        "show",
        "branch",
        "rev-parse",
        "rev-list",
        "ls-files",
        "ls-tree",
        "ls-remote",
        "describe",
        "blame",
        "shortlog",
        "cat-file",
        "count-objects",
        "reflog",
        "whatchanged",
        "config",
        "remote",
    }
)

# gh subcommands that only read.
_GH_READ = frozenset({"view", "list", "status", "search", "auth"})

# A command that chains anything is not a read: `cat x; rm y` reads and writes.
_CHAIN = re.compile(r"[|;&`]|&&|\|\||\$\(|\n")


def ledger_path(session_id: str) -> str:
    """Where one session's ledger lives. The id is sanitised, because it is a filename."""
    safe = (
        re.sub(r"[^A-Za-z0-9._-]+", "_", str(session_id or "")).strip("_")
        or "anonymous"
    )
    return os.path.join(PLAN_LEDGER_DIR, safe + ".jsonl")


def append_plan_event(session_id: str, tool: str, args: dict) -> bool:
    """One plan-tool call, appended. Never raises: a broken ledger must not take a session down."""
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        line = json.dumps(
            {"at": time.time(), "session": session_id, "tool": tool, "args": args},
            sort_keys=True,
        )
        with open(ledger_path(session_id), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except Exception:  # noqa: BLE001 - the ledger is a convenience, never a crash
        return False


def _ledger_record(line: str):
    """One ledger line -> the plan-tool call it holds, or None when it is not one."""
    try:
        rec = json.loads(line)
    except ValueError:
        return None
    if isinstance(rec, dict) and rec.get("tool") in PLAN_TOOLS:
        return [rec["tool"], rec.get("args") or {}]
    return None


def ledger_calls(session_id: str) -> list:
    """The plan-tool calls one session made, in order. A damaged line is skipped, not fatal."""
    out = []
    try:
        with open(ledger_path(session_id), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = _ledger_record(line)
                if rec:
                    out.append(rec)
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001 - an unreadable ledger is no plan, never a crash
        return []
    return out


def ledger_plan(session_id: str):
    """The plan one session has declared: the replay of its ledger."""
    return replay(ledger_calls(session_id))


def session_pointer_path(pid: int) -> str:
    """Where a runtime adapter binds its session id to the process that owns it."""
    return os.path.join(PLAN_LEDGER_DIR, "session-%d.json" % int(pid))


def write_session_pointer(session_id: str, pid: Optional[int] = None) -> bool:
    """Bind a session id to the process that owns the session.

    The door cannot ask the caller who it is, and the caller's word is exactly what a gate
    must not trust. The adapter that owns the session writes the binding; the door reads it.
    """
    if not session_id:
        return False
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        path = session_pointer_path(os.getpid() if pid is None else pid)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"session_id": session_id, "at": time.time()}, fh, sort_keys=True)
        return True
    except Exception:  # noqa: BLE001 - a pointer that cannot be written must not break the agent
        return False


def resolve_session_id() -> str:
    """The caller's session identity, in order of trust.

    1. `ESTATE_SESSION_ID` in the environment -- the runtime that set it owns the session.
    2. The pointer file the owning runtime wrote for this process (or its parent): the MCP
       server runs underneath the runtime, so the runtime's pid is the door's parent.
    3. Nothing. The caller is automation, the fact is recorded, and the work is let through.
    """
    sid = (os.environ.get("ESTATE_SESSION_ID") or "").strip()
    if sid:
        return sid
    for pid in (os.getppid(), os.getpid()):
        try:
            with open(session_pointer_path(pid), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        sid = str((data or {}).get("session_id") or "").strip()
        if sid:
            return sid
    return ""


def is_read_only_command(command: str) -> bool:
    """True when a command only reads. A plan-tool call is not work: it IS the declaration."""
    cmd = (command or "").strip()
    if not cmd:
        return False
    if shell_plan_call(cmd):
        return True
    if _CHAIN.search(cmd):
        return False
    toks = cmd.split()
    exe = os.path.basename(toks[0])
    if exe in _READ_ONLY_CMDS:
        return True
    if exe == "git":
        sub = toks[1] if len(toks) > 1 else ""
        return sub in _GIT_READ
    if exe == "gh":
        sub = toks[1] if len(toks) > 1 else ""
        if sub in _GH_READ:
            return True
        if sub == "api":
            # `gh api` is a GET by default; a verb, a body or --input makes it a write.
            return not re.search(
                r"(-X|--method)[= ]?(POST|PUT|PATCH|DELETE)|--input|(^|\s)-[fF]\s", cmd
            )
        return False
    return False


def door_plan_gate(command: str, session_id=None) -> dict:
    """The door's verdict on one command.

    `{"ok": True, ...}` or `{"ok": False, "reason": <class>, "detail": <what to do>}`.

    No session presented means no agent session was identified: the caller is automation (the
    fleet collector, the reaper, the lane watcher) and is let through, but the fact is RECORDED,
    so the founder can see work that ran without a declaration. A session that presents an id
    and has no plan is refused: that is the case the bug is about.
    """
    sid = (
        session_id
        if session_id is not None
        else os.environ.get("ESTATE_SESSION_ID", "")
    )
    if not sid:
        return {"ok": True, "reason": "no_session_presented"}
    if is_read_only_command(command):
        return {"ok": True, "reason": "read_only"}
    plan = ledger_plan(sid)
    if not plan:
        return {
            "ok": False,
            "reason": "plan_not_declared",
            "detail": (
                "this session has declared no goal and no sub-goal, so this command is refused. "
                "Declare the plan first: "
                + ESTATE_PLAN
                + ' declare_plan \'{"goal": "<what done looks like>", "subgoals": '
                '[{"id": "goal_1", "text": "<first step>"}]}\' -- then add_bdd for the '
                "sub-goal you are on, and the door lets the work through."
            ),
        }
    active = next((s for s in plan["subgoals"] if s["id"] not in plan["done"]), None)
    if active is None:
        return {
            "ok": False,
            "reason": "plan_complete",
            "detail": (
                "every sub-goal of this plan is done, so this command is refused. Call revise_plan "
                "to declare what is next."
            ),
        }
    if active["id"] not in plan["bdd"]:
        return {
            "ok": False,
            "reason": "subgoal_scenario_missing",
            "detail": (
                active["id"]
                + " ("
                + active["text"]
                + ") has no BDD scenario, so this command is refused. Pin the behaviour down "
                'before building it: add_bdd({goal_id: "'
                + active["id"]
                + '", given: "<state>", when: "<action>", then: "<observable result>"}).'
            ),
        }
    return {"ok": True, "reason": "plan_active", "goal_id": active["id"]}


def record_unplanned(command: str, session_id: str = "", source: str = "door") -> None:
    """One line: this command ran with no plan behind it. The visibility the founder asked for."""
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        line = json.dumps(
            {
                "at": time.time(),
                "session": session_id,
                "source": source,
                "command": (command or "")[:2000],
            },
            sort_keys=True,
        )
        with open(
            os.path.join(PLAN_LEDGER_DIR, PLAN_OBSERVE_FILE), "a", encoding="utf-8"
        ) as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001 - recording must never break the door
        return


def main(argv: list) -> int:
    if argv and argv[0] == "gate":
        # The door's verdict, one command at a time: `plan.py gate "<command>" [session-id]`.
        command = argv[1] if len(argv) > 1 else ""
        sid = argv[2] if len(argv) > 2 else None
        print(json.dumps(door_plan_gate(command, sid)))
        return 0
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
