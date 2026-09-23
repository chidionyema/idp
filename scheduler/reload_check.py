"""Judge a Dagster `reloadWorkspace` reply: 0 when every code location loads, 1 otherwise.

crew#85, 2026-08-27 07:45Z: the webserver kept the code location it imported before idp#316
(ImportError: load_gate) for two hours while the tree on disk was correct. `bin/scheduler-up`
now reloads the workspace on every tick and pipes the reply here; a location that does not
import, a GraphQL error, or a reply that is not a workspace is a stated refusal, never a
"webserver already up".
"""
from __future__ import annotations

import json
import sys


def verdict(reply: str) -> tuple[int, list[str]]:
    """(exit code, lines to print) for one reloadWorkspace reply body."""
    try:
        doc = json.loads(reply)
    except ValueError as e:
        return 1, [f"reloadWorkspace reply is not JSON: {e}"]
    if doc.get("errors"):
        return 1, ["reloadWorkspace refused: " + "; ".join(str(e.get("message", e))[:200] for e in doc["errors"])]
    w = (doc.get("data") or {}).get("reloadWorkspace") or {}
    if w.get("__typename") != "Workspace":
        return 1, [f"reloadWorkspace returned {w.get('__typename') or 'nothing'}: {str(w.get('message', ''))[:200]}"]
    bad = [e for e in w.get("locationEntries", [])
           if (e.get("locationOrLoadError") or {}).get("__typename") == "PythonError"]
    lines = [f"code location {e['name']} does not load: "
             f"{e['locationOrLoadError'].get('message', '').splitlines()[0][:200]}" for e in bad]
    if not w.get("locationEntries"):
        return 1, ["reloadWorkspace returned a workspace with no code location"]
    return (1 if bad else 0), lines


if __name__ == "__main__":
    rc, lines = verdict(sys.stdin.read())
    print("\n".join(lines))
    sys.exit(rc)
