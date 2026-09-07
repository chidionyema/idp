"""An exception that names no workload is not an exception, it is a weaker baseline.

Founder order, 2026-09-02 (~/.claude/docs/founder/2026-09-02T1350Z...a466b5d4.md and
...1351Z...4f516e6d.md): a surgical exception scoped to the exact workloads, never a weaker
baseline. Kyverno will happily take a PolicyException whose match names a namespace and nothing
else -- every pod in that namespace then skips the policy, including pods written later by
someone who never read the waiver. The prose in each file says the scope is locked; this grades
whether it is.

Written from the Tailscale ingress proxy for the JIT broker (operator log 2026-09-07T23:36:04Z,
StatefulSet/tailscale/ts-jit-broker-85shp denied by nine policies), which needed the twentieth
exception in this tree and made it worth grading the shape of all of them at once.
"""

import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "platform")


def _exceptions():
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
                    yield os.path.relpath(path, ROOT), doc


def _matches(doc):
    match = (doc.get("spec") or {}).get("match") or {}
    for key in ("any", "all"):
        for entry in match.get(key) or []:
            yield entry.get("resources") or {}


def test_there_are_exceptions_to_grade():
    """A guard that silently matches nothing is decoration."""
    assert list(_exceptions()), "no PolicyException found under platform/"


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


# The nine restricted pod-security policies. Waiving one of these lets a pod run privileged, as
# root, with a writable root filesystem -- so the founder's order applies to these in full:
# a surgical exception scoped to the exact workloads, never a weaker baseline.
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
# is deleted blind; each is still a pod excused because of where it sits rather than what it is.
# The fourth is a different reason: dagster's k8sRunLauncher launches a Job per run with a name
# it mints at runtime, so there is no pattern to name -- the fix there is upstream, not here.
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
    """A name in the ledger that no longer needs to be there is a row to delete, not to keep."""
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


def test_every_exception_is_wired_into_a_kustomization():
    """An exception no kustomization builds is a waiver that does not apply and a file that lies."""
    orphans = []
    for path, doc in _exceptions():
        directory = os.path.dirname(os.path.join(ROOT, path))
        kustomization = os.path.join(directory, "kustomization.yaml")
        if not os.path.exists(kustomization):
            continue  # built by a parent overlay, not this test's business
        built = (
            yaml.safe_load(open(kustomization, encoding="utf-8")).get("resources") or []
        )
        if os.path.basename(path) not in built:
            orphans.append(f"{doc['metadata']['name']} ({path})")
    assert not orphans, f"not built by their own kustomization: {orphans}"
