"""An exception that names no workload is not an exception, it is a weaker baseline.

Founder order, 2026-09-02 (~/.claude/docs/founder/2026-09-02T1350Z...a466b5d4.md and
...1351Z...4f516e6d.md): a surgical exception scoped to the exact workloads, never a weaker
baseline. Kyverno will happily take a PolicyException whose match names a namespace and nothing
else -- every pod in that namespace then skips the policy, including pods written later by
someone who never read the waiver. Each file's prose says its scope is locked; this grades it.

Written from the Tailscale ingress proxy for the JIT broker (operator log 2026-09-07T23:36:04Z,
StatefulSet/tailscale/ts-jit-broker-85shp denied by nine policies), which needed the twentieth
exception in this tree and made it worth grading the shape of all of them at once.

What is graded is the built output, not the files. Every exception directory is run through
`kubectl kustomize`, which is what Flux applies, so a waiver sitting in the tree unreferenced by
its kustomization never reaches this test at all -- and a waiver that does reach it is one the
cluster really holds.
"""

import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "platform")


def _kustomize_dirs():
    """Every directory Flux builds that ships a PolicyException file."""
    dirs = set()
    for dirpath, _, filenames in os.walk(PLATFORM):
        if "kustomization.yaml" not in filenames:
            continue
        for filename in filenames:
            if not filename.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(dirpath, filename), encoding="utf-8") as handle:
                if "kind: PolicyException" in handle.read():
                    dirs.add(dirpath)
                    break
    return sorted(dirs)


def _built():
    """The PolicyException objects `kubectl kustomize` actually produces."""
    found = []
    for directory in _kustomize_dirs():
        built = subprocess.run(
            ["kubectl", "kustomize", directory],
            capture_output=True,
            text=True,
            check=False,
        )
        assert built.returncode == 0, f"{directory}: {built.stderr}"
        for doc in yaml.safe_load_all(built.stdout):
            if isinstance(doc, dict) and doc.get("kind") == "PolicyException":
                found.append((os.path.relpath(directory, ROOT), doc))
    return found


def _matches(doc):
    match = (doc.get("spec") or {}).get("match") or {}
    for key in ("any", "all"):
        for entry in match.get(key) or []:
            yield entry.get("resources") or {}


BUILT = None


def _exceptions():
    global BUILT
    if BUILT is None:
        BUILT = _built()
    return BUILT


def test_the_cluster_holds_exceptions_to_grade():
    """A guard that silently matches nothing is decoration."""
    assert _exceptions(), "kubectl kustomize built no PolicyException under platform/"


def test_every_exception_in_the_tree_is_one_the_cluster_holds():
    """A waiver no kustomization builds does not apply, and its prose says otherwise."""
    on_disk = set()
    for dirpath, _, filenames in os.walk(PLATFORM):
        for filename in filenames:
            if not filename.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, encoding="utf-8") as handle:
                try:
                    loaded = list(yaml.safe_load_all(handle))
                except yaml.YAMLError:
                    continue
            for doc in loaded:
                if isinstance(doc, dict) and doc.get("kind") == "PolicyException":
                    on_disk.add(doc["metadata"]["name"])
    unbuilt = on_disk - {doc["metadata"]["name"] for _, doc in _exceptions()}
    assert not unbuilt, f"in the tree but built by nothing: {sorted(unbuilt)}"


def test_no_exception_is_unbounded():
    """Bounded on some axis -- names, namespaces or a label -- or it excuses the estate."""
    loose = []
    for path, doc in _exceptions():
        for resources in _matches(doc):
            bounded = (
                resources.get("names")
                or resources.get("namespaces")
                or resources.get("selector")
                or resources.get("namespaceSelector")
            )
            if not bounded:
                loose.append(
                    f"{doc['metadata']['name']} ({path}) bounds nothing: {resources}"
                )
            elif any(n.strip() in ("*", "?*") for n in resources.get("names") or []):
                loose.append(f"{doc['metadata']['name']} ({path}) names the wildcard")
    assert not loose, "\n".join(loose)


# The nine restricted pod-security policies. Waiving one lets a pod run privileged, as root, with
# a writable root filesystem -- so the founder's order applies to these in full: a surgical
# exception scoped to the exact workloads, never a weaker baseline.
POD_SECURITY = {
    "disallow-capabilities-strict",
    "disallow-privilege-escalation",
    "disallow-privileged-containers",
    "drop-all-capabilities",
    "require-ro-rootfs",
    "require-run-as-nonroot",
    "restrict-seccomp-strict",
    "require-pod-probes",
    "require-requests-limits",
}

# The waivers that were already namespace-wide when this rule was written, 2026-09-07. The first
# three are a vendor's own system namespace, which is why each was written that way and why none
# is deleted blind; each is still a pod excused for where it sits rather than what it is. The
# fourth is a different reason: dagster's k8sRunLauncher launches a Job per run under a name it
# mints at runtime, so there is no pattern to name -- the fix there is upstream, not here.
# This ledger only ever shrinks: a new namespace-wide pod-security waiver fails the test below,
# and removing a name from here is the fix, never adding one.
STILL_NAMESPACE_WIDE = {
    "calico-is-the-network",
    "spire",
    "chaos-mesh",
    "dagster-password-from-secret",
}


def test_a_pod_security_waiver_names_the_workloads_it_excuses():
    loose = []
    for path, doc in _exceptions():
        name = doc["metadata"]["name"]
        if name in STILL_NAMESPACE_WIDE:
            continue
        waived = {
            entry.get("policyName")
            for entry in (doc.get("spec") or {}).get("exceptions") or []
        }
        if not waived & POD_SECURITY:
            continue
        for resources in _matches(doc):
            if not (resources.get("names") or resources.get("selector")):
                loose.append(
                    f"{name} ({path}) waives {sorted(waived & POD_SECURITY)} "
                    f"for every pod in {resources.get('namespaces')}"
                )
    assert not loose, "\n".join(loose)


def test_the_ledger_of_namespace_wide_waivers_only_shrinks():
    """A name in the ledger the cluster no longer holds is a row to delete, not to keep."""
    present = {doc["metadata"]["name"] for _, doc in _exceptions()}
    stale = STILL_NAMESPACE_WIDE - present
    assert not stale, f"ledger names exceptions that no longer exist: {sorted(stale)}"


def test_every_exception_names_the_rules_it_excuses():
    """policyName with no ruleNames waives every rule the policy will ever grow."""
    loose = [
        f"{doc['metadata']['name']} -> {entry.get('policyName')} ({path})"
        for path, doc in _exceptions()
        for entry in (doc.get("spec") or {}).get("exceptions") or []
        if not (entry.get("ruleNames") or [])
    ]
    assert not loose, "\n".join(loose)


def test_the_brokers_proxy_is_excused_and_nothing_else_in_that_namespace_is():
    """The waiver this rule was written beside, and the piggyback it must not allow."""
    scopes = [
        resources
        for _, doc in _exceptions()
        if doc["metadata"]["name"] == "tailscale-ingress-proxies"
        for resources in _matches(doc)
    ]
    assert scopes, "tailscale-ingress-proxies is not built"
    for resources in scopes:
        assert resources.get("namespaces") == ["tailscale"]
        assert resources.get("names") == ["ts-jit-broker*"]
