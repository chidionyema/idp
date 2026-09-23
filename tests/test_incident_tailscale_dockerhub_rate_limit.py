"""Incident guard, 2026-09-02.

The moment pod security allowed the Mac proxy pods to be created, both sat unable to pull
docker.io/tailscale/tailscale:v1.102.3: "toomanyrequests: You have reached your
unauthenticated pull rate limit". The cluster shares one outbound address, so Docker Hub's
anonymous quota is a shared resource any workload can exhaust for all the others. The
vendor publishes the same images on GitHub's registry, which sets no anonymous quota on
public images (both tags measured answering 200 on 2026-09-02, the proxy image with an
arm64 build).

Record: docs/reference/policy/tailscale-ghcr-images.md
"""

from pathlib import Path

import yaml

VALUES_FILE = (
    Path(__file__).resolve().parents[1] / "platform" / "tailscale" / "operator.yaml"
)


def _values() -> dict:
    for doc in yaml.safe_load_all(VALUES_FILE.read_text()):
        if doc and doc.get("kind") == "HelmRelease":
            return doc["spec"]["values"]
    raise AssertionError(f"no HelmRelease in {VALUES_FILE}")


def test_both_tailscale_images_come_from_github_registry() -> None:
    values = _values()
    assert values["proxyConfig"]["image"]["repository"] == "ghcr.io/tailscale/tailscale"
    assert (
        values["operatorConfig"]["image"]["repository"]
        == "ghcr.io/tailscale/k8s-operator"
    )


def test_no_tailscale_image_points_at_docker_hub() -> None:
    assert "docker.io/tailscale" not in yaml.safe_dump(_values()), (
        "a Tailscale image points back at Docker Hub; its anonymous pull quota is shared "
        "across the cluster's one outbound address and took both proxy pods down"
    )
