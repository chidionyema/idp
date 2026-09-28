#!/usr/bin/env python3
"""JudgeDrift control loop: continuous calibration monitoring.

Implements ControlLoop protocol.
Post-verdict hook that monitors judge drift and enqueues calibration tasks.
"""

from platform.eval.protocol import ControlLoop, GateDecision, LoopHealth
from platform.eval.judge_drift import JudgeDriftSentinel, GoldSetCalibrator
from datetime import datetime
import sqlite3
import os


class JudgeDriftLoop(ControlLoop):
    """
    JudgeDrift as a ControlLoop.
    Monitors judge score distribution, enqueues calibration on drift.
    """

    name = "judge_drift"

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("QUEUE_DB_PATH", "state/queue.db")
        self.sentinel = JudgeDriftSentinel(db_path=self.db_path)
        self.calibrator = GoldSetCalibrator(db_path=self.db_path)
        self.last_run_at = None
        self.last_error = None
        self.mode = "shadow"

    def pre_llm(self, state: dict) -> GateDecision:
        """JudgeDrift doesn't gate on pre_llm. Return allow."""
        return GateDecision(action="allow")

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """
        Called after verdict.
        Record judge score, check for drift, enqueue calibration if needed.
        """
        self.last_run_at = datetime.now().isoformat()

        try:
            # Extract judge score if available
            judge_score = verdict.get("judge_score", 0.5)

            # Record verdict and check for drift
            alert = self.sentinel.record_verdict(judge_score)

            if alert and alert.get("alert") == "judge_drift_detected":
                # Drift detected: enqueue calibration task
                self._enqueue_calibration_task(alert)

        except Exception as e:
            self.last_error = str(e)
            raise

    def periodic(self) -> None:
        """
        Periodic maintenance: weekly calibration check.
        Run gold-set kappa computation.
        """
        self.last_run_at = datetime.now().isoformat()

        try:
            calibration_result = self.calibrator.calibrate()

            if calibration_result["status"] == "calibrated":
                kappa = calibration_result["kappa"]
                if kappa < self.calibrator.KAPPA_THRESHOLDS["substantial"]:
                    self.last_error = (
                        f"Kappa below threshold: {kappa}. Judge unreliable."
                    )
                    # In production, trigger alert + escalation

        except Exception as e:
            self.last_error = str(e)

    def health(self) -> LoopHealth:
        """Report loop health."""
        return LoopHealth(
            name=self.name,
            mode=self.mode,
            last_run_at=self.last_run_at or "never",
            last_error=self.last_error or "none",
            is_healthy=self.last_error is None,
        )

    def _enqueue_calibration_task(self, alert: dict) -> None:
        """
        Enqueue a calibration task to the dispatcher queue.
        Uses existing SQLite queue infrastructure.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (goal, status)
                    VALUES (?, 'pending')
                    """,
                    (f"judge_calibration:{alert.get('reason', 'drift')}",),
                )
                conn.commit()
        except Exception:  # noqa: S110
            # Queue may not exist yet; fail silently
            pass
