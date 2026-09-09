# ruff: noqa: S101
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import compute_plan, cost_gate, grade, label_probs, split, usd_for  # noqa: E402


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
        "compute",
    ):
        assert key in task
    assert "{input}" in task["prompt_template"]
    assert 0 < task["abstain_below"] < 1
    assert cost_gate(task) is None, "the shipped task file must fit its own budget"


def test_cost_gate_refuses_only_on_money():
    # a bigger model on a bigger GPU is fine when the budget covers the worst case
    assert (
        cost_gate({"compute": {"gpu": "H100", "timeout_s": 1800, "budget_usd": 2.0}})
        is None
    )
    # the same run over budget is refused, and the reason names the numbers
    reason = cost_gate(
        {"compute": {"gpu": "H100", "timeout_s": 3600, "budget_usd": 2.0}}
    )
    assert reason and "3.95" in reason and "2.00" in reason
    # an unpriced GPU cannot be budgeted: fail closed
    assert "no price" in cost_gate({"compute": {"gpu": "TPU", "budget_usd": 100}})
    # no compute block means the defaults, which fit
    assert compute_plan({})["gpu"] == "T4" and cost_gate({}) is None
    assert usd_for("T4", 3600) == 0.59


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
        TASK, "x", _Msg('{"label": "positive", "reason": "because"}'), "m"
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


def test_experiment_record_front_matter_parses_to_the_run():
    import experiment_record as er

    task = yaml.safe_load((Path(__file__).parents[1] / "task.yaml").read_text())
    run = {
        "task": task["task"],
        "dry_run": False,
        "max_steps": -1,
        "gpu": "T4",
        "seconds": 321,
        "trace": "tr_1",
        "artifact": None,
        "verdict": "refused",
        "eval": {
            "held_out": 100,
            "agreement": 0.91,
            "abstain_rate": 0.05,
            "verdict": "refused",
            "refusal": "held-out agreement 0.9100 below 0.95",
        },
        "dataset": {
            "rows": 500,
            "train": 400,
            "eval": 100,
            "sha256": "ab" * 32,
            "langfuse_dataset": task["task"],
        },
    }
    data = [{"input": "x", "output": "1", "split": "train", "teacher": "default"}] * 3
    ctx = {
        "stamp": "20260906T1200Z",
        "sha": "deadbeef",
        "run_url": None,
        "langfuse_host": "https://lf.example",
        "task_path": "forge/task.yaml",
        "data_path": None,
    }
    md = er.render(task, run, data, ctx)
    front = yaml.safe_load(md.split("---")[1])
    assert front["verdict"] == "refused"
    assert front["agreement"] == pytest.approx(0.91)
    assert front["dataset_sha256"] == "ab" * 32
    assert front["experiment"] == f"20260906T1200Z-{task['task']}"
    assert er.data_summary(data) == {
        "per_label": {"1": 3},
        "teachers": ["default"],
        "splits": {"train": 3},
    }
    assert er.half_width(0.95, 100) == pytest.approx(0.0427, abs=1e-3)


def test_modal_app_imports_common_after_module_reads_both_dirs():
    """2026-09-06 regression guard.

    Modal stages the forge entrypoint at the image ROOT (/root/modal_app.py) while
    add_local_dir copies forge/ to /root/forge, so the original file -- importing `common`
    from the module dir alone -- died on `ModuleNotFoundError: No module named 'common'`
    and no run record was ever filed (the 90-min CI slot was consumed spinning). The file
    must append BOTH its own module dir and its REMOTE layout to sys.path before importing
    common. Graded on the AST (parsed structure, R76), not on prose.
    """
    import ast

    path = Path(Path(__file__).resolve().parents[1], "modal_app.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    remote_lineno = None
    appends = []  # lineno of each sys.path.append call in the body
    inserts = []  # lineno of each sys.path.insert call in the body (module dir registration)
    common_lineno = None

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "REMOTE" for t in node.targets
        ):
            remote_lineno = node.lineno
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "common"
            and any(a.name == "compute_plan" for a in node.names)
        ):
            common_lineno = node.lineno

    def _sys_path_mutations(body):
        for node in body:
            node = (
                node.value if isinstance(node, ast.Expr) else node
            )  # unwrap Expr(Call)
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if not isinstance(f, ast.Attribute) or f.attr not in ("append", "insert"):
                continue
            # callee is sys.path.<attr>; walk the value chain for the leading Name("sys")
            head = f.value
            while isinstance(head, ast.Attribute):
                head = head.value
            if isinstance(head, ast.Name) and head.id == "sys":
                yield node  # a real sys.path mutation

    for node in _sys_path_mutations(tree.body):
        f = node.func
        if f.attr == "append":
            appends.append(node.lineno)
        elif f.attr == "insert":
            inserts.append(node.lineno)

    assert remote_lineno is not None, "modal_app.py must bind a REMOTE dir constant"
    assert common_lineno is not None, "modal_app.py must import from common"
    assert inserts, "modal_app.py must register its own module dir on sys.path"
    assert appends, (
        "modal_app.py must append its REMOTE dir to sys.path (2026-09-06 re-break)"
    )
    assert common_lineno > max(appends + inserts), (
        "the common import must run after the module dir and REMOTE are both on sys.path"
    )


# ---- Forge spend control (founder 2026-09-09: track + refuse so no card is reached) ----
import tempfile


def _write_record(dir_, name, usd):
    d = Path(dir_)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(
        f"---\nexperiment: {name}\ntask: t\nverdict: shipped\nusd: {usd}\n---\n# body\n",
        encoding="utf-8",
    )


def test_total_spend_sums_recorded_ledger():
    import shutil

    from common import spend_from_ledger, total_spend

    d = Path(tempfile.mkdtemp())
    try:
        _write_record(d, "20260909T0000Z-a.md", 0.1632)
        _write_record(d, "20260910T0000Z-b.md", 0.84)
        _write_record(d, "0001-plan.md", None)  # no usd -> not a run
        rows = spend_from_ledger(d)
        assert {r["file"]: r["usd"] for r in rows} == {
            "20260909T0000Z-a.md": 0.1632,
            "20260910T0000Z-b.md": 0.84,
        }, rows
        assert total_spend(d) == pytest.approx(0.1632 + 0.84)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_modal_spend_gate_refuses_at_or_over_cap_and_allows_below():
    import shutil

    from common import modal_spend_gate

    d = Path(tempfile.mkdtemp())
    try:
        _write_record(d, "20260909T0000Z-a.md", 7.0)  # over the $5 cap
        refusal = modal_spend_gate(d, cap_usd=5.00)
        assert refusal is not None and "cap" in refusal.lower(), refusal
        # below cap -> allowed
        d2 = Path(tempfile.mkdtemp())
        try:
            _write_record(d2, "20260909T0000Z-a.md", 0.16)
            assert modal_spend_gate(d2, cap_usd=5.00) is None
        finally:
            shutil.rmtree(d2, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
