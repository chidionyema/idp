"""A pod that names the estate's own public URL is talking to the estate, not the internet.

The front-door heartbeat in the identity namespace curled https://catalogue.<zone>/ every five
minutes and timed out at 20s, while in the same container and the same run an upload to OCI object
storage over 443 succeeded (job front-door-heartbeat-29813565-npblb, 2026-09-07T20:45:02Z). Both
angles point at one mechanism: catalogue.<zone> resolves to 193.123.184.22, which is the estate's
own traefik LoadBalancer, and a LoadBalancer address is programmed into every node -- so the packet
never leaves for the load balancer. It is delivered to a traefik pod on the cluster network at
10.244.x.x and judged as ordinary pod-to-pod egress. allow-internet-egress excludes 10.0.0.0/8 by
design, and identity's rendered policies opened no route to edge, so the fence dropped it.

The rule is capability, not intent: if a workload holds one of the estate's own public URLs, it is
one code path away from dialling it, and the failure is a twenty-second silence nothing reports. A
namespace is exempt only for the hostnames its own HTTPRoutes serve -- that is a workload naming
itself.

What is graded is the NetworkPolicy the cluster enforces, not the sentence that asked for it. This
runs bin/idp-ns-fence-gen, proves the rendered policies under platform/ns-fences/network are what
the declaration produces, and then walks those policies the way Calico does: a hop is open when an
egress rule in the source namespace selects the destination namespace AND an ingress rule in the
destination selects the source. One side alone is a deny.
"""

import os
import re
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "platform")
RENDERED = os.path.join(PLATFORM, "ns-fences", "network")

# The zone is one value in clusters/*/estate-config.yaml (LAW 46), so a manifest carries the
# placeholder Flux substitutes and this is what a public estate URL looks like on disk.
ESTATE_URL = re.compile(r"https?://([a-z0-9.-]*\$\{ESTATE_ZONE\})")

# Traefik is the one front door; reaching any estate hostname from inside means reaching it.
DOOR = "edge"

NAMESPACE_LABEL = "kubernetes.io/metadata.name"


def _run(*argv):
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)


def _docs(directory):
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if not filename.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, encoding="utf-8") as handle:
                try:
                    loaded = list(yaml.safe_load_all(handle))
                except yaml.YAMLError:
                    continue  # templates and Helm values are not ours to parse
            for doc in loaded:
                if isinstance(doc, dict):
                    yield os.path.relpath(path, ROOT), doc


def _namespace(doc):
    named = (doc.get("metadata") or {}).get("namespace")
    if named:
        return named
    # A kustomization stamps its namespace onto everything it builds.
    if doc.get("kind") == "Kustomization":
        return doc.get("namespace")
    return None


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _served_by():
    """hostname -> the namespaces whose HTTPRoutes answer for it."""
    owners = {}
    for _, doc in _docs(PLATFORM):
        if doc.get("kind") != "HTTPRoute":
            continue
        for hostname in (doc.get("spec") or {}).get("hostnames") or []:
            owners.setdefault(hostname, set()).add(_namespace(doc))
    return owners


def _dials():
    """namespace -> {hostname: file} for every estate URL that is not the namespace's own."""
    owners = _served_by()
    found = {}
    for path, doc in _docs(PLATFORM):
        namespace = _namespace(doc)
        if not namespace:
            continue  # nothing with no namespace is behind a namespace fence
        for text in _strings(doc):
            for hostname in ESTATE_URL.findall(text):
                if namespace in owners.get(hostname, set()):
                    continue  # a workload naming its own front door
                found.setdefault(namespace, {}).setdefault(hostname, path)
    return found


def _policies():
    """The NetworkPolicy objects the cluster enforces, keyed by namespace."""
    by_namespace = {}
    for _, doc in _docs(RENDERED):
        if doc.get("kind") == "NetworkPolicy":
            by_namespace.setdefault(_namespace(doc), []).append(doc)
    return by_namespace


def _selects(peers, namespace):
    """Would this rule's `to`/`from` list match a pod in `namespace`?"""
    for peer in peers or []:
        selector = peer.get("namespaceSelector")
        if selector is None:
            continue  # a podSelector alone means the policy's own namespace
        labels = selector.get("matchLabels") or {}
        if labels.get(NAMESPACE_LABEL) == namespace:
            return True
    return False


def _hop_is_open(policies, source, destination):
    """Calico's arithmetic: both sides must select the other, or the packet is dropped."""
    leaves = any(
        _selects(rule.get("to"), destination)
        for policy in policies.get(source, [])
        for rule in (policy.get("spec") or {}).get("egress") or []
    )
    arrives = any(
        _selects(rule.get("from"), source)
        for policy in policies.get(destination, [])
        for rule in (policy.get("spec") or {}).get("ingress") or []
    )
    return leaves, arrives


def test_the_rendered_fences_are_what_the_declaration_produces():
    """A hand-edited policy under network/ is a fence the next generator run silently reverts."""
    generated = _run(sys.executable, os.path.join("bin", "idp-ns-fence-gen"))
    assert generated.returncode == 0, generated.stdout + generated.stderr
    clean = _run("git", "diff", "--quiet", "--", os.path.join("platform", "ns-fences"))
    assert clean.returncode == 0, (
        "bin/idp-ns-fence-gen changed the rendered policies; commit the regenerated files:\n"
        + _run(
            "git", "diff", "--stat", "--", os.path.join("platform", "ns-fences")
        ).stdout
    )


def test_every_namespace_holding_an_estate_url_can_reach_the_front_door():
    policies = _policies()
    cut = []
    for namespace, hostnames in sorted(_dials().items()):
        if namespace not in policies:
            continue  # not fenced yet; idp-ns-fence-gen lists those separately
        leaves, arrives = _hop_is_open(policies, namespace, DOOR)
        if leaves and arrives:
            continue
        hostname, path = sorted(hostnames.items())[0]
        side = (
            "no egress rule reaches edge"
            if not leaves
            else "edge admits nobody from it"
        )
        cut.append(f"{namespace} holds {hostname} ({path}) and {side}")
    assert not cut, "\n".join(cut)


def test_the_evaluator_reads_a_closed_hop_as_closed():
    """Without this the check above passes by seeing nothing rather than by seeing a route."""
    policies = _policies()
    leaves, arrives = _hop_is_open(
        policies, "identity", "a-namespace-that-does-not-exist"
    )
    assert not leaves and not arrives


def test_a_workload_naming_only_its_own_hostname_is_not_called_a_dialler():
    """Without this, every service that knows its own public URL would be told to open a fence."""
    dials = _dials()
    # llm's PROXY_BASE_URL is llm.<zone>, which llm's own HTTPRoute serves.
    assert "llm" not in dials or "llm.${ESTATE_ZONE}" not in dials["llm"]


def test_the_heartbeat_that_measured_this_is_still_the_case_the_rule_covers():
    """The defect this rule was written from: identity curling catalogue.<zone>."""
    assert "catalogue.${ESTATE_ZONE}" in _dials().get("identity", {})
