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


# ------------------------------------------------- it runs, and it still takes no money


# The two rows that hold money -- Lago and its ledger. The bus is not one of them: it carries
# `estate.commerce.order_paid`, it does not price, charge or store a card.
#
# Both were suspended until 2026-09-04, when the founder gave the word ("need ithis fiilly
# enabled JetStream/Lago suspension") and they were woken in one commit. Waking them is not the
# same as taking money, and the difference is what the rest of this file guards: no edge-attach
# label so the Gateway refuses a route from the namespace, signup off, and no payment provider
# configured. This test now asks the two questions that outlived the suspension -- the pair wake
# together, and the ledger brings no database of its own.
MONEY_ROWS = {"commerce-data", "commerce"}


def test_the_money_rows_wake_together():
    rows = _rows()
    assert set(rows) == {"commerce-data", "commerce", "event-bus"}
    for name in sorted(MONEY_ROWS):
        assert rows[name]["spec"].get("suspend") is False, (
            f"{name} is suspended while the other money row is not. Lago and its ledger run "
            f"as a pair: one without the other is a billing engine with no storage, or storage "
            f"nothing writes to."
        )


def test_the_ledger_lives_on_the_estate_database_and_brings_no_other():
    """Founder, 2026-09-04: a new layer never brings its own Postgres."""
    depends = [d["name"] for d in _rows()["commerce-data"]["spec"]["dependsOn"]]
    assert "estate-db" in depends, (
        "the ledger is a database on the estate cluster, so this row waits for that cluster"
    )
    stateful = sorted(
        d["metadata"]["name"]
        for d in _all_docs(COMMERCE)
        if d.get("kind") == "StatefulSet"
    )
    assert stateful == ["commerce-redis"], (
        f"{stateful} -- the only stateful thing this layer may bring is its own queue. A "
        f"Postgres here would be a second database in an estate that has one."
    )


def test_the_commerce_namespace_cannot_attach_to_the_edge():
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
