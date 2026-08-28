"""crew#562, 2026-08-28: the same requirement went to the founder three times in one evening.

Sunshine or Guacamole, then "does it have the Sunshine features", then "what about Apple". Each
was answerable from criteria the estate already holds as laws. The founder's ruling: "we need a
matrix for decision making — rather than asking these questions it should be auto — for all
requirements — just reference matrix, because we solve once and forever". This test holds the one
reference matrix (docs/decisions/decision-matrix.yaml, ADR 0009): weights sum to 100, every worked
decision scores every criterion, and the recorded decision IS the top score.
"""
from pathlib import Path

import yaml

MATRIX = Path(__file__).resolve().parents[1] / "docs" / "decisions" / "decision-matrix.yaml"


def _load():
    return yaml.safe_load(MATRIX.read_text())


def score(weights: dict, scores: dict) -> int:
    return sum(weights[k] * scores[k] for k in weights)


def test_weights_sum_to_one_hundred():
    m = _load()
    assert sum(m["weights"].values()) == 100, m["weights"]
    assert 0 < m["tie_band"] < 50


def test_every_decision_scores_every_criterion_zero_to_five():
    m = _load()
    for d in m["decisions"]:
        for name, c in d["candidates"].items():
            assert set(c["scores"]) == set(m["weights"]), (d["slug"], name)
            assert all(0 <= v <= 5 for v in c["scores"].values()), (d["slug"], name)


def test_the_recorded_decision_is_the_top_score():
    m = _load()
    for d in m["decisions"]:
        ranked = sorted(d["candidates"], key=lambda n: score(m["weights"], d["candidates"][n]["scores"]), reverse=True)
        assert d["decision"] == ranked[0], (d["slug"], ranked)
        assert d["receipt"].startswith("https://"), d["slug"]


def test_a_decision_with_a_worse_top_score_is_refused():
    m = _load()
    d = m["decisions"][0]
    worst = min(d["candidates"], key=lambda n: score(m["weights"], d["candidates"][n]["scores"]))
    assert worst != d["decision"]
