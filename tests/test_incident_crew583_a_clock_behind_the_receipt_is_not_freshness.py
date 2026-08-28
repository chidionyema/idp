"""crew#583: freshness measured against this machine's clock is not freshness.

Four instruments read an Object Storage receipt and grade how old it is, and until now all four
asked the question the same way:

    age = (datetime.now(timezone.utc) - parsedate_to_datetime(last_modified)).total_seconds() / N
    if age > max:  FAIL
    else:          ok

Two defects, and the second is why this module exists rather than a one-line sign check.

The visible one: `age` is a subtraction of two clocks and only its upper bound was graded. A local
clock behind the stamp makes the age negative, `age > max` is false however dead the CronJob is,
and the instrument prints ok. The same bound in bin/idp-drills-row printed
`ok drills login-drill  login-drill.yml last green -9599.0h ago (max 3h)` and exited 0 under a
clock moved forward 400 days (idp#611, merged fb779d7).

The real one: **the local clock was in the subtraction at all.** When a MacBook's battery dies flat
the RTC resets to a default epoch -- the 1970 stamps of 2026-08-27 -- and every age computed
against it is wrong in whichever direction the reset landed. A sign check catches one of those two
directions and calls it solved. So the local clock is not asked: `now` is the `date` header of the
same response that carried the receipt, the storage service's own clock, stamped by the authority
that stamped `last-modified`. The subtraction is one clock minus itself, and a machine that thinks
it is 1970 computes the same age as one correct to the microsecond.

Rules:
  1. the verdict follows the authority's clock and this machine's cannot move it -- graded by
     moving both timestamps 400 days off local time, in both directions, and requiring the same
     answer every time;
  2. a response carrying no `date` is BLIND, never a quiet fall back to the local clock: that is
     the defect with a longer code path, and every backend bin/idp-cloud speaks carries one;
  3. a receipt stamped after the response that found it is BLIND too -- the store disagreeing with
     itself is not a fresh drill -- and never a FAIL naming the drill, which would send somebody to
     look at a healthy CronJob (LAW 28);
  4. real grading is unchanged: a fresh receipt is still ok, a genuinely old one is still FAIL;
  5. the rule is written once, in bin/lib/receipt_age.py, and imported. Four copies of three lines
     is how the bound came to be one-sided in seven places to begin with.

Every test drives the real script: it is copied into a temp `bin/` beside a fake `idp-cloud` and
the real `receipt_age.py`, so `$IDP` resolves to the temp tree and the module lookup that ships is
the one exercised. No network, no OCI session, no source text is matched.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# (script, row label, object body that grades ok, env, how old is genuinely stale)
CASES = [
    ("idp-door-heartbeat", "door-heartbeat", "ok front door 302 -> identity",
     {"DOOR_MAX_AGE_MIN": "20"}, timedelta(minutes=90)),
    ("idp-kini-state", "kini-finish", "ok status=COMPLETED red=0",
     {"KINI_STATE_MAX_AGE_MIN": "60"}, timedelta(minutes=180)),
    ("idp-science-facts", "science-facts", "ok sources=3\n{}",
     {"SCIENCE_FACTS_MAX_AGE_MIN": "120"}, timedelta(minutes=400)),
    ("idp-chaos-drill", "chaos-drill", "ok backstage pod killed, healthcheck stayed 200",
     {"CHAOS_MAX_AGE_HOURS": "194"}, timedelta(hours=400)),
]
IDS = [c[0] for c in CASES]

# Far enough from any real clock that no test below can pass by accident of the machine it runs on.
FAR = timedelta(days=400)


def _estate(tmp: Path, script: str, head: dict, body: str) -> Path:
    """The real script in a temp bin/, beside a fake idp-cloud answering `head` and the real module."""
    b = tmp / "bin"
    (b / "lib").mkdir(parents=True)
    shutil.copy2(ROOT / "bin" / script, b / script)
    shutil.copy2(ROOT / "bin" / "lib" / "receipt_age.py", b / "lib" / "receipt_age.py")
    fake = b / "idp-cloud"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "a = sys.argv[1:]\n"
        "if a[:2] == ['object', 'head']:\n"
        "    sys.stdout.write(%r); sys.exit(0)\n"
        "if a[:2] == ['object', 'get']:\n"
        "    sys.stdout.write(%r); sys.exit(0)\n"
        "print('fake idp-cloud: unexpected call', a, file=sys.stderr); sys.exit(1)\n"
        % (json.dumps(head), body))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return b


def _head(served: datetime, age: timedelta) -> dict:
    """What the store answers: it stamped the object `age` before it answered this read."""
    return {"last-modified": format_datetime(served - age),
            "date": format_datetime(served),
            "content-length": 42}


def _run(tmp: Path, b: Path, script: str, env: dict) -> subprocess.CompletedProcess:
    e = {"PATH": "%s:/usr/bin:/bin" % os.path.dirname(sys.executable), "HOME": str(tmp)}
    e.update(env)
    return subprocess.run([str(b / script)], env=e, capture_output=True, text=True, timeout=60)


# Rule 1 -- the whole point. Both timestamps sit 400 days off this machine's clock, in both
# directions, and the answer does not move. A flat CMOS battery is exactly this test's -FAR case.
@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
@pytest.mark.parametrize("skew", [-FAR, timedelta(0), FAR], ids=["clock_400d_behind", "clock_correct", "clock_400d_ahead"])
def test_a_fresh_receipt_is_fresh_whatever_this_machine_thinks_the_time_is(
        tmp_path, script, row, body, env, stale, skew):
    served = datetime.now(timezone.utc) + skew
    b = _estate(tmp_path, script, _head(served, timedelta(minutes=1)), body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("ok      %s " % row), r.stdout + r.stderr
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
@pytest.mark.parametrize("skew", [-FAR, timedelta(0), FAR], ids=["clock_400d_behind", "clock_correct", "clock_400d_ahead"])
def test_a_dead_drill_is_dead_whatever_this_machine_thinks_the_time_is(
        tmp_path, script, row, body, env, stale, skew):
    """The case the old code got wrong and a sign check still gets wrong: a stopped CronJob under a
    machine whose clock reads 1970 has to come out red, not green and not BLIND."""
    served = datetime.now(timezone.utc) + skew
    b = _estate(tmp_path, script, _head(served, stale), body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("FAIL    %s " % row), r.stdout + r.stderr
    assert "old (max" in r.stdout, r.stdout
    assert r.returncode == 1, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_a_response_with_no_clock_is_blind_not_a_fall_back_to_this_machine(
        tmp_path, script, row, body, env, stale):
    """Rule 2. Falling back here would reinstate the defect and hide it behind a branch nobody
    reads. Every backend carries a date, so an absent one means the read is wrong."""
    served = datetime.now(timezone.utc)
    head = _head(served, timedelta(minutes=1))
    head.pop("date")
    b = _estate(tmp_path, script, head, body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("BLIND   %s " % row), r.stdout + r.stderr
    assert "did not bring it" in r.stdout, r.stdout
    assert r.returncode == 2, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_a_receipt_stamped_after_the_read_that_found_it_is_blind(tmp_path, script, row, body, env, stale):
    """Rule 3. One authority, two timestamps, and the later one is the read -- so this is the store
    contradicting itself, not a drill that ran in the future."""
    served = datetime.now(timezone.utc)
    b = _estate(tmp_path, script, _head(served, timedelta(hours=-9)), body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("BLIND   %s " % row), r.stdout + r.stderr
    assert "disagreeing with itself" in r.stdout, r.stdout
    assert r.returncode == 2, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_the_store_is_named_as_the_broken_thing_not_the_drill(tmp_path, script, row, body, env, stale):
    """Rule 3, the half that matters operationally: a FAIL here sends somebody to a healthy drill
    while the actual fault goes unnamed (LAW 28)."""
    served = datetime.now(timezone.utc)
    b = _estate(tmp_path, script, _head(served, timedelta(hours=-9)), body)
    r = _run(tmp_path, b, script, env)
    assert "FAIL" not in r.stdout, r.stdout
    assert "old (max" not in r.stdout, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_a_stamp_seconds_after_the_read_is_still_fresh(tmp_path, script, row, body, env, stale):
    """Rule 3's bound is not zero: a store may round a stamp or answer from a replica a beat behind,
    and a guard that refuses correct work is an outage (LAW 38)."""
    served = datetime.now(timezone.utc)
    b = _estate(tmp_path, script, _head(served, timedelta(seconds=-30)), body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("ok      %s " % row), r.stdout + r.stderr
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_an_unreadable_timestamp_is_blind_not_zero(tmp_path, script, row, body, env, stale):
    """Rule 2's neighbour. A date that will not parse must not become an age of nothing."""
    served = datetime.now(timezone.utc)
    head = _head(served, timedelta(minutes=1))
    head["date"] = "not a date"
    b = _estate(tmp_path, script, head, body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("BLIND   %s " % row), r.stdout + r.stderr
    assert r.returncode == 2, r.stdout


@pytest.mark.parametrize("script,row,body,env,stale", CASES, ids=IDS)
def test_header_case_is_the_servers_choice_and_does_not_change_the_verdict(
        tmp_path, script, row, body, env, stale):
    """oci-cli renders response headers verbatim (objectstorage_cli_extended.py:1933 ->
    cli_util.py:775 under display_all_headers=True), so the store picks the casing, not us."""
    served = datetime.now(timezone.utc)
    head = {k.title(): v for k, v in _head(served, stale).items()}
    b = _estate(tmp_path, script, head, body)
    r = _run(tmp_path, b, script, env)
    assert r.stdout.startswith("FAIL    %s " % row), r.stdout + r.stderr
    assert r.returncode == 1, r.stdout


def test_every_backend_of_idp_cloud_carries_its_own_clock(tmp_path):
    """Rule 2 depends on this: the reader may refuse a response with no date only because every
    backend sends one. Graded by running the file backend, not by reading it."""
    root = tmp_path / "store"
    (root / "objects" / "b").mkdir(parents=True)
    (root / "objects" / "b" / "o").write_text("hi\n")
    r = subprocess.run([str(ROOT / "bin" / "idp-cloud"), "object", "head", "--bucket", "b", "--name", "o"],
                       env={"PATH": "%s:/usr/bin:/bin" % os.path.dirname(sys.executable),
                            "HOME": str(tmp_path),
                            "IDP_CLOUD_BACKEND": "file", "IDP_CLOUD_FILE_ROOT": str(root)},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    head = json.loads(r.stdout)
    assert "date" in head, head
    assert "last-modified" in head, head
    # Same clock for both, so the age it yields is right even when that clock is wrong.
    from email.utils import parsedate_to_datetime
    delta = (parsedate_to_datetime(head["date"]) - parsedate_to_datetime(head["last-modified"])).total_seconds()
    assert 0 <= delta < 60, head


def test_the_rule_is_one_file_the_four_import_not_four_copies():
    """Rule 5. Not a proxy for the behaviour -- the behaviour is graded above -- but the thing CP1
    asked for, and the only property a runtime test cannot see."""
    lib = ROOT / "bin" / "lib" / "receipt_age.py"
    assert lib.is_file()
    for script, _, _, _, _ in CASES:
        src = (ROOT / "bin" / script).read_text()
        assert "from receipt_age import receipt_age" in src, script
        assert 'IDP_LIB="$IDP/bin/lib"' in src, script
        assert "parsedate_to_datetime" not in src, (script, "still parsing the stamp on its own")
        assert "datetime.now" not in src, (script, "still asking this machine what time it is")
