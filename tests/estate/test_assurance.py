"""The decision-assurance substrate: policy, hypothesis space, simulation and the receipt.

Every test here is a way the doctrine could be wrong, and is made to fail if it is:

  * an agent that declares it does not need simulation must be REFUSED, because the policy
    selects the method and not the agent;
  * a lint failure must not be charged a Monte Carlo tax;
  * the same seed must produce the same number in two processes, and a tampered number must
    not survive verification;
  * a measurement that could not be taken must be BLIND, never PASS;
  * a paraphrase must merge and a conjunction must not;
  * the unexplained residual must never be pruned, and evidence that refutes everything must
    produce an EXPANSION rather than a confident wrong winner.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIBEXEC = REPO / "platform" / "estate" / "libexec"
CATALOG = REPO / "catalog" / "decision-assurance.json"


def _load(name: str):
    loader = SourceFileLoader(name, str(LIBEXEC / ("%s.py" % name)))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


assurance = _load("assurance")


@pytest.fixture(scope="module")
def catalog():
    data = json.loads(CATALOG.read_text())
    return data


# --------------------------------------------------------------------------------------
# layer 1: the policy selects the method
# --------------------------------------------------------------------------------------


def test_policy_refuses_an_agents_self_exemption(catalog):
    """The agent asked for no simulation; the policy says the decision needs it."""
    case = {"class": "router.failover", "monte_carlo_required": False}
    selection = assurance.method_selection(case, catalog)
    assert selection["method"] == "monte_carlo"
    assert selection["refused_self_exemption"] is True
    assert "REFUSED" in selection["reason"]


def test_policy_ignores_a_self_exemption_even_when_the_agent_is_polite(catalog):
    case = {
        "class": "router.failover",
        "monte_carlo_required": False,
        "impact": "critical",
    }
    selection = assurance.method_selection(case, catalog)
    assert selection["method"] != "deterministic"


def test_a_lint_failure_is_not_charged_a_monte_carlo_tax(catalog):
    selection = assurance.method_selection({"class": "lint.schema"}, catalog)
    assert selection["method"] == "deterministic"
    assert selection["tier"] == "tier0"


def test_a_formal_invariant_outranks_simulation(catalog):
    selection = assurance.method_selection(
        {"class": "router.failover", "formal_invariant": True}, catalog
    )
    assert selection["method"] == "formal"


def test_an_agent_may_ask_for_more_assurance(catalog):
    selection = assurance.method_selection(
        {
            "class": "lint.schema",
            "requested_method": "monte_carlo",
            "requested_tier": "tier1",
        },
        catalog,
    )
    assert selection["escalation"] is not None
    assert selection["escalation"]["accepted"] is True
    assert selection["method"] == "deterministic", (
        "the policy's own choice is unchanged"
    )


def test_an_unknown_class_has_no_method(catalog):
    selection = assurance.method_selection({"class": "nonsense.class"}, catalog)
    assert selection["method"] is None


# --------------------------------------------------------------------------------------
# layer 3: the simulation
# --------------------------------------------------------------------------------------


def test_the_same_seed_produces_the_same_number(catalog):
    one = assurance.run_scenario("router.correlated-outage", catalog, 42, 500)
    two = assurance.run_scenario("router.correlated-outage", catalog, 42, 500)
    assert one["simulation_digest"] == two["simulation_digest"]
    assert one["metrics"] == two["metrics"]


def test_a_different_seed_produces_a_different_number(catalog):
    one = assurance.run_scenario("router.correlated-outage", catalog, 42, 500)
    two = assurance.run_scenario("router.correlated-outage", catalog, 43, 500)
    assert one["simulation_digest"] != two["simulation_digest"]


def test_the_model_reports_the_metrics_the_doctrine_names(catalog):
    run = assurance.run_scenario("router.correlated-outage", catalog, 42, 1000)
    metrics = run["metrics"]
    for key in (
        "expected_loss_s",
        "p_loss_gt_lmax",
        "cvar99_s",
        "p_slo_breach",
        "uncertainty_margin",
        "slo_breach_bound",
    ):
        assert key in metrics, key
    assert metrics["slo_breach_bound"] >= metrics["p_slo_breach"]


def test_the_correlated_model_is_not_the_naive_one(catalog):
    """The independent model understates the tail. That is the whole reason for this lane."""
    run = assurance.run_scenario("router.correlated-outage", catalog, 42, 2000)
    variants = {v["variant"]: v for v in run["sensitivity"]}
    assert "independent" in variants
    assert run["metrics"]["p_slo_breach"] >= variants["independent"]["p_slo_breach"]


def test_the_convergence_diagnostics_are_reported(catalog):
    run = assurance.run_scenario("router.correlated-outage", catalog, 42, 1000)
    assert len(run["convergence"]) >= 3
    assert run["convergence"][-1]["samples"] == 1000
    assert run["drift"] >= 0.0


def test_assumed_parameters_are_flagged_as_assumed(catalog):
    scenario = catalog["scenarios"]["router.correlated-outage"]
    assumed = [
        k for k, v in scenario["parameters"].items() if v.get("provenance") == "assumed"
    ]
    measured = [
        k
        for k, v in scenario["parameters"].items()
        if v.get("provenance") == "measured"
    ]
    assert assumed, "a model with no assumed parameter is a model nobody declared"
    assert measured, "a model with no measured parameter is a model nobody checked"
    run = assurance.run_scenario("router.correlated-outage", catalog, 42, 200)
    assert set(run["model"]["provenance"]["assumed"]) == set(assumed)
    assert set(run["model"]["provenance"]["measured"]) == set(measured)


# --------------------------------------------------------------------------------------
# the receipt
# --------------------------------------------------------------------------------------


def _receipt(catalog, tmp_path, samples=2000, seed=42):
    run = assurance.run_scenario("router.correlated-outage", catalog, seed, samples)
    run["scenario_name"] = "router.correlated-outage"
    return assurance.build_receipt(
        decision_id="router-failover",
        decision_class="router.failover",
        method="monte_carlo",
        tier="tier1",
        candidate_digest="sha256:none",
        run=run,
    )


def test_an_honest_receipt_verifies_by_recomputation(catalog, tmp_path):
    receipt = _receipt(catalog, tmp_path)
    result = assurance.verify_receipt(receipt, catalog)
    assert result["verdict"] in ("PASS", "REVIEW_REQUIRED")
    assert not [p for p in result["problems"] if "does not reproduce" in p]


def test_a_tampered_metric_is_blocked(catalog, tmp_path):
    receipt = _receipt(catalog, tmp_path)
    receipt["metrics"]["p_slo_breach"] = 0.0
    receipt["metrics"]["slo_breach_bound"] = 0.0
    result = assurance.verify_receipt(receipt, catalog)
    assert result["verdict"] == "BLOCK"
    assert any("altered" in p or "differs" in p for p in result["problems"])


def test_a_tampered_seed_is_blocked(catalog, tmp_path):
    receipt = _receipt(catalog, tmp_path)
    receipt["seed"] = 4242
    result = assurance.verify_receipt(receipt, catalog)
    assert result["verdict"] == "BLOCK"


def test_a_receipt_for_a_scenario_this_catalog_does_not_carry_is_blind(
    catalog, tmp_path
):
    receipt = _receipt(catalog, tmp_path)
    receipt["scenario"] = "no.such.scenario"
    receipt["digest"] = assurance.digest(
        {k: v for k, v in receipt.items() if k != "digest"}
    )
    result = assurance.verify_receipt(receipt, catalog)
    assert result["verdict"] == "BLIND"


def test_a_receipt_is_bound_to_the_candidate_artifact(catalog, tmp_path):
    candidate = tmp_path / "candidate.yaml"
    candidate.write_text("one\n")
    receipt = _receipt(catalog, tmp_path)
    receipt["candidate_digest"] = assurance.sha256_file(candidate)
    receipt["digest"] = assurance.digest(
        {k: v for k, v in receipt.items() if k != "digest"}
    )
    assert (
        assurance.verify_receipt(receipt, catalog, str(candidate))["verdict"] != "BLOCK"
    )
    candidate.write_text("two\n")
    assert (
        assurance.verify_receipt(receipt, catalog, str(candidate))["verdict"] == "BLOCK"
    )


def test_a_missing_candidate_is_blind_not_a_pass(catalog, tmp_path):
    receipt = _receipt(catalog, tmp_path)
    result = assurance.verify_receipt(receipt, catalog, str(tmp_path / "absent.yaml"))
    assert result["verdict"] == "BLIND"


def test_the_gate_blocks_when_the_method_is_not_the_policys(catalog, tmp_path):
    receipt = _receipt(catalog, tmp_path)
    receipt["method"] = "deterministic"
    receipt["digest"] = assurance.digest(
        {k: v for k, v in receipt.items() if k != "digest"}
    )
    result = assurance.gate({"class": "router.failover"}, receipt, catalog)
    assert result["verdict"] == "BLOCK"


def test_the_gate_blocks_when_there_is_no_receipt(catalog):
    result = assurance.gate({"class": "router.failover"}, None, catalog)
    assert result["verdict"] == "BLOCK"


def test_the_gate_is_blind_for_a_class_it_has_no_policy_for(catalog):
    result = assurance.gate({"class": "no.such.class"}, None, catalog)
    assert result["verdict"] == "BLIND"
    assert result["exit_code"] == assurance.EXIT_BLIND


def test_the_gate_never_admits(catalog, tmp_path):
    """Greenlane is the only admission authority. This gate blocks or flags; it never admits."""
    receipt = _receipt(catalog, tmp_path)
    result = assurance.gate({"class": "router.failover"}, receipt, catalog)
    assert result["verdict"] in ("PASS", "REVIEW_REQUIRED", "BLOCK")
    assert "admit" not in json.dumps(result).lower().replace("admission", "")


# --------------------------------------------------------------------------------------
# layer 2: the hypothesis space
# --------------------------------------------------------------------------------------


def _evidence(eid="e1", digest_value="sha256:aa", reliability=1.0, kind="observation"):
    return assurance.Evidence.from_dict(
        {
            "id": eid,
            "source": "test",
            "observation": "an observation",
            "collected_at": "2026-10-29T00:00:00Z",
            "source_digest": digest_value,
            "reliability": reliability,
            "kind": kind,
        }
    )


def _hypothesis(
    hid="h1",
    mechanism="the disk filled",
    prior=0.6,
    likelihoods=None,
    falsifier="e1",
    conjuncts=None,
):
    return assurance.Hypothesis.from_dict(
        {
            "id": hid,
            "mechanism": mechanism,
            "family": "disk",
            "prior": prior,
            "likelihoods": likelihoods or {"e1": 0.8},
            "falsifier": falsifier,
            "conjuncts": conjuncts or [],
        }
    )


def test_a_paraphrase_is_one_hypothesis(catalog):
    one = _hypothesis("h1", "the disk filled up")
    two = _hypothesis("h2", "The  disk  filled up.")
    packet = assurance.build_packet(
        "why is the disk full", [_evidence()], [one, two], catalog
    )
    assert len(packet["hypotheses"]) == 1
    assert packet["merges"], "the merge must be reported, not silent"


def test_a_conjunction_is_not_a_paraphrase(catalog):
    one = _hypothesis("h1", "the disk filled up", conjuncts=["the disk filled up"])
    two = _hypothesis(
        "h2",
        "the disk filled up",
        conjuncts=["the disk filled up", "the lease never expired"],
    )
    packet = assurance.build_packet("why", [_evidence()], [one, two], catalog)
    assert len(packet["hypotheses"]) == 2


def test_the_residual_is_never_pruned(catalog):
    packet = assurance.build_packet("why", [_evidence()], [_hypothesis()], catalog)
    assert packet["unknown"]["posterior"] > 0


def test_the_residual_is_a_first_class_hypothesis(catalog):
    packet = assurance.build_packet("why", [_evidence()], [_hypothesis()], catalog)
    assert packet["unknown"]["id"] == "unknown"
    assert "never pruned" in packet["unknown"]["note"]


def test_evidence_that_refutes_everything_triggers_expansion_not_a_winner(catalog):
    dead = _hypothesis("h1", "the disk filled up", likelihoods={"e1": 0.0})
    other = _hypothesis("h2", "the lease never expired", likelihoods={"e1": 0.0})
    packet = assurance.build_packet("why", [_evidence()], [dead, other], catalog)
    assert all(h["status"] == "falsified" for h in packet["hypotheses"])
    assert packet["expansion_proposals"], (
        "a residual with no live hypothesis must expand"
    )
    assert all(p["posterior"] is None for p in packet["expansion_proposals"]), (
        "a proposed mechanism is not a scored one"
    )


def test_coverage_gaps_are_reported(catalog):
    unused = _evidence("e2", "sha256:bb")
    packet = assurance.build_packet(
        "why", [_evidence(), unused], [_hypothesis()], catalog
    )
    assert any(g.startswith("evidence-unused") for g in packet["coverage_gaps"])


def test_the_edvi_ranking_is_ordered_and_declared_a_proxy(catalog):
    packet = assurance.build_packet(
        "why",
        [_evidence("e1"), _evidence("e2", "sha256:bb")],
        [
            _hypothesis("h1", "the disk filled up", likelihoods={"e1": 0.9}),
            _hypothesis("h2", "the lease never expired", likelihoods={"e1": 0.4}),
        ],
        catalog,
    )
    scores = [r["edvi_per_cost"] for r in packet["ranking"]]
    assert scores == sorted(scores, reverse=True)
    assert any("proxy" in lim for lim in packet["limits"])


def test_duplicate_evidence_ids_are_refused(catalog):
    with pytest.raises(ValueError):
        assurance.build_packet(
            "why", [_evidence("e1"), _evidence("e1")], [_hypothesis()], catalog
        )


def test_evidence_without_a_source_digest_is_refused(catalog):
    with pytest.raises(ValueError):
        assurance.Evidence.from_dict(
            {
                "id": "e1",
                "source": "test",
                "observation": "x",
                "collected_at": "",
                "source_digest": "",
                "reliability": 1.0,
            }
        )


def test_a_hypothesis_without_a_mechanism_is_refused(catalog):
    with pytest.raises(ValueError):
        assurance.Hypothesis.from_dict({"id": "h1", "mechanism": "  ", "prior": 0.5})


# --------------------------------------------------------------------------------------
# the door
# --------------------------------------------------------------------------------------


class _Proc:
    """The result of a door invocation: the code and the bytes it printed."""

    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _run(args):
    """Invoke the door in-process.

    The CLI is the same entry point the executor uses -- main(argv) is what bin/estate-assurance
    and the intent call -- so this exercises the door's own argument parsing and dispatch.
    It is done in-process because a fork on this machine costs seconds, and a test suite that
    costs a minute per assertion is a suite nobody runs. One test below still runs the door as
    a real process, and the failure-class acceptance test runs TWO real processes, because a
    process boundary is the thing being proved there.
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = assurance.main(list(args))
    return _Proc(int(code), buf.getvalue())


def test_the_door_refuses_a_self_exemption_in_words():
    proc = _run(
        ["method", "--class", "router.failover", "--monte-carlo-required", "false"]
    )
    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["selection"]["refused_self_exemption"] is True


def test_the_door_simulates_and_writes_a_receipt(tmp_path):
    out = tmp_path / "receipt.json"
    proc = _run(
        [
            "simulate",
            "--scenario",
            "router.correlated-outage",
            "--seed",
            "7",
            "--samples",
            "200",
            "--out",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stdout
    receipt = json.loads(out.read_text())
    assert receipt["schema"] == "estate.decision-assurance/v1"
    again = _run(
        [
            "simulate",
            "--scenario",
            "router.correlated-outage",
            "--seed",
            "7",
            "--samples",
            "200",
        ]
    )
    assert json.loads(again.stdout)["simulation_digest"] == receipt["simulation_digest"]


def test_the_door_runs_as_a_real_process():
    """The one door test that forks: the entry point must work as an executable."""
    proc = subprocess.run(
        [
            sys.executable,
            str(LIBEXEC / "assurance.py"),
            "method",
            "--class",
            "router.failover",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["selection"]["method"] == "monte_carlo"
