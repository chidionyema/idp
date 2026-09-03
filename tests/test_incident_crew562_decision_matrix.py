"""Incident 2026-08-28 (crew#562): screen access from the founder's phone went to him three times
in one evening because each session chose between mature tools on the criteria it happened to think
of. Founder: "we need a matrix for decision making ... rather than asking these questions it should
be auto ... for all requirements", then "i like the matrix, enforce it" / "rigorously, cant be
cheated" / "need evidence" / "and we eed to rview weekly" (crew#562 5458078376).

Rule: docs/decisions/decision-matrix.yaml is graded by bin/matrix-gate, and the gate refuses every
cheat a session could reach for: a score without evidence, a sentence as evidence, a weight changed
without the founder's receipted history entry, a decision outside the tie band, an in-band pick with
no tie receipt, a candidate that skips a criterion. policy/operating_model.rego rule `matrix_cited`
refuses a PR that adds an ADR or a HelmRelease without `Matrix: <slug>`. Rung 4, one test per bug.
The gate is run as a process on a mutated copy of the real file (MATRIX_FILE); opens no socket."""

import copy
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "matrix-gate"
MATRIX = ROOT / "docs" / "decisions" / "decision-matrix.yaml"
POLICY = ROOT / "policy"
SLUG = "founder-screen-access"

conftest_only = pytest.mark.skipif(
    shutil.which("conftest") is None, reason="conftest not installed"
)


def _gate(path: pathlib.Path, *argv: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, MATRIX_FILE=str(path))
    return subprocess.run(
        [sys.executable, str(GATE), *argv],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        cwd=ROOT,
    )


def _mutated(tmp_path: pathlib.Path, mutate) -> pathlib.Path:
    m = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    m = copy.deepcopy(m)
    mutate(m)
    p = tmp_path / "decision-matrix.yaml"
    p.write_text(yaml.safe_dump(m, sort_keys=False), encoding="utf-8")
    return p


def _decision(m: dict) -> dict:
    return next(d for d in m["decisions"] if d["slug"] == SLUG)


def _totals(m: dict) -> dict[str, int]:
    w = m["weights"]
    d = _decision(m)
    return {
        name: sum(w[k] * c["scores"][k]["score"] for k in w)
        for name, c in d["candidates"].items()
    }


def test_the_real_matrix_passes_the_gate():
    r = _gate(MATRIX)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS  matrix-gate" in r.stdout


def test_a_bare_number_score_is_refused(tmp_path):
    def mutate(m):
        _decision(m)["candidates"]["guacamole-vnc"]["scores"]["cost"] = 5

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1 and "FAIL  matrix-gate" in r.stdout, r.stdout


def test_a_sentence_as_evidence_is_refused(tmp_path):
    def mutate(m):
        _decision(m)["candidates"]["guacamole-vnc"]["scores"]["cost"] = {
            "score": 5,
            "evidence": "it is free, trust me",
        }

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1 and "evidence" in r.stdout, r.stdout


def test_a_weight_changed_without_a_receipted_history_entry_is_refused(tmp_path):
    def mutate(m):
        m["weights"]["cost"] += 5
        m["weights"]["maturity"] -= (
            5  # still sums to 100: only the sha lock can catch this
        )

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1 and "weights" in r.stdout, r.stdout


def test_a_decision_outside_the_tie_band_is_refused_even_with_a_receipt(tmp_path):
    def mutate(m):
        totals = _totals(m)
        loser = min(totals, key=totals.get)
        assert max(totals.values()) - totals[loser] > m["tie_band"]
        _decision(m)["decision"] = loser

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1, r.stdout


def test_an_in_band_choice_without_a_tie_receipt_is_refused(tmp_path):
    def mutate(m):
        d = _decision(m)
        totals = _totals(m)
        assert d["decision"] != max(totals, key=totals.get), (
            "the fixture must be an in-band pick"
        )
        d.pop("tie_receipt", None)

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1 and "tie" in r.stdout, r.stdout


def test_a_candidate_that_skips_a_criterion_is_refused(tmp_path):
    def mutate(m):
        del _decision(m)["candidates"]["guacamole-vnc"]["scores"]["security_by_default"]

    r = _gate(_mutated(tmp_path, mutate))
    assert r.returncode == 1, r.stdout


def test_slugs_mode_lists_the_scored_decisions():
    r = _gate(MATRIX, "--slugs")
    assert r.returncode == 0 and SLUG in json.loads(r.stdout), r.stdout


# --- matrix_cited at the PR ---------------------------------------------------------------------

LAWS = (
    "\n\n## Architecture laws\n- LAW 1 zero-gravity: n/a: docs only\n- LAW 2 fractal: n/a: no service boundary changes\n"
    "- LAW 3 nervous system: n/a: no workload changes\n- LAW 4 calibration: n/a: no prediction made\n"
)


def _rules(
    tmp_path: pathlib.Path, files: list[str], added: str, body: str, matrix=(SLUG,)
) -> set[str]:
    payload = {
        "pr": {
            "number": 1,
            "files": files,
            "added": added,
            "body": body + LAWS,
            "labels": [],
        },
        "budget_monthly_usd": 50,
        "drills": ["oke-check", "drill-heartbeat", "login-drill"],
        "matrix": list(matrix),
    }
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = subprocess.run(
        [
            "conftest",
            "test",
            "--parser",
            "json",
            "-p",
            str(POLICY),
            "-o",
            "json",
            str(p),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    rules = set()
    for result in json.loads(out):
        for failure in result.get("failures") or []:
            rules.add(failure["msg"].split(" | ")[0])
    return rules


ADR = ["docs/decisions/0010-x.md"]
ADR_ADDED = "+# 0010. Something is the standard\n+\n+- Status: PROPOSED\n"


@conftest_only
def test_an_adr_citing_a_scored_slug_passes(tmp_path):
    rules = _rules(
        tmp_path, ADR, ADR_ADDED, f"adds an ADR\n\nNo-Issue: test\nMatrix: {SLUG}"
    )
    assert "rule=matrix_cited" not in rules, rules


@conftest_only
def test_a_slug_scored_in_the_same_pr_counts(tmp_path):
    files = ADR + ["docs/decisions/decision-matrix.yaml"]
    added = ADR_ADDED + "+  - slug: new-thing\n"
    rules = _rules(
        tmp_path,
        files,
        added,
        "adds an ADR\n\nNo-Issue: test\nMatrix: new-thing",
        matrix=(),
    )
    assert "rule=matrix_cited" not in rules, rules


@conftest_only
def test_a_new_helmrelease_on_a_platform_layer_needs_a_matrix_line(tmp_path):
    files = ["platform/new-tool/helmrelease.yaml"]
    added = "+apiVersion: helm.toolkit.fluxcd.io/v2\n+kind: HelmRelease\n"
    assert "rule=matrix_cited" in _rules(
        tmp_path, files, added, "new chart\n\nNo-Issue: test\nDrill: oke-check"
    )
    rules = _rules(
        tmp_path,
        files,
        added,
        f"new chart\n\nNo-Issue: test\nDrill: oke-check\nMatrix: {SLUG}",
    )
    assert "rule=matrix_cited" not in rules, rules
