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
            if (
                d
                and d.get("kind") == "Kustomization"
                and str(d.get("apiVersion", "")).startswith("kustomize.toolkit")
                and d["spec"].get("path")
            ):
                out[d["metadata"]["name"]] = (
                    ROOT / d["spec"]["path"],
                    {x["name"] for x in d["spec"].get("dependsOn", [])},
                )
    return out


#: The GitRepository this repository is served to Flux as. A row pointing at any other source
#: names a path inside somebody else's checkout, so `kubectl kustomize` here cannot render it.
LOCAL_SOURCE = "flux-system"


def _foreign_rows():
    """Rows whose `sourceRef` is not this repository, read off the Kustomization rather than listed.

    crew#488. The sweeps below used to answer `if docs is None: continue` -- a row that failed to
    render was silently not checked, and a hand-maintained skip list would have grown one entry per
    complaint, which is the defect the closure rewrite removed in the first place. Three rows are
    foreign today (`estate-catalog` off an OCIRepository, `gateway-api-crds` off the upstream
    gateway-api GitRepository, `prospector` off the product's own), and every one of them is
    foreign because of a field, not because somebody typed its name.
    """
    out = set()
    for f in sorted(glob.glob(str(ROOT / "clusters" / "*" / "*.yaml"))):
        for d in yaml.safe_load_all(open(f)):
            if (
                d
                and d.get("kind") == "Kustomization"
                and str(d.get("apiVersion", "")).startswith("kustomize.toolkit")
                and d["spec"].get("path")
                and d["spec"].get("sourceRef", {}).get("name") != LOCAL_SOURCE
            ):
                out.add(d["metadata"]["name"])
    return out


def _sweep(rows, offenders_for, counter):
    """Run one offender check over every row of this repository at once.

    Returns `(offences, seen, asked)`. `offences` carries one line per row, and the sweep does not
    stop at the first: a check that asserts inside the loop reports one row per run, so a tree with
    three faults needs three runs to show three faults (LAW 28 -- an instrument you have to
    re-trigger to see the rest of the fault is not showing you the fault).

    A row of this repository that will not render is an offence too, not a skip.
    """
    foreign = _foreign_rows()
    offences, seen, asked = [], 0, 0
    for name, (path, _) in sorted(rows.items()):
        docs = _docs(path)
        if docs is None:
            if name not in foreign:
                offences.append(
                    f"row {name} ({path}) does not render, and its source is "
                    f"{LOCAL_SOURCE}, so the sweep cannot say whether it is clean"
                )
            continue
        seen += 1
        asked += sum(counter(d) for d in docs)
        bad = offenders_for(name, docs)
        if bad:
            offences.append(
                f"row {name} ({path.relative_to(ROOT)}), whose closure is "
                f"{sorted(_closure(name, rows))}: " + ", ".join(bad)
            )
    return offences, seen, asked


def _closure(name, rows, seen=None):
    seen = set() if seen is None else seen
    for parent in rows.get(name, (None, set()))[1]:
        if parent not in seen:
            seen.add(parent)
            _closure(parent, rows, seen)
    return seen


@functools.lru_cache(maxsize=None)
def _docs(path):
    out = subprocess.run(
        [
            "kubectl",
            "kustomize",
            "--load-restrictor",
            "LoadRestrictionsNone",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
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
        where = (
            f"needs row '{provider}'"
            if provider
            else f"group '{g}' is provided by no row"
        )
        bad.append(f"{d['kind']}/{d['metadata']['name']} ({where})")
    return sorted(bad)


def test_the_chaos_mesh_incident_shape_is_refused():
    docs = [
        {
            "apiVersion": "helm.toolkit.fluxcd.io/v2",
            "kind": "HelmRelease",
            "metadata": {"name": "chaos-mesh"},
        },
        {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "Schedule",
            "metadata": {"name": "backstage-pod-kill"},
        },
    ]
    assert offenders(docs, set(), row="chaos") == [
        "Schedule/backstage-pod-kill (needs row 'chaos-mesh')"
    ]
    assert offenders(docs, {"chaos-mesh"}, row="chaos") == []


def test_the_two_maps_do_not_overlap_so_a_group_cannot_be_quietly_promoted_to_built_in():
    """The flat set failed by growing. `BUILTIN` is the only place with no row behind it, so a
    group appearing in both maps is that growth starting again."""
    assert BUILTIN & set(PROVIDED_BY) == set()


def test_the_edge_incident_shape_is_refused_which_the_flat_allow_list_permitted():
    """crew#488: `platform/edge` carried the Kyverno chart and its own ClusterPolicy in one row.
    The old guard passed it because `kyverno.io` had been added to `PRE_INSTALLED`; this one asks
    whether the row that provides kyverno.io comes first."""
    docs = [
        {
            "apiVersion": "helm.toolkit.fluxcd.io/v2",
            "kind": "HelmRelease",
            "metadata": {"name": "kyverno"},
        },
        {
            "apiVersion": "kyverno.io/v1",
            "kind": "ClusterPolicy",
            "metadata": {"name": "provider-independence"},
        },
    ]
    assert offenders(docs, set(), row="edge") == [
        "ClusterPolicy/provider-independence (needs row 'kyverno')"
    ]
    assert offenders(docs, {"kyverno"}, row="edge") == []


@pytest.mark.parametrize(
    "group,cr",
    [
        ("traefik.io", "Middleware"),
        ("external-secrets.io", "ExternalSecret"),
        ("cert-manager.io", "ClusterIssuer"),
    ],
)
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
            where = (
                f"needs row '{provider}'"
                if provider
                else f"no row creates PriorityClass/{pc}"
            )
            bad.append(f"{d['kind']}/{d['metadata']['name']} asks for {pc} ({where})")
    return sorted(bad)


def test_the_traefik_incident_shape_is_refused():
    """The incident as a fixture, both directions. `edge` before the fix reached `scheduling`
    through nothing; after it, `priority-classes` is a row with no dependencies of its own."""
    docs = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "traefik"},
            "spec": {
                "template": {"spec": {"priorityClassName": "infrastructure-critical"}}
            },
        }
    ]
    before = {"infrastructure-critical": "scheduling"}
    after = {"infrastructure-critical": "priority-classes"}
    assert priority_class_offenders(
        docs, before, {"gateway-api-crds", "kyverno"}, row="edge"
    ) == [
        "Deployment/traefik asks for infrastructure-critical (needs row 'scheduling')"
    ]
    assert (
        priority_class_offenders(
            docs, after, {"gateway-api-crds", "kyverno", "priority-classes"}, row="edge"
        )
        == []
    )


def test_a_priority_class_no_row_creates_is_an_offender_and_never_waved_through():
    """The default-deny branch, the one a mutation of the CRD check slipped past in the first
    version of this file. Depending on every row in the estate cannot excuse a name nothing
    creates -- there is no row to wait for."""
    docs = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "d"},
            "spec": {"template": {"spec": {"priorityClassName": "invented-critical"}}},
        }
    ]
    providers = {"infrastructure-critical": "priority-classes"}
    assert priority_class_offenders(docs, providers, set(), row="x") == [
        "Deployment/d asks for invented-critical (no row creates PriorityClass/invented-critical)"
    ]
    assert (
        priority_class_offenders(
            docs, providers, set(providers.values()) | {"x"}, row="x"
        )
        != []
    )


def test_only_the_classes_kubernetes_creates_itself_are_free():
    """`BUILTIN_PRIORITY_CLASSES` is the one place with no row behind it, and it holds exactly the
    two names kube-apiserver bootstraps. A class the tree creates appearing in it would be the
    flat-allow-list habit starting again in a new file."""
    assert _priority_class_providers(_rows()).keys() & BUILTIN_PRIORITY_CLASSES == set()
    docs = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "d"},
            "spec": {
                "template": {"spec": {"priorityClassName": "system-cluster-critical"}}
            },
        }
    ]
    assert priority_class_offenders(docs, {}, set(), row="metrics-server") == []


def test_a_kyverno_pattern_is_not_read_as_a_pod_asking_for_a_class():
    """The over-fix guard on that exclusion, both halves. The policy's own strings are skipped;
    a Deployment in the same row is still read, so the exclusion cannot be widened into "the
    scheduling row is exempt"."""
    policy = {
        "apiVersion": "kyverno.io/v1",
        "kind": "ClusterPolicy",
        "metadata": {"name": "require-priority-class"},
        "spec": {
            "rules": [{"validate": {"pattern": {"spec": {"priorityClassName": "?*"}}}}]
        },
    }
    balloon = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "balloon"},
        "spec": {"template": {"spec": {"priorityClassName": "balloon"}}},
    }
    assert priority_class_offenders([policy], {}, set(), row="scheduling") == []
    assert priority_class_offenders(
        [balloon], {"balloon": "priority-classes"}, set(), row="scheduling"
    ) == ["Deployment/balloon asks for balloon (needs row 'priority-classes')"]


#: The namespaces a cluster has before this tree applies: Kubernetes' four, plus flux-system,
#: which `bin/idp-hydrate` creates with `flux install`. Everything else is created by a row, and
#: like the PriorityClasses that map is measured -- `_namespace_providers()` reads the Namespace
#: objects out of the rendered rows rather than trusting a list somebody kept up to date.
BUILTIN_NAMESPACES = {
    "default",
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "flux-system",
}


def _namespaces_used(doc):
    """Every namespace a rendered document needs to exist before it is applied.

    `metadata.namespace` for the object itself, and for a HelmRelease also `spec.targetNamespace`
    and `spec.storageNamespace`: the release lands somewhere other than where the HelmRelease
    object lives, and Helm refuses a release into a namespace that is not there.
    """
    out = set()
    ns = doc.get("metadata", {}).get("namespace")
    if ns:
        out.add(ns)
    spec = doc.get("spec")
    if doc.get("kind") == "HelmRelease" and isinstance(spec, dict):
        for key in ("targetNamespace", "storageNamespace"):
            if isinstance(spec.get(key), str):
                out.add(spec[key])
    return out


def _namespaces_provided(docs):
    """Every namespace a row's rendered documents bring into existence.

    A Namespace object, and a HelmRelease with `install.createNamespace`: Helm creates the
    namespace itself there and no Namespace document is rendered, so a map built only from
    Namespace objects would call every row waiting on that release an offender -- a guard
    refusing correct work (LAW 38), which is how allow-lists start being widened by hand. No row
    in this tree uses `install.createNamespace` today (measured 2026-08-28, 0 of 40 rows); this
    branch is what keeps adding one from being refused.
    """
    out = set()
    for d in docs:
        if d.get("kind") == "Namespace":
            out.add(d["metadata"]["name"])
        spec = d.get("spec")
        if (
            d.get("kind") == "HelmRelease"
            and isinstance(spec, dict)
            and spec.get("install", {}).get("createNamespace")
        ):
            ns = spec.get("targetNamespace") or d["metadata"].get("namespace")
            if ns:
                out.add(ns)
    return out


def _namespace_providers(rows):
    """Namespace name -> the row that creates it, read from the rendered tree."""
    out = {}
    for name, (path, _) in rows.items():
        for ns in sorted(_namespaces_provided(_docs(path) or ())):
            out.setdefault(ns, name)
    return out


def namespace_offenders(docs, providers, available, row=None):
    """Objects placed in a namespace the ordering has not created yet.

    The third face of the same rule, and the one the drill found last: `flux-system/cluster-state:
    ServiceAccount/backstage/cluster-state not found: namespaces "backstage" not found`. A
    namespace is cluster-scoped and named, exactly like a CRD or a PriorityClass, and a row that
    reaches into one it does not own has to be ordered after the row that does.
    """
    bad = []
    for d in docs:
        for ns in sorted(_namespaces_used(d)):
            if ns in BUILTIN_NAMESPACES:
                continue
            provider = providers.get(ns)
            if provider is not None and (provider in available or provider == row):
                continue
            where = (
                f"needs row '{provider}'"
                if provider
                else f"no row creates Namespace/{ns}"
            )
            bad.append(f"{d['kind']}/{d['metadata']['name']} lands in {ns} ({where})")
    return sorted(bad)


def test_the_cluster_state_incident_shape_is_refused():
    """Both directions, on the exact object the drill named."""
    docs = [
        {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {"name": "cluster-state", "namespace": "backstage"},
        }
    ]
    providers = {"backstage": "backstage"}
    assert namespace_offenders(
        docs, providers, {"scheduling"}, row="cluster-state"
    ) == ["ServiceAccount/cluster-state lands in backstage (needs row 'backstage')"]
    assert (
        namespace_offenders(
            docs, providers, {"scheduling", "backstage"}, row="cluster-state"
        )
        == []
    )


def test_a_namespace_a_helm_release_creates_itself_counts_as_provided():
    """Written after a mutation that deleted the `install.createNamespace` branch stayed green:
    the old version of this test passed a providers map it had built by hand, so it never ran the
    function it was about. It now reads the fixture through `_namespaces_provided`, the same call
    the sweep makes."""
    hr = {
        "apiVersion": "helm.toolkit.fluxcd.io/v2",
        "kind": "HelmRelease",
        "metadata": {"name": "chaos-mesh", "namespace": "flux-system"},
        "spec": {"targetNamespace": "chaos-mesh", "install": {"createNamespace": True}},
    }
    assert _namespaces_provided([hr]) == {"chaos-mesh"}
    assert _namespaces_provided(
        [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "spire"}}]
    ) == {"spire"}
    without = dict(hr, spec={"targetNamespace": "chaos-mesh"})
    assert _namespaces_provided([without]) == set(), (
        "a HelmRelease that does not ask Helm to create the namespace provides nothing"
    )


def test_the_namespaces_kubernetes_and_flux_install_create_are_the_only_free_ones():
    """The over-fix guard on the last of the three maps. A namespace this tree creates appearing
    in the built-in set is the flat-allow-list habit arriving for the third time."""
    assert _namespace_providers(_rows()).keys() & BUILTIN_NAMESPACES == set()
    docs = [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "c", "namespace": "kube-system"},
        }
    ]
    assert namespace_offenders(docs, {}, set(), row="metrics-server") == []


def test_every_row_of_this_repository_renders_and_a_row_that_does_not_is_an_offence():
    """The silent-miss guard. `if docs is None: continue` checked nothing and said nothing; a row
    of this repository that stops rendering (a moved path, a broken kustomization) would leave the
    sweep passing on 36 rows instead of 37, and the count bound alone would not notice one."""
    rows = _rows()
    foreign = _foreign_rows()
    assert foreign == {"estate-catalog", "gateway-api-crds", "prospector"}, sorted(
        foreign
    )
    local = {n for n in rows if n not in foreign}
    assert len(local) >= 35, sorted(local)
    unrenderable = sorted(n for n in local if _docs(rows[n][0]) is None)
    assert unrenderable == [], (
        "rows served from this repository that kubectl kustomize will not build: "
        + ", ".join(unrenderable)
    )

    #: And the offence is reported, not skipped: a row pointed at a directory that does not exist.
    offences, _, _ = _sweep(
        {"invented": (ROOT / "no-such-directory", set())},
        lambda name, docs: [],
        lambda d: 0,
    )
    assert len(offences) == 1 and "does not render" in offences[0], offences


def test_the_sweep_reports_every_offending_row_in_one_run():
    """LAW 28. Asserting inside the loop showed one row per run, so the tree that produced this
    incident -- `edge`, `chaos`, `cluster-state` and `spire` all wrong at once -- would have taken
    four runs to read. Two bad rows in, two lines out."""
    renders = _rows()["scheduling"][0]  # any path this repository really builds
    bad_rows = {"a": (renders, set()), "b": (renders, set())}
    offences, seen, asked = _sweep(
        bad_rows, lambda name, docs: [f"{name} is wrong"], lambda d: 1
    )
    assert len(offences) == 2, offences
    assert offences[0].startswith("row a") and offences[1].startswith("row b"), offences
    assert seen == 2 and asked > 0, (seen, asked)
