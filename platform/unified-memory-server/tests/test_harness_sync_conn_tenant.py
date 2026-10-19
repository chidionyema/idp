"""Regression: harness route conns must run under the caller's tenant (RLS GUC).

The harness tables are FORCE ROW LEVEL SECURITY with
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
(schema.sql), and a policy with USING alone is also the INSERT's WITH CHECK. A bare
psycopg.connect never sets app.tenant_id, so current_setting returns NULL and every
write is rejected: seen in production 2026-10-19 as POST /harness/memory/consolidate
-> 500, psycopg.errors.InsufficientPrivilege on preference_recurrence, while
GET /harness/stats (no writes) served 200 on the same image.

The test loads the real _harness_sync_conn source out of main.py (ast, so it grades
the shipped code rather than a copy) and pins the contract: with a tenant it sets
app.tenant_id transaction-locally as the connection's first statement; without one
it touches nothing. It also pins that every call site passes its tenant -- a future
route must not be able to reintroduce the bare conn. It deliberately does not import
main.py: the module needs fastapi/psycopg and Python 3.12 union syntax.
"""

# ruff: noqa: S102 -- the exec below compiles this repo's own main.py source, never user
# input. It is file-level because python-strict passes --per-file-ignores on its command
# line, which replaces this repo's pyproject exemptions, and ruff format rewraps a long
# call so a trailing same-line noqa lands on the wrong line.

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

import pytest

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


class _FakeCursor:
    def __init__(self, log):
        self._log = log

    def execute(self, sql, args=None):
        self._log.append((sql, args))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, log):
        self._log = log

    def cursor(self):
        return _FakeCursor(self._log)


def _load_harness_sync_conn(psycopg_connect):
    """Compile _harness_sync_conn out of main.py, bound to the given connect callable."""
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = psycopg_connect
    fake_psycopg.extras = types.SimpleNamespace()
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_harness_sync_conn":
            namespace = {
                "psycopg": fake_psycopg,
                "Optional": None,
                "DATABASE_URL": "postgresql://fake",
                "dict_row": None,
            }
            exec(  # noqa: S102
                ast.get_source_segment(MAIN_PY.read_text(), node), namespace
            )
            return namespace["_harness_sync_conn"]
    pytest.fail("_harness_sync_conn not found in main.py")


def test_with_a_tenant_the_first_statement_sets_the_rls_guc():
    log = []

    def connect(url, row_factory=None):
        log.append(("connect", url))
        return _FakeConn(log)

    fn = _load_harness_sync_conn(connect)
    conn = fn("0f1e-tenant")
    assert conn is not None and log[0][0] == "connect"
    sql, args = log[1]
    assert "set_config" in sql and "app.tenant_id" in sql
    assert args == ("0f1e-tenant",)
    assert "true" in sql  # transaction-local (third arg true), not session-wide


def test_without_a_tenant_it_sets_nothing():
    log = []

    def connect(url, row_factory=None):
        log.append(("connect", url))
        return _FakeConn(log)

    fn = _load_harness_sync_conn(connect)
    assert fn() is not None
    assert len(log) == 1 and log[0][0] == "connect"


def test_every_call_site_passes_its_tenant():
    """A future route must not reintroduce the bare conn that RLS rejects."""
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_harness_sync_conn"
    ]
    assert len(calls) == 3  # prefetch, consolidate, scratchpad
    bare = [n for n in calls if not n.args]
    assert not bare, f"bare _harness_sync_conn() at line {[n.lineno for n in bare]}"


def test_the_def_takes_an_optional_tenant():
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_harness_sync_conn":
            assert len(node.args.args) == 1
            assert node.args.defaults, "tenant must default to None"
            return
    pytest.fail("_harness_sync_conn not found in main.py")
