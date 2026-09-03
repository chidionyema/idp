"""Incident guard, 2026-09-02.

The Dagster chart's default web-page/daemon image (docker.io/dagster/dagster-celery-k8s)
publishes no arm64 build, and every node on the cluster is arm64: the kubelet refused the
pull ('no image found in image index for architecture "arm64"') and the pods never booted.
Separately, a patch forced the scheduler to require secret "dagster-celery-config-secret",
which the chart only generates under CeleryK8sRunLauncher (the estate runs K8sRunLauncher),
so the pod sat in CreateContainerConfigError forever.

Record: docs/reference/policy/dagster-arm64-images.md
"""

from pathlib import Path

import yaml

VALUES_FILE = (
    Path(__file__).resolve().parents[1] / "platform" / "dagster" / "dagster.yaml"
)
ESTATE_IMAGE = "ghcr.io/chidionyema/estate-scheduler"


def _helm_release() -> dict:
    for doc in yaml.safe_load_all(VALUES_FILE.read_text()):
        if (
            doc
            and doc.get("kind") == "HelmRelease"
            and doc["metadata"]["name"] == "dagster"
        ):
            return doc
    raise AssertionError(f"no dagster HelmRelease in {VALUES_FILE}")


def test_no_vendor_dagster_image_anywhere_in_the_release() -> None:
    dumped = yaml.safe_dump(_helm_release())
    assert "docker.io/dagster" not in dumped


def test_the_impossible_celery_secret_is_never_referenced() -> None:
    release = _helm_release()
    assert release["spec"]["values"]["global"]["celeryConfigSecretName"] == ""
    assert (
        release["spec"]["values"]["dagster-user-deployments"]["celeryConfigSecretName"]
        == ""
    )
    assert "dagster-celery-config-secret" not in yaml.safe_dump(release)
