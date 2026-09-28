"""A reset connection to a chart host is retried; a chart that is wrong still fails.

Run 34122274707, 2026-09-07: `read: connection reset by peer` fetching index.yaml from
charts.signoz.io and go.temporal.io turned into

    FAIL  render   platform/observability-collector: the render did not complete
    FAIL  render   platform/temporal: the render did not complete

on main, for two directories nobody had touched, and rule-guard then refused every merge onto
the red main it produced. bin/lib/helm_retry.py is the fix; these grade it by counting what it
actually asks for, with a fake helm and a fake clock, so the suite pays nothing to run them.
"""

import importlib.machinery
import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_loader(
    "helm_retry",
    importlib.machinery.SourceFileLoader(
        "helm_retry", str(ROOT / "bin" / "lib" / "helm_retry.py")
    ),
)
helm_retry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helm_retry)

RESET = (
    'Error: looks like "https://charts.signoz.io" is not a valid chart repository or cannot '
    'be reached: Get "https://charts.signoz.io/index.yaml": read tcp '
    "10.1.0.165:33676->185.199.108.153:443: read: connection reset by peer"
)


def _helm(failures, out="---\nkind: ConfigMap\n"):
    """A helm that hangs up `failures` times and then renders. Records every call."""
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if len(calls) <= failures:
            return subprocess.CompletedProcess(cmd, 1, "", RESET)
        return subprocess.CompletedProcess(cmd, 0, out, "")

    return calls, run


def _slept():
    waits = []
    return waits, waits.append


def test_a_host_that_hangs_up_once_is_asked_again_and_the_render_succeeds():
    calls, run = _helm(failures=1)
    waits, sleep = _slept()
    r, tried = helm_retry.template(["helm"], {}, sleep=sleep, run=run)
    assert r.returncode == 0
    assert len(calls) == 2
    assert len(tried) == 1  # the reset is remembered, not swallowed
    assert waits == [1.5]  # and it waited before asking again


def test_a_chart_that_is_genuinely_wrong_is_asked_three_times_and_then_fails():
    calls, run = _helm(failures=99)
    waits, sleep = _slept()
    r, tried = helm_retry.template(["helm"], {}, sleep=sleep, run=run)
    assert r.returncode == 1
    assert len(calls) == helm_retry.ATTEMPTS == 3
    assert len(tried) == 3
    assert "connection reset by peer" in tried[-1]
    assert waits == [1.5, 3.0]  # widening, and never after the last attempt


def test_a_chart_that_renders_is_asked_exactly_once():
    calls, run = _helm(failures=0)
    waits, sleep = _slept()
    r, tried = helm_retry.template(["helm"], {}, sleep=sleep, run=run)
    assert r.returncode == 0
    assert len(calls) == 1
    assert tried == [] and waits == []  # the happy path pays nothing for the retry


def test_a_failure_with_no_stderr_still_reports_something():
    """LAW 28: an instrument that reports an empty string has destroyed the cause."""

    def run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 7, "", "")

    _, tried = helm_retry.template(["helm"], {}, sleep=lambda _: None, run=run)
    assert tried == ["exit 7"] * 3
