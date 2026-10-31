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


def test_rank_table_is_sound_and_shadow_cannot_push():
    assert f.problems(M) == []
    r = M["ranks"]["ranks"]
    assert r["shadow"]["push_lane"] is False and r["shadow"]["paths"] == []
    assert r["duke"]["always_held"] is True


def test_no_rank_may_be_granted_a_forbidden_path():
    m = copy.deepcopy(M)
    m["ranks"]["ranks"]["marquis"]["paths"].append(".github/**")
    assert any("forbidden path" in p for p in f.problems(m))


def test_higher_rank_includes_lower_reach_and_top_rank_is_held():
    m = copy.deepcopy(M)
    m["ranks"]["ranks"]["marquis"]["paths"] = ["bin/**"]
    assert any("must include the paths" in p for p in f.problems(m))
    m2 = copy.deepcopy(M)
    m2["ranks"]["ranks"]["duke"]["always_held"] = False
    assert any("always_held" in p for p in f.problems(m2))


def test_promotion_cannot_be_self_graded_and_breach_demotes_to_shadow():
    m = copy.deepcopy(M)
    m["ranks"]["promotion"]["evidence"] = "the runner reports it"
    assert any("self-grading" in p for p in f.problems(m))
    m2 = copy.deepcopy(M)
    m2["ranks"]["demotion"]["rule"] = "a warning"
    assert any("demote to shadow" in p for p in f.problems(m2))


def test_quad_layer_is_complete_and_every_enforcer_exists():
    assert f.problems(M) == []
    assert sorted(M["dna"]["layers"]) == [
        "assassin",
        "mathematician",
        "soldier",
        "surgeon",
    ]


def test_a_layer_with_no_enforcer_or_a_missing_one_is_refused():
    m = copy.deepcopy(M)
    m["dna"]["layers"]["assassin"]["enforced_by"] = []
    assert any("a wish" in p for p in f.problems(m))
    m2 = copy.deepcopy(M)
    m2["dna"]["layers"]["surgeon"]["enforced_by"] = ["bin/does-not-exist"]
    assert any("does not exist" in p for p in f.problems(m2))


def test_dropping_a_layer_is_refused():
    m = copy.deepcopy(M)
    del m["dna"]["layers"]["mathematician"]
    assert any("exactly soldier" in p for p in f.problems(m))


def test_session_pick_follows_priority_and_defaults_to_surgeon_with_a_claim():
    assert (
        f.pick(M, {"has_sealed_order": True, "claim_open": True})["layer"] == "soldier"
    )
    assert (
        f.pick(
            M, {"retire_target": True, "target_in_register": True, "claim_open": True}
        )["layer"]
        == "assassin"
    )
    assert (
        f.pick(M, {"unproved_claim": True, "claim_open": True})["layer"]
        == "mathematician"
    )
    assert f.pick(M, {"claim_open": True})["layer"] == "surgeon"


def test_no_signal_no_layer_a_session_cannot_start_unclaimed():
    r = f.pick(M, {})
    assert r["layer"] is None and r["how"] == "refused"


def test_choosing_a_layer_needs_its_precondition_and_is_recorded():
    bad = f.pick(M, {"claim_open": True}, choose="assassin")
    assert bad["how"] == "refused" and "precondition" in bad["why"]
    ok = f.pick(
        M,
        {"claim_open": True, "unproved_claim": True, "chosen_by": "founder"},
        choose="mathematician",
    )
    assert (
        ok["layer"] == "mathematician"
        and ok["how"] == "chosen"
        and ok["chosen_by"] == "founder"
    )
    assert f.pick(M, {}, choose="wizard")["how"] == "refused"


def test_recording_is_append_only_and_needs_an_agent_name(tmp_path):
    p = tmp_path / "s.jsonl"
    r = f.pick(M, {"claim_open": True})
    f.record(str(p), "a1", r, {"claim_open": True}, now="2026-10-31T00:00:00Z")
    f.record(str(p), "a2", f.pick(M, {}), {}, now="2026-10-31T00:01:00Z")
    lines = p.read_text().splitlines()
    assert (
        len(lines) == 2 and '"agent": "a1"' in lines[0] and '"layer": null' in lines[1]
    )


def test_drift_is_blind_without_enough_sessions():
    rows = [{"layer": "surgeon"}] * 10
    assert f.drift(rows)["verdict"] == "BLIND"


def test_drift_flags_a_change_in_behaviour_and_calls_stable_stable():
    steady = [{"layer": "surgeon"}, {"layer": "soldier"}] * 20
    assert f.drift(steady)["verdict"] == "STABLE"
    shifted = [{"layer": "surgeon"}] * 30 + [{"layer": None}] * 30
    r = f.drift(shifted)
    assert r["verdict"] == "CHANGED" and r["moved"][0][0] in ("surgeon", "refused")


def _sess(tmp_path, n, layer="surgeon", how="picked", by_rule=None):
    p = tmp_path / "o.jsonl"
    ids = []
    for i in range(n):
        line = f.record(
            str(p),
            "agent-%d" % i,
            {"layer": layer, "how": how, "by_rule": by_rule},
            {},
            now="2026-10-31T00:00:%02dZ" % i,
        )
        ids.append(line["id"])
    return p, ids


def test_an_agent_cannot_grade_itself_and_unknown_session_is_refused(tmp_path):
    import pytest

    p, ids = _sess(tmp_path, 1)
    with pytest.raises(ValueError):
        f.outcome(str(p), ids[0], "operating", "agent-0")
    with pytest.raises(ValueError):
        f.outcome(str(p), "nope", "operating", "grader")
    with pytest.raises(ValueError):
        f.outcome(str(p), ids[0], "great", "grader")


def test_report_is_blind_below_min_graded_and_counts_ungraded(tmp_path):
    p, ids = _sess(tmp_path, 3)
    f.outcome(str(p), ids[0], "operating", "grader")
    rows = [__import__("json").loads(x) for x in p.read_text().splitlines()]
    r = f.report(rows)
    assert r["ungraded"] == 2 and r["cells"]["surgeon/picked"]["verdict"] == "BLIND"


def test_report_separates_chosen_overrides_and_scores_enough_graded(tmp_path):
    p, ids = _sess(tmp_path, 12, layer="mathematician", how="chosen", by_rule="surgeon")
    for i, sid in enumerate(ids):
        f.outcome(str(p), sid, "operating" if i < 9 else "breach", "grader")
    rows = [__import__("json").loads(x) for x in p.read_text().splitlines()]
    c = f.report(rows)["cells"]["mathematician/chosen"]
    assert (
        c["overrides"] == 12
        and c["graded"] == 12
        and c["bad"] == 3
        and c["verdict"] == "0.75 good"
    )


def test_delivery_includes_qa_integration_and_operating_as_states():
    states = [h["to"] for h in f.path(M, "vision", "done")]
    i = {
        s: states.index(s)
        for s in (
            "lane",
            "verified",
            "landed",
            "integrated",
            "operating",
            "closed",
            "done",
        )
    }
    assert list(i.values()) == sorted(i.values())


def test_landing_without_verification_is_refused():
    m = copy.deepcopy(M)
    m["edges"].append(
        {
            "from": "lane",
            "to": "landed",
            "gate": "green",
            "decider": "machine",
            "evidence": "x",
        }
    )
    assert any(
        "landed must be reachable only from verified" in p for p in f.problems(m)
    )


def test_operating_without_integration_is_refused():
    m = copy.deepcopy(M)
    m["edges"].append(
        {"from": "landed", "to": "operating", "gate": "x", "decider": "machine"}
    )
    p = f.problems(m)
    assert any("skip integration" in x for x in p) and any(
        "operating must be reachable only from integrated" in x for x in p
    )


def test_verifier_must_be_independent_of_issuer_and_runner():
    m = copy.deepcopy(M)
    m["states"]["verified"]["independent_of"] = ["runner"]
    assert any("independent of the issuer and the runner" in p for p in f.problems(m))


def test_every_delivery_edge_names_the_evidence_it_emits():
    m = copy.deepcopy(M)
    for x in m["edges"]:
        if (x["from"], x["to"]) == ("landed", "integrated"):
            x.pop("evidence")
    assert any("no gap in intel" in p for p in f.problems(m))


def test_qa_and_integration_failures_have_cause_classes_and_corrections():
    ec = M["feedback"]["edge_causes"]
    assert set(ec["verified->ordered"]) == {
        "claim-unverified",
        "eval-regressed",
        "judge-rejected",
    }
    assert ec["integrated->ordered"] == ["integration-failed"]
    assert all(c in M["feedback"]["causes"] for cs in ec.values() for c in cs)


def test_abyss_finds_the_known_voids_and_ranks_nearest_first():
    r = f.abyss(M)
    assert r["verdict"] == "ABYSS" and r["count"] > 0
    depths = [v["depth"] for v in r["voids"]]
    assert depths == sorted(depths)
    assert any(v["edge"] == "ordered->staged" for v in r["voids"])


def test_removing_a_mechanism_creates_a_void_and_a_missing_file_does_too():
    m = copy.deepcopy(M)
    for x in m["edges"]:
        if (x["from"], x["to"]) == ("queued", "ordered"):
            x["mechanism"] = []
    assert any(
        v["edge"] == "queued->ordered" and v["kind"] == "no-mechanism"
        for v in f.abyss(m)["voids"]
    )
    m2 = copy.deepcopy(M)
    for x in m2["edges"]:
        if (x["from"], x["to"]) == ("queued", "ordered"):
            x["mechanism"] = ["bin/not-a-file"]
    assert any("does not exist" in v["why"] for v in f.abyss(m2)["voids"])


def test_a_judgment_with_no_register_entry_is_a_black_box():
    m = copy.deepcopy(M)
    for x in m["edges"]:
        if (x["from"], x["to"]) == ("held", "lane"):
            x["register_id"] = "dec:invented"
    assert any(v["kind"] == "black-box" for v in f.abyss(m)["voids"])


def test_a_cycle_with_no_exit_is_an_open_loop_and_a_clean_model_has_no_abyss():
    m = {
        "start": "a",
        "done": "z",
        "states": {"a": {}, "b": {}, "z": {}},
        "edges": [
            {
                "from": "a",
                "to": "b",
                "decider": "machine",
                "gate": "g",
                "mechanism": ["bin/intent-flow"],
                "event": "e1",
            },
            {
                "from": "b",
                "to": "a",
                "decider": "machine",
                "gate": "g",
                "mechanism": ["bin/intent-flow"],
                "event": "e2",
            },
        ],
    }
    assert any(v["kind"] == "open-loop" for v in f.abyss(m)["voids"])
    m["edges"].append(
        {
            "from": "b",
            "to": "z",
            "decider": "machine",
            "gate": "g",
            "mechanism": ["bin/intent-flow"],
            "event": "e3",
        }
    )
    assert f.abyss(m)["verdict"] == "NO_ABYSS"
