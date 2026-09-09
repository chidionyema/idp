"""The scheduler had no reason to prefer the thing that takes money.

On 2026-09-09 the cross-node link was severed, the ingress path was pinned to one node, and that
node had 32m of CPU free. prospector-store-api asks for 100m, so the storefront could not be
seated and mumchimp.com returned 000 to three requests in three. Nothing in the cluster said it
should be seated: observability/langfuse-worker held 1000m as infrastructure-critical while its
own web front end was stranded and unreadable, and prospector ran at priority 0 with no class at
all -- below platform-batch, the nightly jobs.

These grade the ordering, not the wording.
"""

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "platform" / "priority-classes" / "priorityclasses.yaml"
POLICY = ROOT / "platform" / "scheduling" / "revenue-priority.yaml"
NAMESPACE = ROOT / "platform" / "prospector" / "namespace.yaml"
KUSTOMIZATION = ROOT / "platform" / "scheduling" / "kustomization.yaml"


def classes():
    docs = [d for d in yaml.safe_load_all(CLASSES.read_text()) if d]
    return {d["metadata"]["name"]: d for d in docs if d.get("kind") == "PriorityClass"}


def test_revenue_outranks_infrastructure():
    c = classes()
    assert "revenue-critical" in c, "no class for the thing being sold"
    assert c["revenue-critical"]["value"] > c["infrastructure-critical"]["value"], (
        "the trace viewer still outranks the shop"
    )
    assert c["revenue-critical"]["value"] > c["platform-batch"]["value"]


def test_revenue_can_take_a_seat():
    """A class that cannot preempt leaves the shop down on a full node, which is the whole fault."""
    assert classes()["revenue-critical"]["preemptionPolicy"] == "PreemptLowerPriority"


def test_system_classes_are_untouched():
    """Cluster components still win; this is not a licence to outrank the control plane."""
    c = classes()
    assert c["revenue-critical"]["value"] < 2000000000
    assert c["balloon"]["value"] < 0


def test_the_policy_only_fills_an_absence():
    """R38: a guard that refuses correct work is an outage. This mutates, never validates."""
    pol = yaml.safe_load(POLICY.read_text())
    rule = pol["spec"]["rules"][0]
    assert "mutate" in rule and "validate" not in rule
    pre = rule["preconditions"]["all"][0]
    assert pre["operator"] == "Equals" and pre["value"] == "", (
        "an explicit priorityClassName set by a product team must be kept"
    )
    assert (
        rule["mutate"]["patchStrategicMerge"]["spec"]["template"]["spec"][
            "priorityClassName"
        ]
        == "revenue-critical"
    )


def test_the_product_namespace_declares_its_tier():
    """The product's Deployments live in its own repository; the namespace is the seam."""
    ns = [d for d in yaml.safe_load_all(NAMESPACE.read_text()) if d][0]
    assert ns["metadata"]["labels"]["estate.mumchimp.com/tier"] == "revenue"
    pol = yaml.safe_load(POLICY.read_text())
    sel = pol["spec"]["rules"][0]["match"]["any"][0]["resources"]["namespaceSelector"]
    assert sel["matchLabels"] == {"estate.mumchimp.com/tier": "revenue"}, (
        "the policy and the namespace do not agree on the label"
    )


def test_the_policy_is_actually_applied():
    """A policy no Kustomization names is decoration."""
    assert "revenue-priority.yaml" in KUSTOMIZATION.read_text()
