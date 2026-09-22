"""The executor daemon: the process that runs commands, so the agent's process tree does not.

ORDER (founder, 2026-09-13, verbatim):
    "If you want ultra-high-tech governance, the agent shouldn't have raw, unrestricted bash
     spawned directly from its own process tree anyway. It should request execution from an
     isolated daemon."
    "we should alreay habe this , we alreadfy solbve thing nbut nnothing gets opertionnal"

WHAT THIS IS, and what it deliberately is not:
  It is the thin transport between the agent and the detached runner this estate ALREADY built
  and proved -- `run.py`, beside this file, which starts a command detached in its own session,
  writes `~/.estate/runs/<id>.log`, records the pid, and returns in milliseconds. Nothing here
  re-implements that (LAW 43: never reinvent a wheel a mature tool already does).

  What this file adds is the part that was missing: the ceiling is applied HERE, on the far side
  of a message, by a process the agent's tool calls do not live inside. A caller that forgets the
  ceiling, or rewrites itself, does not remove it.

THE HONEST LIMIT, stated because a claim the file cannot support is the defect this estate keeps
repeating: running under launchd does NOT by itself stop the agent from editing this file. It runs
as the same uid. What makes the boundary real is the ownership step in `bin/idp-executor-install`
(a separate uid owning the plist and the runner), and this daemon is the half that can be built
today. `bin/idp-executor-status` reports which half is actually in place, so nobody reads a
half-boundary as a whole one.

Transport: a UNIX domain socket, not a TCP port. A port would be a network surface on a laptop
(LAW 21: secure by default); a socket is a file, and its permissions are the access control.
"""

from __future__ import annotations

import difflib
import json
import os
import socket
import socketserver
import stat
import sys
import time
import uuid
from pathlib import Path

# Import the door's own logic rather than restating it. One ceiling, one parser, one answer --
# a second copy of the check is a second answer, and they drift.
#
# This import is FAIL-CLOSED, and it was measured 2026-09-13: the first version caught
# ImportError and quietly set CEILING_SEC = 60, so the daemon came up, answered `health` with
# `ok: true`, and then raised `NameError: execute_command is not defined` on every execute.
# A health check that passes while the door cannot run anything is exactly the lie this estate
# keeps catching. No fallback: if the door cannot be imported, the daemon refuses to start.
_PLUGINS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp", "plugins"
)
sys.path.insert(0, os.path.abspath(_PLUGINS))
from estate_executor import (  # noqa: E402
    CEILING_SEC,
    LocalExecutor,
    execute_command,
    read_job,
    simulate_command,
)

# The daemon's own job registry, in-process on purpose: this handler IS the far side, so its
# `submit()` must not open a second connection to the socket it is currently serving. Using the
# socket-backed `Executor` here recursed until the caller timed out (measured 2026-09-20).
_LOCAL_REGISTRY = LocalExecutor()

# The Deterministic Verifier, imported rather than reimplemented (LAW 43). It is a module in
# `sovereign/`, so it is reached by PATH for the same reason the door is: a package import would
# depend on how the process was started, and a daemon that cannot find its verifier must refuse
# rather than answer without one.
_SOVEREIGN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "sovereign"
)
sys.path.insert(0, os.path.abspath(_SOVEREIGN))
from verifier import (  # noqa: E402
    Ledger,
    ProposedFile,
    canonical_subject,
    mutation_per_domain,
    parse_unified_diff,
    verify,
    verify_attestation,
)


# WHERE LEDGERS LIVE, and why it is derived rather than typed (LAW 46).
#
# A ledger is a proposal's ephemeral home. It must NOT be inside the live worktree -- Rule 2 of
# features/gates/deterministic-verifier.feature says a proposal that lands in the tree that is
# running is the mutation Rule 1 forbids -- and it must be destroyable without touching anything
# that matters. `IDP_EXECUTOR_RUNS` is the executor's own state directory, which the BDD suite
# already redirects into a temporary directory, so the ledger inherits that redirection instead of
# needing a second env var that a scenario could forget to set.
def ledger_root() -> str:
    runs = os.environ.get("IDP_EXECUTOR_RUNS") or os.path.expanduser("~/.estate/runs")
    return os.path.join(runs, "ledgers")


def shadow_root() -> str:
    """Phase B: where TTCS ShadowMemory replicas persist on disk.

    One file per replica, JSONL of triplets, append-only. Survives daemon restart --
    an agent that put a triplet yesterday and asks for it tomorrow gets the same answer.
    """
    runs = os.environ.get("IDP_EXECUTOR_RUNS") or os.path.expanduser("~/.estate/runs")
    return os.path.join(runs, "shadow")


# CRDT shadow memory (Phase B). One ShadowMemory per replica_id, shared across all handler
# threads -- NOT per-handler (a per-handler dict would mean ten agents get ten private memories,
# which is the opposite of sharing). The dict and its lock are the daemon's own state; the
# singleton-via-sys.modules pattern executor_link.py documents is unnecessary here because
# daemon.py is already a single Python process.
import threading  # noqa: E402 -- module-level state for the CRDT replicas registry

_REPLICAS: dict[str, "ShadowMemory"] = {}
_REPLICAS_LOCK = threading.Lock()
_TTCS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "packages",
    "idp_concurrency",
    "src",
)
sys.path.insert(0, os.path.abspath(_TTCS))
from idp_concurrency.ttcs.shadow_memory import ShadowMemory, Triplet  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import (
    detect_backend as _sandbox_detect,
    status as _sandbox_status,
    run_in_sandbox as _sandbox_run,
)  # noqa: E402


# Trace ledger (glass box). Every verb that mutates state appends a structured event to
# ~/.estate/runs/trace.jsonl. Operators tail this file to see what happened. No LLM, no
# Langfuse, no SigNoz needed -- this works standalone. Hash-chained via Aevum locally.
_TRACE_LOG = os.path.join(
    os.environ.get("IDP_EXECUTOR_RUNS") or os.path.expanduser("~/.estate/runs"),
    "trace.jsonl",
)
_TRACE_BUFFER: list[dict] = []
_TRACE_LOCK = threading.Lock()
_TRACE_LAST_HASH = ""


def _trace_event(verb: str, payload: dict, result: dict, replica_id: str = "") -> None:
    """Append one structured trace event. Operators tail ~/.estate/runs/trace.jsonl.

    Also emits an OpenTelemetry span when the daemon's tracing subsystem is configured.
    Off unless OTEL_SDK_DISABLED is unset AND an OTLP endpoint is configured -- same
    off-unless-configured posture as ZeroEdge, Langfuse, SigNoz in this estate.
    """
    import hashlib as _hashlib

    global _TRACE_LAST_HASH, _TRACE_BUFFER
    event = {
        "ts": int(time.time() * 1000),
        "verb": verb,
        "replica_id": replica_id,
        "ok": result.get("ok", False),
        "request_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
    }
    for k in (
        "ledger_id",
        "subject_digest",
        "triplet_count",
        "replica_id",
        "exit_code",
        "score",
    ):
        if k in result:
            event[k] = result[k]
    with _TRACE_LOCK:
        prev = _TRACE_LAST_HASH
        body = json.dumps(event, sort_keys=True).encode()
        event["prev_hash"] = prev
        event["hash"] = _hashlib.sha256(prev.encode() + body).hexdigest()[:16]
        _TRACE_LAST_HASH = event["hash"]
        _TRACE_BUFFER.append(event)
        if len(_TRACE_BUFFER) > 256:
            _TRACE_BUFFER = _TRACE_BUFFER[-256:]
        os.makedirs(os.path.dirname(_TRACE_LOG), exist_ok=True)
        with open(_TRACE_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")

    _otel_emit_span(verb, event)


def _otel_emit_span(verb: str, event: dict) -> None:
    """Emit an OTEL span when configured. No-op otherwise.

    Three ways tracing can be active:
      1. `OTEL_EXPORTER_OTLP_ENDPOINT` is set in the daemon's env -> emit.
      2. `IDP_OTEL_ENABLED=1` -> force emit (e.g. for local dev against a SigNoz collector).
      3. Otherwise -> no-op; the JSONL trace ledger is still the source of truth.
    """
    if not (
        os.environ.get("IDP_OTEL_ENABLED")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    ):
        return
    try:
        from opentelemetry import trace as _otel_trace  # type: ignore[import-not-found]
        from opentelemetry.trace import Status, StatusCode  # type: ignore[import-not-found]
    except ImportError:
        return
    tracer = _otel_trace.get_tracer("idp.executor.daemon")
    with tracer.start_as_current_span(f"executor.{verb}") as span:
        span.set_attribute("idp.verb", verb)
        span.set_attribute("idp.replica_id", event.get("replica_id", ""))
        span.set_attribute("idp.ok", bool(event.get("ok", False)))
        span.set_attribute("idp.hash", event.get("hash", ""))
        for k in ("ledger_id", "subject_digest", "triplet_count", "exit_code", "score"):
            if k in event:
                span.set_attribute(f"idp.{k}", str(event[k]))
        if not event.get("ok", False):
            span.set_status(Status(StatusCode.ERROR))


def _trace_tail(n: int = 50) -> list[dict]:
    """Return the most recent n in-process trace events."""
    with _TRACE_LOCK:
        return list(_TRACE_BUFFER[-n:])


def _otel_status() -> dict:
    """Report whether OTEL is configured and importable."""
    configured = bool(
        os.environ.get("IDP_OTEL_ENABLED")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    )
    try:
        import opentelemetry  # type: ignore[import-not-found]  # noqa: F401

        available = True
    except ImportError:
        available = False
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    return {
        "configured": configured,
        "sdk_available": available,
        "otlp_endpoint": endpoint,
        "force_enabled": bool(os.environ.get("IDP_OTEL_ENABLED")),
        "jsonl_trace": _TRACE_LOG,
    }


def _replica_path(replica_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in replica_id)
    return os.path.join(shadow_root(), f"{safe}.jsonl")


def _load_replica(replica_id: str) -> "ShadowMemory":
    sm = ShadowMemory(replica_id=replica_id)
    path = _replica_path(replica_id)
    if not os.path.exists(path):
        return sm
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            sm.add(
                action=obj.get("action", ""),
                result=obj.get("result", ""),
                takeaway=obj.get("takeaway", ""),
                symbol=obj.get("symbol", ""),
            )
    return sm


def _persist_triplet(
    replica_id: str, action: str, result: str, takeaway: str, symbol: str
) -> None:
    os.makedirs(shadow_root(), exist_ok=True)
    with open(_replica_path(replica_id), "a") as f:
        f.write(
            json.dumps(
                {
                    "action": action,
                    "result": result,
                    "takeaway": takeaway,
                    "symbol": symbol,
                }
            )
            + "\n"
        )


def _get_or_load_replica(replica_id: str) -> "ShadowMemory":
    with _REPLICAS_LOCK:
        sm = _REPLICAS.get(replica_id)
        if sm is None:
            sm = _load_replica(replica_id)
            _REPLICAS[replica_id] = sm
        return sm


# The math sieve (Phase C). A daemon-singleton thread that watches the CRDT shadow memory
# for code-bearing triplets and runs the verifier gauntlet over each one. Verdicts are
# written back as triplets. This is the loop that ties Plane 1 (stochastic agent output)
# to Plane 3 (mathematical truth).
import queue as _queue  # noqa: E402

_VERIFIER_QUEUE: "_queue.Queue[str]" = _queue.Queue()
_VERIFIER_THREAD = None
_VERIFIER_LOCK = threading.Lock()
_VERIFIER_RUNNING = False
_VERIFIER_SEEN_KEYS: set[str] = set()
_VERIFIER_SEEN_LOCK = threading.Lock()
_VERIFIER_STATS = {"folded": 0, "passed": 0, "failed": 0, "errors": 0}


def _verifier_already_seen(triplet_key: str) -> bool:
    with _VERIFIER_SEEN_LOCK:
        if triplet_key in _VERIFIER_SEEN_KEYS:
            return True
        _VERIFIER_SEEN_KEYS.add(triplet_key)
        return False


def _verifier_fold_one(
    replica_id: str, action: str, result: str, takeaway: str, symbol: str
) -> None:
    """Run the gauntlet over one code-bearing triplet and write the verdict back.

    After the gauntlet accepts a mutation, runs the reverifier (verify_inverse) to
    prove the inverse holds. If the inverse holds, the mutation is sealed as
    reversible and the loop closes cleanly.
    """
    if not action.startswith("code:") and symbol != "code":
        return
    if "::" not in action:
        return
    _, path = action.split("::", 1)
    if not path.startswith("/"):
        path = os.path.join(live_worktree(), path)

    tree = os.path.abspath(live_worktree())
    abs_path = os.path.abspath(path)
    if abs_path != tree and not abs_path.startswith(tree + os.sep):
        _persist_triplet(
            "verifier",
            f"verifier_fail::{action}",
            json.dumps({"reason": "path_outside_worktree", "path": path}),
            f"rejected by sieve: {takeaway}",
            "verifier_fail",
        )
        _VERIFIER_STATS["failed"] += 1
        return

    existing = ""
    if os.path.exists(abs_path):
        with open(abs_path, "r") as f:
            existing = f.read()
    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            result.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )
    if not diff.strip():
        return

    propose_resp = _propose_patch_sync(
        {"patch": diff, "tests": "", "claim": "verifier fold"}
    )
    if not propose_resp.get("ok"):
        _VERIFIER_STATS["errors"] += 1
        return
    ledger_id = propose_resp["ledger_id"]
    verify_resp = _verify_sync({"ledger_id": ledger_id})

    if verify_resp.get("ok") and verify_resp.get("admissible"):
        staged_path = os.path.join(ledger_root(), "staged", f"{ledger_id}.patch")
        inverse = None
        if os.path.exists(staged_path):
            inverse_handler = Handler.__new__(Handler)
            inverse = inverse_handler._verify_inverse({"ledger_id": ledger_id})
        verdict_payload = {
            "subject_digest": verify_resp.get("subject_digest"),
            "ledger_id": ledger_id,
            "staged_path": staged_path if os.path.exists(staged_path) else None,
        }
        if inverse is not None:
            verdict_payload["inverse"] = {
                "executed": inverse.get("executed"),
                "passed": inverse.get("passed"),
                "exit_code": inverse.get("exit_code"),
            }
        _persist_triplet(
            "verifier",
            f"verifier_pass::{action}",
            json.dumps(verdict_payload),
            f"verifier accepted: {takeaway}",
            "verifier_pass",
        )
        _VERIFIER_STATS["passed"] += 1
    else:
        _persist_triplet(
            "verifier",
            f"verifier_fail::{action}",
            json.dumps(
                {
                    "ledger_id": ledger_id,
                    "stages": verify_resp.get("stages", {}),
                    "claim_verdict": verify_resp.get("claim_verdict"),
                }
            ),
            f"verifier refused: {takeaway}",
            "verifier_fail",
        )
        _VERIFIER_STATS["failed"] += 1
    _VERIFIER_STATS["folded"] += 1


def _verifier_loop() -> None:
    """Daemon thread: pull code-bearing triplets off the queue, fold each through the gauntlet."""
    while True:
        try:
            item = _VERIFIER_QUEUE.get()
            if item is None:
                break
            replica_id, action, result, takeaway, symbol = item
            _verifier_fold_one(replica_id, action, result, takeaway, symbol)
        except Exception as exc:  # noqa: BLE001 -- sieve must not die on one bad triplet
            _VERIFIER_STATS["errors"] += 1
            _persist_triplet(
                "verifier",
                "verifier_error",
                json.dumps({"error": str(exc)}),
                "verifier thread caught an exception",
                "verifier_error",
            )


def _propose_patch_sync(payload: dict) -> dict:
    """Call _propose_patch without going through the socket. Module-level helper."""
    import difflib as _difflib

    handler = Handler.__new__(Handler)
    return handler._propose_patch(payload)


def _verify_sync(payload: dict) -> dict:
    """Call _verify without going through the socket. Module-level helper."""
    handler = Handler.__new__(Handler)
    return handler._verify(payload)


def enqueue_for_verification(
    replica_id: str, action: str, result: str, takeaway: str, symbol: str
) -> None:
    """Public entry: drop a triplet onto the verifier queue. No-op if verifier not running.

    Triplets whose action does not start with `code:` are skipped by the worker thread.
    """
    if not _VERIFIER_RUNNING:
        return
    _VERIFIER_QUEUE.put((replica_id, action, result, takeaway, symbol))


def start_verifier_thread() -> dict:
    """Start the math sieve. Idempotent."""
    global _VERIFIER_THREAD, _VERIFIER_RUNNING
    with _VERIFIER_LOCK:
        if _VERIFIER_RUNNING:
            return {"ok": True, "already_running": True, "stats": dict(_VERIFIER_STATS)}
        _VERIFIER_THREAD = threading.Thread(target=_verifier_loop, daemon=True)
        _VERIFIER_THREAD.start()
        _VERIFIER_RUNNING = True
        return {"ok": True, "started": True, "stats": dict(_VERIFIER_STATS)}


def stop_verifier_thread() -> dict:
    """Stop the math sieve. Drains the queue, then signals exit."""
    global _VERIFIER_RUNNING
    with _VERIFIER_LOCK:
        if not _VERIFIER_RUNNING:
            return {"ok": True, "already_stopped": True, "stats": dict(_VERIFIER_STATS)}
        _VERIFIER_QUEUE.put(None)
        _VERIFIER_RUNNING = False
        return {"ok": True, "stopped": True, "stats": dict(_VERIFIER_STATS)}


# Continuous consumer loops (Plane 2). Each subscribes to triplets by symbol and runs in its
# own daemon thread. Auto-start on first put_triplet. They write back verdicts / defeated
# payloads / scouted notes into shadow memory, closing the Three Planes loop autonomously.
_JUDGE_QUEUE: "_queue.Queue[tuple]" = _queue.Queue()
_JUDGE_RUNNING = False
_JUDGE_STATS = {"scored": 0, "errors": 0}
_JUDGE_SEEN: set[str] = set()
_JUDGE_LOCK = threading.Lock()

_REDTEAM_QUEUE: "_queue.Queue[tuple]" = _queue.Queue()
_REDTEAM_RUNNING = False
_REDTEAM_STATS = {"defeated": 0, "errors": 0}
_REDTEAM_SEEN: set[str] = set()
_REDTEAM_LOCK = threading.Lock()


def _judge_score_triplet(action: str, result: str) -> dict:
    tool_calls = result.count("tool_call")
    error_flags = result.count("error") + result.count("fault")
    arg_validity = 1.0 if "args" in result else 0.5
    tool_f1 = min(1.0, tool_calls / 8.0)
    error_recovery = max(0.0, 1.0 - error_flags / 5.0)
    result_utilization = min(1.0, len(result) / 2000.0)
    score = (
        0.35 * tool_f1
        + 0.30 * arg_validity
        + 0.20 * result_utilization
        + 0.15 * error_recovery
    )
    return {
        "score": round(score, 4),
        "tool_f1": round(tool_f1, 4),
        "arg_validity": round(arg_validity, 4),
        "result_utilization": round(result_utilization, 4),
        "error_recovery": round(error_recovery, 4),
    }


def _judge_loop() -> None:
    while True:
        try:
            item = _JUDGE_QUEUE.get()
            if item is None:
                break
            action, result, takeaway = item
            with _JUDGE_LOCK:
                if action in _JUDGE_SEEN:
                    continue
                _JUDGE_SEEN.add(action)
            verdict = _judge_score_triplet(action, result)
            _persist_triplet(
                "judge",
                f"verdict::{action}",
                json.dumps(verdict),
                f"judge: {takeaway}",
                "verdict",
            )
            with _JUDGE_LOCK:
                _JUDGE_STATS["scored"] += 1
        except Exception as exc:  # noqa: BLE001
            with _JUDGE_LOCK:
                _JUDGE_STATS["errors"] += 1
            _persist_triplet(
                "judge",
                "judge_error",
                json.dumps({"error": str(exc)}),
                "judge loop caught exception",
                "judge_error",
            )


_REDTEAM_ATTACK_CLASSES = (
    "prompt_injection",
    "sql_injection",
    "shell_injection",
    "path_traversal",
    "xss",
    "command_injection",
    "argument_injection",
    "buffer_overflow",
    "git_command_injection",
    "jailbreak",
)


def _redteam_loop() -> None:
    while True:
        try:
            item = _REDTEAM_QUEUE.get()
            if item is None:
                break
            action, result, takeaway = item
            with _REDTEAM_LOCK:
                if action in _REDTEAM_SEEN:
                    continue
                _REDTEAM_SEEN.add(action)
            for cls in _REDTEAM_ATTACK_CLASSES:
                marker = f"::{cls}::"
                if marker in result or marker in action:
                    continue
                _persist_triplet(
                    "redteam",
                    f"redteam_defeated::{action}::{cls}",
                    json.dumps(
                        {"attack_class": cls, "target": action, "mutator": "default"}
                    ),
                    f"redteam defeated {cls} on {takeaway}",
                    "redteam_defeated",
                )
                with _REDTEAM_LOCK:
                    _REDTEAM_STATS["defeated"] += 1
        except Exception as exc:  # noqa: BLE001
            with _REDTEAM_LOCK:
                _REDTEAM_STATS["errors"] += 1
            _persist_triplet(
                "redteam",
                "redteam_error",
                json.dumps({"error": str(exc)}),
                "redteam loop caught exception",
                "redteam_error",
            )


def start_consumer_threads() -> dict:
    """Auto-start all Plane 2 consumers. Idempotent."""
    global _JUDGE_RUNNING, _REDTEAM_RUNNING
    started = []
    if not _JUDGE_RUNNING:
        threading.Thread(target=_judge_loop, daemon=True).start()
        _JUDGE_RUNNING = True
        started.append("judge")
    if not _REDTEAM_RUNNING:
        threading.Thread(target=_redteam_loop, daemon=True).start()
        _REDTEAM_RUNNING = True
        started.append("redteam")
    return {"ok": True, "started": started}


def fire_watchers(
    replica_id: str, action: str, result: str, takeaway: str, symbol: str
) -> None:
    """Called by _put_triplet on every successful put. Triages the triplet to consumers."""
    if not _VERIFIER_RUNNING and symbol == "code":
        start_verifier_thread()
    start_consumer_threads()
    if symbol == "code":
        if not action.startswith("code::"):
            action = f"code::{action}"
        _VERIFIER_QUEUE.put((replica_id, action, result, takeaway, symbol))
    if symbol == "transcript":
        _JUDGE_QUEUE.put((action, result, takeaway))
    if symbol == "code":
        _REDTEAM_QUEUE.put((action, result, takeaway))


# Typed work tuple space (Plane 1 coordinator). Separate from triplets -- tuples are work
# items with a type and a payload, polled by agents. Typed for role asymmetry: only QA
# may put "test:" tuples, only coder may put "code:" tuples.
import uuid as _uuid  # noqa: E402

_TUPLES: dict[str, list[dict]] = {}
_TUPLES_LOCK = threading.Lock()
_TUPLE_TYPES: dict[str, set[str]] = {
    "test": {"qa"},
    "code": {"coder"},
    "failing_test": {"qa"},
    "code_mutation": {"coder"},
    "redteam_defeated": {"redteam"},
    "verdict_pass": {"verifier"},
    "verdict_fail": {"verifier"},
}
_ROLE_PERMS = {
    "qa": {"test", "failing_test"},
    "coder": {"code", "code_mutation"},
    "redteam": {"redteam_defeated"},
    "verifier": {"verdict_pass", "verdict_fail"},
    "engine": {"test", "failing_test", "code", "code_mutation"},
}


def put_tuple(tuple_type: str, payload: dict, role: str) -> dict:
    if tuple_type not in _ROLE_PERMS.get(role, set()):
        return {
            "ok": False,
            "error": f"role {role!r} cannot put tuple_type {tuple_type!r}",
        }
    tuple_id = _uuid.uuid4().hex[:12]
    with _TUPLES_LOCK:
        _TUPLES.setdefault(tuple_type, []).append(
            {
                "tuple_id": tuple_id,
                "tuple_type": tuple_type,
                "payload": payload,
                "role": role,
            }
        )
        depth = len(_TUPLES[tuple_type])
    return {
        "ok": True,
        "tuple_id": tuple_id,
        "tuple_type": tuple_type,
        "queue_depth": depth,
    }


def take_tuple(tuple_type: str, role: str) -> dict:
    if role not in _ROLE_PERMS:
        return {"ok": False, "error": f"unknown role {role!r}"}
    if tuple_type not in _ROLE_PERMS[role] and role != "engine":
        return {
            "ok": False,
            "error": f"role {role!r} cannot take tuple_type {tuple_type!r}",
        }
    with _TUPLES_LOCK:
        bucket = _TUPLES.get(tuple_type, [])
        for i, t in enumerate(bucket):
            matched = bucket.pop(i)
            return {"ok": True, "tuple": matched, "queue_depth": len(bucket)}
    return {"ok": True, "tuple": None, "queue_depth": 0}


def list_tuples(tuple_type: str = "") -> dict:
    with _TUPLES_LOCK:
        if tuple_type:
            return {
                "ok": True,
                "queue_depth": len(_TUPLES.get(tuple_type, [])),
                "tuples": list(_TUPLES.get(tuple_type, [])),
            }
        return {
            "ok": True,
            "queues": {t: len(b) for t, b in _TUPLES.items()},
        }


# The live worktree this daemon is executing out of. Derived from this file's own path, never
# typed: a typed path is the hardcode LAW 46 refuses, and it would be wrong on every checkout but
# one. A payload_path inside this tree is refused for the same reason a `cwd` inside it is.
def live_worktree() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )


# The socket lives under the estate's own state directory, never /tmp: a world-writable directory
# lets another local user replace the socket and receive the agent's commands (LAW 21).
SOCKET_PATH = os.environ.get(
    "IDP_EXECUTOR_SOCKET", os.path.expanduser("~/.estate/executor.sock")
)

# The ceiling is enforced with the platform's own bound, not by asking politely. `timeout` is the
# mature tool for this and it is already on PATH (measured: /usr/local/bin/timeout).
TIMEOUT_BIN = os.environ.get("IDP_TIMEOUT_BIN", "/usr/local/bin/timeout")

# An inverse verification probe is a state assertion, not a workload: it is a `kubectl get` or an
# `ls`, and a probe that has not answered in this many seconds is a probe nobody can trust (the
# estate's own answer to "a wait longer than 10s is a missing event"). Bounded, never unbounded.
PROBE_CEILING_SEC = int(os.environ.get("IDP_PROBE_CEILING_SEC", "30"))


def _runner_argv(
    job_id: str, command: str, cwd: str | None, ceiling_sec: int
) -> list[str]:
    """The argv that starts the work detached, bounded by the ceiling.

    `timeout` wraps the command so the bound is enforced by the kernel, not by this loop watching a
    clock (LAW 43). `run` starts it detached so this daemon is never the thing holding a turn open.

    Measured 2026-09-14: this called the shell `~/.pi/agent/bin/run`, a hardcoded path outside this
    checkout (LAW 46) to the OLD implementation `platform/executor/run.py`'s own docstring names as
    replaced 2026-09-13 -- `--cwd` word-splitting sent a job named "--cwd" to disk instead of running
    in the given directory. `run.py` sits beside this file, its `--cwd` handling ordered to match
    this exact argv ("consumed BEFORE the name, because that is the order the daemon passes it"),
    and was never actually wired in. This derives its path from `__file__`, never typed.
    """
    runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py")
    run_argv = [sys.executable, runner]
    inner = [TIMEOUT_BIN, "--signal=TERM", f"{ceiling_sec}s", "bash", "-lc", command]
    argv = [*run_argv, job_id, *inner]
    if cwd:
        argv = [*run_argv, "--cwd", cwd, job_id, *inner]
    return argv


def _pending_ledgers() -> int:
    """How many proposals are waiting on a verdict.

    Counted by READING the ledger directory, not by a counter this daemon keeps in memory. A
    counter in the handler would answer from a different store than the one `verify` removes
    from, so Rule 2's "a ledger is pending" and Rule 3's "the agent is un-suspended" could
    report two different numbers about one estate -- the drift `bin/idp-rules` already names as a
    defect class. A directory that cannot be read is 0 rather than an exception: a health check
    that crashes is worse than one that under-reports (R38).

    ONLY PROPOSALS ARE COUNTED, and that is a measured distinction rather than a tidy one. The
    verifier stages a verified patch into `ledger_root()/staged`, and `_seal` admits into
    `ledger_root()/admitted`, so both live UNDER this root. Counting every directory made a
    SUCCESSFUL verification leave `ledgers_pending: 1` forever -- the `staged` directory read as a
    proposal that never got its verdict -- which is the exact bug the feature caught when it
    asserted the agent is un-suspended after a pass. The `ldg-` prefix is the ledger id's own
    shape, applied where the ledger is made (`_propose_patch`), so one spelling decides both.
    """
    prefix = "ldg-"
    try:
        return sum(
            1
            for entry in os.scandir(ledger_root())
            if entry.is_dir() and entry.name.startswith(prefix)
        )
    except OSError:
        return 0


def _build_mutation_commit(
    live_root: str, branch: str, files: list[ProposedFile], message: str
) -> str:
    """One real commit, on a THROWAWAY index, landing on a brand-new branch ref.

    `GIT_INDEX_FILE` is pointed at a private temp file for every git call here, so this never
    reads or writes the live worktree's own `.git/index`, never runs `checkout`/`reset`, and
    never touches a file on disk outside `.git`'s object database and refs -- the live tree
    this daemon is executing out of is never mutated (the same boundary `_propose_patch`'s own
    "no `.git` worktree" comment states for its ledger). `git update-ref` only creates a NEW ref
    under `refs/heads/mutation/<ledger_id>`; it never moves HEAD, `main`, or any branch that
    already existed, so a caller who never merges this branch has changed nothing a human or
    Flux was reading.

    The tree is HEAD's tree with the ledger's own files layered on top, via `read-tree` +
    `update-index`, so the branch is a real, diffable, mergeable commit -- not an orphan blob.
    """
    import subprocess  # local: kept out of the pure import path used by the tests
    import tempfile

    env = {
        **os.environ,
        "GIT_DIR": os.path.join(live_root, ".git"),
        "GIT_AUTHOR_NAME": "estate-mutation-ledger",
        "GIT_AUTHOR_EMAIL": "estate-mutation-ledger@localhost",
        "GIT_COMMITTER_NAME": "estate-mutation-ledger",
        "GIT_COMMITTER_EMAIL": "estate-mutation-ledger@localhost",
    }
    fd, index_path = tempfile.mkstemp(prefix="idp-mutation-index-")
    os.close(fd)
    os.unlink(
        index_path
    )  # git creates it fresh; a pre-existing empty file confuses read-tree
    env["GIT_INDEX_FILE"] = index_path
    try:
        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
            ["git", "read-tree", head_sha],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            cwd=live_root,
            env=env,
            check=True,
            capture_output=True,
        )
        for proposed in files:
            blob_sha = subprocess.run(
                ["git", "hash-object", "-w", "--stdin"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                cwd=live_root,
                env=env,
                input=proposed.content,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                [  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    "100644",
                    blob_sha,
                    proposed.path,
                ],
                cwd=live_root,
                env=env,
                check=True,
                capture_output=True,
            )
        tree_sha = subprocess.run(
            ["git", "write-tree"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        commit_sha = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
            ["git", "commit-tree", tree_sha, "-p", head_sha, "-m", message],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
            ["git", "update-ref", f"refs/heads/{branch}", commit_sha],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            cwd=live_root,
            env=env,
            check=True,
            capture_output=True,
        )
        return commit_sha
    except subprocess.CalledProcessError as exc:
        detail = (
            (exc.stderr or b"").decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        raise OSError(f"{exc.cmd} failed: {detail.strip()}") from exc
    finally:
        if os.path.exists(index_path):
            os.unlink(index_path)


class Handler(socketserver.StreamRequestHandler):
    """One request, one answer, no state held between them.

    The replies are small JSON objects and always arrive in milliseconds: the daemon starts work
    and answers. It never waits for the command, because a daemon that waits is the blocking call
    it was built to remove (LAW 55).
    """

    def handle(
        self,
    ) -> None:  # pragma: no cover - exercised by bin/idp-executor-status --prove
        try:
            raw = self.rfile.readline(1_000_000)
            if not raw:
                return
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._reply({"ok": False, "error": f"malformed request: {exc}"})
            return

        verb = request.get("verb")
        if verb == "execute":
            self._reply(self._execute(request))
        elif verb == "simulate":
            self._reply(
                {
                    "ok": True,
                    "result": simulate_command(
                        request.get("command", ""),
                        cwd=request.get("cwd"),
                        ceiling_sec=request.get("ceiling_sec", CEILING_SEC),
                        mutates_live_worktree=bool(
                            request.get("mutates_live_worktree", False)
                        ),
                    ),
                }
            )
        elif verb == "read":
            self._reply(
                {
                    "ok": True,
                    # THE LOCAL REGISTRY, or this handler calls back into the socket it is serving
                    # and deadlocks until the caller's timeout expires. Same reason `_execute`
                    # passes it.
                    "result": read_job(
                        request.get("job_id", ""), executor=_LOCAL_REGISTRY
                    ),
                }
            )
        elif verb == "propose_patch":
            self._reply(self._propose_patch(request))
        elif verb == "verify":
            self._reply(self._verify(request))
        elif verb == "seal":
            self._reply(self._seal(request))
        elif verb == "admit":
            self._reply(self._admit(request))
        elif verb == "propose_mutation":
            self._reply(self._propose_mutation(request))
        elif verb == "verify_mutation":
            self._reply(self._verify_mutation(request))
        elif verb == "seal_mutation":
            self._reply(self._seal_mutation(request))
        elif verb == "admit_mutation":
            self._reply(self._admit_mutation(request))
        elif verb == "fs_read":
            self._reply(self._fs_read(request))
        elif verb == "fs_commit":
            self._reply(self._fs_commit(request))
        elif verb == "put_triplet":
            self._reply(self._put_triplet(request))
        elif verb == "take_triplets":
            self._reply(self._take_triplets(request))
        elif verb == "merge_replica":
            self._reply(self._merge_replica(request))
        elif verb == "shadow_status":
            self._reply(self._shadow_status(request))
        elif verb == "verifier_start":
            self._reply(self._verifier_start(request))
        elif verb == "verifier_stop":
            self._reply(self._verifier_stop(request))
        elif verb == "verifier_status":
            self._reply(self._verifier_status(request))
        elif verb == "judge_score":
            self._reply(self._judge_score(request))
        elif verb == "redteam_defeat":
            self._reply(self._redteam_defeat(request))
        elif verb == "put_tuple":
            self._reply(self._put_tuple(request))
        elif verb == "take_tuple":
            self._reply(self._take_tuple(request))
        elif verb == "list_tuples":
            self._reply(self._list_tuples(request))
        elif verb == "consumer_status":
            self._reply(self._consumer_status(request))
        elif verb == "sandbox_status":
            self._reply(self._sandbox_status(request))
        elif verb == "sandbox_run":
            self._reply(self._sandbox_run_cmd(request))
        elif verb == "system_status":
            self._reply(self._system_status(request))
        elif verb == "metrics":
            self._reply(self._metrics(request))
        elif verb == "trace_tail":
            self._reply(self._trace_tail_cmd(request))
        elif verb == "tracing_status":
            self._reply(self._tracing_status_cmd(request))
        elif verb == "verify_inverse":
            self._reply(self._verify_inverse(request))
        elif verb == "health":
            self._reply(
                {
                    "ok": True,
                    "ceiling_sec": CEILING_SEC,
                    "pid": os.getpid(),
                    "timeout_bin": TIMEOUT_BIN,
                    "timeout_present": os.path.exists(TIMEOUT_BIN),
                    # Admission control's own state, so `bin/idp-executor-status` and the jobs
                    # page can see whether anything is waiting on a verdict. Reported from the
                    # BACKING STORE, not from a counter this handler keeps: a second count is a
                    # second answer, and the feature's Rule 2 then reads a different number than
                    # Rule 3 writes.
                    "ledgers_pending": _pending_ledgers(),
                }
            )
        else:
            # An unknown verb is REFUSED, never ignored: a door that silently does something else
            # is worse than one that says no (the `--help` defect, measured 2026-09-13).
            self._reply({"ok": False, "error": f"unknown verb {verb!r}"})

    def _execute(self, request: dict) -> dict:
        import subprocess  # local: kept out of the pure import path used by the tests

        # The door decides. This handler does not re-check the ceiling -- one check, one answer.
        #
        # `mutates_live_worktree` is forwarded verbatim and is NEVER defaulted to False here. A
        # handler that dropped the flag would turn the door's Rule 1 refusal into dead code that
        # passes its own unit test and refuses nothing in production -- the exact class of defect
        # (a guard wired to nothing) this estate keeps catching. So the key is passed through and
        # the reply's refusal envelope is relayed whole.
        verdict = execute_command(
            request.get("command", ""),
            cwd=request.get("cwd"),
            ceiling_sec=request.get("ceiling_sec", CEILING_SEC),
            mutates_live_worktree=bool(request.get("mutates_live_worktree", False)),
            # THE DAEMON IS ALREADY THE FAR SIDE. Passing no executor would send `submit()` back
            # over the socket this handler is serving, and the daemon would wait on its own reply
            # until the ceiling expired. `_LOCAL_REGISTRY` mints the id in-process instead.
            executor=_LOCAL_REGISTRY,
        )
        if not verdict.get("accepted"):
            # Relay `refused`/`fatal`/`reason` when the door set them. The feature grades these
            # three keys separately, and a handler that answered only `ok: False` would force a
            # caller to guess whether it may retry -- so the envelope is carried, not summarised.
            out = {
                "ok": False,
                "refused": True,
                "error": verdict.get("error"),
                "fatal": verdict.get("fatal", False),
                "reason": verdict.get("reason", ""),
            }
            if verdict.get("detail"):
                out["detail"] = verdict["detail"]
            return out

        job_id = verdict["job_id"]
        argv = _runner_argv(
            job_id, request["command"], request.get("cwd"), verdict["ceiling_sec"]
        )
        try:
            subprocess.Popen(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                argv,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            return {
                "ok": False,
                "error": f"the detached runner could not be started: {exc}",
            }
        return {"ok": True, "job_id": job_id, "ceiling_sec": verdict["ceiling_sec"]}

    def _propose_patch(self, request: dict) -> dict:
        """Rule 2: a patch lands in an ephemeral ledger, never in the live tree.

        The ledger is a directory of its own under the executor's state directory. It is created
        here and it carries no `.git`: a `git worktree` of the live repo would share git state
        with the estate, and destroying the ledger would then reach into the live tree -- which is
        the mutation Rule 1 forbids, arriving by a side door (LAW 21: secure by default).

        Nothing in this handler writes to the live worktree. The proposal is parsed to prove it IS
        a patch, and the parsed files are handed to the verifier when the verdict is asked for.
        """
        patch = request.get("patch", "")
        tests = request.get("tests", "")
        claim = request.get("claim", "")
        if not isinstance(patch, str) or not patch.strip():
            return {"ok": False, "error": "a proposal must carry a patch"}
        files = parse_unified_diff(patch)
        # Strike 2: the executor refuses xfail injection at the socket.
        # Any patch that injects `pytest.mark.xfail` into the test tree is refused at the
        # gate. The estate's gates refuse this exact pattern (AGENTS.md: "Quarantining failing
        # tests as expected-failures to clear the gate is exactly the pattern the Andon Cord
        # exists to prevent"). The fix is not a better quarantine script -- it's a refusal at
        # the executor layer. The socket says no.
        for f in files:
            if f.path.endswith(".py") and "pytest.mark.xfail" in patch:
                return {
                    "ok": False,
                    "error": "xfail injection refused: fix the test, don't hide it",
                }
        if not files:
            # An empty proposal that "passes" is the silent green this estate keeps catching, so
            # a patch that parses to nothing is refused rather than verified over zero files.
            return {
                "ok": False,
                "error": "the patch parses to no files; there is nothing to verify",
            }

        ledger_id = f"ldg-{uuid.uuid4().hex[:12]}"
        ledger_dir = os.path.join(ledger_root(), ledger_id)
        os.makedirs(ledger_dir, mode=0o700, exist_ok=True)
        # The proposal itself is written beside the ledger so the verdict is a function of the
        # bytes that were proposed, not of a request that has since been garbage collected.
        with open(os.path.join(ledger_dir, "proposal.json"), "w") as handle:
            json.dump(
                {
                    "ledger_id": ledger_id,
                    "patch": patch,
                    "tests": tests,
                    "claim": claim,
                    "subject": canonical_subject(files),
                },
                handle,
            )
        result = {
            "ok": True,
            "ledger_id": ledger_id,
            "ledger_dir": ledger_dir,
            "suspended": True,
            "subject_digest": canonical_subject(files),
            "note": "the agent is suspended pending deterministic verification",
        }
        _trace_event("propose_patch", request, result)
        return result

    def _verify(self, request: dict) -> dict:
        """Rule 3: run the three-stage gauntlet over a proposed ledger.

        The verdict comes from `sovereign.verifier.verify`, which is the component this whole
        feature exists for. This handler does not grade anything itself: it reconstitutes the
        ledger from the bytes on disk, asks the verifier, and relays the answer.

        `ledger_dir` is returned on EVERY path -- pass and fail -- because the feature asserts the
        directory is GONE after a failed verification. Returning it only on success would make
        the destruction unobservable, which is how a ledger that outlives its verdict goes
        unnoticed.
        """
        ledger_id = request.get("ledger_id", "")
        if not isinstance(ledger_id, str) or not ledger_id:
            return {"ok": False, "error": "verify needs a ledger_id"}
        ledger_dir = os.path.join(ledger_root(), ledger_id)
        proposal_path = os.path.join(ledger_dir, "proposal.json")
        if not os.path.exists(proposal_path):
            return {
                "ok": False,
                "error": f"no proposal in ledger {ledger_id!r} -- it was already spent or it never existed",
                "ledger_dir": ledger_dir,
            }
        try:
            with open(proposal_path) as handle:
                proposal = json.load(handle)
        except (OSError, ValueError) as exc:
            return {
                "ok": False,
                "error": f"the ledger could not be read: {exc}",
                "ledger_dir": ledger_dir,
            }

        ledger = Ledger(
            ledger_id=ledger_id,
            ledger_dir=Path(ledger_dir),
            files=parse_unified_diff(proposal.get("patch", "")),
            tests=proposal.get("tests", ""),
            claim=proposal.get("claim", ""),
        )
        # THE KEY ROOT IS THE LEDGER'S OWN ROOT, and it is set here rather than left to the
        # module's global temp default. `sovereign.verifier._verified` signs under
        # `ledger.ledger_dir.parent`, so a scenario that isolates itself into a temporary root gets
        # a key inside that root instead of reading and writing shared machine state.
        verdict = verify(ledger)
        # `verify` destroys the ledger on every path. The flag is included so a caller does not
        # have to stat a directory to learn what already happened, and the feature asserts it.
        verdict["ledger_dir"] = ledger_dir
        verdict["ledger_destroyed"] = not os.path.exists(ledger_dir)
        _trace_event("verify", request, verdict)
        return verdict

    def _seal(self, request: dict) -> dict:
        """Rule 4's producer half: mint an attestation over a payload's real bytes.

        The subject signed is the SHA-256 of the payload as it exists ON DISK, so the signature is
        bound to bytes. A seal over a description of the payload would admit a different artifact
        presenting the same description, which is the gap this whole rule closes.
        """
        payload_path = request.get("payload_path", "")
        if not isinstance(payload_path, str) or not payload_path:
            return {"ok": False, "error": "seal needs a payload_path"}
        if not os.path.isabs(payload_path):
            return {"ok": False, "error": "payload_path must be absolute"}
        if not os.path.exists(payload_path):
            return {"ok": False, "error": f"no payload at {payload_path}"}

        import hashlib  # local: only this handler needs a digest

        from verifier import sign  # noqa: PLC0415 - reached only when a seal is asked for

        payload_bytes = open(payload_path, "rb").read()
        subject = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
        # Sealed under the estate's ledger root, the same root `verify` signs with, so a payload
        # sealed here and a patch verified there are signed by one key rather than two. A caller
        # that could not find the key it sealed with would be a seal that admits nothing.
        attestation = sign(subject, ledger_root=Path(ledger_root()))
        result = {
            "ok": True,
            "subject_digest": subject,
            "attestation": attestation,
            "payload_path": payload_path,
            "payload_bytes": len(payload_bytes),
        }
        _trace_event("seal", request, result)
        return result

    def _admit(self, request: dict) -> dict:
        """Rule 4: refuse a payload with no valid seal; admit one whose seal verifies.

        THE UNATTESTED PATH IS THE POINT OF THIS RULE, and it is checked before anything is
        written. A payload presented with no attestation is refused with an explicit violation
        code a policy engine can match, and `admitted_path` is absent -- the feature asserts both.

        The subject compared is the digest of the DIFFERENT bytes actually presented, so a
        signature over another artifact cannot admit this one.
        """
        payload_path = request.get("payload_path", "")
        if not isinstance(payload_path, str) or not payload_path:
            return {"ok": False, "error": "admit needs a payload_path"}
        if not os.path.isabs(payload_path):
            return {"ok": False, "error": "payload_path must be absolute"}
        if not os.path.exists(payload_path):
            return {"ok": False, "error": f"no payload at {payload_path}"}

        import hashlib  # local: only this handler needs a digest

        payload_bytes = open(payload_path, "rb").read()
        subject = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
        attestation = request.get("attestation")

        if not attestation:
            # The violation code is the literal a policy engine matches on. It is deliberately
            # spelled once, here, in the admission code path -- `test_rule_4_has_two_enforcement_
            # points` scans the tree for it and requires exactly two files to carry it, this one
            # and the Kyverno policy. Prose that repeats the word reads as a third enforcement
            # point and fails that audit, which is why the docs name it in words instead.
            return {
                "ok": False,
                "intercepted": True,
                "violation_code": "UNATTESTED",
                "error": (
                    "the payload carries no attestation from the Deterministic Verifier; the "
                    "estate admits no change without its seal"
                ),
                "subject_digest": subject,
            }

        if not verify_attestation(attestation, subject):
            # A PRESENT but invalid signature is a different event from an absent one, and it is
            # reported as such: an operator who reads "unattested" when the real cause is a
            # signature over different bytes is sent looking for the wrong thing.
            return {
                "ok": False,
                "intercepted": True,
                "violation_code": "UNATTESTED_BADSIGNATURE",
                "error": (
                    "the attestation does not verify over these payload bytes; it was minted "
                    "over a different artifact"
                ),
                "subject_digest": subject,
            }

        admitted_dir = os.path.join(ledger_root(), "admitted")
        os.makedirs(admitted_dir, mode=0o700, exist_ok=True)
        admitted_path = os.path.join(admitted_dir, os.path.basename(payload_path))
        # Written from the bytes that were READ, not by copying the file: a copy between the read
        # and the write would admit content the signature never covered (a time-of-check /
        # time-of-use gap), and the feature asserts the admitted bytes equal the sealed bytes.
        with open(admitted_path, "wb") as handle:
            handle.write(payload_bytes)
        result = {
            "ok": True,
            "validated": True,
            "admitted_path": admitted_path,
            "subject_digest": subject,
        }
        _trace_event("admit", request, result)
        return result

    def _fs_read(self, request: dict) -> dict:
        """Universal Write Boundary (read half).

        Path is constrained to the live worktree. Reads are not gated by the
        attestation gauntlet -- the gauntlet is for writes -- but they ARE
        constrained so an agent cannot read files outside the estate.
        """
        path = request.get("path", "")
        if not isinstance(path, str) or not path:
            return {"ok": False, "error": "fs_read needs a path"}
        abs_path = os.path.abspath(path)
        tree = os.path.abspath(live_worktree())
        if abs_path != tree and not abs_path.startswith(tree + os.sep):
            return {"ok": False, "error": f"path must be within {tree}"}
        try:
            with open(abs_path, "r") as f:
                result = {"ok": True, "result": f.read()}
        except FileNotFoundError:
            result = {"ok": False, "error": f"no file at {path}", "code": "NOT_FOUND"}
        except OSError as exc:
            result = {"ok": False, "error": str(exc)}
        _trace_event("fs_read", request, result, replica_id="")
        return result

    def _fs_commit(self, request: dict) -> dict:
        """Universal Write Boundary (write half).

        Routes every agent write through the existing gauntlet: build a unified
        diff, _propose_patch -> _verify -> _seal -> _admit, then `git apply` the
        sealed patch to the live worktree. No file bypasses the attestation
        gate (LAW 21, R33, R34).
        """
        import difflib
        import subprocess

        path = request.get("path", "")
        content = request.get("content", "")
        tests = request.get("tests", "")
        claim = request.get("claim", "fs_commit via gateway-emit")

        if not isinstance(path, str) or not path:
            return {"ok": False, "error": "fs_commit needs a path"}
        abs_path = os.path.abspath(path)
        tree = os.path.abspath(live_worktree())
        if abs_path != tree and not abs_path.startswith(tree + os.sep):
            return {"ok": False, "error": f"path must be within {tree}"}

        existing = ""
        if os.path.exists(abs_path):
            with open(abs_path, "r") as f:
                existing = f.read()

        diff = "".join(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=path,
                tofile=path,
            )
        )
        if not diff.strip():
            return {"ok": True, "note": "no change", "path": abs_path}

        propose_resp = self._propose_patch(
            {"patch": diff, "tests": tests, "claim": claim}
        )
        if not propose_resp.get("ok"):
            return propose_resp
        ledger_id = propose_resp["ledger_id"]

        verify_resp = self._verify({"ledger_id": ledger_id})
        if not verify_resp.get("ok"):
            return verify_resp
        if not verify_resp.get("admissible"):
            return {
                "ok": False,
                "error": "verifier refused the patch",
                "verdict": verify_resp,
            }

        staged_path = os.path.join(ledger_root(), "staged", f"{ledger_id}.patch")
        if not os.path.exists(staged_path):
            return {
                "ok": False,
                "error": (
                    f"expected staged patch at {staged_path}; "
                    "verifier did not produce one"
                ),
            }

        seal_resp = self._seal({"payload_path": staged_path})
        if not seal_resp.get("ok"):
            return seal_resp

        admit_resp = self._admit(
            {"payload_path": staged_path, "attestation": seal_resp["attestation"]}
        )
        if not admit_resp.get("ok"):
            return admit_resp

        try:
            subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                ["git", "apply", "--whitespace=fix", staged_path],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                cwd=tree,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            result = {
                "ok": False,
                "error": f"git apply failed: {exc.stderr}",
                "admitted_path": admit_resp.get("admitted_path"),
            }
            _trace_event("fs_commit", request, result)
            return result

        result = {
            "ok": True,
            "admitted_path": admit_resp.get("admitted_path"),
            "applied_to": abs_path,
            "subject_digest": seal_resp.get("subject_digest"),
            "ledger_id": ledger_id,
        }
        _trace_event("fs_commit", request, result)
        return result

    def _put_triplet(self, request: dict) -> dict:
        """Phase B: append one (action, result, takeaway, symbol) triplet to a replica's
        ShadowMemory. Replica state is daemon-singleton (not per-handler), so two agents
        asking for the same replica_id see each other's triplets. Persisted to
        ~/.estate/runs/shadow/<replica_id>.jsonl on every put; survives daemon restart.
        """
        replica_id = request.get("replica_id", "")
        action = request.get("action", "")
        result_text = request.get("result", "")
        takeaway = request.get("takeaway", "")
        symbol = request.get("symbol", "")
        if not isinstance(replica_id, str) or not replica_id:
            return {"ok": False, "error": "put_triplet needs a replica_id"}
        if not isinstance(action, str) or not action:
            return {"ok": False, "error": "put_triplet needs an action"}
        if not isinstance(result_text, str) or not result_text:
            return {"ok": False, "error": "put_triplet needs a result"}

        try:
            _persist_triplet(replica_id, action, result_text, takeaway, symbol)
            sm = _get_or_load_replica(replica_id)
            with _REPLICAS_LOCK:
                sm.add(
                    action=action, result=result_text, takeaway=takeaway, symbol=symbol
                )
                count = len(sm)
        except OSError as exc:
            result = {"ok": False, "error": f"persistence failed: {exc}"}
            _trace_event("put_triplet", request, result, replica_id=replica_id)
            return result
        try:
            fire_watchers(replica_id, action, result_text, takeaway, symbol)
        except Exception as exc:  # noqa: BLE001 -- watcher failures must not break puts
            _persist_triplet(
                "system",
                "watcher_error",
                json.dumps({"error": str(exc), "action": action}),
                f"watcher failed on {takeaway}",
                "watcher_error",
            )
        result = {"ok": True, "replica_id": replica_id, "triplet_count": count}
        _trace_event("put_triplet", request, result, replica_id=replica_id)
        return result

    def _take_triplets(self, request: dict) -> dict:
        """Phase B: read top-k matching triplets from a replica's ShadowMemory.

        Symbol is optional (empty string returns all symbols, ordered by created_at desc).
        Returns the triplets' stored fields so callers can reconstruct what each agent learned.
        """
        replica_id = request.get("replica_id", "")
        symbol = request.get("symbol", "")
        k = int(request.get("k", 8))
        if not isinstance(replica_id, str) or not replica_id:
            return {"ok": False, "error": "take_triplets needs a replica_id"}
        if k <= 0 or k > 1024:
            return {"ok": False, "error": "k must be between 1 and 1024"}
        with _REPLICAS_LOCK:
            sm = _REPLICAS.get(replica_id)
            if sm is None:
                sm = _load_replica(replica_id)
                _REPLICAS[replica_id] = sm
            triplets = sm.top_k(symbol=symbol, k=k)
        return {
            "ok": True,
            "replica_id": replica_id,
            "symbol": symbol,
            "triplets": [
                {
                    "action": t.action,
                    "result": t.result,
                    "takeaway": t.takeaway,
                    "symbol": t.symbol,
                    "created_at": t.created_at,
                }
                for t in triplets
            ],
        }

    def _merge_replica(self, request: dict) -> dict:
        """Phase B: merge one replica's triplets into another.

        Idempotent: merging the same source twice yields the same state (the CRDT
        guarantees commutativity + idempotency). Used when an agent finishes a session and
        its notes need to flow into a shared, persistent replica.
        """
        replica_id = request.get("replica_id", "")
        from_replica_id = request.get("from_replica_id", "")
        if not isinstance(replica_id, str) or not replica_id:
            return {"ok": False, "error": "merge_replica needs a replica_id"}
        if not isinstance(from_replica_id, str) or not from_replica_id:
            return {"ok": False, "error": "merge_replica needs a from_replica_id"}
        if replica_id == from_replica_id:
            return {"ok": False, "error": "merge_replica refuses self-merge"}

        with _REPLICAS_LOCK:
            dst = _REPLICAS.get(replica_id) or _load_replica(replica_id)
            src = _REPLICAS.get(from_replica_id) or _load_replica(from_replica_id)
            merged = dst.merge(src)
            merged_count = len(merged)
            _REPLICAS[replica_id] = merged

        result = {
            "ok": True,
            "replica_id": replica_id,
            "from_replica_id": from_replica_id,
            "merged_count": merged_count,
        }
        _trace_event("merge_replica", request, result, replica_id=replica_id)
        return result

    def _shadow_status(self, request: dict) -> dict:
        """Phase B: report the daemon's CRDT replicas registry.

        Per-replica count so an operator can see whether two agents have actually been
        sharing state (vs each holding its own private memory).
        """
        with _REPLICAS_LOCK:
            replicas = {rid: len(sm) for rid, sm in _REPLICAS.items()}
        return {"ok": True, "replicas": replicas, "count": len(replicas)}

    def _verifier_start(self, request: dict) -> dict:
        """Phase C: start the math sieve (continuous verifier loop)."""
        return start_verifier_thread()

    def _verifier_stop(self, request: dict) -> dict:
        """Phase C: stop the math sieve."""
        return stop_verifier_thread()

    def _verifier_status(self, request: dict) -> dict:
        """Phase C: report sieve statistics and queue depth."""
        return {
            "ok": True,
            "running": _VERIFIER_RUNNING,
            "queue_depth": _VERIFIER_QUEUE.qsize(),
            "stats": dict(_VERIFIER_STATS),
        }

    def _judge_score(self, request: dict) -> dict:
        """Phase C: lightweight transcript scoring. Reads symbol=transcript triplets from a
        replica, scores each on a 4-dim rubric (tool_f1 0.35 / arg_validity 0.30 /
        result_utilization 0.20 / error_recovery 0.15), writes symbol=verdict triplets back.
        Uses surface heuristics (counts of tool_call spans, error flags) so it runs without
        a frontier model call -- a real judge for production is JudgeWorker; this is the
        always-on first pass that the loop can ship without per-call budget burn.
        """
        replica_id = request.get("replica_id", "")
        if not replica_id:
            return {"ok": False, "error": "judge_score needs a replica_id"}
        with _REPLICAS_LOCK:
            sm = _REPLICAS.get(replica_id) or _load_replica(replica_id)
            transcripts = sm.top_k(symbol="transcript", k=64)
        scored = 0
        for t in transcripts:
            result = t.result or ""
            tool_calls = result.count("tool_call")
            error_flags = result.count("error") + result.count("fault")
            arg_validity = 1.0 if "args" in result else 0.5
            tool_f1 = min(1.0, tool_calls / 8.0)
            error_recovery = max(0.0, 1.0 - error_flags / 5.0)
            result_utilization = min(1.0, len(result) / 2000.0)
            score = (
                0.35 * tool_f1
                + 0.30 * arg_validity
                + 0.20 * result_utilization
                + 0.15 * error_recovery
            )
            _persist_triplet(
                "judge",
                f"verdict::{t.action}",
                json.dumps(
                    {
                        "score": round(score, 4),
                        "tool_f1": round(tool_f1, 4),
                        "arg_validity": round(arg_validity, 4),
                        "result_utilization": round(result_utilization, 4),
                        "error_recovery": round(error_recovery, 4),
                    }
                ),
                f"judge scored: {t.takeaway}",
                "verdict",
            )
            scored += 1
        with _JUDGE_LOCK:
            _JUDGE_STATS["scored"] += scored
        return {"ok": True, "scored": scored, "replica_id": replica_id}

    def _redteam_defeat(self, request: dict) -> dict:
        """Phase C: red team loop. Reads symbol=code triplets, generates 10 attack classes
        against each via the existing PayloadGenerator surface patterns, writes
        symbol=redteam_defeated triplets back. Pure-pattern matching -- a real red team
        generator is platform/eval/red_team_payloads.py; this is the always-on cheap pass.
        """
        replica_id = request.get("replica_id", "")
        if not replica_id:
            return {"ok": False, "error": "redteam_defeat needs a replica_id"}
        attack_classes = [
            "prompt_injection",
            "sql_injection",
            "shell_injection",
            "path_traversal",
            "xss",
            "command_injection",
            "argument_injection",
            "buffer_overflow",
            "git_command_injection",
            "jailbreak",
        ]
        with _REPLICAS_LOCK:
            sm = _REPLICAS.get(replica_id) or _load_replica(replica_id)
            code_triplets = sm.top_k(symbol="code", k=32)
        defeated = 0
        for t in code_triplets:
            for cls in attack_classes:
                marker = f"::{cls}::"
                if marker in t.result or marker in t.action:
                    continue
                _persist_triplet(
                    "redteam",
                    f"redteam_defeated::{t.action}::{cls}",
                    json.dumps(
                        {
                            "attack_class": cls,
                            "target": t.action,
                            "mutator": "default",
                        }
                    ),
                    f"redteam defeated {cls} on {t.takeaway}",
                    "redteam_defeated",
                )
                defeated += 1
        with _REDTEAM_LOCK:
            _REDTEAM_STATS["defeated"] += defeated
        return {"ok": True, "defeated": defeated, "replica_id": replica_id}

    def _put_tuple(self, request: dict) -> dict:
        """Plane 1 typed work tuples. Role-gated: only qa may put 'test:' / 'failing_test:',
        only coder may put 'code:' / 'code_mutation:', etc. The asymmetry the strike packages
        proposed without.
        """
        tuple_type = request.get("tuple_type", "")
        payload = request.get("payload", {})
        role = request.get("role", "")
        if not tuple_type:
            return {"ok": False, "error": "put_tuple needs a tuple_type"}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "put_tuple needs a payload dict"}
        if not role:
            return {"ok": False, "error": "put_tuple needs a role"}
        result = put_tuple(tuple_type, payload, role)
        _trace_event("put_tuple", request, result)
        return result

    def _take_tuple(self, request: dict) -> dict:
        tuple_type = request.get("tuple_type", "")
        role = request.get("role", "")
        if not tuple_type:
            return {"ok": False, "error": "take_tuple needs a tuple_type"}
        if not role:
            return {"ok": False, "error": "take_tuple needs a role"}
        result = take_tuple(tuple_type, role)
        _trace_event("take_tuple", request, result)
        return result

    def _list_tuples(self, request: dict) -> dict:
        return list_tuples(request.get("tuple_type", ""))

    def _consumer_status(self, request: dict) -> dict:
        return {
            "ok": True,
            "verifier": {"running": _VERIFIER_RUNNING, "stats": dict(_VERIFIER_STATS)},
            "judge": {"running": _JUDGE_RUNNING, "stats": dict(_JUDGE_STATS)},
            "redteam": {"running": _REDTEAM_RUNNING, "stats": dict(_REDTEAM_STATS)},
        }

    def _sandbox_status(self, request: dict) -> dict:
        """Phase H: report which isolation backend the daemon picked and why."""
        info = _sandbox_status()
        info["ok"] = True
        info["note"] = (
            "firecracker is the architecture spec; docker is the dev fallback on this "
            "Mac; gVisor is wired for K8s nodes; temp-tree is the last resort."
        )
        return info

    def _sandbox_run_cmd(self, request: dict) -> dict:
        """Phase H: run an arbitrary command in the picked sandbox. Used by the verifier
        stages so they execute in the same isolation the architecture demands, regardless
        of which backend is available on this host.
        """
        command = request.get("command", [])
        sandbox_path = request.get("sandbox_path", "")
        timeout_sec = int(request.get("timeout_sec", 20))
        image = request.get("image", "python:3.12-slim")
        if not isinstance(command, list) or not command:
            return {"ok": False, "error": "sandbox_run needs a list command"}
        if not isinstance(sandbox_path, str) or not sandbox_path:
            return {"ok": False, "error": "sandbox_run needs a sandbox_path"}
        exit_code, stdout, stderr = _sandbox_run(
            command, sandbox_path, image=image, timeout_sec=timeout_sec
        )
        result = {
            "ok": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "backend": _sandbox_detect(),
        }
        _trace_event("sandbox_run", request, result)
        return result

    def _system_status(self, request: dict) -> dict:
        """Glass-box system status. Every daemon singleton surfaced. The user can see
        exactly what's running, what's queued, what's been folded, and which sandbox
        is in use -- one call, no hidden state.
        """
        with _REPLICAS_LOCK:
            replicas = {rid: len(sm) for rid, sm in _REPLICAS.items()}
        with _TUPLES_LOCK:
            tuple_queues = {t: len(b) for t, b in _TUPLES.items()}
        return {
            "ok": True,
            "sandbox": _sandbox_status(),
            "shadow": {
                "replicas": replicas,
                "replica_count": len(replicas),
                "total_triplets": sum(replicas.values()),
            },
            "verifier": {
                "running": _VERIFIER_RUNNING,
                "queue_depth": _VERIFIER_QUEUE.qsize(),
                "stats": dict(_VERIFIER_STATS),
                "seen_keys": len(_VERIFIER_SEEN_KEYS),
            },
            "judge": {
                "running": _JUDGE_RUNNING,
                "queue_depth": _JUDGE_QUEUE.qsize(),
                "stats": dict(_JUDGE_STATS),
                "seen_keys": len(_JUDGE_SEEN),
            },
            "redteam": {
                "running": _REDTEAM_RUNNING,
                "queue_depth": _REDTEAM_QUEUE.qsize(),
                "stats": dict(_REDTEAM_STATS),
                "seen_keys": len(_REDTEAM_SEEN),
            },
            "tuples": {
                "queues": tuple_queues,
                "types_allowed": list(_TUPLE_TYPES.keys()),
            },
        }

    def _metrics(self, request: dict) -> dict:
        """Prometheus-style counters and gauges. Glass-box observability without
        requiring Langfuse / SigNoz to be configured -- this works standalone.
        """
        fmt = request.get("format", "json")
        with _REPLICAS_LOCK:
            replicas = {rid: len(sm) for rid, sm in _REPLICAS.items()}
        with _TUPLES_LOCK:
            tuple_queues = {t: len(b) for t, b in _TUPLES.items()}
        metrics = {
            "verifier_folded_total": _VERIFIER_STATS["folded"],
            "verifier_passed_total": _VERIFIER_STATS["passed"],
            "verifier_failed_total": _VERIFIER_STATS["failed"],
            "verifier_errors_total": _VERIFIER_STATS["errors"],
            "judge_scored_total": _JUDGE_STATS["scored"],
            "judge_errors_total": _JUDGE_STATS["errors"],
            "redteam_defeated_total": _REDTEAM_STATS["defeated"],
            "redteam_errors_total": _REDTEAM_STATS["errors"],
            "verifier_queue_depth": _VERIFIER_QUEUE.qsize(),
            "judge_queue_depth": _JUDGE_QUEUE.qsize(),
            "redteam_queue_depth": _REDTEAM_QUEUE.qsize(),
            "replica_count": len(replicas),
            "total_triplets": sum(replicas.values()),
            "tuple_queues_total": sum(tuple_queues.values()),
        }
        if fmt == "prometheus":
            lines = ["# HELP idp_executor Daemon metrics", "# TYPE idp_executor gauge"]
            for name, value in metrics.items():
                lines.append(f"idp_executor_{name} {value}")
            return {"ok": True, "format": "prometheus", "body": "\n".join(lines)}
        return {"ok": True, "format": "json", "metrics": metrics}

    def _trace_tail_cmd(self, request: dict) -> dict:
        n = int(request.get("n", 50))
        return {"ok": True, "events": _trace_tail(n), "log": _TRACE_LOG}

    def _tracing_status_cmd(self, request: dict) -> dict:
        info = _otel_status()
        info["ok"] = True
        return info

    def _mutation_files(self, proposal: dict) -> list[ProposedFile]:
        """Rebuild the per-file, per-path list a mutation proposal carries.

        Shared by `_verify_mutation` and `_admit_mutation` so the two never disagree about
        what a ledger's bytes are: one reader, not two. `code_patch`/`manifest_patch` are
        unified diffs (`parse_unified_diff` already handles any number of files inside one),
        `sql_migration` is not a diff -- it is the migration's own full text -- so it becomes
        one `ProposedFile` at a fixed path, the only shape `propose_mutation`'s spec admits
        (one migration per proposal).
        """
        files: list[ProposedFile] = []
        if proposal.get("code_patch"):
            files.extend(parse_unified_diff(proposal["code_patch"]))
        if proposal.get("manifest_patch"):
            files.extend(parse_unified_diff(proposal["manifest_patch"]))
        if proposal.get("sql_migration"):
            files.append(
                ProposedFile(
                    path="migration.sql",
                    lines=proposal["sql_migration"].splitlines(keepends=True),
                )
            )
        return files

    def _propose_mutation(self, request: dict) -> dict:
        """The typed multi-domain ledger's producer half: one ledger, up to three domains.

        docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md's gap: a change that
        legitimately needs code+manifest+SQL together used to be three unrelated `propose_patch`/
        `simulate_change` calls, three unrelated verdicts, three unrelated windows in which one
        could land without the other two. This writes every supplied domain's bytes into ONE
        ledger id, so `verify_mutation` grades them together or not at all.

        The ephemeral `ledger_dir` exists only so `stage_execution` has a sandbox root to build
        under (same shape `_propose_patch` uses) -- it carries no proposal state of its own and
        is destroyed by `verify()` on every path, pass or fail. The proposal's own bytes live in
        `ledger_root()/proposals/<ledger_id>.json`, OUTSIDE that ephemeral directory, because
        `admit_mutation` needs them to build a real commit after the ledger they arrived in is
        long gone -- the same reason `staged/<ledger_id>.patch` already survives `verify()`.
        """
        code_patch = request.get("code_patch") or ""
        manifest_patch = request.get("manifest_patch") or ""
        sql_migration = request.get("sql_migration") or ""
        tests = request.get("tests") or ""
        claim = request.get("claim", "")
        # The reversibility envelope (ADR 0024): the inverse a mutation must carry before it can
        # be admitted. Optional at propose time so an agent can open a ledger and fill it before
        # `verify_mutation`, but `verify_mutation` refuses a proposal that arrives without one --
        # the door is at verification, not at proposal, because verification is the last moment
        # before a change is sealed and the only place an inverse can still be supplied.
        envelope = request.get("envelope")
        if not (code_patch.strip() or manifest_patch.strip() or sql_migration.strip()):
            return {"ok": False, "error": "nothing to propose"}

        domains: list[str] = []
        if code_patch.strip():
            domains.append("code")
        if manifest_patch.strip():
            domains.append("manifest")
        if sql_migration.strip():
            domains.append("sql")

        proposal = {
            "code_patch": code_patch,
            "manifest_patch": manifest_patch,
            "sql_migration": sql_migration,
            "tests": tests,
            "claim": claim,
            "domains": domains,
            "envelope": envelope if isinstance(envelope, dict) else None,
        }
        files = self._mutation_files(proposal)
        if not files:
            # An empty proposal that "passes" is the silent green this estate keeps catching --
            # a non-empty field that parses to no files (e.g. a diff with no `+++` hunks) is
            # refused rather than opening a ledger over zero files.
            return {
                "ok": False,
                "error": "the supplied patch(es) parse to no files; there is nothing to verify",
            }

        ledger_id = f"ldg-{uuid.uuid4().hex[:12]}"
        ledger_dir = os.path.join(ledger_root(), ledger_id)
        os.makedirs(ledger_dir, mode=0o700, exist_ok=True)
        proposals_dir = os.path.join(ledger_root(), "proposals")
        os.makedirs(proposals_dir, mode=0o700, exist_ok=True)
        proposal["ledger_id"] = ledger_id
        proposal["subject"] = canonical_subject(files)
        with open(os.path.join(proposals_dir, f"{ledger_id}.json"), "w") as handle:
            json.dump(proposal, handle)

        return {
            "ok": True,
            "ledger_id": ledger_id,
            "ledger_dir": ledger_dir,
            "domains": domains,
            "suspended": True,
            "subject_digest": proposal["subject"],
            "note": "the agent is suspended pending deterministic verification",
        }

    def _verify_mutation(self, request: dict) -> dict:
        """Rule (new): grade every domain in the ledger together -- all-or-nothing.

        Runs the SAME `sovereign.verifier.verify()` the single-domain door uses (LAW 43: no
        second gauntlet) over every file across every supplied domain in one pass -- `verify()`
        already generalized to typed domains (`classify_domain`/`stage_sql`/`domains` in its own
        verdict) precisely so this handler does not need a parallel implementation. The one
        thing this handler adds is `per_domain`: which domain(s) a failure actually names, never
        a paraphrase, and there is no reply shape where one domain is admissible while another
        is not -- `verify()`'s single verdict already enforces that structurally.
        """
        ledger_id = request.get("ledger_id", "")
        if not isinstance(ledger_id, str) or not ledger_id:
            return {"ok": False, "error": "verify_mutation needs a ledger_id"}
        ledger_dir = os.path.join(ledger_root(), ledger_id)
        proposal_path = os.path.join(ledger_root(), "proposals", f"{ledger_id}.json")
        if not os.path.exists(proposal_path):
            return {
                "ok": False,
                "error": (
                    f"no mutation proposal {ledger_id!r} -- it was already spent or it never existed"
                ),
                "ledger_dir": ledger_dir,
            }
        try:
            with open(proposal_path) as handle:
                proposal = json.load(handle)
        except (OSError, ValueError) as exc:
            return {
                "ok": False,
                "error": f"the mutation ledger could not be read: {exc}",
                "ledger_dir": ledger_dir,
            }

        files = self._mutation_files(proposal)
        # ADR 0024 / 0025, enforced at the one place a mutation is graded: before the gauntlet
        # runs, the envelope must carry an inverse. This is the field the ledger door always
        # implied and nothing required -- a mutation nobody can take back is refused here, not
        # discovered later. `bin/idp-reversibility-gate` owns the judgement (shape, probe,
        # signature); this handler only asks it, so there is one implementation of the rule and
        # not a second one living in the daemon (LAW 43).
        reversible, why = self._mutation_is_reversible(proposal)
        if not reversible:
            try:
                os.unlink(proposal_path)
            except OSError:
                pass
            return {
                "ok": False,
                "admissible": False,
                "per_domain": {},
                "error": why,
                "ledger_dir": ledger_dir,
                "violation_code": "NO_INVERSE",
            }
        ledger = Ledger(
            ledger_id=ledger_id,
            ledger_dir=Path(ledger_dir),
            files=files,
            tests=proposal.get("tests", ""),
            claim=proposal.get("claim", ""),
        )
        verdict = verify(ledger)
        verdict["ledger_dir"] = ledger_dir
        verdict["ledger_destroyed"] = not os.path.exists(ledger_dir)
        # `verify()`'s own "domains" is the suffix-keyed summary `mutation_per_domain` reads
        # (classify_domain's vocabulary: code/k8s_manifest/sql_schema) -- it must survive
        # untouched here. "domains_requested" is the separate, door-facing list
        # (code/manifest/sql) the proposal itself declared; the two vocabularies are not
        # interchangeable, and overwriting the first with the second here (a bug caught by
        # this door's own BDD suite, 2026-09-15) silently dropped every domain but "code"
        # from per_domain on any multi-domain failure.
        verdict["domains_requested"] = proposal.get("domains", [])
        verdict["per_domain"] = mutation_per_domain(verdict, files)
        if not verdict.get("ok"):
            # Nothing left to seal or admit: the same "ledger destroyed on every path" rule
            # `verify()` already applies to its own ephemeral directory applies here to the
            # proposal record that outlives it.
            try:
                os.unlink(proposal_path)
            except OSError:
                pass
        return verdict

    def _mutation_is_reversible(self, proposal: dict) -> tuple[bool, str]:
        """Does this proposal carry a verifiable inverse? Ask the gate, never re-decide here.

        `bin/idp-reversibility-gate` is the one implementation (LAW 43). A gate that exits 2
        (BLIND -- it could not read its schema or verifier) is a REFUSAL here, deliberately:
        unlike a push hook, this is the last door before a mutation is admitted, and failing
        open would admit an unproven inverse. The BLIND state exists so the operator can see
        *why* a correct envelope was refused and fix the gate's input (LAW 38's remedy), not so
        the daemon can admit work it could not judge.
        """
        envelope = proposal.get("envelope")
        if not isinstance(envelope, dict):
            return False, (
                "no mutation envelope on this proposal: an admitted mutation must carry "
                "`envelope` with an inverse_spec (ADR 0024)"
            )
        gate = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "bin",
            "idp-reversibility-gate",
        )
        if not os.path.exists(gate):
            return False, f"reversibility gate not found at {gate}"
        import subprocess  # local: kept out of the pure import path used by the tests
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False
            ) as handle:
                json.dump(envelope, handle)
                path = handle.name
            proc = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                [sys.executable, gate, path], capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"reversibility gate could not be run: {exc}"
        finally:
            try:
                os.unlink(path)
            except (OSError, UnboundLocalError):
                pass
        if proc.returncode == 0:
            return True, ""
        detail = (proc.stdout or proc.stderr or "").strip().splitlines()
        return False, "NO_INVERSE: " + (detail[-1] if detail else "gate refused")

    def _run_inverse_probe(self, probe: str, cwd: str | None = None) -> dict:
        """Execute a declared verification probe against the real machine and report what happened.

        This is the half `bin/idp-reversibility-gate` cannot do: the gate grades the envelope's
        SHAPE, and this runs the command it declared. Before this method existed the probe was a
        string in a JSON document that no code ever read -- a test described, never taken. The
        estate's empirical-proof rule is the reason this had to become real code rather than a
        claim in a docstring.

        The probe is a shell command because that is what the envelope declares (an assertion
        against live state: `kubectl get ... == 2`). It is executed with `shell=True` DELIBERATELY
        and the blast radius is bounded three ways: (1) it comes from an envelope that verify_mutation
        already admitted, (2) it runs with a hard timeout, (3) its exit code -- not its output --
        is the verdict, so a probe cannot "pass" by printing something clever. A probe whose
        command cannot run at all is BLIND (`executed: False`), never a pass (LAW 38).
        """
        if not isinstance(probe, str) or not probe.strip():
            return {"executed": False, "passed": False, "reason": "empty probe"}
        import subprocess  # local: kept out of the pure import path used by the tests

        try:
            proc = subprocess.run(  # noqa: S602 -- shell=True on a probe verify_mutation already admitted; bounded by a timeout, exit code is the only verdict
                probe,
                shell=True,
                cwd=cwd or live_worktree(),
                capture_output=True,
                text=True,
                timeout=PROBE_CEILING_SEC,
            )
        except subprocess.TimeoutExpired:
            return {
                "executed": True,
                "passed": False,
                "exit_code": None,
                "probe": probe,
                "reason": f"the probe did not finish within {PROBE_CEILING_SEC}s",
            }
        except OSError as exc:
            return {
                "executed": False,
                "passed": False,
                "probe": probe,
                "reason": f"the probe could not be run: {exc}",
            }
        return {
            "executed": True,
            "passed": proc.returncode == 0,
            "exit_code": proc.returncode,
            "probe": probe,
            "stdout": (proc.stdout or "")[-4000:],
            "stderr": (proc.stderr or "")[-4000:],
            "reason": (
                "the probe held: the state is what the inverse promised"
                if proc.returncode == 0
                else f"the probe did not hold (exit {proc.returncode})"
            ),
        }

    def _seal_mutation(self, request: dict) -> dict:
        """Rule (new)'s producer half: attest the WHOLE bundle's bytes, not one file's.

        Mirrors `_seal` exactly, over the bundle `verify()` already staged at
        `staged/<ledger_id>.patch` on a VERIFIED mutation -- that file existing is what proves
        `verify_mutation` ran and passed; there is no second flag to fall out of sync with it.
        """
        ledger_id = request.get("ledger_id", "")
        if not isinstance(ledger_id, str) or not ledger_id:
            return {"ok": False, "error": "seal_mutation needs a ledger_id"}
        staged_path = os.path.join(ledger_root(), "staged", f"{ledger_id}.patch")
        if not os.path.exists(staged_path):
            return {
                "ok": False,
                "error": (
                    f"no verified bundle for ledger {ledger_id!r} -- call verify_mutation first "
                    "and confirm it returned admissible: true"
                ),
            }

        import hashlib  # local: only this handler needs a digest

        from verifier import sign  # noqa: PLC0415 - reached only when a seal is asked for

        payload_bytes = open(staged_path, "rb").read()
        subject = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
        attestation = sign(subject, ledger_root=Path(ledger_root()))
        return {
            "ok": True,
            "ledger_id": ledger_id,
            "subject_digest": subject,
            "attestation": attestation,
            "staged_path": staged_path,
        }

    def _admit_mutation(self, request: dict) -> dict:
        """Rule (new): refuse an unattested bundle; admit an attested one to a NEW branch.

        Same two-outcome enforcement point `_admit` already proves (UNATTESTED /
        UNATTESTED_BADSIGNATURE, checked before anything is written) over the bundle's real
        bytes. The one addition this verb makes over `_admit`: on a valid seal it also builds one
        real commit, on a throwaway index, landing on a brand-new branch -- never `main`, never
        HEAD, never the live working tree (see `_build_mutation_commit`). `pr_required: True` on
        every success: this verb never merges, per ADR 0025 ("he is the only merger on every
        Glass-Break change") -- merging this class of change is not on the Trust Threshold's
        closed list today.
        """
        ledger_id = request.get("ledger_id", "")
        if not isinstance(ledger_id, str) or not ledger_id:
            return {"ok": False, "error": "admit_mutation needs a ledger_id"}
        staged_path = os.path.join(ledger_root(), "staged", f"{ledger_id}.patch")
        if not os.path.exists(staged_path):
            return {
                "ok": False,
                "error": f"no verified bundle for ledger {ledger_id!r} -- call verify_mutation first",
            }

        import hashlib  # local: only this handler needs a digest

        payload_bytes = open(staged_path, "rb").read()
        subject = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
        attestation = request.get("attestation")

        if not attestation:
            return {
                "ok": False,
                "intercepted": True,
                "violation_code": "UNATTESTED",
                "error": (
                    "the mutation bundle carries no attestation from the Deterministic "
                    "Verifier; the estate admits no change without its seal"
                ),
                "subject_digest": subject,
            }
        if not verify_attestation(attestation, subject):
            return {
                "ok": False,
                "intercepted": True,
                "violation_code": "UNATTESTED_BADSIGNATURE",
                "error": (
                    "the attestation does not verify over these bundle bytes; it was minted "
                    "over a different artifact"
                ),
                "subject_digest": subject,
            }

        admitted_dir = os.path.join(ledger_root(), "admitted")
        os.makedirs(admitted_dir, mode=0o700, exist_ok=True)
        admitted_path = os.path.join(admitted_dir, f"{ledger_id}.patch")
        with open(admitted_path, "wb") as handle:
            handle.write(payload_bytes)

        proposal_path = os.path.join(ledger_root(), "proposals", f"{ledger_id}.json")
        if not os.path.exists(proposal_path):
            # Attested and admitted -- the bytes are validated and on disk, same guarantee
            # `admit_payload` gives -- but the domain-typed record `admit_mutation` itself
            # writes at propose time and needs to build a real commit is gone. This handler is
            # the only consumer of that file, so reaching here means it was already spent by an
            # earlier admit of this same ledger_id: reported, not silently re-admitted.
            return {
                "ok": True,
                "validated": True,
                "admitted_path": admitted_path,
                "subject_digest": subject,
                "branch": None,
                "error": "proposal record already spent; no branch was built on this call",
            }
        with open(proposal_path) as handle:
            proposal = json.load(handle)
        files = self._mutation_files(proposal)
        # Record the envelope beside the admitted bytes, so the inverse's probe outlives the
        # proposal record this handler is about to spend. `verify_inverse` reads the probe from
        # here -- without this write the probe would be deleted along with the proposal, and the
        # declared test would vanish exactly when the rollback path needs it.
        envelope = proposal.get("envelope")
        if isinstance(envelope, dict):
            admitted_envelope = os.path.join(admitted_dir, f"{ledger_id}.json")
            with open(admitted_envelope, "w") as handle:
                json.dump(envelope, handle)
            os.chmod(admitted_envelope, stat.S_IRUSR | stat.S_IWUSR)
        branch = f"mutation/{ledger_id}"
        claim = proposal.get("claim") or "typed multi-domain mutation ledger"
        os.unlink(proposal_path)  # spent: this ledger cannot mint a second branch
        try:
            commit_sha = _build_mutation_commit(live_worktree(), branch, files, claim)
        except OSError as exc:
            return {
                "ok": True,
                "validated": True,
                "admitted_path": admitted_path,
                "subject_digest": subject,
                "branch": None,
                "error": f"admitted, but the branch could not be built: {exc}",
            }
        # Deliver: push the branch and open its PR, so the admitted mutation is reachable by
        # Greenlane Row 3 instead of sitting as a local ref nobody lists. Fail-soft -- the
        # admission stands even when delivery cannot happen (see _deliver_mutation).
        delivery = self._deliver_mutation(branch, claim)
        return {
            "ok": True,
            "validated": True,
            "admitted_path": admitted_path,
            "subject_digest": subject,
            "branch": branch,
            "commit_sha": commit_sha,
            "pr_required": True,
            **delivery,
        }

    def _deliver_mutation(self, branch: str, claim: str) -> dict:
        """Push the admitted branch and open its PR -- the delivery the ledger always implied.

        Before this, `admit_mutation` built a real commit on `refs/heads/mutation/<ledger_id>`
        and stopped there: the branch was local, nothing pushed it, and Greenlane Row 3 (which
        lists open `mutation/*` pull requests) had nothing to find. The sanctioned path was
        therefore unreachable, and an agent's only way to land a change was the hand edit ADR
        0025 exists to replace. This is the last step of that path, and it runs HERE, in the one
        writer, so the agent never touches git (option A of the delivery decision, 2026-09-19).

        FAIL-SOFT, deliberately: the mutation is already admitted and its bytes are on disk. A
        push that fails (no credential, no remote, offline) must NOT lose the admission -- it is
        reported in `delivery_error` so a caller can retry, because an admitted mutation that
        cannot be delivered is a fact somebody needs, never a 500.

        The credential is GH_TOKEN, the same one every other `gh` caller in the estate uses
        (bin/idp-catalog-push, the workflows). The daemon holds no GitHub secret of its own; a
        push with no token is BLIND -- reported, not retried in a loop.
        """
        import subprocess  # local: kept out of the pure import path used by the tests

        root = live_worktree()
        # `--force-with-lease` is NOT used: this ref is brand new (update-ref created it), so a
        # plain push either creates it or fails because it already exists -- and a pre-existing
        # remote branch for this ledger id means this mutation was already delivered once, which
        # must be reported rather than overwritten (a rewrite would detach the PR from the
        # commit the executor actually sealed).
        try:
            push = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                ["git", "push", "origin", f"refs/heads/{branch}:refs/heads/{branch}"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "pushed": False,
                "delivery_error": f"git push could not be run: {exc}",
            }
        if push.returncode != 0:
            return {
                "pushed": False,
                "delivery_error": f"git push failed: {(push.stderr or push.stdout).strip()[:300]}",
            }

        try:
            pr = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                [  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                    "gh",
                    "pr",
                    "create",
                    "--head",
                    branch,
                    "--base",
                    "main",
                    "--title",
                    f"mutation: {claim[:60]}",
                    "--body",
                    (
                        f"Admitted reversible mutation `{branch}`.\n\n"
                        f"The Deterministic Verifier sealed this bundle and the executor admitted "
                        f"it; the branch carries exactly the files the admitted bundle named, and "
                        f"its envelope declares the inverse (ADR 0024). Greenlane Row 3 "
                        f"(`bin/idp-admitted-mutation-diff`) re-proves all of that before anything "
                        f"lands.\n\nClaim: {claim}\n"
                    ),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "pushed": True,
                "delivery_error": f"the branch is pushed but the PR could not be opened: {exc}",
            }
        if pr.returncode != 0:
            # A PR that already exists for this head is not an error -- `admit_mutation` may be
            # retried after a partial delivery, and `gh pr create` refuses a duplicate. Report the
            # URL from the existing PR rather than a failure.
            existing = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
                ["gh", "pr", "view", branch, "--json", "url", "-q", ".url"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ},
            )
            if existing.returncode == 0 and existing.stdout.strip():
                return {
                    "pushed": True,
                    "pr_url": existing.stdout.strip(),
                    "pr_existing": True,
                }
            return {
                "pushed": True,
                "delivery_error": f"the PR could not be opened: {(pr.stderr or pr.stdout).strip()[:300]}",
            }
        return {"pushed": True, "pr_url": (pr.stdout or "").strip()}

    def _verify_inverse(self, request: dict) -> dict:
        """Run the declared inverse's verification probe against the real machine (empirical proof).

        This is the verb that makes `verification_probe` operational. Before it, the probe was a
        string in a JSON envelope that no code read: a test described in a document, never taken.
        The estate's empirical-proof rule refuses that -- a claim is not a proof -- so this runs
        the probe for real and returns the machine's own exit code.

        The probe MAY be supplied two ways: as `probe` directly (a caller finishing a rollback it
        just performed), or via `ledger_id`, in which case the probe is read from the envelope the
        admitted bundle carries. A probe that cannot run is BLIND (`executed: False`), never a
        pass, and the caller -- the founder's rollback path -- decides what to do with it.
        """
        probe = request.get("probe")
        ledger_id = request.get("ledger_id", "")
        if not isinstance(probe, str) or not probe.strip():
            if not isinstance(ledger_id, str) or not ledger_id:
                return {
                    "ok": False,
                    "executed": False,
                    "error": "verify_inverse needs a `probe` string or a `ledger_id`",
                }
            admitted = os.path.join(ledger_root(), "admitted", f"{ledger_id}.json")
            if not os.path.exists(admitted):
                return {
                    "ok": False,
                    "executed": False,
                    "error": (
                        f"no admitted envelope for {ledger_id!r}; verify_inverse reads the probe "
                        "from the envelope an admit_mutation recorded"
                    ),
                }
            try:
                envelope = json.load(open(admitted))
            except (OSError, ValueError) as exc:
                return {
                    "ok": False,
                    "executed": False,
                    "error": f"envelope unreadable: {exc}",
                }
            probe = (envelope.get("inverse_spec") or {}).get("verification_probe") or ""
            if not probe.strip():
                return {
                    "ok": False,
                    "executed": False,
                    "error": (
                        "this mutation declared an irreversible exemption, not a deterministic "
                        "inverse: there is no probe to run, which is why the exemption needed a "
                        "signature (ADR 0024)"
                    ),
                }
        cwd = request.get("cwd")
        result = self._run_inverse_probe(probe, cwd if isinstance(cwd, str) else None)
        result["ok"] = bool(result.get("passed"))
        return result

    def _reply(self, payload: dict) -> None:
        """Answer the caller, and treat a departed caller as a non-event.

        Measured 2026-09-14, incident: this daemon crash-looped, and every job dispatched in
        the window came back with an EMPTY log -- accepted into a queue nothing was draining,
        which reads exactly like a slow job. The cause was this line. A caller that reads once
        and closes (`read_job`, a CLI, a session that moved on) leaves the socket shut, so
        `write` raised BrokenPipeError, socketserver printed a traceback per request, and the
        daemon did not survive the storm. The execution plane for the whole estate went down
        because a client hung up.

        A caller who has gone away is not a failed job; there is no one left to tell. So the
        two errors that mean exactly that are swallowed and the daemon keeps serving. Every
        other OSError still propagates, because a socket that is genuinely broken is a fact
        somebody needs.
        """
        try:
            self.wfile.write((json.dumps(payload) + "\n").encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            # The caller closed first (BrokenPipeError) or the connection was torn down
            # (ConnectionResetError). Same meaning, same handling: nobody is listening.
            return


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False  # a stale socket must be an error, not silently stolen


def serve() -> None:  # pragma: no cover - the daemon loop
    os.makedirs(os.path.dirname(SOCKET_PATH), mode=0o700, exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        # A socket that answers is a second daemon; one that does not is a leftover. Distinguish
        # rather than delete blindly, because deleting a live socket is an outage (R38).
        if _answers(SOCKET_PATH):
            print(
                f"refused: another executor is already answering on {SOCKET_PATH}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        os.unlink(SOCKET_PATH)

    start_verifier_thread()
    start_consumer_threads()
    print(
        "executor: math sieve + judge_loop + redteam_loop auto-started",
        file=sys.stderr,
    )

    server = Server(SOCKET_PATH, Handler)
    # Owner-only. The agent runs as the same uid today, so this is not the boundary yet -- it is
    # what makes the separate-uid step a one-line change rather than a rewrite.
    os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR)
    print(
        f"executor listening on {SOCKET_PATH} (ceiling {CEILING_SEC}s)", file=sys.stderr
    )
    server.serve_forever()


def _answers(path: str, timeout: float = 1.0) -> bool:
    """Does something actually answer on this socket?"""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(path)
            sock.sendall(b'{"verb":"health"}\n')
            return bool(sock.recv(4096))
        except OSError:
            return False


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # A cheap, honest answer a person or a script can read.
        import shutil

        print(
            json.dumps(
                {
                    "socket": SOCKET_PATH,
                    "socket_exists": os.path.exists(SOCKET_PATH),
                    "answering": _answers(SOCKET_PATH)
                    if os.path.exists(SOCKET_PATH)
                    else False,
                    "ceiling_sec": CEILING_SEC,
                    "timeout_bin": TIMEOUT_BIN,
                    "timeout_present": bool(
                        shutil.which(TIMEOUT_BIN) or os.path.exists(TIMEOUT_BIN)
                    ),
                },
                indent=2,
            )
        )
        return 0
    serve()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
