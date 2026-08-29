"""crew#584: oke-check 33234280926 (2026-08-29T04:40Z) found observability-agent empty while its
HelmRelease read Ready (UpgradeSucceeded v7 03:46:32Z). helm-controller's uninstall of the pruned
pre-idp#702 object hit the same Helm release name ("release mismatch", 03:47Z) and stripped the
v7 DaemonSet and Deployment. Nothing re-applied them: the release had no drift detection and an
hourly interval. telemetry-coverage read seen=2/97 for an hour and no row named why."""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _hr():
    docs = yaml.safe_load_all((ROOT / "platform/observability-collector/k8s-infra.yaml").read_text())
    return next(d for d in docs if d and d["kind"] == "HelmRelease")


def test_the_agent_release_is_reapplied_when_its_objects_go_missing():
    spec = _hr()["spec"]
    assert spec.get("driftDetection", {}).get("mode") == "enabled", spec.get("driftDetection")


def test_a_blind_agent_is_corrected_within_the_coverage_window():
    interval = _hr()["spec"]["interval"]
    assert interval.endswith("m") and int(interval[:-1]) <= 15, interval
