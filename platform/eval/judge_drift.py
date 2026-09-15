#!/usr/bin/env python3
"""Judge drift detection and calibration control loop.

Continuous drift sentinel via Jensen-Shannon divergence.
Periodic gold-set kappa recalibration.
"""

import sqlite3
from collections import deque
from datetime import datetime, timedelta
import numpy as np
from scipy.spatial.distance import jensenshannon


class JudgeDriftSentinel:
    """
    Continuous drift detection. Runs every polling cycle.
    Triggers recalibration task when JS divergence exceeds threshold.
    """

    def __init__(
        self,
        db_path: str,
        baseline_window: int = 500,
        current_window: int = 100,
        js_threshold: float = 0.15,
    ):
        self.db_path = db_path
        self.baseline_scores = None
        self.current_scores = deque(maxlen=current_window)
        self.js_threshold = js_threshold
        self.alert_raised_at = None
        self._load_baseline()

    def _load_baseline(self):
        """Load baseline distribution from first 500 judge verdicts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT score FROM judge_verdicts
                ORDER BY created_at ASC
                LIMIT 500
                """
            )
            scores = [row[0] for row in cursor.fetchall()]
            if scores:
                self.baseline_scores = self._to_distribution(scores)

    def record_verdict(self, score: float) -> dict | None:
        """
        Record a judge verdict score. Check for drift.
        Returns dict with alert if drift detected, else None.
        """
        self.current_scores.append(score)

        if len(self.current_scores) < len(self.current_scores.__class__.__bases__[0]):
            return None

        if self.baseline_scores is None:
            return None

        current_dist = self._to_distribution(list(self.current_scores))
        js_div = jensenshannon(self.baseline_scores, current_dist) ** 2

        if js_div > self.js_threshold:
            if (
                self.alert_raised_at is None
                or datetime.now() - self.alert_raised_at > timedelta(hours=1)
            ):
                self.alert_raised_at = datetime.now()
                return {
                    "alert": "judge_drift_detected",
                    "js_divergence": js_div,
                    "threshold": self.js_threshold,
                    "action": "enqueue calibration task",
                }

        return None

    @staticmethod
    def _to_distribution(scores: list[float]) -> np.ndarray:
        """Convert scores to probability distribution."""
        if not scores:
            return np.array([])
        hist, _ = np.histogram(scores, bins=10, range=(0.0, 1.0))
        return hist / hist.sum()


class GoldSetCalibrator:
    """
    Periodic gold-set recalibration.
    Computes Cohen's kappa against expert-labeled examples.
    """

    KAPPA_THRESHOLDS = {
        "almost_perfect": 0.85,
        "substantial": 0.75,
        "moderate": 0.60,
    }

    def __init__(self, db_path: str, gold_set_size: int = 50):
        self.db_path = db_path
        self.gold_set_size = gold_set_size
        self.current_kappa = None

    def calibrate(self) -> dict:
        """
        Run calibration against gold set.
        Returns dict with kappa, interpretation, action.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT judge_score, human_label
                FROM judge_verdicts_gold_set
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self.gold_set_size,),
            )
            rows = cursor.fetchall()

        if not rows or len(rows) < self.gold_set_size // 2:
            return {
                "status": "insufficient_gold_set",
                "rows_found": len(rows),
                "rows_needed": self.gold_set_size,
            }

        judge_scores = np.array([r[0] for r in rows])
        human_labels = np.array([r[1] for r in rows])

        # Cohen's kappa: agreement corrected for chance
        po = np.mean(judge_scores == human_labels)  # observed agreement
        pe = 0.5  # expected agreement (binary, uniform)
        kappa = (po - pe) / (1 - pe)

        self.current_kappa = kappa

        if kappa >= self.KAPPA_THRESHOLDS["almost_perfect"]:
            interpretation = "almost_perfect"
            action = "trust_verdicts"
        elif kappa >= self.KAPPA_THRESHOLDS["substantial"]:
            interpretation = "substantial"
            action = "trust_verdicts"
        elif kappa >= self.KAPPA_THRESHOLDS["moderate"]:
            interpretation = "moderate"
            action = "flag_for_review"
        else:
            interpretation = "poor"
            action = "halt_judge"

        return {
            "status": "calibrated",
            "kappa": kappa,
            "sample_size": len(rows),
            "interpretation": interpretation,
            "action": action,
            "po": po,
            "pe": pe,
        }

    def is_calibrated(self) -> bool:
        """Check if current kappa is above substantial threshold."""
        return (
            self.current_kappa is not None
            and self.current_kappa >= self.KAPPA_THRESHOLDS["substantial"]
        )
