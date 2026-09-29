"""The merge loop must believe main requires what the live ruleset actually requires.

platform/github/ruleset.idp.required-checks.json drifted from the live ruleset on
chidionyema/idp for an unknown period: the file said idp-required-checks and required
offline-gate/security-scan/shadow-verify/portal-app, while the live ruleset (24071703) was
named required-checks-main and actually required fast-gate/fast-gate, bdd, guarded-paths,
test, executes-gate, feature-request-plan. bin/idp-pr-landable reads that file to decide which
checks a PR must pass, so a drift there is a drift in every PR verdict.

This loads bin/idp-pr-landable and calls its own required_contexts(), so it grades the set the
merge loop will actually wait for, not a copy of the file's text.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LIVE_REQUIRED = {
    "fast-gate / fast-gate",
    "bdd",
    "guarded-paths",
    "test",
    "executes-gate",
    "feature-request-plan",
}


def _landable():
    path = ROOT / "bin" / "idp-pr-landable"
    loader = importlib.machinery.SourceFileLoader("idp_pr_landable", str(path))
    spec = importlib.util.spec_from_loader("idp_pr_landable", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_merge_loop_waits_for_exactly_the_checks_main_requires():
    assert _landable().required_contexts() == LIVE_REQUIRED


def test_the_merge_loop_reads_the_reconciled_ruleset_not_the_stale_one():
    stale = {"offline-gate", "security-scan", "shadow-verify", "portal-app"}
    assert not (_landable().required_contexts() & stale)
