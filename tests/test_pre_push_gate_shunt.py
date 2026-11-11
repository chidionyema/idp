"""Falsifiers for the pre-push fast gate's load shunt.

MEASURED 2026-11-10: a lane push took 101 s and blew the executor's 100 s ceiling. The same 13
rwgate tests passed in 54 s run directly, and the machine's load average was 484 with 170 runnable
processes from other agents' work. So the rung is not slow -- the laptop is -- and no trimming of
the rung fixes a queue that long.

The fix hands the gate to CI when the laptop cannot carry it, and this file pins BOTH halves of
that decision, because only one of them is the feature:

  * a saturated machine shunts, so correct work can still be pushed (R14);
  * an unreadable machine measurement does NOT shunt, so the gate still runs rather than silently
    passing (R1). "Cannot judge" is not a licence to pass.
"""
import re
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
HOOK = IDP / ".githooks" / "pre-push"

# The decision, extracted verbatim from the hook so this test pins the shipped logic rather than a
# paraphrase of it. A Python reimplementation would be the second copy of a layer (section 6).
# The decision is read OUT OF THE SHIPPED HOOK, never paraphrased. An earlier draft of this file
# inlined the condition, so a mutation of the hook left the test green -- a falsifier that never
# reaches the mutated code is a paragraph, not a falsifier (measured 2026-11-10: the inlined
# version passed 7/7 against a deliberately fail-open hook).
_DECIDE = re.compile(r"^\s*if \[ -n .*?\n(?:.*?\n)*?\s*SHUNT=1\n\s*fi", re.M)


def decision_fragment() -> str:
    text = HOOK.read_text()
    m = _DECIDE.search(text)
    assert m, "the hook no longer contains the shunt decision, so this test grades nothing"
    return m.group(0)


def shunts(load, free):
    script = f'SHUNT=""; load="$1"; free="$2"; {decision_fragment()}; echo "${{SHUNT:-0}}"'
    out = subprocess.run(
        ["/bin/bash", "-c", script, "_", load, free],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip() == "1"


# ---- the machine that cannot carry the gate hands it over ----------------
def test_a_saturated_machine_hands_the_gate_to_ci():
    """load 484 is the measurement that blew the ceiling. Shunting keeps the lane pushable."""
    assert shunts("484", "50") is True


def test_a_nearly_full_disk_hands_the_gate_to_ci():
    """The second half of the thin-client law: under 10GB free, local work is what fails."""
    assert shunts("2", "4") is True


# ---- and every normal machine still runs the gate ------------------------
def test_a_quiet_machine_runs_the_gate():
    """The feature must not swallow the gate: a healthy laptop runs it as before."""
    assert shunts("2", "50") is False


def test_an_unreadable_load_does_not_shunt():
    """R1: 'cannot judge' is not 'pass'. Empty load means run the gate, not skip it."""
    assert shunts("", "50") is False


# ---- the hook's own text carries the decision and its reason ------------
def test_the_hook_hands_the_gate_over_instead_of_dropping_it():
    text = HOOK.read_text()
    assert "SHUNT=1" in text, "the hook has no shunt, so a saturated laptop still blocks every push"
    assert "handed to CI" in text, "the shunt is silent, so an agent cannot tell the gate did not run"
    # The reasoning must survive: a future agent must be able to see WHY this is not a fail-open.
    assert "Greenlane" in text, "the hand-off no longer names who proves the branch instead"


def test_the_shunt_thresholds_are_the_thin_client_thresholds():
    """One definition of 'this machine cannot take it', not two that can drift apart."""
    thin = (IDP / "platform" / "estate" / "governance" / "thin_client.py").read_text()
    assert "MIN_FREE_GB = 10.0" in thin
    assert "MAX_LOAD = 16.0" in thin
    hook = HOOK.read_text()
    assert re.search(r"-gt 16\b", hook), "the hook's load bound drifted from thin_client's 16"
    assert re.search(r"-lt 10\b", hook), "the hook's disk bound drifted from thin_client's 10GB"


def test_the_hook_still_parses_as_shell():
    out = subprocess.run(["/bin/bash", "-n", str(HOOK)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
