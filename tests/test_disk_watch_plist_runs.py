"""The disk watcher's plist must name a binary launchd can exec.

Measured 2026-11-10: the installed agent sat in launchd's xpcproxy state with `runs = 1` and a
heartbeat 1671s old against a 180s max. The job was loaded and dead at the same time, so
estate_health read `disk-guardian FAIL` for hours while nothing was wrong with the disk or the
script. The template named `/bin/sh` as ProgramArguments[0] with the script as a bare second
argument; naming the script itself (it has a `#!/bin/sh` shebang and is executable) removed the
extra launcher and the tick resumed on three consecutive 60s intervals.

A gate that cannot fail is not a gate (AGENTS.md section 9, R1/R2), so these tests pin both
directions: the current template passes, and the shape that broke it is rejected.
"""

from __future__ import annotations

import pathlib
import plistlib

REPO = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "launchd" / "ai.estate.disk-watch.plist.tmpl"


def render(text: str) -> str:
    """The template is not valid XML until ${HOME} is substituted."""
    return text.replace("${HOME}", "/Users/someone")


def program_arguments(text: str) -> list[str]:
    return plistlib.loads(render(text).encode())["ProgramArguments"]


class TestTheTemplateRuns:
    def test_it_parses_as_a_plist(self) -> None:
        assert plistlib.loads(render(TEMPLATE.read_text()).encode())["Label"] == (
            "ai.estate.disk-watch"
        )

    def test_the_program_is_the_watcher_itself(self) -> None:
        args = program_arguments(TEMPLATE.read_text())
        assert args == ["/Users/someone/.estate/bin/idp-disk-watch"], args

    def test_the_named_program_exists_and_is_executable(self) -> None:
        # The template names $HOME/.estate/bin/idp-disk-watch; the repo copy is bin/idp-disk-watch.
        script = REPO / "bin" / "idp-disk-watch"
        assert script.is_file(), f"the plist names a program the repo does not carry: {script}"
        assert script.stat().st_mode & 0o111, f"{script} is not executable"

    def test_the_script_carries_a_shebang(self) -> None:
        # A direct ProgramArguments[0] is only valid because the kernel can find an interpreter.
        first = (REPO / "bin" / "idp-disk-watch").read_text().splitlines()[0]
        assert first.startswith("#!"), first

    def test_the_interval_is_a_tick_not_a_park(self) -> None:
        assert plistlib.loads(render(TEMPLATE.read_text()).encode())["StartInterval"] == 60


class TestItStillRejectsTheBrokenShape:
    """The falsifier: the shape that was load-bearing-dead must fail these tests."""

    BROKEN = TEMPLATE.read_text()

    def test_a_shell_wrapper_is_rejected(self) -> None:
        broken = self.BROKEN.replace(
            "    <string>${HOME}/.estate/bin/idp-disk-watch</string>",
            "    <string>/bin/sh</string>\n"
            "    <string>${HOME}/.estate/bin/idp-disk-watch</string>",
        )
        assert broken != self.BROKEN, "the falsifier no longer matches the template"
        assert program_arguments(broken) != [
            "/Users/someone/.estate/bin/idp-disk-watch"
        ], "a /bin/sh wrapper must not satisfy the test"

    def test_naming_python3_for_a_shell_script_is_rejected(self) -> None:
        # critical-watch names python3 because it reads the repo under TCC; THIS script is shell,
        # and python3 would parse bash (`SyntaxError: unmatched ')'`). Copying that idiom here
        # must fail.
        broken = self.BROKEN.replace(
            "    <string>${HOME}/.estate/bin/idp-disk-watch</string>",
            "    <string>/Library/Frameworks/Python.framework/Versions/3.12/bin/python3</string>\n"
            "    <string>-c</string>\n"
            "    <string>import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))</string>\n"
            "    <string>${HOME}/.estate/bin/idp-disk-watch</string>",
        )
        assert broken != self.BROKEN, "the falsifier no longer matches the template"
        assert program_arguments(broken) != [
            "/Users/someone/.estate/bin/idp-disk-watch"
        ], "a python3 wrapper must not satisfy the test"
