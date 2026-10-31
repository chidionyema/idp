#!/usr/bin/env python3
"""dept-launch -- one parameterised path from "launch department <name>" to the spine files.

WHY THIS EXISTS. The Media Department charter v1 (2026-10-28, idp#7395) makes Media the first of
a family of autonomous estate departments, and its M7 is the reuse test: "a second department uses
the same spine without copying infrastructure." The stamped decision (docs/decisions/
2026-10-30-the-infrastructure-department-and-the-stamped-vision.md) defines what a department IS:
a role, not a model -- a standing claim that owns outcomes, not activity, and is visibly on duty.
The first department cost a hand-built PR claimed on six paths; the founder's ask (2026-10-31,
idp#7661) is that the next one -- research, science, media-engineering -- costs one command.

WHAT IT WRITES, and nothing more:

    platform/department/<name>.yaml    the department as configuration over the ONE contract
                                       (platform/department/contract.py): roles, authorization
                                       doors, per-day cap. workers EMPTY -- fail closed.
    docs/departments/<name>/README.md  the department's page: status SHADOW, what a department is
                                       here, and the path from baseline to granted workers.

WHAT IT NEVER DOES. It never talks to a cluster, never starts a workload, never grants a worker
and never edits the contract, the schemas or another department's files. A launched department is
shadow: every write to its ledger is refused as unauthorized_write until a capability-scoped claim
of its own grants workers, wired to the existing Temporal workers in the same change (the M2
pattern). After `write`, the path to main is claim-open + lane-submit (AGENTS.md sections 2, 5).

    dept-launch.py plan   --name <name> [--title <title>] [--cap-usd 10.0] [--repo <path>]
    dept-launch.py write  --name <name> [...]
    dept-launch.py verify --name <name> [--repo <path>]

plan (the default) prints every CREATE and writes nothing. write writes, then verifies the
scaffold against the real contract and removes what it wrote if that fails. verify is a read-only
gate over a committed department, one line per declaration, exit 1 per missing or broken one --
so it can fail on the defect it exists to prevent.

Refusals are typed, one per line, because a launcher an agent drives must be greppable:
invalid_department_id, invalid_cap, repo_not_found, spine_missing, department_exists,
verify_failed.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SPINE_SCHEMAS = (
    "envelope",
    "objective",
    "opportunity",
    "experiment",
    "artifact",
    "review",
    "decision",
    "outcome",
    "event",
)

# The spine's standard role skeleton: the same nine roles media.yaml carries, because the roles
# are the contract's states and kinds given names, not a per-department invention (charter M7:
# same schemas, same workflow; a department's own evaluators and policies arrive with its workers).
ROLES = {
    "portfolio-governor": {
        "states": ["NEW", "TRIAGED", "BLOCKED", "PARKED", "REJECTED"],
        "kinds": ["objective", "opportunity", "event"],
    },
    "research-scout": {
        "states": ["RESEARCHING", "BLOCKED"],
        "kinds": ["opportunity", "experiment", "event"],
    },
    "creative-director": {
        "states": ["RESEARCHING", "PROTOTYPING"],
        "kinds": ["experiment", "event"],
    },
    "prototype-studio": {
        "states": ["PROTOTYPING", "BLOCKED"],
        "kinds": ["artifact", "event"],
    },
    "evaluator": {
        "states": ["EVALUATING", "PROPOSED", "PROTOTYPING", "REJECTED"],
        "kinds": ["review", "event"],
    },
    "authorization-door": {
        "states": ["APPROVED", "REJECTED", "PARKED"],
        "kinds": ["decision", "event"],
    },
    "delivery": {
        "states": ["SHIPPING", "VERIFYING", "BLOCKED"],
        "kinds": ["artifact", "event"],
    },
    "verifier": {
        "states": ["OPERATING", "BLOCKED"],
        "kinds": ["review", "event"],
    },
    "learning-loop": {
        "states": ["LEARNING", "TRIAGED", "PARKED"],
        "kinds": ["outcome", "event"],
    },
}


def refuse(code: str, reason: str) -> int:
    print(f"REFUSED {code}: {reason}")
    return 1
