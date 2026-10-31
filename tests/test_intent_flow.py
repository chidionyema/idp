import copy
import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader(
    "intent_flow", str(ROOT / "bin" / "intent-flow")
)
_s = importlib.util.spec_from_loader("intent_flow", _l)
f = importlib.util.module_from_spec(_s)
_l.exec_module(f)
M = f.load()


def test_the_shipped_machine_is_sound():
    assert f.problems(M) == []


def test_vision_reaches_done_only_through_operating():
    hops = f.path(M, "vision", "done")
    assert [h["to"] for h in hops][-3:] == ["operating", "closed", "done"]


def test_merge_alone_is_not_done():
    m = copy.deepcopy(M)
    m["edges"].append(
        {"from": "landed", "to": "done", "gate": "merged", "decider": "machine"}
    )
    assert any("done must be reachable only" in p or "skip" in p for p in f.problems(m))


def test_unreachable_and_dead_end_states_are_caught():
    m = copy.deepcopy(M)
    m["states"]["orphan"] = {"level": "x", "class": "angel"}
    p = f.problems(m)
    assert any("unreachable" in x for x in p) and any("dead end" in x for x in p)


def test_a_legion_edge_cannot_be_decided_by_judgment_or_model():
    m = copy.deepcopy(M)
    for x in m["edges"]:
        if x["from"] == "running" and x["to"] == "lane":
            x["decider"] = "model"
    assert any("legion edge" in p for p in f.problems(m))


def test_running_must_have_a_failure_path():
    m = copy.deepcopy(M)
    m["edges"] = [
        x
        for x in m["edges"]
        if not (x["from"] == "running" and x["to"] in ("ordered", "escalated"))
    ]
    assert any("running has no failure path" in p for p in f.problems(m))


def test_timeout_never_approves():
    gates = [x["gate"] for x in M["edges"] if x["from"] == "held"]
    assert any("timeout leaves status quo" in g for g in gates)


def test_shortest_path_does_not_skip_the_order():
    states = [h["to"] for h in f.path(M, "vision", "done")]
    for needed in ("decided", "ordered", "sealed", "running", "lane", "landed"):
        assert needed in states, needed


def test_every_failure_edge_has_cause_classes_with_corrections():
    assert "running->ordered" in M["feedback"]["edge_causes"]
    m = copy.deepcopy(M)
    m["feedback"]["causes"].pop("check-failed")
    assert any("no correction" in p for p in f.problems(m))


def test_a_new_failure_edge_without_feedback_is_caught():
    m = copy.deepcopy(M)
    m["edges"].append(
        {"from": "sealed", "to": "ordered", "gate": "x", "decider": "machine"}
    )
    assert any("no cause classes" in p for p in f.problems(m))


def test_spent_budget_escalates_and_repeats_fix_the_process():
    assert M["feedback"]["reissue_budget"] >= 1
    assert any(x["from"] == "running" and x["to"] == "escalated" for x in M["edges"])
    assert M["feedback"]["causes"]["repeated-cause"]["level"] == "correct the process"


def test_chain_is_a_tree_rooted_at_the_founder_and_legion_is_a_leaf():
    assert f.problems(M) == []
    roles = M["chain"]["roles"]
    assert roles["legion-runner"]["parent"] == "issuer-angel"
    assert not any(v["parent"] == "legion-runner" for v in roles.values())


def test_legion_cannot_escalate_past_its_issuer():
    m = copy.deepcopy(M)
    m["chain"]["routing"]["legion-runner"]["reports_to"] = "final-angel"
    assert any("not its parent" in p for p in f.problems(m))


def test_a_cycle_or_second_root_is_caught():
    m = copy.deepcopy(M)
    m["chain"]["roles"]["final-angel"]["parent"] = "legion-runner"
    assert any("without a cycle" in p for p in f.problems(m))
    m2 = copy.deepcopy(M)
    m2["chain"]["roles"]["coordinator-angel"]["parent"] = None
    assert any("exactly one root" in p for p in f.problems(m2))


def test_a_legion_that_commands_is_caught():
    m = copy.deepcopy(M)
    m["chain"]["roles"]["extra"] = {"class": "legion", "parent": "legion-runner"}
    assert any("must be a leaf" in p for p in f.problems(m))
