"""An unreadable incident list never refuses a write at edit time (idp#8669).

bin/dof-gate turns an unreadable incident list into the fail-closed `dof-probe` sentinel, which is
right at merge: health unproven. Measured 2026-11-27 18:59 UTC: once #8660 let the deployed write
hook find dof-gate, the hook read the list anonymously on every write, the anonymous GitHub budget
(core 60/h) ran out, and the sentinel refused every idp write fleet-wide ("README.md is outside
every open incident's repairScope ... dof-probe"). The hook's own contract is ok=None on an
unreadable list -- the merge gate still judges (class
edit-time-reader-inherits-merge-fail-closed-sentinel).

These tests drive dof_verdict with a stubbed incident reader: the sentinel is unknown, a real
incident still refuses, a readable list is reused within its TTL, and the sentinel is never cached.
`--optimus` prints 1 when the hook refuses a write on the sentinel (main b04af78dc) and 0 here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "bin/estate-memory-enforce"
SENTINEL = [
    {
        "id": "dof-probe",
        "issue": None,
        "evidence": "incident list unreadable: HTTP Error 403",
    }
]
TARGET = str(REPO / "README.md")


def load(path: Path, name: str):
    sys.path.insert(0, str(REPO / "platform/estate/memory"))
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_file_location(name, str(path), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


DOF = load(REPO / "bin/dof-gate", "dof_gate_for_test")
REGISTRY = json.loads((REPO / "catalog/dof-registry.json").read_text())


def hook_with(reader, source: Path = HOOK, cache: str | None = None):
    """The hook, judging with `reader` as its incident list and a private cache."""
    hook = load(source, f"eme_dof_{abs(hash((str(source), id(reader))))}")
    hook._load_dof = lambda root=None: (
        reader,
        DOF.scope_of,
        DOF.glob_match,
        lambda base: (REGISTRY, True),
    )
    if hasattr(hook, "DOF_CACHE"):
        hook.DOF_CACHE = cache or str(
            Path(tempfile.mkdtemp(prefix="dof-cache-")) / "c.json"
        )
    return hook


class Counting:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def __call__(self, registry):
        self.calls += 1
        return self.answers[min(self.calls, len(self.answers)) - 1]


def refuses_on_unreadable(source: Path = HOOK) -> bool:
    return hook_with(Counting(SENTINEL), source).dof_verdict(TARGET)[0] is False


def test_the_unreadable_sentinel_is_unknown_never_a_refusal():
    ok, why = hook_with(Counting(SENTINEL)).dof_verdict(TARGET)
    assert ok is None and "unreadable" in why


def test_a_real_incident_still_refuses_a_path_outside_its_scope():
    comp = next(iter(REGISTRY["components"]))
    real = [{"id": comp, "issue": 1, "updated_at": "2026-11-27T00:00:00Z"}]
    ok, why = hook_with(Counting(real)).dof_verdict(TARGET)
    assert ok is False and comp in why


def test_a_readable_list_is_reused_within_its_ttl(tmp_path):
    reader = Counting([])
    hook = hook_with(reader, cache=str(tmp_path / "c.json"))
    assert hook.dof_verdict(TARGET)[0] is True
    assert hook.dof_verdict(TARGET)[0] is True
    assert reader.calls == 1
    hook.DOF_CACHE_TTL = 0
    hook.dof_verdict(TARGET)
    assert reader.calls == 2


def test_the_sentinel_is_never_cached(tmp_path):
    reader = Counting(SENTINEL, [])
    hook = hook_with(reader, cache=str(tmp_path / "c.json"))
    assert hook.dof_verdict(TARGET)[0] is None
    assert hook.dof_verdict(TARGET)[0] is True
    assert reader.calls == 2


def test_falsifier_a_hook_that_passes_the_sentinel_through_refuses():
    hook = hook_with(Counting(SENTINEL))
    hook._dof_incidents = lambda open_inc, registry, **_: open_inc(registry)
    assert hook.dof_verdict(TARGET)[0] is False


if __name__ == "__main__" and "--optimus" in sys.argv:
    src = (
        Path(sys.argv[sys.argv.index("--source") + 1])
        if "--source" in sys.argv
        else HOOK
    )
    print(
        f"optimus.hooks.enforce_refuses_on_unreadable_incidents={int(refuses_on_unreadable(src))}"
    )
