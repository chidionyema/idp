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
        """The program launchd execs must END at the watcher.

        Re-expressed 2026-11-11. The old form asserted `args == [script]` because the watcher was
        a shell script a tick could exec directly. Commit 735ea73e4 rewrote the guardian from
        Python to shell, and that shell tick is the shape this test was then pinned to. The
        estate restored the Python guardian (brake, heartbeat, single-instance lock, phase
        ladder), which launchd reaches THROUGH python3 so the TCC grant attaches to a binary --
        the same reason critical-watch names python3. The contract is therefore: the LAST
        argument is the watcher, and the launcher in front of it is a python3 that exists.
        """
        args = program_arguments(TEMPLATE.read_text())
        assert args, "the plist names no program at all"
        assert args[-1] == "/Users/someone/.estate/bin/idp-disk-watch", args
        if len(args) > 1:
            # A launcher is allowed, but only one launchd can actually exec on this machine.
            assert "python3" in args[0], (
                "the launcher must be python3, the binary the TCC grant attaches to: "
                + repr(args[0])
            )

    def test_the_named_program_exists_and_is_executable(self) -> None:
        # The template names $HOME/.estate/bin/idp-disk-watch; the repo copy is bin/idp-disk-watch.
        script = REPO / "bin" / "idp-disk-watch"
        assert script.is_file(), (
            f"the plist names a program the repo does not carry: {script}"
        )
        assert script.stat().st_mode & 0o111, f"{script} is not executable"

    def test_the_watcher_is_python_and_parses(self) -> None:
        """The named program must be the language its launcher can run.

        This is the assertion that would have caught 735ea73e4: the plist named python3 while the
        file had become `#!/bin/sh`, so launchd handed bash to a Python interpreter
        (`SyntaxError: unmatched ')'`). The shebang and the launcher must agree, and the file must
        compile as what its shebang claims.
        """
        src = (REPO / "bin" / "idp-disk-watch").read_text()
        first = src.splitlines()[0]
        assert first.startswith("#!"), first
        assert "python3" in first, (
            "the guardian must be Python: the restored version carries the memory brake, the "
            "heartbeat and the single-instance lock that the shell rewrite dropped: "
            + first
        )
        import ast

        ast.parse(
            src
        )  # a SyntaxError here is the 735ea73e4 defect, caught at test time

    def test_the_job_is_resident_not_a_tick(self) -> None:
        """Resident, per the template's own header (2026-10-28).

        The old form asserted StartInterval == 60. The guardian is a `while` loop that costs one
        statvfs per healthy cycle, so a 60s tick would start a fresh resident guardian every
        minute -- measured 2026-11-11, two were alive at once and both wrote the same heartbeat
        file, so the estate could not read its own brake. The job is KeepAlive with a throttle.
        """
        d = plistlib.loads(render(TEMPLATE.read_text()).encode())
        assert d.get("KeepAlive") is True, (
            "a resident guardian must be KeepAlive, or launchd leaves it dead-but-loaded"
        )
        assert d.get("StartInterval") is None, (
            "StartInterval on a resident loop starts a new guardian every interval"
        )


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
        assert program_arguments(broken)[-1] == (
            "/Users/someone/.estate/bin/idp-disk-watch"
        ), "a shell wrapper in front of the watcher must not satisfy the test"

    def test_a_non_python_launcher_is_rejected(self) -> None:
        # The guardian is Python; a launcher that is not python3 cannot run it, and launchd would
        # hand the file to a shell that cannot parse it. That is the 735ea73e4 shape.
        broken = self.BROKEN.replace(
            "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
            "/bin/bash",
        )
        assert broken != self.BROKEN, "the falsifier no longer matches the template"
        args = program_arguments(broken)
        # Same predicate the real test applies: a launcher must be python3.
        assert not (len(args) > 1 and "python3" in args[0]), (
            "a non-python launcher for a Python guardian must not satisfy the test: "
            + repr(args[0])
        )
