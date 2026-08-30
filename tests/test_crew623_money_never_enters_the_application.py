"""The money layer is a firewall, and it is dark until the founder says otherwise.

Founder, 2026-08-29: "we ban money from the application logic entirely ... The .NET API should
not know what a credit card is, it should not generate Stripe Checkout sessions, and it
absolutely should not parse Stripe webhooks", and "also we want user subscriptions also".

What was true when this file was written (measured, not assumed): `Store.Api/Payments/
StripeProvider.cs` held `using Stripe.Checkout;`, built Checkout Sessions, and called
`EventUtility.ConstructEvent` on the `Stripe-Signature` header. The layer these tests guard is
what replaces that. It is suspended, so merging this branch changes nothing that runs -- and
the last test here is the one that matters: it refuses a HALF flip at cutover.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "clusters" / "oke" / "commerce.yaml"
COMMERCE = ROOT / "platform" / "commerce"
BUS = ROOT / "platform" / "event-bus"
FEATURES = ROOT / "platform" / "features" / "features.yaml"
CONTRACT = BUS / "contract" / "estate.commerce.order_paid.json"


def _docs(path: Path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _all_docs(directory: Path):
    out = []
    for f in sorted(directory.rglob("*.yaml")):
        out.extend(_docs(f))
    return out


def _rows():
    return {
        d["metadata"]["name"]: d
        for d in _docs(ROWS)
        if d.get("kind") == "Kustomization"
    }


# ---------------------------------------------------------------- it is dark


def test_every_money_row_is_suspended():
    rows = _rows()
    assert set(rows) == {"commerce-data", "commerce", "event-bus"}
    for name, row in rows.items():
        assert row["spec"].get("suspend") is True, (
            f"{name} is not suspended: merging this branch would put a money layer on the "
            f"cluster. The cutover is its own PR, on the founder's word (LAW 11)."
        )


def test_nothing_in_the_money_layer_is_reachable_from_the_internet():
    routable = {"HTTPRoute", "Ingress", "Gateway", "IngressRoute"}
    for doc in _all_docs(COMMERCE) + _all_docs(BUS):
        assert doc.get("kind") not in routable, (
            f"{doc.get('kind')}/{doc['metadata']['name']} publishes the money layer while it "
            f"is meant to be dark"
        )


def test_the_commerce_namespace_cannot_attach_to_the_edge_while_dark():
    ns = [d for d in _all_docs(COMMERCE) if d.get("kind") == "Namespace"][0]
    labels = ns["metadata"].get("labels", {})
    assert "idp.estate/edge-attach" not in labels, (
        "the Gateway accepts routes from labelled namespaces only; while dark this label is "
        "the second lock after suspend"
    )
    assert labels.get("pod-security.kubernetes.io/enforce") == "restricted"


def test_the_chart_ships_with_signup_and_ingress_off():
    hr = [d for d in _all_docs(COMMERCE) if d.get("kind") == "HelmRelease"][0]
    values = hr["spec"]["values"]
    assert values["global"]["ingress"]["enabled"] is False
    assert values["global"]["signup"]["enabled"] is False, (
        "self-service signup on the service that holds the money is a default nobody chose"
    )
    assert values["global"]["segment"]["enabled"] is False, (
        "no third-party telemetry from the layer that holds the money"
    )


# ------------------------------------------------------- it is pinned and sound


@pytest.mark.parametrize(
    "directory, chart, version",
    [(COMMERCE, "lago", "1.28.0"), (BUS, "nats", "2.14.6")],
)
def test_the_chart_is_pinned_to_an_exact_version(directory, chart, version):
    hrs = [d for d in _all_docs(directory) if d.get("kind") == "HelmRelease"]
    spec = [
        h["spec"]["chart"]["spec"]
        for h in hrs
        if h["spec"]["chart"]["spec"]["chart"] == chart
    ]
    assert spec, f"no HelmRelease for chart {chart}"
    got = str(spec[0]["version"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", got), (
        f"{chart} is pinned to {got!r}. A range or a floating tag on the money layer means the "
        f"chart under the ledger can change without a commit."
    )
    assert got == version


def test_every_money_workload_names_a_class_and_is_guaranteed():
    kinds = {"Deployment", "StatefulSet"}
    workloads = [d for d in _all_docs(COMMERCE) if d.get("kind") in kinds]
    assert workloads, "no workloads found; the ledger and the queue should be here"
    for w in workloads:
        pod = w["spec"]["template"]["spec"]
        name = w["metadata"]["name"]
        assert pod.get("priorityClassName"), (
            f"{name} names no priorityClassName (crew#539)"
        )
        assert pod["priorityClassName"] != "infrastructure-critical", (
            f"{name} borrows the radio-room class; that set is the six workloads in "
            f"platform/priority-classes"
        )
        for c in pod["containers"]:
            req, lim = c["resources"]["requests"], c["resources"]["limits"]
            assert req == lim, (
                f"{name}/{c['name']} is Burstable: the kubelet evicts it before Guaranteed "
                f"pods, and this one holds the money ledger (crew#539 CP9)"
            )


def test_no_payment_credential_is_ever_typed_in_the_tree():
    # R49: name where a secret lives, never the value.
    forbidden = re.compile(r"\b(sk_live_|sk_test_|whsec_|rk_live_)\w")
    for f in list(COMMERCE.rglob("*.yaml")) + list(BUS.rglob("*.yaml")) + [ROWS]:
        assert not forbidden.search(f.read_text()), (
            f"a payment credential is typed in {f}"
        )


def test_the_payment_credential_is_scoped_to_the_commerce_namespace():
    secrets = [d for d in _all_docs(COMMERCE) if d.get("kind") == "ExternalSecret"]
    payment = [
        s for s in secrets if s["metadata"]["name"] == "commerce-payment-provider"
    ]
    assert payment, "the layer that holds the money has no payment-provider secret"
    assert payment[0]["metadata"]["namespace"] == "commerce"
    # and it exists nowhere else in the platform tree, which is the point of the firewall
    others = [
        f
        for f in (ROOT / "platform").rglob("*.yaml")
        if COMMERCE not in f.parents and "commerce-payment-provider" in f.read_text()
    ]
    assert not others, f"the payment credential is reachable from {others}"


# ------------------------------------------------------------- the contract


def test_the_event_contract_is_the_founders_payload():
    schema = json.loads(CONTRACT.read_text())
    assert schema["properties"]["event"]["const"] == "estate.commerce.order_paid"
    assert set(schema["required"]) == {
        "event",
        "user_id",
        "item_sku",
        "amount_paid",
        "currency",
    }
    assert schema["additionalProperties"] is False
    assert schema["properties"]["amount_paid"]["type"] == "integer", (
        "money in a float is a rounding bug with a customer attached"
    )
    example = schema["examples"][0]
    assert example == {
        "event": "estate.commerce.order_paid",
        "user_id": "usr_998",
        "item_sku": "100_ai_credits",
        "amount_paid": 2000,
        "currency": "USD",
    }


def test_the_bus_keeps_events_for_a_consumer_that_is_down():
    hr = [d for d in _all_docs(BUS) if d.get("kind") == "HelmRelease"][0]
    js = hr["spec"]["values"]["config"]["jetstream"]
    assert js["enabled"] is True, (
        "without JetStream a consumer that is restarting when order_paid fires never sees it, "
        "and no log anywhere says so"
    )
    assert js["fileStore"]["pvc"]["enabled"] is True


# ------------------------------------------------- the guard that fires at cutover


def test_the_cutover_cannot_be_half_done():
    """LAW 45. This passes trivially today and is the whole reason the file exists.

    The dangerous state is not "dark" and not "live" -- it is half. A row un-suspended while
    the namespace still cannot attach to the edge gives a money service that runs, takes the
    webhook, and is unreachable by the buyer. A namespace opened to the edge while the feature
    register still says "off" gives a live money path nobody chose. This refuses both.
    """
    rows = _rows()
    live = [n for n, r in rows.items() if r["spec"].get("suspend") is not True]
    if not live:
        return  # still dark, nothing to enforce

    register = yaml.safe_load(FEATURES.read_text())
    commerce = [f for f in register["features"] if f["name"] == "commerce"]
    assert commerce, (
        "the commerce rows are live but the feature register has no row for them"
    )
    assert commerce[0]["default"] == "on", (
        f"rows {live} are live while platform/features/features.yaml still defaults commerce "
        f"to {commerce[0]['default']!r}: the plan does not count a layer that is running"
    )

    ns = [d for d in _all_docs(COMMERCE) if d.get("kind") == "Namespace"][0]
    labels = ns["metadata"].get("labels", {})
    assert labels.get("idp.estate/edge-attach") == "true", (
        "the commerce row is live but the Gateway will refuse its route: a money service that "
        "runs and cannot be reached is the worst of the three states"
    )
    assert labels.get("availability.idp/tier") == "founder-facing", (
        "a live checkout endpoint is founder-facing; that label is what forces two replicas "
        "and a spread across nodes (crew#555)"
    )


def test_the_chart_that_cannot_name_a_class_has_one_patched_in():
    """The Lago chart ships no `priorityClassName` field of its own -- it appears in
    lago-1.28.0.tgz only inside the bundled minio subchart, which is disabled. Its Deployments
    would land in a namespace labelled `app.kubernetes.io/part-of: idp` naming no class, which is
    exactly what `platform-workload-names-a-class` audits, and that rule stays on Audit until a
    pass finds zero violations. So the class is patched in at render time.
    """
    releases = [d for d in _all_docs(COMMERCE) if d.get("kind") == "HelmRelease"]
    assert releases, "the money layer installs no chart"
    for hr in releases:
        patches = [
            p
            for r in hr["spec"].get("postRenderers", [])
            for p in r.get("kustomize", {}).get("patches", [])
        ]
        assert patches, (
            f"{hr['metadata']['name']} renders a chart with no priorityClassName field and "
            f"patches nothing in; every pod it ships is a PolicyReport row (crew#539)"
        )
        classed = [
            p
            for p in patches
            if p.get("target", {}).get("kind") == "Deployment"
            and "priorityClassName: platform-batch" in p["patch"]
        ]
        assert classed, (
            f"{hr['metadata']['name']} post-renders something, but no patch gives its "
            f"Deployments a priorityClassName"
        )


def _cpu(v):
    v = str(v)
    return float(v[:-1]) / 1000 if v.endswith("m") else float(v)


def _mem_gi(v):
    v = str(v)
    for suffix, gi in (
        ("Gi", 1.0),
        ("Mi", 1 / 1024),
        ("G", 1 / 1.073741824),
        ("M", 1 / 1073.741824),
    ):
        if v.endswith(suffix):
            return float(v[: -len(suffix)]) * gi
    return float(v) / 1073741824


# WHAT ACTUALLY RUNS, and the only honest way to know it: the pods helm produces, not the keys
# the values file happens to carry. This file used to read the values dict and call the answer a
# size. It was wrong twice on 2026-08-29, both times because a values key is a request to a chart
# and not a description of a pod:
#
#   1. `replicaCount: 0` on four components. lago's key is `replicas`; helm ignored the line and
#      rendered three worker pods this repository claimed were switched off, and the published
#      figure was short by their whole cost.
#   2. Every `resources.requests` at any depth was summed, so the one-shot database migration Job
#      -- a Helm hook that runs once and exits -- was counted as standing capacity.
#
# So the size is measured from `helm template` here, with the same chart, version and values
# helm-controller will use, and with the post-renderer's `$patch: delete` removals applied, which
# is what the cluster ends up holding. When helm is not installed the render cannot happen and
# this says so and skips: the same judgement runs in CI and in .githooks/pre-push through
# bin/idp-kyverno-render, which renders this chart and puts the cluster's admission policies over
# it. A machine without helm is not a licence to publish an unmeasured number (LAW 38, LAW 28).
LAGO_RUNNING_PODS = {
    "lago-front": ("50m", "128Mi"),
    "lago-api": ("200m", "512Mi"),
    "lago-worker": ("100m", "512Mi"),
    "lago-clock": ("25m", "128Mi"),
    "lago-clock-worker": ("100m", "384Mi"),
    "lago-billing-worker": ("100m", "384Mi"),
    "lago-webhook-worker": ("100m", "384Mi"),
    "lago-payment-worker": ("100m", "384Mi"),
}

# Measured 2026-08-29 from the render below, on the branch that carries it:
#   lago            0.775 cores  2.75 Gi  across the eight Deployments above
#   commerce-db     0.100        0.25     platform/commerce/data/postgres.yaml
#   commerce-redis  0.050        0.13     platform/commerce/data/redis.yaml
#   nats            0.110        0.28     jetstream 100m/256Mi plus the exporter 10m/32Mi
#   -------------------------------------
#   total           1.035 cores  3.41 Gi  standing, on a node that is 6 OCPU / 24 Gi
#
# Plus lago-migrate-db, a Helm hook asking 100m / 512Mi that runs once per install and upgrade
# and then exits. It has to fit, it is not standing cost, and it is why the two are separate.
#
# The ceilings are above the measurement with room for one component to grow, and low enough that
# a chart bump doubling a request fails here rather than at 3 a.m. on the node.
COMMERCE_CPU_CEILING = 1.5
COMMERCE_MEMORY_CEILING_GI = 4.0


def _lago_hr():
    hrs = [
        d
        for d in _all_docs(COMMERCE)
        if d.get("kind") == "HelmRelease" and d["metadata"]["name"] == "lago"
    ]
    assert len(hrs) == 1, "expected exactly one lago HelmRelease"
    return hrs[0]


def _deleted_by_post_render(hr):
    """The names the post-renderer drops, read out of the HelmRelease rather than hardcoded."""
    gone = set()
    for r in hr["spec"].get("postRenderers") or []:
        for patch in (r.get("kustomize") or {}).get("patches") or []:
            body = patch.get("patch") or ""
            if "$patch: delete" in body:
                gone.add(patch["target"]["name"])
    return gone


def _render_lago():
    """`helm template` with the chart, version and values helm-controller will use."""
    helm = shutil.which("helm")
    if not helm:
        pytest.skip(
            "helm is not installed, so the chart cannot be rendered and the size cannot be "
            "measured here; bin/idp-kyverno-render does it in CI and in the pre-push hook"
        )
    hr = _lago_hr()
    chart = hr["spec"]["chart"]["spec"]
    src = [
        d
        for d in _all_docs(COMMERCE)
        if d.get("kind") == "HelmRepository"
        and d["metadata"]["name"] == chart["sourceRef"]["name"]
    ][0]
    with tempfile.TemporaryDirectory() as tmp:
        vals = Path(tmp) / "values.yaml"
        vals.write_text(yaml.safe_dump(hr["spec"]["values"]))
        env = {
            **os.environ,
            "HELM_REPOSITORY_CACHE": tmp,
            "HELM_CACHE_HOME": tmp,
            "HELM_REPOSITORY_CONFIG": str(Path(tmp) / "repositories.yaml"),
        }
        r = subprocess.run(
            [
                helm,
                "template",
                "lago",
                chart["chart"],
                "--repo",
                src["spec"]["url"],
                "--version",
                str(chart["version"]),
                "-f",
                str(vals),
                "--namespace",
                "commerce",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
    if r.returncode != 0:
        pytest.skip(f"the chart could not be pulled here: {r.stderr.strip()[:200]}")
    gone = _deleted_by_post_render(hr)
    return [
        d
        for d in yaml.safe_load_all(r.stdout)
        if d and d["metadata"]["name"] not in gone
    ]


def test_every_running_pod_is_one_this_repository_sized():
    """No pod appears that this file did not expect, and none is left at the chart's default.

    The chart's own defaults for these eight ask for 6.80 CPU and 6.75 Gi -- written for a
    cluster metering usage for many tenants. On a 6-OCPU node that is a layer which never
    schedules the day it is switched on, and nothing in this repository would have said so.
    """
    deployments = {
        d["metadata"]["name"]: d
        for d in _render_lago()
        if d["kind"] == "Deployment" and int(d["spec"].get("replicas", 1)) > 0
    }
    assert set(deployments) == set(LAGO_RUNNING_PODS), (
        f"the render holds {sorted(deployments)}; this file expects "
        f"{sorted(LAGO_RUNNING_PODS)}. A component switched on or off in values, or a chart "
        f"bump renaming one, changes what the node is asked for and is not a silent edit."
    )
    for name, (cpu, mem) in LAGO_RUNNING_PODS.items():
        containers = deployments[name]["spec"]["template"]["spec"]["containers"]
        assert len(containers) == 1, f"{name} is no longer a single-container pod"
        requests = (containers[0].get("resources") or {}).get("requests") or {}
        assert (requests.get("cpu"), requests.get("memory")) == (cpu, mem), (
            f"{name} asks for {requests}, this repository sized it at {cpu}/{mem}"
        )


def test_a_switched_off_component_is_absent_from_the_manifest_not_a_husk():
    """pdf and events-worker have no `enabled` guard in this chart, so they are removed.

    A Deployment at zero replicas still has to carry a probe, a priority class, a security
    context and a request, and a reader has to work out that it never runs. The post-renderer
    drops them; this proves the drop matched, which a comment cannot.
    """
    rendered = {
        d["metadata"]["name"] for d in _render_lago() if d["kind"] == "Deployment"
    }
    gone = _deleted_by_post_render(_lago_hr())
    assert gone == {"lago-pdf", "lago-events-worker"}, (
        f"the post-renderer removes {sorted(gone)}; expected the two guardless disabled ones"
    )
    assert not (rendered & gone), (
        f"still in the manifest after the removal: {rendered & gone}"
    )


def test_the_whole_money_layer_fits_on_the_node_it_would_run_on():
    """Every standing pod of the three suspended rows, against one ceiling.

    The Helm hook that migrates the database is excluded on purpose: it runs once per install
    and exits, so counting it as standing capacity overstates the layer for as long as it is on.
    """
    total_cpu = total_mem = 0.0
    for d in _render_lago():
        if d["kind"] != "Deployment":
            continue
        replicas = int(d["spec"].get("replicas", 1))
        for c in d["spec"]["template"]["spec"]["containers"]:
            requests = (c.get("resources") or {}).get("requests") or {}
            total_cpu += _cpu(requests.get("cpu", "0")) * replicas
            total_mem += _mem_gi(requests.get("memory", "0")) * replicas
    for directory in (COMMERCE, BUS):
        for doc in _all_docs(directory):
            if doc.get("kind") in ("StatefulSet", "Deployment"):
                for c in doc["spec"]["template"]["spec"]["containers"]:
                    requests = (c.get("resources") or {}).get("requests") or {}
                    total_cpu += _cpu(requests.get("cpu", "0"))
                    total_mem += _mem_gi(requests.get("memory", "0"))
            elif doc.get("kind") == "HelmRelease" and doc["metadata"]["name"] == "nats":
                # The NATS chart puts its requests under `config.jetstream.container.merge`,
                # three levels below the values root; reading only the top level counted it as
                # zero, the same silent miss the capacity guard had (crew#623).
                cpu, mem = _requests_anywhere(doc["spec"].get("values") or {})
                total_cpu += cpu
                total_mem += mem
    assert 0 < total_cpu <= COMMERCE_CPU_CEILING, (
        f"the money layer asks for {total_cpu:.2f} cores, ceiling {COMMERCE_CPU_CEILING}"
    )
    assert 0 < total_mem <= COMMERCE_MEMORY_CEILING_GI, (
        f"the money layer asks for {total_mem:.2f} Gi, ceiling {COMMERCE_MEMORY_CEILING_GI}"
    )


def _requests_anywhere(node):
    """Every `resources.requests` at any depth, skipping any branch switched off.

    Only used for a chart this repository does not render here (NATS): `enabled: false` and
    `replicas: 0` both mean no pod. `replicaCount` is deliberately NOT read -- it is the key
    that was believed and was not the chart's, and honouring it here would keep that belief
    alive somewhere in this estate.
    """
    cpu = mem = 0.0
    if isinstance(node, dict):
        if node.get("replicas") == 0 or node.get("enabled") is False:
            return 0.0, 0.0
        requests = (node.get("resources") or {}).get("requests") or {}
        if isinstance(requests, dict):
            if requests.get("cpu"):
                cpu += _cpu(requests["cpu"])
            if requests.get("memory"):
                mem += _mem_gi(requests["memory"])
        for value in node.values():
            c, m = _requests_anywhere(value)
            cpu += c
            mem += m
    elif isinstance(node, list):
        for value in node:
            c, m = _requests_anywhere(value)
            cpu += c
            mem += m
    return cpu, mem
