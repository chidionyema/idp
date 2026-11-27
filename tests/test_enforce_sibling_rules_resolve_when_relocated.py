"""The deployed write hook judges with the checkout's rules, not with what sits beside it.

Every harness runs the copy bin/estate-memory-install deploys to ~/.estate/memory/bin, and that
copy carries none of bin/dof-gate, bin/pin-open or platform/estate/governance. Measured
2026-11-27: the deployed hook loaded dof_gate=False, governance=False, pin-open=False while the
same file in a checkout loaded all three, so the DoF repair lock, the founder's freeze and
lockdown, and the pin all failed OPEN for every agent (class
hook-reads-sibling-absent-from-deployed-copy, idp#8660; claim-open was the first instance).

A relocated copy of the hook (the hook alone, as deployed) judges a path inside this checkout,
and each rule must report a decision, never "nothing to decide" for want of the rule.
`--optimus` prints how many of the three rules a relocated copy loses: 3 on main 0f9d86375.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import inspect
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "bin/estate-memory-enforce"
ABSENT = {
    "dof": "DoF registry unreadable: nothing to decide",
    "governance": "governance state unavailable: nothing to decide",
    "pin": "pin-open door absent: nothing to decide",
}


def load(path: Path, name: str):
    sys.path.insert(0, str(REPO / "platform/estate/memory"))
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_file_location(name, str(path), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def lost_when_relocated(source: str) -> list[str]:
    """The rules a copy of the hook, alone in a bin/ of its own, cannot read for a repo path."""
    with tempfile.TemporaryDirectory() as scratch:
        deployed = Path(scratch) / "deployed/bin/estate-memory-enforce"
        deployed.parent.mkdir(parents=True)
        deployed.write_text(source)
        hook = load(deployed, f"eme_relocated_{abs(hash(source))}")
        target = str(REPO / "README.md")
        verdicts = {
            "dof": hook.dof_verdict(target)[1],
            "governance": hook.governance_verdict(target, "")[1],
            # main's pin_verdict() took no path: it could only ever look beside itself.
            "pin": (
                hook.pin_verdict(target)
                if inspect.signature(hook.pin_verdict).parameters
                else hook.pin_verdict()
            )[1],
        }
        return sorted(k for k, why in verdicts.items() if why == ABSENT[k])


def test_the_deployed_copy_reads_every_rule_from_the_checkout():
    assert lost_when_relocated(HOOK.read_text()) == []


def test_falsifier_a_hook_that_reads_only_beside_itself_loses_all_three():
    source = HOOK.read_text()
    blind = source.replace("([root] if root else []) + ", "", 1)
    assert blind != source
    assert lost_when_relocated(blind) == ["dof", "governance", "pin"]


def test_the_relocated_copy_does_not_find_the_rules_beside_itself():
    # Otherwise the test above would pass for the wrong reason.
    with tempfile.TemporaryDirectory() as scratch:
        deployed = Path(scratch) / "deployed/bin/estate-memory-enforce"
        deployed.parent.mkdir(parents=True)
        shutil.copy(HOOK, deployed)
        hook = load(deployed, "eme_relocated_alone")
        assert hook._sibling("bin/dof-gate") is None
        assert hook._sibling("bin/pin-open") is None
        assert hook._sibling("platform/estate/governance") is None


if __name__ == "__main__" and "--optimus" in sys.argv:
    print(
        "optimus.hooks.enforce_rules_lost_when_relocated="
        f"{len(lost_when_relocated(HOOK.read_text()))}"
    )
