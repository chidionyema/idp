#!/usr/bin/env python3
"""Sovereign Bus CLI: `bin/sb <command> ...`. See sovereign/CONTRACT.md.

Core subcommands (owner: builder A) are defined here. otto's and cockpit's
subcommands plug in through the try-import hook at the bottom of main() --
this module never imports them at module load time, so it works with
neither present (cp6: the engine runs with no vendor around).
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import client as engine_client


def _emit(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, sort_keys=True, default=str))
        return
    if isinstance(obj, list):
        for row in obj:
            print(json.dumps(row, sort_keys=True, default=str))
    else:
        print(obj)


def _add_json(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="print JSON")


# ---- core commands (engine) ----


def cmd_start(args: argparse.Namespace) -> int:
    budget_resolved = config.get("budget.default", cli_value=args.budget)
    if budget_resolved.value is None:
        print("budget required", file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    if args.estate:
        # cp21 wiring, partial by attach/README.md's own admission: repo
        # defaults to the attach root so a step's own git/file work happens
        # there. Routing this session's receipts under
        # attach_core.estate_dir_for(Path(args.estate))/receipts.jsonl
        # needs engine/workflow.py's append_receipt activity to take a
        # path param -- it always writes config.SB_RECEIPTS today -- so
        # that half is out of scope for this patch (attach/README.md
        # flags it as residual, not mine to invent).
        from sovereign.attach import core as attach_core  # noqa: F401

        args.repo = args.repo or args.estate
    if getattr(args, "branches", None) and int(args.branches) > 1:
        from sovereign.shadow import branching

        res = asyncio.run(
            branching.start_on_estate(
                args.task, runner=args.runner, repo=args.repo, budget=int(budget_resolved.value), count=int(args.branches)
            )
        )
        _emit(res, args.json)
        return 0
    res = asyncio.run(
        engine_client.start(
            args.task, runner=args.runner, repo=args.repo, by=args.by, budget=int(budget_resolved.value),
            critical=bool(getattr(args, "critical", False)),
        )
    )
    _emit(res, args.json)
    return 0


def cmd_refill(args: argparse.Namespace) -> int:
    res = asyncio.run(
        engine_client.signal(
            args.session_id, "refill", args.by, tokens=args.tokens, signed=args.signed
        )
    )
    _emit(res, args.json)
    return 0


def cmd_verify_receipts(args: argparse.Namespace) -> int:
    from sovereign.engine import receipts as receipts_mod

    res = receipts_mod.verify()
    _emit(res, args.json)
    return 0 if res.get("ok") else 1


def cmd_audit(args: argparse.Namespace) -> int:
    """cp34: the audit log IS the signed receipt chain (cp19), plus the
    DAG under heads/main. `--verify` checks every signature, the monotonic
    counter and the head anchor, then walks heads/main to genesis, and
    exits non-zero on the first break. `--at <hash>` answers who did what,
    when, under which policy, and which trust backend signed it, for one
    chain line. With neither flag, verify."""
    from sovereign.engine import checkpoint

    if args.at:
        res = checkpoint.audit_at(args.at)
        if res is None:
            print(f"no receipt with hash {args.at}", file=sys.stderr)
            return config.CLI_EXIT_USAGE_ERROR
        _emit(res, args.json)
        return 0 if res["chain_ok"] else 1
    res = checkpoint.audit_verify()
    _emit(res, args.json)
    return 0 if res["ok"] else 1


def cmd_undo(args: argparse.Namespace) -> int:
    """R7: revert the commit a receipt names, by walking the chain back to
    that receipt (`--to <receipt hash>`) or to the session's newest receipt
    that carries a commit. One receipt of kind "undo" is written."""
    from sovereign.engine import undo as undo_mod

    try:
        res = undo_mod.undo(args.session_id, args.by, receipt_hash=args.to)
    except undo_mod.NothingToUndo as exc:
        print(str(exc), file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    _emit(res, args.json)
    return 0


def _services_down() -> dict[str, str]:
    """Stop the worker and Temporal by their pid files; the same code path
    as `sb down`, so rewind stops exactly what up started."""
    ns = argparse.Namespace(json=True)
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_down(ns)
    return json.loads(buf.getvalue())


def _services_up() -> dict[str, str]:
    ns = argparse.Namespace(json=True)
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_up(ns)
    return json.loads(buf.getvalue())


def cmd_rewind(args: argparse.Namespace) -> int:
    """cp33: stop services, move heads/main to the named hash, rebuild the
    projection view from the DAG, write one signed REWIND receipt. Nothing
    after the hash is deleted. Services are brought back up afterwards
    when recover.start_services is on, the same switch `sb recover` uses."""
    from sovereign.engine import checkpoint

    if not args.signed:
        print("rewind is a destructive op and needs --signed", file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    stopped = _services_down()
    try:
        res = checkpoint.rewind(args.hash, args.by, signed=True)
    except checkpoint.UnknownRoot as exc:
        print(str(exc), file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    started = _services_up() if config.RECOVER_START_SERVICES else {}
    _emit({**res, "services_stopped": stopped, "services_started": started}, args.json)
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    """cp35: point heads/main at the last fully committed root, rebuild
    the projection view, bring the services back, write one RECOVER
    receipt."""
    from sovereign.engine import checkpoint

    res = checkpoint.recover(args.by)
    started = _services_up() if config.RECOVER_START_SERVICES else {}
    _emit({**res, "services": started, "services_started": bool(config.RECOVER_START_SERVICES)}, args.json)
    return 0


def cmd_root(args: argparse.Namespace) -> int:
    """cp9/cp15: `sb root --json` reports the cross-stack composite root
    -- {root, code_root, db_root, policy_root, ai_policy_root} -- plus
    cp9's own DB-chain diagnostics (db_nodes, db_parent, db_verified).
    db_root IS .estate/heads/shadow_main, the branch pointer cp8's
    sidecar advances once per write; the other three children are cp15's
    (git HEAD, the attach policy config, the trust/presence config)."""
    from sovereign.engine import cross_stack

    res = cross_stack.root()
    _emit(res, args.json)
    return 0 if res.get("db_verified") else 1


def cmd_consensus(args: argparse.Namespace) -> int:
    """cp11: `sb consensus --json` -- {reads, matches, mismatches, rate}
    aggregated from every cp10 dualread receipt on disk."""
    from sovereign.sidecar import dualread

    _emit(dualread.summary(), args.json)
    return 0


def cmd_flip(args: argparse.Namespace) -> int:
    """cp13: `sb flip --by <who> --signed` sets the legacy DB read-only
    and signs one "flip" receipt; `sb flip --rollback --by <who> --signed`
    restores write access if nothing wrote to the file while flipped."""
    from sovereign.engine import flip

    try:
        if args.rollback:
            _emit(flip.rollback(by=args.by, signed=args.signed), args.json)
        else:
            _emit(flip.flip(by=args.by, signed=args.signed), args.json)
        return 0
    except flip.FlipError as exc:
        print(f"flip refused: {exc}", file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR

def cmd_rebuild(args: argparse.Namespace) -> int:
    """cp14: `sb rebuild --json` replays the whole DAG from genesis and
    rewrites the projection store; verified=False means the DAG chain
    itself did not check out and the store on disk was left untouched."""
    from sovereign.engine import projection

    result = projection.rebuild(by=args.by)
    _emit(result, args.json)
    return 0 if result["verified"] else 1


def cmd_list(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.list_sessions())
    _emit(res, args.json)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.show(args.session_id))
    _emit(res, args.json)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "stop", args.by, args.reason or ""))
    _emit(res, args.json)
    return 0


APPROVE_ACTION = "approve"


def cmd_approve(args: argparse.Namespace) -> int:
    """R11/R22: no signature, no act (cp29).

    `--sign` mints a challenge and signs it here and now -- Touch ID
    through presence_helper.swift when this Mac has an enclave, and the
    configured 2-of-3 signer set when it does not (cp29 scenario 3, R24).
    `--signature` takes an envelope somebody else already signed, as JSON
    or as a path to it.

    With neither, and trust.require_signed_approval left on, the command
    refuses. That refusal is the requirement: before it, the founder's
    name in `--by` was the only credential on a destructive override, and
    a name is not a secret."""
    from sovereign.engine import interventions as interventions_mod
    from sovereign.engine import receipts as receipts_mod
    from sovereign.trust import approval
    from sovereign.trust.anchor import HardwareTrustAnchor

    envelope = approval.load(args.signature)

    if envelope is None and args.sign:
        trust_anchor = HardwareTrustAnchor()
        challenge = approval.challenge(args.session_id, APPROVE_ACTION, args.by)
        if trust_anchor.backend == "secure_enclave":
            envelope = approval.sign(challenge, trust_anchor)
        else:
            # cp29 scenario 3: degraded mode is logged, not silent. The
            # fallback happens automatically because refusing outright
            # would make every non-Mac host unable to approve anything,
            # and a guard that refuses correct work is an outage (LAW 38).
            envelope = approval.sign_fallback(challenge)

    if envelope is None and not config.REQUIRE_SIGNED_APPROVAL:
        res = asyncio.run(engine_client.signal(args.session_id, APPROVE_ACTION, args.by))
        _emit(res, args.json)
        return 0

    verdict = approval.verify(envelope)
    if not verdict["ok"]:
        print(verdict["reason"], file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR

    # Spend the counter before acting, never after: a crash between the
    # two must leave an approval that cannot be replayed, not one that can.
    approval.spend(int(verdict["counter"]))
    entry = receipts_mod.append(
        {
            "session_id": args.session_id,
            # kind is the action name so interventions.is_intervention()
            # recognises the line; "intervention" was not in
            # interventions.kinds and the approve never reached the
            # interventions/ view cp29 reads (found writing its steps).
            "kind": APPROVE_ACTION,
            "by": args.by,
            "text": APPROVE_ACTION,
            "step": 0,
            "status": APPROVE_ACTION,
            "task": "",
            "runner": "",
            "attestation": verdict["attestation"],
            "approval_counter": int(verdict["counter"]),
            "approval_sig": envelope.get("sig") or envelope.get("signers"),
            "approval_backend": envelope.get("backend"),
            "approval_signers": verdict["signers"],
        }
    )
    interventions_mod.mirror(entry)
    res = asyncio.run(
        engine_client.signal(args.session_id, APPROVE_ACTION, args.by, attestation=verdict["attestation"])
    )
    _emit(
        {**res, "attestation": verdict["attestation"], "counter": entry["counter"], "hash": entry["hash"]},
        args.json,
    )
    return 0


def cmd_model_consensus(args: argparse.Namespace) -> int:
    """cp30: three models vote through LiteLLM, and policy overrules them.

    Deliberately NOT folded into `sb consensus`, which is cp11's
    DB-versus-DAG dual read. Same English word, two unrelated questions."""
    from sovereign.consensus.decide import decide as decide_fn

    destructive = True if args.destructive else (False if args.non_destructive else None)
    res = decide_fn(args.op, destructive=destructive)
    _emit(res, args.json)
    return 0 if res["ok"] else 1


def cmd_identity(args: argparse.Namespace) -> int:
    """R31: this agent's SPIFFE identity, and the heartbeat registry that
    revokes a ghost after 3 missed beats."""
    from sovereign.trust import spiffe

    if args.beat:
        _emit(spiffe.beat(args.beat), args.json)
        return 0
    if args.miss:
        _emit(spiffe.miss(args.miss), args.json)
        return 0
    if args.sweep:
        _emit({"revoked": spiffe.sweep()}, args.json)
        return 0
    me = spiffe.identity()
    _emit({**me, "revoked": spiffe.is_revoked(me["spiffe_id"]), "registry": spiffe.status()}, args.json)
    return 0 if me["trusted"] else 1


def cmd_self_check(args: argparse.Namespace) -> int:
    """R32: evaluate the self-termination conditions from spec section 5
    against what is observable right now, and print the action they ask
    for. Reports; it does not halt anything by itself."""
    from sovereign.engine import termination

    signals = termination.Signals(
        low_confidence_streak=args.low_confidence_streak,
        last_latency_s=args.last_latency_s,
        latency_retries_used=args.latency_retries_used,
        langfuse_blind_s=termination.langfuse_blind_seconds(),
        alerts_last_hour=termination.alerts_in_last_hour(),
    )
    res = termination.evaluate(signals)
    enforced: dict[str, Any] = {}
    if getattr(args, "enforce", False):
        enforced = termination.enforce(res, by=args.by)
    _emit({**res, "signals": vars(signals), "enforced": enforced}, args.json)
    return 0 if res["action"] == termination.ACTIONS[0] else 1


def cmd_deny(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "deny", args.by))
    _emit(res, args.json)
    return 0


def cmd_steer(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "steer", args.by, args.text or ""))
    _emit(res, args.json)
    return 0


def cmd_episodes(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.episodes(args.kind))
    _emit(res, args.json)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if getattr(args, "config_command", None) == "set":
        resolved = config.set_key(args.key, args.value, args.by)
        _emit({"key": resolved.key, "value": resolved.value, "source": resolved.source}, args.json)
        return 0

    if args.lint:
        hits = config.lint()
        for h in hits:
            print(f"{h.path}:{h.line} {h.kind} {h.snippet}")
        print(len(hits))
        return 1 if hits else 0

    rows = {}
    for key, resolved in config.resolve_all().items():
        if config.is_secret(key):
            rows[key] = {
                "value": "set" if resolved.value else "unset",
                "default": "set" if resolved.default else "unset",
                "source": resolved.source,
            }
        else:
            rows[key] = {"value": resolved.value, "default": resolved.default, "source": resolved.source}
    _emit(rows, args.json)
    return 0


# ---- process management (up / down / worker) ----


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _port_open(address: str, timeout: float = 1.0) -> bool:
    host, _, port_s = address.rpartition(config.NET_HOST_PORT_SEP)
    if not host or not port_s.isdigit():
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, int(port_s))) == 0


def _spawn(cmd: list[str], log_path: Path, pid_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    pid_path.write_text(str(proc.pid))
    return proc.pid


def cmd_up(args: argparse.Namespace) -> int:
    config.ensure_dirs()

    # cp14 boot check: "when the kernel boots and the view hash differs
    # from heads/main, it rebuilds automatically and writes a receipt."
    # Runs before temporal/the worker start, since neither depends on the
    # projection store and a stale store should never be served even for
    # the brief window before the worker comes up.
    from sovereign.engine import projection

    boot_check = projection.ensure_fresh(by="boot")

    result = {"temporal": "already-running", "worker": "already-running", "projection": boot_check}

    if _alive(_read_pid(config.TEMPORAL_PID_FILE)) or _port_open(
        config.TEMPORAL_ADDRESS, config.CLI_PORT_PROBE_TIMEOUT_S
    ):
        pass
    else:
        host, _, port_s = config.TEMPORAL_ADDRESS.rpartition(config.NET_HOST_PORT_SEP)
        temporal_cmd = [
            "temporal", "server", "start-dev",
            "--db-filename", str(config.TEMPORAL_DB),
            "--namespace", config.TEMPORAL_NAMESPACE,
            "--headless",
            "--ip", host or config.TEMPORAL_HOST,
            "--port", port_s or config.TEMPORAL_PORT,
        ]
        pid = _spawn(temporal_cmd, config.TEMPORAL_LOG_FILE, config.TEMPORAL_PID_FILE)
        result["temporal"] = f"started pid={pid}"
        deadline = time.time() + config.CLI_UP_WAIT_DEADLINE_S
        while time.time() < deadline and not _port_open(
            config.TEMPORAL_ADDRESS, config.CLI_PORT_PROBE_TIMEOUT_S
        ):
            time.sleep(config.CLI_UP_POLL_INTERVAL_S)

    if _alive(_read_pid(config.WORKER_PID_FILE)):
        pass
    else:
        worker_cmd = [sys.executable, "-m", "sovereign.cli", "worker"]
        pid = _spawn(worker_cmd, config.WORKER_LOG_FILE, config.WORKER_PID_FILE)
        result["worker"] = f"started pid={pid}"
        time.sleep(1.0)

    _emit(result, args.json)
    return 0


def _stop_by_pid(pid: int) -> None:
    """Signals exactly this one pid -- never a process group, never a
    `pkill` pattern match. A process-group kill (os.killpg(os.getpgid(pid),
    ...)) is only as safe as the pid it is handed: a stale or reused pid --
    the recorded process already exited and the OS gave that number to
    something else, e.g. the very shell that is running `sb down` -- puts
    that shell's own process group on the receiving end, which is exactly
    what happened (2026-08-25: `bin/sb down` printed "Terminated: 15" for
    the calling shell while the real Temporal dev server, a different pid
    the stale pid file never recorded, kept running). Signaling only the
    literal pid removes that failure mode: the worst case is a no-op
    ProcessLookupError, never a group we do not own."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return
    deadline = time.time() + config.CLI_DOWN_WAIT_DEADLINE_S
    while time.time() < deadline and _alive(pid):
        time.sleep(config.CLI_UP_POLL_INTERVAL_S)
    if _alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def cmd_down(args: argparse.Namespace) -> int:
    result = {}
    for name, pid_path in (("worker", config.WORKER_PID_FILE), ("temporal", config.TEMPORAL_PID_FILE)):
        pid = _read_pid(pid_path)
        if pid is None:
            result[name] = "not-running"
            continue
        if _alive(pid):
            _stop_by_pid(pid)
            result[name] = f"stopped pid={pid}"
        else:
            result[name] = "not-running"
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass
    _emit(result, args.json)
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    from sovereign.engine.worker import run_worker

    asyncio.run(run_worker())
    return 0


def cmd_kini(args: argparse.Namespace) -> int:
    """crew#396 step 3: `kini finish` starts KiniFinishWorkflow (one run at a time, workflow id
    config.KINI_WORKFLOW_ID); `kini status` reads its progress query and, when it has finished,
    its result. Both talk to the engine the worker polls; nothing here runs a test locally."""
    from temporalio.client import Client, WorkflowFailureError
    from temporalio.exceptions import WorkflowAlreadyStartedError
    from temporalio.service import RPCError, RPCStatusCode

    from sovereign.engine import kini

    async def go() -> dict[str, Any]:
        client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)
        if args.kini_command == "finish":
            try:
                handle = await client.start_workflow(
                    kini.WORKFLOW, config.kini_workflow_params(),
                    id=config.KINI_WORKFLOW_ID, task_queue=config.TEMPORAL_TASK_QUEUE,
                )
            except WorkflowAlreadyStartedError:
                handle = client.get_workflow_handle(config.KINI_WORKFLOW_ID)
                return {"ok": True, "started": False, "already_running": True, "workflow_id": handle.id}
            out = {"ok": True, "started": True, "workflow_id": handle.id, "run_id": handle.result_run_id}
            if args.wait:
                try:
                    out["result"] = await handle.result()
                    out["ok"] = bool(out["result"].get("ok"))
                except WorkflowFailureError as e:
                    out.update(ok=False, error=str(e))
            return out
        handle = client.get_workflow_handle(config.KINI_WORKFLOW_ID)
        try:
            desc = await handle.describe()
        except RPCError as e:
            if e.status != RPCStatusCode.NOT_FOUND:
                raise
            return {"ok": True, "workflow_id": handle.id, "status": "NONE", "never_started": True}
        out: dict[str, Any] = {"ok": True, "workflow_id": handle.id, "status": desc.status.name if desc.status else None}
        out["close_time"] = desc.close_time.isoformat() if desc.close_time else None
        if desc.status is not None and desc.status.name == "RUNNING":
            out["progress"] = await handle.query("progress")
        else:
            try:
                out["result"] = await handle.result()
                out["ok"] = bool(out["result"].get("ok"))
            except WorkflowFailureError as e:
                out.update(ok=False, error=str(e))
        return out

    res = asyncio.run(go())
    if args.kini_command == "receipt":
        # The receipt platform/temporal/kini-state.yaml publishes as state/kini and
        # bin/idp-kini-state grades: line 1 is the verdict, the rest is the JSON body.
        sys.stdout.write(kini.receipt_head(res) + "\n" + json.dumps(res, sort_keys=True, default=str) + "\n")
        return 0
    _emit(res, args.json)
    return 0 if res.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sb", description="Sovereign Bus")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="start a session")
    p.add_argument("--task", required=True)
    p.add_argument("--runner", default=config.SB_DEFAULT_RUNNER)
    p.add_argument("--repo", default=None)
    p.add_argument("--by", default="cli")
    p.add_argument("--budget", type=int, default=None)
    p.add_argument("--critical", action="store_true", help="survives self-termination (crew#284 CP6, spec section 5)")
    p.add_argument("--estate", default=None, help="attach root; repo defaults to it, receipts chain under its estate dir")
    p.add_argument("--branches", type=int, default=None, help="R19: fork this many silent child sessions instead of one (sovereign/shadow)")
    _add_json(p)
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("refill", help="signal a halted session to resume with more budget")
    p.add_argument("session_id")
    p.add_argument("--tokens", type=int, required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--signed", action="store_true")
    _add_json(p)
    p.set_defaults(func=cmd_refill)

    p = sub.add_parser("verify-receipts", help="verify the signed receipt chain")
    _add_json(p)
    p.set_defaults(func=cmd_verify_receipts)

    p = sub.add_parser("audit", help="cp34 -- verify the signed receipt chain and the DAG, or explain one receipt")
    p.add_argument("--verify", action="store_true", help="verify every signature, the counter, the anchor and heads/main")
    p.add_argument("--at", default=None, help="explain the receipt with this chain hash")
    _add_json(p)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("undo", help="R7 -- revert the commit a session's receipt names")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--to", default=None, help="receipt hash to walk the chain back to; default is the newest with a commit")
    _add_json(p)
    p.set_defaults(func=cmd_undo)

    p = sub.add_parser("rewind", help="cp33 -- move heads/main to a DAG hash and rebuild the views")
    p.add_argument("hash")
    p.add_argument("--by", required=True)
    p.add_argument("--signed", action="store_true", help="sign the receipt with the trust anchor (required)")
    _add_json(p)
    p.set_defaults(func=cmd_rewind)

    p = sub.add_parser("recover", help="cp35 -- point heads/main at the last fully committed root and rebuild")
    p.add_argument("--by", default="recover")
    _add_json(p)
    p.set_defaults(func=cmd_recover)

    p = sub.add_parser("config", help="show or change engine configuration")
    _add_json(p)
    p.add_argument("--lint", action="store_true", help="report magic literals outside config.py")
    config_sub = p.add_subparsers(dest="config_command")
    p_set = config_sub.add_parser("set", help="set one config key in estate.toml")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument("--by", required=True)
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("root", help="cp9 -- show and verify the shadow Merkle root, the shadow_main head")
    _add_json(p)
    p.set_defaults(func=cmd_root)

    p = sub.add_parser("consensus", help="cp11 -- legacy versus DAG dual-read match rate")
    _add_json(p)
    p.set_defaults(func=cmd_consensus)

    p = sub.add_parser("flip", help="cp13 -- flip the DAG to primary, legacy DB to read-only (or --rollback)")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--by", required=True)
    p.add_argument("--signed", action="store_true")
    _add_json(p)
    p.set_defaults(func=cmd_flip)

    p = sub.add_parser("rebuild", help="cp14 -- replay the DAG from genesis and rewrite the projection store")
    p.add_argument("--by", default="operator")
    _add_json(p)
    p.set_defaults(func=cmd_rebuild)

    p = sub.add_parser("list", help="list sessions")
    _add_json(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one session")
    p.add_argument("session_id")
    _add_json(p)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("stop", help="stop a session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--reason", default="")
    _add_json(p)
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("approve", help="approve a waiting session (requires a signature)")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--sign", action="store_true", help="sign here and now with Touch ID, or with the 2-of-3 fallback set")
    p.add_argument("--signature", default=None, help="a signed approval envelope, as JSON or a path to it")
    _add_json(p)
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("model-consensus", help="cp30 -- three models vote via LiteLLM, policy overrules them")
    p.add_argument("--op", required=True, help="the operation to put to the models")
    p.add_argument("--destructive", action="store_true", help="force the 3-model path")
    p.add_argument("--non-destructive", action="store_true", dest="non_destructive", help="force the single cheap model")
    _add_json(p)
    p.set_defaults(func=cmd_model_consensus)

    p = sub.add_parser("identity", help="R31 -- this agent's SPIFFE identity and heartbeat state")
    p.add_argument("--beat", default=None, help="record a heartbeat for this SPIFFE ID")
    p.add_argument("--miss", default=None, help="record a missed heartbeat for this SPIFFE ID")
    p.add_argument("--sweep", action="store_true", help="charge a missed beat to every stale identity")
    _add_json(p)
    p.set_defaults(func=cmd_identity)

    p = sub.add_parser("self-check", help="R32 -- evaluate the self-termination conditions")
    p.add_argument("--low-confidence-streak", type=int, default=0, dest="low_confidence_streak")
    p.add_argument("--last-latency-s", type=float, default=0.0, dest="last_latency_s")
    p.add_argument("--latency-retries-used", type=int, default=0, dest="latency_retries_used")
    p.add_argument("--enforce", action="store_true",
                   help="act on the verdict: halt/soft_halt stop every running session, digest posts one signed digest (crew#284 CP6)")
    p.add_argument("--by", default="kernel", help="who the stop receipt names")
    _add_json(p)
    p.set_defaults(func=cmd_self_check)

    p = sub.add_parser("deny", help="deny a waiting session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    _add_json(p)
    p.set_defaults(func=cmd_deny)

    p = sub.add_parser("steer", help="steer a running session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--text", default="")
    _add_json(p)
    p.set_defaults(func=cmd_steer)

    p = sub.add_parser("episodes", help="query receipts")
    p.add_argument("--kind", default=None)
    _add_json(p)
    p.set_defaults(func=cmd_episodes)

    p = sub.add_parser("up", help="start temporal dev server + worker if not running")
    _add_json(p)
    p.set_defaults(func=cmd_up)

    p = sub.add_parser("down", help="stop worker + temporal dev server")
    _add_json(p)
    p.set_defaults(func=cmd_down)

    p = sub.add_parser("worker", help="run the worker in the foreground")
    _add_json(p)
    p.set_defaults(func=cmd_worker)

    # Plug-in hook: otto and cockpit register their own subcommands here if
    # their package is present. Absence of either is not an error (cp6).
    for modname in ("sovereign.otto.cli", "sovereign.cockpit.cli", "sovereign.attach.cli", "sovereign.intake.cli", "sovereign.presence.cli", "sovereign.shadow.cli"):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue
        register = getattr(mod, "register", None)
        if callable(register):
            register(sub)

    # otto.cli registers its own `install-plugin`. This fallback exists for
    # a checkout without otto, and it is added after the hook because
    # argparse on Python 3.11+ raises "conflicting subparser" for a second
    # parser of the same name -- which broke every `bin/sb` command under
    # a 3.11+ venv while the 3.10 venv accepted the duplicate silently.
    def cmd_install_plugin(args: argparse.Namespace) -> int:
        # otto is not importable in this checkout, so there is nothing to delegate to. Say so;
        # a NameError here (crew#325, ruff F821) used to be the only message.
        _emit({"ok": False, "error": "install-plugin needs sovereign.otto, which this checkout does not import"}, args.json)
        return 2

    if "install-plugin" not in sub.choices:
        p = sub.add_parser("install-plugin", help="install the hermes plugin (delegates to otto.cli)")
        _add_json(p)
        p.set_defaults(func=cmd_install_plugin)

    if "kini" not in sub.choices:
        p = sub.add_parser("kini", help="KINI checkpoints as one durable workflow (crew#396)")
        ks = p.add_subparsers(dest="kini_command", required=True)
        pf = ks.add_parser("finish", help="start KiniFinishWorkflow; the worker runs CP1..CP7 with retries and healing")
        pf.add_argument("--wait", action="store_true", help="block until the workflow returns")
        _add_json(pf)
        pf.set_defaults(func=cmd_kini)
        pst = ks.add_parser("status", help="progress of the running (or last) KiniFinishWorkflow")
        _add_json(pst)
        pst.set_defaults(func=cmd_kini)
        prc = ks.add_parser("receipt", help="the state/kini receipt: verdict line then JSON (kini-state CronJob)")
        prc.set_defaults(func=cmd_kini, json=True)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
