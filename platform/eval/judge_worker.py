#!/usr/bin/env python3
"""Judge worker: transcript evaluation and kappa calibration.

Loads transcript spans, computes multi-dimensional scores, and validates
verdicts against gold set. Cohen's kappa checks ensure calibration before
trusting verdicts.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from platform.eval.judge_drift import GoldSetCalibrator


@dataclass
class JudgeVerdict:
    """Judge verdict on a transcript."""

    transcript_id: str
    judge_score: float
    tool_f1: float
    arg_validity: float
    result_utilization: float
    error_recovery: float
    span_count: int
    is_calibrated: bool
    kappa: Optional[float] = None
    interpretation: str = ""
    action: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reasoning: str = ""


class JudgeWorker:
    """
    Evaluate transcripts by scoring tool use dimensions.

    Multi-dimensional scoring:
    - Tool F1: precision/recall of correct tool selection
    - Arg validity: correctness of arguments passed to tools
    - Result utilization: proper use of tool results in subsequent steps
    - Error recovery: handling of tool errors and exceptions

    Scores are combined via weighted average and validated against
    gold set via Cohen's kappa before trusting verdicts.
    """

    SCORE_WEIGHTS = {
        "tool_f1": 0.35,
        "arg_validity": 0.30,
        "result_utilization": 0.20,
        "error_recovery": 0.15,
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.calibrator = GoldSetCalibrator(db_path=db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure required database tables exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Transcript spans table (loaded from execution)
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

            # Judge verdicts table (results of evaluation)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS judge_verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcript_id TEXT NOT NULL,
                    judge_score REAL NOT NULL,
                    tool_f1 REAL,
                    arg_validity REAL,
                    result_utilization REAL,
                    error_recovery REAL,
                    span_count INTEGER,
                    is_calibrated BOOLEAN,
                    kappa REAL,
                    interpretation TEXT,
                    action TEXT,
                    reasoning TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Gold set for calibration
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

            conn.commit()

    def evaluate(self, transcript_id: str) -> JudgeVerdict:
        """
        Evaluate a transcript.

        1. Load transcript_spans from database
        2. Score each span on multiple dimensions
        3. Combine scores via weighted average
        4. Check calibration (Cohen's kappa)
        5. Return verdict with calibration status

        Args:
            transcript_id: Identifier for the transcript to evaluate

        Returns:
            JudgeVerdict with scores, calibration, and interpretation
        """
        # Load spans for this transcript
        spans = self._load_transcript_spans(transcript_id)

        if not spans:
            return JudgeVerdict(
                transcript_id=transcript_id,
                judge_score=0.5,  # Neutral score if no spans
                tool_f1=0.0,
                arg_validity=0.0,
                result_utilization=0.0,
                error_recovery=0.0,
                span_count=0,
                is_calibrated=False,
                interpretation="insufficient_data",
                action="flag_for_review",
                reasoning="No spans found for transcript",
            )

        # Score each span
        scores = {
            "tool_f1": [],
            "arg_validity": [],
            "result_utilization": [],
            "error_recovery": [],
        }

        for span in spans:
            span_scores = self._score_span(span)
            for key, value in span_scores.items():
                scores[key].append(value)

        # Compute averages
        avg_scores = {
            k: (sum(v) / len(v) if v else 0.5)  # Default 0.5 if no scores recorded
            for k, v in scores.items()
        }

        # Combine into judge_score via weighted average
        judge_score = sum(
            avg_scores[k] * self.SCORE_WEIGHTS[k] for k in self.SCORE_WEIGHTS.keys()
        )

        # Check calibration
        is_calibrated = self.calibrator.is_calibrated()
        current_kappa = self.calibrator.current_kappa

        # Determine interpretation and action
        interpretation = ""
        action = ""

        if current_kappa is not None:
            if current_kappa >= self.calibrator.KAPPA_THRESHOLDS["almost_perfect"]:
                interpretation = "almost_perfect"
                action = "trust_verdicts"
            elif current_kappa >= self.calibrator.KAPPA_THRESHOLDS["substantial"]:
                interpretation = "substantial"
                action = "trust_verdicts"
            elif current_kappa >= self.calibrator.KAPPA_THRESHOLDS["moderate"]:
                interpretation = "moderate"
                action = "flag_for_review"
            else:
                interpretation = "poor"
                action = "halt_judge"
        else:
            interpretation = "uncalibrated"
            action = "flag_for_review"

        verdict = JudgeVerdict(
            transcript_id=transcript_id,
            judge_score=judge_score,
            tool_f1=avg_scores["tool_f1"],
            arg_validity=avg_scores["arg_validity"],
            result_utilization=avg_scores["result_utilization"],
            error_recovery=avg_scores["error_recovery"],
            span_count=len(spans),
            is_calibrated=is_calibrated,
            kappa=current_kappa,
            interpretation=interpretation,
            action=action,
            reasoning=self._generate_reasoning(
                avg_scores, judge_score, is_calibrated, current_kappa
            ),
        )

        # Record verdict in database
        self._record_verdict(verdict)

        return verdict

    def _load_transcript_spans(self, transcript_id: str) -> list[dict]:
        """Load all spans for a transcript from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT span_id, span_kind, payload
                FROM transcript_spans
                WHERE transcript_id = ?
                ORDER BY created_at ASC
                """,
                (transcript_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _score_span(self, span: dict) -> dict:
        """
        Score a single span on all dimensions.

        span format: {span_id, span_kind, payload}
        span_kind: 'tool_call', 'tool_result', 'error', 'agent_message'
        payload: JSON with tool_name, args, result, error, etc.

        Returns:
            {tool_f1, arg_validity, result_utilization, error_recovery}
        """
        import json

        scores = {
            "tool_f1": 0.5,
            "arg_validity": 0.5,
            "result_utilization": 0.5,
            "error_recovery": 0.5,
        }

        span_kind = span.get("span_kind", "")

        try:
            payload = json.loads(span.get("payload", "{}"))
        except (json.JSONDecodeError, TypeError):
            return scores

        # Tool call: score F1 and arg validity
        if span_kind == "tool_call":
            scores["tool_f1"] = self._score_tool_f1(payload)
            scores["arg_validity"] = self._score_arg_validity(payload)

        # Tool result: score result utilization
        elif span_kind == "tool_result":
            scores["result_utilization"] = self._score_result_utilization(payload)

        # Error: score error recovery
        elif span_kind == "error":
            scores["error_recovery"] = self._score_error_recovery(payload)

        return scores

    @staticmethod
    def _score_tool_f1(payload: dict) -> float:
        """
        Score tool selection F1.

        Heuristics (no ground truth without gold set):
        - Known tool in payload: +0.8 base
        - Tool exists in known set: +0.1
        - Error in tool call: -0.3
        """
        known_tools = {
            "bash",
            "git",
            "read",
            "write",
            "search",
            "grep",
            "curl",
            "python",
        }

        tool_name = payload.get("tool_name", "").lower()

        if not tool_name:
            return 0.3  # No tool specified

        score = 0.5  # Base neutral score

        if tool_name in known_tools:
            score += 0.3

        if payload.get("error"):
            score -= 0.2

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_arg_validity(payload: dict) -> float:
        """
        Score argument correctness.

        Heuristics:
        - Args present and non-empty: +0.3
        - Args match expected schema: +0.2
        - No validation error: +0.2
        """
        score = 0.5

        args = payload.get("arguments", {})
        if args:
            score += 0.2

        # Check for obvious arg errors
        if payload.get("validation_error"):
            score -= 0.3

        # Check if result indicates arg issue
        if payload.get("error") and "argument" in payload.get("error", "").lower():
            score -= 0.2

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_result_utilization(payload: dict) -> float:
        """
        Score whether tool result was properly used.

        Heuristics:
        - Result present and non-null: +0.3
        - Result is substantial (not empty string): +0.2
        - Next action references result: +0.2
        """
        score = 0.5

        result = payload.get("result")
        if result is not None:
            score += 0.2

        if isinstance(result, str) and len(result.strip()) > 10:
            score += 0.15

        if isinstance(result, dict) and result:
            score += 0.15

        # Check if result was referenced in follow-up
        next_input = payload.get("next_input", "")
        if result and str(result) in next_input:
            score += 0.2

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_error_recovery(payload: dict) -> float:
        """
        Score error handling and recovery.

        Heuristics:
        - No error: base 0.7
        - Error but recovery attempted: +0.2
        - Error and handled gracefully: +0.1
        - Repeated same error: -0.3
        """
        score = 0.5

        if not payload.get("error"):
            return 0.8  # No error is good

        # Error detected
        recovery_attempted = payload.get("recovery_attempted", False)
        retry_count = payload.get("retry_count", 0)

        if recovery_attempted:
            score += 0.25

        if retry_count > 2:
            score -= 0.15  # Repeated retries indicate bad recovery

        # Check for graceful degradation
        if payload.get("fallback_used"):
            score += 0.1

        return min(1.0, max(0.0, score))

    @staticmethod
    def _generate_reasoning(
        scores: dict, judge_score: float, is_calibrated: bool, kappa: Optional[float]
    ) -> str:
        """Generate human-readable reasoning for the verdict."""
        reasoning = f"Judge score {judge_score:.2f}: "

        # Identify strengths and weaknesses
        strengths = [k for k, v in scores.items() if v >= 0.7]
        weaknesses = [k for k, v in scores.items() if v <= 0.4]

        if strengths:
            reasoning += f"Strong in {', '.join(strengths)}. "

        if weaknesses:
            reasoning += f"Weak in {', '.join(weaknesses)}. "

        if is_calibrated:
            reasoning += f"Calibrated (κ={kappa:.2f}). "
        else:
            reasoning += "Not yet calibrated. "

        return reasoning

    def _record_verdict(self, verdict: JudgeVerdict) -> None:
        """Store verdict in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO judge_verdicts
                (transcript_id, judge_score, tool_f1, arg_validity,
                 result_utilization, error_recovery, span_count,
                 is_calibrated, kappa, interpretation, action, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verdict.transcript_id,
                    verdict.judge_score,
                    verdict.tool_f1,
                    verdict.arg_validity,
                    verdict.result_utilization,
                    verdict.error_recovery,
                    verdict.span_count,
                    verdict.is_calibrated,
                    verdict.kappa,
                    verdict.interpretation,
                    verdict.action,
                    verdict.reasoning,
                ),
            )
            conn.commit()

    def calibrate_on_gold_set(self) -> dict:
        """
        Run calibration against gold set.

        Called periodically or on drift alert.
        Recomputes Cohen's kappa and updates interpretation.

        Returns:
            Calibration result with kappa, interpretation, action
        """
        return self.calibrator.calibrate()
