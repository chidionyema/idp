r"""The reconcile ledger's deny list, run through the engine that actually applies it.

`platform/alerts-github/alert.yaml` decides which Flux events become a repository_dispatch on
this repository, and on 2026-09-07 that filter was letting through 80 events an hour it was
written to stop. Flux puts every object a Kustomization applied into ONE event, newline
separated; Go's regexp is not multi-line by default, so `^Kind/name configured$` matched the
one-object messages and never once matched a four-line one.

A Python stand-in would not have caught that and would not catch the next one, because the
defect was in a difference between regexp engines. So this compiles the patterns straight out
of the manifest with Go's `regexp` -- RE2, the same package notification-controller links -- and
runs them against message strings copied verbatim from
`kubectl -n flux-system logs deploy/notification-controller`. What is graded is the filter the
controller will run, not a translation of it.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ALERT = ROOT / "platform" / "alerts-github" / "alert.yaml"

# notification-controller drops an event when ANY exclusion pattern matches anywhere in the
# message: regexp.MatchString, unanchored (internal/server/event_server.go). Hence the harness
# below, and hence why the drift pattern has to anchor itself.
MATCHER = r"""
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
)

type in struct {
	Patterns []string `json:"patterns"`
	Messages []string `json:"messages"`
}

func main() {
	var q in
	if err := json.NewDecoder(os.Stdin).Decode(&q); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	res := map[string]bool{}
	for _, m := range q.Messages {
		dispatched := true
		for _, p := range q.Patterns {
			re, err := regexp.Compile(p)
			if err != nil {
				fmt.Fprintf(os.Stderr, "pattern %q does not compile: %v\n", p, err)
				os.Exit(2)
			}
			if re.MatchString(m) {
				dispatched = false
			}
		}
		res[m] = dispatched
	}
	json.NewEncoder(os.Stdout).Encode(res)
}
"""


@pytest.fixture(scope="module")
def dispatched():
    """Return {message: True if it reaches GitHub}, decided by Go's own regexp."""
    go = shutil.which("go")
    if go is None:
        pytest.skip(
            "go toolchain absent; this test grades RE2 and will not fake it in another engine"
        )
    patterns = yaml.safe_load(ALERT.read_text())["spec"]["exclusionList"]
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "main.go"
        src.write_text(MATCHER)
        env = {**os.environ, "GOCACHE": str(Path(tmp) / "cache"), "GOFLAGS": "-mod=mod"}
        proc = subprocess.run(
            [go, "run", str(src)],
            input=json.dumps({"patterns": patterns, "messages": ALL_MESSAGES}),
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
    assert proc.returncode == 0, f"go regexp harness failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


# Verbatim from notification-controller, 2026-09-07 20:20Z. The first is the leak that was
# costing 80 GitHub Actions runs an hour.
MULTILINE_DRIFT = (
    "NetworkPolicy/otto-gateway/allow-dns-egress configured\n"
    "NetworkPolicy/otto-gateway/default-deny-all configured\n"
    "NetworkPolicy/otto-golden/allow-dns-egress configured\n"
    "NetworkPolicy/otto-golden/default-deny-all configured"
)
SINGLE_DRIFT = "ServiceAccount/kube-system/calico-node configured"
CREATED_JOB = "Job/observability/estate-db-copy-langfuse-r7 created"
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
DRIFT_THEN_FAILURE = MULTILINE_DRIFT + "\n" + HEALTH_FAILED

DROPPED = [MULTILINE_DRIFT, SINGLE_DRIFT, CREATED_JOB, HEARTBEAT, DEPENDENCY_REPEAT]
KEPT = [HEALTH_PASSED, HEALTH_FAILED, TIMEOUT, DRIFT_THEN_FAILURE]
ALL_MESSAGES = DROPPED + KEPT


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
    dispatched, message
):
    assert dispatched[message] is False


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(HEALTH_PASSED, id="passed-is-what-closes-a-P0"),
        pytest.param(HEALTH_FAILED, id="failed-is-what-opens-one"),
        pytest.param(TIMEOUT, id="bare-timeout-carries-no-health-prefix"),
        pytest.param(DRIFT_THEN_FAILURE, id="failure-buried-under-four-drift-lines"),
    ],
)
def test_a_failure_still_reaches_the_board_even_when_drift_shares_its_event(
    dispatched, message
):
    assert dispatched[message] is True
