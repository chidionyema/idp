#!/usr/bin/env python3
"""Estate MCP: one door to the intent registry.

Three tools only:
  estate_list   — list all available intents
  estate_show   — show args and description for one intent
  estate_invoke — run an intent and return stdout

THE CONSOLIDATION RULE (2026-09-24):
Every other estate MCP plugin that executes commands is dead.
estate_executor.py (execute_command, propose_patch, verify, etc.) is deleted.
estate_simulate.py is deleted.
The intent YAML is the only executable unit. The MCP server wraps it.

Tools that remain as read-only inquiry (NOT deleted, NOT modified):
  estate_holmes     — ask the estate's AI investigator
  estate_inventory   — what is the estate (from crew/STATE.md + catalog)
  estate_memory      — remember / recall from Hindsight vector store
  estate_sessions    — list_sessions / get_session from catalog
  estate_state       — get_estate_state from estate-db
  estate_twin        — live state vs declared state from estate-db
  estate_guards      — get_estate_guards (read-only policy check)

These are inquiry tools. They answer questions. They do not execute commands.
They are not duplicated by the intent system and are kept intact.
"""

import json, os, subprocess, sys, tempfile, yaml
from pathlib import Path

HOME = Path.home()
INTENTS = HOME / ".estate" / "intents"
LIBEXEC = HOME / ".estate" / "libexec"
DB = HOME / ".estate" / "estate.db"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_intents():
    results = []
    for f in sorted(INTENTS.glob("*.yaml")):
        try:
            with open(f) as fh:
                d = yaml.safe_load(fh)
            results.append(
                {
                    "name": f.stem,
                    "description": d.get("description", "").strip(),
                    "args": {
                        k: v.get("help", "") for k, v in d.get("args", {}).items()
                    },
                    "halt_on_failure": d.get("halt_on_failure", True),
                }
            )
        except Exception:
            pass
    return results


def _load_intent(name):
    path = INTENTS / f"{name}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def estate_list(args):
    """List all available intents with one-line descriptions."""
    intents = _load_intents()
    lines = [f"# {len(intents)} intents available:\n"]
    for i in intents:
        lines.append(f"## {i['name']}")
        lines.append(f"{i['description'][:120]}")
        if i["args"]:
            lines.append(f"args: {', '.join(i['args'].keys())}")
        lines.append("")
    return "\n".join(lines)


def estate_show(args):
    """Show full description and args for one intent."""
    name = args.get("intent", "")
    if not name:
        return "ERROR: intent name required"
    d = _load_intent(name)
    if d is None:
        return f"ERROR: unknown intent: {name}\n\nAvailable: {', '.join([f.name for f in INTENTS.glob('*.yaml')])}"
    lines = [f"# {name}", "", d.get("description", "")]
    if d.get("args"):
        lines.append("\n## Args:")
        for k, v in d["args"].items():
            lines.append(f"  {k}: {v.get('help', '')[:80]}")
            if "default" in v:
                lines.append(f"    default: {v['default']}")
    if d.get("steps"):
        lines.append("\n## Steps:")
        for i, s in enumerate(d["steps"]):
            lines.append(f"  {i + 1}. {s.get('cmd', '')[:80]}")
    return "\n".join(lines)


def estate_invoke(args):
    """Run an intent and return stdout. Never modifies source files unless via verified patch."""
    name = args.get("intent", "")
    raw_args = args.get("args", {})
    timeout = int(args.get("timeout", 120))

    if not name:
        return "ERROR: intent name required"
    d = _load_intent(name)
    if d is None:
        return f"ERROR: unknown intent: {name}"

    # Resolve args to positional and --key=value strings
    arg_defs = d.get("args", {})
    positional_names = list(arg_defs.keys())
    resolved = {}

    for k, v in raw_args.items():
        resolved[k] = v
    for i, val in enumerate(raw_args.get("_positional", [])):
        if i < len(positional_names):
            resolved[positional_names[i]] = val

    # Build command line
    cmd = ["python3", str(HOME / ".estate" / "bin" / "estate-execute"), name]
    for k, v in resolved.items():
        if k == "_positional":
            continue
        cmd.append(f"{k}={v}")
    for k, spec in arg_defs.items():
        if k not in resolved:
            cmd.append(f"{k}={spec.get('default', '')}")

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(HOME / "Documents" / "code" / "idp"),
        )
        out = r.stdout.strip()
        if r.stderr:
            # Log lines go to stderr, capture them for debugging
            pass
        if r.returncode == 0:
            return out if out else "ok"
        else:
            return f"ERROR (exit {r.returncode}):\n{r.stdout}\n{r.stderr}"
    except subprocess.TimeoutExpired:
        return f"ERROR: intent timed out after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# datasette-mcp plugin hook
# ---------------------------------------------------------------------------

try:
    from datasette import hookimpl
except ImportError:

    def hookimpl(fn):
        return fn


TOOL_DEFS = [
    {
        "name": "estate_list",
        "description": "List all available estate intents. Returns name and one-line description for each.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "estate_show",
        "description": "Show full description, args, and steps for one intent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "Intent name (e.g. shell.parse, git.branch)",
                },
            },
            "required": ["intent"],
        },
    },
    {
        "name": "estate_invoke",
        "description": "Run an estate intent and return its stdout. The intent system is the only execution layer -- no arbitrary bash, no subprocess outside an intent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "Intent name"},
                "args": {
                    "type": "object",
                    "description": "Intent arguments as key-value pairs",
                    "default": {},
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds to wait (default 120)",
                },
            },
            "required": ["intent"],
        },
    },
]

TOOL_FNS = {
    "estate_list": estate_list,
    "estate_show": estate_show,
    "estate_invoke": estate_invoke,
}


@hookimpl
def register_mcp_tools(datasette, mcp):
    for td in TOOL_DEFS:

        def make_wrapper(fn, td=td):
            def wrapper(**kwargs):
                try:
                    result = fn(kwargs)
                    return {"content": [{"type": "text", "text": str(result)}]}
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"ERROR: {e}"}],
                        "isError": True,
                    }

            mcp.add_tool(
                wrapper,
                name=td["name"],
                description=td["description"],
                inputSchema=td["inputSchema"],
            )

        make_wrapper(TOOL_FNS[td["name"]])
