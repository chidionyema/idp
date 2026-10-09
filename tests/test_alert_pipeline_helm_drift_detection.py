"""The alert pipeline's HelmReleases correct a hand scale on their own.

Founder law 2026-09-30: the alert pipeline can never be silent. 2026-09-26 -> 09-30: every
kube-prometheus-stack workload sat at spec.replicas 0 with the release reading Ready, because
helm-controller renders only on a spec change. driftDetection: enabled is what makes Flux
re-apply the chart every interval. This refuses a monitoring HelmRelease without it.
"""

from pathlib import Path

import yaml

MONITORING = Path(__file__).resolve().parents[1] / "platform" / "monitoring"


def _helmreleases():
    for f in sorted(MONITORING.glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if isinstance(d, dict) and d.get("kind") == "HelmRelease":
                yield f.name, d


def test_every_monitoring_helmrelease_has_drift_detection_enabled():
    seen = {}
    for _name, d in _helmreleases():
        seen[d["metadata"]["name"]] = (
            (d.get("spec") or {}).get("driftDetection", {}).get("mode")
        )
    assert seen, (
        "no HelmRelease under platform/monitoring: the pipeline is not declared"
    )
    assert {"kube-prometheus-stack", "blackbox"} <= set(seen), seen
    lacking = sorted(n for n, m in seen.items() if m != "enabled")
    assert not lacking, (
        f"HelmRelease without driftDetection.mode=enabled (a hand scale to 0 would be permanent): {lacking}"
    )
