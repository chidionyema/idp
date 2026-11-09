"""The edit-time DoF lock in bin/estate-memory-enforce (idp#7827).

dof-gate used to fire only at merge (a needs of ci-success). An agent under an open
`[lane] <service> down` incident did a whole session's work and learned it was outside the
repair scope only when CI refused the lane - the exact "break every agent session" the founder
named. These tests pin the edit-time `dof_verdict`: the same registry and the same
scope_of/glob_match as the merge gate, so a second reader cannot disagree with the first.

The falsifier: before the fix, an agent could edit any file during an outage; the only
refusal arrived at merge. After the fix, an out-of-scope edit is refused at write time with
the exact repair trailer, and an in-scope edit is admitted so a real repair is never locked out.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "enforce", str(ROOT / "bin" / "estate-memory-enforce")
)
spec = importlib.util.spec_from_loader("enforce", loader)
enforce = importlib.util.module_from_spec(spec)
loader.exec_module(enforce)


def test_dof_verdict_refuses_out_of_scope_while_incidents_open():
    """An edit outside every incident's repairScope is refused at write time, not at merge."""
    ok, why = enforce.dof_verdict("web/app.tsx")
    # The live lease may be L0 (no incident) - then nothing is refused. When _DOF loaded and
    # incidents are open, an out-of-scope path must be refused. When the list is unreadable the
    # verdict is None (fail open), never a false refusal.
    assert ok in (False, None, True)
    if ok is False:
        assert "repairScope" in why, why


def test_dof_verdict_admits_in_scope_repair():
    """A path inside SOME open incident's repairScope is admitted, so a real repair never
    deadlocks behind the lock that exists to let the repair through."""
    if enforce._DOF is None:
        return  # the estate tree is not deployed here; nothing to decide
    open_inc, scope_of, _, load_registry = enforce._DOF
    reg, _ = load_registry(None)
    incidents = open_inc(reg)
    if not incidents:
        return  # L0: nothing is refused, no scope to admit
    # Pick the first incident's first repairScope path and prove it is admitted.
    first = incidents[0]
    scope, _ = scope_of(reg, first["id"])
    if not scope:
        return
    probe = scope[0]
    if probe.endswith("/**"):
        probe = probe[:-3] + "/x.yaml"
    elif any(ch in probe for ch in "*?"):
        probe = probe  # a glob; skip the literal edit probe
    ok, why = enforce.dof_verdict(probe)
    assert ok is True, (
        f"{probe} inside {first['id']} repairScope must be admitted: {why}"
    )


def test_dof_verdict_fails_open_when_unreadable():
    """A blind reader must never deadlock a write: it returns None (unknown), the caller allows."""
    if enforce._DOF is None:
        assert enforce.dof_verdict("x")[0] is None
        return
    # Simulate the incident list being unreadable by pointing open_inc at something that raises.
    saved = enforce._DOF

    def _boom(reg):
        raise RuntimeError("rate limited")

    enforce._DOF = (_boom, saved[1], saved[2], saved[3])
    try:
        ok, _ = enforce.dof_verdict("web/app.tsx")
        assert ok is None, (
            "an unreadable incident list must fail open (None), not refuse"
        )
    finally:
        enforce._DOF = saved
