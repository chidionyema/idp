"""bin/estate-diagnose: Bayesian posterior arithmetic and its refusals.

crew#654, founder 2026-09-29: "no theories without bayesian reasoning and evidence gathering",
"we don't do guesswork". This tool is the only thing allowed to turn a diagnosis record into a
posterior; these cases pin the arithmetic against a hand-computed two-hypothesis case and pin
every refusal the docstring promises.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import math
import os

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "bin", "estate-diagnose")


def _load():
    # bin/estate-diagnose has no .py suffix, so spec_from_file_location cannot infer a loader
    # from the extension; hand it one explicitly (same reason platform/llm/*.py based tests
    # don't need this -- they have a real suffix).
    loader = importlib.machinery.SourceFileLoader("estate_diagnose", MODULE_PATH)
    spec = importlib.util.spec_from_file_location(
        "estate_diagnose", MODULE_PATH, loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


def _hand_computed_two_hypothesis_posterior() -> dict:
    """8 heads / 2 tails. H1: fair coin (0.5/0.5). H2: biased (0.9/0.1). Uniform priors.

    log P(H1|D) unnorm = ln(0.5) + 8*ln(0.5) + 2*ln(0.5)
    log P(H2|D) unnorm = ln(0.5) + 8*ln(0.9) + 2*ln(0.1)
    normalize by log-sum-exp.
    """
    lp1 = math.log(0.5) + 8 * math.log(0.5) + 2 * math.log(0.5)
    lp2 = math.log(0.5) + 8 * math.log(0.9) + 2 * math.log(0.1)
    peak = max(lp1, lp2)
    denom = math.log(math.exp(lp1 - peak) + math.exp(lp2 - peak)) + peak
    return {"H1": math.exp(lp1 - denom), "H2": math.exp(lp2 - denom)}


def _two_hypothesis_record() -> dict:
    return {
        "hypotheses": [
            {"name": "H1", "prior": 0.5},
            {"name": "H2", "prior": 0.5},
        ],
        "evidence": [
            {
                "name": "coin flips",
                "observed": {"heads": 8, "tails": 2},
                "likelihoods": {
                    "H1": {"heads": 0.5, "tails": 0.5},
                    "H2": {"heads": 0.9, "tails": 0.1},
                },
            }
        ],
    }


def test_posterior_matches_hand_computed_two_hypothesis_case(mod):
    expected = _hand_computed_two_hypothesis_posterior()
    got = mod.compute_posteriors(_two_hypothesis_record())
    assert got["H1"] == pytest.approx(expected["H1"], abs=1e-9)
    assert got["H2"] == pytest.approx(expected["H2"], abs=1e-9)
    assert (
        got["H2"] > got["H1"]
    )  # the biased-coin hypothesis explains 8/10 heads far better
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-9)


def test_posteriors_sum_to_one_with_three_hypotheses(mod):
    record = {
        "hypotheses": [
            {"name": "A", "prior": 0.2},
            {"name": "B", "prior": 0.3},
            {"name": "C", "prior": 0.5},
        ],
        "evidence": [
            {
                "name": "e1",
                "observed": {"x": 4, "y": 6},
                "likelihoods": {
                    "A": {"x": 0.3, "y": 0.7},
                    "B": {"x": 0.5, "y": 0.5},
                    "C": {"x": 0.9, "y": 0.1},
                },
            }
        ],
    }
    got = mod.compute_posteriors(record)
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-9)


def test_n_eff_divisor_shrinks_the_evidence_without_changing_the_winner(mod):
    record = _two_hypothesis_record()
    undivided = mod.compute_posteriors(record)
    record["n_eff_divisor"] = 10
    divided = mod.compute_posteriors(record)
    # Down-weighting correlated evidence pulls the posterior back toward the (uniform) prior.
    assert divided["H2"] < undivided["H2"]
    assert divided["H2"] > 0.5  # still favors H2, just less confidently


def test_real_record_sk4bd_evidence_alone_gives_h1_about_0_998(mod):
    """The number named in the crew#654 ticket for the first evidence item alone, used here as
    an arithmetic pin independent of the full two-evidence record committed to docs/diagnoses/."""
    record = {
        "hypotheses": [
            {"name": "H1", "prior": 0.3333333333},
            {"name": "H2", "prior": 0.3333333333},
            {"name": "H3", "prior": 0.3333333333},
        ],
        "n_eff_divisor": 10,
        "evidence": [
            {
                "name": "sk-4bd",
                "observed": {"fast": 153, "deepseek": 50, "minimax": 0},
                "likelihoods": {
                    "H1": {"fast": 0.70, "deepseek": 0.20, "minimax": 0.10},
                    "H2": {
                        "fast": 0.3636363636,
                        "deepseek": 0.4141414141,
                        "minimax": 0.2222222222,
                    },
                    "H3": {"fast": 0.10, "deepseek": 0.20, "minimax": 0.70},
                },
            }
        ],
    }
    got = mod.compute_posteriors(record)
    assert got["H1"] == pytest.approx(0.998, abs=2e-3)


def test_refuses_priors_that_do_not_sum_to_one(mod):
    record = _two_hypothesis_record()
    record["hypotheses"][0]["prior"] = 0.4
    with pytest.raises(mod.Refused, match="priors sum to"):
        mod.compute_posteriors(record)


def test_priors_within_tolerance_are_accepted(mod):
    record = _two_hypothesis_record()
    record["hypotheses"][0]["prior"] = 0.5 + 1e-9
    record["hypotheses"][1]["prior"] = 0.5 - 1e-9
    mod.compute_posteriors(record)  # must not raise


def test_refuses_evidence_missing_a_hypothesis_likelihood(mod):
    record = _two_hypothesis_record()
    del record["evidence"][0]["likelihoods"]["H2"]
    with pytest.raises(mod.Refused, match="no likelihood distribution"):
        mod.compute_posteriors(record)


def test_refuses_evidence_missing_a_category_for_one_hypothesis(mod):
    record = _two_hypothesis_record()
    del record["evidence"][0]["likelihoods"]["H2"]["tails"]
    with pytest.raises(mod.Refused, match="missing category"):
        mod.compute_posteriors(record)


def test_refuses_a_hypothesis_with_no_prior(mod):
    record = _two_hypothesis_record()
    del record["hypotheses"][1]["prior"]
    with pytest.raises(mod.Refused, match="no 'prior'"):
        mod.compute_posteriors(record)


def test_cli_refuses_bad_priors_file(mod, tmp_path):
    record = _two_hypothesis_record()
    record["hypotheses"][0]["prior"] = 0.9
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(record))
    rc = mod.main([str(p), "--no-write"])
    assert rc == 2


def test_cli_writes_posteriors_back_by_default(mod, tmp_path):
    p = tmp_path / "record.yaml"
    p.write_text(yaml.safe_dump(_two_hypothesis_record()))
    rc = mod.main([str(p)])
    assert rc == 0
    written = yaml.safe_load(p.read_text())
    assert "posteriors" in written
    assert written["winner"] == "H2"
    assert written["posteriors"]["H1"] + written["posteriors"]["H2"] == pytest.approx(
        1.0, abs=1e-6
    )


def test_cli_no_write_leaves_the_file_untouched(mod, tmp_path):
    p = tmp_path / "record.yaml"
    original = yaml.safe_dump(_two_hypothesis_record())
    p.write_text(original)
    rc = mod.main([str(p), "--no-write"])
    assert rc == 0
    assert p.read_text() == original


def test_cli_min_posterior_below_threshold_exits_3(mod, tmp_path):
    p = tmp_path / "record.yaml"
    p.write_text(yaml.safe_dump(_two_hypothesis_record()))
    rc = mod.main([str(p), "--no-write", "--min-posterior", "0.999999"])
    assert rc == 3


def test_cli_min_posterior_met_exits_0(mod, tmp_path):
    p = tmp_path / "record.yaml"
    p.write_text(yaml.safe_dump(_two_hypothesis_record()))
    rc = mod.main([str(p), "--no-write", "--min-posterior", "0.5"])
    assert rc == 0


def test_committed_record_reaches_required_posterior(mod):
    """The real crew#654 record ships with its posteriors already computed; recomputing them
    from its own priors and likelihoods must reach the same winner with posterior >= 0.95 --
    this is exactly what bin/diagnosis-gate relies on."""
    path = os.path.join(
        ROOT, "docs", "diagnoses", "2026-09-29-laptop-router-auth-errors.yaml"
    )
    record = yaml.safe_load(open(path, encoding="utf-8").read())
    posteriors = mod.compute_posteriors(record)
    winner = max(posteriors, key=posteriors.get)
    assert winner == "H1"
    assert posteriors["H1"] >= 0.95
