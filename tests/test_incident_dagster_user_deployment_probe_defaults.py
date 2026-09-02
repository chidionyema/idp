"""idp incident 2026-09-02: the estate-scheduler pod could never read Ready.

Two classes of mistake, one file. First: helm never merges list entries. The
user-deployments entry set a bare `readinessProbe: enabled: true`, which
replaced the chart's whole probe block, so the timings fell to the Kubernetes
API defaults -- a 1-second timeout. Second: an exec probe that spawns the
`dagster` CLI costs a full Python boot per probe; measured in-pod on the 250m
CPU limit its HEALTHY path takes 5 seconds wall -- equal to its own timeout --
so an exec probe on a CPU-limited pod can only flap, and the liveness variant
kills healthy pods. This test refuses both: timings explicit and humane, and
the handler is the kubelet-native gRPC probe (a millisecond RPC from the
node), never a spawned process. A probe rendered without any handler is
refused by the API server (incident 2026-09-01).
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
                f"{dep['name']} {kind} leans on the 1s Kubernetes default timeout"
            )
            assert probe.get("initialDelaySeconds", 0) >= 30, (
                f"{dep['name']} {kind} probes before Python can possibly have booted"
            )


def test_the_probe_spawns_no_process():
    for dep in deployments():
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind)
            if not probe:
                continue
            assert "exec" not in probe, (
                f"{dep['name']} {kind} spawns a process per probe; measured "
                "2026-09-02: the CLI's healthy path takes 5s wall at the 250m "
                "CPU limit, equal to its own timeout, so it can only flap"
            )
            assert "grpc" in probe, (
                f"{dep['name']} {kind} names no handler; a probe rendered "
                "without one is refused by the API server (incident 2026-09-01)"
            )


def test_the_probe_knocks_on_the_code_server_port():
    for dep in deployments():
        port = dep.get("port", 3030)
        for kind in ("readinessProbe", "livenessProbe"):
            probe = dep.get(kind) or {}
            grpc_port = probe.get("grpc", {}).get("port")
            if grpc_port is not None:
                assert str(grpc_port) == str(port), (
                    f"{dep['name']} {kind} knocks on {grpc_port} but the code "
                    f"server listens on {port}"
                )
