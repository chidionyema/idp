"""crew#539: a chaos template inside a Chaos Mesh Workflow carries no `duration`.

Incident (oke-check 33271070020, 2026-08-29): Kustomization flux-system/chaos stayed not-ready
because the Chaos Mesh admission webhook refused Workflow/observability/langfuse-alert-drill-first-run:
`spec.templates[2]: Invalid value: 480000000000: should not define duration in chaos when using
Workflow, use Template#Deadline instead.` The scheduled twin (kind: Schedule, type: Workflow) carried
the same field and would have been refused the moment it fired. Inside a Workflow the template's
`deadline` is the chaos duration; `duration` is only for a standalone chaos object.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHAOS_KINDS = {
    "podChaos",
    "networkChaos",
    "stressChaos",
    "ioChaos",
    "timeChaos",
    "dnsChaos",
    "httpChaos",
    "kernelChaos",
    "jvmChaos",
    "awsChaos",
    "gcpChaos",
    "blockChaos",
    "physicalmachineChaos",
}


def _workflow_templates():
    for path in sorted((ROOT / "platform").rglob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if not isinstance(doc, dict):
                continue
            kind = doc.get("kind")
            spec = doc.get("spec") or {}
            if kind == "Workflow":
                templates = spec.get("templates") or []
            elif kind == "Schedule" and spec.get("type") == "Workflow":
                templates = (spec.get("workflow") or {}).get("templates") or []
            else:
                continue
            for i, t in enumerate(templates):
                yield path.relative_to(ROOT), i, t


def test_no_workflow_chaos_template_defines_duration():
    bad = []
    seen = 0
    for rel, i, t in _workflow_templates():
        for key in CHAOS_KINDS & set(t):
            seen += 1
            if "duration" in (t.get(key) or {}):
                bad.append(f"{rel} templates[{i}] ({t.get('name')}).{key}.duration")
            assert t.get("deadline"), (
                f"{rel} templates[{i}] ({t.get('name')}): a chaos template in a Workflow needs a "
                "deadline; that is its duration"
            )
    assert seen >= 2, (
        "expected the alert-drill Workflow and its Schedule twin to be scanned"
    )
    assert bad == [], (
        "Chaos Mesh refuses `duration` inside a Workflow template "
        "(use the template's deadline): " + ", ".join(bad)
    )
