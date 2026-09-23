"""crew#727: reconcile intervals are one estate value, and reconcile state is visible.

Founder, 2026-08-31, verbatim: "it shouldn't be a number anyone has to know... the interval
field and the time to land a change are different things, and nothing in your tooling says
so... Set intervals consistently and deliberately across every HelmRelease and Kustomization.
Not per-chart guesses. One value in the base patch — 10m for drift detection is a reasonable
estate-wide default... Make the actual state visible instead of inferred."

The distinction, stated once where CI can hold it: a Kustomization/HelmRelease `interval` is
drift detection — how often Flux re-asserts git against the cluster when nothing changed.
Time-to-land is the flux-system GitRepository poll (1m) plus the dependency chain: a new git
revision triggers reconciliation immediately, whatever the drift interval says. Measured spread
before this wave: Kustomizations 34x1m + 14x10m + 1x1m0s, HelmReleases 24x1h + 2x10m — three
spellings of a decision nobody made.
"""

import glob
import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
KUST = ROOT / "clusters" / "oke" / "kustomization.yaml"


def base_value() -> str:
    doc = yaml.safe_load(KUST.read_text())
    hits = [
        p
        for p in doc.get("patches", [])
        if (p.get("target") or {}).get("group") == "kustomize.toolkit.fluxcd.io"
        and (p.get("target") or {}).get("kind") == "Kustomization"
    ]
    assert len(hits) == 1, (
        "exactly one estate interval patch, the one place the value lives"
    )
    return yaml.safe_load(hits[0]["patch"])["spec"]["interval"]


def flux_docs():
    files = glob.glob(
        str(ROOT / "clusters" / "**" / "*.yaml"), recursive=True
    ) + glob.glob(str(ROOT / "platform" / "**" / "*.yaml"), recursive=True)
    for f in files:
        if "flux-system/" in f:
            continue  # gotk-*.yaml is flux-generated; the base patch overrides it in-cluster
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if isinstance(d, dict):
                yield f, d


def test_every_kustomization_and_helmrelease_interval_is_the_one_estate_value():
    v = base_value()
    bad = []
    for f, d in flux_docs():
        kind = d.get("kind")
        api = str(d.get("apiVersion", ""))
        iv = (d.get("spec") or {}).get("interval")
        if iv is None:
            continue
        if (kind == "Kustomization" and api.startswith("kustomize.toolkit")) or (
            kind == "HelmRelease" and api.startswith("helm.toolkit")
        ):
            if str(iv) != str(v):
                bad.append(
                    f"{f}: {kind} {d['metadata'].get('name')} interval={iv} != {v}"
                )
    assert not bad, (
        "per-chart guesses (founder 2026-08-31: one estate value):\n" + "\n".join(bad)
    )


def test_no_file_beside_the_base_patch_is_silently_dropped():
    """With an explicit resources list, an unlisted file is not applied and prune deletes its
    objects. The list is pinned to the directory: adding a file without a row here is red CI."""
    doc = yaml.safe_load(KUST.read_text())
    listed = set(doc["resources"])
    on_disk = {p.name for p in (ROOT / "clusters" / "oke").glob("*.yaml")} - {
        "kustomization.yaml"
    }
    on_disk |= {"flux-system"}
    assert listed == on_disk, (
        f"listed-but-missing={listed - on_disk} unlisted={on_disk - listed}"
    )


def test_landing_speed_is_the_source_poll_not_the_drift_interval():
    """A merged change lands at GitRepository-poll speed; the 10m drift value never gates it.
    If someone 'standardises' the source poll to 10m, changes land ten minutes late — red."""
    docs = yaml.safe_load_all(
        (ROOT / "clusters/oke/flux-system/gotk-sync.yaml").read_text()
    )
    git = next(
        d for d in docs if isinstance(d, dict) and d.get("kind") == "GitRepository"
    )
    assert git["spec"]["interval"] in ("30s", "1m", "1m0s"), (
        "the flux-system GitRepository poll is time-to-land; it stays at a minute, "
        "not at the drift default"
    )


def test_the_receipt_row_says_which_revision_is_applied():
    """Founder: make the actual state visible instead of inferred. The cluster receipt's
    Kustomization and HelmRelease rows carry the applied revision, so 'did my merge land'
    is a read, never an inference from interval arithmetic."""
    text = (ROOT / "platform" / "state" / "cluster-state.yaml").read_text()
    assert "lastAppliedRevision" in text and "lastAttemptedRevision" in text


def _builder():
    loader = importlib.machinery.SourceFileLoader(
        "estate_state_build", str(ROOT / "bin" / "idp-estate-state-build")
    )
    spec = importlib.util.spec_from_loader("estate_state_build", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_state_page_carries_every_reconcile_row_not_only_the_failed():
    """flux get all -A, as a graded receipt: ready rows appear in `reconcile` with revision and
    since; `flux_rows` (the red-row grader) still carries only the not-ready ones."""
    mod = _builder()
    body = {
        "flux": [
            {
                "kind": "Kustomization",
                "ns": "flux-system",
                "name": "edge",
                "ready": True,
                "message": "Applied revision: main@sha1:abc",
                "since": "2026-08-31T05:00:00Z",
                "revision": "main@sha1:abc",
            },
            {
                "kind": "HelmRelease",
                "ns": "tailscale",
                "name": "tailscale-operator",
                "ready": False,
                "message": "Helm upgrade failed",
                "since": "2026-08-31T04:00:00Z",
                "revision": "1.102.3",
            },
            {
                "kind": "HelmRepository",
                "ns": "flux-system",
                "name": "traefik",
                "ready": True,
                "message": "ok",
                "since": "2026-08-31T05:00:00Z",
            },
        ],
        "flux_not_ready": [
            {
                "kind": "HelmRelease",
                "ns": "tailscale",
                "name": "tailscale-operator",
                "ready": False,
                "message": "Helm upgrade failed",
            }
        ],
    }
    import json as _json

    text = (
        "FAIL cluster-state at 2026-08-31T05:00:00Z nodes=2 ready=2 flux_not_ready=1\n"
        + _json.dumps(body)
    )
    got = mod.parse_cluster_receipt(text)
    rec = got.get("reconcile")
    assert rec is not None, "the receipt's full flux table must reach the state page"
    kinds = {(r["kind"], r["name"]): r for r in rec}
    assert ("Kustomization", "edge") in kinds, (
        "a READY row is visible, not only the failed ones"
    )
    assert kinds[("Kustomization", "edge")]["revision"] == "main@sha1:abc"
    assert kinds[("Kustomization", "edge")]["since"] == "2026-08-31T05:00:00Z"
    assert ("HelmRepository", "traefik") not in kinds, (
        "chart polling is a different knob"
    )
    assert [r["name"] for r in got["flux_rows"]] == ["tailscale-operator"], (
        "the red-row grader is unchanged"
    )
