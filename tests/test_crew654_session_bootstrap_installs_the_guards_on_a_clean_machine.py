"""crew#654 / crew#300: a session on a machine with no ~/.claude gets the guards from git before it works.

Pins: the repo hook names the script; the script installs the guards into an empty HOME from a local
estate clone; a present checkout is left untouched (a peer's branch is never moved).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-session-bootstrap"
LIVE = Path.home() / ".claude"


def test_repo_hook_names_the_script():
    hooks = json.loads((ROOT / ".claude" / "settings.json").read_text())["hooks"]
    cmds = [h["command"] for g in hooks["SessionStart"] for h in g["hooks"]]
    assert any("bin/idp-session-bootstrap" in c for c in cmds)


@pytest.mark.skipif(
    not (LIVE / ".git").exists(), reason="no local claude-estate checkout to clone from"
)
def test_empty_home_gets_the_guards(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), ESTATE_REPO=str(LIVE))
    r = subprocess.run(
        [str(SCRIPT), "--check"], env=env, capture_output=True, text=True
    )
    assert r.returncode == 1
    r = subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (home / ".claude" / "scripts" / "hook-run.py").is_file()
    assert (home / ".claude" / "scripts" / "feed-guard.py").is_file()


def test_present_checkout_is_left_alone(tmp_path):
    home = tmp_path / "home"
    (home / ".claude" / "scripts").mkdir(parents=True)
    marker = home / ".claude" / "scripts" / "hook-run.py"
    marker.write_text("# local edit\n")
    env = dict(os.environ, HOME=str(home), ESTATE_REPO="file:///nonexistent")
    r = subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    assert marker.read_text() == "# local edit\n"
