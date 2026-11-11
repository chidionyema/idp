"""The producer can honestly fill the block the grader reads.

Issue #7467: "one grader for every pull request, and a producer that can honestly fill it".
The grader is `bin/idp-bdd-proof-gate`. The producer is the estate's own lander -- the
Greenlane (`greenlane/github.py::GitHubBackend._ensure_pr`) -- which creates the pull
request and writes the `BDD-PROOF` block itself.

A producer whose block the grader refuses is a producer that cannot honestly fill it: the
only pull requests the estate raises would fail the estate's own gate. This file drives
the REAL producer (the estate's own class, with `gh` and `git` replaced by recorders) and
grades what it wrote with the REAL grader, so the two can never drift apart silently.

What is asserted here is a round trip, not a sentence:
  * the block the producer writes names the commit the pull request's head will be;
  * the grader accepts that body when the head matches;
  * the grader refuses that same body when the head is a different commit.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
if str(IDP) not in sys.path:
    sys.path.insert(0, str(IDP))

from greenlane.github import GitHubBackend  # noqa: E402 -- the repo root is the import root

GATE = IDP / "bin" / "idp-bdd-proof-gate"

REBASED = "a" * 40
LANE_HEAD = "b" * 40
CANDIDATE = "c" * 40


def produced_body() -> str:
    """The body the estate's own lander writes, captured from the real code path."""
    backend = GitHubBackend(
        repo="chidionyema/idp",
        required=["bdd", "ci-success"],
        run_url="https://github.com/chidionyema/idp/actions/runs/1",
    )
    captured: dict[str, str] = {}

    def fake_gh(path: str, method: str = "GET", fields: dict | None = None):
        if method == "POST":
            captured["body"] = (fields or {}).get("body", "")
            return {"number": 4242}
        return []

    backend.gh = fake_gh  # type: ignore[method-assign]
    backend.git = lambda *a, **k: "feat(lane): the lane's own subject"  # type: ignore[method-assign]

    number = backend._ensure_pr("lane/demo", LANE_HEAD, REBASED, CANDIDATE)
    assert number == 4242, "the producer did not create the pull request"
    assert captured.get("body"), "the producer wrote no body"
    return captured["body"]


def grade(body: str, head: str) -> tuple[int, str]:
    """Grade a pull request with the real gate, in its real JSON mode."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "GH_"))}
    p = subprocess.run(  # noqa: S603 -- fixed argv
        [sys.executable, str(GATE)],
        env=env,
        input=json.dumps(
            {"title": "the lander's own pull request", "body": body, "headRefOid": head}
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def test_the_producer_writes_a_proof_block() -> None:
    body = produced_body()
    assert "BDD-PROOF" in body
    assert "END-BDD-PROOF" in body


def test_the_producers_block_names_the_commit_the_head_will_be() -> None:
    body = produced_body()
    assert f"head: {REBASED}" in body


def test_the_grader_accepts_what_the_producer_wrote() -> None:
    rc, out = grade(produced_body(), REBASED)
    assert rc == 0, out


def test_the_grader_refuses_the_producers_body_on_another_head() -> None:
    rc, out = grade(produced_body(), "d" * 40)
    assert rc == 1, out


def test_the_producers_evidence_names_a_commit_and_a_check() -> None:
    """The lander's evidence line is evidence, not a sentence.

    It has to name the candidate it is about and at least one required check; the
    grader accepts that shape and nothing looser.
    """
    body = produced_body()
    assert f"required checks green on candidate {CANDIDATE}" in body
    assert "bdd" in body
