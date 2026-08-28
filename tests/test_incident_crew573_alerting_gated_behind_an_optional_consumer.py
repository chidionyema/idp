"""Incident 2026-08-28 (crew#573): the estate had no Prometheus, no Alertmanager and no
kube-state-metrics, and nobody knew, because Kustomization `monitoring` carried
`dependsOn: [edge, secret-store, robusta]`. Robusta's HelmRelease went `Failed` on an unrelated
fault (idp#593), so `monitoring` never became Ready, so `monitoring-rules` and `chaos` never did
either — 4 of the 6 not-Ready Flux objects in oke-check run 33172282641. `KubePodCrashLooping`
and `KubePodNotReady` are declared by this repo (`defaultRules.create: true`, `kubernetesApps`
not disabled) and had never once fired; `hindsight-api` crash-looped 13 hours at 0/1 ready with
nothing red anywhere in the estate.

The class of mistake is not "robusta was in a list". It is: **something that only the alerting
stack needs was placed upstream of the alerting stack**, so one optional row can blind the whole
estate and the blindness is itself unalerted. The rule below is measured off the dependency graph
rather than a hand-kept allow-list, because an allow-list has a silent miss case and this one
would have to be remembered by whoever adds the next row:

    every row the alerting stack depends on, transitively, must also be depended on by at least
    one row that is not the alerting stack.

A genuine prerequisite always passes it — on the tree that fixed this incident, `edge` had 5 such
dependents and `secret-store` had 13. A row that only the alerting stack needs is, by definition,
a consumer of alerting or an add-on beside it, and it can never be a reason for alerting not to
exist. There is no threshold to tune and nothing to keep in sync by hand.

The second test holds the other door. The dependency bought nothing even while robusta was
healthy: Alertmanager routes `receiver: telegram` by default and copies warnings to robusta on a
route carrying `continue: true`. A webhook receiver whose service is absent costs one retried
notification, not the delivery path. Make robusta the *default* receiver, though, and the same
blindness returns without any `dependsOn` being touched — so the catch-all receiver is graded too.
"""
import collections
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLUSTERS = sorted(ROOT.glob("clusters/*/platform.yaml"))
ALERTMANAGER = ROOT / "platform" / "monitoring" / "alertmanager-config.yaml"

#: The rows that are the estate's eyes. `monitoring` is the chart (Prometheus, Alertmanager,
#: kube-state-metrics); `monitoring-rules` is the PrometheusRules and the founder-surface Probe,
#: split out because a chart and its own CRs in one row never reconcile (incident 2026-08-25).
ALERTING = frozenset({"monitoring", "monitoring-rules"})


def _graph():
    """dependsOn edges over every cluster's Kustomizations, forward and reverse."""
    forward, reverse = {}, collections.defaultdict(set)
    for path in CLUSTERS:
        for doc in yaml.safe_load_all(path.read_text()):
            if not isinstance(doc, dict) or doc.get("kind") != "Kustomization":
                continue
            name = doc["metadata"]["name"]
            forward[name] = [d["name"] for d in (doc.get("spec", {}).get("dependsOn") or [])]
            for dependency in forward[name]:
                reverse[dependency].add(name)
    return forward, reverse


def _closure(forward, roots):
    """Everything `roots` needs, transitively, minus the roots themselves."""
    seen, stack = set(), list(roots)
    while stack:
        for dependency in forward.get(stack.pop(), []):
            if dependency not in seen:
                seen.add(dependency)
                stack.append(dependency)
    return seen - set(roots)


def test_the_graph_is_actually_read():
    """Anti-vacuous. A parser that silently found nothing would pass every assertion below."""
    forward, _ = _graph()
    assert CLUSTERS, "no clusters/*/platform.yaml found; the guard is grading an empty set"
    assert len(forward) >= 20, f"only {len(forward)} Kustomizations parsed; the parser is broken"
    missing = ALERTING - set(forward)
    assert not missing, f"the alerting rows this guard exists for are absent: {sorted(missing)}"


def test_the_alerting_stack_depends_on_nothing_only_it_needs():
    """The rule. A row upstream of the estate's eyes must be a real prerequisite, and the graph
    is what says so: something other than the alerting stack has to need it too."""
    forward, reverse = _graph()
    orphans = {}
    for row in sorted(_closure(forward, ALERTING)):
        outside = reverse[row] - ALERTING
        if not outside:
            orphans[row] = sorted(reverse[row])
    assert not orphans, (
        "these rows gate the alerting stack and nothing outside it depends on them, so a fault "
        "in any of them leaves the estate with no Prometheus and no Alertmanager and nothing to "
        f"say so (crew#573): {orphans}"
    )


def test_a_pager_that_is_always_reachable_is_the_catch_all_receiver():
    """The other door: robusta as the *default* receiver reintroduces the blindness with the
    dependency graph left clean."""
    raw = ALERTMANAGER.read_text()
    doc = next(
        d for d in yaml.safe_load_all(raw)
        if isinstance(d, dict) and d.get("kind") == "ExternalSecret"
        and "alertmanager.yaml" in yaml.safe_dump(d.get("spec", {}).get("target", {}).get("template", {}))
    )
    embedded = doc["spec"]["target"]["template"]["data"]["alertmanager.yaml"]
    # The embedded config is a Go template resolved by external-secrets (`{{ .token }}`), and an
    # unquoted `{{ ... }}` is not loadable YAML — it opens a flow mapping. Substituting a scalar
    # changes no structure the assertions below read.
    config = yaml.safe_load(re.sub(r"\{\{.*?\}\}", "TEMPLATED", embedded))

    route = config["route"]
    assert route["receiver"] != "robusta", (
        "the catch-all Alertmanager receiver is robusta; when the robusta row is down every alert "
        "in the estate goes nowhere, which is crew#573 by a different door"
    )
    for sub in route.get("routes", []):
        if sub.get("receiver") == "robusta":
            assert sub.get("continue") is True, (
                "the robusta route swallows alerts instead of copying them: without "
                "`continue: true` a matching alert stops here and never reaches the catch-all"
            )
