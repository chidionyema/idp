"""2026-08-29: the chaos Kustomization sat not Ready and the alert-drill job failed with

    Workflow/observability/langfuse-alert-drill-first-run dry-run failed (Forbidden): admission
    webhook "vworkflow.kb.io" denied the request: spec.templates[2]: Invalid value: 480000000000:
    should not define duration in chaos when using Workflow, use Template#Deadline instead.

Inside a Chaos Mesh Workflow (or a Schedule whose workflow embeds one), a chaos template's own
`duration` is refused: the template's `deadline` bounds the run. Both langfuse-alert-drill.yaml
and langfuse-alert-drill-first-run.yaml carried `duration: 8m` beside `deadline: 540s`, so the
whole row stayed red and every drill behind it read silent-green.

The guard sweeps every chaos manifest, not the two that were wrong (LAW 45).
"""
import glob
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAOS = os.path.join(ROOT, "platform", "chaos")

# Every Chaos Mesh chaos kind carries its spec under this key inside a Workflow template.
CHAOS_SPEC_KEYS = (
    "podChaos", "networkChaos", "ioChaos", "timeChaos", "kernelChaos", "stressChaos",
    "dnsChaos", "httpChaos", "jvmChaos", "awsChaos", "gcpChaos", "blockChaos",
    "physicalmachineChaos",
)


def _templates(doc):
    """Workflow templates, whether the doc is a Workflow or a Schedule that embeds one."""
    if not isinstance(doc, dict):
        return []
    spec = doc.get("spec") or {}
    if doc.get("kind") == "Workflow":
        return spec.get("templates") or []
    if doc.get("kind") == "Schedule":
        return ((spec.get("workflow") or {}).get("templates")) or []
    return []


def test_no_chaos_workflow_template_defines_a_duration():
    offenders = []
    for path in sorted(glob.glob(os.path.join(CHAOS, "*.yaml"))):
        for doc in yaml.safe_load_all(open(path)):
            for i, tpl in enumerate(_templates(doc)):
                if not isinstance(tpl, dict):
                    continue
                for key in CHAOS_SPEC_KEYS:
                    block = tpl.get(key)
                    if isinstance(block, dict) and "duration" in block:
                        offenders.append(
                            "%s: %s templates[%d] (%s) %s.duration=%r — use the template's "
                            "deadline, vworkflow.kb.io refuses this"
                            % (os.path.basename(path), doc.get("kind"), i,
                               tpl.get("name"), key, block["duration"])
                        )
    assert not offenders, "\n".join(offenders)


def test_the_guard_can_see_the_manifests_it_grades():
    """A sweep over an empty list is not a pass (silent green is the defect class)."""
    found = [
        1
        for path in glob.glob(os.path.join(CHAOS, "*.yaml"))
        for doc in yaml.safe_load_all(open(path))
        for tpl in _templates(doc)
        if isinstance(tpl, dict) and any(k in tpl for k in CHAOS_SPEC_KEYS)
    ]
    assert found, "no chaos template found under platform/chaos: the guard would pass on nothing"
