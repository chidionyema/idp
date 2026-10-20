"""Recency + frequency ranking, retrieval reinforcement and scheduled consolidation.

main.py needs fastapi, psycopg and Python 3.12 syntax, so it is not imported: the pure rules live
in ranking.py / consolidation.py and are graded directly, and the wiring in main.py, schema.sql, the
Dockerfile and the manifest is pinned by reading the shipped text (ast / yaml), the same way
test_db_conn_commit.py grades get_db_conn.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import consolidation
import ranking

HERE = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)


def result(key, maple, age_days, access=0, kind="fact"):
    return {
        "key": key,
        "maple_score": maple,
        "recorded_at": (NOW - timedelta(days=age_days)).isoformat(),
        "access_count": access,
        "provenance": {"kind": kind},
    }


# --- the scoring rules --------------------------------------------------------------------------


def test_a_fresh_fact_outranks_an_old_one_with_the_same_maple_score():
    got = ranking.rank([result("old", 1.0, 200), result("new", 1.0, 1)], NOW)
    assert [r["key"] for r in got] == ["new", "old"]


def test_a_frequently_retrieved_fact_outranks_a_never_retrieved_one():
    got = ranking.rank([result("cold", 1.0, 5, 0), result("hot", 1.0, 5, 40)], NOW)
    assert [r["key"] for r in got] == ["hot", "cold"]


def test_a_decision_does_not_age():
    old = ranking.boost(NOW - timedelta(days=900), 0, NOW, "decision")
    fresh = ranking.boost(NOW, 0, NOW, "decision")
    assert old == fresh == ranking.RECENCY_WEIGHT
    assert ranking.boost(NOW - timedelta(days=900), 0, NOW, "fact") < 0.001


def test_the_boost_is_bounded_so_a_much_nearer_fact_still_wins():
    ceiling = ranking.RECENCY_WEIGHT + ranking.FREQUENCY_WEIGHT
    assert ranking.boost(NOW, 10**9, NOW) <= ceiling + 1e-9
    # 0.09 nearer on MAPLE score beats the largest possible boost on the other side
    nearer = result("nearer", 1.09, 900, 0)
    boosted = result("boosted", 1.00, 0, 10**6)
    assert ranking.rank([boosted, nearer], NOW)[0]["key"] == "nearer"


def test_frequency_saturates_instead_of_running_away():
    assert ranking.frequency_factor(0) == 0.0
    assert ranking.frequency_factor(10**9) == 1.0
    assert ranking.frequency_factor(5) < ranking.frequency_factor(25) < 1.0


def test_a_row_with_no_usable_timestamp_ranks_on_maple_alone():
    r = {"key": "k", "maple_score": 1.0, "recorded_at": "garbage", "provenance": {}}
    out = ranking.rank([r], NOW)
    assert out[0]["rank_boost"] == 0.0 and out[0]["rank_score"] == 1.0


def test_the_boost_is_reported_so_a_caller_can_see_why_a_fact_moved():
    out = ranking.rank([result("a", 1.0, 0, 50)], NOW)[0]
    assert out["rank_boost"] == pytest.approx(0.08, abs=1e-3)
    assert out["rank_score"] == pytest.approx(1.08, abs=1e-3)


# --- the wiring in the shipped files -------------------------------------------------------------


def _func(name):
    tree = ast.parse((HERE / "main.py").read_text())
    for node in tree.body:
        if (
            isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"main.py no longer defines {name}")


def test_the_boost_runs_after_the_gate_so_it_orders_and_never_admits():
    src = ast.unparse(_func("_ranked"))
    assert src.index("final_score > 0.35") < src.index("ranking.rank(")
    assert "ranking.rank(scored_results)[:limit]" in src


def test_recall_and_brief_both_count_the_retrieval():
    assert "_record_access" in ast.unparse(_func("memory_recall"))
    assert "_record_access" in ast.unparse(_func("memory_brief"))


def test_a_failed_access_count_never_fails_the_recall():
    src = ast.unparse(_func("_record_access"))
    assert "except Exception" in src and "transaction()" in src  # savepoint + swallow


def test_the_count_lives_in_its_own_table_not_on_memories():
    # Updating memories fires fn_bump_memory_version: it would bump version and reset updated_at.
    sql = (HERE / "schema.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS memory_access" in sql
    assert "ALTER TABLE memory_access FORCE ROW LEVEL SECURITY" in sql
    assert (
        "access_count"
        not in sql.split("CREATE TABLE IF NOT EXISTS memories")[1].split(");")[0]
    )
    assert "UPDATE memories" not in ast.unparse(_func("_record_access"))


def test_the_image_ships_every_module_main_and_the_cronjob_import():
    # a module missing from this COPY is an ImportError at pod start, not at review
    copy = next(
        line
        for line in (HERE / "Dockerfile").read_text().splitlines()
        if line.startswith("COPY main.py")
    )
    for f in (
        "ranking.py",
        "consolidation.py",
        "hedge.py",
        "harness.py",
        "security_core.py",
        "schema.sql",
    ):
        assert f in copy


# --- scheduled consolidation ---------------------------------------------------------------------


class FakeCursor:
    def __init__(self, log, rowcounts=(3, 2), tenants=()):
        self.log, self._counts, self.rowcount = log, list(rowcounts), 0
        self._tenants = tenants

    def execute(self, sql, args=None):
        self.log.append((" ".join(sql.split()), args))
        if sql.lstrip().upper().startswith("DELETE"):
            self.rowcount = self._counts.pop(0)

    def fetchall(self):
        return [{"tenant_id": t} for t in self._tenants]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_a_tenant_is_swept_under_its_own_rls_guc_first():
    log = []
    got = consolidation.sweep_tenant(FakeCursor(log), "t-1")
    assert log[0][0].startswith("SELECT set_config('app.tenant_id'") and log[0][1] == (
        "t-1",
    )
    assert (
        "harness_scratchpad" in log[1][0]
        and "expires_at < CURRENT_TIMESTAMP" in log[1][0]
    )
    assert "preference_recurrence" in log[2][0]
    assert got == {"scratchpad_expired": 3, "recurrence_aged": 2}


def test_the_sweep_never_touches_memories():
    log = []
    consolidation.sweep_tenant(FakeCursor(log), "t-1")
    assert not [sql for sql, _ in log if "memories" in sql]


class FakeConn:
    def __init__(self, tenants, fail=()):
        self.tenants, self.fail, self.log, self.swept = tenants, set(fail), [], []

    def cursor(self):
        c = FakeCursor(self.log, rowcounts=(1, 1) * 10, tenants=self.tenants)
        real = c.execute

        def execute(sql, args=None):
            if args and args[0] in self.fail and "set_config" in sql:
                raise RuntimeError("boom")
            if "set_config" in sql:
                self.swept.append(args[0])
            real(sql, args)

        c.execute = execute
        return c

    def transaction(self):
        return FakeCursor(self.log)


def test_one_failing_tenant_does_not_stop_the_others_and_fails_the_job(capsys):
    conn = FakeConn(["a", "b", "c"], fail=["b"])
    totals = consolidation.sweep(conn)
    assert conn.swept == ["a", "c"]
    assert totals["tenants"] == 3 and totals["failed"] == 1
    assert (
        totals["scratchpad_expired"] == 2
        and "tenant b failed" in capsys.readouterr().err
    )


def _docs():
    return [
        d
        for d in yaml.safe_load_all((HERE / "oke-unified-memory.yaml").read_text())
        if d
    ]


def test_the_cronjob_is_scheduled_bounded_and_cannot_receive_service_traffic():
    docs = _docs()
    job = next(d for d in docs if d["kind"] == "CronJob")
    svc = next(d for d in docs if d["kind"] == "Service")
    spec = job["spec"]
    assert spec["schedule"] and spec["concurrencyPolicy"] == "Forbid"
    pod = spec["jobTemplate"]["spec"]["template"]
    assert spec["jobTemplate"]["spec"]["activeDeadlineSeconds"] <= 600
    labels = pod["metadata"]["labels"]
    selector = svc["spec"]["selector"]
    assert not all(
        labels.get(k) == v for k, v in selector.items()
    )  # Service must not select it
    c = pod["spec"]["containers"][0]
    assert c["command"] == ["python", "consolidation.py"]
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert all("value" not in e or "PASSWORD" not in e["name"] for e in c["env"])
    assert {"name": "DATABASE_URL_FILE", "value": "/var/run/memory/DATABASE_URL"} in c[
        "env"
    ]


def test_every_table_is_granted_to_the_role_requests_run_as():
    """Every request drops to memory_app (schema.sql section 9), so a table it is not granted is a
    500 on whichever route touches it -- measured 2026-10-20: memory_access shipped without one
    and every brief that searched by meaning failed with "permission denied"."""
    import re

    sql = (HERE / "schema.sql").read_text()
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql)
    granted = set()
    for m in re.finditer(r"GRANT [^;]*? ON (?:TABLE )?([\w, ]+?) TO memory_app", sql):
        granted |= {t.strip() for t in m.group(1).split(",")}
    assert tables and not [t for t in tables if t not in granted]
