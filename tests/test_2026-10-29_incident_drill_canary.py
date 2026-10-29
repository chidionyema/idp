"""The incident loop's canary. Injected by `bin/estate-incident-loop drill seed`.

The drill writes this file with a deliberately wrong assertion, so the estate's CI goes red
for a real reason and the loop has a real error to sense. `drill fix` rewrites it to the true
assertion, and the lane goes green and merges. Nothing here is special-cased for the drill:
the same sensors, the same ticket, the same dispatch, the same verdict.

WHERE IT LIVES. Under tests/, because that is where the estate's CI collects test files from
(bin/idp-tests-for's blanket runs every cheap tests/test_*.py); a canary in a directory no CI
job collects would be a drill that cannot fail, and a test that executes nothing is not a test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

LIBEXEC = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "incident-loop.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("incident_loop", LIBEXEC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_policy_scores_a_critical_incident_above_a_minor_one():
    module = _load()
    policy = module.load_policy()
    critical, critical_label = module.score_incident(policy, "critical", "main")
    minor, minor_label = module.score_incident(policy, "minor", "local")
    assert critical < minor, (critical, minor)
    assert critical_label == "P0", critical_label
    assert minor_label == "P2", minor_label
