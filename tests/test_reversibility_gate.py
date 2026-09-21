"""The reversibility gate (bin/idp-reversibility-gate): a mutation with no inverse is refused.

Rung 4, incident: the estate had three things that look like reversibility and no requirement
that a mutation carry its inverse -- `bin/idp-rollback-only-diff` gates a diff that is ALREADY a
rollback, `rewind` is a destructive capability an agent may invoke, and ADR 0024 routes the
un-undoable to a human. Nothing demanded the artefact. This gate adds that demand as a field on
the mutation envelope the ledger door already consumes.

Proved both ways, and the exemption path is proved with a REAL keypair rather than a committed
one: `prefix-forgery.json` carries a `sig-live-quorum-...` string, which is the shape the
rejected implementation accepted by `startswith`, and it must be refused by the ed25519 check
`sovereign.verifier.verify_attestation` runs. A genuinely signed attestation over the same
subject must pass -- so the refusal is a signature verdict, not an accident of parsing.

BLIND is a third state (LAW 38): a gate that cannot read its schema or its verifier has not
found a defect. Every unreadable-input path exits 2, never 1.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-reversibility-gate"
BAD = ROOT / "tests" / "fixtures" / "reversibility" / "bad"
GOOD = ROOT / "tests" / "fixtures" / "reversibility" / "good"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_good_fixtures_pass():
    r = _run(str(GOOD))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASSED: deterministic inverse verified" in r.stdout


def test_bad_fixtures_refuse():
    r = _run(str(BAD))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "INVALID_INVERSE" in r.stdout
    assert "SCHEMA_REJECTED" in r.stdout
    assert "did not verify" in r.stdout


def test_prefix_forgery_is_refused_by_signature_not_by_luck():
    """The specific string the rejected design accepted must not admit a destructive forward."""
    forgery = json.loads((BAD / "prefix-forgery.json").read_text())
    assert forgery["forward"]["action"] == "drop_bucket"
    token = base64.b64decode(forgery["inverse_spec"]["attestation"]["signature"]).decode()
    assert token.startswith("sig-live-quorum-"), (
        "the fixture must carry the magic-prefix shape, or this test proves nothing"
    )
    r = _run(str(BAD / "prefix-forgery.json"))
    assert r.returncode == 1
    assert "did not verify" in r.stdout


@pytest.mark.skipif(
    pytest.importorskip("cryptography", reason="crypto library absent") is None,
    reason="cryptography not installed",
)
def test_a_genuinely_signed_exemption_passes(tmp_path):
    """The other half: the exemption path is not a blanket refusal.

    A fresh keypair signs the envelope's subject; the gate must accept it. This fixture cannot
    live in git as static bytes without committing a private key, which is why it is generated
    here.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    subject = "sha256:" + "ab" * 32
    envelope = {
        "mutation_id": "mut-real-exemption-9001",
        "target": "bucket/cold-archive-2024",
        "subject": subject,
        "forward": {
            "action": "drop_bucket",
            "parameters": {"bucket_name": "cold-archive-2024"},
        },
        "inverse_spec": {
            "type": "irreversible_exemption",
            "justification": (
                "Purging expired compliance archives under the retention cycle; the data is "
                "past its regulatory hold and no restore target exists."
            ),
            "attestation": {
                "scheme": "estate-ed25519",
                "subject": subject,
                "public_key": base64.b64encode(pub).decode(),
                "signature": base64.b64encode(sk.sign(subject.encode())).decode(),
            },
        },
    }
    path = tmp_path / "envelope.json"
    path.write_text(json.dumps(envelope))
    r = _run(str(path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "exemption attestation verified" in r.stdout


def test_a_signature_over_a_different_subject_is_refused(tmp_path):
    """A signature is valid only for the subject it was made over."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    signed_subject = "sha256:" + "aa" * 32
    presented_subject = "sha256:" + "bb" * 32
    envelope = {
        "mutation_id": "mut-wrong-subject-9002",
        "target": "bucket/cold-archive-2024",
        "subject": presented_subject,
        "forward": {
            "action": "drop_bucket",
            "parameters": {"bucket_name": "cold-archive-2024"},
        },
        "inverse_spec": {
            "type": "irreversible_exemption",
            "justification": (
                "A justification long enough to pass the length check, over a swapped subject."
            ),
            "attestation": {
                "scheme": "estate-ed25519",
                "subject": signed_subject,
                "public_key": base64.b64encode(pub).decode(),
                "signature": base64.b64encode(sk.sign(signed_subject.encode())).decode(),
            },
        },
    }
    path = tmp_path / "envelope.json"
    path.write_text(json.dumps(envelope))
    r = _run(str(path))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not verify" in r.stdout


def test_blind_paths_exit_two_and_never_refuse():
    """LAW 38: a machine that cannot judge has not found a defect."""
    no_args = _run()
    assert no_args.returncode == 2, no_args.stdout + no_args.stderr
    assert "BLIND" in no_args.stderr

    missing = _run("/nonexistent/envelope.json")
    assert missing.returncode == 2
    assert "BLIND" in missing.stderr


# --- the door itself: verify_mutation refuses a proposal with no inverse ---

def _daemon_module():
    import importlib.util as _ilu

    path = ROOT / "platform" / "executor" / "daemon.py"
    spec = _ilu.spec_from_file_location("idp_executor_daemon_revtest", path)
    mod = _ilu.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_daemon_refuses_a_proposal_with_no_envelope():
    """`_mutation_is_reversible` is the daemon's one question to the gate (LAW 43)."""
    daemon = _daemon_module()
    handler = daemon.Handler
    ok, why = handler._mutation_is_reversible(None, {"code_patch": "x"})
    assert ok is False
    assert "no mutation envelope" in why


def test_the_daemon_accepts_a_proposal_with_a_valid_inverse():
    daemon = _daemon_module()
    envelope = json.loads((GOOD / "scale-deployment.json").read_text())
    ok, why = daemon.Handler._mutation_is_reversible(None, {"envelope": envelope})
    assert ok is True, why


def test_the_daemon_refuses_a_proposal_with_a_forged_exemption():
    daemon = _daemon_module()
    envelope = json.loads((BAD / "prefix-forgery.json").read_text())
    ok, why = daemon.Handler._mutation_is_reversible(None, {"envelope": envelope})
    assert ok is False
    assert "NO_INVERSE" in why


# --- operational: the probe is EXECUTED, not merely declared -------------------------------

def test_the_probe_runs_against_the_real_filesystem(tmp_path):
    """The claim that matters: a probe string becomes a real command with a real exit code.

    Before `_run_inverse_probe` existed, the probe was a JSON string no code read -- a test
    described in a document, never taken. This is the empirical proof the estate's own rule
    requires: a file is created, the inverse (delete it) is performed, and the declared probe
    (`test ! -e ...`) is executed against the real OS. The daemon reports the machine's exit
    code, not a parse of the string.
    """
    daemon = _daemon_module()
    artifact = tmp_path / "mutdoor_created_by_forward.txt"
    artifact.write_text("the forward mutation")  # forward: the file exists
    probe = f"test ! -e {artifact}"
    # Forward state: the file is still there, so the inverse's probe must FAIL (exit 1).
    before = daemon.Handler._run_inverse_probe(None, probe, str(tmp_path))
    assert before["executed"] is True, before
    assert before["passed"] is False, f"a probe passed while the forward state was present: {before}"
    assert before["exit_code"] == 1, before

    # Perform the inverse: delete what the forward created.
    artifact.unlink()
    after = daemon.Handler._run_inverse_probe(None, probe, str(tmp_path))
    assert after["executed"] is True, after
    assert after["passed"] is True, f"the probe did not hold after the inverse ran: {after}"
    assert after["exit_code"] == 0, after


def test_an_empty_probe_is_blind_not_a_pass(tmp_path):
    daemon = _daemon_module()
    result = daemon.Handler._run_inverse_probe(None, "   ", str(tmp_path))
    assert result["executed"] is False
    assert result["passed"] is False


def test_a_probe_that_cannot_run_is_blind_not_a_pass(tmp_path):
    """LAW 38: a probe the machine cannot execute has not found a defect."""
    daemon = _daemon_module()
    result = daemon.Handler._run_inverse_probe(
        None, "this-command-does-not-exist-9f3a2b", str(tmp_path)
    )
    assert result["executed"] is True  # the shell ran; the command inside it failed
    assert result["passed"] is False  # and that is a real non-zero exit, not a pass


# --- delivery: the gateway pushes the branch and opens the PR (option A, 2026-09-19) --------

def test_admit_delivers_by_pushing_and_opening_a_pr():
    """`admit_mutation` must not stop at a local ref -- the sanctioned path has to be reachable.

    Before `_deliver_mutation` existed, the executor built `refs/heads/mutation/<ledger_id>` and
    stopped: nothing pushed it, no PR existed, and Greenlane Row 3 (which lists open mutation
    PRs) had nothing to find. The whole point is that an AGENT never runs git -- the gateway
    delivers -- so the delivery must be part of the admit reply.
    """
    daemon = _daemon_module()
    calls: list = []

    def _fake_run(argv, **kwargs):
        calls.append(argv)
        code = 0

        class _R:
            returncode = code
            stdout = "https://github.com/chidionyema/idp/pull/9999\n" if "pr" in argv else ""
            stderr = ""

        return _R()

    import types

    handler = types.SimpleNamespace(live_worktree=lambda: "/tmp/x")
    handler._deliver_mutation = daemon.Handler._deliver_mutation.__get__(handler)

    import unittest.mock as mock

    with mock.patch("subprocess.run", _fake_run):
        result = handler._deliver_mutation("mutation/ldg-xyz", "a claim")

    assert result["pushed"] is True, result
    assert "pull/9999" in result.get("pr_url", ""), result
    assert any("push" in c for c in calls), f"git push was not run: {calls}"
    assert any("pr" in c and "create" in c for c in calls), f"gh pr create was not run: {calls}"


def test_delivery_failure_does_not_lose_the_admission():
    """Fail-soft: an admitted mutation whose push fails is still admitted, and says why."""
    daemon = _daemon_module()
    import types
    import unittest.mock as mock

    class _Fail:
        returncode = 128
        stdout = ""
        stderr = "fatal: could not read Username for 'https://github.com'"

    handler = types.SimpleNamespace(live_worktree=lambda: "/tmp/x")
    handler._deliver_mutation = daemon.Handler._deliver_mutation.__get__(handler)

    with mock.patch("subprocess.run", return_value=_Fail()):
        result = handler._deliver_mutation("mutation/ldg-xyz", "a claim")

    assert result["pushed"] is False
    assert "could not read Username" in result["delivery_error"]


def test_admit_mutation_calls_delivery():
    """The wire: admit_mutation must reach _deliver_mutation, or the path stays unreachable."""
    subprocess.run(["true"], check=True)
    src = (ROOT / "platform" / "executor" / "daemon.py").read_text()
    assert "_deliver_mutation(branch, claim)" in src, (
        "admit_mutation does not call _deliver_mutation -- the admitted branch would sit "
        "local and Greenlane Row 3 would never see a pull request"
    )
    assert "**delivery" in src, "the delivery result is not folded into the admit reply"
