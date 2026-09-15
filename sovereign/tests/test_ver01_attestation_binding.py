"""idp#3525 CP4, VER-01: attestation stays bound to the SHA-256 of verified bytes.

Spec (docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md section 4):
"ACCEPT: mutation of verified bytes invalidates attestation. METHOD: unit test."

This calls the real gauntlet (`Ledger` -> `verify()`) directly, in-process -- the BDD suite's
`Door` fixture exercises the same pipeline over the executor daemon's socket, which is the right
tool for proving the transport, but a plain unit test proving a property of `verify()` and
`verify_attestation()` themselves needs neither a daemon nor a socket. No new logic is added
here: every function called below already exists in sovereign/verifier.py.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from sovereign.verifier import (
    Ledger,
    ProposedFile,
    canonical_subject,
    verify,
    verify_attestation,
)

_TESTS = "from greet import greet\n\n\ndef test_greet():\n    assert greet() == 'hi'\n"


def _proposal() -> list[ProposedFile]:
    return [
        ProposedFile(path="greet.py", lines=["def greet():\n", "    return 'hi'\n"])
    ]


def _run_gauntlet(files: list[ProposedFile]) -> dict:
    ledger = Ledger(
        ledger_id=f"ver01-{uuid.uuid4().hex[:8]}",
        ledger_dir=Path(tempfile.mkdtemp(prefix="idp-ver01-")),
        files=files,
        tests=_TESTS,
        claim="greet returns 'hi'",
    )
    return verify(ledger)


def test_a_candidate_that_passes_the_gauntlet_is_attested_over_its_own_bytes() -> None:
    verdict = _run_gauntlet(_proposal())
    assert verdict["ok"] is True, (
        f"the gauntlet did not verify a passing candidate: {verdict!r}"
    )
    assert verdict["attestation"] is not None
    subject = verdict["subject_digest"]
    assert subject == canonical_subject(_proposal())
    assert verify_attestation(verdict["attestation"], subject) is True


def test_mutating_the_verified_bytes_after_attestation_invalidates_it() -> None:
    original = _proposal()
    verdict = _run_gauntlet(original)
    assert verdict["ok"] is True, (
        f"the gauntlet did not verify the baseline candidate: {verdict!r}"
    )
    attestation = verdict["attestation"]

    mutated = [
        ProposedFile(path="greet.py", lines=["def greet():\n", "    return 'bye'\n"])
    ]
    mutated_subject = canonical_subject(mutated)

    assert mutated_subject != verdict["subject_digest"], (
        "the mutation must actually change the subject digest, or this test proves nothing"
    )
    assert verify_attestation(attestation, mutated_subject) is False, (
        "an attestation minted over the original bytes admitted a mutated subject"
    )
    # And the original subject the attestation was actually minted over still holds --
    # the invalidation above is a property of the SUBJECT presented, not a revoked key.
    assert verify_attestation(attestation, verdict["subject_digest"]) is True
