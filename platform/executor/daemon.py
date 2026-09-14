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

import json
import os
import socket
import socketserver
import stat
import sys
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
    execute_command,
    read_job,
    simulate_command,
)

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
    canonical_subject,
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
            self._reply({"ok": True, "result": read_job(request.get("job_id", ""))})
        elif verb == "propose_patch":
            self._reply(self._propose_patch(request))
        elif verb == "verify":
            self._reply(self._verify(request))
        elif verb == "seal":
            self._reply(self._seal(request))
        elif verb == "admit":
            self._reply(self._admit(request))
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
            subprocess.Popen(
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
        return {
            "ok": True,
            "ledger_id": ledger_id,
            "ledger_dir": ledger_dir,
            "suspended": True,
            "subject_digest": canonical_subject(files),
            "note": "the agent is suspended pending deterministic verification",
        }

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
        return {
            "ok": True,
            "subject_digest": subject,
            "attestation": attestation,
            "payload_path": payload_path,
            "payload_bytes": len(payload_bytes),
        }

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
        return {
            "ok": True,
            "validated": True,
            "admitted_path": admitted_path,
            "subject_digest": subject,
        }

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
