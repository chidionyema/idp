"""Tests for the three remaining forcing-function lint rules."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from idp_concurrency.lint.no_locks import check_file as check_locks
from idp_concurrency.lint.no_unbounded import check_file as check_unbounded
from idp_concurrency.lint.no_untraced import check_file as check_untraced


def _write(tmp_path: Path, name: str, src: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(src))
    return path


# ---------------------------------------------------------------------------
# F2 — no unbounded tasks


def test_unbounded_clean_when_inside_task_group(tmp_path: Path):
    p = _write(
        tmp_path,
        "good.py",
        """\
        import asyncio
        from idp_concurrency.task_scope import task_scope

        async def go():
            async with task_scope() as tg:
                tg.start_soon(asyncio.create_task, _noop())

        async def _noop():
            pass
    """,
    )
    assert check_unbounded(p) == []


def test_unbounded_flags_asyncio_create_task_outside_scope(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        import asyncio

        async def go():
            asyncio.create_task(_noop())          # banned

        async def _noop():
            pass
    """,
    )
    violations = check_unbounded(p)
    assert len(violations) == 1
    assert "Forcing F2" in violations[0][1]


def test_unbounded_flags_gather_outside_scope(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        import asyncio

        async def go():
            await asyncio.gather(_noop())         # banned

        async def _noop():
            pass
    """,
    )
    violations = check_unbounded(p)
    assert any("Forcing F2" in v[1] for v in violations)


def test_unbounded_allows_task_scope_file_itself(tmp_path: Path):
    p = _write(
        tmp_path,
        "task_scope.py",
        """\
        import asyncio
    """,
    )
    assert check_unbounded(p) == []


# ---------------------------------------------------------------------------
# F3 — no untraced I/O


def test_untraced_flags_httpx_import(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        import httpx
    """,
    )
    violations = check_untraced(p)
    assert len(violations) == 1
    assert "Forcing F3" in violations[0][1]


def test_untraced_flags_aiohttp_import(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        from aiohttp import ClientSession
    """,
    )
    violations = check_untraced(p)
    assert len(violations) == 1
    assert "Forcing F3" in violations[0][1]


def test_untraced_flags_requests_import(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        import requests as r
    """,
    )
    violations = check_untraced(p)
    assert len(violations) == 1


def test_untraced_allows_traced_client_file_itself(tmp_path: Path):
    p = _write(
        tmp_path,
        "tracer.py",
        """\
        import httpx                # allowed inside the wrapper
    """,
    )
    assert check_untraced(p) == []


def test_untraced_allows_unrelated_imports(tmp_path: Path):
    p = _write(
        tmp_path,
        "good.py",
        """\
        import os
        import json
        from pathlib import Path
    """,
    )
    assert check_untraced(p) == []


# ---------------------------------------------------------------------------
# F4 — protocol coordination needs a TLA+ spec


def test_no_ad_hoc_violation_when_specs_missing(tmp_path: Path):
    src_dir = tmp_path / "src" / "pkg"
    src_dir.mkdir(parents=True)
    (src_dir / "coordinator.py").write_text("from idp_concurrency.crdt_doc import ORSet\n")
    from idp_concurrency.lint.no_ad_hoc import check_tree

    violations = check_tree(tmp_path / "src")
    assert len(violations) == 1
    assert "Forcing F4" in violations[0][1]


def test_no_ad_hoc_passes_when_specs_present(tmp_path: Path):
    src_dir = tmp_path / "src" / "pkg"
    specs_dir = src_dir / "specs"
    specs_dir.mkdir(parents=True)
    (src_dir / "coordinator.py").write_text("from idp_concurrency.crdt_doc import ORSet\n")
    (specs_dir / "coordinator.tla").write_text("---- MODULE coordinator ----\n====\n")
    from idp_concurrency.lint.no_ad_hoc import check_tree

    violations = check_tree(tmp_path / "src")
    assert violations == []


def test_no_ad_hoc_skips_idp_concurrency_itself(tmp_path: Path):
    """The idp_concurrency package and its tests don't need sibling specs."""
    src_dir = tmp_path / "src" / "idp_concurrency"
    src_dir.mkdir(parents=True)
    (src_dir / "anything.py").write_text("from idp_concurrency.crdt_doc import ORSet\n")
    from idp_concurrency.lint.no_ad_hoc import check_tree

    violations = check_tree(tmp_path / "src")
    assert violations == []


# ---------------------------------------------------------------------------
# F1 — no locks (sanity)


def test_locks_still_works(tmp_path: Path):
    p = _write(
        tmp_path,
        "bad.py",
        """\
        from threading import Lock
    """,
    )
    violations = check_locks(p)
    assert any("Forcing F1" in v[1] for v in violations)
