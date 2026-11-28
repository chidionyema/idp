"""The Greenlane repairs the ruff rules ruff cannot fix, so a lane is never red for them.

Falsifiers: each repair must change what it should and leave alone what it must not. The end to
end test runs real git and the pinned Ruff through `format_fixes` and then grades the result with
the estate's own rule set, so a repair that would still leave the lane red fails here.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

from greenlane.ferrari import (
    FORMAT_REFUSAL,
    TRUSTED_RUFF_VERSION,
    format_fixes,
    source_assess,
)
from greenlane.pyfix import asserts_to_raises, repair, unused_loop_vars

RULES = ["--select", "E9,F,B,S", "--ignore", "S603,S607"]


def test_assert_with_message_becomes_a_raise():
    out = asserts_to_raises('def f(x):\n    assert x > 0, f"bad {x}"\n', "a.py")
    assert out == (
        'def f(x):\n    if not (x > 0):\n        raise AssertionError(f"bad {x}")\n'
    )


def test_bare_assert_and_multiline_assert():
    src = "def f(a, b):\n    assert a == b\n    assert (\n        a\n        and b\n    ), 'm'\n"
    out = asserts_to_raises(src, "a.py")
    ast.parse(out)
    assert "assert" not in out.replace("AssertionError", "")
    assert out.count("raise AssertionError") == 2


def test_tests_and_declared_files_keep_their_asserts():
    src = "def test_x():\n    assert 1\n"
    assert asserts_to_raises(src, "tests/test_a.py") == src
    assert asserts_to_raises(src, "pkg/test_a.py") == src
    assert asserts_to_raises(src, "pkg/a_test.py") == src
    declared = "# ruff: noqa: S101\ndef f():\n    assert 1\n"
    assert asserts_to_raises(declared, "pkg/a.py") == declared


def test_assert_sharing_a_line_is_left_alone_not_mangled():
    one_line = "def f(x):\n    if x: assert x\n"
    semi = "def f(x):\n    assert x; return x\n"
    assert asserts_to_raises(one_line, "a.py") == one_line
    assert asserts_to_raises(semi, "a.py") == semi


def test_unparsable_source_is_returned_unchanged():
    broken = "def f(:\n    assert 1\n"
    assert repair(broken, "a.py") == broken


def test_unused_loop_variable_is_renamed():
    out = unused_loop_vars("for i in range(3):\n    print('x')\n")
    assert out == "for _i in range(3):\n    print('x')\n"


def test_used_or_later_read_loop_variable_is_not_renamed():
    used = "for i in range(3):\n    print(i)\n"
    later = "for i in range(3):\n    pass\nprint(i)\n"
    assert unused_loop_vars(used) == used
    assert unused_loop_vars(later) == later


def test_repair_is_idempotent():
    src = "def f(x):\n    assert x, 'm'\n    for i in range(2):\n        pass\n"
    once = repair(src, "a.py")
    assert repair(once, "a.py") == once


def _ruff() -> str:
    for cand in (str(Path.home() / ".local/bin/ruff"), "ruff"):
        r = subprocess.run([cand, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() == f"ruff {TRUSTED_RUFF_VERSION}":
            return cand
    raise AssertionError("pinned ruff not installed; these tests never skip it")


def _lane(
    tmp_path: Path, files: dict[str, str], base_files: dict[str, str] | None = None
) -> tuple[str, str]:
    def git(*args):
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
            env={
                **os.environ,
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
            },
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "t")
    git("config", "user.email", "t@example.invalid")
    (tmp_path / "README.md").write_text("base\n")
    for name, text in (base_files or {}).items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    git("add", ".")
    git("commit", "-qm", "work")
    return base, git("rev-parse", "HEAD")


DIRTY = (
    "import json\n"
    "from typing import Optional\n\n\n"
    "def check(rows: list) -> int:\n"
    "    assert len(rows) == 2, 'need two rows'\n"
    "    for i in range(3):\n"
    "        pass\n"
    "    return len(rows)\n"
)


def test_a_lane_that_fails_the_standard_comes_back_passing_it(tmp_path):
    ruff = _ruff()
    base, head = _lane(tmp_path, {"pkg/a.py": DIRTY})
    before = subprocess.run(
        [ruff, "check", "--isolated", *RULES, "pkg/a.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert before.returncode == 1, "the fixture must fail the standard before the fix"
    fixes = format_fixes(base, head, checkout=tmp_path, ruff_binary=ruff)
    assert set(fixes) == {"pkg/a.py"}
    fixed = tmp_path / "fixed" / "pkg" / "a.py"
    fixed.parent.mkdir(parents=True)
    fixed.write_text(fixes["pkg/a.py"])
    for cmd in (
        [ruff, "check", "--isolated", *RULES, str(fixed)],
        [ruff, "format", "--isolated", "--check", str(fixed)],
    ):
        after = subprocess.run(cmd, capture_output=True, text=True)
        assert after.returncode == 0, after.stdout + after.stderr
    assert "raise AssertionError('need two rows')" in fixes["pkg/a.py"].replace(
        '"', "'"
    )


def test_a_test_file_with_asserts_is_not_rewritten(tmp_path):
    ruff = _ruff()
    src = "def test_x():\n    assert 1 == 1\n"
    base, head = _lane(tmp_path, {"tests/test_a.py": src})
    assert format_fixes(base, head, checkout=tmp_path, ruff_binary=ruff) == {}


def test_a_rebound_loop_variable_is_still_renamed():
    src = "def f():\n    for i in range(2):\n        pass\n    for i in range(3):\n        print(i)\n"
    out = unused_loop_vars(src)
    assert out.startswith("def f():\n    for _i in range(2):")
    assert "for i in range(3):" in out


def test_a_read_before_the_rebinding_blocks_the_rename():
    src = "def f():\n    for i in range(2):\n        pass\n    print(i)\n    for i in range(3):\n        pass\n"
    out = unused_loop_vars(src)
    assert "    for i in range(2):\n        pass\n    print(i)" in out
    assert "    for _i in range(3):" in out


def _no_language_gate(args, **kw):
    """The language gate is not under test here; real git and the pinned Ruff do everything else."""
    if len(args) > 1 and str(args[1]).endswith("language-gate"):
        return subprocess.CompletedProcess(args, 0, "", "")
    return subprocess.run(args, **kw)


FORMATTED_WITH_ASSERT = 'def f(x):\n    assert x, "m"\n    return x\n'


def _assess(tmp_path, files, base_files=None):
    base, head = _lane(tmp_path, files, base_files)
    return source_assess(
        base,
        head,
        "r",
        runner=_no_language_gate,
        checkout=tmp_path,
        ruff_binary=_ruff(),
    )


def test_a_formatted_new_file_with_an_assert_is_refused_for_repair_not_sent_to_ci(
    tmp_path,
):
    verdict = _assess(tmp_path, {"pkg/a.py": FORMATTED_WITH_ASSERT})
    assert verdict.state == "REFUSE"
    assert verdict.reason.startswith(
        FORMAT_REFUSAL
    )  # the engine's repair hook keys on this
    assert "machine-repairable" in verdict.reason, (
        "must not pass as a plain format failure"
    )
    assert "pkg/a.py" in verdict.reason


def test_a_clean_new_file_is_admitted(tmp_path):
    clean = "def f(x):\n    return x\n"
    assert _assess(tmp_path, {"pkg/a.py": clean}).state == "ADMIT"


def test_a_new_test_file_with_asserts_is_admitted(tmp_path):
    src = "def test_x():\n    assert 1 == 1\n"
    assert _assess(tmp_path, {"tests/test_a.py": src}).state == "ADMIT"


def test_an_existing_file_is_never_rewritten_or_refused_for_old_asserts(tmp_path):
    old = FORMATTED_WITH_ASSERT
    new = FORMATTED_WITH_ASSERT + "\n\ndef g():\n    return 1\n"
    verdict = _assess(tmp_path, {"pkg/a.py": new}, base_files={"pkg/a.py": old})
    assert verdict.state == "ADMIT"
