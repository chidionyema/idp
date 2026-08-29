"""How old is a receipt, measured without asking this machine what time it is (crew#583).

Every drill row in this estate that reads an Object Storage receipt asks the same question, and
until 2026-08-28 every one of them asked it the same way:

    age = (datetime.now(timezone.utc) - parsedate_to_datetime(last_modified)).total_seconds() / N
    if age > max:  FAIL
    else:          ok

Two defects, one bad and one worse.

The bad one: `age` is a subtraction of two clocks and only its upper bound was ever graded. A local
clock behind the stamp makes `age` negative, `age > max` is false however dead the CronJob is, and
the instrument prints ok. The same bound in bin/idp-drills-row printed `ok drills login-drill
login-drill.yml last green -9599.0h ago (max 3h)` and exited 0 under a clock moved forward 400 days
(idp#611, merged fb779d7).

The worse one, and the reason this module exists rather than a sign check: **the local clock was in
the subtraction at all.** When a MacBook's battery dies flat the hardware RTC resets to a default
epoch. Every age computed against it is wrong, in whichever direction the reset happened to land,
and a sign check only catches one of the two directions. A dashboard that a dead CMOS battery can
talk into reporting green is not an instrument.

So the local clock is not asked. `now` comes from the `date` header of the very response that
carried the receipt -- the storage service's own clock, stamped by the same authority that stamped
`last-modified`, travelling in the same round trip. The subtraction is one clock minus itself. A
machine whose RTC says 1970 gets the same age as one that is correct to the microsecond, because
neither machine's opinion is consulted.

That property has a test rather than this paragraph:
`test_the_age_follows_the_authoritys_clock_not_this_machines` moves both timestamps 400 days away
from the local clock, in both directions, and requires the same verdict.

A response with no `date` is BLIND. Not "fall back to the local clock" -- that is the defect with a
longer code path -- and not a silent default. Every backend bin/idp-cloud speaks carries one,
including the file backend, so an absent `date` means something is wrong with the read, and an
instrument that cannot measure says so (LAW 45 step 5).
"""
from __future__ import annotations

import sys
from datetime import timedelta
from email.utils import parsedate_to_datetime

# How far the receipt may be stamped ahead of the clock that served it. Both come from the same
# authority in the same response, so this is not clock skew -- it is the object claiming to have
# been written after the read that found it, which is not a thing that happens. Small and non-zero
# only because a store may round or a replica may lag a beat.
FUTURE_GRACE = timedelta(seconds=60)


def receipt_age(head: dict, per_unit: float, row: str) -> float:
    """Age of the receipt described by `head`, in units of `per_unit` seconds.

    `head` is the parsed object-head response: `last-modified` is when the receipt was written and
    `date` is what the authority's clock said as it answered. Both are that authority's; this
    machine's clock is not consulted and cannot change the answer.

    `row` is the label the caller prints its own verdicts under, so a refusal reads like the rest of
    that script's output. BLIND and an exit rather than a returned value, because a read this
    untrustworthy is untrustworthy for every row the caller was about to print: naming one stale
    drill sends somebody to look at a healthy drill while the actual fault goes unnamed (LAW 28).
    """
    def blind(why: str) -> None:
        print("BLIND   %s  %s" % (row, why))
        sys.exit(2)

    # These are HTTP response headers, and header case is the server's choice, not a contract: the
    # oci backend hands back whatever casing the store used (oci-cli 3.90.3 renders response.headers
    # with display_all_headers=True and keeps the key verbatim -- objectstorage_cli_extended.py:1933,
    # cli_util.py:775), while the file backend writes them lowercase. Fold once, read once.
    h = {str(k).lower(): v for k, v in head.items()}
    stamped_raw = h.get("last-modified")
    served_raw = h.get("date")
    if not stamped_raw:
        blind("object head carried no last-modified -- cannot say when the receipt was written")
    if not served_raw:
        blind("object head carried no date header -- the only clock that could measure this "
              "receipt is the one that stamped it, and this response did not bring it. Refusing to "
              "substitute this machine's clock (crew#583)")
    try:
        stamped = parsedate_to_datetime(stamped_raw)
        served = parsedate_to_datetime(served_raw)
    except Exception as e:  # a malformed date is not a fresh receipt
        blind("object head carried an unreadable timestamp (%s): last-modified=%r date=%r"
              % (e, stamped_raw, served_raw))

    delta = served - stamped
    if delta < -FUTURE_GRACE:
        blind("the receipt is stamped %s but the store answered at %s -- it claims to have been "
              "written after the read that found it, which is the store disagreeing with itself, "
              "not a fresh drill" % (stamped_raw, served_raw))
    return delta.total_seconds() / per_unit
