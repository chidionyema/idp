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

# The one collector every workload emits to (LAW 50). idp-ns-fence-gen grants every namespace
# egress to it whether the namespace asked or not, which is the whole of the law on the egress
# side and none of it on the ingress side -- see the SINK block in that file.
COLLECTOR = "observability"

# A cluster-internal address as a manifest spells it: service.namespace.svc[.cluster.local].
SERVICE_ADDRESS = re.compile(
    r"\b([a-z0-9][a-z0-9-]*)\.([a-z0-9][a-z0-9-]*)\.svc(?:\.cluster\.local)?\b"
)

# Kinds that name an address without being the thing that dials it.
#   Job          -- a one-shot migration that has already run is not a standing dialler; its pod
#                   is gone and will not be recreated, so declaring a hop for it would open a
#                   door for nobody. A CronJob is the opposite case and is graded.
#   Middleware   -- a Traefik middleware describes what the gateway does with a request. The pod
#                   that dials a forwardAuth address is traefik, in the edge namespace, not
#                   anything in the namespace the middleware object happens to live in.
NAMES_BUT_DOES_NOT_DIAL = {"Job", "Middleware"}


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


def _service_dials(fenced):
    """namespace -> {(destination, service): file} for every cross-namespace address it holds.

    This is the general form of the rule at the top of this file. The front door was one
    hostname; a Service address is the same capability spelled the other way, and the same
    twenty-second silence when the fence says no.
    """
    found = {}
    for path, doc in _docs(PLATFORM):
        if doc.get("kind") in NAMES_BUT_DOES_NOT_DIAL:
            continue
        source = _namespace(doc)
        if source not in fenced:
            continue
        for text in _strings(doc):
            for service, destination in SERVICE_ADDRESS.findall(text):
                if destination == source or destination not in fenced:
                    continue
                found.setdefault(source, {}).setdefault((destination, service), path)
    return found


def test_every_fenced_namespace_can_reach_the_one_collector():
    """LAW 50's grant was one-sided until 2026-09-08, so the law generated its own outage.

    policy_docs() appends the collector to every namespace's egress -- and until this was fixed
    gave the collector no matching ingress, so observability's allow-declared-ingress admitted
    edge and monitoring and nobody else. Both namespaces are default-deny in both directions, so
    every other namespace's traces were dropped at the collector's door. Silently: an OTLP
    exporter drops what it cannot deliver and the workload goes on serving.
    """
    policies = _policies()
    closed = []
    for namespace in sorted(policies):
        if namespace == COLLECTOR:
            continue
        leaves, arrives = _hop_is_open(policies, namespace, COLLECTOR)
        if not (leaves and arrives):
            closed.append(
                f"{namespace} -> {COLLECTOR}: egress={leaves} ingress={arrives}"
            )
    assert not closed, (
        "LAW 50 says every workload emits to the one collector, and these namespaces cannot:\n"
        + "\n".join(closed)
    )


def test_every_live_workload_that_dials_another_namespace_declares_the_hop():
    """The pre-flight for the roll onto the enforcing CNI.

    A fence gap is invisible while the two pods are still wired by flannel and becomes a drop the
    moment either is recreated onto Calico. On 2026-09-08 the estate was half rolled -- 96 pods on
    flannel, 39 on Calico -- so every undeclared hop here is an outage with a date on it rather
    than a hypothetical. Finding them by reading the manifests costs nothing; finding them by
    restarting a pod costs whatever that pod does.
    """
    policies = _policies()
    fenced = set(policies)
    assert len(fenced) > 20, (
        f"only {len(fenced)} fenced namespaces rendered; the walk found nothing"
    )
    closed = []
    for source, hops in sorted(_service_dials(fenced).items()):
        for (destination, service), path in sorted(hops.items()):
            leaves, arrives = _hop_is_open(policies, source, destination)
            if not (leaves and arrives):
                closed.append(
                    f"{source} -> {destination} ({service}, {path}): "
                    f"egress={leaves} ingress={arrives}"
                )
    assert not closed, (
        "these workloads dial across a fence that does not declare the hop; each is a drop on "
        "the day its pod lands on Calico:\n" + "\n".join(closed)
    )


def test_the_scan_reads_the_addresses_it_claims_to_read():
    """A walk that matched nothing would pass the rule above without grading anything."""
    fenced = set(_policies())
    dials = _service_dials(fenced)
    assert len(dials) >= 10, (
        f"only {len(dials)} namespaces found dialling; the regex missed"
    )
    assert ("llm", "litellm") in dials.get("research", {}), (
        "the research engine's LITELLM_BASE_URL is the hop this scan was built from and it is "
        "not in the result"
    )


# A host the pod dials itself. An image reference is not one of these: the kubelet pulls images on
# the node, over the node's own network, where no pod policy applies.
EXTERNAL_HOST = re.compile(r"(?:https://|oci://)([a-z0-9.-]+\.[a-z]{2,})")
INTERNAL_HOST = re.compile(r"\.svc\b|\$\{ESTATE_ZONE\}|localhost|127\.0\.0\.1")

INTERNET_EGRESS = "allow-internet-egress"


def _pod_spec(doc):
    spec = doc.get("spec") or {}
    template = (spec.get("template") or {}).get("spec")
    if template:
        return template
    job = ((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}
    return job.get("spec") or {}


def test_every_pod_that_dials_the_internet_sits_behind_a_fence_that_allows_it():
    """An image pull is the node's traffic; a container running curl is the pod's.

    Measured 2026-09-08T00:39Z: pod estate-mcp-6cb8dd5b87-8gnpt was created onto Calico and sat in
    CrashLoopBackOff on its `fetch-estate-db` init container, whose whole command is
    `flux pull artifact oci://ghcr.io/chidionyema/idp/estate-db`. Its one log line was "pulling
    artifact from ghcr.io/chidionyema/idp/estate-db:latest" and then nothing. The mcp fence
    rendered no allow-internet-egress at all, so the pull had nowhere to go.

    This is a different gap from the cross-namespace one above and was missed by that scan
    entirely: the destination is not a namespace, so no declaration between two rows could ever
    have covered it.
    """
    open_to_internet = {
        namespace
        for namespace, docs in _policies().items()
        if any(d["metadata"]["name"] == INTERNET_EGRESS for d in docs)
    }
    fenced = set(_policies())
    closed = []
    for path, doc in _docs(PLATFORM):
        namespace = _namespace(doc)
        if namespace not in fenced or namespace in open_to_internet:
            continue
        pod = _pod_spec(doc)
        for container in (pod.get("initContainers") or []) + (
            pod.get("containers") or []
        ):
            words = list(container.get("command") or []) + list(
                container.get("args") or []
            )
            words += [e.get("value", "") for e in container.get("env") or []]
            for host in EXTERNAL_HOST.findall(" ".join(str(w) for w in words)):
                if INTERNAL_HOST.search(host):
                    continue
                closed.append(f"{namespace}/{container['name']} dials {host} ({path})")
    assert not closed, (
        "these containers dial the public internet from inside a fence that renders no "
        + INTERNET_EGRESS
        + ":\n"
        + "\n".join(sorted(set(closed)))
    )
