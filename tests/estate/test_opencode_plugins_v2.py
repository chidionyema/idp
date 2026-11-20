"""The estate OpenCode guards must load in the harness that runs them (V2)."""
import json
import subprocess
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2] / "estate" / "plugins"


def test_each_plugin_is_a_v2_package():
    dirs = sorted(d for d in PLUGINS.iterdir() if d.is_dir())
    assert dirs, PLUGINS
    for d in dirs:
        pkg = json.loads((d / "package.json").read_text())
        assert pkg["exports"]["."] == "./index.ts", d.name
        assert (d / "index.ts").is_file(), d.name


def test_no_plugin_keeps_the_v1_hook_name():
    for src in sorted(PLUGINS.glob("*/index.ts")):
        text = src.read_text()
        assert "Plugin.define" in text, src
        assert "tool.execute.before" not in text, f"{src} is V1"


def test_the_guard_refuses_a_full_checkout():
    guard = PLUGINS.parents[1] / "bin" / "estate-zero-worktree"
    run = subprocess.run(
        [str(guard), "check", "--", "git worktree add /tmp/x"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 78, run.stdout + run.stderr
