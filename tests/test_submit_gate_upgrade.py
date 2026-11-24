"""Stage 2 submit-gate upgrade falsifiers (I-8455, tests 09-12): hygiene
normalization, evidence-carrying failure comments, 2-strike circuit breaker."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greenlane.submit_gate_upgrade import (  # noqa: E402
    SubmitCircuitBreaker,
    build_failure_comment,
    fingerprint_failure,
    normalize_python_files,
    sanitize_ascii,
)


class TestStage2SubmitGateUpgrade(unittest.TestCase):
    def test_09_ascii_normalizer_repairs_smart_quotes_and_arrows(self) -> None:
        dirty = "x = \u201chello\u201d  # a \u2192 b\n"
        self.assertEqual(sanitize_ascii(dirty), 'x = "hello"  # a -> b\n')

    def test_10_normalize_python_files_cleans_non_ascii_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.py"
            p.write_text("# dash \u2014 ok\nx = 1\n", encoding="utf-8")
            res = normalize_python_files([p], run_ruff=False)
            self.assertTrue(res["ok"])
            self.assertEqual(len(res["ascii_normalized"]), 1)
            self.assertTrue(all(b < 128 for b in p.read_bytes()))

    def test_11_failure_comment_inlines_annotation_and_redacts_secrets(self) -> None:
        log = (
            "line 1\n"
            "Authorization: Bearer topsecret999999\n"
            "AssertionError: expected 200 got 525\n"
        )
        comment = build_failure_comment(
            branch="submit/7790-test",
            owner="chatgpt-web",
            head_sha="b11a0b0",
            run_url="https://github.com/chidionyema/idp/actions/runs/45333935030",
            failing_job="fast-gate",
            failing_step="pytest",
            annotation="AssertionError: expected 200 got 525",
            raw_log=log,
        )
        self.assertIn("AssertionError: expected 200 got 525", comment)
        self.assertNotIn("topsecret999999", comment)
        self.assertIn("[REDACTED]", comment)

    def test_12_circuit_breaker_trips_on_second_identical_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cb = SubmitCircuitBreaker(Path(tmp) / "breaker.json")
            fp = fingerprint_failure(
                "fast-gate",
                "E501 line too long",
                ["runs/111/job/222 failed"],
            )
            fp2 = fingerprint_failure(
                "fast-gate",
                "E501 line too long",
                ["runs/999/job/888 failed"],
            )
            self.assertEqual(fp, fp2)
            d1 = cb.record_failure("7790", "chatgpt-web", fp)
            self.assertFalse(d1.tripped)
            d2 = cb.record_failure("7790", "chatgpt-web", fp2)
            self.assertTrue(d2.tripped)
            self.assertTrue(cb.is_blocked("7790", "chatgpt-web"))
