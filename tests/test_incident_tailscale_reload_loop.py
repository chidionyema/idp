"""Incident 2026-09-02: the tailscale proxy StatefulSets rolled forever.

The require-auto-reload policy annotates every workload at admission, Reloader
then restarts a workload when a Secret it references changes -- and the
tailscale proxy writes its own state Secret on every boot. Reload on a
self-written Secret is a loop: 689 StatefulSet generations were measured, pods
killed one to two seconds after starting, while the tailscale operator fought
the injected env in a second loop.

The guard: the auto-reload mutation excludes the tailscale namespace, where the
operator owns config rollout and the workload writes its own config.
"""

from pathlib import Path

import yaml

POLICY = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "edge"
    / "require-auto-reload.yaml"
)


def test_auto_reload_mutation_excludes_tailscale():
    docs = [d for d in yaml.safe_load_all(POLICY.read_text()) if d]
    policies = [d for d in docs if d.get("kind") == "ClusterPolicy"]
    assert policies, "require-auto-reload.yaml holds no ClusterPolicy"
    rules = [r for d in policies for r in d["spec"]["rules"] if r.get("mutate")]
    assert rules, "no mutate rule found; the incident guard grades the mutation"
    for rule in rules:
        excluded = [
            ns
            for clause in rule.get("exclude", {}).get("any", [])
            for ns in clause.get("resources", {}).get("namespaces", [])
        ]
        assert "tailscale" in excluded, (
            f"rule {rule['name']} would annotate the tailscale proxies again; "
            "they write their own state Secret, so auto-reload there is a "
            "restart loop"
        )
