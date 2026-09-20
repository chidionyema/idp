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


def _propose(context, *, code="", manifest="", sql="", tests="", claim="", envelope="DEFAULT"):
    # A proposal must carry a reversibility envelope (ADR 0024) or `verify_mutation` refuses it
    # with NO_INVERSE. Every setup proposal in this suite is a reversible mutation, so the
    # default envelope is the well-formed one; the scenarios that deliberately test a MISSING or
    # defective envelope pass `envelope=None` or their own mapping.
    if envelope == "DEFAULT":
        envelope = _default_envelope(code=code, manifest=manifest, sql=sql)
    return context["door"].request(
        {
            "verb": "propose_mutation",
            "code_patch": code,
            "manifest_patch": manifest,
            "sql_migration": sql,
            "tests": tests,
            "claim": claim,
            "envelope": envelope,
        }
    )


def _default_envelope(*, code="", manifest="", sql=""):
    """The inverse a benign ledger mutation declares: apply the bundle, delete it to undo."""
    return {
        "mutation_id": "ldg-mutdoor-default",
        "target": "deployment/mutdoor",
        "forward": {
            "action": "apply_bundle",
            "parameters": {"code": bool(code), "manifest": bool(manifest), "sql": bool(sql)},
        },
        "inverse_spec": {
            "type": "deterministic_inverse",
            "action": "delete_bundle",
            "parameters": {"code": bool(code), "manifest": bool(manifest), "sql": bool(sql)},
            "verification_probe": (
                "the estate's checkout reports no mutdoor_* file from this ledger"
            ),
        },
    }


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


# ---------------------------------------------------------------------------
# Rule: a mutation carries a pre-validated inverse or it is refused (ADR 0024).
#
# OPERATIONAL proof, not a shape check: every scenario below drives the LIVE daemon over its
# real socket and asserts what `verify_mutation` actually answered. The gate's own unit tests
# (tests/test_reversibility_gate.py) prove the gate discriminates; these prove the DOOR asks,
# on every mutation, and refuses before the gauntlet runs.
# ---------------------------------------------------------------------------

# A well-formed deterministic inverse over the mutdoor fixture. The forward action and the
# inverse action differ, and the probe is a deterministic state assertion, so this is the
# "pass" half that proves the door is not a blanket refusal.
GOOD_INVERSE_ENVELOPE = {
    "mutation_id": "ldg-mutdoor-reversible",
    "target": "deployment/mutdoor",
    "forward": {
        "action": "apply_manifest",
        "parameters": {"path": "mutdoor_deploy.yaml", "replicas": 3},
    },
    "inverse_spec": {
        "type": "deterministic_inverse",
        "action": "delete_manifest",
        "parameters": {"path": "mutdoor_deploy.yaml"},
        "verification_probe": (
            "kubectl get deployment mutdoor -o jsonpath='{.metadata.name}' == "
            "ErrorFromServer/NotFound"
        ),
    },
}

ECHO_INVERSE_ENVELOPE = {
    "mutation_id": "ldg-mutdoor-echo",
    "target": "deployment/mutdoor",
    "forward": {
        "action": "apply_manifest",
        "parameters": {"path": "mutdoor_deploy.yaml", "replicas": 3},
    },
    "inverse_spec": {
        "type": "deterministic_inverse",
        "action": "apply_manifest",
        "parameters": {"path": "mutdoor_deploy.yaml", "replicas": 3},
        "verification_probe": "kubectl get deployment mutdoor == mutdoor",
    },
}

FORGED_EXEMPTION_ENVELOPE = {
    "mutation_id": "ldg-mutdoor-forged",
    "target": "bucket/mutdoor-archive",
    "subject": "sha256:" + "7f" * 32,
    "forward": {
        "action": "drop_bucket",
        "parameters": {"bucket_name": "mutdoor-archive"},
    },
    "inverse_spec": {
        "type": "irreversible_exemption",
        "justification": (
            "An exemption claimed without a signature, over a destructive forward action."
        ),
        "attestation": {
            "scheme": "estate-ed25519",
            "subject": "sha256:" + "7f" * 32,
            # The base64 of the literal "sig-live-quorum-..." -- the shape the REJECTED design
            # accepted by startswith. The door must refuse it on the signature, not the prefix.
            "public_key": "AAAA",
            "signature": "c2lnLWxpdmUtcXVvcnVtLWZvcmdlZHRva2Vu",
        },
    },
}


def _propose_with_envelope(context, envelope):
    return context["door"].request(
        {
            "verb": "propose_mutation",
            "code_patch": GOOD_CODE_PATCH,
            "manifest_patch": GOOD_MANIFEST_PATCH,
            "sql_migration": "",
            "tests": "def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
            "claim": "a mutation whose reversibility is graded by the door",
            "envelope": envelope,
        }
    )


@given("an agent has proposed a mutation touching \"code, manifest, sql\" with no envelope")
def an_agent_has_proposed_with_no_envelope(
    context: dict[str, Any], door: Door
) -> None:
    context["door"] = door
    proposal = _propose(
        context,
        code=GOOD_CODE_PATCH,
        manifest=GOOD_MANIFEST_PATCH,
        sql=GOOD_SQL,
        tests="def test_add():\n    from mutdoor_code import add\n    assert add(1, 2) == 3\n",
        claim="a mutation with no reversibility envelope",
        envelope=None,
    )
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@given("an agent has proposed a mutation whose envelope answers the forward with itself")
def an_agent_has_proposed_an_echo_inverse(
    context: dict[str, Any], door: Door
) -> None:
    context["door"] = door
    proposal = _propose_with_envelope(context, ECHO_INVERSE_ENVELOPE)
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@given(
    "an agent has proposed a destructive mutation claiming an exemption it did not sign"
)
def an_agent_has_proposed_a_forged_exemption(
    context: dict[str, Any], door: Door
) -> None:
    context["door"] = door
    proposal = _propose_with_envelope(context, FORGED_EXEMPTION_ENVELOPE)
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@given("an agent has proposed a reversible mutation with a deterministic inverse")
def an_agent_has_proposed_a_reversible_mutation(
    context: dict[str, Any], door: Door
) -> None:
    context["door"] = door
    proposal = _propose_with_envelope(context, GOOD_INVERSE_ENVELOPE)
    assert proposal.get("ok") is True, f"setup proposal was refused: {proposal!r}"
    context["ledger_id"] = proposal["ledger_id"]


@then(parsers.parse('the bundle is refused with violation code "{code}"'))
def the_bundle_is_refused_with_code(context: dict[str, Any], code: str) -> None:
    verdict = context["verdict"]
    assert verdict.get("ok") is False, (
        f"a proposal with no verifiable inverse was admitted: {verdict!r}"
    )
    assert verdict.get("admissible") is False, (
        f"the bundle was marked admissible despite having no inverse: {verdict!r}"
    )
    assert verdict.get("violation_code") == code, (
        f"expected violation_code {code!r}, got {verdict.get('violation_code')!r}: {verdict!r}"
    )


@then("the refusal names the missing envelope, not a paraphrase")
def the_refusal_names_the_envelope(context: dict[str, Any]) -> None:
    error = context["verdict"].get("error", "")
    assert "no mutation envelope" in error, (
        f"the refusal does not name the missing envelope: {error!r}"
    )


@then("the refusal names an inverse that reverses nothing")
def the_refusal_names_the_echo(context: dict[str, Any]) -> None:
    error = context["verdict"].get("error", "")
    assert "No inverse" in error or "NO_INVERSE" in error, (
        f"the refusal does not name the inverse defect: {error!r}"
    )
    assert "cannot match forward action" in error or "reverses nothing" in error, (
        f"the refusal does not name the echo: {error!r}"
    )


@then("the refusal is a signature verdict, not a prefix match")
def the_refusal_is_a_signature_verdict(context: dict[str, Any]) -> None:
    error = context["verdict"].get("error", "")
    assert "did not verify" in error, (
        f"the forged exemption was not refused on its signature: {error!r}"
    )
    assert "sig-live-quorum" not in error, (
        "the refusal names the token prefix -- that is the check that was removed"
    )


@then("the inverse is accepted and the bundle is graded on its own merits")
def the_inverse_is_accepted(context: dict[str, Any]) -> None:
    verdict = context["verdict"]
    assert verdict.get("violation_code") != "NO_INVERSE", (
        f"a valid inverse was refused: {verdict!r}"
    )
    # The door's verdict must be the gauntlet's, not a reversibility refusal: whatever the
    # gauntlet says about the code, the inverse itself was accepted.
    assert "no mutation envelope" not in verdict.get("error", ""), (
        f"the envelope was read as absent: {verdict!r}"
    )
    assert "did not verify" not in verdict.get("error", ""), (
        f"the signature path refused a plain deterministic inverse: {verdict!r}"
    )


# ---------------------------------------------------------------------------
# Rule: a declared probe is EXECUTED, not read as a string.
#
# The empirical proof the estate requires. The daemon's `verify_inverse` verb runs the probe
# command against the real OS and answers with the machine's own exit code -- so this scenario
# creates a real file, has the daemon probe for its absence (fails), deletes it (the inverse),
# and probes again (passes). A probe that merely existed as a string could not do any of that.
# ---------------------------------------------------------------------------


@given("a forward mutation has created a file on the real filesystem")
def a_forward_mutation_created_a_file(context: dict[str, Any], tmp_path: Path) -> None:
    context["artifact"] = tmp_path / "mutdoor_forward_artifact.txt"
    context["artifact"].write_text("state the forward mutation created\n")
    context["probe"] = f"test ! -e {context['artifact']}"
    context["rollback_cwd"] = str(tmp_path)


@when("the rollback path performs the inverse")
def the_rollback_path_performs_the_inverse(context: dict[str, Any], door: Door) -> None:
    context["door"] = door
    # Probe BEFORE the inverse: the file the forward created is still present, so the declared
    # assertion ("the artifact is gone") must not hold. This is the half a shape-check cannot do.
    context["probe_before"] = door.request(
        {"verb": "verify_inverse", "probe": context["probe"], "cwd": context["rollback_cwd"]}
    )
    context["artifact"].unlink()  # the inverse itself
    context["probe_after"] = door.request(
        {"verb": "verify_inverse", "probe": context["probe"], "cwd": context["rollback_cwd"]}
    )


@then("verify_inverse runs the declared probe and reports the machine's exit code")
def verify_inverse_ran_the_probe(context: dict[str, Any]) -> None:
    before = context["probe_before"]
    after = context["probe_after"]
    assert before.get("executed") is True, (
        f"the probe was not executed -- it was read as a string: {before!r}"
    )
    assert after.get("executed") is True, (
        f"the probe was not executed after the inverse: {after!r}"
    )
    assert isinstance(before.get("exit_code"), int), (
        f"no real exit code came back from the machine: {before!r}"
    )
    assert isinstance(after.get("exit_code"), int), (
        f"no real exit code came back from the machine: {after!r}"
    )


@then("the probe holds only after the inverse has run")
def the_probe_holds_only_after(context: dict[str, Any]) -> None:
    before = context["probe_before"]
    after = context["probe_after"]
    assert before.get("passed") is False, (
        f"the probe passed while the forward state was still present: {before!r}"
    )
    assert before.get("exit_code") != 0, before
    assert after.get("passed") is True, (
        f"the probe did not hold after the inverse ran: {after!r}"
    )
    assert after.get("exit_code") == 0, after


# ---------------------------------------------------------------------------
# Rule: admission DELIVERS -- the gateway pushes the branch and opens the PR.
#
# The path ADR 0025 describes only works if the last step exists: the agent never runs git, so
# the executor must push the branch and open its pull request, or the admitted mutation sits as
# a local ref that Greenlane Row 3 can never see. These steps assert delivery was ATTEMPTED and
# its outcome REPORTED -- fail-soft, because the test checkout has no writable origin and a
# failed push must still leave the mutation admitted (an admitted change is never lost to a
# delivery error).
# ---------------------------------------------------------------------------


@then("the admission reports its delivery outcome")
def the_admission_reports_its_delivery(context: dict[str, Any]) -> None:
    reply = context["admission"]
    assert "pushed" in reply, (
        f"the admit reply says nothing about delivery: {reply!r}. Without this the branch sits "
        f"local and Greenlane Row 3 never sees a pull request."
    )
    # Fail-soft contract: whatever happened, the mutation is still admitted and the reason is
    # named. A push that could not happen must not read as success, and must not lose the work.
    if reply.get("pushed") is False:
        assert reply.get("delivery_error"), (
            f"delivery failed without saying why: {reply!r}"
        )
    assert reply.get("admitted_path"), reply
