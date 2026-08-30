"""crew#631 CP8: a probe that cannot fail is theatre. Every probe must FAIL against each broken
door; a probe that passes one is quarantined; graduation needs one real FAIL and one real PASS."""

import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
IDP = os.path.dirname(HERE)
sys.path.insert(0, IDP)
from probes import mutations as M  # noqa: E402


def test_every_probe_fails_against_every_broken_door_and_nothing_is_quarantined():
    rows = M.run_mutations()
    assert len(rows) >= 10
    assert M.quarantine(rows) == [], [r for r in rows if not r[2]]
    assert {p for p, _, _ in rows} == {
        "l1_liveness",
        "l2_machine",
        "l3_from_sessions",
        "l4_journey",
        "verdict_grade",
    }


def test_a_probe_that_passes_a_broken_door_is_quarantined_and_the_tool_exits_1(
    tmp_path,
):
    rows = M.run_mutations(
        {"always_green": {"auth_off": lambda: [M.V.assertion("x", 1, 1, True)]}}
    )
    assert M.quarantine(rows) == ["always_green"]
    r = subprocess.run(
        [sys.executable, os.path.join(IDP, "bin", "idp-probe-mutations")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "quarantine  empty" in r.stdout, r.stdout


def test_graduation_needs_one_real_fail_and_one_real_pass(tmp_path):
    def v(ok):
        return {
            "assertions": [
                {"name": "l2.projects.status", "ok": ok},
                {"name": "l1.health.status", "ok": True},
            ]
        }

    g = M.graduation([v(True), v(False)])
    assert g["l2.projects.status"][0] == "PROVEN"
    assert (
        g["l1.health.status"][0] == "UNPROVEN"
        and "needs a real FAIL" in g["l1.health.status"][1]
    )
    d = tmp_path / "1"
    d.mkdir()
    (d / "verdict.json").write_text(json.dumps(v(False)))
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(IDP, "bin", "idp-probe-mutations"),
            "--verdicts",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert (
        "l2.projects.status" in r.stdout
        and "needs a real PASS" in r.stdout
        and "from 1 verdicts" in r.stdout
    )


def test_the_workflow_is_weekly_and_reads_real_verdicts():
    wf = yaml.safe_load(
        open(os.path.join(IDP, ".github/workflows/probe-mutations.yml"))
    )
    on = wf.get(True, wf.get("on"))
    assert on["schedule"][0]["cron"].split()[4] == "1"
    run = "\n".join(s.get("run", "") for s in wf["jobs"]["mutate"]["steps"])
    assert "verdict-langfuse" in run and "bin/idp-probe-mutations --verdicts" in run
