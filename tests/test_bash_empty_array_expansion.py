"""A bash array expanded under `set -u` must survive being empty.

macOS ships bash 3.2.57, where `"${arr[@]}"` on an empty array is a fatal
`arr[@]: unbound variable` rather than zero words. macOS is the platform every agent on this
estate runs on, and the scripts below all open with `set -euo pipefail` -- so an array that is
only sometimes filled turns into a door that works until the day its input is empty.

That is how estate-substrate went BLIND: `bin/idp-cloud` built `ns=()` and expanded it
immediately, so the object-head/ls path died with `line 203: ns[@]: unbound variable` whenever
OCI_OS_NAMESPACE was unset, which is the normal case. The critical entry then reported the
cluster-state receipt as unreadable while the cluster was fine.

The repo's own safe idiom already exists (bin/idp-agent-key:120):

    ${arr[@]+"${arr[@]}"}

It expands to nothing when the array is empty and to the quoted elements when it is not. This
test pins two things:

1. The idiom really behaves that way on THIS shell -- both directions, empty and filled. A test
   that only proved the empty case would pass on a form that also drops real arguments.
2. No script in the swept set goes back to the unguarded form. The sweep is the class, so a new
   copy of the bug fails here instead of in production.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BASH = "/bin/bash" if Path("/bin/bash").exists() else "bash"

# The files swept in this change. Every one of them runs under `set -u` and expands an array that
# can be empty, or already used the safe idiom and must keep it.
SWEPT = [
    "bin/idp-cloud",
    "bin/dockerfiles",
    "bin/idp-ci-local",
    "bin/idp-agent-key",
]

# `"${name[@]}"` not preceded by a `+` guard. PCRE lookbehind keeps the guarded form from
# matching, so this is exactly the unsafe shape and not its own fix.
UNGUARDED = re.compile(r'(?<!\+)"\$\{[A-Za-z_][A-Za-z0-9_]*\[@\]\}"')


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )


class TestTheIdiomItself:
    """Both directions, on the shell the estate actually runs."""

    def test_unguarded_empty_array_fails_this_is_the_falsifier(self):
        """The bug still reproduces: if it did not, this whole change proves nothing."""
        out = _run('set -u\na=()\nprintf "[%s]\\n" "${a[@]}"')
        assert out.returncode != 0, (
            "expected the unguarded empty expansion to fail on this bash"
        )
        assert "unbound variable" in out.stderr

    def test_guarded_empty_array_expands_to_nothing(self):
        # Count the WORDS the expansion contributes, not printf's output: `printf '[%s]'` with no
        # arguments still runs its format once and prints `[]`, so stdout shape is the wrong
        # oracle. `set -- ` is the right one -- it makes the word count visible as $#.
        out = _run('set -u\na=()\nset -- ${a[@]+"${a[@]}"}\nprintf "argc=%s\\n" "$#"')
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "argc=0", (
            f"an empty array must contribute zero words: {out.stdout!r}"
        )

    def test_guarded_filled_array_still_passes_every_element(self):
        """The failure mode of a bad fix: 'passing' by silently dropping real arguments."""
        out = _run(
            'set -u\na=(--namespace-name "ns with space" plain)\nprintf "[%s]\\n" ${a[@]+"${a[@]}"}'
        )
        assert out.returncode == 0, out.stderr
        lines = out.stdout.splitlines()
        # Quoted: an element with a space must arrive as ONE word. That is the whole point of
        # the inner quotes, and it is what `"${a[@]}"` bought before the guard was added.
        assert lines[0] == "[--namespace-name]"
        assert lines[1] == "[ns with space]"
        assert lines[2] == "[plain]"


class TestNoScriptGoesBack:
    """The sweep. A new unguarded expansion in a swept file fails here."""

    @pytest.mark.parametrize("rel", SWEPT)
    def test_no_unguarded_array_expansion(self, rel: str):
        path = REPO / rel
        if (
            not path.exists()
        ):  # a checkout may legitimately not carry every branch's file
            pytest.skip(f"{rel} not present in this checkout")
        offenders = [
            f"{rel}:{i}: {line.strip()}"
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if UNGUARDED.search(line)
        ]
        assert not offenders, (
            "an array expanded under `set -u` without the empty-array guard; on bash 3.2.57 this "
            "is fatal the first time the array is empty:\n" + "\n".join(offenders)
        )

    @pytest.mark.parametrize("rel", SWEPT)
    def test_the_scripts_still_parse(self, rel: str):
        path = REPO / rel
        if not path.exists():
            pytest.skip(f"{rel} not present in this checkout")
        out = subprocess.run(
            [BASH, "-n", str(path)], capture_output=True, text=True, check=False
        )
        assert out.returncode == 0, f"{rel} does not parse: {out.stderr}"
