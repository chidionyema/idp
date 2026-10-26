"""Interface 3 -- the reasoning layer.

    Reason(artifact, pack) -> DiagnosticReport

The workflow is fixed and auditable, and every step can stop it with a named
outcome rather than a guess:

    1. validate the artifact and its digest      -> TAMPER_DETECTED
    2. resolve the pack for class and version    -> COVERAGE_VIOLATION
    3. negotiate the interface version           -> SKILLPACK_INCOMPATIBLE
    4. load the pack's budget and isolation
    5. evaluate each signature's matchLogic in the sandbox, best first
    6. score, rank, and either report or say NEEDS_HUMAN

The artifact's own ``self_assessment`` is input, never verdict: a hypothesis
nothing corroborates is marked ``UNCORROBORATED_HYPOTHESIS`` and is not
propagated as a cause.
"""

from __future__ import annotations

from . import INTERFACE_VERSION
from .contract import validate_artifact
from .match import Budget, BudgetExceeded, MatchError, matches

CONFIDENCE_THRESHOLD = 0.5
T1_CONFIDENCE = 0.85
T2_CONFIDENCE = 0.95


def _evidence_strength(artifact: dict) -> float:
    """How much evidence the artifact actually carries.

    Three payloads is the point where the estate has seen enough to call a
    cause; one payload is a hint. The factor is clamped so a thin artifact
    can never reach the T1 gate on its own.
    """
    payloads = (artifact.get("raw_evidence") or {}).get("payloads") or []
    if not payloads:
        return 0.2
    return max(0.2, min(1.0, len(payloads) / 3.0))


def _corroboration(artifact: dict, signature: dict) -> float:
    """Independent support for this signature's cause.

    A cause stated by the component's own assessment, or echoed by a payload
    kind, is corroborated. A cause that only the signature asserts is weaker.
    """
    cause = (signature.get("cause") or "").lower()
    hypotheses = (artifact.get("self_assessment") or {}).get("hypotheses") or []
    for hypothesis in hypotheses:
        if str(hypothesis.get("cause", "")).lower() == cause:
            return 1.0
    payload_kinds = {
        str(p.get("kind", ""))
        for p in ((artifact.get("raw_evidence") or {}).get("payloads") or [])
    }
    tokens = {token for token in cause.replace("_", " ").split() if len(token) > 3}
    for kind in payload_kinds:
        for token in tokens:
            if token in kind.replace("_", " "):
                return 1.0
    return 0.85


def reason(artifact: dict, pack: dict, registry=None, packs_by_name=None) -> dict:
    """Produce a DiagnosticReport for an artifact under a pack."""
    report = {
        "status": "DIAGNOSED",
        "cause": "",
        "confidence": 0.0,
        "packRef": "",
        "signatureId": "",
        "evidenceRefs": [],
        "questionsAsked": [],
        "warnings": [],
        "budgetBreaches": [],
        "remediation": {},
        "hypotheses": [],
    }

    errors = validate_artifact(artifact, registry)
    if errors:
        report["status"] = "TAMPER_DETECTED"
        report["warnings"].extend(errors)
        return report

    spec = (pack or {}).get("spec") or {}
    report["packRef"] = "{}@{}".format(
        ((pack or {}).get("metadata") or {}).get("name", ""),
        spec.get("version", ""),
    )

    interface = spec.get("interfaceVersion", INTERFACE_VERSION)
    if interface != INTERFACE_VERSION:
        report["status"] = "SKILLPACK_INCOMPATIBLE"
        report["warnings"].append(
            f"pack interface {interface} does not negotiate with {INTERFACE_VERSION}"
        )
        return report

    if not spec.get("signatures"):
        report["status"] = "COVERAGE_VIOLATION"
        report["warnings"].append("pack carries no signatures")
        return report

    budget_spec = spec.get("executionBudget") or {}
    budget = Budget(
        max_wall_clock_ms=budget_spec.get("maxWallClockMs", 5000),
        max_steps=budget_spec.get("maxSteps", 20000),
        max_regex_complexity=budget_spec.get("maxRegexComplexity", "moderate"),
    )

    signatures = sorted(
        spec.get("signatures") or [],
        key=lambda s: float(s.get("confidenceBase", 0.0)),
        reverse=True,
    )

    scored = []
    for signature in signatures:
        try:
            fired = matches(signature.get("matchLogic", ""), artifact, budget)
        except BudgetExceeded as exc:
            report["budgetBreaches"].append(
                {"signatureId": signature.get("id"), "reason": str(exc)}
            )
            continue
        except MatchError as exc:
            report["budgetBreaches"].append(
                {
                    "signatureId": signature.get("id"),
                    "reason": f"matchLogic invalid: {exc}",
                }
            )
            continue
        if not fired:
            continue
        strength = _evidence_strength(artifact)
        corroboration = _corroboration(artifact, signature)
        confidence = round(
            float(signature.get("confidenceBase", 0.0)) * strength * corroboration, 4
        )
        scored.append(
            {
                "signature": signature,
                "confidence": confidence,
                "evidence_strength": round(strength, 4),
                "corroboration": round(corroboration, 4),
            }
        )

    if not scored:
        report["status"] = "NEEDS_HUMAN"
        report["questionsAsked"] = list(spec.get("diagnosticQuestions") or [])
        report["warnings"].append("no signature matched the artifact's evidence")
        return report

    best = scored[0]
    signature = best["signature"]
    report["cause"] = signature.get("cause", "")
    report["confidence"] = best["confidence"]
    report["signatureId"] = signature.get("id", "")
    report["evidenceRefs"] = [
        f"raw_evidence.payloads[{index}]"
        for index, payload in enumerate(
            (artifact.get("raw_evidence") or {}).get("payloads") or []
        )
    ]
    report["questionsAsked"] = list(signature.get("diagnosticQuestions") or [])
    report["remediation"] = dict(signature.get("remediation") or {})
    report["hypotheses"] = [
        {
            "rank": index + 1,
            "cause": entry["signature"].get("cause", ""),
            "confidence": entry["confidence"],
            "signatureId": entry["signature"].get("id", ""),
        }
        for index, entry in enumerate(scored)
    ]

    # The artifact's own assessment is input, never verdict.
    for hypothesis in (artifact.get("self_assessment") or {}).get("hypotheses") or []:
        stated = str(hypothesis.get("cause", "")).lower()
        if not stated:
            continue
        if stated not in {str(h["cause"]).lower() for h in report["hypotheses"]}:
            report["warnings"].append(
                f"UNCORROBORATED_HYPOTHESIS: {hypothesis.get('cause')} is asserted by the artifact "
                "and corroborated by nothing"
            )

    if best["confidence"] < CONFIDENCE_THRESHOLD:
        report["status"] = "NEEDS_HUMAN"
        report["warnings"].append(
            f"top confidence {best['confidence']} is below the {CONFIDENCE_THRESHOLD} threshold"
        )
    return report
