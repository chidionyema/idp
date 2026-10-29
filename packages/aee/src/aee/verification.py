"""Independent verification: the estate's NSVEE verdict becomes an AEE receipt.

The estate already has a verification engine -- ``nsvee/engine.py`` -- with a
four-tier zero-trust pipeline. It already has a verification spine --
``sovereign/engine/receipts.py``. This module is the SEAM between them and the
AEE's WorkGraph, and it is deliberately a seam and not a second engine:

  * it never imports ``nsvee``. The report is DATA (a mapping), so the AEE
    package inherits nothing from NSVEE and cannot drift from it.
  * it never re-runs a verdict. NSVEE already decided; this records what it
    decided, at the level the work graph asks for.
  * it never invents a verdict for a status it does not know. An unknown
    status is INCONCLUSIVE -- not a pass, and not a failure either.

The three levels are the AEE's, and they are three different questions:

    operation    the code did what the contract said
    integration  the work works inside the work that consumes it
    objective    the work achieved the objective it was chosen for

Only the first is something NSVEE can testify to (its tier 3, the sandboxed
execution). The other two are the estate's own, and the objective one carries
a rule: the agent that did the work may not sign its own objective
acceptance. That refusal is ``IndependenceRequiredError`` in ``aee.graph`` and
it is raised when the receipt is recorded, not when the node is accepted -- a
receipt that should not exist never enters the graph.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .contracts import (
    ContractError,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
)
from .digest import digest_of

#: The pipeline statuses NSVEE's report carries. A status outside this list is
#: not a failure of the work; it is a status this module does not know, and it
#: is treated as inconclusive rather than guessed at.
NSVEE_STATUSES = (
    "VERIFIED",
    "HUMAN_INPUT_REQUIRED",
    "EXHAUSTED",
    "SANDBOX_DEGRADED",
    "FORMALIZATION_ERROR",
)

_STATUS_VERDICTS: Dict[str, Verdict] = {
    "VERIFIED": Verdict.PASS,
    "EXHAUSTED": Verdict.FAIL,
    "FORMALIZATION_ERROR": Verdict.FAIL,
    "SANDBOX_DEGRADED": Verdict.INCONCLUSIVE,
    "HUMAN_INPUT_REQUIRED": Verdict.INCONCLUSIVE,
}


def _value(enum_value: Any) -> str:
    """The value of a str enum, whether it arrived as the enum or as its text."""
    return str(getattr(enum_value, "value", enum_value))


def verdict_for_status(status: str) -> Verdict:
    """The AEE verdict for an NSVEE pipeline status.

    ``VERIFIED`` is a pass. ``EXHAUSTED`` and ``FORMALIZATION_ERROR`` are
    failures: the pipeline ran and the work was not proven.
    ``SANDBOX_DEGRADED`` and ``HUMAN_INPUT_REQUIRED`` are inconclusive: the
    infrastructure broke, or a person has to decide, and neither is the code's
    fault -- recording either as a failure would punish the work for the
    verifier's problem. An unrecognised status is inconclusive as well.
    """
    return _STATUS_VERDICTS.get(str(status or "").strip().upper(), Verdict.INCONCLUSIVE)


def level_for_tier(tier: str) -> Optional[VerificationLevel]:
    """The level an NSVEE tier can testify to, or ``None`` when it cannot.

    Only tier 3 -- multi-engine verification and sandboxed execution -- produces
    an executable verdict, so only tier 3 can attest the operation. Tiers 1, 2
    and 4 shape and repair the attempt; they say nothing about whether the work
    was done.
    """
    name = str(tier or "").strip().lower()
    if name.startswith("tier3"):
        return VerificationLevel.OPERATION
    return None


def report_digest(report: Mapping[str, Any]) -> str:
    """The content address of an NSVEE report: the locator a receipt points at."""
    return digest_of(dict(report))


def receipt_for(
    *,
    node_id: str,
    attempt_id: str,
    level: VerificationLevel,
    verdict: Verdict,
    evidence: str,
    verifier: str,
    contract_id: str = "",
    at: float = 0.0,
    fingerprint: Optional[Mapping[str, Any]] = None,
) -> VerificationReceipt:
    """Build a verification receipt whose id is derived, never generated.

    The id is a digest of what the receipt says, so the same evidence produces
    the same receipt id and a replay does not become a second receipt.
    """
    basis = {
        "node": node_id,
        "attempt": attempt_id,
        "level": _value(level),
        "verdict": _value(verdict),
        "evidence": evidence,
        "verifier": verifier,
        "contract": contract_id,
        "fingerprint": dict(fingerprint or {}),
    }
    receipt_id = "ver-%s" % digest_of(basis)[:16]
    return VerificationReceipt(
        id=receipt_id,
        node_id=node_id,
        attempt_id=attempt_id,
        level=level,
        verdict=verdict,
        evidence=evidence,
        verifier=verifier,
        at=at,
        contract_id=contract_id,
    )


def receipt_from_nsvee(
    *,
    node_id: str,
    attempt_id: str,
    report: Mapping[str, Any],
    level: VerificationLevel = VerificationLevel.OPERATION,
    verifier: str = "nsvee",
    contract_id: str = "",
    at: float = 0.0,
) -> VerificationReceipt:
    """Turn an NSVEE pipeline report into an AEE verification receipt.

    The evidence is the report's content address, so the receipt points at the
    exact report it read. The verdict is the report's status read through
    :func:`verdict_for_status` -- an unknown or degraded status becomes an
    inconclusive receipt, which never counts as a pass and never counts as a
    failure of the work.
    """
    if not isinstance(report, Mapping):
        raise ContractError(
            "an NSVEE report is a mapping, got %r" % type(report).__name__
        )
    status = str(report.get("status", "") or "")
    verdict = verdict_for_status(status)
    try:
        digest = report_digest(report)
    except Exception as exc:  # noqa: BLE001 - any serialisation failure is the caller's
        raise ContractError(
            "an NSVEE report must be JSON data to serve as evidence: %s" % exc
        ) from exc
    return receipt_for(
        node_id=node_id,
        attempt_id=attempt_id,
        level=level,
        verdict=verdict,
        evidence="nsvee-report:%s" % digest,
        verifier=verifier,
        contract_id=contract_id,
        at=at,
        fingerprint={"status": status, "report": digest},
    )
