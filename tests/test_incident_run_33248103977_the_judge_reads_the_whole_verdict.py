"""Run 33248103977 (main, 2026-08-29 10:33Z): offline-gate said "the must-fail fixture passed; the
judge admits an unpatched chart". Reproduced locally: bin/idp-kyverno-render printed
`ok render signoz ... fail: 53` over a CLI verdict holding 52 `policy ... failed` lines.

Cause: `printf '%s\n' "$out" | grep -qE '^policy .* failed'` under `set -o pipefail`. grep -q exits
on the first match; on a render bigger than the pipe buffer printf then dies of SIGPIPE, the
pipeline's status is printf's, the `if` falls through, and the judge says ok. Every earlier green
was buffer luck (silent green, LAW 28). The verdict is read from a here-string now.
"""

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
JUDGE = ROOT / "bin" / "idp-kyverno-render"


def test_the_bug_shape_reads_ok_and_the_fix_reads_fail():
    # A verdict larger than any pipe buffer, with the failure at its very top.
    body = "policy x -> resource default/Pod/y failed:\n" + ("a" * 200 + "\n") * 20000
    script = r"""
set -euo pipefail
out=$(cat "$1")
if printf '%s\n' "$out" | grep -qE '^policy .* failed'; then echo PIPE=FAIL; else echo PIPE=ok; fi
if grep -qE 'policy .* -> resource .* failed' <<<"$out"; then echo HERE=FAIL; else echo HERE=ok; fi
"""
    p = pathlib.Path(__file__).parent / "_verdict.tmp"
    try:
        p.write_text(body)
        r = subprocess.run(
            ["bash", "-c", script, "-", str(p)],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        p.unlink(missing_ok=True)
    assert "HERE=FAIL" in r.stdout, r.stdout
    # The pipe form is not asserted either way: it depends on the kernel's pipe buffer, which is
    # the whole point. It is recorded so a reader sees both on one screen.


def test_a_glued_first_line_is_still_a_failure():
    line = "Mutation has been applied successfully.policy require-catalogue-entity -> resource observability/Service/s failed:"
    r = subprocess.run(
        ["grep", "-qE", "policy .* -> resource .* failed"], input=line, text=True
    )
    assert r.returncode == 0
