"""The failure-class authority: one identity, one owner, one published correction.

Every test here is a way loop engineering could be wrong, and is made to fail if it is:

  * two agents hitting the same failure must land on the SAME class, or the correction is an
    anecdote rather than a shared fact;
  * a class must have ONE owner, and a crashed owner's late write must be refused by its
    fencing token rather than landing on a class that has moved on;
  * adoption must require an observation and the exact published version;
  * a class that comes back after it was resolved must re-open and record the prevention gap;
  * and the founder's acceptance test: a SECOND INDEPENDENT PROCESS must inherit the published
    correction and be able to acknowledge it, with no diagnostic investigation of its own.

The operations are driven through the door's own entry point (``main(argv)``), which is what
``bin/estate-failure-class`` and the intent call, because a fork on this machine costs seconds
and a suite that costs a minute per assertion is a suite nobody runs. The acceptance test at
the bottom runs TWO REAL PROCESSES, because there the process boundary is the thing proved.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIBEXEC = REPO / "platform" / "estate" / "libexec"
SCRIPT = LIBEXEC / "failure_class.py"


def _load(name: str):
    loader = SourceFileLoader(name, str(LIBEXEC / ("%s.py" % name)))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


fcr = _load("failure_class")
assurance = _load("assurance")
CATALOG = REPO / "catalog" / "decision-assurance.json"


def _real_receipt():
    """A genuine assurance receipt for the router scenario, so a tamper is a tamper."""
    catalog = json.loads(CATALOG.read_text())
    run = assurance.run_scenario("router.correlated-outage", catalog, 42, 200)
    run["scenario_name"] = "router.correlated-outage"
    return assurance.build_receipt(
        decision_id="router-failover",
        decision_class="router.failover",
        method="monte_carlo",
        tier="tier1",
        candidate_digest="sha256:none",
        run=run,
    )


class _Proc:
    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _run(db, *args, expect=None):
    """Invoke the failure-class door against a store of this test's own."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = fcr.main(["--db", str(db), *args])
    if expect is not None:
        assert code == expect, buf.getvalue()
    return _Proc(int(code), buf.getvalue())


def _subprocess(db, *args, expect=None):
    """Invoke the door as a real, separate process."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(db), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    if expect is not None:
        assert proc.returncode == expect, proc.stdout + proc.stderr
    return proc


def _json(proc):
    return json.loads(proc.stdout)


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "fcr.db"


def _class(db, kind="python-lint.rule", signature="F401", **kwargs):
    args = [
        "open",
        "--kind",
        kind,
        "--signature",
        signature,
        "--invariant",
        "ruff reports an unused import",
    ]
    for key, value in kwargs.items():
        args += ["--" + key.replace("_", "-"), str(value)]
    proc = _run(db, *args, expect=0)
    return _json(proc)["class_id"]


# --------------------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------------------


def test_the_class_identity_is_deterministic(db):
    one = _json(
        _run(db, "identify", "--kind", "python-lint.rule", "--signature", "F401")
    )
    two = _json(
        _run(db, "identify", "--kind", "python-lint.rule", "--signature", "F401")
    )
    other = _json(
        _run(db, "identify", "--kind", "python-lint.rule", "--signature", "F811")
    )
    assert one["class_id"] == two["class_id"]
    assert one["class_id"] != other["class_id"]
    assert one["class_id"].startswith("fcr-")


def test_two_agents_hitting_the_same_failure_land_on_the_same_class(db):
    first = _class(db, owner="pi")
    second = _class(db, owner="other-agent")
    assert first == second


def test_an_unknown_class_is_reported_as_unknown_not_invented(db):
    payload = _json(
        _run(db, "check", "--kind", "python-lint.rule", "--signature", "F401", expect=0)
    )
    assert payload["known"] is False
    assert payload["correction"] is None


# --------------------------------------------------------------------------------------
# the lease
# --------------------------------------------------------------------------------------


def test_a_class_has_one_owner_at_a_time(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    refused = _run(db, "claim", "--class", cid, "--owner", "other", "--ttl-s", "600")
    assert refused.returncode == 1
    assert "owned by pi" in refused.stdout


def test_an_expired_lease_is_reassignable_and_the_old_token_is_stale(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "0", expect=0)
    taken = _json(
        _run(
            db, "claim", "--class", cid, "--owner", "other", "--ttl-s", "600", expect=0
        )
    )
    assert taken["token"] == 2, "the fencing token must move on when the owner changes"
    stale = _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "the old owner was wrong",
    )
    assert stale.returncode == 1
    assert "stale" in stale.stdout


def test_a_stale_owner_cannot_resolve_even_while_the_new_lease_is_live(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "0", expect=0)
    _run(db, "claim", "--class", cid, "--owner", "other", "--ttl-s", "600", expect=0)
    stale = _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "late write from a crashed owner",
    )
    assert stale.returncode == 1


def test_renewal_refuses_a_stale_token(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    refused = _run(
        db, "renew", "--class", cid, "--owner", "pi", "--token", "1", "--ttl-s", "600"
    )
    assert refused.returncode == 1
    assert "stale" in refused.stdout


# --------------------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------------------


def test_a_resolution_publishes_a_versioned_correction(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    payload = _json(
        _run(
            db,
            "resolve",
            "--class",
            cid,
            "--owner",
            "pi",
            "--token",
            "1",
            "--correction",
            "remove the unused import",
            expect=0,
        )
    )
    assert payload["version"] == 1
    check = _json(_run(db, "check", "--class", cid, expect=0))
    assert check["state"] == "RESOLVED"
    assert check["correction"] == "remove the unused import"


def test_a_consequential_class_cannot_be_resolved_without_a_receipt(db):
    cid = _class(db, decision_class="router.failover")
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    refused = _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "raise the retry budget",
    )
    assert refused.returncode == 1
    assert "receipt" in refused.stdout


def test_a_resolution_with_a_tampered_receipt_is_refused(db, tmp_path):
    """A receipt whose numbers do not reproduce is refused, and the class stays unresolved."""
    cid = _class(db, decision_class="router.failover")
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(_real_receipt()))
    receipt_data = json.loads(receipt.read_text())
    receipt_data["metrics"]["p_slo_breach"] = 0.0
    receipt_data["metrics"]["slo_breach_bound"] = 0.0
    receipt.write_text(json.dumps(receipt_data))
    refused = _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "raise the retry budget",
        "--receipt-file",
        str(receipt),
    )
    assert refused.returncode == 1, refused.stdout
    assert "receipt" in refused.stdout.lower()
    state = _json(_run(db, "check", "--class", cid, expect=0))
    assert state["state"] != "RESOLVED", (
        "a refused resolution must not publish a correction"
    )


# --------------------------------------------------------------------------------------
# adoption and recurrence
# --------------------------------------------------------------------------------------


def test_adoption_requires_an_observation(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "remove the unused import",
        expect=0,
    )
    refused = _run(
        db, "adopt", "--class", cid, "--surface", "idp-python-strict", "--version", "1"
    )
    assert refused.returncode == 1
    assert "never observed" in refused.stdout


def test_adoption_is_bound_to_the_published_version(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "remove the unused import",
        expect=0,
    )
    _run(
        db,
        "observe",
        "--class",
        cid,
        "--surface",
        "idp-python-strict",
        "--evidence",
        "file.py:F401",
        expect=0,
    )
    refused = _run(
        db, "adopt", "--class", cid, "--surface", "idp-python-strict", "--version", "99"
    )
    assert refused.returncode == 1
    assert "version" in refused.stdout


def test_a_class_that_comes_back_reopens_and_records_the_prevention_gap(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "remove the unused import",
        expect=0,
    )
    payload = _json(
        _run(
            db,
            "observe",
            "--class",
            cid,
            "--surface",
            "idp-python-strict",
            "--evidence",
            "file.py:F401",
            expect=0,
        )
    )
    assert payload["recurrence"] is True
    assert payload["prevention_gap"]["published_version"] == 1
    check = _json(_run(db, "check", "--class", cid, expect=0))
    assert check["state"] == "REOPENED"
    assert check["recurrence"] == 1


def test_the_event_log_is_append_only_and_ordered(db):
    cid = _class(db)
    _run(db, "claim", "--class", cid, "--owner", "pi", "--ttl-s", "600", expect=0)
    _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "pi",
        "--token",
        "1",
        "--correction",
        "remove the unused import",
        expect=0,
    )
    events = _json(_run(db, "events", "--class", cid, expect=0))["events"]
    names = [e["event"] for e in events]
    assert names.index("claimed") < names.index("resolved")
    ids = [e["id"] for e in events]
    assert ids == sorted(ids)


# --------------------------------------------------------------------------------------
# THE FOUNDER'S ACCEPTANCE TEST -- two real processes
# --------------------------------------------------------------------------------------


SESSION_DRIVER = """
import io, json, sys
from contextlib import redirect_stdout
sys.path.insert(0, sys.argv[1])
import failure_class

db, phase = sys.argv[2], sys.argv[3]

def call(op, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = failure_class.main(["--db", db, op, *args])
    out = buf.getvalue()
    try:
        out = json.loads(out)
    except ValueError:
        pass
    print(json.dumps({"op": op, "code": int(code), "out": out}))
    sys.stdout.flush()

if phase == "a":
    call("open", "--kind", "python-lint.rule", "--signature", "F401",
         "--invariant", "ruff reports an unused import")
    # the class id is deterministic, so the session does not have to read it back
    import hashlib
    fingerprint = hashlib.sha256(json.dumps(["python-lint.rule", "F401"],
                                            sort_keys=True, separators=(",", ":"),
                                            default=str).encode("utf-8")).hexdigest()
    cid = "fcr-" + fingerprint[:20]
    call("claim", "--class", cid, "--owner", "session-a", "--ttl-s", "600")
    call("resolve", "--class", cid, "--owner", "session-a", "--token", "1",
         "--correction", "remove the unused import as a separate authoring step")
else:
    call("check", "--kind", "python-lint.rule", "--signature", "F401")
    import hashlib
    fingerprint = hashlib.sha256(json.dumps(["python-lint.rule", "F401"],
                                            sort_keys=True, separators=(",", ":"),
                                            default=str).encode("utf-8")).hexdigest()
    cid = "fcr-" + fingerprint[:20]
    call("observe", "--class", cid, "--surface", "idp-python-strict",
         "--evidence", "file.py:F401")
    call("pending", "--surface", "idp-python-strict")
    call("adopt", "--class", cid, "--surface", "idp-python-strict", "--version", "1",
         "--evidence", "clean run")
"""


def _session(db, phase, tmp_path):
    """Run one agent session in its own process and return its printed steps."""
    driver = tmp_path / ("session_%s.py" % phase)
    driver.write_text(SESSION_DRIVER)
    proc = subprocess.run(
        [sys.executable, str(driver), str(LIBEXEC), str(db), phase],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    steps = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            steps.append(json.loads(line))
    return steps


def test_a_second_independent_process_inherits_the_correction(db, tmp_path):
    """Session A resolves the class. Session B -- a different process, given nothing but the
    class -- inherits the published correction and acknowledges it, with no diagnosis of its
    own."""
    # SESSION A: one agent session, one process.
    session_a = _session(db, "a", tmp_path)
    assert [s["op"] for s in session_a] == ["open", "claim", "resolve"]
    assert all(s["code"] == 0 for s in session_a), session_a
    cid = session_a[0]["out"]["class_id"]

    # SESSION B: an independent process. It knows the class and nothing else.
    session_b = _session(db, "b", tmp_path)
    by_op = {s["op"]: s for s in session_b}
    inherited = by_op["check"]["out"]
    assert inherited["known"] is True
    assert (
        inherited["correction"]
        == "remove the unused import as a separate authoring step"
    )
    assert inherited["correction_version"] == 1
    assert by_op["observe"]["out"]["recurrence"] is True, (
        "the class came back at a surface that had been told about it"
    )
    pending = by_op["pending"]["out"]["pending"]
    assert [p["class_id"] for p in pending] == [cid]
    assert by_op["adopt"]["out"]["state"] == "ADOPTED"
    assert by_op["adopt"]["code"] == 0


def test_the_correction_is_inherited_without_any_diagnostic_input(db):
    """The inheritance must be a pull, not a side effect of the resolver's process."""
    cid = _class(db)
    _run(
        db, "claim", "--class", cid, "--owner", "session-a", "--ttl-s", "600", expect=0
    )
    _run(
        db,
        "resolve",
        "--class",
        cid,
        "--owner",
        "session-a",
        "--token",
        "1",
        "--correction",
        "the published correction",
        expect=0,
    )
    payload = _json(_run(db, "check", "--class", cid, expect=0))
    assert payload["correction"] == "the published correction"
    assert payload["state"] == "RESOLVED"
