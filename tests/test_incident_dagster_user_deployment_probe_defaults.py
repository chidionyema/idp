"""idp incident 2026-09-02: the estate-scheduler pod could never read Ready.

The class of mistake: helm never merges list entries. The user-deployments
entry set a bare `readinessProbe: enabled: true`, which replaced the chart's
whole probe block, so the timings fell to the Kubernetes API defaults -- a
1-second timeout that the CPU-limited `dagster api grpc-health-check` CLI can
never meet. The pod stayed unready forever and every helm upgrade stalled on
it. This test refuses a user-deployment probe that leans on those silent
defaults: timings explicit and humane, and a handler spelled out (a probe
rendered without one is refused by the API server, incident 2026-09-01).
"""

from pathlib import Path

import yaml

DAGSTER = Path(__file__).resolve().parents[1] / "platform" / "dagster" / "dagster.yaml"


def deployments():
    docs = list(yaml.safe_load_all(DAGSTER.read_text()))
    rel = next(d for d in docs if d and d.get("kind") == "HelmRelease")
    return rel["spec"]["values"]["dagster-user-deployments"]["deployments"]


def test_every_user_deployment_probe_has_explicit_humane_timings():
    for dep in deployments():
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind)
            if not probe:
                continue
            assert probe.get("timeoutSeconds", 1) >= 5, (
                f"{dep['name']} {kind} leans on the 1s Kubernetes default timeout; "
                "the grpc-health-check CLI cannot boot in 1s on a CPU-limited pod"
            )
            assert "exec" in probe, (
                f"{dep['name']} {kind} names no handler; a probe rendered without "
                "one is refused by the API server (incident 2026-09-01)"
            )


def test_the_probe_knocks_on_the_code_server_port():
    for dep in deployments():
        port = dep.get("port", 3030)
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind) or {}
            cmd = probe.get("exec", {}).get("command", [])
            if cmd:
                assert str(port) in [str(c) for c in cmd], (
                    f"{dep['name']} {kind} checks port {cmd} but the code server "
                    f"listens on {port}"
                )
