"""crew#292: verify-drill had never once been green -- 22 runs, 22 failures, no first green on
record. The attribution was not the drill. platform/hermes-agent/gateway.yaml declares the A2A
gateway token with refreshInterval "0", which is ESO's "sync once, then never poll", chosen so a
rotation under a running gateway stays a deliberate act. The crew#387 staleness rule read that
"0" as unparseable, fell back to a 1h interval, and graded the row not-ready two hours after it
synced -- with no later age at which it could recover, because refreshTime never moves again.
Every run since has carried `BLIND receipt not-ready ExternalSecret hermes-agent/hermes-agent-a2a`
and exited 1.

Rules this file holds:
  1. An explicit zero has no interval to be late against: the row is left as ESO reports it.
  2. A zero written as an int is the same zero as a string. `or "1h"` collapsed the int to the
     default, which is the silent miss case that hides one config shape and no test failed.
  3. The crew#387 rule survives intact for every interval that IS one: 2x, floored at 2h.
  4. A never-synced ExternalSecret is still stale. Absent evidence is not evidence of freshness.
  5. The class, not the instance: for every interval the collector accepts there is an age at
     which the row reads ok. A grading rule with a permanently-red configuration is an outage
     (LAW 38), and that is the shape this incident was.

The function is lifted out of the deployed ConfigMap by ast and executed. Nothing here asserts on
the text of the source: a mutation to the rule has to turn a named test red.
"""
import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
NOW = datetime(2026, 8, 28, 12, 32, 0, tzinfo=timezone.utc)
# the live row, verbatim from verify-drill run 33171419917: frozen 14.6h before NOW
LIVE_FROZEN = {"refreshTime": "2026-08-27T21:55:54Z"}


def _collect() -> str:
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def _stale_sync():
    """The real function out of the manifest the cluster runs, executed, not string-matched."""
    fn = next(n for n in ast.walk(ast.parse(_collect()))
              if isinstance(n, ast.FunctionDef) and n.name == "stale_sync")
    ns = {"re": re, "datetime": datetime, "timezone": timezone}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "collect.py", "exec"), ns)
    return ns["stale_sync"]


def _at(age: timedelta) -> dict:
    return {"refreshTime": (NOW - age).strftime("%Y-%m-%dT%H:%M:%SZ")}


@pytest.mark.parametrize("iv", ["0", 0, "0s", "0m", "0h", "0h0m"])
def test_an_explicit_zero_is_never_late_however_old_the_last_sync_is(iv):
    """Rule 1 and 2. The int is the miss case `or "1h"` swallowed."""
    assert _stale_sync()({"refreshInterval": iv}, LIVE_FROZEN, NOW) == ""
    assert _stale_sync()({"refreshInterval": iv}, _at(timedelta(days=400)), NOW) == ""


def test_the_live_a2a_row_that_took_every_verify_drill_down_now_reads_ok():
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/hermes-agent/gateway.yaml").read_text()) if d]
    es = next(d for d in docs if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "hermes-agent-a2a")
    assert es["spec"]["refreshInterval"] == "0", "the incident is only fixed while the declaration stands"
    assert _stale_sync()(es["spec"], LIVE_FROZEN, NOW) == ""


@pytest.mark.parametrize("iv,secs", [("1h", 3600), ("30m", 1800), ("90s", 90), ("1h30m", 5400)])
def test_a_real_interval_is_still_graded_at_twice_it_with_a_two_hour_floor(iv, secs):
    """Rule 3. crew#387 is not weakened by the zero case."""
    f, bar = _stale_sync(), max(2 * secs, 7200)
    assert f({"refreshInterval": iv}, _at(timedelta(seconds=bar - 60)), NOW) == ""
    late = f({"refreshInterval": iv}, _at(timedelta(seconds=bar + 60)), NOW)
    assert late.startswith("Ready but last sync") and f"2x refreshInterval {iv}" in late


def test_an_absent_interval_is_the_one_hour_default_not_a_zero():
    f = _stale_sync()
    assert f({}, LIVE_FROZEN, NOW).startswith("Ready but last sync")
    assert f(None, LIVE_FROZEN, NOW).startswith("Ready but last sync")
    assert f({}, _at(timedelta(minutes=1)), NOW) == ""


@pytest.mark.parametrize("iv", ["", "always", "1 hour", "-5m"])
def test_an_interval_that_parses_to_nothing_falls_back_to_an_hour_not_to_never_stale(iv):
    """A value the parser cannot read must not become a second silent way to be exempt."""
    assert _stale_sync()({"refreshInterval": iv}, LIVE_FROZEN, NOW).startswith("Ready but last sync")


@pytest.mark.parametrize("status", [{}, None, {"refreshTime": None}, {"refreshTime": "not a time"}])
def test_an_externalsecret_that_has_never_synced_is_stale(status):
    """Rule 4."""
    assert _stale_sync()({"refreshInterval": "1h"}, status, NOW).startswith("Ready but last sync")


@pytest.mark.parametrize("iv", ["0", "1s", "90s", "5m", "1h", "24h", "168h", "", "always"])
def test_every_accepted_interval_has_an_age_at_which_the_row_reads_ok(iv):
    """Rule 5, the class guard. This is the shape of the incident, not its instance: a rule with
    a configuration that is red at every age can never be repaired by the cluster behaving."""
    f = _stale_sync()
    assert f({"refreshInterval": iv}, _at(timedelta(seconds=0)), NOW) == "", iv


def test_the_externalsecret_branch_calls_the_rule_rather_than_grading_inline_again():
    """Wiring: the loop must reach the function, or the tests above grade code nothing runs."""
    tree = ast.parse(_collect())
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "stale_sync" in called
    inline = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
              and isinstance(n.value, str) and "older than 2x refreshInterval" in n.value]
    assert len(inline) == 1, "the message is built in one place, so one edit changes the rule"
