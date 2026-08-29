"""2026-08-29: main went red on the kyverno rung (run 33248103977) because bin/idp-kyverno-render
judged its verdict with `printf '%s\n' "$out" | grep -qE '^policy .* failed'` under
`set -o pipefail`. `grep -q` exits on the first match; printf, still writing the rest of the
report, takes SIGPIPE; pipefail hands the pipeline printf's 141 and `if` read a 52-fail render
as "ok". Whether it bites depends on how much output sits behind the first match, so the same
commit was green on the PR and red on main: silent green, the defect class.

idp#774 fixed that one judge with a here-string. This is the class fence (LAW 45): no script
under bin/ pipes into `grep -q`. `grep ... >/dev/null` reads all of its input, so the writer
never sees SIGPIPE and the exit status is grep's own.
"""

import re
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PIPED_GREP_Q = re.compile(r"\|\s*grep\s+-q")


def _shell_scripts():
    for p in sorted((IDP / "bin").iterdir()):
        if not p.is_file():
            continue
        try:
            first = p.open("rb").readline()
        except OSError:
            continue
        if b"sh" in first:
            yield p


def test_no_script_under_bin_pipes_into_grep_q():
    offenders = []
    for p in _shell_scripts():
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if PIPED_GREP_Q.search(line):
                offenders.append(f"{p.relative_to(IDP)}:{n}")
    assert not offenders, (
        "`| grep -q` under pipefail reads green on SIGPIPE; use `grep ... >/dev/null`: "
        + ", ".join(offenders)
    )


def test_the_fence_sees_the_shape_it_guards():
    assert PIPED_GREP_Q.search("printf '%s\\n' \"$out\" | grep -qE '^policy .* failed'")
    assert PIPED_GREP_Q.search('head -1 "$f" | grep -q bash || continue')
    assert not PIPED_GREP_Q.search(
        "printf '%s\\n' \"$out\" | grep -E 'failed' >/dev/null"
    )
    assert not PIPED_GREP_Q.search("grep -qE 'failed' <<<\"$out\"")
