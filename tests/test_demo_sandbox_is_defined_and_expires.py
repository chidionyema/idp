"""crew#805 tier 3: the buyer sandbox is defined, bounded, and expires by machinery.

The sandbox is a vCluster OSS control plane under platform/sandbox/vcluster, launched by a
person as one imperative Flux Kustomization carrying the label cleanup.kyverno.io/ttl. The
kyverno cleanup controller deletes that row on schedule; Flux prune then sweeps every sandbox
object except the marked namespace (deleting a namespace is refused at admission, so pruning
it would deadlock on a finalizer — the annotation opts it out).

Every assertion here pins a decision an admission policy or an estate test enforces at
runtime, so a future edit that would make the sandbox unlaunchable or immortal is a red CI,
never a live incident during a buyer demo.
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SBX = ROOT / "platform" / "sandbox" / "vcluster"


def _by_kind() -> dict:
    out = {}
    for f in sorted(SBX.glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if isinstance(d, dict) and "kind" in d:
                out[d["kind"]] = d
    return out


def _estate_interval() -> str:
    doc = yaml.safe_load((ROOT / "clusters" / "oke" / "kustomization.yaml").read_text())
    hits = [
        p
        for p in doc.get("patches", [])
        if (p.get("target") or {}).get("group") == "kustomize.toolkit.fluxcd.io"
        and (p.get("target") or {}).get("kind") == "Kustomization"
    ]
    assert len(hits) == 1, "the estate interval lives in exactly one patch (crew#727)"
    return yaml.safe_load(hits[0]["patch"])["spec"]["interval"]


def test_the_estate_root_never_applies_the_sandbox():
    """The sandbox exists only while the founder's launch row exists."""
    offenders = [
        str(f)
        for f in (ROOT / "clusters").rglob("*.yaml")
        if "platform/sandbox" in f.read_text()
    ]
    assert offenders == [], f"sandbox must never ride the estate root: {offenders}"


def test_the_namespace_survives_prune():
    """protect-namespaces refuses namespace deletes; prune must skip it or expiry deadlocks."""
    ns = _by_kind()["Namespace"]
    assert ns["metadata"]["name"] == "demo-sandbox"
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )


def test_the_control_plane_is_oss_bounded_and_ephemeral():
    hr = _by_kind()["HelmRelease"]
    assert hr["spec"]["chart"]["spec"]["chart"] == "vcluster"
    assert hr["spec"]["chart"]["spec"]["version"] == "0.36.1"
    sts = hr["spec"]["values"]["controlPlane"]["statefulSet"]
    # The chart default image is the paid build; the OSS build must be pinned explicitly.
    assert sts["image"]["repository"] == "loft-sh/vcluster-oss"
    assert sts["image"]["registry"], (
        "cri-o short-name policy: every image names its registry"
    )
    # capacity-policy refuses container CPU requests over 250m without approval.
    m = re.fullmatch(r"(\d+)m", str(sts["resources"]["requests"]["cpu"]))
    assert m and int(m.group(1)) <= 250, (
        "control plane CPU request must clear admission"
    )
    # A one-hour sandbox keeps no state: no volume claim, restart resets it.
    assert sts["persistence"]["volumeClaim"]["enabled"] is False


def test_the_sandbox_interval_is_the_one_estate_value():
    hr = _by_kind()["HelmRelease"]
    assert hr["spec"]["interval"] == _estate_interval()


def test_services_carry_the_catalogue_label():
    """require-catalogue-entity: every Service needs backstage.io/kubernetes-id."""
    hr = _by_kind()["HelmRelease"]
    patches = hr["spec"]["postRenderers"][0]["kustomize"]["patches"]
    svc = [p for p in patches if p["target"]["kind"] == "Service"]
    assert svc and "backstage.io~1kubernetes-id" in svc[0]["patch"]
    seeded = hr["spec"]["values"]["experimental"]["deploy"]["vcluster"]["manifests"]
    assert "backstage.io/kubernetes-id" in seeded, (
        "seeded in-sandbox Services sync to the host and face admission too"
    )


def test_the_expiry_reaper_is_enabled_and_may_delete_the_flux_row():
    docs = [
        d
        for d in yaml.safe_load_all(
            (ROOT / "platform" / "kyverno" / "kyverno.yaml").read_text()
        )
        if isinstance(d, dict) and d.get("kind") == "HelmRelease"
    ]
    assert len(docs) == 1
    values = docs[0]["spec"]["values"]
    cc = values["cleanupController"]
    assert cc["enabled"] is True, (
        "cleanup controller off means the sandbox never expires"
    )
    extra = cc["rbac"]["clusterRole"]["extraResources"]
    flux = [
        r
        for r in extra
        if "kustomize.toolkit.fluxcd.io" in r["apiGroups"]
        and "kustomizations" in r["resources"]
    ]
    assert flux and {"list", "watch", "delete"} <= set(flux[0]["verbs"]), (
        "the reaper needs list/watch/delete on Flux Kustomizations to expire the sandbox"
    )


def test_the_runbook_quotes_the_launch_and_the_expiry():
    text = (ROOT / "docs" / "runbooks" / "demo-sandbox.md").read_text()
    assert "cleanup.kyverno.io/ttl" in text, "the runbook must quote the expiry label"
    assert "--prune" in text, "the launch command must prune, or expiry sweeps nothing"
    assert "platform/sandbox/vcluster" in text


def test_synced_services_have_an_admission_exception():
    """The syncer mints host Services at runtime; without this exception the sandbox's DNS
    and every guest deployment inside it are refused by require-catalogue-entity (Enforce)."""
    doc = yaml.safe_load(
        (ROOT / "platform" / "edge" / "catalogue-entity-exception.yaml").read_text()
    )
    matches = doc["spec"]["match"]["any"]
    hit = [
        m
        for m in matches
        if m["resources"].get("namespaces") == ["demo-sandbox"]
        and m["resources"]["kinds"] == ["Service"]
    ]
    assert hit, "demo-sandbox Services need the catalogue-entity exception to sync"
