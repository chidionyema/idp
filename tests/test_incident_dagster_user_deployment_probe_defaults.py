"""idp incident 2026-09-02: the estate-scheduler pod could never read Ready.

Two classes of mistake, one file. First: helm never merges list entries. The
user-deployments entry set a bare `readinessProbe: enabled: true`, which
replaced the chart's whole probe block, so the timings fell to the Kubernetes
API defaults -- a 1-second timeout the CPU-limited health-check CLI can never
meet (measured in-pod: its HEALTHY path takes 5 seconds wall at the 250m CPU
limit, so a 5s timeout also flaps and its liveness variant kills healthy
pods; the founder set 30). Second: the chart copies only the known timing
fields from the values probe block and silently drops any other handler key
-- a kubelet-native `grpc:` probe written here never reached the cluster
(measured on the rendered Deployment 2026-09-02) -- so the values must spell
out the exec handler the chart actually renders, on the port the code server
listens on.
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
            assert probe.get("timeoutSeconds", 1) >= 30, (
                f"{dep['name']} {kind} timeout is under the founder-set 30s; "
                "the health-check CLI's healthy path alone takes 5s wall at "
                "the 250m CPU limit"
            )
            assert probe.get("initialDelaySeconds", 0) >= 30, (
                f"{dep['name']} {kind} probes before Python can possibly have booted"
            )


def test_the_probe_handler_is_one_the_chart_renders():
    for dep in deployments():
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind)
            if not probe:
                continue
            assert "grpc" not in probe and "httpGet" not in probe, (
                f"{dep['name']} {kind} carries a handler the chart silently "
                "drops (only known timing fields and exec survive rendering, "
                "measured on the Deployment 2026-09-02); the values would lie"
            )
            assert "exec" in probe, (
                f"{dep['name']} {kind} spells out no exec handler; the values "
                "must say exactly what the chart renders"
            )


def test_the_probe_knocks_on_the_code_server_port():
    for dep in deployments():
        port = dep.get("port", 3030)
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind) or {}
            cmd = probe.get("exec", {}).get("command", [])
            if cmd:
                assert str(port) in [str(c) for c in cmd], (
                    f"{dep['name']} {kind} checks {cmd} but the code server "
                    f"listens on {port}"
                )
