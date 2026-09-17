"""BDD bindings for features/gates/egress-block.feature.

Tests the Calico manifests at platform/calico/raw/deny-direct-ai-vendor-egress.yaml.
No cluster access required — all assertions are on the manifest text.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/egress-block.feature")

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "platform" / "calico" / "raw" / "deny-direct-ai-vendor-egress.yaml"


def _docs():
    return list(yaml.safe_load_all(MANIFEST.read_text()))


def _network_set(docs):
    return next(d for d in docs if d["kind"] == "GlobalNetworkSet")


def _policy(docs):
    return next(d for d in docs if d["kind"] == "GlobalNetworkPolicy")


@pytest.fixture
def state():
    return {}


# Background -------------------------------------------------------------------

@given("the Calico GlobalNetworkPolicy manifest exists at platform/calico/raw/deny-direct-ai-vendor-egress.yaml")
def _manifest_exists(state):
    assert MANIFEST.exists(), f"manifest not found: {MANIFEST}"
    state["docs"] = _docs()


@given("the GlobalNetworkSet manifest exists in the same file")
def _network_set_exists(state):
    kinds = {d["kind"] for d in state["docs"]}
    assert "GlobalNetworkSet" in kinds


# Scenario: policy name and order ----------------------------------------------

@when("the policy manifest is parsed")
def _parse_policy(state):
    state["policy"] = _policy(state["docs"])


@then("the GlobalNetworkPolicy name is \"deny-direct-ai-vendor-egress\"")
def _policy_name(state):
    assert state["policy"]["metadata"]["name"] == "deny-direct-ai-vendor-egress"


@then(parsers.parse("the policy order is {order:d}"))
def _policy_order(state, order):
    assert state["policy"]["spec"]["order"] == order


@then("the policy type includes \"Egress\"")
def _policy_egress_type(state):
    assert "Egress" in state["policy"]["spec"]["types"]


# Scenario: vendor domains -----------------------------------------------------

@when("the GlobalNetworkSet manifest is parsed")
def _parse_network_set(state):
    state["ns"] = _network_set(state["docs"])


@then(parsers.parse('the allowedEgressDomains includes "{domain}"'))
def _domain_present(state, domain):
    domains = state["ns"]["spec"]["allowedEgressDomains"]
    assert domain in domains, f"{domain!r} not in {domains}"


@then(parsers.parse('the GlobalNetworkSet label "{key}" is "{value}"'))
def _ns_label(state, key, value):
    assert state["ns"]["metadata"]["labels"][key] == value


# Scenario: namespace exemptions -----------------------------------------------

@when("the namespaceSelector is parsed from the GlobalNetworkPolicy")
def _parse_ns_selector(state):
    docs = state.get("docs") or _docs()
    state["selector"] = _policy(docs)["spec"]["namespaceSelector"]


@then("the selector uses \"not in\" logic")
def _selector_not_in(state):
    assert "not in" in state["selector"]


@then(parsers.parse('"{ns}" is in the exempt namespaces'))
def _ns_exempt(state, ns):
    assert ns in state["selector"]


@then(parsers.parse("exactly {count:d} namespaces are exempt"))
def _exempt_count(state, count):
    import re
    found = re.findall(r"'([^']+)'", state["selector"])
    assert len(found) == count, f"found {len(found)} exempt namespaces: {found}"


# Scenario: egress rule --------------------------------------------------------

@when("the egress rules are parsed")
def _parse_egress_rules(state):
    docs = state.get("docs") or _docs()
    state["egress"] = _policy(docs)["spec"]["egress"]


@then("there is exactly 1 egress rule")
def _one_egress_rule(state):
    assert len(state["egress"]) == 1


@then(parsers.parse('the egress action is "{action}"'))
def _egress_action(state, action):
    assert state["egress"][0]["action"] == action


@then(parsers.parse('the egress protocol is "{protocol}"'))
def _egress_protocol(state, protocol):
    assert state["egress"][0]["protocol"] == protocol


@then(parsers.parse("the destination selector references '{selector}'"))
def _egress_dest_selector(state, selector):
    assert state["egress"][0]["destination"]["selector"] == selector


@then(parsers.parse("the destination port is {port:d}"))
def _egress_port(state, port):
    ports = state["egress"][0].get("ports") or state["egress"][0]["destination"].get("ports", [])
    assert port in ports


# Scenario Outline: non-exempt namespace ---------------------------------------

EXEMPT = {"llm", "kube-system", "flux-system", "kube-public", "kube-node-lease"}


@when(parsers.parse('checking namespace "{namespace}"'))
def _check_namespace(state, namespace):
    state["checked_ns"] = namespace


@then("the namespace is not in the exempt list")
def _ns_not_exempt(state):
    assert state["checked_ns"] not in EXEMPT


@then("a pod in that namespace would be subject to the deny rule")
def _subject_to_deny(state):
    # Structural: if not exempt and policy selector is "all()" pods are subject
    docs = _docs()
    policy = _policy(docs)
    assert policy["spec"]["selector"] == "all()"


# Scenario: manifest validity --------------------------------------------------

@when("the manifest file is read")
def _read_manifest(state):
    state["raw"] = MANIFEST.read_text()
    state["docs2"] = list(yaml.safe_load_all(state["raw"]))


@then("it parses as valid YAML")
def _valid_yaml(state):
    assert state["docs2"] is not None


@then("it contains exactly 2 documents")
def _two_docs(state):
    non_none = [d for d in state["docs2"] if d is not None]
    assert len(non_none) == 2


@then(parsers.parse('the first document kind is "{kind}"'))
def _first_kind(state, kind):
    non_none = [d for d in state["docs2"] if d is not None]
    assert non_none[0]["kind"] == kind


@then(parsers.parse('the second document kind is "{kind}"'))
def _second_kind(state, kind):
    non_none = [d for d in state["docs2"] if d is not None]
    assert non_none[1]["kind"] == kind
