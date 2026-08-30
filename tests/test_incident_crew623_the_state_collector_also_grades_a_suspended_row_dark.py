"""crew#623's class, second instance (2026-08-30): the estate-state collector still graded a
suspended Flux row as a cluster red. bin/idp-portability-drill learnt on crew#623 that a
`suspend: true` row carries no Ready condition and is OFF, not broken; the collector in
platform/state/cluster-state.yaml kept the same else-branch, so the moment the commerce layer
landed dark (commerce, commerce-data, event-bus) and temporal was parked (idp#923), the
estate-state page said `cluster oke (production): FAIL` on four rows nobody had broken
(break-glass diagnose 33331157383). Worse than the drill instance: a row suspended AFTER a red
keeps its last stale condition frozen (temporal still said "dependency 'flux-system/edge' is
not ready" while edge was True at f92233e4), so the fix must win over a stale condition too.

The class (LAW 6, crew#623): an else-branch that treats "I have no information about this" as
"this is broken". Off, pending, cascaded and broken are four states; a grader that knows three
of them invents the fourth."""

import re
import runpy
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _collect():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def _suspend_branch(collect):
    m = re.search(
        r"^( *)if \(o\.get\(\"spec\"\) or \{\}\)\.get\(\"suspend\"\) is True:\n(?:\1 .*\n|\n)+",
        collect,
        re.M,
    )
    assert m, "the flux loop carries the suspended-row branch"
    return m


def test_the_suspend_branch_exists_after_grading_and_before_append():
    collect = _collect()
    m = _suspend_branch(collect)
    row_built = collect.index('"ready": c.get("status") == "True"')
    appended = collect.index("flux.append(row)", row_built)
    assert row_built < m.start() < appended, (
        "suspend wins after the condition is read, before the row lands"
    )


def _run_branch(snippet, o, row, tmp_path):
    """Run the shipped branch verbatim as a throwaway module: the estate Python standard
    (crew#620, ruff S102) bans exec, and runpy gives the same globals-in, mutation-out."""
    mod = tmp_path / "suspend_branch.py"
    mod.write_text(textwrap.dedent(snippet))
    runpy.run_path(str(mod), init_globals={"o": o, "row": row})


def test_a_suspended_row_is_ready_even_with_a_frozen_stale_condition(tmp_path):
    """Run the shipped branch verbatim against the temporal shape: suspended, stale False."""
    m = _suspend_branch(_collect())
    o = {"spec": {"suspend": True}}
    row = {"ready": False, "message": "dependency 'flux-system/edge' is not ready"}
    _run_branch(m.group(0), o, row, tmp_path)
    assert row["ready"] is True
    assert "suspended" in row["message"]


def test_a_not_suspended_red_row_still_grades_red(tmp_path):
    m = _suspend_branch(_collect())
    o = {"spec": {}}
    row = {"ready": False, "message": "health check failed"}
    _run_branch(m.group(0), o, row, tmp_path)
    assert row["ready"] is False and row["message"] == "health check failed"
