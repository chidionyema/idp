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


# --- teacher labelling: the pure pieces, no network -------------------------------------
import generate_teacher_dataset as teacher  # noqa: E402

TASK = yaml.safe_load(
    open(Path(__file__).resolve().parents[1] / "task.yaml", encoding="utf-8")
)


class _Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Msg:
    def __init__(self, text, stop_reason="end_turn"):
        self.content, self.stop_reason = [_Block(text)], stop_reason


def test_read_inputs_dedups_and_limits(tmp_path):
    p = tmp_path / "raw.jsonl"
    p.write_text(
        '{"input":"a"}\n\n{"text":"b"}\n{"input":"a"}\n{"input":""}\n{"input":"c"}\n'
    )
    assert teacher.read_inputs(str(p)) == ["a", "b", "c"]
    assert teacher.read_inputs(str(p), limit=2) == ["a", "b"]


def test_params_carry_schema_with_every_label_and_unsure():
    params = teacher.build_params(TASK, "hello", "claude-opus-5", "medium")
    enum = params["output_config"]["format"]["schema"]["properties"]["label"]["enum"]
    assert set(enum) == {*TASK["labels"].values(), teacher.UNSURE}
    assert params["max_tokens"] == teacher.MAX_TOKENS
    assert "hello" in params["messages"][0]["content"]


def test_parse_maps_label_name_to_train_key():
    row, reject = teacher.parse_message(
        TASK, "x", _Msg('{"label": "class_1", "reason": "because"}'), "m"
    )
    assert reject is None
    assert row == {"input": "x", "output": "1", "reason": "because", "teacher": "m"}


def test_parse_rejects_unsure_refusal_and_garbage():
    for msg, why in [
        (_Msg('{"label": "unsure", "reason": "both"}'), "unsure"),
        (_Msg("", stop_reason="refusal"), "refusal"),
        (_Msg("not json"), "unparseable"),
    ]:
        row, reject = teacher.parse_message(TASK, "x", msg, "m")
        assert row is None and reject["why"] == why


def test_limit_run_emits_split_below_floor():
    rows = split([{"input": "t", "output": "0"}] * 5, minimum=0)
    assert all(r["split"] in ("train", "eval") for r in rows)
    with pytest.raises(ValueError):
        split([{"input": "t", "output": "0"}] * 5)


def test_grade_reports_abstain_rate_for_the_max_abstain_gate():
    rows = [("0", "0", 0.9)] * 2 + [("0", "1", 0.1)] * 8
    g = grade(rows, abstain_below=0.8)
    assert g["agreement"] == 1.0 and g["abstain_rate"] == pytest.approx(0.8)


def test_router_root_strips_the_v1_the_sdk_adds_back():
    assert teacher.router_root("https://r.example/v1") == "https://r.example"
    assert teacher.router_root("https://r.example/v1/") == "https://r.example"
    assert teacher.router_root("https://r.example") == "https://r.example"
    assert teacher.router_root(None) is None


def test_dataset_items_round_trip_the_export_shape_and_upsert_ids():
    rows = [
        {"input": "a", "output": "1", "reason": "r", "teacher": "m", "split": "train"}
    ]
    rejected = [{"input": "b", "why": "unsure", "reason": "both"}]
    items = teacher.dataset_items("t", rows, rejected)
    assert [i["dataset_name"] for i in items] == ["t", "t-unsure"]
    assert (
        items[0]["input"]["text"] == "a" and items[0]["expected_output"]["label"] == "1"
    )
    assert items[1]["metadata"]["why"] == "unsure"
    assert items[0]["id"] == teacher.item_id("t", "a") != teacher.item_id("u", "a")
    assert teacher.dataset_items("t", rows, rejected) == items
