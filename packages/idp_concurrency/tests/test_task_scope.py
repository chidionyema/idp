"""Real tests for task_scope.task_scope."""

from __future__ import annotations

import sys
import anyio
import pytest

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup  # noqa: F401

from idp_concurrency.task_scope import task_scope


@pytest.mark.asyncio
async def test_all_tasks_run_to_completion():
    results: list[int] = []

    async def work(i: int) -> None:
        await anyio.sleep(0)
        results.append(i)

    async with task_scope() as tg:
        for i in range(10):
            tg.start_soon(work, i)

    assert sorted(results) == list(range(10))


@pytest.mark.asyncio
async def test_exception_in_one_task_cancels_siblings():
    cancelled: list[int] = []

    async def slow(i: int) -> None:
        try:
            await anyio.sleep(1.0)
        except BaseException:
            cancelled.append(i)
            raise

    async def boom() -> None:
        raise RuntimeError("nope")

    with pytest.raises(BaseExceptionGroup):
        async with task_scope() as tg:
            for i in range(5):
                tg.start_soon(slow, i)
            tg.start_soon(boom)

    assert sorted(cancelled) == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_scope_returns_a_task_group():
    async with task_scope() as tg:
        assert hasattr(tg, "start_soon")
        assert hasattr(tg, "start")
