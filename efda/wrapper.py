"""L1 -- the process wrapper: checkpoint, capture, resume.

Everything the spec asks of the wrapper, in one process that never depends on
the child's cooperation:

  * a checkpoint every ``EFDA_CHECKPOINT_INTERVAL`` seconds (default 30) and
    on SIGTERM, written by the **parent**, so a SIGKILL loses <=30s of work
    instead of the whole run
  * a terminal artifact on a non-zero exit, a signal, or a hard kill
  * a kill-observer: a second process that watches the wrapper and writes the
    ``hard_kill`` artifact when the wrapper itself is SIGKILLed and cannot
  * a bounded local WAL when the sink is unreachable
  * the read-first gate: a relaunch reads the previous artifact **before** it
    starts the child, and refuses to start when the artifact is missing

The child is started in its own process group so a stall-kill of the group
reaches it, and the wrapper's own signals are forwarded to it.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time

from .contract import build_artifact, now_iso
from .store import ArtifactStore, CheckpointStore, RedisClient, RedisError

DEFAULT_CHECKPOINT_INTERVAL = 30
GRACE_PERIOD = 3.0
SCHEMA_VIOLATION_EXIT = 75


def _env(name, default=""):
    value = os.environ.get(name, "")
    return value if value else default


def build_store():
    """The artifact and checkpoint stores, wired to the environment."""
    redis = RedisClient(_env("EFDA_REDIS_HOST"), _env("EFDA_REDIS_PORT") or None)
    wal_dir = _env("EFDA_WAL_DIR", "/var/efda/wal")
    return ArtifactStore(redis, wal_dir), CheckpointStore(redis, wal_dir), redis


def identity_for(runner_id=None):
    return {
        "component_id": _env("EFDA_COMPONENT_ID", "unclassified"),
        "component_class": _env("EFDA_COMPONENT_CLASS", "unclassified"),
        "component_kind": _env("EFDA_COMPONENT_KIND", "agent"),
        "component_version": _env("EFDA_COMPONENT_VERSION", ""),
        "runner_id": runner_id or _env("EFDA_RUNNER_ID", f"run-{os.getpid()}"),
        "parent_task_id": _env("EFDA_PARENT_TASK_ID", ""),
        "tenant_id": _env("EFDA_TENANT_ID", "default"),
        "cluster": _env("EFDA_CLUSTER", "oke"),
        "namespace": _env("EFDA_NAMESPACE", "default"),
    }


def read_checkpoint_state(state_file):
    """The child's progress, as far as the wrapper can see it."""
    if not state_file or not os.path.exists(state_file):
        return "", []
    try:
        with open(state_file, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return "", []
    completed = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            completed = list(parsed.get("completed_steps") or [])
    except ValueError:
        completed = []
    return raw, completed


def write_checkpoint(store, identity, state_file):
    """Write the checkpoint. The parent does this, not the child."""
    blob, completed = read_checkpoint_state(state_file)
    checkpoint = {
        "runner_id": identity["runner_id"],
        "component_id": identity["component_id"],
        "component_class": identity["component_class"],
        "component_kind": identity["component_kind"],
        "last_seen": now_iso(),
        "state_blob": blob,
        "completed_steps": completed,
    }
    try:
        store.write(checkpoint)
    except RedisError as exc:
        sys.stderr.write(f"ARTIFACT_WRITE_FAILED checkpoint: {exc}\n")
    return checkpoint


def write_terminal_artifact(
    store, identity, exit_code, failure_class=None, capture_method="supervisor_wrapper"
):
    """The artifact a failure leaves behind."""
    if failure_class is None:
        if exit_code == 137:
            failure_class = "hard_kill"
        elif exit_code == 143:
            failure_class = "stall"
        elif exit_code == 124:
            failure_class = "timeout"
        elif exit_code > 0:
            failure_class = "exit_nonzero"
        else:
            failure_class = "none"
    artifact = build_artifact(
        component_id=identity["component_id"],
        component_class=identity["component_class"],
        component_kind=identity["component_kind"],
        component_version=identity["component_version"],
        runner_id=identity["runner_id"],
        parent_task_id=identity["parent_task_id"],
        tenant_id=identity["tenant_id"],
        cluster=identity["cluster"],
        namespace=identity["namespace"],
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero" if failure_class != "none" else "none",
        triggering_step="process_exit",
        failure_class=failure_class,
        failure_class_registry_version=_env("EFDA_FAILURE_CLASS_VERSION", "v1"),
        capture_method=capture_method,
        payloads=[
            {
                "kind": "checkpoint",
                "uri": f"efda:ckpt:{identity['runner_id']}",
            }
        ],
        hypotheses=[
            {
                "rank": 1,
                "cause": "unknown",
                "confidence": 0.0,
                "evidence_refs": [],
                "source": "wrapper",
            }
        ],
        writer_identity=_env("EFDA_WRITER_IDENTITY", "spiffe://estate/efda-wrapper"),
    )
    try:
        store.write(artifact)
    except RedisError as exc:
        sys.stderr.write(f"ARTIFACT_WRITE_FAILED artifact: {exc}\n")
        return None
    return artifact


def observe_death(wrapper_pid, runner_id):
    """The kill-observer: write the hard_kill artifact when the wrapper dies.

    It runs as a separate process, so it survives the wrapper's own SIGKILL.
    """
    interval = 0.2
    while True:
        try:
            os.kill(wrapper_pid, 0)
        except ProcessLookupError:
            break
        except PermissionError:
            break
        time.sleep(interval)

    store, _, _ = build_store()
    identity = identity_for(runner_id)
    checkpoint = None
    try:
        checkpoint = store.redis.get(f"efda:ckpt:{runner_id}") if store.redis else None
    except (RedisError, OSError):
        checkpoint = None
    payloads = [{"kind": "checkpoint", "uri": f"efda:ckpt:{runner_id}"}]
    if checkpoint:
        payloads.append(
            {
                "kind": "log_tail",
                "inline": "the wrapper was SIGKILLed; the last checkpoint stands",
            }
        )
    artifact = build_artifact(
        component_id=identity["component_id"],
        component_class=identity["component_class"],
        component_kind=identity["component_kind"],
        component_version=identity["component_version"],
        runner_id=identity["runner_id"],
        tenant_id=identity["tenant_id"],
        cluster=identity["cluster"],
        namespace=identity["namespace"],
        attempted_operation="run_to_completion",
        invariant_broken="alive",
        triggering_step="supervisor_kill_observer",
        failure_class="hard_kill",
        failure_class_registry_version=_env("EFDA_FAILURE_CLASS_VERSION", "v1"),
        capture_method="supervisor_wrapper",
        payloads=payloads,
        hypotheses=[
            {
                "rank": 1,
                "cause": "the supervising process was killed before it could write its own artifact",
                "confidence": 0.4,
                "evidence_refs": ["raw_evidence.payloads[0]"],
                "source": "wrapper",
            }
        ],
        writer_identity=_env("EFDA_WRITER_IDENTITY", "spiffe://estate/efda-wrapper"),
    )
    try:
        store.write(artifact)
    except RedisError as exc:
        sys.stderr.write(f"ARTIFACT_WRITE_FAILED observer: {exc}\n")


def read_first_gate(store, identity, log=print):
    """The read-first contract, enforced at the door.

    A relaunch reads the previous artifact before it starts anything. If the
    artifact is missing or invalid, the relaunch is refused and the gap is
    written down as a SCHEMA_VIOLATION artifact -- recursive compliance.
    """
    try:
        artifact = store.read(identity)
    except RedisError as exc:
        log(f"artifact_read=false error={exc}")
        artifact = None
    if not artifact:
        violation = build_artifact(
            component_id=identity["component_id"],
            component_class=identity["component_class"],
            component_kind=identity["component_kind"],
            runner_id=identity["runner_id"],
            tenant_id=identity["tenant_id"],
            cluster=identity["cluster"],
            namespace=identity["namespace"],
            attempted_operation="relaunch",
            invariant_broken="evidence_present",
            triggering_step="read_first_gate",
            failure_class="schema_violation",
            failure_class_registry_version=_env("EFDA_FAILURE_CLASS_VERSION", "v1"),
            capture_method="supervisor_wrapper",
            payloads=[
                {
                    "kind": "process_tree",
                    "inline": "no artifact was found at the deterministic address",
                }
            ],
            hypotheses=[],
            writer_identity=_env(
                "EFDA_WRITER_IDENTITY", "spiffe://estate/efda-wrapper"
            ),
            routing={
                "routed_to": "human_review",
                "reason": "no_artifact_at_address",
                "at": now_iso(),
            },
        )
        try:
            store.write(violation)
        except RedisError:
            pass
        log(
            "artifact_read=false action=refused reason=no_artifact routed_to=human_review"
        )
        return None
    log("artifact_read=true")
    return artifact


def run(argv):
    """Run a child under the wrapper. Returns the exit code."""
    if not argv:
        sys.stderr.write("usage: efda wrapper -- <command> [args...]\n")
        return 2

    store, checkpoint_store, redis = build_store()
    identity = identity_for()
    runner_id = identity["runner_id"]
    state_file = _env("EFDA_STATE_FILE")
    interval = float(_env("EFDA_CHECKPOINT_INTERVAL", str(DEFAULT_CHECKPOINT_INTERVAL)))

    resume = _env("EFDA_RESUME", "") in ("1", "true", "yes")
    if resume:
        artifact = read_first_gate(store, identity)
        if artifact is None:
            return SCHEMA_VIOLATION_EXIT
        checkpoint = checkpoint_store.read(runner_id)
        if checkpoint:
            log_line = f"resume_from_checkpoint=true completed_steps={checkpoint.get('completed_steps', [])}"
            print(log_line)
            if state_file and checkpoint.get("state_blob"):
                try:
                    with open(state_file, "w", encoding="utf-8") as handle:
                        handle.write(checkpoint["state_blob"])
                except OSError:
                    pass

    # The kill-observer outlives the wrapper.
    observer = None
    if _env("EFDA_OBSERVER", "1") in ("1", "true", "yes"):
        try:
            observer = subprocess.Popen(  # noqa: S603 -- fixed argv
                [
                    sys.executable,
                    "-m",
                    "efda",
                    "wrapper-observe",
                    str(os.getpid()),
                    runner_id,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            observer = None

    try:
        process = subprocess.Popen(argv, start_new_session=True)  # noqa: S603 -- the command is the point
    except OSError as exc:
        sys.stderr.write(f"failed to start {argv[0]}: {exc}\n")
        write_terminal_artifact(store, identity, 127, failure_class="exit_nonzero")
        return 127

    stop = threading.Event()

    def ticker():
        while not stop.wait(interval):
            write_checkpoint(checkpoint_store, identity, state_file)

    thread = threading.Thread(target=ticker, daemon=True)
    thread.start()

    def on_term(signum, _frame):
        write_checkpoint(checkpoint_store, identity, state_file)
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + GRACE_PERIOD
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                pass

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    # Readiness, so a supervisor can wait for the wrapper instead of guessing.
    print(
        "efda_wrapper_ready=true runner_id=%s component_class=%s resume=%s"
        % (runner_id, identity["component_class"], str(resume).lower()),
        flush=True,
    )

    exit_code = process.wait()
    if exit_code < 0:
        # A child killed by a signal reports 128+signo, the way a shell does.
        exit_code = 128 + abs(exit_code)
    stop.set()
    thread.join(timeout=1.0)

    if exit_code != 0:
        write_checkpoint(checkpoint_store, identity, state_file)
        write_terminal_artifact(store, identity, exit_code)
    else:
        write_checkpoint(checkpoint_store, identity, state_file)

    if observer is not None:
        try:
            observer.terminate()
        except OSError:
            pass
    redis.close()
    return exit_code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "wrapper-observe":
        if len(argv) < 3:
            return 2
        observe_death(int(argv[1]), argv[2])
        return 0
    if argv and argv[0] == "wrapper":
        argv = argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    return run(argv)


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    sys.exit(main())
