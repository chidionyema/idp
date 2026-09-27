"""Every portal button starts a workflow that exists, and passes it only inputs it declares.

The generator that kept backstage/templates/founder-actions/ in step with the workflows was
removed (462ed10f), so the templates are hand-kept and nothing noticed when one drifted: a button
naming a deleted workflow, or an input the workflow never declared, fails only when the founder
presses it. This reads every template and the workflow it names.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = sorted(
    (ROOT / "backstage/templates/founder-actions").glob("*/template.yaml")
)
WORKFLOWS = ROOT / ".github/workflows"
# Buttons already dead when this test arrived, tracked to be removed or rewired (crew#975 CP29).
# A new one fails; this list may only shrink.
KNOWN_DEAD = {"estate-bootstrap-preflight"}


def _dispatches(path: Path) -> list[dict]:
    spec = yaml.safe_load(path.read_text())["spec"]
    return [
        s["input"]
        for s in spec["steps"]
        if s.get("action") == "github:actions:dispatch"
    ]


def _params(path: Path) -> set[str]:
    spec = yaml.safe_load(path.read_text())["spec"]
    return {
        k
        for page in spec.get("parameters") or []
        for k in (page.get("properties") or {})
    }


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.parent.name)
def test_the_button_starts_a_workflow_that_can_be_started(path):
    for step in _dispatches(path):
        wf_path = WORKFLOWS / step["workflowId"]
        if not wf_path.exists() and path.parent.name in KNOWN_DEAD:
            pytest.xfail(f"{step['workflowId']} is gone: a dead button (crew#975 CP29)")
        assert wf_path.exists(), (
            f"the button starts {step['workflowId']}, which does not exist"
        )
        on = yaml.safe_load(wf_path.read_text())[True]
        assert "workflow_dispatch" in on, (
            f"{step['workflowId']} cannot be started by hand"
        )
        declared = set(((on["workflow_dispatch"] or {}).get("inputs")) or {})
        passed = set(step.get("workflowInputs") or {})
        assert passed <= declared, (
            f"passes inputs the workflow does not declare: {passed - declared}"
        )


def test_the_known_dead_list_only_names_buttons_that_are_still_dead():
    for name in KNOWN_DEAD:
        path = ROOT / f"backstage/templates/founder-actions/{name}/template.yaml"
        assert path.exists() and any(
            not (WORKFLOWS / s["workflowId"]).exists() for s in _dispatches(path)
        ), f"{name} was fixed or removed: take it off KNOWN_DEAD"


def test_the_agent_button_asks_for_everything_the_agent_workflow_requires():
    path = ROOT / "backstage/templates/founder-actions/agent-sandbox/template.yaml"
    (step,) = _dispatches(path)
    on = yaml.safe_load((WORKFLOWS / "agent-sandbox.yml").read_text())[True]
    required = {
        k for k, v in on["workflow_dispatch"]["inputs"].items() if v.get("required")
    }
    assert required <= set(step["workflowInputs"]) and required <= _params(path)
    harness = yaml.safe_load(path.read_text())["spec"]["parameters"][0]["properties"][
        "harness"
    ]
    assert set(harness["enum"]) == set(
        on["workflow_dispatch"]["inputs"]["harness"]["options"]
    )
