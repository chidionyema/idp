"""The commit-msg stamp must be a trailer git can parse, in every message shape that occurs.

`.githooks/commit-msg` stamps `X-Idp-Signed` so `guarded-paths` can refuse a commit that bypassed
the hooks. That only works if git *parses* the stamp as a trailer, and git recognises a trailer
block only as the last paragraph of the message.

On 2026-09-22 it did not, on consolidate/fix-everything. The hook appended "\\nX-Idp-Signed: ..."
unconditionally, and `git merge --no-edit` writes .git/MERGE_MSG with no trailing newline -- so the
append merely terminated the subject line and left the stamp on line 2 with no blank line before
it. git read a two-line subject and no trailer, and guarded-paths refused HEAD as
"unsigned (--no-verify / --no-commit-hooks bypass detected)" on a commit that had run the hook.
The same unconditional blank line split an existing `Co-Authored-By:` block in two, and since git
reads only the last block, co-authorship stopped being attributed.

These tests drive the real hook and ask git itself, the way the check does. They fail against the
hook as it was written before that date.
"""

from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent
HOOK = REPO / ".githooks" / "commit-msg"


def _run(tmp_path, message: str) -> list[str]:
    """Run the hook over `message`, then return the trailers git parses back out of it."""
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603,S607 -- argv list, no shell; the estate's tool-invocation idiom / partial path is deliberate -- the tool is resolved from the operator's PATH
    (repo / ".git" / "idp-hook-secret").write_text("testsecret\n")

    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message)

    done = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
        ["bash", str(HOOK), str(msg)],  # noqa: S607 -- bash from the operator's PATH, deliberately
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, f"hook refused: {done.stderr}"

    parsed = subprocess.run(
        ["git", "interpret-trailers", "--parse"],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
        cwd=repo,
        input=msg.read_text(),
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in parsed.stdout.split("\n") if line.strip()]


def _keys(trailers: list[str]) -> set[str]:
    return {t.split(":", 1)[0] for t in trailers}


def test_a_merge_message_without_a_trailing_newline_is_still_signed(tmp_path):
    """This is the shape `git merge --no-edit` writes, and the one that broke."""
    trailers = _run(tmp_path, "Merge remote-tracking branch 'origin/x' into y")
    assert "X-Idp-Signed" in _keys(trailers), (
        "the stamp landed on the subject line, so git parses no trailer and guarded-paths "
        f"reads HEAD as unsigned; got {trailers!r}"
    )


def test_a_message_already_ending_in_a_trailer_block_keeps_those_trailers(tmp_path):
    trailers = _run(
        tmp_path,
        "fix(x): a thing\n\nBody line.\n\nCo-Authored-By: Someone <a@b.c>\n",
    )
    keys = _keys(trailers)
    assert "X-Idp-Signed" in keys, f"stamp missing; got {trailers!r}"
    assert "Co-Authored-By" in keys, (
        "the stamp opened a second trailer block, and git reads only the last one, so the "
        f"co-authorship was dropped; got {trailers!r}"
    )


def test_a_plain_body_gets_a_trailer_block_opened_for_it(tmp_path):
    trailers = _run(tmp_path, "fix(x): a thing\n\nBody line.\n")
    assert "X-Idp-Signed" in _keys(trailers), f"stamp missing; got {trailers!r}"


def test_the_stamp_is_not_applied_twice_on_amend(tmp_path):
    """Amend flows re-run the hook over a message that already carries the stamp."""
    signed = _run(tmp_path, "fix(x): a thing\n\nBody line.\n")
    already = [t for t in signed if t.startswith("X-Idp-Signed")][0]
    trailers = _run(tmp_path, f"fix(x): a thing\n\nBody line.\n\n{already}\n")
    stamps = [t for t in trailers if t.startswith("X-Idp-Signed")]
    assert len(stamps) == 1, f"stamped twice: {trailers!r}"
