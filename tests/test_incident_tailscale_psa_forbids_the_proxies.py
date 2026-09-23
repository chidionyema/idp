"""Incident (2026-09-02 15:25Z, idp#1152): the scoped Kyverno exception (idp#1147) admitted both
Tailscale Mac proxy StatefulSets, but the API server then refused their pods:
  Create Pod ts-sunshine-mac-ql4xm-0 ... violates PodSecurity "baseline:latest": privileged
  (containers "sysctler", "tailscale" must not set securityContext.privileged=true)
Pod Security Admission is enforced by the API server per namespace; no Kyverno PolicyException can
waive it. Five review rounds saw the Kyverno layer and nobody saw the PSA layer under it.

Rule: the tailscale namespace manifest carries enforce=privileged (the vendor's proxies require
privileged containers), and warn+audit stay restricted so anything else landing there is reported.
Same shape as platform/edge/k8s-infra-namespace.yaml (the node log agent).
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_tailscale_namespace_pod_security_admits_the_proxies_and_reports_everything_else():
    docs = list(
        yaml.safe_load_all(
            (ROOT / "platform" / "tailscale" / "namespace.yaml").read_text()
        )
    )
    ns = next(d for d in docs if d and d.get("kind") == "Namespace")
    labels = ns["metadata"]["labels"]
    assert labels.get("pod-security.kubernetes.io/enforce") == "privileged", (
        "the vendor's sysctler/tailscale containers are privileged; baseline refuses their pods"
    )
    assert labels.get("pod-security.kubernetes.io/warn") == "restricted"
    assert labels.get("pod-security.kubernetes.io/audit") == "restricted", (
        "warn and audit stay restricted so any non-proxy workload landing here is reported"
    )
