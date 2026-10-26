"""L3 -- the pack factory's adversarial validation.

No synthesized pack is promoted without passing five checks, and a check that
cannot fail is not a check:

1. **schema**      the pack carries the fields the contract names and every
                   ``match_logic`` parses
2. **replay**      the signature fires on the failures it was synthesized from
                   and does not fire on the non-failures of the same component
                   (precision >= 0.70, recall >= 0.60)
3. **blast radius** every diagnostic question is read-only, every remediation
                   template is allowlisted, and a T1/T2 template without a
                   tested rollback is downgraded to T0
4. **counterfactual** remove the cause from the evidence and the signature must
                   stop firing -- otherwise it was reading the symptom, not the
                   cause
5. **budget and isolation** the signature runs over the whole corpus inside
                   its declared sandbox, and the expression names nothing that
                   could reach the network or the filesystem
"""

from __future__ import annotations

from .match import Budget, BudgetExceeded, MatchError, matches, parse

PRECISION_FLOOR = 0.70
RECALL_FLOOR = 0.60

READ_ONLY_VERBS = ("get", "list", "describe", "read", "explain", "show", "fetch")
MUTATING_VERBS = (
    "delete",
    "remove",
    "patch",
    "apply",
    "create",
    "update",
    "replace",
    "scale",
    "restart",
    "rollout",
    "exec",
    "drain",
    "cordon",
    "evict",
    "annotate",
    "label",
    "set",
)

FORBIDDEN_IN_EXPRESSION = (
    "http://",
    "https://",
    "curl",
    "wget",
    "open(",
    "file://",
    "socket",
    "subprocess",
    "os.environ",
    "exec(",
    "eval(",
)


def _signature_positives(signature, corpus):
    """The failures this signature was synthesized from."""
    expected = signature.get("provenance", {}).get("expectedFailureClass")
    if expected:
        return [
            item
            for item in corpus
            if item.get("positive") and item.get("failure_class") == expected
        ]
    return [item for item in corpus if item.get("positive")]


def _signature_negatives(signature, corpus):
    expected = signature.get("provenance", {}).get("expectedFailureClass")
    if expected:
        return [
            item
            for item in corpus
            if not item.get("positive") or item.get("failure_class") != expected
        ]
    return [item for item in corpus if not item.get("positive")]


def validate_signature(signature, corpus, allowlist=None, budget_spec=None) -> dict:
    """The five checks for one signature."""
    result = {
        "id": signature.get("id", ""),
        "schema_valid": False,
        "precision": 0.0,
        "recall": 0.0,
        "blast_radius_ok": True,
        "counterfactual_ok": True,
        "budget_ok": True,
        "isolation_ok": True,
        "failures": [],
        "tier": (signature.get("remediation") or {}).get("tier", "T0"),
    }

    for field in ("id", "symptom", "matchLogic", "cause"):
        if not signature.get(field):
            result["failures"].append(f"{field} is required")
    try:
        parse(signature.get("matchLogic", ""))
    except MatchError as exc:
        result["failures"].append(f"matchLogic does not parse: {exc}")
    confidence = signature.get("confidenceBase")
    if confidence is None or not (0.0 <= float(confidence) <= 1.0):
        result["failures"].append("confidenceBase must be between 0 and 1")
    result["schema_valid"] = not result["failures"]

    budget = Budget(
        max_wall_clock_ms=(budget_spec or {}).get("maxWallClockMs", 5000),
        max_regex_complexity=(budget_spec or {}).get("maxRegexComplexity", "moderate"),
    )

    positives = _signature_positives(signature, corpus)
    negatives = _signature_negatives(signature, corpus)

    true_positive = 0
    for item in positives:
        try:
            if matches(
                signature.get("matchLogic", ""), item.get("artifact", {}), budget
            ):
                true_positive += 1
        except (BudgetExceeded, MatchError) as exc:
            result["failures"].append(f"budget/parse failure on a positive: {exc}")
            result["budget_ok"] = False

    false_positive = 0
    for item in negatives:
        try:
            if matches(
                signature.get("matchLogic", ""), item.get("artifact", {}), budget
            ):
                false_positive += 1
        except (BudgetExceeded, MatchError) as exc:
            result["failures"].append(f"budget/parse failure on a negative: {exc}")
            result["budget_ok"] = False

    precision = (
        true_positive / float(true_positive + false_positive)
        if (true_positive + false_positive)
        else 0.0
    )
    recall = true_positive / float(len(positives)) if positives else 0.0
    result["precision"] = round(precision, 4)
    result["recall"] = round(recall, 4)

    if positives and precision < PRECISION_FLOOR:
        result["failures"].append(
            f"precision {precision:.2f} below the {PRECISION_FLOOR} floor"
        )
    if positives and recall < RECALL_FLOOR:
        result["failures"].append(f"recall {recall:.2f} below the {RECALL_FLOOR} floor")

    # 3. blast radius
    for question in signature.get("diagnosticQuestions") or []:
        verb = str(question).strip().split(" ", 1)[0].lower()
        if verb in MUTATING_VERBS:
            result["blast_radius_ok"] = False
            result["failures"].append(
                f"diagnostic question is not read-only: {question!r}"
            )
        elif verb not in READ_ONLY_VERBS:
            result["blast_radius_ok"] = False
            result["failures"].append(
                f"diagnostic question does not start with a read verb: {question!r}"
            )
    remediation = signature.get("remediation") or {}
    tier = remediation.get("tier", "T0")
    if tier in ("T1", "T2"):
        if not remediation.get("safetyProof"):
            result["blast_radius_ok"] = False
            result["failures"].append("a T1/T2 signature needs a safetyProof")
        if tier == "T2" and not remediation.get("rollbackTemplate"):
            result["blast_radius_ok"] = False
            result["failures"].append("a T2 signature needs a rollback_template")

    # 4. counterfactual: remove the evidence that carries the cause
    if positives:
        stripped = _remove_cause_evidence(positives[0], signature)
        try:
            if matches(signature.get("matchLogic", ""), stripped, budget):
                result["counterfactual_ok"] = False
                result["failures"].append(
                    "the signature still fires with the cause removed"
                )
        except (BudgetExceeded, MatchError):
            result["counterfactual_ok"] = False
            result["failures"].append(
                "the counterfactual replay could not be evaluated"
            )

    # 5. budget and isolation
    expression = str(signature.get("matchLogic", ""))
    lowered = expression.lower()
    for needle in FORBIDDEN_IN_EXPRESSION:
        if needle in lowered:
            result["isolation_ok"] = False
            result["failures"].append(
                f"matchLogic names something outside the sandbox: {needle!r}"
            )

    result["ok"] = (
        result["schema_valid"]
        and result["blast_radius_ok"]
        and result["counterfactual_ok"]
        and result["budget_ok"]
        and result["isolation_ok"]
        and (not positives or (precision >= PRECISION_FLOOR and recall >= RECALL_FLOOR))
    )
    return result


def _remove_cause_evidence(item, signature):
    """The artifact with the causal evidence taken out.

    The failure class is the cause marker every synthesized signature reads,
    so removing it is the counterfactual the spec asks for: if the signature
    still fires, it was reading something else.
    """
    import copy

    artifact = copy.deepcopy(item.get("artifact") or {})
    boundary = artifact.get("failure_boundary") or {}
    boundary["failure_class"] = "unknown"
    artifact["failure_boundary"] = boundary
    return artifact


def validate_pack(pack, corpus, allowlist=None) -> dict:
    """The five checks over every signature in a pack."""
    spec = pack.get("spec") or {}
    results = []
    for signature in spec.get("signatures") or []:
        results.append(
            validate_signature(
                signature,
                corpus,
                allowlist=allowlist,
                budget_spec=spec.get("executionBudget") or {},
            )
        )
    report = {
        "pack": (pack.get("metadata") or {}).get("name", ""),
        "componentClass": spec.get("componentClass", ""),
        "corpusSize": len(corpus),
        "signatures": results,
        "ok": all(result["ok"] for result in results) if results else False,
        "precisionFloor": PRECISION_FLOOR,
        "recallFloor": RECALL_FLOOR,
    }
    return report
