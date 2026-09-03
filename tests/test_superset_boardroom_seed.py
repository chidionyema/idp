"""The boardroom seed job stays one-shot, bounded and read-safe (decision 0018).

The seed renders the Superset import bundle at run time and loads it with the
tool's own importer. These rows pin the shape that keeps it safe: it rides the
batch bucket instead of standing capacity (crew#584), reads secrets from mounts
only, pins its drivers, and can be re-run without doubling anything (fixed
uuids overwrite in place).
"""

import re
from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parents[1] / (
    "platform/observability/superset-boardroom-seed.yaml"
)
KUSTOMIZATION = Path(__file__).resolve().parents[1] / (
    "platform/observability/kustomization.yaml"
)
SUPERSET_VALUES = Path(__file__).resolve().parents[1] / (
    "platform/observability/superset.yaml"
)


def _job():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    jobs = [d for d in docs if d.get("kind") == "Job"]
    assert len(jobs) == 1, "exactly one Job in the seed manifest"
    return jobs[0]


def _script():
    job = _job()
    container = job["spec"]["template"]["spec"]["containers"][0]
    return "\n".join(container.get("args", []))


def test_seed_is_wired_into_the_kustomization():
    doc = yaml.safe_load(KUSTOMIZATION.read_text())
    assert "superset-boardroom-seed.yaml" in doc["resources"]


def test_seed_rides_the_batch_bucket_not_standing_capacity():
    spec = _job()["spec"]["template"]["spec"]
    assert spec["priorityClassName"] == "platform-batch"
    cpu = spec["containers"][0]["resources"]["requests"]["cpu"]
    assert cpu.endswith("m") and int(cpu[:-1]) <= 225, (
        "the batch bucket is bounded by the balloon's 225m per pod"
    )


def test_seed_can_be_changed_in_place():
    annotations = _job()["metadata"].get("annotations", {})
    assert annotations.get("kustomize.toolkit.fluxcd.io/force") == "Enabled", (
        "Jobs are immutable; Flux recreates the seed only with the force annotation"
    )


def test_seed_is_bounded_and_self_deleting():
    spec = _job()["spec"]
    assert spec["backoffLimit"] <= 1
    assert spec["activeDeadlineSeconds"] <= 900
    assert spec["ttlSecondsAfterFinished"] >= 86400


def test_seed_image_names_its_registry_in_full():
    image = _job()["spec"]["template"]["spec"]["containers"][0]["image"]
    registry = image.split("/")[0]
    assert "." in registry, "image must name its registry host in full"
    assert ":" in image.rsplit("/", 1)[-1], "image tag must be pinned"


def test_seed_reads_secrets_from_mounts_never_env():
    container = _job()["spec"]["template"]["spec"]["containers"][0]
    for env in container.get("env", []):
        assert "value" not in env or "PASSWORD" not in env["name"].upper()
    mounts = {m["mountPath"] for m in container["volumeMounts"]}
    assert "/secrets/clickhouse" in mounts
    assert "/run/secrets/superset" in mounts


def test_seed_script_is_strict_pinned_and_write_free_on_the_source():
    script = _script()
    assert "set -euo pipefail" in script
    assert "psycopg2-binary==" in script and "clickhouse-connect==" in script, (
        "both drivers pinned"
    )
    assert "ImportDashboardsCommand" in script, (
        "Superset 6.1 has no import-assets command; the seed calls the importer class"
    )
    assert "import-assets" not in script
    assert '"type": "Dashboard"' in script, (
        "the importer class validates the bundle's metadata type as Dashboard"
    )
    assert '"type": "assets"' not in script
    upper = script.upper()
    for verb in ("DROP TABLE", "DELETE FROM", "TRUNCATE", "ALTER TABLE"):
        assert verb not in upper, "the seed never writes to the trace store"


def test_seed_queries_the_clickhouse_trace_store_not_postgres():
    script = _script()
    assert "signoz-clickhouse.observability" in script
    assert "clickhousedb+connect://" in script
    assert "FROM observations" in script and "FROM traces" in script


def test_seed_is_idempotent_via_fixed_uuids_and_proves_the_result():
    script = _script()
    assert script.count("5f2e77a0-91c4-4d0e-8e30-2b6c5d9e") >= 10, (
        "every seeded object carries a fixed uuid so a re-run overwrites in place"
    )
    assert "BOARDROOM-SEEDED" in script, "the job prints a read-back receipt"


def test_web_pods_get_the_clickhouse_driver_too():
    docs = [d for d in yaml.safe_load_all(SUPERSET_VALUES.read_text()) if d]
    release = next(
        d
        for d in docs
        if d.get("kind") == "HelmRelease" and d["metadata"]["name"] == "superset"
    )
    script = release["spec"]["values"]["bootstrapScript"]
    pinned = dict(re.findall(r"(\S+)==(\S+)", script))
    assert "clickhouse-connect" in pinned, (
        "bootstrapScript must pin the driver the seeded connection needs"
    )
