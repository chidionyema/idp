"""A chart renders more than one Deployment, and the gate was only ever reading the first.

2026-09-08. All three cert-manager pods and all four external-secrets pods were scheduled on
node 10.0.159.197. That node stopped answering the API server, so `webhook.cert-manager.io` and
`validate.externalsecret.external-secrets.io` -- both `failurePolicy: Fail` -- timed out on every
admission call. Flux fell to 14 of 80 Kustomizations Ready and could not apply the repair either,
because the repair is a manifest and admission refused it. Kyverno, already two replicas with a
required anti-affinity, kept one pod on the healthy node and degraded to roughly half its calls
rather than all of them.

`bin/idp-availability-gate` had carried the right standard since 2026-08-28 -- replicas >= 2, a
budget expressed as maxUnavailable, a required podAntiAffinity on `kubernetes.io/hostname`. It
could not have caught this: `grade_helm` read the TOP-LEVEL chart keys, and both webhooks live
under a `webhook:` sub-key. The controller's numbers were graded and called the release's.

These pin the component grading, and they pin the two live releases, so the day someone drops
`webhook.replicaCount` the suite says so instead of the cluster.
"""

import importlib.util
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SPEC = importlib.util.spec_from_loader(
    "availability_gate",
    importlib.machinery.SourceFileLoader(
        "availability_gate", os.path.join(ROOT, "bin", "idp-availability-gate")
    ),
)
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _hr(values, name="chart", ns="ns"):
    return {
        "apiVersion": "helm.toolkit.fluxcd.io/v2",
        "kind": "HelmRelease",
        "metadata": {"name": name, "namespace": ns},
        "spec": {"values": values},
    }


SURVIVES = {
    "replicaCount": 2,
    "podDisruptionBudget": {"enabled": True, "maxUnavailable": 1},
    "affinity": {
        "podAntiAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": [
                {"topologyKey": "kubernetes.io/hostname"}
            ]
        }
    },
}


def test_a_hardened_top_level_does_not_vouch_for_a_bare_sub_chart():
    """The exact shape of the incident: the release looks compliant, the webhook is a singleton."""
    hr = _hr(dict(SURVIVES, webhook={"resources": {}}))

    top, top_replicas = gate.grade_helm(hr, [])
    assert top == [], "the top level is hardened and must pass on its own terms"
    assert top_replicas == 2

    sub, sub_replicas = gate.grade_helm(hr, [], component="webhook")
    assert sub_replicas == 1
    assert len(sub) == 3, sub


def test_a_hardened_sub_chart_passes_on_its_own_numbers():
    hr = _hr({"replicaCount": 1, "webhook": SURVIVES})
    bad, replicas = gate.grade_helm(hr, [], component="webhook")
    assert bad == [], bad
    assert replicas == 2


def test_a_budget_beside_the_release_is_never_credited_to_a_component():
    """A sibling PDB is matched by the release's own app name, so it is the top level's."""
    pdb = {
        "kind": "PodDisruptionBudget",
        "metadata": {"name": "chart", "namespace": "ns"},
        "spec": {
            "maxUnavailable": 1,
            "selector": {"matchLabels": {"app.kubernetes.io/name": "chart"}},
        },
    }
    values = {
        "replicaCount": 2,
        "affinity": SURVIVES["affinity"],
        "webhook": {
            "replicaCount": 2,
            "affinity": SURVIVES["affinity"],
        },
    }
    hr = _hr(values)

    top, _ = gate.grade_helm(hr, [pdb])
    assert top == [], "the sibling budget is the top level's and must satisfy it"

    sub, _ = gate.grade_helm(hr, [pdb], component="webhook")
    assert any("podDisruptionBudget" in b for b in sub), sub


def test_a_component_is_a_surface_of_its_own():
    """Keyed on the release alone, the first sub-chart settled would silence the second."""
    assert gate.surface_key("ns/chart") == "ns/chart"
    assert gate.surface_key("ns/chart", "webhook") != gate.surface_key(
        "ns/chart", "cainjector"
    )
    assert gate.surface_key("ns/chart", "webhook") != gate.surface_key("ns/chart")


def _release(relpath, name):
    docs = yaml.safe_load_all(open(os.path.join(ROOT, relpath), encoding="utf-8"))
    return next(
        d
        for d in docs
        if d and d.get("kind") == "HelmRelease" and d["metadata"]["name"] == name
    )


def test_the_two_fail_closed_webhooks_in_this_estate_survive_losing_a_node():
    """Every instance of the class the incident belongs to, not just the class."""
    for relpath, name in (
        ("platform/edge/cert-manager.yaml", "cert-manager"),
        ("platform/secrets/external-secrets.yaml", "external-secrets"),
    ):
        bad, replicas = gate.grade_helm(
            _release(relpath, name), [], component="webhook"
        )
        assert bad == [], "%s webhook: %s" % (name, bad)
        assert replicas >= 2, "%s webhook has %s replicas" % (name, replicas)


def test_the_anti_affinity_selector_does_not_rest_on_the_release_name():
    """`app.kubernetes.io/instance` is the Helm release name.

    A required podAntiAffinity whose selector matches no pod is not a constraint -- it is two
    replicas free to share one node, which is the state this whole change exists to end. The
    first draft of these values selected on `instance` and matched nothing under any release
    name but the expected one.
    """
    for relpath, name in (
        ("platform/edge/cert-manager.yaml", "cert-manager"),
        ("platform/secrets/external-secrets.yaml", "external-secrets"),
    ):
        values = _release(relpath, name)["spec"]["values"]["webhook"]
        terms = values["affinity"]["podAntiAffinity"][
            "requiredDuringSchedulingIgnoredDuringExecution"
        ]
        for t in terms:
            keys = set(t["labelSelector"]["matchLabels"])
            assert keys, (
                "%s: an empty selector matches every pod in the namespace" % name
            )
            assert "app.kubernetes.io/instance" not in keys, name


def test_every_component_row_is_armed_in_the_cluster_by_name():
    """CI passing is not the cluster enforcing, and a component cannot be armed by a label.

    `availability.idp/tier: founder-facing` is a namespace label, and both of these namespaces
    also hold Deployments that are singletons on purpose -- cert-manager's cainjector,
    external-secrets' cert-controller, the bitwarden SDK server. Arming the namespace would
    refuse correct work, which LAW 38 calls an outage. So a component row names its Deployment
    and a rule matches that name, and this is what keeps the two files from drifting apart.
    """
    doc = yaml.safe_load(
        open(os.path.join(ROOT, "platform", "availability.yaml"), encoding="utf-8")
    )
    waived = {w["surface"] for w in doc["waivers"]}
    components = [r for r in doc["also_graded"] if r.get("component")]
    assert components, "the component rows are the whole subject of this file"

    covered = gate.policy_workloads()
    for r in components:
        wl = r.get("admission_workload")
        assert wl, "%s names no admission_workload" % r["surface"]
        if gate.surface_key(r["surface"], r["component"]) in waived:
            # A waived row is debt read out loud, not a passing surface. Arming admission for it
            # would refuse the very update that pays the debt off.
            assert wl not in covered, (
                "%s is waived but admission already enforces %s: one of the two is wrong"
                % (r["surface"], wl)
            )
            continue
        assert wl in covered, "%s: no rule in require-availability.yaml matches %s" % (
            r["surface"],
            wl,
        )


def test_the_gate_reads_the_kyverno_charts_spelling_of_anti_affinity():
    """Most charts nest it under `affinity`; the kyverno chart takes a bare `podAntiAffinity`.

    Reading only the first spelling would report `nothing in the values keeps the replicas off
    one node` about values that do exactly that -- a guard that refuses correct work, which
    LAW 38 calls an outage.
    """
    required = {
        "podAntiAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": [
                {"topologyKey": "kubernetes.io/hostname"}
            ]
        }
    }
    common = {
        "replicas": 2,
        "podDisruptionBudget": {"enabled": True, "maxUnavailable": 1},
    }

    nested, _ = gate.grade_helm(
        _hr({"c": dict(common, affinity=required)}), [], component="c"
    )
    assert nested == [], nested

    bare, _ = gate.grade_helm(_hr({"c": dict(common, **required)}), [], component="c")
    assert bare == [], bare

    preferred = {
        "podAntiAffinity": {
            "preferredDuringSchedulingIgnoredDuringExecution": [
                {
                    "weight": 1,
                    "podAffinityTerm": {"topologyKey": "kubernetes.io/hostname"},
                }
            ]
        }
    }
    weak, _ = gate.grade_helm(_hr({"c": dict(common, **preferred)}), [], component="c")
    assert any("one node" in b for b in weak), (
        "a preference is not a constraint: kyverno 3.9.0 ships exactly this shape and its two "
        "replicas were on separate nodes by luck (idp#2558)"
    )


def test_a_namespace_label_would_refuse_the_singletons_beside_the_webhook():
    """Why the narrower instrument exists, graded rather than asserted in prose.

    Each of these charts renders Deployments this estate deliberately runs at one replica. The
    namespace rule is `replicas: ">1"` with failureAction Enforce, so labelling the namespace
    would refuse every one of them.
    """
    singletons = {
        "platform/edge/cert-manager.yaml": ("cert-manager", ["cainjector"]),
        "platform/secrets/external-secrets.yaml": (
            "external-secrets",
            ["certController", "bitwarden-sdk-server"],
        ),
    }
    for relpath, (name, keys) in singletons.items():
        values = _release(relpath, name)["spec"]["values"]
        for k in keys:
            got = (values.get(k) or {}).get("replicaCount", 1)
            assert got == 1, (
                "%s/%s is no longer a singleton (replicaCount %s); if every workload in the "
                "namespace now survives a node, the namespace label is the better instrument "
                "and this test should be replaced by it" % (name, k, got)
            )
