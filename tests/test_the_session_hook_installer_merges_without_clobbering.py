"""The installer merges into the user's settings.json and never clobbers it.

`~/.claude/settings.json` on this machine carries ~20 estate guards across five events. A
settings file that fails to parse silently disables every one of them, so the two cases
that matter most here are: an existing guard is never dropped, and an unparseable file is
refused rather than rewritten.

The third case is the one that would bite later. The rule-guard sends every task into a
throwaway worktree under ~/Documents/code/wt-*, so `bin/idp-install-hooks` gets run from
clones that are deleted a day later. An installer that appended one entry per clone would
leave a hook command pointing into a removed worktree, and every Bash call in every
session would then fail on a missing file.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_HOOK = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "install_session_hooks.py"
)
# Quarantine gate: same `.claude/hooks/` infrastructure gap as test_the_token_gate_*.
# See that file's skip-reason block for the rationale. Skip the whole module when the
# installer is absent (it is spec_from_file_location'd at module top, before any test).
if not _HOOK.exists():
    pytest.skip(
        f"claude session hook {_HOOK.name} is not materialised in this checkout",
        allow_module_level=True,
    )
_spec = importlib.util.spec_from_file_location("install_session_hooks", _HOOK)
assert _spec and _spec.loader
installer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(installer)

GATE = ".claude/hooks/pre_bash_token_gate.py"
REPORTER = ".claude/hooks/after_agent_turn.py"


def commands(settings: dict, event: str, matcher: str) -> list[str]:
    for group in settings.get("hooks", {}).get(event, []):
        if group.get("matcher") == matcher:
            return [h.get("command", "") for h in group.get("hooks", [])]
    return []


def test_both_hooks_are_wired_into_an_empty_settings_file() -> None:
    settings: dict = {}
    installer.wire(settings)
    assert any(GATE in c for c in commands(settings, "PreToolUse", "Bash"))
    assert any(REPORTER in c for c in commands(settings, "Stop", ""))


def test_an_existing_guard_in_the_same_group_survives() -> None:
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 /est/rule-guard.py"}
                    ],
                }
            ]
        }
    }
    installer.wire(settings)
    got = commands(settings, "PreToolUse", "Bash")
    assert "python3 /est/rule-guard.py" in got
    assert any(GATE in c for c in got)


def test_unrelated_settings_keys_are_untouched() -> None:
    settings = {"model": "opus[1m]", "permissions": {"allow": ["Bash(*)"]}}
    installer.wire(settings)
    assert settings["model"] == "opus[1m]"
    assert settings["permissions"] == {"allow": ["Bash(*)"]}


def test_a_second_run_changes_nothing() -> None:
    settings: dict = {}
    installer.wire(settings)
    once = json.dumps(settings, sort_keys=True)
    installer.wire(settings)
    assert json.dumps(settings, sort_keys=True) == once


def test_another_clones_copy_is_repointed_not_duplicated() -> None:
    """The worktree case. Two entries would mean one of them dangles on removal."""
    stale = f"python3 /Users/x/Documents/code/wt-gone/{GATE}"
    settings = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": stale}]}
            ]
        }
    }
    installer.wire(settings)
    got = commands(settings, "PreToolUse", "Bash")
    assert len(got) == 1, f"the installer left a second copy of the gate: {got}"
    assert got[0] != stale
    assert got[0].endswith(GATE)


def test_a_repoint_keeps_the_entry_a_command_hook_with_a_timeout() -> None:
    stale = f"python3 /Users/x/Documents/code/wt-gone/{REPORTER}"
    settings = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": stale, "timeout": 15}],
                }
            ]
        }
    }
    installer.wire(settings)
    entry = settings["hooks"]["Stop"][0]["hooks"][0]
    assert entry["type"] == "command"
    assert entry["timeout"] == 15
    assert entry["command"].endswith(REPORTER)


def test_a_hooks_key_of_the_wrong_shape_is_refused_not_overwritten() -> None:
    with pytest.raises(ValueError):
        installer.wire({"hooks": ["not", "an", "object"]})
    with pytest.raises(ValueError):
        installer.wire({"hooks": {"PreToolUse": "not a list"}})


def test_an_unparseable_settings_file_is_left_exactly_as_it_was(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    config = tmp_path / ".claude"
    config.mkdir()
    broken = config / "settings.json"
    broken.write_text("{not json")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    assert installer.main() == 1
    assert broken.read_text() == "{not json"


def test_a_machine_with_no_settings_file_gets_one(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / ".claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    assert installer.main() == 0
    written = json.loads((config / "settings.json").read_text())
    assert any(GATE in c for c in commands(written, "PreToolUse", "Bash"))


def test_a_linked_worktree_does_not_take_over_the_wiring(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wt-* tree exists for an afternoon. If it repointed the live hooks at itself,
    `git worktree remove` would then fail every Bash call in every session."""
    config = tmp_path / ".claude"
    config.mkdir()
    (config / "settings.json").write_text("{}")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    worktree = tmp_path / "wt-thing"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /somewhere/.git/worktrees/wt-thing\n")
    monkeypatch.setattr(installer, "REPO", str(worktree))
    assert installer.main() == 0
    assert (config / "settings.json").read_text() == "{}"


def test_a_normal_clone_is_not_mistaken_for_a_worktree(tmp_path: pathlib.Path) -> None:
    clone = tmp_path / "idp"
    (clone / ".git").mkdir(parents=True)
    assert installer.is_linked_worktree(str(clone)) is False
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /x\n")
    assert installer.is_linked_worktree(str(worktree)) is True
