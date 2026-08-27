"""crew#483 (2026-08-27): the healthchecks pod crash-looped 9 times. The kubelet's probe carries
the pod IP as Host, Django's ALLOWED_HOSTS in env.yaml allows one hostname, and every probe
got 400. Rule: when a workload restricts Host, each HTTP probe presents a host that
restriction allows."""

from pathlib import Path

import yaml

HC = Path(__file__).resolve().parents[1] / "platform" / "healthchecks"


def _probes() -> list[dict]:
    docs = [d for d in yaml.safe_load_all((HC / "healthchecks.yaml").read_text()) if d]
    dep = next(d for d in docs if d["kind"] == "Deployment")
    return [c[k] for c in dep["spec"]["template"]["spec"]["containers"] for k in ("readinessProbe", "livenessProbe") if k in c]


def _allowed_hosts() -> set[str]:
    docs = [d for d in yaml.safe_load_all((HC / "env.yaml").read_text()) if d]
    cm = next(d for d in docs if d["kind"] == "ConfigMap")
    return set(cm["data"]["ALLOWED_HOSTS"].split(","))


def test_every_http_probe_presents_an_allowed_host() -> None:
    probes = _probes()
    assert len(probes) == 2
    for probe in probes:
        hosts = {h["value"] for h in probe["httpGet"].get("httpHeaders", []) if h["name"] == "Host"}
        assert hosts and hosts <= _allowed_hosts(), probe
