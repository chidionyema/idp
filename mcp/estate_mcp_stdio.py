#!/usr/bin/env python3
"""estate_mcp_stdio.py -- the pi runtime's stdio MCP entrypoint.

This is the sanctioned replacement for the orphaned ~/estate-mcp-stdio.py (dated 2026-09-27):
that installed copy pointed at a repo file (mcp/estate_mcp_stdio.py) that was deleted, and it
was NOT the wired estate server -- it reimplemented estate_invoke by shelling straight to
~/.estate/bin/estate-execute with no PoBR gate. Section 6 (one of each layer) forbids leaving
two, so this file restores the single entrypoint AND routes every tool through the wired
mcp.plugins.estate_mcp module, which is the only place the class:mutate PoBR action gate and
the intent library live. There is no gate logic here: this is a thin stdio transport over the
one wired module.

Protocol: the same JSON-RPC-over-stdio pi already speaks (initialize / tools/list / tools/call),
so the runtime keeps working unchanged. The difference is that estate_invoke now answers through
the wired _estate_invoke, which refuses a class:mutate intent in a LIVE session that has not
first produced an admitted PoBR receipt (hypotheses + counterfactual + calibrated posterior).

Import contract: mcp.plugins.estate_mcp does `from mcp.plugins import pobr_grant` and
`from mcp.plugins.estate_executor import CEILING_SEC`, so mcp must be importable as a package.
The checkout root is resolved first from IDP_ROOT, then from this file's own location
(../..), so the entrypoint imported from the installed ~/ copy still resolves the wired
module from the checkout it names, never from a stale sibling.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HOME = Path.home()
_DEFAULT_IDP = HOME / "Documents" / "code" / "idp"
# The checkout that owns the wired module. Explicit env beats the estate's conventional
# checkout path beats the checkout this file happens to live under. The installed copy in
# ~ points at the MAIN checkout, never at a lane worktree that vanishes on merge; a caller
# with no root and no checkout gets a loud failure, never a silent stale import.
_IDP_ROOT = Path(
    os.environ.get("IDP_ROOT") or os.environ.get("ESTATE_IDP") or _DEFAULT_IDP
)


def _load_wired_module():
    """Import mcp.plugins.estate_mcp from the checkout, as a package.

    The wired module needs its mcp/ package context (mcp.plugins.pobr_grant etc.), so we put
    the checkout root on sys.path and import by dotted name rather than by file path. Returns
    the module, or raises ImportError with a message naming the missing root -- a RUNNABLE
    entrypoint must never answer 'ok' from a module it could not load.
    """
    root = _IDP_ROOT
    if not (root / "mcp" / "__init__.py").is_file():
        raise ImportError(
            "estate_mcp_stdio: wired module not found -- not a checkout at {} "
            "(set IDP_ROOT)".format(root)
        )
    sys.path.insert(0, str(root))
    try:
        from mcp.plugins import estate_mcp  # noqa: F401
    except Exception as exc:  # noqa: BLE001 - a genuine import failure must be visible
        raise ImportError(
            "estate_mcp_stdio: could not import mcp.plugins.estate_mcp from {}: {}".format(
                root, exc
            )
        ) from exc
    return estate_mcp


# Resolve once at import so a load failure is immediate and visible at start-up, not deferred
# to the first tool call. A pi session whose entrypoint cannot load the wired module must see
# it on initialize, not discover it mid-task.
try:
    _WIRED = _load_wired_module()
except ImportError as exc:
    _WIRED = None
    _LOAD_ERROR = str(exc)


def _text(value, is_error=False):
    return {"content": [{"type": "text", "text": value}], "isError": is_error}


def _call(name, args):
    # A wired module that failed to load is an outage, named on every tool call.
    if _WIRED is None:
        return _text("ERROR: {}".format(_LOAD_ERROR), True)

    if name == "estate_list":
        return _text(_WIRED._estate_list(args))
    if name == "estate_show":
        return _text(_WIRED._estate_show(args))
    if name == "estate_invoke":
        # The ONE wired path: _estate_invoke carries the class:mutate PoBR gate. The legacy
        # arg_<intent>_<arg> encoding is translated into the wired {args: {k: v}} shape, and
        # the session_id (if the caller supplied one) is passed through unchanged so
        # _resolve_caller_session can consult the plan ledger for liveness.
        intent = (args.get("intent") or args.get("name") or "").strip()
        if not intent:
            return _text(_WIRED._estate_invoke({}), True)
        argdict = {}
        prefix = "arg_{}_".format(intent)
        for k, v in args.items():
            if k.startswith(prefix):
                argdict[k[len(prefix) :]] = v
        wired_args = {"intent": intent, "args": argdict}
        if args.get("session_id"):
            wired_args["session_id"] = args["session_id"]
        if args.get("timeout"):
            wired_args["timeout"] = args["timeout"]
        return _text(_WIRED._estate_invoke(wired_args))
    # pobr_submit / pobr_status / capability_* are the receipt-building and registry tools the
    # wired module already defines; route them through the same module so one entrypoint serves
    # the whole surface instead of two.
    fn = getattr(_WIRED, "_" + name, None)
    if fn is not None:
        return _text(str(fn(args)))
    return _text("unknown tool: {}".format(name), True)


def _make_tools():
    if _WIRED is None:
        return []
    # One source of truth for tool schemas: the wired module's TOOL_DEFS. The legacy
    # estate_pending/estate_create (human-approval-only) tools are dropped here on purpose:
    # the wired module never exposed them, and re-adding an approval tool the agent could call
    # is the exact defect the 2026-09-27 replacement fixed.
    tools = []
    for td in _WIRED.TOOL_DEFS:
        tools.append(
            {
                "name": td["name"],
                "description": td["description"],
                "inputSchema": td["inputSchema"],
            }
        )
    return tools


def _emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _serve():
    for raw in sys.stdin:
        try:
            req = json.loads(raw)
        except ValueError:
            continue
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            _emit(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "estate", "version": "0.5"},
                    },
                }
            )
        elif method == "tools/list":
            _emit({"jsonrpc": "2.0", "id": rid, "result": {"tools": _make_tools()}})
        elif method == "tools/call":
            params = req.get("params") or {}
            try:
                result = _call(params.get("name", ""), params.get("arguments") or {})
            except Exception as exc:  # noqa: BLE001 - a tool error is an answer, never a hang
                result = _text("error: {}".format(exc), True)
            _emit({"jsonrpc": "2.0", "id": rid, "result": result})
        elif rid is not None:
            _emit(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {
                        "code": -32601,
                        "message": "method not found: {}".format(method),
                    },
                }
            )


if __name__ == "__main__":
    if _WIRED is None:
        # Fail loud and visible on a broken load, before pi reads any tool list.
        sys.stderr.write("{}\n".format(_LOAD_ERROR))
        sys.stderr.flush()
        sys.exit(2)
    _serve()
