"""idp#3525 CP4, VER-03: the claim-graph (DoD v3) reused as the NL verifier for NL candidates.

Spec: "The claim-graph mechanism (DoD v3) SHALL be pointed at NL output candidates as the NL
verifier (reuse, not new build)." ACCEPT: claim-graph run over candidate outputs produces
verdicts recorded in trace. METHOD: integration test.

Honest scope, named per docs/tickets/2026-09-15-dod-v3-claim-graph.md: the literal claim-graph
that ticket describes (a Postgres claims/verifications schema, a signed 5-verifier fleet) is
"scoped, not built" -- roughly two-thirds of it already exists under other names, and the ticket
explicitly does not authorize building the rest in this pass. What IS real, already built and
already wired into rules.yaml's `epistemic` rule is bin/idp-epistemic (a symlink to
bin/epistemic_firewall.py, same file): a deterministic, non-self-graded gate that refuses a
first-person claim of completed work unless the transcript backing it carries THREE INDEPENDENT
pieces of evidence, at least one reading state the claimant did not author. That -- not a
not-yet-built graph store -- is this estate's real claim-graph mechanism today, and it is what
VER-03 points at NL output candidates.

This module runs the real gate as a subprocess against a real transcript file, the same way
sovereign/tests/bdd/test_epistemic_and_trajectory.py already grades it ("by the exit code of the
executable a person would run", its own words): no import of the library under test, no second
implementation of its evidence rules.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

IDP_ROOT = Path(__file__).resolve().parent.parent.parent
EPISTEMIC_GATE = IDP_ROOT / "bin" / "idp-epistemic"

_VERDICT_BY_EXIT_CODE = {0: "VERIFIED", 1: "REFUSED", 2: "BLIND"}


def _write_transcript(turns: list[dict[str, Any]], tmp_dir: Path) -> Path:
    """pi's real nesting -- every turn under a `message` key, the same shape the epistemic
    gate's own BDD fixtures use (test_epistemic_and_trajectory.py's `_write`)."""
    path = tmp_dir / "session.jsonl"
    path.write_text(
        "\n".join(json.dumps({"type": "message", "message": t}) for t in turns) + "\n"
    )
    return path


def grade_candidate(
    candidate: dict[str, Any], *, gate: Path = EPISTEMIC_GATE
) -> dict[str, Any]:
    """Run the real gate over one NL output candidate's transcript, by its exit code.

    `candidate` carries `id` and `turns` -- the transcript backing the candidate's own claim,
    in pi's nested shape (a list of `{"role": ..., "content": [...]}` turns).
    """
    with tempfile.TemporaryDirectory(prefix="idp-claim-graph-") as td:
        transcript = _write_transcript(candidate.get("turns", []), Path(td))
        completed = subprocess.run(  # noqa: S603 -- fixed argv, no shell, path from this checkout
            [sys.executable, str(gate), str(transcript)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    return {
        "candidate_id": candidate.get("id"),
        "verdict": _VERDICT_BY_EXIT_CODE.get(completed.returncode, "UNKNOWN"),
        "exit_code": completed.returncode,
        "detail": (completed.stdout + completed.stderr).strip(),
    }


def run_claim_graph(
    candidates: list[dict[str, Any]], *, gate: Path = EPISTEMIC_GATE
) -> list[dict[str, Any]]:
    """VER-03's ACCEPT line: a claim-graph run over candidate outputs produces verdicts recorded
    in the trace. The trace IS the returned list -- one entry per candidate, in order, each
    carrying the candidate's own id so a caller can join a verdict back to its output."""
    return [grade_candidate(c, gate=gate) for c in candidates]
