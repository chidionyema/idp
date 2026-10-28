"""platform.estate.context -- the estate's context plane: one compiler, one broker, one door.

WHAT THIS PACKAGE IS. The decision the founder took on 2026-10-27, and the shape the
consultant's review confirmed: there is exactly one door, the broker, and the engine behind it
is private and unroutable. This package holds the part that makes that true -- the POLICY.
The transport (MCP/HTTP) and the engine adapter are separate modules; the decisions are here,
in pure functions, because a refusal that cannot be tested is a refusal nobody can rely on.

WHAT IT IS NOT. It is not a retriever. Retrieval is gortex's job (zzet/gortex, Apache-2.0);
ranking, symbol resolution and impact selection are the engine's. What the engine cannot do is
decide whether an answer may be served: that is here, and it is the estate's law expressed as
code -- a claim, a commit, a budget, a secret name and a provenance envelope.

    from platform.estate.context.broker import decide_request

    verdict = decide_request(request, state)
    if not verdict.allow:
        raise Refused(verdict)
    return verdict

THE LAWS THIS ENFORCES, ONE PER FUNCTION:

    freshness_decision()  the index must match the commit the caller asked about (AGENTS.md: proof,
                           not assertion -- a stale answer is not an answer)
    path_allowed()         a path outside the live claim's paths is refused (AGENTS.md 5: no work
                           without a claim)
    tool_allowed()         context is read-only; a context request may not mutate the tree
    budget_decision()      a context budget is a ceiling, not a suggestion (request_ceiling.py)
    scrub()                a secret value never leaves; the agent gets REF:<NAME> instead
    provenance()           every excerpt says which file, which commit, which lines, which digest

ONE OF EACH (AGENTS.md 6). This is the ONE context decision point. A second implementation of
these decisions -- in a harness, in a hook, in a script -- is stitching and gets deleted in the
same change that adds it.
"""

from __future__ import annotations

__all__ = ["broker"]
