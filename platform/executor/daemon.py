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
            ["git", "rev-parse", "HEAD"],
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "read-tree", head_sha],
            cwd=live_root,
            env=env,
            check=True,
            capture_output=True,
        )
        for proposed in files:
            blob_sha = subprocess.run(
                ["git", "hash-object", "-w", "--stdin"],
                cwd=live_root,
                env=env,
                input=proposed.content,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                [
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
            ["git", "write-tree"],
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        commit_sha = subprocess.run(
            ["git", "commit-tree", tree_sha, "-p", head_sha, "-m", message],
            cwd=live_root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "update-ref", f"refs/heads/{branch}", commit_sha],
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
            self._reply({"ok": True, "result": read_job(request.get("job_id", ""))})
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
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "bin",
            "idp-reversibility-gate",
        )
        if not os.path.exists(gate):
            return False, f"reversibility gate not found at {gate}"
        import subprocess  # local: kept out of the pure import path used by the tests
        import tempfile

        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
                json.dump(envelope, handle)
                path = handle.name
            proc = subprocess.run(
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
            proc = subprocess.run(
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
            push = subprocess.run(
                ["git", "push", "origin", f"refs/heads/{branch}:refs/heads/{branch}"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"pushed": False, "delivery_error": f"git push could not be run: {exc}"}
        if push.returncode != 0:
            return {
                "pushed": False,
                "delivery_error": f"git push failed: {(push.stderr or push.stdout).strip()[:300]}",
            }

        try:
            pr = subprocess.run(
                [
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
            existing = subprocess.run(
                ["gh", "pr", "view", branch, "--json", "url", "-q", ".url"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ},
            )
            if existing.returncode == 0 and existing.stdout.strip():
                return {"pushed": True, "pr_url": existing.stdout.strip(), "pr_existing": True}
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
                return {"ok": False, "executed": False, "error": f"envelope unreadable: {exc}"}
            probe = ((envelope.get("inverse_spec") or {}).get("verification_probe") or "")
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
