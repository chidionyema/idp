"""Every control primitive is guarded: an agent can read it, never land a change to it unsigned.

Founder, 2026-11-13: an agent rewrote the estate's control files with no founder seal (49 commits
on main 2026-11-05..13, 44 by estate-agents[bot]). This test runs the REAL guard list and the REAL
prefix rule bin/idp-ci-guarded-paths applies, so the two cannot drift. Removing a row from
bin/idp-guarded-paths fails here; that removal itself is a guarded change needing X-Idp-Auth.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# One real file per control primitive: what agents read as law, and what decides what lands.
CONTROL_PRIMITIVES = [
    "AGENTS.md",
    "CLAUDE.md",
    "CODEOWNERS",
    ".github/workflows/guarded-paths.yml",
    ".github/workflows/founder-passkey-deploy.yml",
    "docs/keys/founder.pub",
    "bin/claim-gate",
    "bin/claim-open",
    "bin/dof-gate",
    "bin/idp-ci",
    "bin/idp-ci-guarded-paths",
    "bin/idp-guarded-paths",
    "bin/idp-auth",
    "bin/idp-auth-verify",
    "bin/idp-greenlane",
    "bin/estate-memory-enforce",
    "catalog/dof-registry.json",
    "catalog/critical-functions.json",
    "platform/estate/protocolkit/protocolkit/gates.py",
    "platform/estate/memory/handback.py",
    "platform/founder-passkey/worker.js",
    ".githooks/pre-push",
]

# Paths that are NOT control primitives must stay unguarded, or every lane needs a signature.
ORDINARY = [
    "docs/runbooks/greenlane.md",
    "tests/test_control_primitives_are_guarded.py",
    "README.md",
]


def _guards() -> list[str]:
    out = subprocess.run(
        [str(REPO / "bin/idp-guarded-paths")],
        capture_output=True,
        text=True,
        check=True,
    )
    return [g for g in out.stdout.splitlines() if g]


def _guarded(path: str, guards: list[str]) -> bool:
    # Same predicate as bin/idp-ci-guarded-paths: grep -E "^${g}" against the changed path.
    return any(re.match(g, path) for g in guards)


def test_every_control_primitive_exists_and_is_guarded() -> None:
    guards = _guards()
    missing = [p for p in CONTROL_PRIMITIVES if not (REPO / p).exists()]
    assert missing == [], (
        f"control primitive list names files that do not exist: {missing}"
    )
    unguarded = [p for p in CONTROL_PRIMITIVES if not _guarded(p, guards)]
    assert unguarded == [], (
        f"control primitives an agent can change unsigned: {unguarded}"
    )


def test_ordinary_paths_stay_unguarded() -> None:
    guards = _guards()
    over = [p for p in ORDINARY if _guarded(p, guards)]
    assert over == [], f"ordinary paths wrongly need a founder signature: {over}"


def test_unguarded_list_fails_before_this_change() -> None:
    # Falsifier: the guard list as it stood on main 8eaf70d2 leaves AGENTS.md and workflows open.
    old = [
        "platform/edge/otel-endpoint-exception.yaml",
        "platform/edge/inject-otel-endpoint.yaml",
        "platform/edge/require-otel-endpoint.yaml",
        "platform/policies/kyverno/",
        ".githooks/",
        "bin/idp-auth",
        "bin/idp-guarded-paths",
        "bin/idp-ci-guarded-paths",
    ]
    assert not _guarded("AGENTS.md", old)
    assert not _guarded(".github/workflows/argon-guardian-relay.yml", old)
