"""BDD step definitions for `features/gates/typed-multidomain-mutation-ledger.feature`.

WHAT THIS BINDS
----------------
The four new verbs in `platform/executor/daemon.py` (`propose_mutation`, `verify_mutation`,
`seal_mutation`, `admit_mutation`) that extend the single-domain deterministic-verifier door
(`features/gates/deterministic-verifier.feature`, bound by `test_deterministic_verifier.py`) to
one ledger spanning code+manifest+SQL together, all-or-nothing. LAW 43: this reuses the SAME
`sovereign.verifier.verify()` gauntlet the single-domain door already proves, and the SAME `Door`
harness pattern that file already measured correct (real daemon subprocess, real socket, stderr
to a file never a pipe, bounded polling wait, no reaper thread) -- duplicated here rather than
imported because pytest-bdd step bindings, like the harness that drives them, are scoped to the
module that calls `scenarios(...)`.

`admit_mutation` builds a real Git commit on a new branch of the REAL checkout this daemon's own
`live_worktree()` resolves to (derived from `daemon.py`'s own path, LAW 46 -- there is no env
override for it, on purpose: a mutation must land where a human will actually look for it). The
`created_branches` fixture deletes every branch a scenario creates in its own teardown, so this
suite proves the behavior without leaving `mutation/ldg-*` litter in the checkout it runs from.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

REPO_ROOT = Path(__file__).resolve().parents[3]
STARTUP_DEADLINE_SEC = 20.0

scenarios("features/gates/typed-multidomain-mutation-ledger.feature")


class Door:
    """A live executor daemon, addressed over its UNIX socket. See `test_deterministic_verifier.py`
    for the measured defects (pipe-shared stderr, tight-spin polling, no reaper thread) this
    duplicate shape already fixes -- unchanged here, just re-stated once per module."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.socket_path = root / "executor.sock"
        self.runs_dir = root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.proc: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        env = {
            **os.environ,
            "IDP_EXECUTOR_SOCKET": str(self.socket_path),
            "IDP_EXECUTOR_RUNS": str(self.runs_dir),
            "PI_SUBAGENT": "",
        }
        self._stderr_path = self.root / "daemon.stderr"
        self._stderr_file = self._stderr_path.open("wb")
        self.proc = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "platform" / "executor" / "daemon.py")],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self._stderr_file,
            stderr=self._stderr_file,
        )
        self._await_socket()

    def stderr_text(self) -> str:
        try:
            self._stderr_file.flush()
            return self._stderr_path.read_text(errors="replace")
        except OSError:  # pragma: no cover - the file is created in start()
            return "(the daemon's stderr file could not be read)"

    def _await_socket(self) -> None:
        deadline = time.monotonic() + STARTUP_DEADLINE_SEC
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise AssertionError(
                    f"the executor daemon exited before it answered (rc="
                    f"{self.proc.returncode}): {self.stderr_text()[-2000:]!r}"
                )
            if self.socket_path.exists() and self.health().get("ok"):
                return
            time.sleep(0.02)
        detail = "(the daemon is still running and printed nothing)"
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - a wedged daemon
                self.proc.kill()
                self.proc.wait(timeout=10)
            detail = self.stderr_text()[-2000:]
        raise AssertionError(
            f"the executor daemon did not answer within {STARTUP_DEADLINE_SEC}s on "
            f"{self.socket_path}; its stderr was: {detail!r}"
        )

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(30)
            sock.connect(str(self.socket_path))
            sock.sendall(json.dumps(payload).encode() + b"\n")
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    return json.loads(b"".join(chunks).decode())
                except json.JSONDecodeError:
                    continue
            reply = b"".join(chunks)
            if not reply:
                state = (
                    f"exited rc={self.proc.returncode}"
                    if self.proc is not None and self.proc.poll() is not None
                    else "still running"
                )
                raise AssertionError(
                    f"the executor daemon closed the socket without a reply ({state}); "
                    f"its stderr was: {self.stderr_text()[-2000:]!r}"
                )
            raise AssertionError(
                f"the executor daemon closed the socket mid-reply; it sent {reply!r}, which is "
                f"not JSON. Its stderr was: {self.stderr_text()[-2000:]!r}"
            )

    def health(self) -> dict[str, Any]:
        try:
            return self.request({"verb": "health"})
        except (OSError, json.JSONDecodeError):
            return {}

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - a hung daemon
                self.proc.kill()
                self.proc.wait(timeout=10)
        try:
            self._stderr_file.close()
        except OSError:  # pragma: no cover - already closed
            pass


@pytest.fixture
def door(tmp_path: Path):
    socket_root = Path(tempfile.mkdtemp(prefix="idp-mut-"))
    d = Door(socket_root)
    d.root.mkdir(parents=True, exist_ok=True)
    d.start()
    try:
        yield d
    finally:
        d.stop()
        import shutil

        shutil.rmtree(socket_root, ignore_errors=True)


@pytest.fixture
def created_branches():
    """Every `mutation/ldg-*` branch a scenario admits, deleted from the REAL checkout at
    teardown -- `admit_mutation` builds its commit against `daemon.py`'s own `live_worktree()`,
    which is this repository, not a temp fixture (see the module docstring)."""
    names: list[str] = []
    try:
        yield names
    finally:
        for name in names:
            subprocess.run(
                ["git", "branch", "-D", name],
                cwd=REPO_ROOT,
                capture_output=True,
                check=False,
            )


GOOD_CODE_PATCH = (
    "--- a/mutdoor_code.py\n+++ b/mutdoor_code.py\n@@ -0,0 +1,2 @@\n"
    "+def add(a, b):\n"
    "+    return a + b\n"
)
GOOD_MANIFEST_PATCH = (
    "--- a/mutdoor_deploy.yaml\n+++ b/mutdoor_deploy.yaml\n@@ -0,0 +1,1 @@\n"
    "+kind: Deployment\n"
)
GOOD_SQL = "CREATE TABLE mutdoor_widgets (id INTEGER PRIMARY KEY, name TEXT);\n"
# A COMPLETE, TERMINATED statement (passes stage_structural's sqlite3.complete_statement
# check) that is nonetheless not valid SQL, so this fails stage_sql specifically, not
# stage_structural -- proving the SQL-domain stage itself, not just "some earlier stage".
BROKEN_SQL = "CREATE TABLE mutdoor_widgets (id INTEGER PRIMARY KEY, name TEXT NOT VALID GARBAGE HERE);\n"


def _propose(context, *, code="", manifest="", sql="", tests="", claim=""):
    return context["door"].request(
        {
            "verb": "propose_mutation",
            "code_patch": code,
            "manifest_patch": manifest,
            "sql_migration": sql,
            "tests": tests,
            "claim": claim,
        }
    )


# ---------------------------------------------------------------------------
# Rule: a proposal with nothing in it is refused before a ledger opens.
# ---------------------------------------------------------------------------


@given(parsers.parse('the agent is restricted to the "{tool}" tool'))
def the_agent_is_restricted_to(context: dict[str, Any], door: Door, tool: str) -> None:
    context["door"] = door
    context["mutation_tool"] = tool


@when("the agent proposes an empty mutation")
def the_agent_proposes_empty(context: dict[str, Any]) -> None:
    context["proposal"] = _propose(context)


@then(parsers.parse('the proposal is refused with the error "{message}"'))
def the_proposal_is_refused(context: dict[str, Any], message: str) -> None:
    reply = context["proposal"]
    assert reply.get("ok") is False, f"an empty proposal was accepted: {reply!r}"
    assert reply.get("error") == message, (
        f"expected error {message!r}, got {reply.get('error')!r}"
    )


@then("no ledger is opened")
def no_ledger_is_opened(context: dict[str, Any]) -> None:
    assert "ledger_id" not in context["proposal"], (
        f"a refused proposal minted a ledger id: {context['proposal']!r}"
    )
    state = context["door"].request({"verb": "health"})
    assert state.get("ledgers_pending", 0) == 0, (
        f"a refused proposal left a ledger pending: {state!r}"
    )


# ---------------------------------------------------------------------------
# Rule: a proposal spans every domain supplied, in one ledger.
# ---------------------------------------------------------------------------


@when(parsers.parse('the agent proposes a mutation touching "{domains}"'))
def the_agent_proposes_a_bundle(context: dict[str, Any], domains: str) -> None:
    context["proposal"] = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=GOOD_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="the multi-domain mutation ledger BDD proposal",
    )
    context["ledger_id"] = context["proposal"].get("ledger_id")


@then("the executor isolates the payload into one ledger spanning all three domains")
def one_ledger_spans_all_domains(context: dict[str, Any]) -> None:
    reply = context["proposal"]
    assert reply.get("ok") is True, f"the proposal was refused: {reply!r}"
    assert reply.get("ledger_id"), (
        f"a proposal must land in a ledger with an id: {reply!r}"
    )
    assert set(reply.get("domains", [])) == {"code", "manifest", "sql"}, (
        f"expected all three domains in one ledger, got: {reply.get('domains')!r}"
    )


@then("the agent is suspended pending deterministic verification")
def the_agent_is_suspended(context: dict[str, Any]) -> None:
    reply = context["proposal"]
    assert reply.get("suspended") is True, f"the agent must be suspended: {reply!r}"
    state = context["door"].request({"verb": "health"})
    assert state.get("ledgers_pending", 0) >= 1, (
        f"the daemon does not report a pending ledger: {state!r}"
    )


# ---------------------------------------------------------------------------
# Rule: verification is all-or-nothing across the bundle.
# ---------------------------------------------------------------------------


@given(parsers.parse('an agent has proposed a mutation touching "{domains}"'))
def an_agent_has_proposed_a_bundle(
    context: dict[str, Any], door: Door, domains: str
) -> None:
    context["door"] = door
    proposal = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=GOOD_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="the multi-domain mutation ledger BDD proposal",
    )
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@given(
    parsers.parse('an agent has proposed a mutation with a broken "{domain}" domain')
)
def an_agent_has_proposed_a_broken_bundle(
    context: dict[str, Any], door: Door, domain: str
) -> None:
    context["door"] = door
    assert domain == "sql", f"only the sql-broken fixture is wired up, got {domain!r}"
    proposal = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=BROKEN_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="a deliberately broken sql migration",
    )
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@when("the Deterministic Verifier evaluates the whole bundle")
def the_verifier_evaluates_the_bundle(context: dict[str, Any]) -> None:
    context["verdict"] = context["door"].request(
        {"verb": "verify_mutation", "ledger_id": context["ledger_id"]}
    )


@then(parsers.parse('every domain is reported "{status}"'))
def every_domain_is_reported(context: dict[str, Any], status: str) -> None:
    verdict = context["verdict"]
    per_domain = verdict.get("per_domain", {})
    assert per_domain, f"no per_domain verdict was returned: {verdict!r}"
    for domain, result in per_domain.items():
        assert result == status, (
            f"domain {domain!r} was {result!r}, expected {status!r}"
        )


@then("the bundle is admissible")
def the_bundle_is_admissible(context: dict[str, Any]) -> None:
    verdict = context["verdict"]
    assert verdict.get("ok") is True, f"the whole bundle failed: {verdict!r}"
    assert verdict.get("admissible") is True, (
        f"the bundle is not admissible: {verdict!r}"
    )


@then("the bundle is not admissible")
def the_bundle_is_not_admissible(context: dict[str, Any]) -> None:
    verdict = context["verdict"]
    assert verdict.get("ok") is False, f"a broken bundle verified: {verdict!r}"


@then(
    parsers.parse(
        'the "{domain}" domain carries the real stage error, not a paraphrase'
    )
)
def the_domain_carries_the_real_error(context: dict[str, Any], domain: str) -> None:
    verdict = context["verdict"]
    per_domain = verdict.get("per_domain", {})
    message = per_domain.get(domain, "")
    assert message and message != "VERIFIED", (
        f"domain {domain!r} was not marked as failed: {per_domain!r}"
    )
    assert "syntax error" in message.lower() or "near" in message.lower(), (
        f"the {domain} domain's message is not the raw SQL error: {message!r}"
    )


@then(
    parsers.parse(
        'the "{domain_a}" and "{domain_b}" domains are marked not verified for the same reason'
    )
)
def the_other_domains_are_marked_not_verified(
    context: dict[str, Any], domain_a: str, domain_b: str
) -> None:
    per_domain = context["verdict"].get("per_domain", {})
    for domain in (domain_a, domain_b):
        message = per_domain.get(domain, "")
        assert message != "VERIFIED", (
            f"domain {domain!r} was falsely marked VERIFIED in a failed bundle: {per_domain!r}"
        )
        assert "all-or-nothing" in message, (
            f"domain {domain!r} does not name the all-or-nothing reason: {message!r}"
        )


# ---------------------------------------------------------------------------
# Rule: a bundle cannot be sealed without first passing verify_mutation.
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        'an agent has proposed a mutation touching "{domains}" but has not verified it'
    )
)
def an_agent_has_proposed_but_not_verified(
    context: dict[str, Any], door: Door, domains: str
) -> None:
    context["door"] = door
    proposal = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=GOOD_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="never verified on purpose",
    )
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@when("the agent calls seal_mutation")
def the_agent_calls_seal_mutation(context: dict[str, Any]) -> None:
    context["seal_reply"] = context["door"].request(
        {"verb": "seal_mutation", "ledger_id": context["ledger_id"]}
    )


@then("the seal is refused because no verified bundle exists for that ledger")
def the_seal_is_refused(context: dict[str, Any]) -> None:
    reply = context["seal_reply"]
    assert reply.get("ok") is False, (
        f"seal_mutation sealed an unverified bundle: {reply!r}"
    )
    assert "verify_mutation" in reply.get("error", ""), (
        f"the refusal must name the missing step: {reply!r}"
    )


# ---------------------------------------------------------------------------
# Rule: the estate admits no mutation bundle without the seal, and never merges.
# ---------------------------------------------------------------------------


@given("a verified and sealed mutation bundle exists")
def a_verified_and_sealed_bundle_exists(context: dict[str, Any], door: Door) -> None:
    context["door"] = door
    proposal = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=GOOD_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="the multi-domain mutation ledger admit scenario",
    )
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]
    verdict = context["door"].request(
        {"verb": "verify_mutation", "ledger_id": context["ledger_id"]}
    )
    assert verdict.get("ok") is True, f"setup verification failed: {verdict!r}"
    sealed = context["door"].request(
        {"verb": "seal_mutation", "ledger_id": context["ledger_id"]}
    )
    assert sealed.get("ok") is True, f"setup seal failed: {sealed!r}"
    context["sealed"] = sealed


@when("admit_mutation is called with no attestation")
def admit_mutation_with_no_attestation(context: dict[str, Any]) -> None:
    context["admission"] = context["door"].request(
        {
            "verb": "admit_mutation",
            "ledger_id": context["ledger_id"],
            "attestation": None,
        }
    )


@then(parsers.parse('the admission is intercepted with violation code "{code}"'))
def the_admission_is_intercepted(context: dict[str, Any], code: str) -> None:
    reply = context["admission"]
    assert reply.get("ok") is False, f"an unattested mutation was admitted: {reply!r}"
    assert reply.get("intercepted") is True, (
        f"the interception must be explicit: {reply!r}"
    )
    assert reply.get("violation_code") == code, (
        f"expected {code!r}, got {reply.get('violation_code')!r}"
    )


@when("admit_mutation is called with the valid attestation")
def admit_mutation_with_valid_attestation(
    context: dict[str, Any], created_branches: list[str]
) -> None:
    context["admission"] = context["door"].request(
        {
            "verb": "admit_mutation",
            "ledger_id": context["ledger_id"],
            "attestation": context["sealed"]["attestation"],
        }
    )
    branch = context["admission"].get("branch")
    if branch:
        created_branches.append(branch)


@then("the bundle is admitted to a new branch named after the ledger")
def the_bundle_is_admitted_to_a_new_branch(context: dict[str, Any]) -> None:
    reply = context["admission"]
    assert reply.get("ok") is True, f"the sealed bundle was not admitted: {reply!r}"
    assert reply.get("branch") == f"mutation/{context['ledger_id']}", (
        f"expected a branch named after the ledger, got: {reply.get('branch')!r}"
    )
    assert reply.get("commit_sha"), f"no commit was produced: {reply!r}"
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", reply["branch"]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, (
        f"the branch {reply['branch']!r} does not exist in the checkout: {verify.stderr}"
    )


@then(parsers.parse('the branch is never "{name}"'))
def the_branch_is_never(context: dict[str, Any], name: str) -> None:
    assert context["admission"].get("branch") != name, (
        f"admit_mutation landed on {name!r} directly"
    )
    head = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head == name or head != context["admission"].get("branch"), (
        "admit_mutation moved the checkout's own HEAD"
    )
    # HEAD must still be exactly what it was before this scenario touched anything: admit_mutation
    # only creates a ref, it never runs checkout.
    assert head != context["admission"].get("branch"), (
        f"the checkout's HEAD moved onto the new branch: {head!r}"
    )


@then("pr_required is true")
def pr_required_is_true(context: dict[str, Any]) -> None:
    assert context["admission"].get("pr_required") is True, (
        f"admit_mutation must never claim to have merged: {context['admission']!r}"
    )
