"""Incident 2026-09-02: twice, a merge into flux/image-updates that meant to keep only the
controller's newTag stamps instead replaced platform/dagster/dagster.yaml with an old copy,
silently reverting values main had gained (the telemetry-off block once, the crew#555
availability block the second time). This test pins the values that were lost so the
class cannot recur on any branch."""

from pathlib import Path

DAGSTER = Path(__file__).resolve().parents[1] / "platform" / "dagster" / "dagster.yaml"


def test_telemetry_off_block_survives_merges():
    text = DAGSTER.read_text()
    assert (
        "telemetry:" in text and "enabled: false" in text.split("telemetry:", 1)[1][:40]
    )


def test_user_deployment_availability_block_survives_merges():
    text = DAGSTER.read_text()
    for needle in ("replicaCount: 2", "maxSurge: 0", "podAntiAffinity"):
        assert needle in text, f"crew#555 availability value missing: {needle}"
