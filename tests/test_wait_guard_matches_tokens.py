"""The wait guard refuses a wait SHAPE, never a word that happens to appear in the command.

WHY THIS TEST EXISTS (measured 2026-10-24). `_NEVER` held the bare pattern `\\bwatch\\b`, which
`re.search` applies to the WHOLE command string. The door therefore refused six correct commands in
one session: `rg -c . ~/.estate/disk-watch.out.log`, `launchctl list | rg disk-watch`, and a
`git commit -m` whose message said the founder "cannot watch it deciding" -- refused twice, while
the agent was landing the commit that put the door's own decisions on /fleet. The agent's only
learnable response to that is to reword, which is not the work (R38), and the retries are invisible
to the founder except as slowness.

The same pass found the matching gap on the other side: `^\\s*sleep` anchored only to the start, so
`echo start; sleep 900` slipped through and was SIGTERMed at the 100s ceiling (job
exec-1792820291-8) instead of being refused -- the doctrine held for `sleep 1` and not for
`; sleep 900`. Both directions are asserted here: what must be allowed, and what must still be
refused. A guard only tested in the refusing direction cannot tell you it is not refusing everything.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "mcp" / "plugins" / "estate_executor.py"


@pytest.fixture(name="door")
def _door():
    spec = importlib.util.spec_from_file_location("estate_executor_guard", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _refused(door, command: str) -> bool:
    return (
        any(pattern.search(door.unquoted(command)) for pattern in door._NEVER)
        or door.parking_sleep(command) is not None
    )


# --- what must be ALLOWED ----------------------------------------------------------------
ALLOWED = [
    # The two that were refused six times between them.
    "rg -c . ~/.estate/disk-watch.out.log",
    "launchctl list | rg disk-watch",
    # Prose in a commit message is not a command.
    'git -m "the founder cannot watch it deciding"',
    # Ordinary work that mentions the letter sequence.
    "ls ~/Library/LaunchAgents",
    "bin/idp-greenlane status",
    "rg -n 'watch' mcp/plugins/estate_executor.py",
    # A commit message that QUOTES a wait is data about waits, not a parked job: this guard's own
    # fix commit was refused by the guard it was fixing.
    'git commit -m "door: echo start; sleep 900 was not refused; tail -f too"',
    # A heredoc body is stdin, not the command: this is how a commit message is written.
    "git commit -F - <<MSG\ndocs: echo start; sleep 900 was refused; tail -f too\nMSG",
    # A single bounded sleep inside a real command is still bounded by the ceiling.
    "curl -sf --max-time 5 http://127.0.0.1:8091/health",
    # Pacing a restart is work, not parking: the door refused this while reloading itself.
    "launchctl kickstart -k gui/501/ai.estate.executor; sleep 2; launchctl print gui/501/x",
    "sleep 5",
    # MEASURED 2026-10-24: 26 refusals in 17 minutes, every one a launch-then-check paced by a
    # sleep under a minute (`nohup …; sleep 30`). That is the estate's own idiom and it is work;
    # the threshold is 60s so the idiom runs and a park is still caught.
    "nohup python3 /tmp/land_builders.py > /tmp/x.log 2>&1 & sleep 30; tail -n 3 /tmp/x.log",
]


# --- what must still be REFUSED ----------------------------------------------------------
REFUSED = [
    "watch -n 1 ls",
    "echo start; sleep 900",
    "sleep 90",
    "bash -c 'sleep 900'",
    "bash <<'EOF'\nsleep 900\nEOF",
    "bash -c 'watch --help'",
    "sh -c 'tail -f /tmp/x.log'",
    "echo start; sleep $DURATION",
    "gh run watch 12345",
    "tail -f /tmp/x.log",
    "true && watch df",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_a_word_is_not_a_wait(door, command):
    assert not _refused(door, command), f"false positive: {command}"


@pytest.mark.parametrize("command", REFUSED)
def test_a_wait_is_still_refused(door, command):
    assert _refused(door, command), f"guard let a parked command through: {command}"
