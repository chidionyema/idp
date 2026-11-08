"""Falsifiers for bin/idp-pr-risk-gate's blindness handling (idp#7801).

Why this test exists, in one paragraph. On 2026-11-09 a push printed:

    jev   idp-pr-risk-gate: no condition could be scored (layer unreachable); tier=high is advisory only
    jev   idp-pr-risk-gate: push allowed -- a blind check is not evidence of risk

The estate's one decision layer had returned tier=high, score=1.0, escalated=true with all six
conditions unanswered -- and the gate discarded that verdict and allowed the push. The scorer was
not broken. Its own docstring says an unanswered condition counts as LIKELY, never as cleared, and
it does exactly that. The gate was the thing that overruled it.

This is LAW 38 in its own teeth: "a gate that cannot fail is not a gate". A check that allows on
blindness cannot fail, so it is not a check. Four separate branches allowed on blindness -- no
output, config_error, scored==0, and the ordinary tier path -- and each is pinned here.

The tests drive the real script with a stubbed scorer, so they assert on exit codes (the thing a
caller branches on) rather than on the wording of a message.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "bin" / "idp-pr-risk-gate"
SCORER = REPO / "bin" / "idp-pr-risk"


def _load_scorer():
    """Import bin/idp-pr-risk as a module.

    It has no .py extension, so the loader is named explicitly. Nothing in it touches the
    network or the decision layer at import time, so this stays hermetic and fast.
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("idp_pr_risk_under_test", str(SCORER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _code_only(path: Path) -> str:
    """The script with comment lines removed.

    A property a comment can satisfy is a spelling check, not a property test. This defect was
    described in prose in the file's own header before it was fixed; a test that searched raw text
    would have matched the description of the bug and called it a fix.
    """
    return "\n".join(
        ln
        for ln in path.read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("#")
    )


# A verdict shaped exactly like the real one measured on 2026-11-09: every condition unanswered,
# escalated, tier high. This is what the scorer returns when the layer cannot be reached.
# It deliberately carries no `block_tier` and no `summary`, so the gate is also exercised against
# an older scorer that predates those fields.
BLIND_HIGH = json.dumps(
    {
        "tier": "high",
        "score": 1.0,
        "escalated": True,
        "config_error": None,
        "diff_error": None,
        "conditions": [
            {"name": "scope-creep", "probability": None},
            {"name": "credentials", "probability": None},
        ],
    }
)

CLEAN_LOW = json.dumps(
    {
        "tier": "low",
        "score": 0.1,
        "escalated": False,
        "config_error": None,
        "diff_error": None,
        "conditions": [{"name": "scope-creep", "probability": 0.05}],
    }
)

CONFIG_ERROR = json.dumps(
    {
        "tier": "low",
        "score": 0.0,
        "escalated": False,
        "config_error": "jev-pr-risk.yml missing",
        "diff_error": None,
        "conditions": [],
    }
)

BLOCK_TIER = json.dumps(
    {
        "tier": "critical",
        "block_tier": "critical",
        "score": 1.0,
        "escalated": False,
        "config_error": None,
        "diff_error": None,
        "summary": "scored",
        "conditions": [
            {
                "name": "credentials",
                "probability": 0.9,
                "contributed": True,
                "weight": 3.0,
                "when": "does it touch a credential",
            }
        ],
    }
)

# The scorer's own contract: an unanswered condition is escalated to LIKELY, never cleared.
# A scorer regression that lowered the tier must not re-open the fail-open, so `escalated`
# has to refuse on its own, whatever tier travelled with it.
ESCALATED_LOW = json.dumps(
    {
        "tier": "low",
        "score": 0.1,
        "escalated": True,
        "config_error": None,
        "diff_error": None,
        "conditions": [{"name": "scope-creep", "probability": None}],
    }
)

# ONE gate run per distinct scenario, shared by every test that asserts on it. Measured on this
# host (load average 97-116) each process spawn costs 0.3-1.3s of wall time for ~15ms of CPU,
# so running the gate once per assertion made this file take 43s. The scenarios are independent
# (the scorer is stubbed) and each waits on process spawns rather than on CPU, so they are run
# CONCURRENTLY: eight sequential runs collapse into one wall-clock window.
#
# Each scenario is (stub stdout, stub exit code, extra env, gate args).
_SCENARIOS = {
    "blind": (BLIND_HIGH, 1, None, ()),
    "override": (BLIND_HIGH, 1, {"IDP_PR_RISK_GATE": "0"}, ()),
    "advise": (BLIND_HIGH, 1, None, ("--advise",)),
    "clean_low": (CLEAN_LOW, 0, None, ()),
    "silent": (None, 0, None, ()),
    "unparseable": ("not json at all", 0, None, ()),
    "config_error": (CONFIG_ERROR, 0, None, ()),
    "block_tier": (BLOCK_TIER, 1, None, ()),
    "escalated_low": (ESCALATED_LOW, 1, None, ()),
}


# ONE stub for the whole session, driven by an environment variable, and the REAL gate reached
# through a symlink instead of a copy.
#
# WHY, measured on this host (2026-11-09): the FIRST exec of a freshly written executable costs
# ~2.8s; the second exec of the same file costs ~0.15s. macOS assesses a new binary on its first
# run. The previous version of this file wrote a fresh copy of the gate and a fresh stub for
# every scenario, so it paid that assessment 8 times: 43s for 10 assertions, of which ~22s was
# the assessment and nothing else. Symlinking the real gate writes no new executable, and one
# stub whose output is chosen by $STUB_OUT pays the assessment once per session.
_STUB = """#!/bin/sh
if [ -n "${STUB_OUT+x}" ]; then
\tprintf '%s\\n' "$STUB_OUT"
fi
exit "${STUB_EXIT:-0}"
"""


def _canonical_stub() -> Path:
    """The stub script, kept at ONE stable path so macOS assesses it once, ever.

    Measured on this host (2026-11-09): the first exec of a freshly written executable costs
    ~1.9s, the second exec of the same inode ~0.014s, and a byte-identical COPY costs ~1.4s
    again because the copy is a new inode. A HARDLINK is the same inode, so it costs ~0.017s.
    The stub is therefore written once, here, and hardlinked into each session's directory.
    """
    base = Path(tempfile.gettempdir()) / "idp-pr-risk-gate-fixture"
    base.mkdir(parents=True, exist_ok=True)
    canonical = base / "idp-pr-risk"
    want = _STUB.encode("utf-8")
    if not canonical.exists() or canonical.read_bytes() != want:
        staging = base / ("idp-pr-risk.%d.tmp" % os.getpid())
        staging.write_bytes(want)
        staging.chmod(0o755)
        os.replace(staging, canonical)  # atomic; a new inode, so it is assessed once
    else:
        canonical.chmod(0o755)
    return canonical


@pytest.fixture(scope="module")
def results():
    from concurrent.futures import ThreadPoolExecutor

    root = Path(tempfile.mkdtemp(prefix="idp-pr-risk-gate-"))
    (root / "bin").mkdir(parents=True, exist_ok=True)
    # A symlink, not a copy: the gate resolves its own repo root from $0, so it still finds the
    # stub as its sibling `bin/idp-pr-risk`, and no new executable is created to be assessed.
    (root / "bin" / "idp-pr-risk-gate").symlink_to(GATE)
    stub = root / "bin" / "idp-pr-risk"
    try:
        os.link(_canonical_stub(), stub)  # same inode -> no second macOS assessment
    except OSError:  # different filesystem, or a race
        shutil.copy2(_canonical_stub(), stub)
    stub.chmod(0o755)

    def _one(item):
        name, (stub_out, stub_exit, env_extra, args) = item
        env = {k: v for k, v in os.environ.items() if k != "IDP_PR_RISK_GATE"}
        env["STUB_EXIT"] = str(stub_exit)
        if stub_out is not None:
            env["STUB_OUT"] = stub_out
        env.update(env_extra or {})
        return name, subprocess.run(
            ["bash", str(root / "bin" / "idp-pr-risk-gate"), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    try:
        with ThreadPoolExecutor(max_workers=len(_SCENARIOS)) as pool:
            return dict(pool.map(_one, _SCENARIOS.items()))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_blind_high_verdict_is_refused(results):
    """The exact defect. tier=high with the layer blind must exit 1, not 0."""
    r = results["blind"]
    assert r.returncode == 1, (
        "a blind layer returned tier=high and the gate allowed the push; "
        f"exit was {r.returncode}, stderr={r.stderr!r}"
    )
    assert "REFUSED" in r.stderr


def test_the_refusal_names_why_it_could_not_answer(results):
    """A refusal an author cannot act on is a wall, not a gate."""
    r = results["blind"]
    low = r.stderr.lower()
    assert "could not answer" in low or "escalated" in low, (
        f"the refusal does not say the layer was blind: {r.stderr!r}"
    )


def test_the_refusal_names_the_override(results):
    """LAW 38's second edge: a fence a correct machine cannot satisfy is an outage.

    The fix cannot be 'refuse forever with no way out', so the way out is named in the refusal.
    """
    r = results["blind"]
    assert "IDP_PR_RISK_GATE=0" in r.stderr, (
        f"the refusal does not name the deliberate override: {r.stderr!r}"
    )


def test_the_override_still_allows_and_says_a_person_owns_it(results):
    r = results["override"]
    assert r.returncode == 0, f"the override did not let the push through: {r.stderr!r}"
    assert "person owns this push" in r.stdout + r.stderr


def test_advise_still_never_refuses(results):
    """--advise is what .githooks/pre-push calls; its documented meaning must not change."""
    r = results["advise"]
    assert r.returncode == 0, (
        f"--advise refused a push, breaking the hook's logger contract: {r.stderr!r}"
    )


def test_a_clean_low_verdict_is_allowed(results):
    """The falsifier's own falsifier: the gate must not refuse correct work."""
    r = results["clean_low"]
    assert r.returncode == 0, f"the gate refused a clean low-risk change: {r.stderr!r}"


def test_a_silent_scorer_is_refused(results):
    """No output at all means the change was never examined -- blind, not safe."""
    r = results["silent"]
    assert r.returncode == 1, (
        f"a scorer that produced nothing was treated as a pass; exit {r.returncode}, stderr={r.stderr!r}"
    )


def test_a_config_error_is_refused(results):
    """A gate that cannot read its own rules has not cleared the change."""
    r = results["config_error"]
    assert r.returncode == 1, (
        f"an unreadable rule file was treated as a pass; exit {r.returncode}, stderr={r.stderr!r}"
    )


def test_a_verdict_that_cannot_be_parsed_is_refused(results):
    """Malformed JSON is blind too: the scorer spoke, but nobody can read it."""
    r = results["unparseable"]
    assert r.returncode == 1, (
        f"an unparseable verdict was treated as a pass; exit {r.returncode}, stderr={r.stderr!r}"
    )


def test_the_block_tier_comes_from_the_scorer_not_the_gate(results):
    """The gate must not hardcode a threshold the scorer reads from the environment.

    JEV_PR_RISK_BLOCK_TIER lets the scorer move its block tier; a gate that hardcodes "high"
    would refuse at a tier the scorer considers safe, or allow at one it considers blocking.
    """
    r = results["block_tier"]
    assert r.returncode == 1, (
        f"the gate ignored the scorer's own block tier and allowed a blocking verdict; "
        f"exit {r.returncode}, stderr={r.stderr!r}"
    )


def test_escalated_alone_refuses_even_when_the_tier_were_low(results):
    """A scorer regression must not re-open the fail-open.

    The scorer escalates every condition it could not score to LIKELY and says so in the
    verdict. If the tier it printed were ever lower -- a regression in the scorer, a changed
    block tier -- the conditions still were not cleared, so the change still was not examined.
    `escalated` therefore has to refuse on its own, whatever tier travelled with it.
    """
    r = results["escalated_low"]
    assert r.returncode == 1, (
        f"an escalated verdict was allowed because the tier was low; "
        f"exit {r.returncode}, stderr={r.stderr!r}"
    )


def test_the_scorer_ships_the_contract_the_gate_reads():
    """The gate reads `block_tier` and `summary` out of the verdict.

    If the scorer stops shipping either one the gate loses its threshold and its summary
    SILENTLY: it falls back to "high" and to an empty message, and neither failure is loud.
    """
    scorer = _load_scorer()
    result = {
        "tier": "high",
        "base": "origin/main",
        "score": 1.0,
        "escalated": True,
        "config_error": None,
        "diff_error": None,
        "conditions": [
            {
                "name": "scope-creep",
                "probability": None,
                "weight": 2.0,
                "contributed": True,
                "when": "does it widen the change",
            }
        ],
    }
    payload = scorer._payload(result, "high")
    assert payload["block_tier"] == "high", (
        f"the verdict does not carry the block tier: {sorted(payload)}"
    )
    assert payload["summary"], "the verdict does not carry the scorer's own rendering"
    assert "idp-pr-risk" in payload["summary"], (
        f"the summary is not the scorer's rendering: {payload['summary']!r}"
    )
    # The summary must be the SAME rendering the human path prints, not a second formatter.
    err_lines, out_lines = scorer._render(result)
    assert payload["summary"].startswith("\n".join(err_lines + out_lines)), (
        f"the summary and the human rendering have drifted apart: {payload['summary']!r}"
    )


def test_no_allow_on_blindness_branch_survives():
    """The class, not the instance: the code must contain no exit 0 on a blindness path.

    Comments are stripped first. The pre-fix file explained this very defect in its header, so a
    raw-text search would match the description of the bug and report it as absent.
    """
    code = _code_only(GATE)
    for phrase in (
        "not refusing on a blind check",
        "push allowed -- a blind check is not evidence of risk",
        "tier=$tier is advisory only",
    ):
        assert phrase not in code, f"the allow-on-blindness branch is back: {phrase!r}"


def test_the_header_cites_law_38_for_the_right_thing():
    """The wrong citation is what produced the defect; it may not be left teaching it."""
    raw = GATE.read_text(encoding="utf-8")
    assert "a gate that cannot fail is not a gate" in raw, (
        "the header no longer states LAW 38 correctly"
    )
