"""Incident test, crew#474 (2026-08-27): Dagster com.estate.catalog-render ran $IDP/bin/catalog-render
from the shared checkout, which a peer had left on feat/crew290. That copy had no estate-showcase
step, so docs/SHOWCASE.md stayed at the old grader's counts while its own worktree sat on main.
Rule: a driver whose bytes differ from the origin/main worktree's copy is stale and hands over;
the worktree's own copy, or an identical copy, is not.
"""
import importlib.util
import pathlib
from importlib.machinery import SourceFileLoader

_p = pathlib.Path(__file__).resolve().parents[1] / "bin" / "catalog-render"
_spec = importlib.util.spec_from_file_location("catalog_render", _p, loader=SourceFileLoader("catalog_render", str(_p)))
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


def test_incident_crew474_stale_driver_is_detected_and_current_driver_is_not(tmp_path):
    on_main = tmp_path / "wt" / "bin" / "catalog-render"
    on_main.parent.mkdir(parents=True)
    on_main.write_text("print('with showcase step')\n")
    stale = tmp_path / "checkout" / "bin" / "catalog-render"
    stale.parent.mkdir(parents=True)
    stale.write_text("print('without showcase step')\n")
    assert cr.driver_is_stale(stale, on_main) is True
    same = tmp_path / "other" / "catalog-render"
    same.parent.mkdir()
    same.write_text(on_main.read_text())
    assert cr.driver_is_stale(same, on_main) is False
    assert cr.driver_is_stale(on_main, on_main) is False
    assert cr.driver_is_stale(stale, tmp_path / "missing") is False, "no worktree copy: run what we have, never crash"


def test_incident_crew474_only_the_scheduled_run_hands_over(tmp_path):
    on_main = tmp_path / "wt" / "catalog-render"
    on_main.parent.mkdir()
    on_main.write_text("main\n")
    branch = tmp_path / "branch" / "catalog-render"
    branch.parent.mkdir()
    branch.write_text("branch edit of the driver\n")
    assert cr.should_hand_over(branch, on_main, ["--scheduled"], {}) is True
    assert cr.should_hand_over(branch, on_main, [], {}) is False, "a PR editing the driver runs its own copy"
    assert cr.should_hand_over(branch, on_main, ["--scheduled"], {"CATALOG_RENDER_REEXEC": "1"}) is False, "never loops"
    assert cr.should_hand_over(on_main, on_main, ["--scheduled"], {}) is False
