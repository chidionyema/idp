"""Regression: a request's transaction must be committed before the pool reclaims the conn.

The pool runs with autocommit=False, so authenticate_surface's tenant SELECT leaves an
implicit transaction open after its rate-limit commit, and a handler's
`async with conn.transaction()` is only a savepoint inside it. psycopg_pool rolls a
connection back on release, so before the fix every INSERT was silently discarded while
the handler still returned 200 CREATED (seen in production 2026-10-18: PUT -> CREATED,
count(*) 0).

The test loads the real get_db_conn source out of main.py (ast, so it grades the shipped
code rather than a copy) and pins the contract: resumed after the handler, it commits,
and only then releases the connection back to the pool. It deliberately does not import
main.py: the module needs fastapi/psycopg and Python 3.12 union syntax, and the contract
under test lives in this one function.
"""

# ruff: noqa: S102 -- the exec below compiles this repo's own main.py source, never user
# input. It is file-level because python-strict passes --per-file-ignores on its command
# line, which replaces this repo's pyproject exemptions, and ruff format rewraps a long
# call so a trailing same-line noqa lands on the wrong line.

from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


def _load_get_db_conn(pool):
    """Compile get_db_conn out of main.py and return it bound to the given pool."""
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_db_conn":
            namespace = {"pool": pool}
            exec(
                compile(ast.Module(body=[node], type_ignores=[]), str(MAIN_PY), "exec"),
                namespace,
            )
            return namespace["get_db_conn"]
    raise AssertionError(
        "main.py no longer defines get_db_conn; rewrite this test against whatever "
        "dependency now injects the database connection"
    )


class FakeConn:
    def __init__(self, order: list):
        self.order = order
        self.committed = False

    async def commit(self):
        self.committed = True
        self.order.append("commit")


class FakePool:
    """Stands in for psycopg_pool: `connection()` releases (and rolls back) on exit."""

    def __init__(self):
        self.order: list = []
        self.conn = FakeConn(self.order)
        self.released = False

    @asynccontextmanager
    async def connection(self):
        try:
            yield self.conn
        finally:
            self.order.append("release")
            self.released = True


@pytest.mark.parametrize("handler_raises", [False, True])
def test_get_db_conn_contract(handler_raises):
    pool = FakePool()
    get_db_conn = _load_get_db_conn(pool)

    async def scenario():
        agen = get_db_conn()
        conn = await agen.__anext__()
        assert conn is pool.conn

        if handler_raises:
            # A failed request (a guard's HTTPException, a route bug) propagates through
            # the yield: the teardown commit must NOT run, so no partial write of a failed
            # request is ever committed. The pool's release rollback returns the
            # connection clean -- that is what a failed request should do.
            with pytest.raises(RuntimeError):
                await agen.athrow(RuntimeError("guard refused the write"))
        else:
            with pytest.raises(StopAsyncIteration):
                await agen.asend(None)

    asyncio.run(scenario())

    assert pool.released
    if handler_raises:
        assert not pool.conn.committed, (
            "a failed request must not be committed: its transaction is aborted and any "
            "partial write belongs in the pool's release rollback"
        )
        assert pool.order == ["release"]
    else:
        assert pool.conn.committed, (
            "get_db_conn must commit the request's transaction: with autocommit=False the "
            "handler's writes sit in an implicit transaction the pool rolls back on release"
        )
        assert pool.order == ["commit", "release"], (
            "commit must land before the pool reclaims the connection, not never"
        )
