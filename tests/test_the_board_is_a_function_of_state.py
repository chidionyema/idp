"""The Flux alarm's board is a function of the cluster, not of its own history.

On 2026-10-12 the board carried 60 open P0 rows "P0: Flux cannot reconcile Kustomization/..."
while exactly four Kustomizations were not Ready. 55 of those rows named an object that had been
Ready for weeks, and quad-ledger -- on fire at that moment -- had no row at all. Nothing here is a
mock: the fixture is that board and that cluster, recorded verbatim, so the plan is graded against
the worst board it will ever meet rather than a tidy one it can only pass.

These tests fail if the reconcile stops closing stale rows, stops opening missing ones, stops
folding one object's duplicates into a single row, or stops leaving another filer's P0 alone. The
first of them fails if the gate itself stops being able to fail.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "flux-board-reconcile"
FIXTURE = ROOT / "tests" / "fixtures" / "flux-board-2026-10-12.json"


def _module():
    loader = importlib.machinery.SourceFileLoader("flux_board_reconcile", str(SCRIPT))
    spec = importlib.util.spec_from_loader("flux_board_reconcile", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rec():
    """(module, cluster, rows) -- the real board and the real cluster it described."""
    m = _module()
    return (
        m,
        m.load_cluster_from_recording(str(FIXTURE)),
        m.load_rows_from_recording(str(FIXTURE)),
    )


def plan_of(rec):
    m, cluster, rows = rec
    present, not_ready = m.readiness(cluster)
    close, keep, to_open = m.plan(rows, present, not_ready)
    return m, present, not_ready, close, keep, to_open


def test_the_gate_can_fail(rec):
    """A gate that cannot fail is not a gate. Run against the board as it really stood, this one
    names the drift in both directions: 55 rows about objects that had recovered, one live fire
    with no row at all, and one object holding three rows."""
    m, cluster, rows = rec
    present, not_ready = m.readiness(cluster)
    bad = m.violations(rows, present, not_ready)
    assert len(bad) == 67, (
        f"the recorded board lied in 67 ways; violations now says {len(bad)}: {bad[:5]}"
    )
    assert any("quad-ledger" in b and "no row" in b for b in bad), (
        "the live fire with no row is the half of this that hides: a board can be wrong by staying silent"
    )
    assert any("is Ready now" in b for b in bad)
    assert any("one row per object" in b for b in bad)


def test_the_plan_makes_the_board_equal_the_cluster(rec):
    """56 close, 3 keep, 1 open -- and afterwards the board lies in zero ways."""
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    assert (len(close), len(keep), len(to_open)) == (56, 3, 1)
    assert (
        m.violations(m.simulate(rec[2], close, to_open, "T"), present, not_ready) == []
    )


def test_the_reconcile_is_idempotent(rec):
    """The property the event path never had. Run it on the board it just produced and it does
    nothing -- so drift cannot survive a tick, and a second tick cannot undo the first."""
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    after = m.simulate(rec[2], close, to_open, "T")
    close2, keep2, open2 = m.plan(after, present, not_ready)
    assert (close2, open2) == ([], []), "a second pass must find nothing left to do"


def test_one_object_keeps_one_row(rec):
    """chaos.flux-system held six open rows for one unreachable admission webhook, differing only
    in which webhook failed to answer. The object is the unit of recovery, so it is the unit of the
    row, and the fork is undone whether the fire is out or still burning: chaos has recovered, so
    all six rows close; jit is still not Ready, so its three rows become one."""
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    closed = {n for n, _ in close}
    chaos = {
        r["number"] for r in rec[2] if m.touches(r["title"]) == "flux-system/chaos"
    }
    assert len(chaos) == 6 and chaos <= closed, (
        "a recovered object's rows all close, however they forked"
    )
    jit = {r["number"] for r in rec[2] if m.touches(r["title"]) == "flux-system/jit"}
    assert len(jit) == 3 and jit - closed == {4362}
    assert [n for k, n in keep if k == "flux-system/jit"] == [4362], (
        "the oldest row of an object survives"
    )
    assert all("duplicate of #4362" in why for n, why in close if n in jit)


def test_a_row_whose_object_no_longer_exists_closes(rec):
    """flux-webhook was deleted from the cluster and its row sat open. 'Absent' is not 'Ready', and
    a board that only closes on recovery keeps a row for an object nobody can fix."""
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    assert "flux-system/flux-webhook" not in present
    why = dict(close).get(3533)
    assert why and "no longer exists" in why


def test_a_live_fire_with_no_row_gets_one(rec):
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    assert to_open == [
        (
            "flux-system/quad-ledger",
            "P0: Flux cannot reconcile Kustomization/quad-ledger.flux-system",
        )
    ]


def test_another_filers_p0_is_left_alone(rec):
    """#5867 is the login drill's P0, not this alarm's. A reconcile that closes everything open is
    a board that eats other people's work."""
    m, present, not_ready, close, keep, to_open = plan_of(rec)
    assert m.touches("P0: login drill failed") is None
    assert 5867 not in {n for n, _ in close}


def test_a_recording_is_not_read_as_a_cluster_with_no_objects(rec):
    """The bug this file hit first. The fixture stores the cluster trimmed; kubectl hands it as a
    document with 'items'. Read the raw shape as the trimmed one and every row silently becomes
    'no longer exists' -- a plan that closes the world and looks plausible doing it."""
    m, cluster, rows = rec
    assert len(cluster) == 41 and len(rows) == 60
    raw = {
        "items": [
            {
                "metadata": {"namespace": "flux-system", "name": "jit"},
                "status": {"conditions": [{"type": "Ready", "status": "False"}]},
            }
        ]
    }
    assert m.kustomizations_from_kubectl(raw) == [
        {"namespace": "flux-system", "name": "jit", "ready": False}
    ]


def test_ready_is_fluxs_own_condition_and_nothing_weaker(rec):
    """An object whose Ready condition is absent, or Unknown, is not Ready. This is the whole
    meaning of the reconcile: a row closes on Flux's verdict, never on a session's opinion."""
    m = rec[0]
    doc = {
        "items": [
            {"metadata": {"namespace": "n", "name": "no-condition"}, "status": {}},
            {
                "metadata": {"namespace": "n", "name": "unknown"},
                "status": {"conditions": [{"type": "Ready", "status": "Unknown"}]},
            },
            {
                "metadata": {"namespace": "n", "name": "ready"},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            },
        ]
    }
    present, not_ready = m.readiness(m.kustomizations_from_kubectl(doc))
    assert not_ready == {"n/no-condition", "n/unknown"} and "n/ready" in present


# --- the verdict cannot outrun GitHub's index (run 38280594349, 2026-10-12) -------------------

# A gh whose LIST endpoint answers with the board as it stood a few reads ago, while the writes
# land immediately. That is not a mock of GitHub; it is the one behaviour of GitHub's issue search
# that turned this reconcile's own correct pass red.
FAKE_GH = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

d = Path(os.environ["FAKE_GH_DIR"])
lag = int(os.environ.get("FAKE_GH_LAG", "1"))
argv = sys.argv[1:]
state = d / "open.json"
reads = d / "reads"

if argv[:2] == ["issue", "list"]:
    n = int(reads.read_text()) if reads.exists() else 0
    n += 1
    reads.write_text(str(n))
    print((state if n > lag else d / "at-first.json").read_text())
elif argv[:2] == ["issue", "close"]:
    num = int(argv[2])
    rows = [r for r in json.loads(state.read_text()) if r["number"] != num]
    state.write_text(json.dumps(rows))
elif argv[:2] == ["issue", "create"]:
    title = argv[argv.index("--title") + 1]
    rows = json.loads(state.read_text())
    rows.append({"number": 9000 + len(rows), "title": title, "createdAt": "2026-10-12T00:00:00Z"})
    state.write_text(json.dumps(rows))
    print("https://github.com/chidionyema/idp/issues/9000")
else:
    print("fake gh: unhandled: " + " ".join(argv), file=sys.stderr)
    sys.exit(1)
"""


def _board_row(n, name):
    return {
        "number": n,
        "title": f"P0: Flux cannot reconcile Kustomization/{name}.flux-system",
        "createdAt": "2026-09-01T00:00:00Z",
    }


def test_the_verdict_waits_for_github_to_show_its_own_writes():
    """The reconcile closed 67 rows and opened 4, then judged itself against the board as it stood
    BEFORE those writes, and went red on a correct pass. The wait is the fix; the judge is
    unchanged, so nothing that was really wrong is green now."""
    m = _module()
    present = {"flux-system/quad-ledger"}
    not_ready = {"flux-system/quad-ledger"}
    stale = [_board_row(3554, "via-negativa")]
    settled = [_board_row(5885, "quad-ledger")]
    reads = []

    def read():
        reads.append(1)
        return stale if len(reads) < 3 else settled

    after, bad = m.settle(
        read,
        lambda rs: m.violations(rs, present, not_ready),
        budget_s=1.0,
        poll_s=0.0,
        say=lambda *_: None,
    )
    assert bad == [], bad
    assert len(reads) == 3, (
        "the first re-read is stale by construction; the verdict must wait"
    )
    assert [r["number"] for r in after] == [5885]


def test_a_board_that_never_settles_is_still_a_failure():
    """The teeth stay. A board that genuinely contradicts the cluster is still a failure, and the
    wait cannot turn that green -- nor hang a 15-minute job, because it is bounded in attempts."""
    m = _module()
    stale = [_board_row(3554, "via-negativa")]
    reads = []

    def read():
        reads.append(1)
        return stale

    after, bad = m.settle(
        read,
        lambda rs: m.violations(
            rs, {"flux-system/quad-ledger"}, {"flux-system/quad-ledger"}
        ),
        budget_s=0.05,
        poll_s=0.02,
        say=lambda *_: None,
    )
    assert bad, "a board that never settles must still be a failure"
    assert len(reads) <= 5, f"bounded, not a spin: {len(reads)} reads"


def _run_reconcile(tmp_path, cluster, board, lag):
    """Run the real script against a gh that lags its own writes by `lag` reads."""
    gh_home = tmp_path / "gh"
    gh_home.mkdir()
    (gh_home / "open.json").write_text(json.dumps(board))
    (gh_home / "at-first.json").write_text(json.dumps(board))
    shim = tmp_path / "bin"
    shim.mkdir()
    (shim / "gh").write_text(FAKE_GH)
    (shim / "gh").chmod(0o755)
    cluster_json = tmp_path / "cluster.json"
    cluster_json.write_text(json.dumps(cluster))

    env = dict(os.environ)
    env.update(
        PATH=f"{shim}:{env['PATH']}",
        FAKE_GH_DIR=str(gh_home),
        FAKE_GH_LAG=str(lag),
        ESTATE_BOARD_SETTLE_S="0.05",
        ESTATE_BOARD_SETTLE_POLL_S="0.02",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--cluster-json", str(cluster_json)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    return r.returncode, r.stdout + r.stderr, gh_home


CLUSTER = [
    {"namespace": "flux-system", "name": "edge", "ready": False},
    {"namespace": "flux-system", "name": "recovered", "ready": True},
]


def test_the_real_run_is_green_when_github_shows_the_writes(tmp_path):
    """End to end: the board is written correctly and the index needs one read to catch up. Before
    the wait, this run exited 1 -- which is exactly what production did (run 38280594349)."""
    board = [_board_row(100, "recovered"), _board_row(101, "edge")]
    rc, out, gh_home = _run_reconcile(tmp_path, CLUSTER, board, lag=2)
    assert rc == 0, out
    assert "settled after" in out
    assert "#100 names" not in out, "the stale read must never reach the verdict"
    assert "ok      flux-board-reconcile" in out
    left = [r["number"] for r in json.loads((gh_home / "open.json").read_text())]
    assert left == [101], (
        f"the row about a recovered object was closed; the live one kept: {left}"
    )


def test_the_real_run_is_red_when_the_board_really_contradicts_the_cluster(tmp_path):
    """And the gate still refuses. Here the writes are right but no read ever shows them, so the
    pass cannot certify the board and says so, naming the contradiction -- a stale read is a
    failure to see, never a licence to claim success."""
    board = [_board_row(100, "recovered"), _board_row(101, "edge")]
    rc, out, gh_home = _run_reconcile(tmp_path, CLUSTER, board, lag=999)
    assert rc == 1, out
    assert "the board still contradicts the cluster" in out
    assert "still contradicts the cluster after" in out, (
        "the bounded wait must say how long it waited"
    )
    left = [r["number"] for r in json.loads((gh_home / "open.json").read_text())]
    assert left == [101], f"the board itself was written correctly: {left}"
