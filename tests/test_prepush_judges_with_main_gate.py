"""FULL SHIFT-LEFT: the pre-push hook judges with origin/main's gate, never a stale copy.

Class (2026-11-25, idp#8543/#8494): a lane pushed from a stale checkout passed the hook's
pre-obligation claim-gate copy at 13:27Z and died in CI 26s later on the obligation rule that
had merged at 13:10Z. CI always runs main's gate; the hook must too. Known-bad these
falsifiers reject: a hook that executes the CHECKOUT's bin/claim-gate as its primary judge
(the regression that produced the class), and a hook whose main-fetch path cannot produce an
executable gate.
"""

import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"


def _hook_source() -> str:
    subprocess.run(["bash", "-n", str(HOOK)], check=True)
    return HOOK.read_text()


def test_the_hook_fetches_main_gate_bytes_at_push_time():
    src = _hook_source()
    assert "git show origin/main:bin/claim-gate" in src, (
        "the hook no longer fetches origin/main's claim-gate; it would judge pushes with a "
        "stale checkout copy (the #8543 class: pass locally, die in CI on a rule main already "
        "had)"
    )


def test_the_primary_judge_is_the_main_bytes_not_the_checkout_copy():
    src = _hook_source()
    # the execution site must invoke the resolved $gate, never $root/bin/claim-gate directly
    exec_line = next(l for l in src.splitlines() if '"$gate" "$base" "$local_sha"' in l)
    assert "$root/bin/claim-gate" not in exec_line, (
        "the hook executes the checkout's claim-gate copy at the judge site; a stale clone "
        "would judge with yesterday's rules again"
    )


def test_the_checkout_copy_is_only_an_offline_fallback():
    src = _hook_source()
    # both fallback branches must print BLIND so nobody mistakes a stale judgment for a current one
    assert src.count("BLIND claim-gate") >= 3, (
        "the offline fallbacks lost their BLIND markers: a silent fallback judges with stale "
        "rules and reports it as ok"
    )
