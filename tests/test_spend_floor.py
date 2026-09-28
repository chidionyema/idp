"""The spend floor catches the shape of the 2026-09-13 leak, on the incident's own numbers.

WHAT THIS GRADES. `bin/idp-spend-floor` reads the router's spend ledger and reports per key: the
biggest single call, the ratio of input to output, and the share of budget already spent.

The claim is narrow and checkable: given the rows the ledger actually held that day, it speaks.
The rows below are the measured values, not invented ones -- 439 calls, 86,525,924 input tokens,
737,169 as the largest single call, $12.13 of a $15.00 budget.

WHY EACH ASSERTION EXISTS. Every one of these is a specific way the estate failed to notice:

  * the existing breaker sums every key into one hourly total, so a single 737k call is
    numerically identical to two hundred 3.7k calls. `test_the_shape_is_reported_without_a_total`
    feeds ONE key and requires the finding anyway -- a check that needs a total cannot pass that.
  * the ratio is what separates "a large document" from "a session re-sending itself". The test
    builds both and requires the estate to tell them apart, because a guard that refuses a
    genuinely large prompt is an outage (R38).
  * LiteLLM stops a key at 100% of budget with no warning, and that day's key sat at $12.13 of
    $15.00 while nobody was told. `test_a_key_near_its_budget_is_named` requires the warning that
    would have arrived with 81 minutes still on the clock.
  * a broken ledger query must FAIL, never report clean. The breaker this replaces swallowed its
    own error and read $0.00 for weeks while the estate spent.
"""

import importlib.util
import pathlib
import sys

import pytest

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-spend-floor"


def _load():
    """Load the gate by path: it is a bin script, not an installed package."""
    spec = importlib.util.spec_from_loader("spend_floor", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__file__"] = str(BIN)
    source = BIN.read_text(encoding="utf-8")
    exec(compile(source, str(BIN), "exec"), mod.__dict__)  # noqa: S102
    sys.modules["spend_floor"] = mod
    return mod


@pytest.fixture(scope="module")
def floor():
    return _load()


def _incident_row(**over):
    """The row the ledger actually held for the leaking key on 2026-09-13."""
    row = {
        "alias": "laptop-20260829T143252Z",
        "key8": "961a3bcd",
        "calls": "439",
        "input_tokens": "86525924",
        "output_tokens": "137728",
        "biggest_call": "737169",
        "usd": "12.13",
        "max_budget": "15.00",
        "pct_of_budget": "80.9",
    }
    row.update(over)
    return row


def test_the_shape_is_reported_without_a_total(floor):
    """ONE key. No estate-wide sum anywhere. The finding must still come.

    This is the assertion the existing breaker cannot satisfy: it grades a total, and a total is
    what made one runaway session look like an ordinary busy hour.
    """
    found = floor.findings([_incident_row()], window=60)
    assert found, "the incident's own row produced no finding"
    assert any("737,169" in f for f in found)


def test_the_ratio_is_named(floor):
    """3,685 tokens in per token out is a session re-sending its history, and it must say so."""
    found = floor.findings([_incident_row()], window=60)
    assert any("whole history" in f for f in found), found


def test_a_genuinely_large_prompt_is_not_accused(floor):
    """R38: a guard that refuses correct work is an outage.

    A big call with a balanced ratio is a large document -- real work. It may be mentioned, but
    it must NOT be called a session re-sending itself.
    """
    honest = _incident_row(
        biggest_call="240000", input_tokens="900000", output_tokens="300000"
    )
    found = floor.findings([honest], window=60)
    assert not any("whole history" in f for f in found), (
        "a 3:1 large prompt was accused of re-sending its history"
    )


def test_an_ordinary_hour_is_silent(floor):
    """The guard must not cry wolf on a normal window, or nobody reads it."""
    ordinary = _incident_row(
        calls="200",
        input_tokens="700000",
        output_tokens="120000",
        biggest_call="3700",
        usd="0.02",
        pct_of_budget="0.1",
    )
    assert floor.findings([ordinary], window=60) == []


def test_a_key_near_its_budget_is_named(floor):
    """The warning that would have arrived with 81 minutes still on the clock."""
    found = floor.findings([_incident_row()], window=60)
    assert any("budget" in f and "80.9%" in f for f in found), found


def test_a_key_far_from_its_budget_is_not_named_for_it(floor):
    healthy = _incident_row(pct_of_budget="12.0", usd="1.80")
    found = floor.findings([healthy], window=60)
    assert not any("budget" in f for f in found)


def test_the_ratio_boundary_is_not_a_tripwire(floor):
    """At the threshold is ordinary work; just over it is the pattern."""
    at = _incident_row(
        biggest_call="300000", input_tokens="4000000", output_tokens="20000"
    )
    assert floor.RATIO_OUTLIER == 200
    found = floor.findings([at], window=60)
    assert any("whole history" in f for f in found), "exactly at the ratio did not fire"


def test_a_broken_ledger_fails_closed(floor, monkeypatch):
    """A checker that cannot read must FAIL. The breaker this replaces read $0.00 for weeks."""
    import subprocess

    def _boom(*a, **k):
        raise subprocess.CalledProcessError(1, "psql", stderr="connection refused")

    monkeypatch.setattr(floor.subprocess, "run", _boom)
    monkeypatch.setattr(sys, "argv", ["idp-spend-floor", "--password-file", __file__])
    assert floor.main() == 1


def test_a_missing_password_file_fails_closed(floor, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["idp-spend-floor", "--password-file", "/nonexistent/pw"]
    )
    assert floor.main() == 1
