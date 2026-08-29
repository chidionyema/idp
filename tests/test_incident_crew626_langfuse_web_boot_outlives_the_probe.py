"""crew#626 CP16 (diagnose run 33265823704): langfuse-web at one full core still died to the chart's
50 s liveness window (exit 143, 35 kills in 109 min) before it ever served, so the SSO fix never met a
request. The liveness budget must outlive a ClickHouse-bound boot, and readiness must be the gentler of the two."""

from pathlib import Path

import yaml

VALUES = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "observability"
    / "langfuse-values.yaml"
)


def _web() -> dict:
    return yaml.safe_load(VALUES.read_text(encoding="utf-8"))["langfuse"]["web"]


def test_liveness_budget_is_at_least_four_minutes() -> None:
    p = _web()["livenessProbe"]
    assert p["initialDelaySeconds"] + p["periodSeconds"] * p["failureThreshold"] >= 240
    assert p["path"] == "/api/public/health"


def test_readiness_starts_earlier_and_lasts_longer_than_liveness() -> None:
    live, ready = _web()["livenessProbe"], _web()["readinessProbe"]
    assert ready["initialDelaySeconds"] <= live["initialDelaySeconds"]
    assert ready["initialDelaySeconds"] + ready["periodSeconds"] * ready[
        "failureThreshold"
    ] >= (
        live["initialDelaySeconds"] + live["periodSeconds"] * live["failureThreshold"]
    )
    assert ready["path"] == "/api/public/ready"
