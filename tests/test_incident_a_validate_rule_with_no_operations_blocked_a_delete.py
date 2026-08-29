"""2026-08-29 02:2xZ, break-glass run 33228300516: Namespace/backstage stayed Terminating because
`provider-independence/no-provider-storage-class` had no `operations:` and so judged the DELETE of
the old PVC pgdata-postgres-0 (`NamespaceDeletionContentFailure ... admission webhook
"validate.kyverno.svc-fail" denied the request`). A validate rule that judges a DELETE turns an
old object into a permanent tenant: a guard that refuses correct work is an outage (LAW 38). Every
validate rule under platform/ names its operations, and DELETE appears only in a rule whose name
says so (protect-namespaces/refuse-delete-of-marked-namespace is the one that means it).
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _validate_rules():
    for p in sorted((ROOT / "platform").rglob("*.yaml")):
        try:
            docs = list(yaml.safe_load_all(p.read_text()))
        except yaml.YAMLError:
            continue
        for d in docs:
            if not isinstance(d, dict) or d.get("kind") != "ClusterPolicy":
                continue
            for r in d.get("spec", {}).get("rules", []):
                if "validate" in r:
                    yield p.relative_to(ROOT), d["metadata"]["name"], r


def _blocks(rule):
    m = rule.get("match", {})
    out = [m["resources"]] if "resources" in m else []
    for sel in ("any", "all"):
        out += [b.get("resources", {}) for b in (m.get(sel) or [])]
    return out


RULES = list(_validate_rules())


@pytest.mark.parametrize("path,policy,rule", RULES, ids=[f"{p}/{r['name']}" for _, p, r in RULES])
def test_every_validate_rule_names_operations_and_judges_a_delete_only_on_purpose(path, policy, rule):
    for b in _blocks(rule):
        ops = b.get("operations")
        assert ops, f"{path} {policy}/{rule['name']}: a match block names no operations, so it judges DELETE too"
        if "DELETE" in ops:
            assert "delete" in rule["name"], f"{path} {policy}/{rule['name']}: judges DELETE without saying so in its name"


def test_the_sweep_found_the_policies():
    # 15 until the PersistentVolumeClaim rule was removed (2026-08-29, it judged the cluster default)
    assert len(RULES) >= 14, [r[1] for r in RULES]
