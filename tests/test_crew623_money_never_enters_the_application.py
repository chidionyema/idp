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
import re
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


# The eight Deployments the values leave running once ClickHouse, PDF and minio are off.
LAGO_RUNNING = (
    "front",
    "api",
    "worker",
    "clock",
    "clockWorker",
    "billingWorker",
    "webhookWorker",
    "paymentWorker",
)

# The node is 6 OCPU / 24 Gi (`bin/idp-features plan`: "smallest A1-6-24"), and the rest of the
# platform already asks for most of it. One ceiling for the whole money layer, chosen so that
# switching it on is a scheduling decision somebody made rather than one nobody noticed.
COMMERCE_CPU_CEILING = 1.5
COMMERCE_MEMORY_CEILING_GI = 4.0


def _requests_anywhere(node):
    """Every `resources.requests` at any depth, skipping any branch switched off.

    A component with `replicaCount: 0` ships no pod, so neither it nor anything under it is
    capacity. Everything else counts, wherever the chart's author chose to nest it.
    """
    cpu = mem = 0.0
    if isinstance(node, dict):
        if node.get("replicaCount") == 0 or node.get("enabled") is False:
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


def test_every_running_chart_component_names_its_own_size():
    """A chart default is not a number in this repository, so no guard here can read it.

    Measured 2026-08-29 from lago-1.28.0.tgz values.yaml: the chart's own defaults for these
    eight Deployments ask for 6.80 CPU and 6.75 Gi of requests -- written for a cluster metering
    usage for many tenants. On a 6-OCPU node that is a layer which never schedules the day it is
    switched on, and nothing in this repository would have said so. Every component that runs
    names its request here, in git, where the capacity guard and this test can both read it.
    """
    hrs = [
        d
        for d in _all_docs(COMMERCE)
        if d.get("kind") == "HelmRelease" and d["metadata"]["name"] == "lago"
    ]
    assert len(hrs) == 1, "expected exactly one lago HelmRelease"
    values = hrs[0]["spec"]["values"]
    for name in LAGO_RUNNING:
        block = values.get(name)
        assert isinstance(block, dict), (
            f"{name} is left at the chart's own default size"
        )
        requests = (block.get("resources") or {}).get("requests") or {}
        assert requests.get("cpu") and requests.get("memory"), (
            f"lago {name} names no cpu and memory request; the chart default for it is "
            f"sized for a metering cluster, not this node"
        )


def test_the_whole_money_layer_fits_on_the_node_it_would_run_on():
    """The three suspended rows together, against one ceiling."""
    total_cpu = total_mem = 0.0
    for directory in (COMMERCE, BUS):
        for doc in _all_docs(directory):
            if doc.get("kind") == "HelmRelease":
                # Recursive, not one level. The NATS chart puts its requests under
                # `config.jetstream.container.merge.resources`, three levels below the values
                # root, and reading only the top level counted it as zero -- the same silent
                # miss the capacity guard had, measured the same day (crew#623).
                cpu, mem = _requests_anywhere(doc["spec"].get("values") or {})
                total_cpu += cpu
                total_mem += mem
            elif doc.get("kind") in ("StatefulSet", "Deployment"):
                for c in doc["spec"]["template"]["spec"]["containers"]:
                    requests = (c.get("resources") or {}).get("requests") or {}
                    if requests.get("cpu"):
                        total_cpu += _cpu(requests["cpu"])
                    if requests.get("memory"):
                        total_mem += _mem_gi(requests["memory"])
    assert 0 < total_cpu <= COMMERCE_CPU_CEILING, (
        f"the money layer asks for {total_cpu:.2f} cores, ceiling {COMMERCE_CPU_CEILING}"
    )
    assert 0 < total_mem <= COMMERCE_MEMORY_CEILING_GI, (
        f"the money layer asks for {total_mem:.2f} Gi, ceiling {COMMERCE_MEMORY_CEILING_GI}"
    )
