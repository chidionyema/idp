"""net-triage never proposes a fix from evidence it could not gather.

Runs the real platform/estate/libexec/triage-eval.py: the unchanged race and verdict, once per
labelled scenario in platform/estate/eval/net-crossnode, against a stub kubectl in a throwaway
HOME. The `gather-failed` scenario is the harmful case measured 2026-09-27: net-forensics produced
nothing, every grep exited 2, and the verdict proposed net-flannel-unmasq -- a live node iptables
mutation -- on no evidence at all. The only right answer there is to abstain.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parents[2] / "platform/estate/libexec/triage-eval.py"


def _rows() -> list[dict]:
    r = subprocess.run(
        [sys.executable, str(EVAL), "--json"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    return json.loads(r.stdout[: r.stdout.rindex("]") + 1])


def test_no_scenario_gets_a_harmful_proposal_and_every_scenario_passes():
    rows = _rows()
    assert len(rows) >= 11
    assert [r["id"] for r in rows if r["harmful"]] == []
    assert [r["id"] for r in rows if not r["ok"]] == []


def test_gather_failed_abstains_and_names_what_it_could_not_see():
    row = next(r for r in _rows() if r["id"] == "gather-failed")
    assert row["verdict"].startswith("VERDICT abstain: evidence unavailable")
    assert row["proposed_fix_for"] is None and row["top"] is None
    assert row["err_as_evidence"] == []
