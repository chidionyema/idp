"""Incident test (rung 4), crew#396.

The 07:00Z cluster-state receipt on 2026-08-27 listed six Failed kini-state pods from the
04:30Z and 04:45Z Jobs, both run on the image before idp#313 carried AGENTS.md. Nothing had
failed for two hours, but ``failedJobsHistoryLimit`` keeps the last two failed Jobs and the
receipt counts their pods under ``pods_not_ready``, so the estate read red on history.

Rule: every CronJob under platform/ sets ``jobTemplate.spec.ttlSecondsAfterFinished`` to at
most a day, so Kubernetes removes finished Jobs and their pods and the receipt carries live
state only. The receipts themselves keep each failure's ``last_log`` (idp#333).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = ROOT / "platform"
MAX_TTL_SECONDS = 86_400


def cronjobs(root: Path) -> list[tuple[Path, dict]]:
    found: list[tuple[Path, dict]] = []
    for path in sorted(root.rglob("*.yaml")):
        try:
            docs = list(yaml.safe_load_all(path.read_text()))
        except yaml.YAMLError:
            continue
        for doc in docs:
            if isinstance(doc, dict) and doc.get("kind") == "CronJob":
                found.append((path, doc))
    return found


def ttl_verdict(doc: dict) -> str | None:
    """None when the CronJob is fine, otherwise the reason it fails the rule."""
    spec = ((doc.get("spec") or {}).get("jobTemplate") or {}).get("spec") or {}
    ttl = spec.get("ttlSecondsAfterFinished")
    if ttl is None:
        return "no jobTemplate.spec.ttlSecondsAfterFinished: finished Jobs and their pods stay in the receipt"
    if not isinstance(ttl, int) or ttl <= 0 or ttl > MAX_TTL_SECONDS:
        return (
            f"ttlSecondsAfterFinished={ttl!r} is not an integer in 1..{MAX_TTL_SECONDS}"
        )
    return None


def test_every_platform_cronjob_removes_its_finished_jobs() -> None:
    found = cronjobs(PLATFORM)
    assert found, "no CronJob under platform/: the sweep denominator is zero"
    bad = [
        (str(p.relative_to(ROOT)), doc["metadata"]["name"], v)
        for p, doc in found
        if (v := ttl_verdict(doc))
    ]
    assert not bad, bad


@pytest.mark.parametrize(
    ("spec", "ok"),
    [
        ({"ttlSecondsAfterFinished": 3600}, True),
        ({}, False),
        ({"ttlSecondsAfterFinished": 0}, False),
        ({"ttlSecondsAfterFinished": MAX_TTL_SECONDS + 1}, False),
    ],
)
def test_the_rule_permits_and_refuses(spec: dict, ok: bool) -> None:
    doc = {
        "kind": "CronJob",
        "metadata": {"name": "x"},
        "spec": {"jobTemplate": {"spec": spec}},
    }
    assert (ttl_verdict(doc) is None) is ok
