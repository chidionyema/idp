#!/usr/bin/env python3
"""Judge verification tests: calibration and drift detection.

Exercises the real JudgeWorker and GoldSetCalibrator (platform/eval/judge_worker.py,
platform/eval/judge_drift.py) against a temporary SQLite database, rather than a
MagicMock standing in for behaviour nothing here ever calls.
"""

import os
import sqlite3
import sys
import tempfile
import importlib.util

import pytest


def _load_judge_worker():
    """platform/ has no __init__.py (idp#3564: it collides with the stdlib
    `platform` module the moment anything imports it bare, which pytest itself
    does at startup). Loading platform.eval.judge_worker/judge_drift by file
    path and seeding sys.modules under their real dotted names sidesteps that
    collision: a later `from platform.eval.judge_worker import X` hits the
    sys.modules fast path for the exact dotted name instead of re-resolving
    through the poisoned bare `platform` name."""
    idp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for dotted, rel in [
        ("platform.eval", "platform/eval/__init__.py"),
        ("platform.eval.judge_drift", "platform/eval/judge_drift.py"),
        ("platform.eval.judge_worker", "platform/eval/judge_worker.py"),
    ]:
        if dotted in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            dotted, os.path.join(idp_root, rel)
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)


_load_judge_worker()

from platform.eval.judge_worker import JudgeWorker  # noqa: E402
from platform.eval.judge_drift import GoldSetCalibrator  # noqa: E402


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _seed_gold_set(db_path, agreeing, disagreeing):
    """Insert gold-set rows: `agreeing` pairs where judge_score == human_label,
    `disagreeing` pairs where they differ."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS judge_verdicts_gold_set (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transcript_id TEXT NOT NULL,
                judge_score REAL NOT NULL,
                human_label REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for i in range(agreeing):
            conn.execute(
                "INSERT INTO judge_verdicts_gold_set (transcript_id, judge_score, human_label) VALUES (?, 1.0, 1.0)",
                (f"gold_agree_{i}",),
            )
        for i in range(disagreeing):
            conn.execute(
                "INSERT INTO judge_verdicts_gold_set (transcript_id, judge_score, human_label) VALUES (?, 1.0, 0.0)",
                (f"gold_disagree_{i}",),
            )
        conn.commit()


def _seed_transcript(db_path, transcript_id, span_count=3):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transcript_spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transcript_id TEXT NOT NULL,
                span_id TEXT UNIQUE,
                span_kind TEXT,
                payload TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                exported BOOLEAN DEFAULT FALSE
            )
            """
        )
        for i in range(span_count):
            conn.execute(
                "INSERT INTO transcript_spans (transcript_id, span_id, span_kind, payload) VALUES (?, ?, 'tool_call', ?)",
                (transcript_id, f"{transcript_id}_span_{i}", '{"tool_name": "bash"}'),
            )
        conn.commit()


def test_kappa_above_threshold(db_path):
    """
    Contract for judge: Cohen's kappa must be >= 0.75 (substantial agreement)
    when the gold set shows strong agreement between judge and human.
    """
    _seed_gold_set(db_path, agreeing=50, disagreeing=0)

    calibrator = GoldSetCalibrator(db_path=db_path, gold_set_size=50)
    result = calibrator.calibrate()

    assert result["status"] == "calibrated"
    assert calibrator.current_kappa >= 0.75, (
        f"Judge kappa {calibrator.current_kappa:.3f} below threshold"
    )


def test_kappa_below_threshold_halts_verdict(db_path):
    """
    Contract for judge: If kappa is below the moderate threshold, an evaluated
    verdict must come back with action='halt_judge', not a trusted one.
    """
    # Half agree, half disagree -> po=0.5, kappa=(0.5-0.5)/0.5=0.0, well below threshold
    _seed_gold_set(db_path, agreeing=25, disagreeing=25)
    _seed_transcript(db_path, "t_low_kappa")

    worker = JudgeWorker(db_path=db_path)
    worker.calibrate_on_gold_set()

    verdict = worker.evaluate("t_low_kappa")

    assert verdict.action == "halt_judge", (
        f"Judge should halt below kappa threshold, got action={verdict.action!r}"
    )
    assert verdict.interpretation == "poor"


def test_raw_accuracy_not_misleading(db_path):
    """
    Contract for judge: High raw pass rate can coexist with kappa near 0 if the
    judge passes everything regardless of the human label. Track kappa, not a
    raw pass rate, because the pass rate alone hides that mismatch.
    """
    # judge_score is always 1.0 (judge "passes" every item) while human_label
    # alternates -- the judge is right by luck on half of them, giving kappa 0.
    _seed_gold_set(db_path, agreeing=25, disagreeing=25)

    calibrator = GoldSetCalibrator(db_path=db_path, gold_set_size=50)
    result = calibrator.calibrate()

    raw_pass_rate = 1.0  # the judge scored every single item as passing

    mismatch_detected = raw_pass_rate > 0.8 and calibrator.current_kappa < 0.2
    assert mismatch_detected, (
        f"Judge has raw pass rate {raw_pass_rate:.2f} but kappa "
        f"{calibrator.current_kappa:.3f} was not flagged as a mismatch "
        f"(calibrate() status={result['status']!r})"
    )


def test_judge_exposes_verdict_details(db_path):
    """
    Contract for judge: Verdict must include all scoring components.
    """
    _seed_transcript(db_path, "t_001")

    worker = JudgeWorker(db_path=db_path)
    verdict = worker.evaluate("t_001")

    assert hasattr(verdict, "interpretation")
    assert hasattr(verdict, "action")
    assert hasattr(verdict, "judge_score")
    assert hasattr(verdict, "tool_f1")
    assert hasattr(verdict, "arg_validity")
    assert hasattr(verdict, "result_utilization")
    assert hasattr(verdict, "error_recovery")
