"""Incident 2026-08-25: the `chaos` Flux row carried the Chaos Mesh HelmRelease and a
chaos-mesh.org Schedule in one Kustomization. Flux server-side dry-runs the whole row, the
Schedule CRD did not exist yet, the row failed every reconcile and Chaos Mesh was never
installed (24 h, flux events: no matches for kind "Schedule" in version chaos-mesh.org/v1alpha1).

Rung 4, and the guard was rewritten on 2026-08-28 (crew#488) because the first version graded a
proxy. It held one flat `PRE_INSTALLED` set of "groups the cluster has before any chart lands",
and every time a row tripped it the group was added to the set: `external-secrets.io`,
`cert-manager.io`, `kyverno.io`, `traefik.io`. All four are false on an empty cluster -- each is
installed by a HelmRelease in this very tree -- so the guard was true only of the live OKE
cluster, where they are all already there, and it passed on `platform/edge` while `edge` carried
the Kyverno chart and thirteen kyverno.io CRs in one row and could not bootstrap from zero. The
portability drill measured the consequence: `ready 2/38 layers on a cluster with no OCI`.

The rule the flat set could not express: a CR is fine when the row that installs its CRD is
*ordered before* the row carrying it. So the question is asked per row, against that row's own
transitive `dependsOn` closure, and a group is not "already there" -- it is provided by a named
row (`PROVIDED_BY`). Adding a group to that map does not widen the check; it points at a row, and
the row still has to be in the closure.
"""
import glob
import pathlib
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Groups a cluster genuinely has before this tree applies: Kubernetes' own, plus the Flux
#: controllers `bin/idp-hydrate` installs with `flux install
#: --components-extra=image-reflector-controller,image-automation-controller` (which is where
#: image.toolkit.fluxcd.io comes from -- not from a row).
BUILTIN = {
    "",
    "apps",
    "batch",
    "policy",
    "autoscaling",
    "rbac.authorization.k8s.io",
    "networking.k8s.io",
    "storage.k8s.io",
    "apiextensions.k8s.io",
    "apiregistration.k8s.io",
    "admissionregistration.k8s.io",
    "scheduling.k8s.io",
    "coordination.k8s.io",
    "source.toolkit.fluxcd.io",
    "helm.toolkit.fluxcd.io",
    "kustomize.toolkit.fluxcd.io",
    "notification.toolkit.fluxcd.io",
    "image.toolkit.fluxcd.io",
}

#: Which Flux row brings each group's CRDs into the cluster. A row may carry CRs of a group it
#: provides itself (the chart lands first inside the row); any other row must reach the provider
#: through `dependsOn`.
PROVIDED_BY = {
    "gateway.networking.k8s.io": "gateway-api-crds",
    "kyverno.io": "kyverno",
    "cert-manager.io": "edge",
    "traefik.io": "edge",
    "external-secrets.io": "external-secrets",
    "generators.external-secrets.io": "external-secrets",
    "chaos-mesh.org": "chaos-mesh",
    "core.k8sgpt.ai": "healing",
    "monitoring.coreos.com": "monitoring",
}


def _group(api_version):
    return api_version.split("/")[0] if "/" in api_version else ""


def _rows():
    """Every Flux Kustomization in the tree: name -> (path, direct dependsOn)."""
    out = {}
    for f in sorted(glob.glob(str(ROOT / "clusters" / "*" / "*.yaml"))):
        for d in yaml.safe_load_all(open(f)):
            if d and d.get("kind") == "Kustomization" and d["spec"].get("path"):
                out[d["metadata"]["name"]] = (ROOT / d["spec"]["path"],
                                              {x["name"] for x in d["spec"].get("dependsOn", [])})
    return out


def _closure(name, rows, seen=None):
    seen = set() if seen is None else seen
    for parent in rows.get(name, (None, set()))[1]:
        if parent not in seen:
            seen.add(parent)
            _closure(parent, rows, seen)
    return seen


def _docs(path):
    out = subprocess.run(["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def offenders(docs, available, row=None):
    """Resources that would dry-run before their CRD exists.

    `available` is the set of rows already applied when this row applies -- its transitive
    dependsOn closure. A group nobody in `PROVIDED_BY` claims is unknown to this guard and is
    reported too: an unmapped group is exactly how the chaos-mesh.org incident arrived.
    """
    bad = []
    for d in docs:
        g = _group(d["apiVersion"])
        if g in BUILTIN:
            continue
        provider = PROVIDED_BY.get(g)
        if provider is not None and (provider in available or provider == row):
            continue
        where = f"needs row '{provider}'" if provider else f"group '{g}' is provided by no row"
        bad.append(f"{d['kind']}/{d['metadata']['name']} ({where})")
    return sorted(bad)


def test_no_flux_row_carries_a_custom_resource_its_ordering_has_not_installed_yet():
    rows = _rows()
    seen, skipped = 0, []
    for name, (path, _) in sorted(rows.items()):
        docs = _docs(path)
        if docs is None:
            # rows needing gitignored inputs render elsewhere (test_incident_backstage_*)
            skipped.append(name)
            continue
        seen += 1
        bad = offenders(docs, _closure(name, rows), row=name)
        assert bad == [], (
            f"row {name} ({path.relative_to(ROOT)}) dry-runs {len(bad)} resource(s) before their "
            f"CRD exists; its closure is {sorted(_closure(name, rows))}: " + ", ".join(bad))
    assert seen > 25, f"only {seen} rows rendered ({skipped} skipped) -- the sweep is not covering the tree"


def test_every_group_the_tree_uses_is_either_built_in_or_owned_by_a_named_row():
    """The over-fix guard on the map itself. `PROVIDED_BY` is the only place a group can be
    excused, and a group that appears in the tree with no owner must not pass silently -- that is
    the flat-allow-list failure returning by another door."""
    rows = _rows()
    unowned = {}
    for name, (path, _) in rows.items():
        docs = _docs(path) or []
        for d in docs:
            g = _group(d["apiVersion"])
            if g not in BUILTIN and g not in PROVIDED_BY:
                unowned.setdefault(g, set()).add(name)
    assert unowned == {}, f"groups used by no known provider row: { {k: sorted(v) for k, v in unowned.items()} }"


def test_the_chaos_mesh_incident_shape_is_refused():
    docs = [{"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease", "metadata": {"name": "chaos-mesh"}},
            {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "Schedule", "metadata": {"name": "backstage-pod-kill"}}]
    assert offenders(docs, set(), row="chaos") == ["Schedule/backstage-pod-kill (needs row 'chaos-mesh')"]
    assert offenders(docs, {"chaos-mesh"}, row="chaos") == []


def test_a_group_no_row_claims_is_an_offender_and_never_waved_through():
    """Written because a mutation of `offenders()` that skipped unmapped groups stayed green: the
    map lookup was covered only by groups already in the map. An unmapped group is how the
    chaos-mesh.org incident arrived in the first place -- it is the default-deny branch, and no
    closure can excuse it, because nothing in the tree installs it."""
    docs = [{"apiVersion": "brand.new.io/v1alpha1", "kind": "Widget", "metadata": {"name": "w"}}]
    assert offenders(docs, set(), row="anywhere") == ["Widget/w (group 'brand.new.io' is provided by no row)"]
    assert offenders(docs, set(PROVIDED_BY.values()), row="anywhere") != [], (
        "depending on every row in the estate must not excuse a group no row installs")


def test_the_two_maps_do_not_overlap_so_a_group_cannot_be_quietly_promoted_to_built_in():
    """The flat set failed by growing. `BUILTIN` is the only place with no row behind it, so a
    group appearing in both maps is that growth starting again."""
    assert BUILTIN & set(PROVIDED_BY) == set()


def test_the_edge_incident_shape_is_refused_which_the_flat_allow_list_permitted():
    """crew#488: `platform/edge` carried the Kyverno chart and its own ClusterPolicy in one row.
    The old guard passed it because `kyverno.io` had been added to `PRE_INSTALLED`; this one asks
    whether the row that provides kyverno.io comes first."""
    docs = [{"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease", "metadata": {"name": "kyverno"}},
            {"apiVersion": "kyverno.io/v1", "kind": "ClusterPolicy", "metadata": {"name": "provider-independence"}}]
    assert offenders(docs, set(), row="edge") == ["ClusterPolicy/provider-independence (needs row 'kyverno')"]
    assert offenders(docs, {"kyverno"}, row="edge") == []


@pytest.mark.parametrize("group,cr", [
    ("traefik.io", "Middleware"),
    ("external-secrets.io", "ExternalSecret"),
    ("cert-manager.io", "ClusterIssuer"),
])
def test_the_four_groups_the_old_set_called_pre_installed_are_no_longer_free(group, cr):
    """Each of these was added to the flat set the day a row tripped over it, and each is
    installed by a chart in this tree. A row that does not order itself after the provider is an
    offender again, in every one of them."""
    docs = [{"apiVersion": f"{group}/v1", "kind": cr, "metadata": {"name": "x"}}]
    assert offenders(docs, set(), row="somewhere") != []
    assert offenders(docs, {PROVIDED_BY[group]}, row="somewhere") == []
