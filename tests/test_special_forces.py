"""[#7692] special forces, bound to the estate's ONE plan contract.

The founder's drop (special-forces-v0) is a bounded state machine with two protocols of its
own. The estate already has one contract for what an agent must prove before its work counts
(platform/estate/memory/plan.py). These tests prove the two are ONE: the machine is unchanged,
and the binding layer (platform/estate/special_forces/unit.py) is what refuses a unit that
would be a second, looser idea of the contract.

What is proved here:
  * the machine itself still behaves as the drop shipped it (happy path, parking, budget,
    write boundaries, the proof gate),
  * every contract stage is covered by exactly one protocol stage,
  * a unit cannot start without a declared plan, and a stage cannot be submitted until the
    ledger has recorded the contract stage it carries,
  * the evidence for a ledger stage is a receipt of the ledger, not a second copy of the
    contract,
  * the door refuses a write outside the unit's boundary, and says so with the machine's own
    exit code (3),
  * the alerter from the drop is NOT installed: the estate already alerts, and the founder's
    Telegram token's polling is off limits.
"""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SF_DIR = os.path.join(ROOT, "platform", "estate", "special_forces")
MACHINE = os.path.join(SF_DIR, "sf_machine.py")
PROTOCOLS = os.path.join(SF_DIR, "protocols")
SESSION = "harness:test:4242"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def unit(tmp_path, monkeypatch):
    """The binding layer, with the ledger and the units held in a temporary directory."""
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    monkeypatch.setenv("ESTATE_UNIT_DIR", str(tmp_path / "units"))
    return _load(os.path.join(SF_DIR, "unit.py"), "estate_sf_unit_under_test")


def _plan(unit_mod):
    return unit_mod._plan_module()


def _declare(session, unit_mod, goal_id="g1"):
    """A session that has declared a plan, in the durable ledger."""
    plan = _plan(unit_mod)
    assert plan.append_plan_event(
        session,
        "declare_plan",
        {
            "goal": "the bounded unit proves the work",
            "subgoals": [{"id": goal_id, "text": "the unit is bound to the ledger"}],
        },
    )
    return plan


# --------------------------------------------------------------------------- the machine, unchanged


def _machine(*args, cwd):
    r = subprocess.run(
        [sys.executable, MACHINE, *args], capture_output=True, text=True, cwd=cwd
    )
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else {})


@pytest.fixture()
def machine_run(tmp_path):
    """A machine running the founder's recon protocol, exactly as the drop ships it."""
    d = tmp_path
    state = str(d / "s.json")
    log = str(d / "events.jsonl")
    os.makedirs(d / "work" / "CLM-1")
    os.makedirs(d / "specs")

    def start(proto="recon.json", **kw):
        args = [
            "start",
            "--protocol",
            os.path.join(PROTOCOLS, proto),
            "--claim",
            "CLM-1",
            "--unit",
            "u1",
            "--state",
            state,
            "--log",
            log,
        ]
        for k, v in kw.items():
            args += ["--" + k.replace("_", "-"), v]
        return _machine(*args, cwd=str(d))

    def write(rel, text):
        p = str(d / rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return rel

    def submit(rel):
        return _machine(
            "submit", "--state", state, "--artifact", str(d / rel), cwd=str(d)
        )

    def events():
        with open(log, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    return {
        "dir": d,
        "state": state,
        "log": log,
        "start": start,
        "write": write,
        "submit": submit,
        "events": events,
        "sf": lambda *a: _machine(*a, cwd=str(d)),
    }


def test_the_machines_recon_happy_path_still_runs(machine_run):
    assert machine_run["start"]()[0] == 0
    machine_run["write"](
        "work/CLM-1/edge_cases.json", '[{"id":"timeout"},{"id":"empty"}]'
    )
    assert machine_run["submit"]("work/CLM-1/edge_cases.json")[0] == 0
    machine_run["write"]("work/CLM-1/second_order.json", '[{"effect":"retry storm"}]')
    assert machine_run["submit"]("work/CLM-1/second_order.json")[0] == 0
    machine_run["write"](
        "specs/CLM-1.feature",
        "Feature: x\n  @CLM-1 @edge-timeout\n  Scenario: a\n    Given b\n"
        "  @CLM-1 @edge-empty\n  Scenario: c\n    Given d\n",
    )
    code, out = machine_run["submit"]("specs/CLM-1.feature")
    assert (code, out["status"]) == (0, "done")
    assert machine_run["events"][-1]["event"] == "done"


def test_the_machine_parks_after_two_retries_on_an_uncovered_edge_case(machine_run):
    machine_run["start"]()
    machine_run["write"](
        "work/CLM-1/edge_cases.json", '[{"id":"timeout"},{"id":"empty"}]'
    )
    machine_run["submit"]("work/CLM-1/edge_cases.json")
    machine_run["write"]("work/CLM-1/second_order.json", "[1]")
    machine_run["submit"]("work/CLM-1/second_order.json")
    machine_run["write"](
        "specs/CLM-1.feature",
        "Feature: x\n  @CLM-1 @edge-timeout\n  Scenario: a\n    Given b\n",
    )
    codes = [machine_run["submit"]("specs/CLM-1.feature")[0] for _ in range(3)]
    assert codes == [1, 1, 2]
    assert machine_run["events"][-1]["event"] == "park"
    assert (
        machine_run["sf"]("status", "--state", machine_run["state"])[1]["status"]
        == "parked"
    )


def test_the_machine_parks_on_a_budget_overrun(machine_run):
    machine_run["start"]()
    assert (
        machine_run["sf"](
            "spend", "--state", machine_run["state"], "--tokens", "15000"
        )[0]
        == 0
    )
    assert (
        machine_run["sf"]("spend", "--state", machine_run["state"], "--tokens", "6000")[
            0
        ]
        == 2
    )
    assert machine_run["events"][-1]["event"] == "park"


def test_the_machine_holds_its_write_boundary(machine_run):
    machine_run["start"]()
    ok = lambda p: machine_run["sf"](  # noqa: E731 - a local shorthand, as in the drop's tests
        "check-write", "--state", machine_run["state"], "--path", p
    )[0]
    assert ok("work/CLM-1/edge_cases.json") == 0
    assert ok("src/app.py") == 3
    assert ok("../etc/passwd") == 3
    assert ok("/etc/passwd") == 3
    assert ok("specs/CLM-1.feature") == 3  # not yet: the wrong stage


def test_the_machine_requires_a_prove_command_for_the_ops_protocol(machine_run):
    assert machine_run["start"]("ops.json")[0] == 2


def test_the_machine_will_not_close_without_the_proof_passing(machine_run):
    flag = str(machine_run["dir"] / "flag")
    machine_run["start"]("ops.json", prove_cmd=f"test -f {flag}")
    for rel in ("work/CLM-1/plan.json", "work/CLM-1/wiring.json"):
        machine_run["write"](rel, '{"a":1}')
        assert machine_run["submit"](rel)[0] == 0
    machine_run["write"]("work/CLM-1/proof.json", '{"claimed":"works"}')
    assert machine_run["submit"]("work/CLM-1/proof.json")[0] == 1
    with open(flag, "w", encoding="utf-8") as fh:
        fh.write("x")
    code, out = machine_run["submit"]("work/CLM-1/proof.json")
    assert (code, out["status"]) == (0, "done")


# --------------------------------------------------------------------------- the binding to the contract


def test_every_contract_stage_is_covered_exactly_once(unit):
    proto = unit.load_protocol("estate_plan")
    stages = unit.protocol_stages(proto)
    covered = [s["contract_stage"] for s in stages]
    assert sorted(covered) == sorted(unit.CONTRACT_STAGES)
    assert len(covered) == len(set(covered)), "a contract stage is covered twice"


def test_the_founder_protocols_map_onto_the_contract(unit):
    recon = unit.contract_map(unit.load_protocol("recon"))
    assert recon["map_edges"] == "address_edgecases"
    assert recon["second_order"] == "address_2nd_order_effects"
    assert recon["write_bdd"] == "add_bdd"
    ops = unit.contract_map(unit.load_protocol("ops"))
    assert ops["plan"] == "declare_plan"
    assert ops["wire"] == "implement"
    assert ops["prove"] == "complete_goal"


def test_a_protocol_that_invents_a_contract_stage_is_refused(unit):
    proto = {
        "name": "rogue",
        "stages": [{"name": "do_it", "contract_stage": "make_it_up", "writes": []}],
    }
    errs = unit.protocol_errors(proto)
    assert errs and "make_it_up" in errs[0]
    assert unit.protocol_errors({"name": "x", "stages": [{"name": "s"}]})


def test_a_unit_cannot_start_without_a_declared_plan(unit):
    result = unit.start(SESSION, "CLM-1", "u1", "estate_plan")
    assert result["ok"] is False
    assert result["exit"] == unit.EXIT_REFUSED
    assert "estate-plan declare_plan" in result["error"]


def test_a_unit_starts_for_a_session_that_has_declared_a_plan(unit):
    _declare(SESSION, unit)
    result = unit.start(SESSION, "CLM-1", "u1", "estate_plan")
    assert result["ok"] is True
    assert result["exit"] == unit.EXIT_OK
    assert result["stage"] == "declare_plan"
    assert result["goal_id"] == "g1"


def test_a_stage_is_refused_until_the_ledger_records_its_contract_stage(unit):
    _declare(SESSION, unit)
    assert unit.start(SESSION, "CLM-1", "u1", "estate_plan")["ok"] is True
    # The ledger has the plan, but not the BDD scenario this stage carries.
    result = unit.submit(SESSION, "unused.json")
    assert result["ok"] is False
    assert result["exit"] == unit.EXIT_RETRY
    assert "estate-plan add_bdd" in result["error"]


def test_the_evidence_for_a_ledger_stage_is_a_receipt_not_a_second_contract(unit):
    _declare(SESSION, unit)
    assert unit.start(SESSION, "CLM-1", "u1", "estate_plan")["ok"] is True
    plan = _plan(unit)
    plan.append_plan_event(
        SESSION,
        "add_bdd",
        {
            "goal_id": "g1",
            "given": "the unit has started",
            "when": "the stage is submitted",
            "then": "the ledger is the evidence",
        },
    )
    result = unit.submit(SESSION, "unused.json")
    assert result["ok"] is True, result
    evidence = os.path.join(unit.session_dir(SESSION), "u1.evidence.json")
    with open(evidence, encoding="utf-8") as fh:
        receipt = json.load(fh)
    assert receipt["contract_stage"] == "add_bdd"
    # A receipt, not a copy of the contract: no goal, no sub-goals, no scenario.
    assert "goal" not in receipt and "subgoals" not in receipt and "bdd" not in receipt


def test_complete_goal_is_refused_until_every_sub_goal_is_done(unit):
    plan = _plan(unit)
    plan.append_plan_event(
        SESSION,
        "declare_plan",
        {
            "goal": "the bounded unit proves the work",
            "subgoals": [
                {"id": "g1", "text": "the unit is bound to the ledger"},
                {"id": "g2", "text": "the door refuses a write outside it"},
            ],
        },
    )
    assert unit.start(SESSION, "CLM-1", "u1", "estate_plan")["ok"] is True
    plan.append_plan_event(
        SESSION,
        "add_bdd",
        {
            "goal_id": "g1",
            "given": "the unit has started",
            "when": "the stage is submitted",
            "then": "the ledger is the evidence",
        },
    )
    plan.append_plan_event(
        SESSION,
        "address_edgecases",
        {"goal_id": "g1", "edgecases": ["a ledger that is unreadable"]},
    )
    plan.append_plan_event(
        SESSION,
        "address_2nd_order_effects",
        {"goal_id": "g1", "effects": ["another runtime sees a half-written ledger"]},
    )
    plan.append_plan_event(SESSION, "complete_goal", {"goal_id": "g1"})
    state = unit.active_state(SESSION)
    state["idx"] = len(unit.protocol_stages(unit.load_protocol("estate_plan"))) - 1
    unit.save_state(unit.state_path(SESSION, "u1"), state)
    result = unit.submit(SESSION, "unused.json")
    assert result["ok"] is False
    assert "g2" in result["error"] or "complete_goal" in result["error"]


# --------------------------------------------------------------------------- the write boundary


def test_write_targets_are_only_the_explicit_ones(unit):
    targets = unit.write_targets(
        "cat a.txt > out.txt && tee -a log.txt | cp src dst && touch new && mkdir d"
    )
    assert "out.txt" in targets
    assert "log.txt" in targets
    assert "dst" in targets
    assert "new" in targets
    assert "d" in targets
    assert "src" not in targets  # a source is not a write
    assert unit.write_targets("pytest tests/test_x.py") == []


def test_the_door_refuses_a_write_outside_the_unit_boundary(unit):
    _declare(SESSION, unit)
    assert unit.start(SESSION, "CLM-1", "u1", "estate_plan")["ok"] is True
    verdict = unit.gate(SESSION, "echo x > platform/estate/special_forces/other.py")
    assert verdict["ok"] is False
    assert verdict["reason"] == "write_denied"
    assert verdict["exit_code"] == unit.EXIT_WRITE_DENIED
    inside = unit.gate(SESSION, "echo x > work/CLM-1/note.md")
    assert inside["ok"] is True


def test_the_door_allows_a_session_with_no_unit(unit):
    assert unit.gate(SESSION, "echo x > /tmp/anything")["ok"] is True


# --------------------------------------------------------------------------- the door in the executor


def test_the_executor_refuses_an_out_of_boundary_write(unit, monkeypatch):
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", os.environ["ESTATE_PLAN_LEDGER_DIR"])
    _declare(SESSION, unit)
    assert unit.start(SESSION, "CLM-1", "u1", "estate_plan")["ok"] is True
    executor = _load(
        os.path.join(ROOT, "mcp", "plugins", "estate_executor.py"),
        "estate_executor_under_test",
    )
    verdict = executor._unit_gate(
        "echo x > platform/estate/special_forces/other.py", SESSION
    )
    assert verdict is not None
    assert verdict["ok"] is False
    assert verdict["exit_code"] == 3
    assert executor._unit_gate("echo x > work/CLM-1/note.md", SESSION)["ok"] is True


# --------------------------------------------------------------------------- what is deliberately absent


def test_the_drop_telegram_alerter_is_not_installed():
    """The estate already alerts, and the founder's Telegram token's polling is off limits."""
    for path in (
        os.path.join(SF_DIR, "telegram_alert.py"),
        os.path.join(SF_DIR, "..", "telegram-alert"),
    ):
        assert not os.path.exists(path), path
