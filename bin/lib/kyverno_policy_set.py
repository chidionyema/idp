"""Shape a rendered ClusterPolicy set the way `kyverno apply --audit-warn` needs it.

Two defects in one pass, both measured on 2026-09-02 (the run 33618879684 follow-up):

1. DUPLICATES. bin/idp-kyverno-render assembles policies from three sources in order --
   the prospector rendered set, this repo's raw files (bin/idp-kyverno-own-policies), and
   the clusters/oke kustomize renders. The first two dedupe against each other; the third
   never did, so all 11 estate policies were applied twice and every estate-policy verdict
   line and fail count printed doubled (platform/llm: fail 8 over 4 workloads). Last copy
   wins here: the clusters/oke render is appended last and is the bytes Flux applies.

2. MIXED POLICIES. The CLI's --audit-warn flag decides at POLICY granularity: a policy
   holding one Enforce rule counts a failing Audit rule as `fail`, not `warn` (minimal
   two-rule fixture, kyverno v1.19.0 -- see the test file). Admission decides per RULE:
   a failureAction Audit rule never blocks an apply. So a mixed policy is split into an
   enforce half (keeps the original name, so PolicyExceptions written for its Enforce
   rules still match) and an audit half (name + `-audit-rules`; an exception aimed at an
   audit rule stops matching, which can only add a warn row, never a verdict).

Rules other than validate (mutate, generate, verifyImages) carry no failureAction and
stay in the enforce half. The policy-level spec.validationFailureAction (default Audit)
backs any rule that omits its own failureAction.
"""

import sys

import yaml


def _effective_action(rule, spec):
    v = rule.get("validate") or {}
    return v.get("failureAction") or spec.get("validationFailureAction") or "Audit"


def split_policy(doc):
    """One ClusterPolicy -> [enforce-or-mixed-free policy, optional audit-half policy]."""
    spec = doc.get("spec") or {}
    rules = spec.get("rules") or []
    audit = [
        r for r in rules if "validate" in r and _effective_action(r, spec) == "Audit"
    ]
    rest = [r for r in rules if r not in audit]
    if not audit or not rest:
        return [doc]

    def _with(rules_subset, name):
        d = yaml.safe_load(yaml.safe_dump(doc))  # deep copy
        d["metadata"]["name"] = name
        d["spec"]["rules"] = rules_subset
        return d

    name = doc["metadata"]["name"]
    return [_with(rest, name), _with(audit, f"{name}-audit-rules")]


def shape(docs):
    """Dedupe ClusterPolicies by name (last copy wins), then split the mixed ones."""
    last = {}
    order = []
    for d in docs:
        if not (isinstance(d, dict) and d.get("kind") == "ClusterPolicy"):
            order.append(("doc", len(order), d))
            continue
        name = (d.get("metadata") or {}).get("name")
        if name not in last:
            order.append(("pol", name, None))
        last[name] = d
    out = []
    for kind, key, d in order:
        if kind == "doc":
            out.append(d)
        else:
            out.extend(split_policy(last[key]))
    return out


def main(path):
    docs = [d for d in yaml.safe_load_all(open(path)) if d]
    open(path, "w").write(yaml.safe_dump_all(shape(docs), sort_keys=False))


if __name__ == "__main__":
    main(sys.argv[1])
