"""FleetView item #9: a receipt check over production traces -- repeatable, not a model judging
a model.

The original ask was to reconcile the qa-agent/receipt-auditor subagent pattern with an
automated, repeatable loop over real production Langfuse traces. Built literally, that is a
model grading another model's session -- exactly what `sovereign/shadow/distill.py`'s own
`grade()` step already refuses ("a deterministic grader ... no model judges another model").
Shipping that here would plant a second, contradictory rule five files from the one that states
it, and it would need a live `claude` subprocess call per production session with no budget
guardrail -- the same class of risk `sovereign/policy.py`'s `[budget]` block exists to bound.

What ships instead: the same question receipt-auditor asks -- "does every claim in this session
have a receipt?" -- answered mechanically, the way `bin/idp-rules` grades every other law in this
estate. `sovereign/engine/tracing.py` writes one Langfuse trace per session, with `id=session_id`
and a `status:<status>` tag (see `trace_session()`). A trace tagged `status:done` or
`status:success` with zero recorded observations is exactly the failure receipt-auditor exists to
catch -- a claimed success with no evidence behind it -- caught here without a model call.

Repeatable, not autonomous: this runs when a person presses "Check receipts" on the Fleet page
(the same rule item #6's nudge button follows) -- one HTTP call over a named batch of sessions,
no scheduler, nothing that could run away unattended.

CONTRACT NOT VERIFIED LIVE: `langfuse>=2.0,<3` is pinned in `sovereign/requirements.txt` but is
not installed in this environment, so `fetch_trace`'s response shape here is written against the
SDK's published contract, not exercised against a running Langfuse -- the same honesty bar
`signals.py` sets for `sovereign.engine.client.signal` (proven by a stub in tests, not a live
call). A Langfuse read failure of any kind is a per-session `not_applicable` verdict with the
reason recorded, never a fabricated pass or fail.

CONFIG (LAW 46): LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY -- the same variables `sovereign.config` and
`sovereign.engine.tracing` already read; no second Langfuse configuration.
"""

from __future__ import annotations

from typing import Any

# A claim of success this check can hold to account. Any other status (running, failed, ...) has
# no success claim to audit, and is not_applicable rather than a false pass.
_SUCCESS_STATUSES = frozenset({"done", "success"})


class InvalidQuery(ValueError):
    """A malformed request -- nothing named to check. routes.py turns this into 400, same as
    blast.py's own InvalidQuery."""


class EvalsUnavailable(RuntimeError):
    """Raised when Langfuse is not configured or not importable here -- routes.py turns this
    into 503, matching signals.py's own rule for a real gap versus a fabricated answer."""


def _langfuse_client():
    try:
        from sovereign import config
    except ImportError as exc:
        raise EvalsUnavailable(f"sovereign package not importable here: {exc}") from exc
    if not (config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY):
        raise EvalsUnavailable("LANGFUSE_* is not configured")
    try:
        from langfuse import Langfuse  # type: ignore
    except ImportError as exc:
        raise EvalsUnavailable(f"langfuse package not importable here: {exc}") from exc
    return Langfuse(
        host=config.LANGFUSE_HOST,
        public_key=config.LANGFUSE_PUBLIC_KEY,
        secret_key=config.LANGFUSE_SECRET_KEY,
    )


def _status_tag(tags: list[str]) -> str | None:
    for tag in tags or []:
        if tag.startswith("status:"):
            return tag[len("status:") :]
    return None


def check_receipts(session_id: str, client: Any = None) -> dict[str, Any]:
    """One session's verdict: 'pass', 'fail', or 'not_applicable', with a reason.

    `client` is accepted so a batch call reuses one Langfuse client instead of opening one per
    session; a caller with none gets one built from config (raises EvalsUnavailable if that is
    not possible, so the whole batch has one honest failure instead of N).
    """
    session_id = (session_id or "").strip()
    if not session_id:
        raise InvalidQuery("session_id is required")
    if client is None:
        client = _langfuse_client()

    try:
        fetched = client.fetch_trace(session_id)
        trace = fetched.data
    except Exception as exc:  # noqa: BLE001 - an unreadable trace is a fact to report, not hide
        return {
            "session_id": session_id,
            "verdict": "not_applicable",
            "reason": f"trace not readable: {exc.__class__.__name__}: {exc}",
        }

    status = _status_tag(getattr(trace, "tags", None) or [])
    if status not in _SUCCESS_STATUSES:
        return {
            "session_id": session_id,
            "verdict": "not_applicable",
            "reason": f"no success claim to check (status tag: {status or 'none recorded'})",
        }

    observations = getattr(trace, "observations", None) or []
    if not observations:
        return {
            "session_id": session_id,
            "verdict": "fail",
            "reason": f"tagged status:{status} but the trace recorded no observations -- "
            "a claimed success with no receipt behind it",
        }
    return {
        "session_id": session_id,
        "verdict": "pass",
        "reason": f"status:{status}, {len(observations)} observation(s) recorded",
    }


def check_receipts_batch(session_ids: list[str]) -> list[dict[str, Any]]:
    """Every session's verdict, one Langfuse client shared across the batch. One session whose
    trace cannot be read never drops the rest -- see check_receipts's own not_applicable rule."""
    session_ids = [s.strip() for s in (session_ids or []) if s and s.strip()]
    if not session_ids:
        raise InvalidQuery("session_ids is required")
    client = _langfuse_client()
    return [check_receipts(sid, client=client) for sid in session_ids]
