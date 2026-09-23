"""crew#284 CP3: the live worker must register what the CLI can start.

Rung 4 (incident test): `sb run --branches 3` started BranchParentWorkflow on
the estate queue while engine/worker.py served only SessionWorkflow, so the
run sat unpicked with no error. The rule is checked against the module the
launchd job imports, not a copy of its list.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from temporalio import activity

from sovereign.engine import worker
from sovereign.engine.workflow import SessionWorkflow
from sovereign.shadow import workflow as shadow_workflow
from sovereign.shadow.workflow import BranchChildWorkflow, BranchParentWorkflow


def _registered_activity_names() -> set[str]:
    return {activity._Definition.from_callable(fn).name for fn in worker.ACTIVITIES}  # type: ignore[attr-defined]


def test_branch_workflows_registered() -> None:
    assert {SessionWorkflow, BranchParentWorkflow, BranchChildWorkflow} <= set(worker.WORKFLOWS)


def test_every_shadow_activity_the_workflow_executes_is_registered() -> None:
    src = inspect.getsource(shadow_workflow)
    # activities are named by string: workflow.execute_activity(\n    "branch_fork", ...
    called = set(re.findall(r"execute_activity\(\s*\"([a-z_]+)\"", src))
    assert called, "no execute_activity calls found; the regex is stale"
    names = _registered_activity_names()
    missing = called - names
    assert not missing, f"shadow workflow calls activities the worker does not register: {sorted(missing)}"


def test_rule_is_documented_next_to_the_list() -> None:
    src = Path(worker.__file__).read_text()
    assert "WORKFLOWS = [" in src and "crew#284" in src
