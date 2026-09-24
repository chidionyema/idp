#!/usr/bin/env python3
from __future__ import annotations
import logging
import re
import subprocess
import sys
import yaml
from pathlib import Path

HOME = Path.home()
INTENTS = HOME / ".estate" / "intents"
log = logging.getLogger(__name__)
_ALLOWED = re.compile(r"^[a-z][a-z0-9.-]*$")


def _is_valid(n):
    return bool(_ALLOWED.match(n))


def _load_intents():
    r = []
    for f in sorted(INTENTS.glob("*.yaml")):
        try:
            with open(f) as fh:
                d = yaml.safe_load(fh)
            r.append(
                {
                    "name": f.stem,
                    "description": d.get("description", "").strip(),
                    "args": {
                        k: v.get("help", "") for k, v in d.get("args", {}).items()
                    },
                    "halt_on_failure": d.get("halt_on_failure", True),
                }
            )
        except Exception as exc:
            log.warning("intent %s failed: %s", f.name, exc)
    return r


def _load_intent(name):
    if not _is_valid(name):
        return None
    p = INTENTS / (name + ".yaml")
    if not p.exists():
        return None
    with open(p) as fh:
        return yaml.safe_load(fh)


def _estate_list(args):
    intents = _load_intents()
    lines = ["# {} intents available:".format(len(intents))]
    for i in intents:
        lines.append("## {}".format(i["name"]))
        lines.append(i["description"][:120])
        if i["args"]:
            lines.append("args: {}".format(", ".join(i["args"].keys())))
        lines.append("")
    return "\n".join(lines)


def _estate_show(args):
    name = args.get("intent", "")
    if not name:
        return "ERROR: intent name required"
    d = _load_intent(name)
    if d is None:
        avail = ", ".join(sorted(f.name for f in INTENTS.glob("*.yaml")))
        return "ERROR: unknown intent: {}\n\nAvailable: {}".format(name, avail)
    lines = ["# {}".format(name), "", d.get("description", "")]
    if d.get("args"):
        lines.append("\n## Args:")
        for k, v in d["args"].items():
            lines.append("  {}: {}".format(k, v.get("help", "")[:80]))
            if "default" in v:
                lines.append("    default: {}".format(v["default"]))
    if d.get("steps"):
        lines.append("\n## Steps:")
        for i, s in enumerate(d["steps"]):
            lines.append("  {}. {}".format(i + 1, s.get("cmd", "")[:80]))
    return "\n".join(lines)


def _estate_invoke(args):
    name = args.get("intent", "")
    timeout = int(args.get("timeout", 55))
    if not name:
        return "ERROR: intent name required"
    if not _is_valid(name):
        return "ERROR: invalid intent name: {}".format(name)
    d = _load_intent(name)
    if d is None:
        return "ERROR: unknown intent: {}".format(name)
    cmd = [sys.executable, str(HOME / ".estate" / "bin" / "estate-execute"), name]
    for k, v in (args.get("args") or {}).items():
        if not re.match(r"^[a-z_][a-z0-9_]*$", str(k)):
            return "ERROR: invalid arg name: {}".format(k)
        cmd.append("{}={}".format(k, v))
    idp_root = HOME / "Documents" / "code" / "idp"
    try:
        r = subprocess.run(  # noqa: S603  # cmd validated by regex above
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(idp_root),
            check=False,
        )
        out = r.stdout.strip()
        if r.returncode == 0:
            return out if out else "ok"
        err = r.stderr.strip() if r.stderr else ""
        msg = "ERROR (exit {}):\n{}\n{}"
        return msg.format(r.returncode, out, err)
    except subprocess.TimeoutExpired:
        return "ERROR: intent timed out after {}s".format(timeout)
    except Exception as exc:
        return "ERROR: {}".format(exc)


try:
    from datasette import hookimpl
except ImportError:

    def hookimpl(fn):
        return fn


TOOL_DEFS = [
    {
        "name": "estate_list",
        "description": "List all available estate intents.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "estate_show",
        "description": "Show args and description for one intent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "Intent name"},
            },
            "required": ["intent"],
        },
    },
    {
        "name": "estate_invoke",
        "description": "Run an estate intent via the intent system.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "Intent name"},
                "args": {"type": "object", "description": "Intent args", "default": {}},
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds (default 55s)",
                },
            },
            "required": ["intent"],
        },
    },
]

TOOL_FNS = {
    "estate_list": _estate_list,
    "estate_show": _estate_show,
    "estate_invoke": _estate_invoke,
}


@hookimpl
def register_mcp_tools(datasette, mcp):
    for td in TOOL_DEFS:
        fn = TOOL_FNS[td["name"]]

        def make_wrapper(f, td=td):
            def wrapper(kwargs):
                try:
                    result = f(kwargs)
                    return {"content": [{"type": "text", "text": str(result)}]}
                except Exception as exc:
                    err_msg = "ERROR: {}".format(exc)
                    return {
                        "content": [{"type": "text", "text": err_msg}],
                        "isError": True,
                    }

            return wrapper

        mcp.add_tool(
            make_wrapper(fn),
            name=td["name"],
            description=td["description"],
            inputSchema=td["inputSchema"],
        )
