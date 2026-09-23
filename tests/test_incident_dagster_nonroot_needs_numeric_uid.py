"""Incident 2026-09-02: dagster pods refused or crashed after the arm64 image landed.

Two measured refusals, one class: runtime security settings that only work when
every piece agrees.

1. The code server and launched-run pods set ``runAsNonRoot: true`` with no
   numeric uid. The image declares its user by name (``scheduler``), and the
   kubelet cannot verify a name is non-root: "container has runAsNonRoot and
   image has non-numeric user (scheduler)" (events 2026-09-02T16:4xZ).
2. The daemon wrote a telemetry id into DAGSTER_HOME at boot; that directory is
   a read-only mount here, so boot died with PermissionError on ``.telemetry``.

The guards: every ``runAsNonRoot`` in the dagster release carries a numeric
``runAsUser`` beside it, telemetry is off, and the image's USER line is numeric
so the kubelet check can never trip again.
"""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DAGSTER = REPO / "platform" / "dagster" / "dagster.yaml"
DOCKERFILE = REPO / "estate-scheduler.Dockerfile"


def _release_values():
    for doc in yaml.safe_load_all(DAGSTER.read_text()):
        if doc and doc.get("kind") == "HelmRelease":
            return doc["spec"]["values"]
    raise AssertionError("no HelmRelease in dagster.yaml")


def _walk(node, path=""):
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def test_every_run_as_non_root_carries_a_numeric_uid():
    values = _release_values()
    offenders = [
        path
        for path, mapping in _walk(values)
        if mapping.get("runAsNonRoot") is True
        and not isinstance(mapping.get("runAsUser"), int)
    ]
    assert offenders == [], (
        "runAsNonRoot without a numeric runAsUser lets the kubelet refuse the "
        f"container when the image names its user: {offenders}"
    )


def test_telemetry_is_off():
    values = _release_values()
    assert values.get("telemetry", {}).get("enabled") is False, (
        "telemetry writes into DAGSTER_HOME at boot; that mount is read-only "
        "here and the daemon crash-looped on it"
    )


def test_image_user_is_numeric():
    user_lines = [
        line.strip()
        for line in DOCKERFILE.read_text().splitlines()
        if line.strip().startswith("USER ")
    ]
    assert user_lines, "estate-scheduler.Dockerfile declares no USER"
    for line in user_lines:
        who = line.split()[1]
        assert who.isdigit(), (
            f"Dockerfile '{line}' names its user; the kubelet cannot verify a "
            "name is non-root under runAsNonRoot"
        )
