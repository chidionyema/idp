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
import functools
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


@functools.lru_cache(maxsize=None)
def _docs(path):
    out = subprocess.run(["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return tuple(d for d in yaml.safe_load_all(out.stdout) if d)


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


#: The only two PriorityClasses a cluster has before this tree applies: Kubernetes creates them
#: itself (`system-cluster-critical`, `system-node-critical`; kube-apiserver bootstraps both).
#: Every other name a pod asks for is created by a row, and this map is measured from the tree --
#: `_priority_class_providers()` renders the rows and reads the PriorityClass objects out of them
#: -- so it cannot be widened by hand the way `PRE_INSTALLED` was.
BUILTIN_PRIORITY_CLASSES = {"system-cluster-critical", "system-node-critical"}


def _named(doc, key, out=None):
    """Every value of `key` anywhere in a rendered document.

    `priorityClassName` sits at a different depth in each shape it appears in: directly under a
    Deployment's pod template, under `spec.values...` in a HelmRelease, inside a CronJob's job
    template. A recursive walk asks the question once instead of once per shape.
    """
    out = [] if out is None else out
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k == key and isinstance(v, str):
                out.append(v)
            else:
                _named(v, key, out)
    elif isinstance(doc, list):
        for v in doc:
            _named(v, key, out)
    return out


def _priority_class_providers(rows):
    """PriorityClass name -> the row that creates it, read from the rendered tree."""
    out = {}
    for name, (path, _) in rows.items():
        for d in _docs(path) or ():
            if d.get("kind") == "PriorityClass":
                out[d["metadata"]["name"]] = name
    return out


def priority_class_offenders(docs, providers, available, row=None):
    """Pods that name a PriorityClass the ordering has not created yet.

    The same rule as `offenders()`, one layer over. A CRD is not the only cluster-scoped object a
    row can reference before it exists: the API server refuses a pod naming an absent
    PriorityClass with `no PriorityClass with name <x> was found`, the Deployment never rolls, the
    HelmRelease times out, and the row is ROOT-RED. Unlike a missing CRD this is invisible in a
    dry-run -- it is an admission failure at pod creation -- so nothing but ordering catches it.

    An unknown name is an offender, not a pass: a class no row creates cannot be waited for.

    Kyverno policies are the one shape read past. `platform/scheduling/require-priority-class.yaml`
    carries `priorityClassName: "?*"` and `priorityClassName: infrastructure-critical` inside
    `validate.pattern` -- those are the strings the policy matches *other* people's pods against,
    not a pod this row schedules, and reading them as references made this sweep report `no row
    creates PriorityClass/?*`. A kyverno.io document schedules nothing itself; whatever it
    generates is admitted later, in a cluster where the ordering has already run.
    """
    bad = []
    for d in docs:
        if _group(d["apiVersion"]) == "kyverno.io":
            continue
        for pc in sorted(set(_named(d, "priorityClassName"))):
            if pc in BUILTIN_PRIORITY_CLASSES:
                continue
            provider = providers.get(pc)
            if provider is not None and (provider in available or provider == row):
                continue
            where = f"needs row '{provider}'" if provider else f"no row creates PriorityClass/{pc}"
            bad.append(f"{d['kind']}/{d['metadata']['name']} asks for {pc} ({where})")
    return sorted(bad)


def test_no_flux_row_names_a_priority_class_its_ordering_has_not_created_yet():
    """crew#488, run 33213889505. The drill's receipt, verbatim:

        edge  2m44s  Warning  FailedCreate  replicaset/traefik-75cd5dd6b9
          Error creating: pods "traefik-75cd5dd6b9-" is forbidden:
          no PriorityClass with name infrastructure-critical was found

    `platform/edge/traefik.yaml` names `infrastructure-critical`; the class was created by the
    `scheduling` row, and `scheduling` dependsOn `edge`. A practical cycle: edge waits for a class
    that waits for edge. On OKE the class predated the dependsOn and nothing was ever wrong there,
    which is exactly why only a cluster with no history could find it -- `ready 3/39, cascaded 33`,
    one cause and thirty-three honest consequences.
    """
    rows = _rows()
    providers = _priority_class_providers(rows)
    assert len(providers) >= 2, f"the tree renders {providers} -- the sweep found no PriorityClass to check against"
    seen, asked = 0, 0
    for name, (path, _) in sorted(rows.items()):
        docs = _docs(path)
        if docs is None:
            continue
        seen += 1
        asked += sum(len(_named(d, "priorityClassName")) for d in docs)
        bad = priority_class_offenders(docs, providers, _closure(name, rows), row=name)
        assert bad == [], (
            f"row {name} ({path.relative_to(ROOT)}) creates pods the API server will refuse; its "
            f"closure is {sorted(_closure(name, rows))}: " + ", ".join(bad))
    assert seen > 25 and asked >= 10, (
        f"{seen} rows rendered and {asked} priorityClassName reference(s) read -- a sweep that "
        f"reads nothing passes for the wrong reason")


def test_the_traefik_incident_shape_is_refused():
    """The incident as a fixture, both directions. `edge` before the fix reached `scheduling`
    through nothing; after it, `priority-classes` is a row with no dependencies of its own."""
    docs = [{"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "traefik"},
             "spec": {"template": {"spec": {"priorityClassName": "infrastructure-critical"}}}}]
    before = {"infrastructure-critical": "scheduling"}
    after = {"infrastructure-critical": "priority-classes"}
    assert priority_class_offenders(docs, before, {"gateway-api-crds", "kyverno"}, row="edge") == [
        "Deployment/traefik asks for infrastructure-critical (needs row 'scheduling')"]
    assert priority_class_offenders(docs, after, {"gateway-api-crds", "kyverno", "priority-classes"},
                                    row="edge") == []


def test_a_priority_class_reference_nested_in_a_helm_release_is_read_too():
    """`platform/observability/langfuse.yaml` names the class inside `spec.values`, not under a
    pod template this file would recognise by shape. A guard that only understood one depth would
    have read the tree as clean while the langfuse pods were unschedulable."""
    docs = [{"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease", "metadata": {"name": "langfuse"},
             "spec": {"values": {"langfuse": {"web": {"deployment": {"priorityClassName": "infrastructure-critical"}}}}}}]
    assert priority_class_offenders(docs, {"infrastructure-critical": "priority-classes"}, set(), row="observability") == [
        "HelmRelease/langfuse asks for infrastructure-critical (needs row 'priority-classes')"]


def test_a_priority_class_no_row_creates_is_an_offender_and_never_waved_through():
    """The default-deny branch, the one a mutation of the CRD check slipped past in the first
    version of this file. Depending on every row in the estate cannot excuse a name nothing
    creates -- there is no row to wait for."""
    docs = [{"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "d"},
             "spec": {"template": {"spec": {"priorityClassName": "invented-critical"}}}}]
    providers = {"infrastructure-critical": "priority-classes"}
    assert priority_class_offenders(docs, providers, set(), row="x") == [
        "Deployment/d asks for invented-critical (no row creates PriorityClass/invented-critical)"]
    assert priority_class_offenders(docs, providers, set(providers.values()) | {"x"}, row="x") != []


def test_only_the_classes_kubernetes_creates_itself_are_free():
    """`BUILTIN_PRIORITY_CLASSES` is the one place with no row behind it, and it holds exactly the
    two names kube-apiserver bootstraps. A class the tree creates appearing in it would be the
    flat-allow-list habit starting again in a new file."""
    assert _priority_class_providers(_rows()).keys() & BUILTIN_PRIORITY_CLASSES == set()
    docs = [{"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "d"},
             "spec": {"template": {"spec": {"priorityClassName": "system-cluster-critical"}}}}]
    assert priority_class_offenders(docs, {}, set(), row="metrics-server") == []


def test_a_kyverno_pattern_is_not_read_as_a_pod_asking_for_a_class():
    """The over-fix guard on that exclusion, both halves. The policy's own strings are skipped;
    a Deployment in the same row is still read, so the exclusion cannot be widened into "the
    scheduling row is exempt"."""
    policy = {"apiVersion": "kyverno.io/v1", "kind": "ClusterPolicy", "metadata": {"name": "require-priority-class"},
              "spec": {"rules": [{"validate": {"pattern": {"spec": {"priorityClassName": "?*"}}}}]}}
    balloon = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "balloon"},
               "spec": {"template": {"spec": {"priorityClassName": "balloon"}}}}
    assert priority_class_offenders([policy], {}, set(), row="scheduling") == []
    assert priority_class_offenders([balloon], {"balloon": "priority-classes"}, set(), row="scheduling") == [
        "Deployment/balloon asks for balloon (needs row 'priority-classes')"]
