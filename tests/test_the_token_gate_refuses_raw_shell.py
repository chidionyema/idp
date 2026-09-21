"""The token gate refuses raw shell and lets the wrapped form through.

Every case below runs the real classifier over a real command string and asserts the exit
code the hook would hand Claude Code (0 = allowed, 2 = refused). No case asserts on a
comment, a docstring, a file extension or a line prefix: the estate has been burned four
times in one day by guards that graded a proxy instead of the thing itself.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_HOOK = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "pre_bash_token_gate.py"
)
_spec = importlib.util.spec_from_file_location("pre_bash_token_gate", _HOOK)
assert _spec and _spec.loader
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


REPO = str(pathlib.Path(__file__).resolve().parents[1])


def verdict(command: str, **extra) -> int:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command, **extra},
        "cwd": extra.pop("cwd", REPO),
    }
    return gate.run(payload)


REFUSED = [
    "cat huge.log",
    "git log --oneline -100",
    "ls -la",
    "rg -n pattern .",
    "python3 -c 'print(1)'",
    "cd /Users/roseonyema/Documents/code/idp && git status",
    "echo hi | wc -l",
    "FOO=bar git status",
    "./bin/some-other-script",
    "kubectl get pods -n temporal",
]

ALLOWED = [
    "bin/idp-exec cat huge.log",
    "bin/idp-exec bash -lc 'git log | head -20'",
    "cd /Users/roseonyema/Documents/code/idp && bin/idp-exec git status",
    "/Users/roseonyema/Documents/code/idp/bin/idp-exec ls",
    "cd /tmp",
    "export FOO=bar",
    "cd /tmp && export FOO=bar",
]


@pytest.mark.parametrize("command", REFUSED)
def test_raw_shell_is_refused(command: str) -> None:
    assert verdict(command) == 2, f"gate let raw shell through: {command!r}"


@pytest.mark.parametrize("command", ALLOWED)
def test_wrapped_or_exempt_is_allowed(command: str) -> None:
    assert verdict(command) == 0, f"gate refused a compliant command: {command!r}"


def test_a_partially_wrapped_command_is_still_refused() -> None:
    """One wrapped segment does not launder the unwrapped one beside it."""
    assert verdict("bin/idp-exec git status && cat huge.log") == 2


def test_an_unreadable_command_is_refused_not_waved_through() -> None:
    """Unbalanced quotes mean the gate cannot read it, so it does not get to call it safe."""
    assert verdict("cat 'unterminated") == 2


def test_the_release_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IDP_TOKEN_GATE", "0")
    assert verdict("cat huge.log") == 0


def test_a_backgrounded_command_is_exempt() -> None:
    """idp-exec captures output; a detached command would never return through it."""
    assert verdict("sleep 600", run_in_background=True) == 0


def test_a_repo_without_the_wrapper_is_not_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    """LAW 38: a fence a correct machine cannot satisfy is an outage.

    A session working somewhere that ships no bin/idp-exec is not on this platform, and
    the gate refuses nothing there.
    """
    monkeypatch.setenv("IDP_ROOT", "/nonexistent-repo-path")
    assert verdict("cat huge.log") == 0


def test_the_wrapper_is_found_by_walking_up_from_a_subdirectory() -> None:
    """A session in idp/platform/llm is still on the platform."""
    assert gate._repo_with_wrapper(str(pathlib.Path(REPO) / "platform" / "llm")) == REPO


def test_a_path_outside_any_wrapper_repo_resolves_to_none() -> None:
    assert gate._repo_with_wrapper("/") is None


def test_a_non_bash_tool_is_not_this_gates_business() -> None:
    assert gate.run({"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}}) == 0


def test_the_refusal_hands_back_a_command_the_gate_then_allows() -> None:
    """A refusal is only worth printing if its own suggestion survives the gate.

    Graded as a round trip, not as wording: the raw form is refused, the form the
    refusal offers is allowed, and the offer really is the text the user reads.
    """
    raw = "cat huge.log"
    offered = gate._suggestion(raw)
    assert offered in gate._refusal(raw, REPO)
    assert verdict(raw) == 2
    assert verdict(offered) == 0


def test_the_suggestion_is_withheld_when_it_cannot_be_built() -> None:
    """A wrong rewrite would be copied, so none is offered."""
    assert gate._suggestion("grep 'foo bar' x") == ""
    assert gate._suggestion("cat x.log") == "bin/idp-exec cat x.log"
    assert gate._suggestion("cat x | wc -l") == "bin/idp-exec bash -lc 'cat x | wc -l'"
