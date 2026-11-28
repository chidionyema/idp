"""Temporal activities. All side effects (subprocess, http, disk) live here,
never in workflow.py, so workflow replay stays deterministic.

Every activity below is `async def` (Temporal dispatches it on the worker's
event loop), so any *synchronous* I/O inside it -- a blocking httpx.post, a
file open()+fcntl.flock(), a `security` Keychain subprocess call made via
subprocess.run -- must run on `asyncio.to_thread`, never inline. Inline sync
I/O here stalls the whole event loop: every other workflow task on this
worker stops being polled, a workflow task then exceeds its 5s limit
(TMPRL1104), and an update sent to a workflow whose task the worker can't
service in time is reported as failed. Observed 2026-08-25: notify_change
called sovereign.otto.card.on_change synchronously (blocking httpx.post
plus a blocking asyncio.run() of a client update back into this same
workflow) and receipts.append() did its file/flock/Keychain I/O inline;
workflow_task_duration=151152ms and "Workflow Task in failed state" on
set_line_message_id were both this one root cause.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from typing import Any

from temporalio import activity

from sovereign import config
from sovereign.engine import budget
from sovereign.engine import gitops
from sovereign.engine import interventions as interventions_mod
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import runners
from sovereign.engine import tracing


@activity.defn
async def run_step(inp: dict[str, Any]) -> dict[str, Any]:
    """Runs the step, then records the git commit the step left behind.

    cp24 requires the receipt to carry "a git commit hash that exists in
    the repo", and R7's undo reverts to that commit's parent. The HEAD is
    read here, after the runner, rather than reported by the runner
    itself: a runner is a vendor CLI (LAW 34) and must not be trusted to
    tell the truth about the repository. `commit` is None when the step
    changed nothing, so a receipt never claims a commit that a later step
    actually produced."""
    repo = inp.get("repo")
    before = (
        await asyncio.to_thread(gitops.head, repo) if gitops.is_repo(repo) else None
    )
    result = await runners.run(
        inp["runner"],
        inp["task"],
        repo,
        inp["step"],
        inp.get("steer") or [],
        session_id=inp.get("session_id"),
    )
    after = await asyncio.to_thread(gitops.head, repo) if gitops.is_repo(repo) else None
    result = dict(result)
    result["commit"] = after if after and after != before else None
    return result


@activity.defn
async def verify_instruction_yield(inp: dict[str, Any]) -> str:
    """Independent authority, pinned by the trusted worker host.

    No worker result, caller-supplied key, or success-shaped prose can
    produce a settlement. The observer must attest the exact external
    effect (or reconciliation that permits replay).
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    expected = inp.get("expected")
    envelope = inp.get("envelope")
    key = os.environ.get("ESTATE_YIELD_VERIFIER_PUBKEY_HEX", "")
    if not (
        isinstance(expected, dict)
        and isinstance(envelope, dict)
        and re.fullmatch(r"[0-9a-fA-F]{64}", key)
    ):
        return "reject"
    receipt = envelope.get("receipt")
    signature = envelope.get("signature")
    if not isinstance(receipt, dict) or not isinstance(signature, str):
        return "reject"
    if not re.fullmatch(r"[0-9a-fA-F]{128}", signature):
        return "reject"
    if set(receipt) != set(expected) | {"action", "ok", "effect_ref", "reconciled"}:
        return "reject"
    if any(receipt.get(field) != value for field, value in expected.items()):
        return "reject"
    if type(receipt.get("epoch")) is not int or receipt.get("ok") is not True:
        return "reject"
    action = receipt.get("action")
    effect = receipt.get("effect_ref")
    if (
        action not in ("settle", "retry")
        or receipt.get("reconciled") is not True
        or not isinstance(effect, str)
        or not effect.strip()
        or len(effect) > 512
    ):
        return "reject"
    try:
        subject = (
            b"meridian/instruction-yield-v1:"
            + json.dumps(
                receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(
            bytes.fromhex(signature), subject
        )
    except (InvalidSignature, TypeError, ValueError):
        return "reject"
    return action


@activity.defn
async def rust_gate_verify_settlement(inp: dict[str, Any]) -> str:
    """Second, compiled authority over settlement (MERIDIAN-CTRL-001 B08, B10).

    Everything that decides trust comes from this host, not from the verifier's message:
    the trusted certifier keys, the worker key (so a worker cannot certify itself), the
    revocation epoch and the clock. The envelope supplies only the obligation's predicate
    and policy hashes and the receipt, and the certifier's signature covers both. Returns
    "allow" only when meridian-gate prints ALLOW; every other outcome, including a missing
    binary, a timeout or a malformed message, is "reject".
    """
    import time

    from sovereign.engine import rust_gate_bridge

    expected = inp.get("expected")
    envelope = inp.get("envelope")
    if not (isinstance(expected, dict) and isinstance(envelope, dict)):
        return "reject"
    settlement = envelope.get("settlement")
    if not isinstance(settlement, dict):
        return "reject"
    claimed = settlement.get("obligation")
    receipt = settlement.get("receipt")
    if not (isinstance(claimed, dict) and isinstance(receipt, dict)):
        return "reject"
    hexkey = re.compile(r"[0-9a-fA-F]{64}")
    certifiers = [
        k.strip().lower()
        for k in os.environ.get("ESTATE_SETTLEMENT_CERTIFIERS_HEX", "").split(",")
        if k.strip()
    ]
    worker_key = os.environ.get("ESTATE_WORKER_PUBKEY_HEX", "")
    if not certifiers or not all(hexkey.fullmatch(k) for k in certifiers):
        return "reject"
    if not hexkey.fullmatch(worker_key):
        return "reject"
    pinned_policy = os.environ.get("ESTATE_SETTLEMENT_POLICY_HASH", "")
    policy = claimed.get("policy_hash")
    predicate = claimed.get("acceptance_predicate_hash")
    if not (isinstance(policy, str) and isinstance(predicate, str)):
        return "reject"
    if pinned_policy and policy != pinned_policy:
        return "reject"
    now = int(time.time())
    request = {
        "obligation": {
            "instruction_id": expected.get("instruction_id"),
            "attempt_id": expected.get("run_id"),
            "execution_epoch": expected.get("epoch"),
            "objective_hash": expected.get("goal_sha256"),
            "acceptance_predicate_hash": predicate,
            "policy_hash": policy,
            "verification_deadline_utc": now,
            "worker_pubkey_hex": worker_key,
        },
        "receipt": receipt,
        "trusted_certifiers_hex": certifiers,
        "current_revocation_epoch": expected.get("epoch"),
        "now_utc": now,
    }
    try:
        await asyncio.to_thread(
            rust_gate_bridge.call_rust_gate, "verify-settlement", request
        )
    except Exception as exc:  # noqa: BLE001 - every failure to get an ALLOW is a reject
        activity.logger.warning("rust gate refused settlement: %s", type(exc).__name__)
        return "reject"
    return "allow"


@activity.defn
async def budget_op(inp: dict[str, Any]) -> dict[str, Any]:
    """The one door to the versioned budget row (R29). sqlite here, never
    in workflow.py: a workflow may not touch disk, and the whole point of
    the row is that two concurrent activities contend for it."""
    op = inp["op"]
    session_id = inp["session_id"]
    tokens = int(inp.get("tokens", 0))
    if op == "allocate":
        result = await asyncio.to_thread(budget.allocate, session_id, tokens)
    elif op == "refill":
        result = await asyncio.to_thread(budget.refill, session_id, tokens)
    elif op == "read":
        result = await asyncio.to_thread(budget.read, session_id)
    else:
        result = await asyncio.to_thread(budget.spend, session_id, tokens)
    return budget.as_dict(result)


@activity.defn
async def append_receipt(record: dict[str, Any]) -> dict[str, Any]:
    """`record` may carry a "state" sub-dict (the session's full state at
    receipt time); this activity turns it into a state_hash field before
    handing the line to the signed chain (cp18/cp19). receipts_mod.append()
    is synchronous (open/fcntl.flock/Keychain subprocess) -- off the event
    loop via asyncio.to_thread, same reasoning as notify_change below."""
    record = dict(record)
    state = record.pop("state", None)
    if state is not None:
        record["state_hash"] = hashlib.sha256(config.canonical_json(state)).hexdigest()
    line = await asyncio.to_thread(receipts_mod.append, record)
    # R17: a founder intervention also lands in the append-only
    # transparency log the spec's topology names. The chain is written
    # first and is the source of truth; the mirror failing must never
    # fail the step that produced it.
    try:
        await asyncio.to_thread(interventions_mod.mirror, line)
    except (OSError, interventions_mod.NotAppendOnly) as exc:
        activity.logger.warning(f"append_receipt: intervention mirror failed: {exc}")
    return line


@activity.defn
async def notify_change(state: dict[str, Any]) -> dict[str, int]:
    """Best-effort fan-out to Otto's card and Langfuse. Never raises: a
    down notification channel must never affect session status. Given a
    short start_to_close timeout and no retry (sovereign/config.py
    notify.activity_timeout_s / notify.retry_max_attempts) so a stuck
    notification channel can never hold up the step loop -- a failure here
    is logged, not retried, because the next state change will notify
    again anyway.

    Returns {session_id: line_message_id} when card.on_change sent or
    edited a line message, else {}. card.on_change makes no call back into
    this workflow (see sovereign/otto/card.py's on_change docstring) --
    workflow.py reads this return value and sets its own line_message_id,
    so no activity ever issues a Temporal update against the workflow that
    is still waiting on that same activity to finish."""
    tracing.trace_session(
        state.get("session_id", ""),
        state.get("task", ""),
        state.get("runner", ""),
        state.get("status", ""),
        {"step": state.get("step", 0), "asking": state.get("asking")},
    )
    try:
        from sovereign.otto import card  # type: ignore

        result = await asyncio.to_thread(card.on_change, state)
        return result if isinstance(result, dict) else {}
    except ImportError:
        return {}
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        activity.logger.warning(f"notify_change: otto.card.on_change failed: {exc}")
        return {}
