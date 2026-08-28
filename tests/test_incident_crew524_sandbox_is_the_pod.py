"""crew#524 CP5: the Hermes fork has no Kubernetes Job terminal backend, so the gateway container
is the sandbox and must stay one. Rules: the row's header says why (the attribution is in git, not
a session's memory); the container keeps the admission shape that makes it a sandbox; no Docker
socket is mounted (docker-in-pod would be the stitching the header rejects)."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GW = ROOT / "platform" / "hermes-agent" / "gateway.yaml"


def _deployment():
    return [d for d in yaml.safe_load_all(GW.read_text()) if d and d["kind"] == "Deployment"][0]


def test_the_row_states_why_the_pod_is_the_sandbox():
    head = GW.read_text().split("---")[0]
    assert "no Kubernetes Job backend" in head and "terminal_tool.py" in head and "LAW 43" in head


def test_the_container_keeps_the_sandbox_shape_and_mounts_no_docker_socket():
    spec = _deployment()["spec"]["template"]["spec"]
    # crew#516 CP5 added a `tailscale` sidecar to this pod (platform/hermes-agent/tailscale.yaml);
    # the sandbox container itself is named `gateway`, checked here specifically rather than
    # assumed to be the pod's only container.
    c = next(x for x in spec["containers"] if x["name"] == "gateway")
    sc = c["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True and sc["allowPrivilegeEscalation"] is False
    assert sc["privileged"] is False and sc["capabilities"] == {"drop": ["ALL"]} and sc["runAsNonRoot"] is True
    assert spec["securityContext"]["runAsUser"] == 10001
    for v in spec.get("volumes", []):
        hp = v.get("hostPath", {}).get("path", "")
        assert "docker.sock" not in hp and "containerd" not in hp, v
