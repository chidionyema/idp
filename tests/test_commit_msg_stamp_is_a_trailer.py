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


# ---------------------------------------------------------------------------------------------
# The agent harness credits itself as a co-author. The estate does not accept that credit.
#
# A coding harness appends `Co-Authored-By: Claude <noreply@anthropic.com>` to every commit it
# makes unless configured not to. It is stripped by the hook rather than suppressed in a harness
# config, because the estate is model- and harness-agnostic: a setting in one vendor's file stops
# working the moment a different harness writes the commit, whereas the hook is the one point
# every commit already passes through.
#
# Measured 2026-10-04: 7 of the 25 lanes in the greenlane queue carried the trailer, under two
# model spellings ("Claude Opus 5.5", "Claude Fable 5.1"). It credits a model as a co-author of
# the founder's estate, which is not true, and it is the only string on those commits that names
# a vendor.


def test_the_harness_does_not_co_author_the_estate(tmp_path):
    """The two real spellings the harness emits both come out of the message."""
    for trailer in (
        "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>",
        "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>",
    ):
        trailers = _run(tmp_path, f"fix(x): a thing\n\nBody line.\n\n{trailer}\n")
        assert "X-Idp-Signed" in _keys(trailers), f"stamp missing; got {trailers!r}"
        assert not any("Claude" in t or "Anthropic" in t for t in trailers), (
            f"the harness still co-authors the commit; got {trailers!r}"
        )


def test_a_human_co_author_is_still_credited(tmp_path):
    """Only the harness's self-attribution goes. A person's does not."""
    trailers = _run(
        tmp_path,
        "feat(y): thing\n\nCo-Authored-By: Jane Doe <jane@example.com>\n",
    )
    assert any("Jane Doe" in t for t in trailers), (
        f"a human co-author was dropped along with the harness; got {trailers!r}"
    )
    assert "X-Idp-Signed" in _keys(trailers), f"stamp missing; got {trailers!r}"


def test_the_harness_is_stripped_and_a_human_is_kept_together(tmp_path):
    """The case that actually occurs: both trailers on one commit."""
    trailers = _run(
        tmp_path,
        "feat(z): thing\n\n"
        "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>\n"
        "Co-Authored-By: Jane Doe <jane@example.com>\n",
    )
    assert not any("Claude" in t for t in trailers), (
        f"harness trailer survived: {trailers!r}"
    )
    assert any("Jane Doe" in t for t in trailers), f"human trailer lost: {trailers!r}"
    assert "X-Idp-Signed" in _keys(trailers), f"stamp missing; got {trailers!r}"


def test_removing_the_harness_trailer_leaves_one_clean_block(tmp_path):
    """Stripping must not leave the blank paragraph that would split the trailer block.

    The hook already regressed once on exactly this: an unconditional blank line split a trailer
    block and git, which reads only the last block, stopped parsing the co-authorship. Removing a
    line has the same shape of hazard, so git -- not this test -- is asked whether the block is
    still one block.
    """
    trailers = _run(
        tmp_path,
        "fix(x): a thing\n\nBody line.\n\n"
        "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>\n",
    )
    keys = _keys(trailers)
    assert keys == {"X-Idp-Signed"}, f"expected exactly the stamp; got {trailers!r}"
