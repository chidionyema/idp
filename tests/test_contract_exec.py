"""Contract execution against the estate's ONE executor.

WHAT THESE TESTS ARE FOR. The executor attaches a tracked contract to `mcp/plugins/estate_executor.py`
-- the door every other agent already executes through -- and records the outcome. Three properties
matter and each is proved below:

  1. NO NEW SPAWN PATH. The module must reach the shared `execute_command`, never a local
     subprocess. If someone later "simplifies" this into a `Popen`, these tests still pass, so the
     structural claim is checked separately by reading the source for spawn keywords.

  2. A REFUSAL IS NOT A COMPLETION. The executor refuses payloads it cannot bound and returns
     `{"accepted": False}` WITHOUT raising. Treating that as dispatched would put a running node on
     the board for work that never started -- the estate's oldest defect class.

  3. IT DOES NOT INVENT THE COMMAND. A contract records what was asked for; the command is
     supplied. A model's `then` clause must never become a shell string.

The stub executor is the same injection point `tests/test_executor_mcp.py` uses, so no daemon and
no subprocess is involved and every case runs offline.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXEC = REPO / "platform" / "intent" / "contract_exec.py"


class StubExecutor:
    """`estate_executor`'s surface, with the outcomes a test needs to force.

    Mirrors only what is called: `execute_command(command, ...)` and `read_job(job_id)`. The real
    module's own tests cover its internals; here it is a boundary to stand in front of.
    """

    def __init__(self, *, accept: bool = True, state: str = "accepted", exit_code=None):
        self.accept = accept
        self.state = state
        self.exit_code = exit_code
        self.calls: list[str] = []
        self.job_id = "exec-test-1"

    def execute_command(self, command, **_kw):
        self.calls.append(command)
        if not self.accept:
            return {"accepted": False, "error": "command is not bounded"}
        return {"accepted": True, "job_id": self.job_id, "ceiling_sec": 60}

    def read_job(self, job_id, **_kw):
        if job_id != self.job_id:
            return {"found": False, "error": "no job with that id"}
        return {
            "found": True,
            "job_id": job_id,
            "state": self.state,
            "exit_code": self.exit_code,
            "log": "",
        }


@pytest.fixture()
def mod(monkeypatch, tmp_path):
    """The module, its database in a temp dir, and its executor replaced by a stub."""
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.setenv("LITELLM_OBSERVER_MODEL", "exec-test-model")
    spec = importlib.util.spec_from_file_location("contract_exec_under_test", EXEC)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["contract_exec_under_test"] = m
    spec.loader.exec_module(m)

    stub = StubExecutor()
    monkeypatch.setattr(m, "_executor", lambda: stub)
    # A LIVE DAEMON BY DEFAULT, because `_poll` now checks for one and the real machine does not
    # have it (measured 2026-09-20: no socket at ~/.estate/executor.sock). Tests that are about the
    # dispatch path must not fail for the estate's own missing daemon; the three tests below that
    # ARE about its absence override this explicitly.
    monkeypatch.setattr(m, "_daemon_is_up", lambda: True)
    m.stub = stub  # type: ignore[attr-defined]
    return m


def _seed(mod, *, command: str | None = "echo done") -> str:
    """A PENDING contract, made the way the Observer makes one."""
    obs = mod._observer()
    con = mod._connect()
    mod.migrate(con)
    bdd = obs.normalise(
        {"feature": "F", "given": "G", "when": "W", "then": "T", "agents_required": 1}
    )
    cid = obs.commit(
        con,
        command="do the thing",
        transcript="agents do the thing",
        bdd=bdd,
        trigger="agents",
        session_id="s-1",
        source_surface="voice",
        asr_seconds=0.1,
        model="exec-test-model",
    )
    if command is not None:
        mod.attach_command(con, cid, command)
    con.close()
    return cid


def test_the_migration_is_additive_and_idempotent(mod):
    """Twice must not raise, and the Observer's own columns must survive."""
    con = mod._connect()
    mod.migrate(con)
    mod.migrate(con)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(action_contracts)")}
    assert {"command", "job_id", "exit_code", "error", "finished_at"} <= cols
    assert {"contract_id", "bdd_json", "status"} <= cols
    con.close()


def test_a_contract_with_no_command_is_refused_not_guessed(mod):
    """PROPERTY 3. The then-clause is prose for a person, not a shell string."""
    cid = _seed(mod, command=None)
    con = mod._connect()
    mod.migrate(con)
    with pytest.raises(mod.Refused) as exc:
        mod.dispatch(con, cid, dry_run=False)
    assert "no command" in str(exc.value)
    assert con.execute(
        "SELECT status FROM action_contracts WHERE contract_id = ?", (cid,)
    ).fetchone()["status"] == "PENDING"
    assert mod.stub.calls == []
    con.close()


def test_dispatch_hands_the_command_to_the_executor_and_records_the_job(mod):
    cid = _seed(mod, command="echo hello")
    con = mod._connect()
    mod.migrate(con)
    assert mod.dispatch(con, cid, dry_run=False) == "RUNNING"

    assert mod.stub.calls == ["echo hello"]
    row = con.execute("SELECT * FROM action_contracts WHERE contract_id = ?", (cid,)).fetchone()
    assert row["status"] == "RUNNING"
    assert row["job_id"] == "exec-test-1"
    signal = con.execute("SELECT text FROM fleetview_signals WHERE kind = 'dispatched'").fetchone()
    assert cid in signal["text"]
    con.close()


def test_an_executor_refusal_becomes_REFUSED_and_never_a_running_node(mod, monkeypatch):
    """PROPERTY 2, and the reason it is a test rather than a comment.

    The executor refuses WITHOUT raising, so a `try/except` around it proves nothing. A caller that
    read `accepted` off the result and ignored it would leave the board showing work in flight.
    """
    monkeypatch.setattr(mod, "_executor", lambda: StubExecutor(accept=False))
    cid = _seed(mod)
    con = mod._connect()
    mod.migrate(con)
    assert mod.dispatch(con, cid, dry_run=False) == "REFUSED"
    row = con.execute("SELECT status, error, job_id FROM action_contracts WHERE contract_id = ?",
                      (cid,)).fetchone()
    assert row["status"] == "REFUSED"
    assert "not bounded" in row["error"]
    assert row["job_id"] is None
    con.close()


def test_a_finished_job_completes_the_contract_and_a_failed_one_blocks_it(mod, monkeypatch):
    for exit_code, expected in ((0, "COMPLETED"), (1, "BLOCKED")):
        stub = StubExecutor(state="finished", exit_code=exit_code)
        monkeypatch.setattr(mod, "_executor", lambda s=stub: s)
        cid = _seed(mod)
        con = mod._connect()
        mod.migrate(con)
        assert mod.dispatch(con, cid, dry_run=False) == "RUNNING"
        assert mod.dispatch(con, cid, dry_run=False) == expected
        row = con.execute("SELECT exit_code, finished_at FROM action_contracts WHERE contract_id = ?",
                          (cid,)).fetchone()
        assert row["exit_code"] == exit_code
        assert row["finished_at"]
        con.close()


def test_a_job_the_executor_has_forgotten_stays_RUNNING(mod, monkeypatch):
    """The registry is in-memory, so a daemon restart loses it. That is not a completion.

    Inventing an outcome here would be a fabricated receipt (AGENTS.md section 3). The contract is
    left RUNNING and the state is reported, not guessed. The daemon IS up in this case, which is
    what makes it a forgotten job rather than a dead executor.
    """
    monkeypatch.setattr(mod, "_daemon_is_up", lambda: True)
    cid = _seed(mod)
    con = mod._connect()
    mod.migrate(con)
    mod.dispatch(con, cid, dry_run=False)
    mod.stub.job_id = "exec-test-1"  # dispatch already recorded it
    mod.stub.state = "accepted"
    assert mod.dispatch(con, cid, dry_run=False) == "RUNNING"

    # Now make the executor forget it entirely.
    forgetful = StubExecutor()
    forgetful.job_id = "something-else"
    mod.stub = forgetful  # type: ignore[assignment]
    assert mod.dispatch(con, cid, dry_run=False) == "RUNNING"
    assert con.execute("SELECT status FROM action_contracts WHERE contract_id = ?",
                       (cid,)).fetchone()["status"] == "RUNNING"
    con.close()


def test_a_terminal_contract_is_never_redispatched(mod):
    cid = _seed(mod)
    con = mod._connect()
    mod.migrate(con)
    con.execute("UPDATE action_contracts SET status = 'COMPLETED' WHERE contract_id = ?", (cid,))
    con.commit()
    assert mod.dispatch(con, cid, dry_run=False) == "COMPLETED"
    assert mod.stub.calls == []
    con.close()


def test_dry_run_dispatches_nothing(mod):
    cid = _seed(mod)
    con = mod._connect()
    mod.migrate(con)
    mod.dispatch(con, cid, dry_run=True)
    assert mod.stub.calls == []
    assert con.execute("SELECT job_id FROM action_contracts WHERE contract_id = ?",
                       (cid,)).fetchone()["job_id"] is None
    con.close()


def test_tick_advances_one_bad_contract_without_stopping_the_others(mod):
    """One unrunnable row is a fact about that row, not a reason to stall the queue.

    `moved` counts contracts ADVANCED, not contracts visited -- an earlier version of this test
    asserted 2 and was wrong: the unrunnable row raises `Refused`, which `tick` reports and does not
    count. The distinction matters because `moved` is printed to a person as "N contract(s)
    advanced", and counting the refused one would overstate what happened.
    """
    good = _seed(mod, command="echo ok")
    _seed(mod, command=None)  # unrunnable: no command
    con = mod._connect()
    mod.migrate(con)
    assert mod.tick(con, dry_run=False, limit=10) == 1
    assert mod.stub.calls == ["echo ok"]
    assert con.execute("SELECT status FROM action_contracts WHERE contract_id = ?",
                       (good,)).fetchone()["status"] == "RUNNING"
    con.close()


def test_no_daemon_is_reported_as_BLIND_and_not_as_a_lost_job(mod, monkeypatch, capsys):
    """The distinction the whole switchover depends on: a job the daemon forgot vs no daemon.

    Measured 2026-09-20: `bin/idp-executor-status` reports `MEASURED_FAIL no socket at
    ~/.estate/executor.sock` on this machine, so EVERY contract dead-ends here. Both cases leave
    the contract RUNNING, and the words a person reads must tell them apart -- otherwise an estate
    where nothing can run looks like a job that was lost.
    """
    cid = _seed(mod, command="echo ok")
    con = mod._connect()
    mod.migrate(con)
    mod.dispatch(con, cid, dry_run=False)  # reaches RUNNING against the stub

    monkeypatch.setattr(mod, "_daemon_is_up", lambda: False)
    assert mod.dispatch(con, cid, dry_run=False) == "RUNNING"
    err = capsys.readouterr().err
    assert "no executor daemon" in err
    assert "bin/exec-daemon" in err


@pytest.mark.parametrize("accept", [True, False])
def test_a_missing_daemon_does_not_mark_the_contract_BLOCKED(mod, monkeypatch, accept):
    """An estate-wide outage must not be recorded against one contract.

    BLOCKED means the command ran and the outcome was bad. Nothing ran here, and a row-level status
    that blamed the contract would be the wrong story told confidently.
    """
    monkeypatch.setattr(mod, "_daemon_is_up", lambda: False)
    cid = _seed(mod)
    con = mod._connect()
    mod.migrate(con)
    mod.dispatch(con, cid, dry_run=False)
    mod.dispatch(con, cid, dry_run=False)
    status = con.execute("SELECT status FROM action_contracts WHERE contract_id = ?",
                         (cid,)).fetchone()["status"]
    assert status in ("PENDING", "RUNNING")
    con.close()


def test_the_socket_check_tests_a_connection_not_a_path(mod, monkeypatch, tmp_path):
    """A stale socket file must read as DOWN.

    A daemon killed with SIGKILL leaves its socket behind. `exists()` would report a dead executor
    as alive, which is worse than not checking.

    THE FIXTURE'S STUB IS UNDONE FIRST. The `mod` fixture replaces `_daemon_is_up` with a live-daemon
    lambda so the dispatch tests do not fail for this machine's missing daemon; a test OF that
    function has to put the real one back. Calling the stub here asserted the stub, not the socket.
    """
    import importlib

    spec = importlib.util.spec_from_file_location("ce_fresh", EXEC)
    fresh = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(fresh)

    stale = tmp_path / "executor.sock"
    stale.write_text("")  # a file, but nothing is listening on it
    monkeypatch.setenv("IDP_EXECUTOR_SOCKET", str(stale))
    assert fresh._daemon_is_up() is False

    # And a path that does not exist at all is down too, without raising.
    monkeypatch.setenv("IDP_EXECUTOR_SOCKET", str(tmp_path / "nope.sock"))
    assert fresh._daemon_is_up() is False


def test_this_module_contains_no_second_spawn_path():
    """PROPERTY 1, checked structurally because a behaviour test cannot see it.

    A future edit that replaced the executor call with a `Popen` would keep every test above green
    while quietly reintroducing the second spawn path LAW 43 forbids. Reading the source is the
    only way to assert the absence.

    DOCSTRINGS ARE STRIPPED TOO. The words appear on purpose in the prose that explains the ban --
    a first version of this check stripped only `#` comments and failed on its own module docstring
    saying "never a local subprocess". That is the check reporting its own explanation as a defect,
    which is the false positive that gets a guard deleted.
    """
    import ast

    tree = ast.parse(EXEC.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            # Drop a leading docstring, which is prose, not a call.
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body = body[1:]
            node.body = body or [ast.Pass()]
    code = ast.unparse(tree)
    for banned in ("subprocess", "Popen", "os.system", "os.spawn", "setsid", "nohup"):
        assert banned not in code, f"{banned} is a second spawn path; use execute_command"
