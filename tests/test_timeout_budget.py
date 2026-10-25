"""bin/timeout-budget has to refuse a second bound, or it is a paragraph with an exit code.

2026-10-25. The estate had three numbers bounding the same work: the executor's ceiling (100s), the
door script's per-step default (120s, so it could never fire), and whatever `timeout N` a step's
author wrote into a shell string. Measured that turn: lane-submit's push took 98s behind `timeout 80`
and the step reported the lane absent while the push was landing -- a false failure invented by a
guess. Two versions of that guess had already been tried (50s, then 80s).

These tests grade the gate the way the gate grades a bound: by running it against a tree it must
refuse, not by reading its prose.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin/timeout-budget"
INTENTS = ROOT / "platform/estate/intents"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - a fixed argv, no shell
        [sys.executable, str(GATE), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or ROOT),
    )


def _copy_intents(tmp_path: Path) -> Path:
    """A checkout shaped like this one, with the real library copied in: the test must grade a
    realistic tree, not an empty one, or 'no findings' would just mean 'no intents'."""
    (tmp_path / "mcp/plugins").mkdir(parents=True)
    shutil.copy(
        ROOT / "mcp/plugins/estate_executor.py",
        tmp_path / "mcp/plugins/estate_executor.py",
    )
    shutil.copytree(INTENTS, tmp_path / "platform/estate/intents")
    (tmp_path / "bin").mkdir()
    return tmp_path


def test_the_library_as_it_stands_is_clean():
    """No intent may declare time no door grants, no step may ask for more than its budget, and no
    command may carry a bound of its own. This is the state the eradication left the tree in; a
    finding here means it came back."""
    result = _run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken budget(s)" in result.stdout
    assert "0 new inner bound(s)" in result.stdout


def test_a_step_bound_wider_than_the_budget_is_refused(tmp_path):
    """The `timeout 80` inside a 100s step defect, at the step level: a cap wider than the budget
    can never fire, so the door always wins and the reader is told a number that means nothing."""
    root = _copy_intents(tmp_path)
    intent = root / "platform/estate/intents/too-wide.yaml"
    intent.write_text(
        "name: too-wide\ndoor_s: 20\nsteps:\n  - name: work\n    timeout: 600\n    cmd: echo hi\n"
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert (
        "too-wide.yaml" in result.stdout and "600s inside a 20s budget" in result.stdout
    )


def test_a_door_larger_than_the_ceiling_is_refused(tmp_path):
    """`door_s: 170` was shipped in lane-submit and tested against by a test that read the number
    back: the declaration was a fiction, because the executor kills at CEILING_SEC whatever the
    file says."""
    root = _copy_intents(tmp_path)
    (root / "platform/estate/intents/too-big-door.yaml").write_text(
        "name: too-big-door\ndoor_s: 600\nsteps:\n  - name: work\n    cmd: echo hi\n"
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert "time no door grants" in result.stdout


def test_steps_summing_past_one_door_are_refused(tmp_path):
    """One invocation runs every step inside one door: 2320s of steps inside a 100s door is the
    2026-10-12 defect, and it is a sum, not any single step."""
    root = _copy_intents(tmp_path)
    (root / "platform/estate/intents/sums-past.yaml").write_text(
        "name: sums-past\ndoor_s: 100\nsteps:\n"
        "  - name: a\n    timeout: 80\n    cmd: echo a\n"
        "  - name: b\n    timeout: 80\n    cmd: echo b\n"
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert "steps total 160s inside a 100s budget" in result.stdout


def test_a_literal_bound_inside_a_step_command_is_refused(tmp_path):
    """The original defect: a wall-clock guess written into the command itself."""
    root = _copy_intents(tmp_path)
    (root / "platform/estate/intents/inner-bound.yaml").write_text(
        "name: inner-bound\ndoor_s: 100\nsteps:\n"
        "  - name: push\n    cmd: |\n      timeout 80 git push -q origin HEAD\n"
    )
    result = _run("--root", str(root))
    assert result.returncode == 1
    assert "literal wall-clock bound inside a step" in result.stdout


def test_a_marked_probe_bound_is_allowed_and_must_carry_a_reason(tmp_path):
    """A probe may be bounded shorter than the work it guards, because a hung probe has to fail
    instead of hanging the step. The marker has to name why, or it is a rubber stamp."""
    root = _copy_intents(tmp_path)
    good = root / "platform/estate/intents/probe.yaml"
    good.write_text(
        "name: probe\ndoor_s: 100\nsteps:\n"
        "  - name: probe\n    cmd: |\n"
        "      timeout 2 curl -sf http://localhost/health  "
        "# estate:bound the service must fail fast, not hang the step\n"
    )
    assert _run("--root", str(root)).returncode == 0

    good.write_text(
        "name: probe\ndoor_s: 100\nsteps:\n"
        "  - name: probe\n    cmd: |\n      timeout 2 curl -sf http://localhost/health  # estate:bound\n"
    )
    result = _run("--root", str(root))
    assert result.returncode == 1, "a marker with no reason was accepted"


def test_the_ratchet_refuses_a_bound_that_was_not_in_the_baseline(tmp_path):
    """Shipping mode: everything already in bin/ is recorded, and one NEW literal bound fails.
    Without this the gate would either fail on history it did not cause, or allow anything."""
    root = _copy_intents(tmp_path)
    (root / "bin/mystery-script").write_text(
        "#!/bin/sh\ntimeout 45 curl -sf http://localhost/x\n"
    )
    first = _run("--root", str(root))
    assert first.returncode == 1, (
        "a new bound in bin/ was accepted with no baseline entry"
    )
    assert "new inner bound" in first.stdout

    assert _run("--root", str(root), "--write-baseline").returncode == 0
    assert _run("--root", str(root)).returncode == 0

    # a second, identical bound is a SECOND bound: the baseline counts, it does not whitelist a file
    (root / "bin/mystery-script").write_text(
        "#!/bin/sh\ntimeout 45 curl -sf http://localhost/x\ntimeout 45 curl -sf http://localhost/y\n"
    )
    again = _run("--root", str(root))
    assert again.returncode == 1, (
        "a second identical bound slipped past on the first one's baseline"
    )
    assert "1 new inner bound" in again.stdout


def test_strict_ratchet_fails_while_a_baseline_remains(tmp_path):
    """The end state: the baseline is empty and the gate is strict. This flag is how an operator sees
    how much of the estate is still carrying a bound of its own -- so it must fail while a bound is
    ratcheted, and pass only once nothing outside the door survives."""
    root = _copy_intents(tmp_path / "repo")
    (root / "bin").mkdir(exist_ok=True)
    (root / "bin/probe.sh").write_text(
        "#!/bin/sh\ntimeout 5 curl -sf http://localhost/x\n"
    )
    assert _run("--root", str(root), "--no-installed").returncode == 1
    assert (
        _run("--root", str(root), "--no-installed", "--write-baseline").returncode == 0
    )
    # ratcheted: reported, not failed
    assert _run("--root", str(root), "--no-installed").returncode == 0
    strict = _run("--root", str(root), "--no-installed", "--strict-ratchet")
    assert strict.returncode == 1, (
        "strict mode accepted a bound the baseline is still carrying"
    )


def test_the_estate_reaches_the_end_state_with_an_empty_ratchet():
    """The lane's finish line, and the assertion that would have been a lie when the gate was written:
    bin/ carried 12 inner bounds that day. Six were deleted (five above the ceiling in
    bin/estate-security-scan, one in bin/treewalk.py) and six marked as probes -- a bound on one HTTP
    exchange or one TCP connect, shorter than the work it sits inside by design."""
    result = _run("--strict-ratchet", "--no-installed")
    assert result.returncode == 0, result.stdout
    assert "0 ratcheted" in result.stdout


def test_the_installed_library_is_checked_too(tmp_path, monkeypatch):
    """The rule has to hold where an agent invokes, not only where a reviewer reads. runtime-sync
    stages main's intents into ~/.estate/intents and never deletes, so the invoked library is main's
    96 plus ~266 crystallized on this laptop: measured 2026-10-25 it carried 133 step caps, 57 of
    them at or above the ceiling. A checkout-only gate would have called that clean."""
    root = _copy_intents(tmp_path / "repo")
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "crystallized.yaml").write_text(
        "name: crystallized\ndoor_s: 100\nsteps:\n  - name: work\n    timeout: 300\n    cmd: echo hi\n"
    )
    monkeypatch.setenv("ESTATE_INTENTS", str(installed))
    result = _run("--root", str(root), "--installed")
    assert result.returncode == 1, "a bound in the invoked library was accepted"
    assert (
        "crystallized.yaml" in result.stdout
        and "300s inside a 100s budget" in result.stdout
    )

    # and the same tree without --installed stays hermetic, so a test never grades this laptop
    ok = _run("--root", str(root), "--no-installed")
    assert ok.returncode == 0, ok.stdout


def test_the_door_script_no_longer_defaults_a_step_to_a_literal():
    """`step.get("timeout", 120)` was the second opinion: it could never fire against a 100s door,
    so the bound that actually killed the job was invisible in the script's own story."""
    text = (ROOT / "platform/estate/bin/estate-execute").read_text()
    assert 'step.get("timeout", 120)' not in text
    assert 'step.get("timeout")' in text
    assert "from estate_executor import CEILING_SEC" in text, (
        "estate-execute must import the ceiling rather than restate it: a restated copy is the "
        "defect this lane exists to remove"
    )


def test_every_intent_in_the_library_still_parses():
    """The eradication deleted 24 lines out of 17 files; a YAML that no longer loads would be a
    worse outcome than the bound it carried."""
    for path in sorted(INTENTS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        assert isinstance(doc, dict) and doc.get("steps"), (
            f"{path.name} no longer loads"
        )
