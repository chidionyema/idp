"""Meridian Epistemic Provenance & Mandatory Falsification Kernel (v1.0.0).

Zero-dependency deterministic verification kernel enforcing four cross-surface
invariants across Chat/MCP, Drive/Artifact stores, Lane 1 Cloudflare Workers,
Lane 2 OCI ARM A1, and Lane 3 GitHub Actions / Greenlane:

  E1: Primary vs. Secondary Provenance Typing (Anti-Epistemic-Laundering)
  E2: Scope-Bounded Observation & Anti-Invalid-Negation (Mandatory Falsification)
  E3: Anti-Proxy-Green Runtime Plane Contract Binding
  E4: Unforgeable Authority-Separated Cryptographic Receipt Verification
"""

from .kernel import (
    EpistemicError,
    EpistemicKernel,
    EvidenceTier,
    ExecutionPlane,
    FalsificationDecision,
    SignedReceipt,
    canonical_json,
    sign_receipt,
    verify_receipt_signature,
)

__all__ = [
    "EpistemicError",
    "EpistemicKernel",
    "EvidenceTier",
    "ExecutionPlane",
    "FalsificationDecision",
    "SignedReceipt",
    "canonical_json",
    "sign_receipt",
    "verify_receipt_signature",
]
