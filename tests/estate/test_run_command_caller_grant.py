"""A workflow that opens the OCI Run Command door needs the caller-side grant (idp#7387).

MEASURED 2026-10-29. The recovery-data workflow drives the recovery host with
`oci instance-agent command create`, and the create came back 404 NotAuthorizedOrNotFound: the
request never reached the host, so the copy of the surviving volumes never started. The CI
dynamic group `estate-github-actions` held exactly one permission, `manage secret-family`.

Run Command is two permissions, and they are not substitutes for each other:

    caller   : manage instance-agent-command-family         -- create and track the command
    instance : use instance-agent-command-execution-family  -- poll and execute it

The instance-side half was declared for the recovery host; the caller-side half was declared for
nobody. The mistake is invisible in a diff -- both statements say "instance-agent-command" -- so
it is graded here instead: every workflow that opens the Run Command door must have a declared
caller-side grant for the CI dynamic group.

This is the falsifier, not the fix: the test fails against the repository that has the workflow
and no caller-side grant, and passes once the grant is declared. A gate that cannot fail is not
a gate (AGENTS.md section 3).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = REPO / ".github" / "workflows"
TERRAFORM = REPO / "platform" / "oci"

# The door: a workflow that issues a Run Command.
OPENS_THE_DOOR = re.compile(r"instance-agent\s+command\s+create|instanceAgentCommands")

# The permission the caller needs, and the permission the instance needs. Both are searched for,
# so the test can also see a door declared with the wrong half.
CALLER_FAMILY = "manage instance-agent-command-family"
INSTANCE_FAMILY = "use instance-agent-command-execution-family"

# The CI dynamic group is the principal the workflows authenticate as.
CI_GROUP = "oci_identity_dynamic_group.github_actions.name"

STATEMENT = re.compile(r'"(Allow [^"]*instance-agent-command[^"]*)"')


def _workflows_opening_the_door() -> list[Path]:
    return [
        path
        for path in sorted(WORKFLOWS.glob("*.y*ml"))
        if OPENS_THE_DOOR.search(path.read_text())
    ]


def _declared_statements() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for path in sorted(TERRAFORM.rglob("*.tf")):
        for match in STATEMENT.finditer(path.read_text()):
            found.append((path, match.group(1)))
    return found


def _caller_grants() -> list[tuple[Path, str]]:
    return [(p, s) for p, s in _declared_statements() if CALLER_FAMILY in s]


def test_a_workflow_opens_the_run_command_door() -> None:
    """The gate must not be vacuous: if no workflow opens the door, the grant below is unused."""
    assert _workflows_opening_the_door(), (
        "no workflow opens the OCI Run Command door; this gate no longer grades anything"
    )


def test_the_caller_side_grant_is_declared() -> None:
    """The CI principal must hold manage instance-agent-command-family."""
    grants = _caller_grants()
    assert grants, (
        f"no declared '{CALLER_FAMILY}' grant in {TERRAFORM.relative_to(REPO)}; "
        "a workflow that creates a Run Command is refused with NotAuthorizedOrNotFound"
    )
    assert any(CI_GROUP in statement for _p, statement in grants), (
        f"the '{CALLER_FAMILY}' grant does not name the CI dynamic group ({CI_GROUP}): "
        f"{[s for _p, s in grants]}"
    )


def test_the_caller_grant_is_not_the_instance_side_one() -> None:
    """The two families are different permissions; the instance-side one does not open the door."""
    ci_statements = [s for _p, s in _declared_statements() if CI_GROUP in s]
    assert ci_statements, "the CI dynamic group holds no declared statement at all"
    assert any(CALLER_FAMILY in s for s in ci_statements), (
        f"the CI group is granted only the instance-side family ('{INSTANCE_FAMILY}'), "
        "which does not authorise creating a command"
    )


def test_every_run_command_workflow_has_the_caller_grant() -> None:
    """No workflow may open a door the declared IAM does not open."""
    grants = _caller_grants()
    for workflow in _workflows_opening_the_door():
        assert grants, (
            f"{workflow.relative_to(REPO)} opens the Run Command door and no caller-side "
            f"grant ('{CALLER_FAMILY}') is declared"
        )
