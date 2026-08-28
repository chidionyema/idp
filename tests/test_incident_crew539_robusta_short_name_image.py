"""Incident 2026-08-28 (crew#539, oke-check run 33162263652 `bin/idp-oke-rebuild --break-glass`):
robusta-forwarder and robusta-runner stuck `ImageInspectError` / `Init:ImageInspectError` for
hours; the pod event was `InspectFailed: short name mode is enforcing, but image name
robustadev/kubewatch:v2.16.1 returns ambiguous list` (robusta-runner:0.48.0 the same). The chart's
templates render `{{ .Values.image.registry }}/{{ .Values.kubewatch|runner.imageName }}`, and the
chart's default `image.registry: robustadev` has no registry host — an unqualified short name the
node's container runtime (short-name mode enforcing, more than one unqualified-search registry
configured) refuses to resolve. HelmRelease/robusta/robusta then failed early on the stalled
Deployments and Flux could never bring it up. Rule: the robusta release pins a fully-qualified
`image.registry`, the same shape every other image reference in this estate carries."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _robusta_values():
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/robusta/robusta.yaml").read_text()) if d]
    hr = next(d for d in docs if d["kind"] == "HelmRelease")
    return hr["spec"]["values"]


def test_image_registry_is_fully_qualified_not_a_short_name() -> None:
    v = _robusta_values()
    assert "image" in v, "no image.registry override: the chart's short unqualified default (robustadev) ships"
    registry = v["image"]["registry"]
    assert "/" in registry, f"image.registry {registry!r} has no host — this is the short name the runtime refused"
    assert registry.split("/")[0].count(".") >= 1 or registry.split("/")[0] == "localhost", (
        f"image.registry {registry!r} does not start with a registry host"
    )


def test_registry_override_is_not_the_bare_chart_default() -> None:
    v = _robusta_values()
    assert v["image"]["registry"] != "robustadev", "still the chart default: robustadev/<image> is an unqualified short name"
