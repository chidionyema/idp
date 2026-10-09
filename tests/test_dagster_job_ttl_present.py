"""A failed Dagster copy-job wedged the `dagster` namespace until a hand delete.

On 2026-10-02 `estate-db-copy-dagster-r3`, launched by the EstateDB K8sRunLauncher as
a one-shot Job, failed and stayed. A Job's spec is immutable after creation, so the
only remedy anyone had was `kubectl delete` by hand -- and until someone noticed, the
Failed Job sat in the namespace. A Failed Job blocks Flux, and blocks the next run.

The chart template leaves `ttlSecondsAfterFinished` unset, so nothing ever collects a
finished Job except the cluster's bulk sweeper; the comment that claimed 3600 would
have been a lie twice over, since the field was not set at all.

The fix is `runK8sConfig.jobSpecConfig.ttlSecondsAfterFinished: 60` under
`runLauncher.config.k8sRunLauncher` -- the one place the chart renders into the launcher's
`job_spec_config`. The first version of this fix (2026-10-04) put it at
`k8sRunLauncher.jobSpec`, a key the chart does not have: its values schema sets
`additionalProperties: false` there, so Helm would have refused the upgrade, and the YAML
test passed anyway. Every Job the launcher spawns inherits the template, so a Failed or Complete Job is removed by Kubernetes itself a minute after
it lands. 60 is deliberately below the runCoordinator's `queuedRunCooldownSeconds`
(chart default 120) so a back-to-back retry does not race the collector.

This test grades the rendered value, not the presence of a comment. A comment saying
the knob is turned is exactly what was there before and was wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "platform/dagster/dagster.yaml"

# Chart default for the QueuedRunCoordinator's queuedRunCooldownSeconds. The TTL must
# stay below it, or a retry can race the collector; see the docstring.
QUEUED_RUN_COOLDOWN_SECONDS = 120
TTL_SECONDS = 60
TTL_PATH = (
    "spec",
    "values",
    "runLauncher",
    "config",
    "k8sRunLauncher",
    "runK8sConfig",
    "jobSpecConfig",
    "ttlSecondsAfterFinished",
)

# The keys chart 1.13.19's values.schema.json allows ($defs K8sRunLauncherConfig and
# RunK8sConfig, both additionalProperties: false). A key outside them fails the Helm upgrade.
CHART_VERSION = "1.13.19"
K8S_RUN_LAUNCHER_KEYS = {
    "envConfigMaps",
    "envSecrets",
    "envVars",
    "failPodOnRunFailure",
    "image",
    "imagePullPolicy",
    "jobNamespace",
    "kubeconfigFile",
    "labels",
    "loadInclusterConfig",
    "resources",
    "runK8sConfig",
    "schedulerName",
    "securityContext",
    "volumeMounts",
    "volumes",
}
RUN_K8S_CONFIG_KEYS = {
    "containerConfig",
    "jobMetadata",
    "jobSpecConfig",
    "podSpecConfig",
    "podTemplateSpecMetadata",
}


def _dagster_helmrelease() -> dict:
    """The HelmRelease in platform/dagster/dagster.yaml, parsed from the real file."""
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    releases = [d for d in docs if d.get("kind") == "HelmRelease"]
    assert len(releases) == 1, (
        f"expected exactly one HelmRelease in {MANIFEST.name}, found {len(releases)}"
    )
    return releases[0]


def _dig(obj, *keys):
    """Walk keys, asserting each hop exists -- a missing hop is the defect."""
    cur = obj
    walked = []
    for key in keys:
        walked.append(key)
        assert isinstance(cur, dict), (
            f"{'.'.join(walked[:-1])} is not a mapping (got {type(cur).__name__})"
        )
        assert key in cur, f"missing {'.'.join(walked)}"
        cur = cur[key]
    return cur


def test_k8s_run_launcher_declares_a_job_ttl() -> None:
    """The field is set, and set to 60 -- not absent, not a placeholder."""
    release = _dagster_helmrelease()
    ttl = _dig(release, *TTL_PATH)
    assert ttl == TTL_SECONDS, (
        f"expected ttlSecondsAfterFinished {TTL_SECONDS}, got {ttl!r}"
    )


def test_the_launcher_is_still_the_k8s_launcher() -> None:
    """A TTL under some other launcher collects nothing: the Jobs are K8s Jobs.

    Guards the assumption the fix rests on. If runLauncher.type stops being
    K8sRunLauncher, jobSpecConfig no longer describes the spawned Jobs and this test fails
    rather than passing on a stale key.
    """
    release = _dagster_helmrelease()
    launcher_type = _dig(release, "spec", "values", "runLauncher", "type")
    assert launcher_type == "K8sRunLauncher", (
        f"jobSpecConfig governs K8s Jobs only; runLauncher.type is {launcher_type!r}"
    )


def test_the_job_ttl_does_not_race_the_run_coordinator() -> None:
    """TTL stays below queuedRunCooldownSeconds, or a retry collides with the GC."""
    release = _dagster_helmrelease()
    ttl = _dig(release, *TTL_PATH)
    assert ttl < QUEUED_RUN_COOLDOWN_SECONDS, (
        f"ttlSecondsAfterFinished {ttl} is not below the coordinator cooldown "
        f"{QUEUED_RUN_COOLDOWN_SECONDS}; a retry can race the collector"
    )


def test_the_ttl_is_positive() -> None:
    """Zero means immediate collection, which can delete a Job mid-read."""
    release = _dagster_helmrelease()
    ttl = _dig(release, *TTL_PATH)
    assert isinstance(ttl, int) and ttl > 0, (
        f"ttlSecondsAfterFinished must be a positive integer, got {ttl!r}"
    )


@pytest.mark.parametrize("path_head", ["spec.values.runLauncher.config.k8sRunLauncher"])
def test_guard_actually_notices_a_missing_ttl(path_head: str) -> None:
    """The gate can fail: remove the TTL from a copy and prove _dig refuses it.

    A test that cannot fail is not a test. This mutates a deep copy in memory only --
    the file on disk is never touched.
    """
    release = _dagster_helmrelease()
    mutated = yaml.safe_load(yaml.safe_dump(release))
    del mutated["spec"]["values"]["runLauncher"]["config"]["k8sRunLauncher"][
        "runK8sConfig"
    ]["jobSpecConfig"]["ttlSecondsAfterFinished"]
    with pytest.raises(AssertionError, match="ttlSecondsAfterFinished"):
        _dig(mutated, *TTL_PATH)


def test_the_chart_accepts_every_launcher_key() -> None:
    """A key the chart's schema does not allow fails the upgrade -- the 2026-10-04 `jobSpec`."""
    release = _dagster_helmrelease()
    assert _dig(release, "spec", "chart", "spec", "version") == CHART_VERSION, (
        "the chart moved: re-read K8sRunLauncherConfig and RunK8sConfig from its "
        "values.schema.json and update the key sets here"
    )
    launcher = _dig(
        release, "spec", "values", "runLauncher", "config", "k8sRunLauncher"
    )
    assert set(launcher) <= K8S_RUN_LAUNCHER_KEYS, (
        f"k8sRunLauncher keys the chart rejects: {sorted(set(launcher) - K8S_RUN_LAUNCHER_KEYS)}"
    )
    run_k8s = _dig(launcher, "runK8sConfig")
    assert set(run_k8s) <= RUN_K8S_CONFIG_KEYS, (
        f"runK8sConfig keys the chart rejects: {sorted(set(run_k8s) - RUN_K8S_CONFIG_KEYS)}"
    )
