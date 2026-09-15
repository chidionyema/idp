"""Verifier-aware candidate selection and volume capping (idp#3525 CP4, VER-02/VER-04).

VER-02: "Where a real verifier exists, weighted voting by verifier score or multi-verifier
SHALL be used; plain best-of-N with a noisy selector is disallowed there." ACCEPT: config sets
selection=weighted-vote for Z3-scored domains; harness honors it; N-scaling on unverifiable
domains is capped.

VER-04: "The harness SHALL detect tasks with no real verifier and SHALL cap candidate volume for
them -- volume scales noise, not accuracy, past the verifier's ROC ceiling." ACCEPT: unverifiable
task class -> N capped at declared constant regardless of config.

Both reuse `classify_domain` from sovereign/verifier.py -- the same suffix-based domain split
CP4's gauntlet already makes (VER-01) -- rather than inventing a second notion of "which domains
are verified." `sovereign.engine.routing_matrix` already excludes plain best-of-N from its own
selection_method enum ({gate, weighted_vote, multi_verifier}); the guard here is what stops a
verified-domain cell from picking `gate` at N>1, which is a noisy selector by another name (N
candidates with no verifier-backed way to choose among them).
"""

from __future__ import annotations

from typing import Any

from sovereign.engine.routing_matrix import RoutingMatrixError
from sovereign.verifier import classify_domain

# The three domains sovereign/verifier.py's gauntlet actually scores (VER-01's stage_symbolic is
# the Z3 half of "code"; stage_structural/stage_sql cover the other two). Everything else is
# "other" -- no real verifier exists for it.
VERIFIED_DOMAINS = {"code", "k8s_manifest", "sql_schema"}

# VER-04's "declared constant". 3, not config: it is the ceiling past which N stops buying
# accuracy on a domain with no verifier to score the extra candidates against (spec S6,
# ROC-n-reroll) -- raising it requires changing this line, not a config file.
MAX_UNVERIFIED_N = 3

_VERIFIER_BACKED_SELECTION = {"weighted_vote", "multi_verifier"}


def has_real_verifier(path: str) -> bool:
    """Whether sovereign/verifier.py's gauntlet actually scores this file's domain."""
    return classify_domain(path) in VERIFIED_DOMAINS


def assert_selection_policy(path: str, cell: dict[str, Any]) -> None:
    """VER-02's disallow clause: a verified domain running more than one candidate must be
    selected among by a verifier-backed method, never `gate` (which does not score candidates
    against each other at all -- run at N>1 with no scoring, it is plain best-of-N wearing a
    different config value).

    A single candidate (N=1) needs no selection among candidates, so `gate` is fine there --
    this only fires where a "noisy selector" would actually be doing something.
    """
    if not has_real_verifier(path):
        return
    n = cell.get("candidate_volume", 1)
    method = cell.get("selection_method")
    if n > 1 and method not in _VERIFIER_BACKED_SELECTION:
        raise RoutingMatrixError(
            f"{path}: domain {classify_domain(path)!r} has a real verifier and candidate_volume="
            f"{n} > 1, so selection_method must be one of {sorted(_VERIFIER_BACKED_SELECTION)} "
            f"(got {method!r}) -- plain best-of-N with a noisy selector is disallowed here (VER-02)"
        )


def resolve_candidate_volume(path: str, requested_n: int) -> int:
    """VER-04: an unverifiable domain's candidate volume is capped at MAX_UNVERIFIED_N no matter
    what a config cell asks for. A verified domain passes `requested_n` through unchanged --
    capping is specifically the mitigation for a domain with nothing to score the extra
    candidates against, not a general throttle."""
    if has_real_verifier(path):
        return requested_n
    return min(requested_n, MAX_UNVERIFIED_N)
