"""The live plan-link state, for the Fleet page and for Face.

ONE implementation of the numbers: the estate's own governance module
(platform/estate/governance/plan_links.py) is loaded by path and asked for the state. This file
only adapts it to the plugin's envelope, because a read that cannot produce an answer says so
rather than returning an empty board -- an empty board and a broken board are different facts
and the founder must be able to tell them apart.

The module is loaded BY PATH, for the same reason the protocol kit is: a name can be shadowed by
a namespace package on sys.path, a path cannot.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

_MODULE_NAME = "estate_plan_links_governance"
_CACHE: dict[str, Any] = {}


def _repo_root() -> Path:
    """Where the estate's repository is on this host."""
    env = os.environ.get("ESTATE_REPO_ROOT", "").strip()
    if env:
        return Path(env).expanduser()
    # .../backstage/plugins/fleetview-backend/src/fleetview_backend/plan_links.py -> the repo root
    return Path(__file__).resolve().parents[5]


def _load_governance():
    """The estate's governance module, loaded by path."""
    path = _repo_root() / "platform" / "estate" / "governance" / "plan_links.py"
    key = str(path)
    if key in _CACHE:
        return _CACHE[key]
    if not path.is_file():
        raise FileNotFoundError(f"the plan-link module is not on this host: {path}")
    pkg = str(path.parent.parent)
    if pkg not in sys.path:
        sys.path.insert(0, pkg)
    spec = importlib.util.spec_from_file_location(
        _MODULE_NAME + "_" + key.replace("/", "_").replace(".", "_"), path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"the plan-link module could not be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CACHE[key] = module
    return module


def plan_link_state() -> dict[str, Any]:
    """The live state, or an honest reason why there is none."""
    try:
        module = _load_governance()
        state = module.state(None)
    except Exception as exc:  # noqa: BLE001 - a dead source says so; the page must be able to tell
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "sessions": 0,
            "linked": 0,
            "unlinked": 0,
            "violations": 0,
            "gaps": 0,
            "summary": "plan links: unavailable",
            "rows": [],
        }
    return {"available": True, "error": None, **state}
