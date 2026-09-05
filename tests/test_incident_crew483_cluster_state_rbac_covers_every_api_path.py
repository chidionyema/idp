"""Incident test, crew#483 (2026-08-27): the receipt showed k8s-infra denied by Kyverno with the
PolicyException on main, and the collector could not say whether the cluster held it, because it
never listed policyexceptions. Adding the list call without the RBAC rule would put an
'list failed: 403' row in every receipt instead. Rule: every API path the collector script calls
is granted get/list by its ClusterRole, and the receipt body carries policy_exceptions and a
'since' on each Flux row. Rung 4, both ways: the manifest on this branch passes; the same script
with one extra ungranted path fails.
"""
import ast
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"

CORE = {"nodes", "pods", "events"}


def _load():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    role = next(d for d in docs if d.get("kind") == "ClusterRole")
    src = next(d["data"]["collect.py"] for d in docs if d.get("kind") == "ConfigMap" and "collect.py" in d.get("data", {}))
    return role, src


def _granted(role):
    out = set()
    for rule in role["rules"]:
        verbs = set(rule["verbs"])
        for g in rule["apiGroups"]:
            for r in rule["resources"]:
                # a subresource such as services/proxy is read with get alone; a collection needs list too
                if ("/" in r and "get" in verbs) or {"get", "list"} <= verbs:
                    out.add((g, r))
    return out


def _paths(src):
    return re.findall(r'"(/api(?:s)?/[^"{]+)"', src)


def _ungranted(role, src):
    granted = _granted(role)
    bad = []
    for p in _paths(src):
        parts = p.split("?")[0].strip("/").split("/")
        # /api/v1/<resource> | /api/v1/namespaces/<ns>/<resource>[/<name>/<subresource>/...]
        # /apis/<group>/<version>/<resource> | /apis/<group>/<version>/namespaces/<ns>/<resource>[/...]
        group, rest = ("", parts[2:]) if parts[0] == "api" else (parts[1], parts[3:])
        if rest and rest[0] == "namespaces" and len(rest) > 2:
            rest = rest[2:]
        resource = rest[0] if rest else parts[-1]
        if len(rest) > 2 and rest[2] in ("proxy", "log", "status"):
            resource = f"{resource}/{rest[2]}"
        if (group, resource) not in granted:
            bad.append(p)
    return bad


def test_incident_crew483_every_api_path_the_collector_calls_is_granted():
    role, src = _load()
    ast.parse(src)
    assert _paths(src), "the collector calls the API by literal path"
    assert _ungranted(role, src) == []
    assert ("kyverno.io", "policyexceptions") in _granted(role)
    assert '"/apis/kyverno.io/v2/policyexceptions"' in src
    assert '"policy_exceptions": policy_exceptions' in src
    assert '"since": c.get("lastTransitionTime")' in src


def test_incident_crew483_an_ungranted_path_fails():
    role, src = _load()
    bad = src + '\nget("/apis/cilium.io/v2/ciliumnetworkpolicies")\n'
    assert _ungranted(role, bad) == ["/apis/cilium.io/v2/ciliumnetworkpolicies"]
