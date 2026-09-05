"""crew#583: no script may grade a foreign timestamp against this machine's clock (LAW 45).

The incident is in test_incident_crew583_a_clock_behind_the_receipt_is_not_freshness.py. This file
is the part that stops it coming back, and it exists because fixing the four instances would not
have done that: the shape was copied into seven places over months, and the eighth copy would have
been written the same way by whoever needed the ninth freshness row.

The forbidden shape is one construct, not a style:

    age = (datetime.now(tz) - <a timestamp some other machine stamped>) / N
    if age > max: FAIL else: ok

Both operands are clocks and only one of them is this machine's. Subtracting them asserts the two
agree, and a MacBook whose battery has gone flat resets its RTC to a default epoch -- the 1970
stamps of 2026-08-27 -- so that assertion fails silently, in whichever direction the reset landed,
on every such row at once. Checking the sign of the result only catches one of the two directions,
which is what idp#611 shipped and why this file goes further: the local clock is removed from the
subtraction. `now` comes from the same response as the stamp (`bin/idp-cloud object head` returns
the store's `date` beside its `last-modified`), so the subtraction is one clock minus itself and a
machine that thinks it is 1970 computes the same age as a correct one.

What this grades is the construct itself -- a file that parses a timestamp it did not write and
also asks the local clock -- not a comment, a filename or a docstring saying the right words.

A file that legitimately needs the wall clock (stamping a receipt it is writing, timing its own
run) never trips this: it does not parse a foreign stamp. A file that needs both must go through
bin/lib/receipt_age.py, which is the one place the local clock is allowed near an age, and is
itself covered by the incident tests.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Asking this machine what time it is.
LOCAL_CLOCK = re.compile(r"datetime\.now\(|\btime\.time\(\)|\bdate \+%s\b|dt\.datetime\.now\(")
# Reading a timestamp somebody else stamped: an HTTP date, a GitHub run, a Kubernetes condition,
# or an ISO string out of a receipt this script is only the reader of.
FOREIGN_STAMP = re.compile(
    r"parsedate_to_datetime\(|[\"']last-modified[\"']|[\"']updatedAt[\"']|"
    r"[\"']lastTransitionTime[\"']|fromisoformat\(|strptime\(")

# The sites that still hold the old shape, each named with who is fixing it. This list may only
# shrink: anything not on it fails the guard below, so a ninth copy cannot be added quietly, and
# removing a name here is what "fixed" means. Entries are paths relative to the repo root.
NOT_YET_MIGRATED = {
    # Sign-guarded in idp#611 (merged fb779d7) so it can no longer read green, but still subtracts
    # this machine's clock from a GitHub timestamp. crew#583 CP3 moves it to the API Date header.
    "bin/idp-drills-row",
    # Held by session 09cd04a6 in worktrees idp-cs and idp-tc at the time of writing; taking them
    # here would have collided with work in flight. crew#583 CP2.
    "bin/idp-cluster-state",
    "bin/idp-telemetry-coverage",
    # Found by this guard rather than by the sweep that wrote it, which is the point of writing it:
    # hours_since() subtracts a GitHub timestamp from the local clock for every row of the founder's
    # report, and its `except ValueError: return 0.0` turns a stamp it cannot parse into "0 hours
    # ago" -- a second way for the same page to read new when it is not. crew#583 CP5, unowned.
    "bin/estate-founder",
    # Also found by the guard. lanes() ages each feed entry against the local clock to decide
    # whether a lane is still live (bin/estate-next:89-92), and the feed is written by other
    # sessions on other machines -- so this is two clocks even when it looks like one. crew#583
    # CP6, unowned.
    "bin/estate-next",
}

# Not offenders, and not a migration backlog: the writer of the stamps. A file here has to be the
# authority for both timestamps in a comparison, so that the local clock cancels out of it rather
# than being trusted. Anything else belongs above, with a checkpoint that will remove it.
THE_AUTHORITY = {
    # Stamps `date` beside `last-modified` for the file backend from one clock, which is what lets
    # every reader stop using its own (crew#583). It grades no age, so there is nothing here to be
    # wrong about the time.
    "bin/idp-cloud",
}


def _code_only(src: str) -> str:
    """The file with its comments and triple-quoted blocks removed.

    Without this the guard reads the incident write-ups: bin/lib/receipt_age.py quotes the
    forbidden line verbatim in its docstring to explain what it exists to prevent, and a guard that
    cannot tell an explanation from an instruction is grading prose. Cheap and textual on purpose --
    these are bash files with python heredocs inside them, so nothing here parses as one language.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('"""', i) or src.startswith("\'\'\'", i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            i = n if j == -1 else j + 3
            continue
        if src[i] == "#":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _offenders() -> dict[str, list[str]]:
    """Every executable under bin/ that reads a foreign stamp and also asks the local clock."""
    out = {}
    for p in sorted(ROOT.joinpath("bin").rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        src = _code_only(src)
        if LOCAL_CLOCK.search(src) and FOREIGN_STAMP.search(src):
            rel = str(p.relative_to(ROOT))
            out[rel] = [l.strip() for l in src.splitlines() if LOCAL_CLOCK.search(l)][:3]
    return out


def test_no_new_script_grades_a_foreign_timestamp_against_the_local_clock():
    """The guard. A file appearing here is either using the wall clock on somebody else's stamp, or
    is a legitimate new case that has to be argued for by name -- never by an unexplained addition
    to the set above."""
    new = {k: v for k, v in _offenders().items()
           if k not in NOT_YET_MIGRATED and k not in THE_AUTHORITY}
    assert not new, (
        "these read a timestamp they did not stamp and then ask this machine what time it is; "
        "measure against the clock that came back with the stamp instead -- "
        "bin/lib/receipt_age.py, crew#583:\n"
        + "\n".join("  %s\n      %s" % (k, "\n      ".join(v)) for k, v in sorted(new.items())))


@pytest.mark.parametrize("path", sorted(NOT_YET_MIGRATED))
def test_the_known_list_only_ever_shrinks(path):
    """A name left on the list after its site is fixed turns the guard back into an allow-list with
    a silent miss case, which is the failure mode that let this class spread. Fix the file, delete
    the line, in the same commit."""
    assert ROOT.joinpath(path).is_file(), "%s no longer exists -- delete it from NOT_YET_MIGRATED" % path
    assert path in _offenders(), (
        "%s no longer grades a foreign stamp against the local clock -- delete it from "
        "NOT_YET_MIGRATED so the guard starts holding it" % path)


def test_the_one_place_the_local_clock_is_allowed_near_an_age_does_not_use_it():
    """bin/lib/receipt_age.py is the exception the guard's docstring promises, so it had better not
    need one: it takes both clocks from the response and never calls datetime.now itself."""
    src = _code_only(ROOT.joinpath("bin/lib/receipt_age.py").read_text(encoding="utf-8"))
    assert not LOCAL_CLOCK.search(src), "receipt_age.py asks this machine what time it is"


def test_the_authority_stamps_both_ends_and_grades_neither():
    """The one exemption in this file, held to what it claims: idp-cloud may call the wall clock
    because it is writing a stamp, not judging one. The moment it compares two timestamps it is an
    instrument like any other and this exemption is wrong."""
    for path in sorted(THE_AUTHORITY):
        src = _code_only(ROOT.joinpath(path).read_text(encoding="utf-8"))
        assert "total_seconds()" not in src, "%s now measures an interval; it cannot be exempt" % path
        assert "max_age" not in src.lower(), "%s now grades an age; it cannot be exempt" % path
