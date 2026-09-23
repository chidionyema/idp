"""Incident, idp#1390 (2026-09-04): the tag bump carrying the image that makes otto-golden
answer with a real model was refused by operating-model-gate rule `control_shipped` -- the
third time a gate has landed after `bin/idp-image-update-pr` and turned every controller push
red for a body a robot wrote (idp#1046 was `Verify:`, crew#584/idp#719 was `Optimised:`).

The script now composes a `Control: none:` line on the create path and backfills it onto a
body that predates the rule, exactly as it already does for the other two. This test is the
guard: it runs the script against a stub GitHub, so the backfill cannot quietly
stop happening.
Rung 2: runs a script from this repository against a local stub; opens no socket.
"""

import os
import pathlib
import subprocess

SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-image-update-pr"
)
SCRIPT = SCRIPT_PATH.read_text()

#: policy/operating_model.rego refuses a `Control: none:` whose reason is shorter than this.
_MIN_REASON_CHARS = 20


def _constant(name: str) -> str:
    for line in SCRIPT.splitlines():
        if line.startswith(f'{name}="'):
            return line.split('="', 1)[1].rstrip('"')
    raise AssertionError(f"{name} is not defined in bin/idp-image-update-pr")


def test_the_script_composes_a_control_line() -> None:
    assert _constant("CONTROL").startswith("Control: none:")


def test_the_reason_clears_the_bar_the_rego_sets() -> None:
    reason = _constant("CONTROL").split("Control: none:", 1)[1].strip()
    assert len(reason) >= _MIN_REASON_CHARS, reason


def test_every_required_line_is_on_the_create_path() -> None:
    create = SCRIPT.split("gh pr create", 1)[1].split("\nfi", 1)[0]
    for name in ("VERIFY", "OPTIMISED", "CONTROL"):
        assert f'"${name}"' in create, name


_STUB_GH = """#!/usr/bin/env bash
# A stand-in for the GitHub CLI: answers the four calls the refresh path makes
# and records every body it is asked to write. It never reaches the network.
set -euo pipefail
here="$STUB_HOME"
case "$*" in
  "pr list"*) echo 42 ;;
  "pr edit"*)
    while [ $# -gt 0 ]; do
      if [ "$1" = --body ]; then printf '%s\\n---EDIT---\\n' "$2" >> "$here/edits.txt"; fi
      shift
    done ;;
  *"--json body"*) cat "$here/body.txt" ;;
  *"--json mergeable"*) echo MERGEABLE ;;
  *) echo "unexpected gh call: $*" >&2; exit 3 ;;
esac
"""


def _run_refresh(tmp_path: pathlib.Path, body: str) -> list[str]:
    """Run the script against a stub GitHub; return the bodies it wrote.

    The script is exercised, not read. The stub reports MERGEABLE so no git
    branch is touched, and the copy of the script sits alone in a directory
    with no ``idp-pr-arm`` beside it, so the arming step says so and exits 0.
    """
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    (tmp_path / "body.txt").write_text(body)
    gh = stub_dir / "gh"
    gh.write_text(_STUB_GH)
    gh.chmod(0o755)

    script = tmp_path / "bin" / "idp-image-update-pr"
    script.parent.mkdir()
    script.write_bytes(SCRIPT_PATH.read_bytes())
    script.chmod(0o755)

    env = dict(
        os.environ,
        PATH=f"{stub_dir}:{os.environ['PATH']}",
        STUB_HOME=str(tmp_path),
    )
    done = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [str(script)], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout + done.stderr
    edits = tmp_path / "edits.txt"
    if not edits.exists():
        return []
    return [b for b in edits.read_text().split("---EDIT---\n") if b.strip()]


def test_a_body_that_predates_the_rule_gains_the_control_line(tmp_path) -> None:
    """The create path alone would never fix an open pull request: the robot
    pushes to the same branch for days and the body it was opened with stands.
    """
    edits = _run_refresh(
        tmp_path,
        "the controller wrote a newTag line\n\n"
        "Verify: `grep -rn imagepolicy platform/`\n"
        "Optimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n",
    )
    assert len(edits) == 1, edits
    assert "Control: none:" in edits[0]
    reason = edits[0].split("Control: none:", 1)[1].strip()
    assert len(reason) >= _MIN_REASON_CHARS, reason


def test_a_body_that_already_names_a_control_is_left_alone(tmp_path) -> None:
    edits = _run_refresh(
        tmp_path,
        "the controller wrote a newTag line\n\n"
        "Verify: `grep -rn imagepolicy platform/`\n"
        "Optimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n"
        "Control: tests/test_incident_catalogue_image_never_repulled.py\n",
    )
    assert edits == []
