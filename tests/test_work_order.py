"""Falsifiers for bin/work-order: it must refuse what it should and do exactly what the order says."""

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader(
    "work_order", str(ROOT / "bin" / "work-order")
)
_s = importlib.util.spec_from_loader("work_order", _l)
wo = importlib.util.module_from_spec(_s)
_l.exec_module(wo)


def g(cwd, *a):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def world(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    g(src, "init", "-q", "-b", "main")
    (src / "a.txt").write_text("one\n")
    g(src, "add", "-A")
    g(src, "commit", "-q", "-m", "base")
    base = g(src, "rev-parse", "HEAD")
    g(src, "checkout", "-q", "-b", "work")
    (src / "a.txt").write_text("one\ntwo\n")
    (src / "ok.py").write_text("import sys\nsys.exit(0)\n")
    g(src, "add", "-A")
    g(src, "commit", "-q", "-m", "work")
    return tmp_path, src, base


def make_order(src, base, tmp, checks=("python3 ok.py",), out="order"):
    args = [
        "make",
        "--id",
        "t1",
        "--claim",
        "o/r#1",
        "--agent",
        "a",
        "--base",
        base,
        "--head",
        "work",
        "--out",
        str(tmp / out),
    ]
    for c in checks:
        args += ["--check", c]
    cwd = str(src)
    import os

    old = os.getcwd()
    os.chdir(cwd)
    try:
        assert wo.main(["work-order", *args]) == 0
    finally:
        os.chdir(old)
    return tmp / out


def fresh(tmp, base, src):
    dst = tmp / "dst"
    subprocess.run(["git", "clone", "-q", str(src), str(dst)], check=True)
    g(dst, "checkout", "-q", base)
    return dst


def test_dry_run_changes_nothing_and_apply_lands_on_the_lane(world):
    tmp, src, base = world
    order = make_order(src, base, tmp)
    dst = fresh(tmp, base, src)
    assert wo.main(["work-order", "run", str(order), "--repo", str(dst)]) == 0
    assert (dst / "a.txt").read_text() == "one\n"
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(dst), "--apply"]) == 0
    )
    assert g(dst, "branch", "--show-current") == "lane/t1"
    assert "Claim: o/r#1" in g(dst, "log", "-1", "--format=%B")


def test_tampered_patch_is_refused(world):
    tmp, src, base = world
    order = make_order(src, base, tmp)
    (order / "change.patch").write_text((order / "change.patch").read_text() + "\n")
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(fresh(tmp, base, src))])
        == 2
    )


def test_path_outside_the_order_is_refused(world):
    tmp, src, base = world
    order = make_order(src, base, tmp)
    o = json.loads((order / "order.json").read_text())
    o["paths"] = ["a.txt"]
    (order / "order.json").write_text(json.dumps(o))
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(fresh(tmp, base, src))])
        == 2
    )


def test_forbidden_path_is_refused(world):
    tmp, src, base = world
    g(src, "checkout", "-q", "work")
    (src / ".github").mkdir()
    (src / ".github" / "w.yml").write_text("x: 1\n")
    g(src, "add", "-A")
    g(src, "commit", "-q", "-m", "wf")
    order = make_order(src, base, tmp, out="o2")
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(fresh(tmp, base, src))])
        == 2
    )


def test_a_shell_string_check_is_refused(world):
    tmp, src, base = world
    order = make_order(src, base, tmp, checks=("rm -rf x",))
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(fresh(tmp, base, src))])
        == 2
    )


def test_failed_check_rolls_back_and_exits_3(world):
    tmp, src, base = world
    (src / "ok.py").write_text("import sys\nsys.exit(1)\n")
    g(src, "add", "-A")
    g(src, "commit", "-q", "-m", "fail")
    order = make_order(src, base, tmp, out="o3")
    dst = fresh(tmp, base, src)
    assert (
        wo.main(["work-order", "run", str(order), "--repo", str(dst), "--apply"]) == 3
    )
    assert (dst / "a.txt").read_text() == "one\n" and not (dst / "ok.py").exists()


def test_patch_that_no_longer_applies_is_refused(world):
    tmp, src, base = world
    order = make_order(src, base, tmp)
    dst = fresh(tmp, base, src)
    (dst / "a.txt").write_text("changed\n")
    assert wo.main(["work-order", "run", str(order), "--repo", str(dst)]) == 2
