"""Load the consult plane by file path and seed sys.modules.

`platform/` has no __init__.py on purpose (idp#3564): a package named
`platform` collides with the stdlib module `platform` the moment anything
imports it bare, which pytest itself does at startup. Seeding sys.modules
under the real dotted names means the `from platform.consult_plane...`
imports hit the sys.modules fast path instead of re-resolving through the
poisoned bare `platform` name.

This is the same technique tests/judge/test_drift.py uses for
platform/eval/judge_drift.py, generalised so every consult-plane test loads
the plane the same way instead of each file carrying its own copy of the
seed loop.

The parent package is seeded first with a __path__, so a module seeded later
can still resolve its own relative imports through the normal finder.
"""

from __future__ import annotations

import importlib.util
import os
import sys

IDP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Seeded in dependency order. The order is not load-bearing for correctness
# (the parent __path__ lets a later module find an earlier one), but it keeps
# the failure of a missing file pointing at the module that wanted it.
CONSULT_PLANE_MODULES = (
    "budget_ledger",
    "search_twin",
    "dialectical_consult",
    "founder_firewall",
    "discovery_poe",
    "stuck_router",
    "service",
    "dream_reflect",
    "telegram_vip",
)


def _seed(dotted: str, path: str, is_package: bool) -> None:
    if dotted in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(dotted, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {dotted} from {path}")
    module = importlib.util.module_from_spec(spec)
    if is_package:
        # Make it a package so the relative imports inside its modules
        # resolve against it.
        module.__path__ = [os.path.dirname(path)]
    sys.modules[dotted] = module
    spec.loader.exec_module(module)


def seed_consult_plane() -> None:
    """Make `platform.consult_plane.*` importable in this interpreter."""
    pkg_dir = os.path.join(IDP_ROOT, "platform", "consult_plane")
    _seed(
        "platform.consult_plane",
        os.path.join(pkg_dir, "__init__.py"),
        is_package=True,
    )
    for name in CONSULT_PLANE_MODULES:
        path = os.path.join(pkg_dir, f"{name}.py")
        if not os.path.exists(path):
            continue
        _seed(f"platform.consult_plane.{name}", path, is_package=False)


seed_consult_plane()
