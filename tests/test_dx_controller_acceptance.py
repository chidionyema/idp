"""Gate proving the DX VoI controller (C) still beats the ladders (A/B).

The V5 acceptance bar (REPORT_3.md / trial_results_v5.json) is, per regime:
  - detection  >= best of A/B
  - false positives == 0   (the strong bar; A/B accumulate FPs under noise)
  - cost        < the cheaper of A/B  (a real saving, not a lucky mean)
  - ECE         <= 0.02
The gate asserts those on the real controller, and a falsifier mutates the controller to a
single-sample-verdict variant that must FAIL, proving the gate rejects a real regression and is
not a tautology. Deterministic: every target's fault/signal stream is a fixed seed, so the gate
is reproducible run-to-run (no Monte Carlo flake).
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "platform" / "dx" / "dx_harness_v5.py"


def _load():
    """Load the DX harness by file path, avoiding the ``platform`` name collision.

    ``idp/platform/`` shadows Python's stdlib ``platform`` module, and there is no
    ``platform/__init__.py`` (the estate's ``platform`` tree is a namespace, not a package).
    ``from platform.dx import ...`` therefore resolves to the *stdlib* ``platform`` and raises
    ``No module named 'platform.dx'``. Load the module by its realpath so the gate is correct
    in any environment, not just the one where conftest rigs sys.path.
    """
    spec = importlib.util.spec_from_file_location("dx_harness_v5", str(MODULE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def h():
    """A fresh module load so the SIG-override mutation in run_regime starts clean."""
    return _load()


def _acceptance(h, regime, trials=15, targets=5):
    acc = h.run_regime(regime, n_trials=trials, n_targets=targets)
    s = {ctl: h.summarize(acc[ctl]) for ctl in "ABC"}
    best_det = max(s["A"]["det_rate"], s["B"]["det_rate"])
    cheaper = min(s["A"]["cost"], s["B"]["cost"])
    return s["C"], best_det, cheaper


@pytest.mark.parametrize("regime", ["V5a_noisy", "V5b_priors", "V5c_redundant"])
def test_controller_meets_v5_acceptance(h, regime):
    c, best_det, cheaper = _acceptance(h, regime)
    assert c["det_rate"] >= best_det, "%s: C det_rate %.4f < best-of-AB %.4f" % (
        regime,
        c["det_rate"],
        best_det,
    )
    assert c["fp"] == 0, "%s: C false positives %d != 0" % (regime, c["fp"])
    assert c["cost"] < cheaper, "%s: C cost %.4f not < cheaper ladder %.4f" % (
        regime,
        c["cost"],
        cheaper,
    )
    assert c["ece"] <= 0.02, "%s: C ECE %.4f > 0.02" % (regime, c["ece"])


def test_a_single_sample_verdict_controller_is_refused(h):
    """Falsifier: break the evidence-multiplicity rule and the gate must go red.

    The real controller requires >=2 positive signature observations before a fault verdict
    (and >=2 confirmed negatives before suppression). A variant that verdicts on one sample
    is exactly the bug class the V5 trials eliminated; the acceptance assertions (FP == 0)
    must catch it.
    """

    # Sabotage BOTH rules the V5 trials made substrate-enforced: no posterior floor AND no
    # evidence multiplicity. This is the pre-fix controller that verdicted on whatever class
    # led after a single observation -- the exact defect the trials eliminated (FP 25%).
    def single_sample_termination(b, pos, neg, priors, conf_min=h.CONF):
        # verdict on the leading class immediately, no confidence gate, no >=2 sample rule
        return max(b, key=b.get)

    h.check_termination = single_sample_termination
    c, best_det, _ = _acceptance(h, "V5a_noisy")
    # The noisy regime is where single-sample verdicts accumulate false positives,
    # so the broken controller must breach at least one acceptance line.
    assert not (c["det_rate"] >= best_det and c["fp"] == 0), (
        "falsifier failed: a single-sample controller still met the bar "
        "(det %.4f fp %d) -- the gate would not catch this regression"
        % (c["det_rate"], c["fp"])
    )
