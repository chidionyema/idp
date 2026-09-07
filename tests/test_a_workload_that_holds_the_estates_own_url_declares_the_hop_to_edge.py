"""A pod that names the estate's own public URL is talking to the estate, not the internet.

The front-door heartbeat in the identity namespace curled https://catalogue.<zone>/ every five
minutes and timed out at 20s, while in the same container and the same run an upload to OCI object
storage over 443 succeeded (job front-door-heartbeat-29813565-npblb, 2026-09-07T20:45:02Z). Both
angles point at one mechanism: catalogue.<zone> resolves to 193.123.184.22, which is the estate's
own traefik LoadBalancer, and a LoadBalancer address is programmed into every node -- so the packet
never leaves for the load balancer. It is delivered to a traefik pod on the cluster network at
10.244.x.x and judged as ordinary pod-to-pod egress. allow-internet-egress excludes 10.0.0.0/8 by
design, and identity declared no egress reaching edge, so the fence dropped it.

The rule this test carries is capability, not intent: if a workload holds one of the estate's own
public URLs in its config, it is one code path away from dialling it, and the fence must already
permit the hop or the failure is a twenty-second silence nothing reports. A namespace is exempt
only for the hostnames its own HTTPRoutes serve -- that is a workload naming itself.
"""

import os
import re
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "platform")
ALLOWANCES = os.path.join(PLATFORM, "ns-fences", "allowances.yaml")

# The zone is one value in clusters/*/estate-config.yaml (LAW 46), so a manifest carries the
# placeholder Flux substitutes and this is what a public estate URL looks like on disk.
ESTATE_URL = re.compile(r"https?://([a-z0-9.-]*\$\{ESTATE_ZONE\})")

# Traefik is the one front door; reaching any estate hostname from inside means reaching it.
DOOR = "edge"


def _docs():
    for dirpath, _, filenames in os.walk(PLATFORM):
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
    for _, doc in _docs():
        if doc.get("kind") != "HTTPRoute":
            continue
        namespace = _namespace(doc)
        for hostname in (doc.get("spec") or {}).get("hostnames") or []:
            owners.setdefault(hostname, set()).add(namespace)
    return owners


def _dials():
    """namespace -> {hostname: file} for every estate URL that is not the namespace's own."""
    owners = _served_by()
    found = {}
    for path, doc in _docs():
        namespace = _namespace(doc)
        if not namespace:
            continue  # nothing with no namespace is behind a namespace fence
        for text in _strings(doc):
            for hostname in ESTATE_URL.findall(text):
                if namespace in owners.get(hostname, set()):
                    continue  # a workload naming its own front door
                found.setdefault(namespace, {}).setdefault(hostname, path)
    return found


def _flows():
    return yaml.safe_load(open(ALLOWANCES, encoding="utf-8"))["flows"]


def test_every_namespace_holding_an_estate_url_may_leave_for_the_front_door():
    flows = _flows()
    cut = []
    for namespace, hostnames in sorted(_dials().items()):
        if DOOR in (flows.get(namespace, {}).get("egress") or []):
            continue
        hostname, path = sorted(hostnames.items())[0]
        cut.append(
            f"{namespace} holds {hostname} ({path}) and declares no egress to {DOOR}"
        )
    assert not cut, "\n".join(cut)


def test_the_front_door_admits_every_namespace_that_may_leave_for_it():
    """A one-sided flow is a deny: Calico needs both the egress rule and the ingress rule."""
    flows = _flows()
    admitted = flows[DOOR].get("ingress_from") or []
    missing = [
        namespace
        for namespace in sorted(_dials())
        if DOOR in (flows.get(namespace, {}).get("egress") or [])
        and namespace not in admitted
    ]
    assert not missing, f"{DOOR} does not admit {missing}"


def test_a_workload_naming_only_its_own_hostname_is_not_called_a_dialler():
    """Without this, every service that knows its own public URL would be told to open a fence."""
    dials = _dials()
    # llm's PROXY_BASE_URL is llm.<zone>, which llm's own HTTPRoute serves.
    assert "llm" not in dials or "llm.${ESTATE_ZONE}" not in dials["llm"]


def test_the_heartbeat_that_measured_this_is_still_the_case_the_rule_covers():
    """The defect this rule was written from: identity curling catalogue.<zone>."""
    assert "catalogue.${ESTATE_ZONE}" in _dials().get("identity", {})
