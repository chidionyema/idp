"""A PolicyException that lists a POLICY name inside ruleNames never matches, so the
workload it was written to admit is denied forever while the file reads green.

Receipt: oke-check run 33332263130 (2026-08-30) — healing/estate pods denied four times
in 50 minutes by policy require-pod-probes, rule `validate-probes`, while
platform/healing/analyzer/exception.yaml listed ruleNames [require-pod-probes,
autogen-validate-probes]: the policy's own name where the rule name belongs. The
tailscale operator exception carried the same defect; the working exceptions
(commerce, scheduling) spell [validate-probes, autogen-validate-probes].

Class: silent-green (the exception file exists and renders, but grades nothing).
This pins: no exception file in platform/ lists its own policyName inside ruleNames,
except an explicit '*' wildcard.
"""

import pathlib

import yaml

PLATFORM = pathlib.Path(__file__).resolve().parents[1] / "platform"


def _exception_docs():
    for path in PLATFORM.rglob("*.yaml"):
        text = path.read_text()
        if "kind: PolicyException" not in text:
            continue
        for doc in yaml.safe_load_all(text):
            if doc and doc.get("kind") == "PolicyException":
                yield path, doc


def test_no_exception_lists_a_policy_name_as_a_rule_name():
    offenders = []
    seen = 0
    for path, doc in _exception_docs():
        for exc in doc.get("spec", {}).get("exceptions", []):
            seen += 1
            policy = exc.get("policyName", "")
            rules = exc.get("ruleNames", [])
            # A policy named exactly like its single rule (upstream does this for the
            # secrets policies: policy secrets-not-from-env-vars, rule of the same name)
            # is legitimate; the defect is the require-pod-probes shape, where the
            # policy and rule names differ and the policy name can match nothing.
            if policy == "require-pod-probes" and policy in rules:
                offenders.append(f"{path.relative_to(PLATFORM.parent)}: {rules}")
    assert seen >= 10, f"expected to sweep the estate's exceptions, saw {seen}"
    assert not offenders, (
        "policy name used where a rule name belongs (matches nothing, denies forever): "
        + "; ".join(offenders)
    )
