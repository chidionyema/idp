"""The nine completeness questions, enforced at the merge point.

The requirement came from an outside proposal (catalog-gate-v0, 2026-10-31) that asked
nine questions of every capability in a catalogue. The estate already keeps one catalogue
-- catalog/estate-capability-registry.json, written by bin/capability-index and judged by
bin/registry-gate -- so the questions were mapped onto that store instead of building a
second one (law 6: one of each layer).

These tests are the gate's own proof. Each one carries the case that must trip it, because
a test that cannot fail is not a test:

  * a record that leaves a question in silence is a HOLE and is refused;
  * coverage below the committed floor is a REGRESSION and is refused;
  * an unknown that is DECLARED (in the record's blind list) is not a hole -- the estate
    may be blind, it may not be silent;
  * a measured "none" (no known issue, no mirror) is a value, not an unknown;
  * the committed witness and the committed floor agree with a fresh generation of the tree.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOOR = REPO / "bin" / "capability-index"
GATE = REPO / "bin" / "registry-gate"
SNAPSHOT = REPO / "catalog" / "estate-capability-registry.json"
BASELINE = REPO / "catalog" / "estate-completeness-baseline.json"

THE_NINE = (
    "owner",
    "description",
    "status",
    "last_verified",
    "dependencies",
    "interfaces",
    "known_issues",
    "mirrors",
    "metrics",
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def door():
    return _load(DOOR, "capability_index")


@pytest.fixture()
def gate():
    return _load(GATE, "registry_gate")


def a_complete_record(door, cap_id="cap:tool/completeness-example"):
    """A record that answers every question, one of them with a value."""
    return {
        "id": cap_id,
        "kind": "tool",
        "owner": "estate-runtime",
        "summary": "a record that answers all nine questions",
        "health": {"state": "operating"},
        "proof": {"proven_at": "2026-10-31T00:00:00+00:00"},
        "contract": {
            "inputs": ["in"],
            "outputs": ["out"],
            "errors": [],
            "depends_on": [],
        },
        "depends_on": [],
        "known_issues": [],
        "mirrors": [],
        "metrics": [{"name": "calls"}],
        "blind": [],
    }


# --------------------------------------------------------------------------------------
# the questions themselves


def test_the_nine_questions_are_the_nine_the_proposal_names(door):
    assert tuple(door.COMPLETENESS_QUESTIONS) == THE_NINE


def test_every_committed_record_answers_every_question(door):
    """The committed witness has no hole: no record is silent about any of the nine."""
    payload = json.loads(SNAPSHOT.read_text())
    coverage = door.completeness_coverage(payload["records"])
    holes = door.completeness_holes(coverage)
    assert holes == [], "holes in the committed witness: {}".format(holes)


def test_the_committed_coverage_is_at_or_above_the_committed_floor(door):
    """The ratchet: coverage may only improve. A fall is a refusal, not a note."""
    payload = json.loads(SNAPSHOT.read_text())
    coverage = door.completeness_coverage(payload["records"])
    baseline = json.loads(BASELINE.read_text())
    regressions = door.completeness_regressions(coverage, baseline)
    assert regressions == [], "coverage fell below the floor: {}".format(regressions)


def test_the_floor_is_a_ratio_and_survives_a_deleted_capability(door):
    """Deleting a capability must not lower the floor: the comparison is a ratio."""
    record = a_complete_record(door)
    coverage = door.completeness_coverage([record])
    baseline = door.completeness_baseline(coverage)
    assert door.completeness_regressions(coverage, baseline) == []
    # the same record, plus a second one that answers nothing: the ratio must fall, and
    # a fall is a refusal -- the floor is per record, not per capability count.
    silent = dict(record)
    silent["id"] = "cap:tool/silent"
    silent.pop("known_issues")
    wider = door.completeness_coverage([record, silent])
    assert [
        r for r in door.completeness_regressions(wider, baseline) if "known_issues" in r
    ]


def test_an_empty_catalogue_is_refused(door):
    """A catalogue with no records at all is not a clean bill of health."""
    baseline = json.loads(BASELINE.read_text())
    empty = door.completeness_coverage([])
    regressions = door.completeness_regressions(empty, baseline)
    assert any("empty" in r for r in regressions), regressions


# --------------------------------------------------------------------------------------
# the falsifiers: the gate must be able to fail


def test_a_record_that_is_silent_about_a_question_is_a_hole(door):
    """The falsifier: no value and no declared unknown. That is a hole."""
    record = a_complete_record(door)
    record.pop("known_issues")
    coverage = door.completeness_coverage([record])
    holes = door.completeness_holes(coverage)
    assert any("known_issues" in h for h in holes), holes


def test_a_declared_unknown_is_not_a_hole(door):
    """The estate may be blind. It may not be silent about being blind."""
    record = a_complete_record(door)
    record.pop("known_issues")
    record["blind"] = list(record.get("blind") or []) + ["known_issues"]
    coverage = door.completeness_coverage([record])
    holes = door.completeness_holes(coverage)
    assert not any("known_issues" in h for h in holes), holes


def test_a_measured_none_is_a_value_not_an_unknown(door):
    """No known issue is a fact about the capability, not a gap in the catalogue."""
    record = a_complete_record(door)
    coverage = door.completeness_coverage([record])
    row = coverage["questions"]["known_issues"]
    assert row["none"] == 1
    assert row["measured"] == 1
    assert row["unknown"] == 0
    assert row["holes"] == 0


def test_the_gate_refuses_a_hole_in_the_witness(gate, door, tmp_path):
    """The merge-point check: a witness with a hole is refused, with the hole named."""
    record = a_complete_record(door)
    record.pop("mirrors")
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"records": [record]}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            door.completeness_baseline(
                door.completeness_coverage([a_complete_record(door)])
            )
        )
    )
    problems, facts = gate.check_completeness(door, snapshot, baseline)
    assert problems, "the gate accepted a witness with a hole"
    assert any("mirrors" in p for p in problems), problems
    assert facts["holes"], facts


def test_the_gate_refuses_coverage_below_the_floor(gate, door, tmp_path):
    """The merge-point check: coverage below the committed floor is refused."""
    record = a_complete_record(door)
    record.pop("mirrors")  # this record never measured the mirrors question
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"records": [record]}))
    baseline = json.loads(BASELINE.read_text())
    strict = json.loads(json.dumps(baseline))
    strict["questions"]["mirrors"]["measured"] = 1
    strict["questions"]["mirrors"]["total"] = 1
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(strict))
    problems, _facts = gate.check_completeness(door, snapshot, baseline_path)
    assert problems, "the gate accepted coverage below the floor"
    assert any("mirrors" in p for p in problems), problems
    assert any("fell from" in p for p in problems), problems


def test_the_gate_proves_its_own_falsifiers(door):
    """bin/registry-gate carries the cases that must trip it, and they do trip."""
    gate = _load(GATE, "registry_gate")
    failures, facts = gate.completeness_falsifiers(door)
    assert failures == [], failures
    assert facts["hole"], facts
    assert facts["regression"], facts


def test_a_missing_floor_is_refused_not_assumed(gate, door, tmp_path):
    """No committed floor means no verdict: the gate says so instead of inventing one."""
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"records": [a_complete_record(door)]}))
    problems, _facts = gate.check_completeness(door, snapshot, tmp_path / "absent.json")
    assert any("no committed baseline" in p for p in problems), problems


# --------------------------------------------------------------------------------------
# the enrichment is deterministic, and it is a pure function of the tree


def test_the_witness_carries_no_home_path(door):
    """The witness is the same bytes on every machine: no user's absolute home path.

    2026-10-31: the intent founder.decision ships defaults like
    "/Users/roseonyema/Documents/code/idp", and the snapshot carried the founder's name
    onto every other machine -- the witness was not reproducible, and the estate's own
    test said so. The writer folds any home directory to '~', so the same source text
    yields the same witness whoever generates it.
    """
    text = SNAPSHOT.read_text()
    assert "/Users/" not in text
    assert str(Path.home()) not in text
    # no unfolded home path is left anywhere in the witness (a directory that merely
    # happens to be called "home" is not a home path, and the rule knows the difference)
    assert door.HOME_PATH_RE.search(text) is None
    # the rule itself, proven on a known-bad sample
    assert door.machine_independent("/Users/someone/Documents/code/idp") == (
        "~/Documents/code/idp"
    )
    assert door.machine_independent("/home/runner/work/idp") == "~/work/idp"
    # and it must not eat a URL path or a directory that is called "home"
    assert door.machine_independent("https://example.com/home/user") == (
        "https://example.com/home/user"
    )
    assert door.machine_independent("packages/app/src/modules/home/") == (
        "packages/app/src/modules/home/"
    )


def test_the_enrichment_reproduces_the_committed_answers(door):
    """The enrichment is a pure function of the tree: it reproduces the witness.

    The whole-witness drift check belongs to bin/registry-gate (it regenerates the tree
    and compares the bytes); here one real capability is re-enriched and must answer
    exactly what the committed witness says it answers.
    """
    payload = json.loads(SNAPSHOT.read_text())
    mirrored = [r for r in payload["records"] if r.get("mirrors")]
    assert mirrored, (
        "the witness has no mirrored capability -- the mirrors answer is dead"
    )
    ctx = door.Context(idp=REPO, home=None)
    record = dict(mirrored[0])
    enriched = door.enrich_completeness(ctx, [record])[0]
    assert enriched["mirrors"] == mirrored[0]["mirrors"]
    assert enriched["known_issues"] == mirrored[0]["known_issues"]
