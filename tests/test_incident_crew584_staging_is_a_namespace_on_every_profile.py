"""crew#584 CP-H (founder 2026-08-29 01:55Z): the staging area is a namespace on the one cluster,
on every profile including lean. It stood `planned` in the register with no manifest behind it.
Now platform/staging/ exists, is a Flux row, admits the dev loop (mirrord) and nothing else can
crowd production from it: a quota ceiling and no public LoadBalancer."""

import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(p):
    return [d for d in yaml.safe_load_all(p.read_text()) if d]


def test_staging_is_a_flux_row_with_no_dependencies():
    rows = {
        d["metadata"]["name"]: d
        for d in _docs(ROOT / "clusters/oke/platform.yaml")
        if d.get("kind") == "Kustomization"
    }
    st = rows["staging"]
    assert st["spec"]["path"] == "./platform/staging"
    assert st["spec"]["prune"] is True and st["spec"]["wait"] is True
    assert not st["spec"].get("dependsOn"), (
        "a namespace waits on nothing; the lean profile has no other rows to wait for"
    )
    kust = yaml.safe_load((ROOT / "platform/staging/kustomization.yaml").read_text())
    assert set(kust["resources"]) == {"namespace.yaml", "quota.yaml"}


def test_the_namespace_admits_the_dev_loop_and_survives_a_row_move():
    ns = next(
        d
        for d in _docs(ROOT / "platform/staging/namespace.yaml")
        if d["kind"] == "Namespace"
    )
    assert ns["metadata"]["name"] == "staging"
    assert ns["metadata"]["labels"]["idp.platform/dev-loop"] == "allowed", (
        "mirrord fence (dev-loop-policy.yaml) keys on this label"
    )
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )
    # and production namespaces do not carry the label: the fence is only worth something if staging is the one door
    others = [
        p for p in ROOT.glob("platform/**/namespace*.yaml") if "staging" not in p.parts
    ]
    for p in others:
        for d in _docs(p):
            if d.get("kind") == "Namespace":
                assert (
                    d["metadata"].get("labels", {}).get("idp.platform/dev-loop")
                    != "allowed"
                ), p


def test_the_ceiling_bounds_the_sum_and_opens_no_public_door():
    q = next(
        d
        for d in _docs(ROOT / "platform/staging/quota.yaml")
        if d["kind"] == "ResourceQuota"
    )
    assert q["metadata"]["namespace"] == "staging"
    hard = q["spec"]["hard"]
    assert hard["services.loadbalancers"] == "0"
    assert (
        hard["requests.cpu"] == "1"
        and hard["requests.memory"] == "2Gi"
        and hard["requests.storage"] == "2Gi"
    )


def test_the_register_can_select_staging_now_and_every_profile_has_it():
    reg = yaml.safe_load((ROOT / "platform/features/features.yaml").read_text())
    feat = next(f for f in reg["features"] if f["name"] == "staging")
    tier = next(t for t in feat["tiers"] if t["name"] == "namespace")
    assert tier.get("status") in (None, "on", "trial"), tier
    assert "floor" not in tier, (
        "a tier with a real switch is summed from git, not from a typed floor"
    )
    assert tier["switches"] == ["staging"] and feat["default"] == "namespace"
