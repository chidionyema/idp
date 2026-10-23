"""The shadow stands in for a private image it cannot pull, so platform/llm converges.

Incident: ghcr.io/chidionyema/zeroedge is private and the shadow holds no registry credential,
so llm/zeroedge sat in ErrImagePull on every run (base and head) and platform/llm never
converged. The stand-in answers the Deployment's own /health probe; the tag is the one Flux
image-automation sets in the kustomization, not the one in the Deployment.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_tag_is_the_one_flux_sets_not_the_deployments():
    shadow = load_shadow()
    kust = (REPO / "platform/llm/kustomization.yaml").read_text()
    import re

    tag = re.search(r"name: ghcr.io/chidionyema/zeroedge\s*\n\s*newTag: (\S+)", kust)
    assert tag
    assert shadow.private_image_refs(["platform/llm"]) == {
        f"ghcr.io/chidionyema/zeroedge:{tag.group(1)}"
    }


def test_a_path_without_a_private_image_lays_nothing():
    assert load_shadow().private_image_refs(["platform/priority-classes"]) == set()


def test_the_stand_in_answers_the_probe_the_deployment_declares():
    shadow = load_shadow()
    port, health = shadow.PRIVATE_STAND_INS["ghcr.io/chidionyema/zeroedge"]
    dep = (REPO / "platform/llm/zeroedge.yaml").read_text()
    assert f"containerPort: {port}" in dep
    assert f"path: {health}" in dep
    df = shadow.STAND_IN_DOCKERFILE.format(port=port, health=health, dir="")
    assert "USER 10001" in df and str(port) in df


def test_a_run_lays_the_stand_in_before_any_path_is_applied():
    src = (REPO / "bin" / "idp-shadow").read_text()
    assert src.index("stand_in_private_images(paths)") < src.index(
        "flux_kustomization(name, path, substitute=True)"
    )


def test_the_creds_row_is_applied_only_after_the_floor_has_converged():
    """The ExternalSecret needs the ESO CRD established; applied beside the floor rows it raced
    them and flux-system/github-app never appeared (runs 39908064993, 39920521952)."""
    src = (REPO / "bin" / "idp-shadow").read_text()
    body = src[src.index("def flux_floor") :]
    body = body[: body.index("\ndef ", 10)]
    assert body.index("wait_ks(name, deadline)") < body.index(
        "flux_kustomization(CREDS_ROW_NAME"
    )
