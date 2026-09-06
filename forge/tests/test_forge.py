# ruff: noqa: S101
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import grade, label_probs, split  # noqa: E402


def rows(n):
    return [{"input": f"text {i}", "output": str(i % 2)} for i in range(n)]


def test_split_refuses_under_500():
    with pytest.raises(ValueError):
        split(rows(499))


def test_split_is_deterministic_and_80_20():
    a, b = split(rows(500)), split(rows(500))
    assert a == b
    assert sum(r["split"] == "train" for r in a) == 400


def test_label_probs_margin_and_abstain():
    top, p, margin = label_probs({"0": 2.0, "1": 2.0})
    assert margin == pytest.approx(0.0) and p == pytest.approx(0.5)
    top, p, margin = label_probs({"0": 0.0, "1": 5.0})
    assert top == "1" and margin > 0.98


def test_grade_counts_answered_only():
    r = grade([("1", "1", 0.9), ("0", "1", 0.9), ("0", "0", 0.1)], abstain_below=0.8)
    assert r == {"held_out": 3, "agreement": 0.5, "abstain_rate": pytest.approx(1 / 3)}


def test_task_yaml_matches_card_contract():
    task = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "task.yaml").read_text()
    )
    for key in (
        "task",
        "base",
        "kind",
        "prompt_template",
        "labels",
        "abstain_below",
        "min_agreement",
        "kv_cache_prefix",
    ):
        assert key in task
    assert "{input}" in task["prompt_template"]
    assert 0 < task["abstain_below"] < 1
