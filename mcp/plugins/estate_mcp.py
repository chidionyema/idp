#!/usr/bin/env python3
from __future__ import annotations
import inspect
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import typing
import yaml
from pathlib import Path

try:
    from mcp.plugins import pobr_grant

except ImportError:
    pobr_grant = None  # type: ignore

HOME = Path.home()
# The laptop installs the library at ~/.estate/intents. The estate-mcp image has no ~/.estate
# and carries the committed library at /app/intents instead (estate-mcp.Dockerfile); before that,
# production estate_list answered "# 0 intents available" (measured 2026-10-01 in the pod).
INTENTS = Path(os.environ.get("ESTATE_INTENTS_DIR") or HOME / ".estate" / "intents")
# The executor's own ledger: how often each intent has run, so the search ranks the intents
# agents actually reuse above the one-offs (1822 runs, 387 of 537 intents run exactly once,
# measured 2026-09-30).
ESTATE_DB = HOME / ".estate" / "estate.db"
MAX_MATCHES = 12
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


_FILLER = frozenset(
    "a an the for to of in on and or with from by is it its my this that".split()
)


def _words(text):
    return [
        w for w in re.split(r"[^a-z0-9]+", str(text).lower()) if w and w not in _FILLER
    ]


def _same(q, t):
    """One word matches another exactly or on a shared stem of five letters or more:
    "encode" finds "encoding", "compare" finds "comparator", "parse" finds "parser", and
    "compare" does not find "comp"."""
    return q == t or len(os.path.commonprefix([q, t])) >= 5


def _covered(query_words, text_words):
    """The query words the text covers."""
    return {q for q in query_words if any(_same(q, t) for t in text_words)}


def _run_counts():
    try:
        con = sqlite3.connect("file:{}?mode=ro".format(ESTATE_DB), uri=True)
        try:
            return dict(
                con.execute("SELECT intent, count(*) FROM intent_tickets GROUP BY 1")
            )
        finally:
            con.close()
    except sqlite3.Error:
        return {}


def _harv_parts():
    """The harv shelf: sealed, tested functions from open-source libraries. Read straight from
    the registry index, newest version of each name."""
    home = Path(os.environ.get("HARV_HOME") or HOME / ".estate" / "harv")
    db = home / "registry" / "index.db"
    if not db.exists():
        return [], "no harv shelf at {}".format(db)
    try:
        con = sqlite3.connect("file:{}?mode=ro".format(db), uri=True)
        try:
            rows = con.execute(
                "SELECT name, version, tier FROM artifacts ORDER BY created"
            ).fetchall()
        finally:
            con.close()
    except sqlite3.Error as exc:
        return [], "harv shelf at {} unreadable: {}".format(db, exc)
    latest = {}
    for name, version, tier in rows:
        latest[name] = (version, tier)
    return [{"name": n, "version": v, "tier": t} for n, (v, t) in latest.items()], None


def _find(query):
    """Everything the estate already has that matches `query`: intents and harv parts, ranked
    by how many query words they cover, then by how often the intent has been reused."""
    q = _words(query)
    if not q:
        return (
            '# nothing in the estate matches "{}"\n'
            'Only filler words were given: say what you need, e.g. "base64 encode".'
        ).format(query)
    runs = _run_counts()
    parts, shelf_error = _harv_parts()
    cands = []
    for i in _load_intents():
        in_name = _covered(q, _words(i["name"]))
        cands.append(
            (in_name | _covered(q, _words(i["description"])), in_name, "intent", i)
        )
    for p in parts:
        cover = _covered(q, _words(p["name"]))
        cands.append((cover, cover, "part", p))
    # A word that matches almost everything ("numbers", "status") says little; a rare one
    # ("levenshtein", "base64") says a lot. Each covered word counts by its rarity (IDF).
    n = len(cands) or 1
    weight = {
        w: math.log((n + 1) / (1 + sum(1 for c in cands if w in c[0]))) for w in q
    }
    found = []
    for cover, in_name, kind, x in cands:
        if cover:
            used = runs.get(x["name"], 0) if kind == "intent" else 0
            score = sum(weight[w] for w in cover)
            found.append((len(cover), round(score, 6), len(in_name), used, kind, x))
    # A shelf that could not be read is said, never shown as "no parts match".
    note = [
        "NOTE: {}; harv parts are missing from these results.".format(shelf_error),
        "",
    ]
    note = note if shelf_error else []
    if not found:
        return "\n".join(
            ['# nothing in the estate matches "{}"'.format(query)]
            + note
            + [
                "No intent and no harv part covers it. Check the words, then build it once "
                "as an intent so the next agent finds it here."
            ]
        )
    # Most of the request covered first; among those, the rarer words; then covered by the
    # name; then the most reused.
    found.sort(key=lambda f: (-f[0], -f[1], -f[2], -f[3], f[5]["name"]))
    lines = [
        '# {} match(es) for "{}" (best first)'.format(len(found), query),
        "",
    ] + note
    for _n, _score, _in_name, used, kind, x in found[:MAX_MATCHES]:
        if kind == "intent":
            lines.append("## intent {} (run {} time(s))".format(x["name"], used))
            lines.append(x["description"][:160])
            argl = ", ".join('"{}": ...'.format(a) for a in x["args"])
            lines.append(
                'call: estate_invoke {{"intent": "{}", "args": {{{}}}}}'.format(
                    x["name"], argl
                )
            )
        else:
            lines.append(
                "## harv part {} {} ({}: tested, sealed, no network/files/clock)".format(
                    x["name"], x["version"], x["tier"]
                )
            )
            lines.append(
                'call: estate_invoke {{"intent": "harv", "args": {{"verb": "run", '
                '"name": "{}", "text": "<input>"}}}}'.format(x["name"])
            )
        lines.append("")
    if len(found) > MAX_MATCHES:
        lines.append(
            "{} more; add words to narrow it.".format(len(found) - MAX_MATCHES)
        )
    return "\n".join(lines)


def _estate_list(args):
    query = (args or {}).get("query", "")
    if query:
        return _find(query)
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
        "description": (
            "Find what the estate already has before building anything. Pass `query` in plain "
            'words ("base64 encode", "ci status for a pr") to get the matching intents and '
            "harv parts (tested, sealed functions from open-source libraries), best first, "
            "each with the exact estate_invoke call. Without `query`: every intent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you need, in plain words",
                },
            },
        },
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
    {
        "name": "pobr_submit",
        "description": "Submit a PoBR receipt to consume the session grant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID matching the grant",
                },
                "receipt": {
                    "type": "object",
                    "description": "PoBR receipt dict from the reasoning trace",
                    "default": {},
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "pobr_status",
        "description": "Check PoBR grant status for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to check",
                },
            },
            "required": ["session_id"],
        },
    },
]


def _pobr_submit(args):
    if pobr_grant is None:
        return "ERROR: pobr_grant not available"
    session_id = args.get("session_id", "")
    receipt = args.get("receipt", {})
    result = pobr_grant.pobr_submit_tool(session_id, receipt)
    return str(result)


def _pobr_status(args):
    if pobr_grant is None:
        return "ERROR: pobr_grant not available"
    session_id = args.get("session_id", "")
    result = pobr_grant.grant_status(session_id)
    return str(result)


TOOL_FNS = {
    "estate_list": _estate_list,
    "estate_show": _estate_show,
    "estate_invoke": _estate_invoke,
    "pobr_submit": _pobr_submit,
    "pobr_status": _pobr_status,
}


@hookimpl
def register_mcp_tools(datasette, mcp):
    for td in TOOL_DEFS:
        fn = TOOL_FNS[td["name"]]

        def make_wrapper(f, td=td):
            def wrapper(kwargs):
                tool_name = td["name"]

                # --- PoBR grant gate ---
                if pobr_grant is not None and pobr_grant.requires_grant(tool_name):
                    session_id = kwargs.get("session_id", "")
                    if not session_id:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "PoBR grant required for {}. "
                                        "Call pobr_submit or pobr_status first."
                                    ).format(tool_name),
                                }
                            ],
                            "isError": True,
                        }
                    check = pobr_grant.check_grant(session_id)
                    if not check.get("valid"):
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "PoBR grant check failed: {}".format(
                                        check.get("reason", "unknown")
                                    ),
                                }
                            ],
                            "isError": True,
                        }
                # --- end PoBR gate ---

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
            _as_mcp_tool(make_wrapper(fn), td),
            name=td["name"],
            description=td["description"],
        )


_JSON_TYPES = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _as_mcp_tool(wrapper, td):
    """The MCP SDK 2.x `add_tool` takes no `inputSchema`: it reads the schema off the function's
    signature. estate-mcp crash-looped on `unexpected keyword argument 'inputSchema'` from
    2026-09-28 (datasette-mcp pulls `mcp>=2.0.0` unpinned). Build that signature from the tool's
    own inputSchema, so the declared schema stays the one source, and turn an error result into
    an exception, which the SDK reports as isError."""
    schema = td["inputSchema"]
    required = set(schema.get("required", []))
    params, annotations = [], {}
    for name, spec in schema.get("properties", {}).items():
        typ = _JSON_TYPES.get(spec.get("type"), object)
        if name in required:
            param = inspect.Parameter(
                name, inspect.Parameter.KEYWORD_ONLY, annotation=typ
            )
        else:
            typ = typing.Optional[typ]
            param = inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=spec.get("default"),
                annotation=typ,
            )
        params.append(param)
        annotations[name] = typ

    def tool(**kwargs):
        out = wrapper({k: v for k, v in kwargs.items() if v is not None})
        text = out["content"][0]["text"]
        if out.get("isError"):
            raise RuntimeError(text)
        return text

    tool.__name__ = td["name"]
    tool.__doc__ = td["description"]
    tool.__signature__ = inspect.Signature(params, return_annotation=str)
    tool.__annotations__ = {**annotations, "return": str}
    return tool
