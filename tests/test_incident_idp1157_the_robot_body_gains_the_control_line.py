"""Incident, idp#1157 (2026-09-02 ~21:47Z): the flux/image-updates pull request carrying the
storefront release (prospector main-108-3da7ac78) sat refused by operating-model-gate rule
`control_shipped` because the body bin/idp-image-update-pr writes carried no `Control:` line.
The rule landed on main 2026-08-31T04:00Z; the generator predates it and #1157 was opened after
the cutoff, so the grandfather clause did not spare it. A hand-added line unblocked the release
at 22:15Z; this is the root fix, the exact idp#719 / idp#1011 shape recorded one gate at a time
in test_incident_crew584_optimised_line_gate.py -- the gate-landed-after-branch class, entry 17.

Rung 2 (fail before merge). conftest on a fixture; opens no socket.
"""

import json
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"
SCRIPT = ROOT / "bin" / "idp-image-update-pr"

needs_conftest = pytest.mark.skipif(
    shutil.which("conftest") is None,
    reason="conftest not installed; ci.yml installs it",
)


def _rules(path: pathlib.Path) -> set[str]:
    out = subprocess.run(
        [
            "conftest",
            "test",
            "--parser",
            "json",
            "-p",
            str(POLICY),
            "-o",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {
        f["msg"].split(" | ")[0]
        for r in json.loads(out)
        for f in (r.get("failures") or [])
    }


def _generated_control_line() -> str:
    hits = [
        l
        for l in SCRIPT.read_text().splitlines()
        if l.startswith('CONTROL="Control: none:')
    ]
    assert len(hits) == 1, "the generator no longer writes exactly one Control line"
    return hits[0].split("=", 1)[1].strip('"')


@needs_conftest
def test_the_literal_line_the_generator_writes_passes_the_real_rule(tmp_path):
    """Graded on the #1027 incident fixture (touches clusters/ and platform/), both ways."""
    d = json.loads((FIX / "opmodel-no-control.json").read_text())
    d["pr"]["createdAt"] = (
        "2026-09-02T21:47:00Z"  # after the cutoff: the rule binds, as on #1157
    )
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(d))
    assert "rule=control_shipped" in _rules(bare)
    d["pr"]["body"] += "\n" + _generated_control_line() + "\n"
    lined = tmp_path / "lined.json"
    lined.write_text(json.dumps(d))
    assert "rule=control_shipped" not in _rules(lined), _generated_control_line()


def _fake_gh(tmp_path, body: str):
    """The crew584 harness: a `gh` that knows one open PR, records every `pr edit` body."""
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    (tmp_path / "body.txt").write_text(body)
    gh = b / "gh"
    gh.write_text(
        '#!/usr/bin/env bash\ncase "$1 $2" in\n'
        "  'pr list') echo 719;;\n"
        '  \'pr view\') case "$*" in *mergeable*) echo MERGEABLE;; *) cat "$BODY_FILE";; esac;;\n'
        '  \'pr edit\') shift 4; printf \'%s\' "$1" > "$EDIT_FILE"; printf \'%s\' "$1" > "$BODY_FILE";;\n'
        "  'pr merge') ;;\n"
        '  *) echo "unexpected gh $*" >&2; exit 9;;\nesac\n'
    )
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "BODY_FILE": str(tmp_path / "body.txt"),
        "EDIT_FILE": str(tmp_path / "edits.txt"),
        "MERGEABLE_WAIT": "0",
    }
    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True
    )


def test_an_existing_body_without_the_line_gains_it_on_the_next_push(tmp_path):
    """#1157's own shape: opened before the fix, carries Optimised and Verify, no Control."""
    verify = "Verify: `grep -rn imagepolicy platform/ clusters/ --include=*.yaml`"
    r = _fake_gh(
        tmp_path,
        "Written by image-automation-controller.\n\n"
        "Optimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n" + verify + "\n",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    edited = (tmp_path / "edits.txt").read_text()
    assert "\nControl: none: " in edited
    assert "body gained the Control line" in r.stderr


@needs_conftest
def test_the_backfilled_body_passes_the_real_rule(tmp_path):
    verify = "Verify: `grep -rn imagepolicy platform/ clusters/ --include=*.yaml`"
    r = _fake_gh(
        tmp_path,
        "Written by image-automation-controller.\n\n"
        "Optimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n" + verify + "\n",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((FIX / "opmodel-no-control.json").read_text())
    d["pr"]["createdAt"] = "2026-09-02T21:47:00Z"
    d["pr"]["body"] = (tmp_path / "edits.txt").read_text()
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    assert "rule=control_shipped" not in _rules(p)
