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
import subprocess
import sys
import time
from typing import Optional

MIN_GOAL_CHARS = 8
MIN_SUBGOAL_CHARS = 4

# The plan's two links to the estate: the INSTRUCTION (the intent the work goes through) and the
# PROMPT (the founder prompt that started it). The shape is checked here, in both copies of the
# contract, so the two cannot drift; whether the names RESOLVE is checked by the governance
# layer (platform/estate/governance/plan_links.py), which is where the ledgers live.
INSTRUCTION_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
PROMPT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,120}$")

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
    instruction = _s(a.get("instruction"))
    prompt = _s(a.get("prompt"))
    if "instruction" in a and not instruction:
        return _refuse("instruction must name the intent this plan serves")
    if "prompt" in a and not prompt:
        return _refuse("prompt must name the founder prompt this plan answers")
    if instruction and not INSTRUCTION_RE.match(instruction):
        return _refuse(f'instruction "{instruction}" is not an intent name')
    if prompt and not PROMPT_ID_RE.match(prompt):
        return _refuse(f'prompt "{prompt}" is not a founder prompt id')
    return {
        "ok": True,
        "goal": goal,
        "subgoals": subgoals,
        "instruction": instruction,
        "prompt": prompt,
    }


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
            # A revision keeps the links it does not restate: the work is still the same work.
            "instruction": v["instruction"] or old.get("instruction", ""),
            "prompt": v["prompt"] or old.get("prompt", ""),
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
        links = []
        if nxt["instruction"]:
            links.append(f"instruction {nxt['instruction']}")
        if nxt["prompt"]:
            links.append(f"founder prompt {nxt['prompt']}")
        if links:
            msg += "\nLinked to " + " and ".join(links) + "."
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

# Where the door writes every REFUSAL it makes, with the reason. A refusal the caller can see
# but nobody can audit is a complaint, not a gate (idp#7518, acceptance I4).
PLAN_REFUSAL_FILE = "refusals.jsonl"

# Where the door records every INTENT invocation, with the session that made it. An intent that
# ran with no session at all is recorded as `anonymous`: identity-less automation stays ALLOWED
# (standing estate policy), but it must be VISIBLE. Work nobody can attribute is not governed
# work, and an unrecorded intent is how the intent door became a blind spot (idp#7576).
PLAN_INTENT_FILE = "intents.jsonl"

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
        "help",
        "version",
    }
)

# git subcommands that have BOTH a reading form and a mutating form. They are NOT blanket
# read-only: `git remote add`, `git config key value` and `git branch -d` are work, and a
# classifier that calls them reads is a gate that cannot fail (R1).
#
# `git config` reads only in its query forms; `git config key value` WRITES the config.
_GIT_CONFIG_READ_FLAGS = (
    "--get",
    "--get-all",
    "--get-regexp",
    "--get-urlmatch",
    "--list",
    "-l",
)

# `git remote` reads only in its listing/query forms; add/remove/rename/set-url/prune/update
# all change the repo.
_GIT_REMOTE_READ_SUBS = ("", "-v", "--verbose", "show", "get-url")

# `git branch` reads only when it lists; the delete/move/copy forms change refs.
_GIT_BRANCH_WRITE_FLAGS = (
    "-d",
    "-D",
    "-m",
    "-M",
    "-c",
    "-C",
    "--delete",
    "--move",
    "--copy",
    "--set-upstream-to",
    "--unset-upstream",
    "--edit-description",
)

# git global options that take a value, in both the separated and the `=` form. `git -C <path>
# status` is the exact command the door used to refuse (the classifier took toks[1] as the
# subcommand and saw `-C`), so the parser skips them before it looks for the subcommand.
_GIT_GLOBAL_VALUE_OPTS = (
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--super-prefix",
    "--config-env",
)

# git's informational flags: they print and exit, changing nothing. The classifier used to
# consume them as bare global options, find no subcommand, and call the whole invocation
# WORK -- so the door refused `git --version` from a session with no plan (idp#7518). A false
# refusal is worse than a missing refusal: it teaches the estate that the gate is noise.
_GIT_INFO_FLAGS = ("--version", "--help", "-h")

# gh subcommands that only read.
_GH_READ = frozenset({"view", "list", "status", "search", "auth"})

# A command that chains anything is not a read: `cat x; rm y` reads and writes.
_CHAIN = re.compile(r"[|;&`]|&&|\|\||\$\(|\n")

# A leading `cd <dir>` is working-directory setup, not work: it changes nothing outside the
# step's own shell. Almost every intent step opens with one (`cd /path && git show ...`), so
# treating it as a chain made the intent door refuse plain reads -- a false refusal is worse
# than a missing refusal, because it teaches the estate that the gate is noise (idp#7576).
_CD_PREFIX = re.compile(r"^\s*cd\s+(?:\"[^\"]*\"|'[^']*'|\S+)\s*(?:&&|;)\s*(.*)$")


def _strip_leading_cd(cmd: str) -> str:
    """Drop leading directory-change segments, leaving the command that actually does the work."""
    out = cmd
    while True:
        m = _CD_PREFIX.match(out)
        if not m:
            return out
        out = m.group(1)


def _writes_a_file(cmd: str) -> bool:
    """True when the command redirects output INTO a file that persists.

    `git show x > out.yml` writes a file; the old classifier had no notion of redirection, so
    that write was classified as a READ -- a write the gate could not see (idp#7576).
    """
    return ">" in cmd


# A descriptor move (`2>&1`, `>&2`) and a discard (`2>/dev/null`) neither create a file nor
# chain anything. They are everywhere in the intent library (15 intents move a descriptor, 23
# discard one), so treating them as work would refuse plain reads -- and a false refusal is
# worse than a missing refusal, because it teaches the estate to route around its own gate.
_FD_MOVE = re.compile(r"\d*>&-?\d+")
_FD_DISCARD = re.compile(r"\d*>/dev/null")


def _scrub_descriptors(cmd: str) -> str:
    """Remove descriptor moves and discards, leaving the command that actually does the work."""
    out = _FD_DISCARD.sub(" ", cmd)
    return _FD_MOVE.sub(" ", out)


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


def ledger_exists(session_id: str) -> bool:
    """True when this session has a ledger at all.

    The ledger's existence is the evidence that the session's runtime adapter is LIVE for it:
    the adapter opens the ledger when the session starts, whether or not a plan is declared.
    That distinction is what keeps a fence a correct machine can satisfy: a session whose
    adapter has not been installed yet has no ledger, so the door cannot tell a compliant
    agent from an unplanned one -- that work is ALLOWED and RECORDED instead of refused.
    """
    try:
        return os.path.exists(ledger_path(session_id))
    except Exception:  # noqa: BLE001 - an unreadable path is no ledger, never a crash
        return False


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


def sync_plan_calls(session_id: str, calls: list) -> int:
    """Make the durable ledger hold the plan calls the caller has made, in order.

    The caller may hold the whole plan in memory (Claude's transcript, the MCP bridge), while
    the ledger holds what has been written so far. The ledger is only ever APPENDED to: it is
    never rewritten, so a declaration made in another surface at the same moment is never
    erased, and the order of the calls is preserved.

    The tail is found by CONTENT, not by count: the calls the caller holds and the calls the
    ledger holds share a prefix, and everything after that prefix is appended. Counting
    instead would drop a call whenever the ledger holds an extra event the caller has not
    seen (a concurrent declaration), which is exactly the case this must not lose.

    Returns how many calls were appended.
    """
    try:
        have = [tuple(c) for c in ledger_calls(session_id)]
        want = [tuple(c) for c in (calls or [])]
        shared = 0
        # An index walk, not zip(): `strict=` is Python 3.10 and this host is 3.9.
        for i in range(min(len(have), len(want))):
            if have[i] != want[i]:
                break
            shared += 1
        missing = want[shared:]
        for tool, args in missing:
            append_plan_event(session_id, tool, args or {})
        return len(missing)
    except Exception:  # noqa: BLE001 - a broken ledger must not take a session down
        return 0


def session_pointer_path(pid: int) -> str:
    """Where a runtime adapter binds its session id to the process that owns it."""
    return os.path.join(PLAN_LEDGER_DIR, "session-%d.json" % int(pid))


def write_session_pointer(
    session_id: str, pid: Optional[int] = None, overwrite: bool = True
) -> bool:
    """Bind a session id to the process that owns the session.

    The door cannot ask the caller who it is, and the caller's word is exactly what a gate
    must not trust. The adapter that owns the session writes the binding; the door reads it.

    `overwrite=False` is the conflict-safe form: a pointer that already names a session is
    left alone, because the runtime that wrote it owns that session's plan. An adapter that
    generates its own id (the MCP bridge) must not replace the owning runtime's pointer with
    a generated one -- that would leave two ledgers behind one pointer.
    """
    if not session_id:
        return False
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        path = session_pointer_path(os.getpid() if pid is None else pid)
        if not overwrite and os.path.exists(path):
            return False
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"session_id": session_id, "at": time.time()}, fh, sort_keys=True)
        return True
    except Exception:  # noqa: BLE001 - a pointer that cannot be written must not break the agent
        return False


def publish_session(
    session_id: str,
    pid: Optional[int] = None,
    calls: Optional[list] = None,
    overwrite: bool = True,
) -> dict:
    """Publish one session to the estate: pointer, marker, and its ordered plan calls.

    This is the ONE place publication happens. A runtime adapter (the pi extension, the
    Claude Code hook, the MCP bridge, the opencode plugin) calls it; none of them keeps its
    own idea of what the ledger means.

    - the pointer binds the session to the process that owns it, so the door can find it;
    - the `session_start` marker opens the ledger, which is what proves the adapter is LIVE
      for that session (a session with no ledger is allowed and recorded, not refused);
    - the plan calls are appended in declaration order, only the missing tail, so a
      concurrent declaration is never erased.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return {"ok": False, "reason": "no_session"}
    out = {"ok": True, "session": sid, "pointer": False, "marker": False, "appended": 0}
    try:
        out["pointer"] = bool(write_session_pointer(sid, pid=pid, overwrite=overwrite))
    except Exception:  # noqa: BLE001 - a missing pointer must not break the session
        out["pointer"] = False
    try:
        if not ledger_exists(sid):
            append_plan_event(sid, "session_start", {})
            out["marker"] = True
    except Exception:  # noqa: BLE001 - a missing ledger must not break the session
        out["marker"] = False
    try:
        out["appended"] = int(sync_plan_calls(sid, calls or []))
    except Exception:  # noqa: BLE001 - a broken ledger must not break the session
        out["appended"] = 0
    return out


def resolve_session_id() -> str:
    """The caller's session identity, in order of trust.

    1. `ESTATE_SESSION_ID` in the environment -- the runtime that set it owns the session.
    2. A pointer file written by the runtime that owns the session, searched along this
       process's ANCESTORS: an MCP server runs under its runtime, and the intent executor
       runs under the MCP server, so the owner is further up the tree than the immediate
       parent. The immediate parent and this process are searched too.
    3. Nothing. The caller is automation, the fact is recorded, and the work is let through.
    """
    sid = (os.environ.get("ESTATE_SESSION_ID") or "").strip()
    if sid:
        return sid
    for pid in _ancestor_pids():
        try:
            with open(session_pointer_path(pid), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        sid = str((data or {}).get("session_id") or "").strip()
        if sid:
            return sid
    return ""


def _ancestor_pids(limit: int = 6) -> list:
    """This process and its ancestors, nearest first.

    The chain is walked with `ps`, so it costs one small subprocess per level and cannot
    block the door. A pid that cannot be read ends the walk.
    """
    out = []
    try:
        pid = os.getpid()
    except Exception:  # noqa: BLE001 - no pid, no chain
        return out
    for _ in range(limit):
        if not pid or pid <= 1 or pid in out:
            break
        out.append(pid)
        parent = _parent_pid(pid)
        if not parent:
            break
        pid = parent
    return out


def _parent_pid(pid: int) -> int:
    """The parent of one pid, or 0 when it cannot be read."""
    try:
        out = subprocess.run(  # noqa: S603 -- fixed argv (/bin/ps), never a shell string
            ["/bin/ps", "-o", "ppid=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return int((out.stdout or "0").strip() or 0)
    except Exception:  # noqa: BLE001 - an unreadable chain is no chain, never a crash
        return 0


def _git_tokens(toks: list):
    """The git subcommand and the tokens after it, skipping git's global options.

    `git -C /path status --short` is a status. The old classifier took `toks[1]` as the
    subcommand and saw `-C`, so the door refused read-only work that agents run constantly --
    a false refusal is worse than a missing refusal, because it teaches the estate that the
    gate is noise (idp#7518).
    """
    i = 1
    n = len(toks)
    while i < n:
        tok = toks[i]
        if tok in _GIT_GLOBAL_VALUE_OPTS:
            i += 2
            continue
        if "=" in tok:
            head = tok.split("=", 1)[0]
            if head in _GIT_GLOBAL_VALUE_OPTS:
                i += 1
                continue
        if tok.startswith("-"):
            # A bare global flag with no value, e.g. `--no-pager`, `--paginate`.
            if tok in _GIT_INFO_FLAGS and i + 1 >= n:
                # `git --version` alone: it prints and exits. It is not a subcommand.
                return "--info", []
            i += 1
            continue
        break
    if i >= n:
        return "", []
    return toks[i], toks[i + 1 :]


def _git_is_read_only(sub: str, rest: list) -> bool:
    """True when this git invocation only reads."""
    if not sub:
        return False
    if sub == "--info":
        # `git --version`, `git --help`: they print the version or the usage and exit.
        return True
    if sub in ("config", "remote", "branch"):
        # Conditional subcommands: their reading and mutating forms share a name.
        if sub == "config":
            if not rest:
                return False
            return any(f in rest for f in _GIT_CONFIG_READ_FLAGS)
        if sub == "remote":
            args = [a for a in rest if not a.startswith("-")]
            verb = args[0] if args else ""
            if verb in ("show", "get-url"):
                return True
            return not args
        # branch
        if any(f in rest for f in _GIT_BRANCH_WRITE_FLAGS):
            return False
        if any(
            a.startswith("-") and a not in ("-a", "-r", "-v", "-vv", "--all", "--list")
            for a in rest
        ):
            return False
        return True
    if sub == "diff":
        # `git diff --output=file` writes a file. It is not a read.
        if any(a == "--output" or a.startswith("--output=") for a in rest):
            return False
        return True
    return sub in _GIT_READ


def is_read_only_command(command: str) -> bool:
    """True when a command only reads. A plan-tool call is not work: it IS the declaration."""
    cmd = (command or "").strip()
    if not cmd:
        return False
    if shell_plan_call(cmd):
        return True
    # A leading `cd <dir>` is setup; what follows is what the step actually does.
    cmd = _strip_leading_cd(cmd)
    if not cmd.strip():
        return False
    # Descriptor moves and discards are neither work nor a chain.
    cmd = _scrub_descriptors(cmd)
    # Output into a file is work, whatever the command reads.
    if _writes_a_file(cmd):
        return False
    if _CHAIN.search(cmd):
        return False
    toks = cmd.split()
    exe = os.path.basename(toks[0])
    if exe in _READ_ONLY_CMDS:
        return True
    if exe == "git":
        sub, rest = _git_tokens(toks)
        return _git_is_read_only(sub, rest)
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
        if not ledger_exists(sid):
            # The adapter for this session has not opened a ledger, so the door cannot tell a
            # compliant agent from an unplanned one. Refusing here would trap a correct agent
            # whose runtime adapter is not installed yet -- a fence a correct machine cannot
            # satisfy is an outage, not a gate. The work is let through and RECORDED.
            return {
                "ok": True,
                "reason": "session_unenforced",
                "detail": (
                    "this session presented an id but has no plan ledger, so its runtime "
                    "adapter is not live for it yet. The work is allowed and recorded."
                ),
            }
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


def record_refusal(
    command: str,
    session_id: str = "",
    reason: str = "",
    detail: str = "",
    source: str = "door",
    fatal: bool = True,
) -> bool:
    """One line: this command was REFUSED, and why.

    The socket reply proves the verdict to the caller; this proves it to the estate. Every
    refusal carries the command, the session, `refused`, `fatal`, the reason and the time, so
    the file can be counted without judgement and so a refusal that never reached the caller
    is still visible (idp#7518, acceptance I4).
    """
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        line = json.dumps(
            {
                "at": time.time(),
                "session": session_id,
                "source": source,
                "command": (command or "")[:2000],
                "refused": True,
                "fatal": bool(fatal),
                "reason": reason or "",
                "detail": (detail or "")[:2000],
            },
            sort_keys=True,
        )
        with open(
            os.path.join(PLAN_LEDGER_DIR, PLAN_REFUSAL_FILE), "a", encoding="utf-8"
        ) as fh:
            fh.write(line + "\n")
        return True
    except Exception:  # noqa: BLE001 - recording must never break the door
        return False


def refusal_log_line(
    command: str, session_id: str, reason: str, fatal: bool = True
) -> str:
    """The one line that goes to the door's stderr, so the production log proves the refusal."""
    return json.dumps(
        {
            "event": "plan_gate_refusal",
            "at": time.time(),
            "session": session_id or "",
            "reason": reason or "",
            "refused": True,
            "fatal": bool(fatal),
            "command": (command or "")[:2000],
        },
        sort_keys=True,
    )


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


def record_intent(
    intent_name: str,
    session_id: str = "",
    source: str = "intent-door",
    detail: str = "",
) -> bool:
    """One line: this intent ran, and the session that ran it.

    Every intent invocation is recorded, including the ones with no session at all: those are
    recorded as `anonymous`. Identity-less automation is ALLOWED by standing estate policy --
    trapping it would break the fleet collector, the reaper and the lane watcher -- but it must
    be VISIBLE, because work nobody can attribute is exactly how the intent door became a blind
    spot (idp#7576). The record is what turns "I could not find the work" into "here is the
    session, or here is the fact that there was none".
    """
    try:
        os.makedirs(PLAN_LEDGER_DIR, exist_ok=True)
        line = json.dumps(
            {
                "at": time.time(),
                "session": session_id or "anonymous",
                "intent": intent_name or "",
                "source": source,
                "detail": (detail or "")[:2000],
            },
            sort_keys=True,
        )
        with open(
            os.path.join(PLAN_LEDGER_DIR, PLAN_INTENT_FILE), "a", encoding="utf-8"
        ) as fh:
            fh.write(line + "\n")
        return True
    except Exception:  # noqa: BLE001 - recording must never break the door
        return False


def _publish_cli(argv: list) -> int:
    """`plan.py publish --session <id> --pid <pid> [--calls '<json>']`.

    The canonical publication entry point for adapters that are not Python (the opencode
    plugin is JavaScript). The calls may come as `--calls` or on stdin, so a runtime with a
    long plan does not have to fit it in an argv.
    """
    session = ""
    pid = None
    calls = None
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--session" and rest:
            session = rest.pop(0)
        elif arg == "--pid" and rest:
            try:
                pid = int(rest.pop(0))
            except ValueError:
                pid = None
        elif arg == "--calls" and rest:
            try:
                calls = json.loads(rest.pop(0))
            except ValueError:
                calls = None
        elif arg == "--overwrite":
            continue
    if calls is None and not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            if raw.strip():
                calls = json.loads(raw)
        except (ValueError, OSError):
            calls = None
    # A pointer that already names a session is owned by that session's runtime: it is left
    # alone unless the caller explicitly asks to overwrite it.
    overwrite = "--overwrite" in argv
    print(
        json.dumps(publish_session(session, pid=pid, calls=calls, overwrite=overwrite))
    )
    return 0


def main(argv: list) -> int:
    if argv and argv[0] == "publish":
        return _publish_cli(argv[1:])
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
