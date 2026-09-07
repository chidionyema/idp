r"""The reconcile ledger's deny list, graded against real notification-controller messages.

`platform/alerts-github/alert.yaml` filters which Flux events become a repository_dispatch on
this repository, and on 2026-09-07 that filter was carrying 11,328 GitHub Actions runs a day
because one of its three patterns matched only half of what it names. Flux puts every object a
Kustomization applied into ONE event, newline-separated; Go's regexp is not multi-line by
default, so `^Kind/name configured$` never matched a four-line message and every one of those
events was dispatched. 80 of the 112 events an hour still reaching GitHub were that leak.

So the patterns are graded here, as data read out of the manifest, against message strings
copied verbatim from `kubectl -n flux-system logs deploy/notification-controller`. A change to
the deny list that starts dropping `health check failed` fails this file.

Go's regexp (RE2) and Python's `re` agree on everything these patterns use, with one spelling
difference: Go writes end-of-text as `\z` and Python as `\Z`. `_to_python` below is that
single translation and nothing else, so what is graded is the pattern the controller compiles.
"""

import re
from pathlib import Path

import pytest
import yaml

ALERT = (
    Path(__file__).resolve().parent.parent / "platform" / "alerts-github" / "alert.yaml"
)


def _patterns():
    spec = yaml.safe_load(ALERT.read_text())["spec"]
    return spec["exclusionList"]


def _to_python(pattern):
    """Go's end-of-text anchor is `\\z`; Python spells the same thing `\\Z`."""
    return pattern.replace(r"\z", r"\Z")


def _dispatched(message):
    """True when the event survives the deny list and becomes a GitHub Actions run.

    notification-controller drops an event when ANY exclusion pattern matches anywhere in the
    message (regexp.MatchString, unanchored), which is why the drift pattern anchors itself.
    """
    return not any(re.search(_to_python(p), message) for p in _patterns())


# Verbatim from notification-controller, 2026-09-07 20:20Z. The first is the leak.
MULTILINE_DRIFT = (
    "NetworkPolicy/otto-gateway/allow-dns-egress configured\n"
    "NetworkPolicy/otto-gateway/default-deny-all configured\n"
    "NetworkPolicy/otto-golden/allow-dns-egress configured\n"
    "NetworkPolicy/otto-golden/default-deny-all configured"
)
SINGLE_DRIFT = "ServiceAccount/kube-system/calico-node configured"
HEARTBEAT = "Reconciliation finished in 1.113946ms, next run in 10m0s"
DEPENDENCY_REPEAT = "Dependencies do not meet ready condition, retrying"

HEALTH_PASSED = "Health check passed in 1.238s"
HEALTH_FAILED = (
    "health check failed after 30.001s: timeout waiting for: "
    "[Deployment/mcp/estate-mcp status: 'InProgress']"
)
TIMEOUT = (
    "timeout waiting for: [ClusterRole/calico-cni-plugin status: 'Terminating', "
    "ClusterRole/calico-node status: 'Terminating']"
)
CREATED_JOB = "Job/observability/estate-db-copy-langfuse-r7 created"
DRIFT_THEN_FAILURE = MULTILINE_DRIFT + "\n" + HEALTH_FAILED


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(MULTILINE_DRIFT, id="four-networkpolicies-in-one-event"),
        pytest.param(SINGLE_DRIFT, id="one-object-reapplied"),
        pytest.param(CREATED_JOB, id="cronjob-spawned-its-job"),
        pytest.param(HEARTBEAT, id="reconcile-heartbeat"),
        pytest.param(DEPENDENCY_REPEAT, id="dependency-not-ready-repeat"),
    ],
)
def test_an_event_that_changes_nothing_the_workflow_acts_on_never_reaches_github(
    message,
):
    assert not _dispatched(message)


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(HEALTH_PASSED, id="passed-is-what-closes-a-P0"),
        pytest.param(HEALTH_FAILED, id="failed-is-what-opens-one"),
        pytest.param(TIMEOUT, id="bare-timeout-carries-no-health-prefix"),
        pytest.param(DRIFT_THEN_FAILURE, id="failure-buried-under-four-drift-lines"),
    ],
)
def test_a_failure_still_reaches_the_board_even_when_drift_shares_its_event(message):
    assert _dispatched(message)


def test_every_pattern_compiles_and_anchors_itself():
    """An unanchored deny pattern matches mid-message and drops events nobody meant to drop."""
    for pattern in _patterns():
        compiled = re.compile(
            _to_python(pattern)
        )  # raises if the manifest ships a bad regex
        assert pattern.startswith(("^", r"\A")), (
            f"{compiled.pattern} floats free of the start"
        )
