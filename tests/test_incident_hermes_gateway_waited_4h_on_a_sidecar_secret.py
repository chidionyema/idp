"""Incident test, 2026-08-29: hermes-agent-gateway sat at ContainerCreating 0/2 for 4h16m because
the Tailscale sidecar's secret (hermes-agent-tailscale, vault key tailscale-operator) did not exist
and the volume was required. Otto was silent. Rule: a sidecar's secret volume is optional; only the
gateway's own env secrets may hold the pod. Both ways: the manifest as committed passes; the same
volume without `optional: true` is named.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/hermes-agent/gateway.yaml"
GATEWAY_OWN = {"env", "data", "tmp", "estate", "mac-run"}


def _deployment() -> dict:
    for doc in yaml.safe_load_all(MANIFEST.read_text()):
        if doc and doc.get("kind") == "Deployment":
            return doc
    raise AssertionError("no Deployment in gateway.yaml")


def _required_sidecar_secret_volumes(volumes: list[dict]) -> list[str]:
    return [v["name"] for v in volumes
            if v["name"] not in GATEWAY_OWN and "secret" in v and not v["secret"].get("optional", False)]


def test_no_sidecar_secret_volume_can_hold_the_gateway():
    volumes = _deployment()["spec"]["template"]["spec"]["volumes"]
    assert _required_sidecar_secret_volumes(volumes) == []


def test_the_tailscale_volume_is_still_mounted_and_optional():
    volumes = {v["name"]: v for v in _deployment()["spec"]["template"]["spec"]["volumes"]}
    assert volumes["tailscale-authkey"]["secret"] == {"secretName": "hermes-agent-tailscale", "optional": True}


def test_the_rule_names_a_required_sidecar_secret():
    bad = [{"name": "tailscale-authkey", "secret": {"secretName": "hermes-agent-tailscale"}}]
    assert _required_sidecar_secret_volumes(bad) == ["tailscale-authkey"]
