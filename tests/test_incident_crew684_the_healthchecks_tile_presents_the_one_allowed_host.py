"""Incident 2026-08-30 06:0xZ, crew#684: the Ops page's Healthchecks tile said "Healthchecks
answered 400" (login drill 33296013135) and the founder read the portal as down. Healthchecks is
Django with ALLOWED_HOSTS set to one hostname (platform/healthchecks/env.yaml; crew#483 was the
same 400 from the kubelet's probe), and the portal's proxy endpoint forwarded the browser's Host.
Guard: the endpoint sends the allowed host, and the pod is given that host from the same zone
value every other manifest uses. Fault class: fix-proved-on-the-wrong-surface (CP5 pinned the key
and the mount, never a successful read).
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _allowed_host() -> str:
    env = yaml.safe_load((ROOT / "platform" / "healthchecks" / "env.yaml").read_text())
    return env["data"]["ALLOWED_HOSTS"]


def test_the_proxy_endpoint_presents_the_host_healthchecks_allows() -> None:
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.container.yaml").read_text())
    ep = cfg["proxy"]["endpoints"]["/healthchecks"]
    assert ep["headers"]["Host"] == "${HEALTHCHECKS_HOST}"
    kz = yaml.safe_load(
        (
            ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml"
        ).read_text()
    )
    envs = [
        op["value"]
        for patch in kz["patches"]
        for op in yaml.safe_load(patch["patch"]) or []
        if isinstance(patch.get("patch"), str)
        and isinstance(op, dict)
        and op.get("path") == "/spec/template/spec/containers/0/env/-"
    ]
    host = next(e["value"] for e in envs if e["name"] == "HEALTHCHECKS_HOST")
    assert host == _allowed_host(), (host, _allowed_host())
