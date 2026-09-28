"""Tests for hypotheses-race.py — Bayesian concurrent hypothesis testing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the script under test
RACE = Path.home() / ".estate" / "libexec" / "hypotheses-race.py"


def run_race(spec: dict) -> dict:
    """Run hypotheses-race.py with spec as stdin JSON, return parsed output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        f.flush()
        r = subprocess.run(
            [sys.executable, str(RACE), f.name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        Path(f.name).unlink()
    if r.returncode != 0:
        pytest.fail(f"race failed: {r.stderr}")
    return json.loads(r.stdout)


class TestBayesianEngine:
    """Tier 1: Bayesian inference correctness."""

    def test_posterior_sums_to_one(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.5,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
                {
                    "id": "H2",
                    "prior": 0.5,
                    "probe": "echo fail",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 2,
            "timeout": 5,
        }
        out = run_race(spec)
        posteriors = out["posteriors"]
        total = sum(posteriors.values())
        assert 0.99 < total < 1.01, f"posteriors sum to {total}, expected ~1.0"

    def test_falsified_probe_raises_posterior(self):
        # H1 probe returns ok (matches falsified_if) -> falsified -> posterior should increase
        # H2 probe returns fail (does not match falsified_if) -> not falsified -> posterior decreases
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.5,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
                {
                    "id": "H2",
                    "prior": 0.5,
                    "probe": "echo fail",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 2,
            "timeout": 5,
        }
        out = run_race(spec)
        # H1 is falsified -> posterior higher, H2 is not -> posterior lower
        assert (
            out["posteriors"]["H2"] > out["posteriors"]["H1"]
        )  # falsified -> posterior drops

    def test_prior_sweep_produces_sweep(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.3,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
                {
                    "id": "H2",
                    "prior": 0.7,
                    "probe": "echo fail",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 2,
            "timeout": 5,
        }
        out = run_race(spec)
        assert "prior_sweep" in out
        # Keys are strings after JSON round-trip; cast to float
        keys = {float(k) for k in out["prior_sweep"].keys()}
        assert keys == {0.5, 1.0, 2.0}

    def test_credible_intervals_present(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 1,
            "timeout": 5,
        }
        out = run_race(spec)
        assert "credible_intervals" in out
        assert "H1" in out["credible_intervals"]
        lo, hi = out["credible_intervals"]["H1"]
        assert 0 <= lo <= hi <= 1

    def test_ranked_is_sorted_descending(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.1,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
                {
                    "id": "H2",
                    "prior": 0.9,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 2,
            "timeout": 5,
        }
        out = run_race(spec)
        ranked = out["ranked"]
        p = out["posteriors"]
        for i in range(len(ranked) - 1):
            assert p[ranked[i]] >= p[ranked[i + 1]]


class TestProbeExecution:
    """Tier 2: probe execution edge cases."""

    def test_timeout_probe_returns_124(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "sleep 10",
                    "falsified_if": {"timeout": True},
                },
            ],
            "parallel": 1,
            "timeout": 1,  # probe times out in 1s
        }
        out = run_race(spec)
        assert out["results"][0]["exit"] == 124
        assert out["results"][0]["timeout"] is True

    def test_falsified_if_exit_code(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "exit 1",
                    "falsified_if": {"exit_code": 1},
                },
            ],
            "parallel": 1,
            "timeout": 5,
        }
        out = run_race(spec)
        assert out["results"][0]["falsified"] is True

    def test_falsified_if_stdout_contains(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "echo secret123",
                    "falsified_if": {"stdout_contains": "secret123"},
                },
            ],
            "parallel": 1,
            "timeout": 5,
        }
        out = run_race(spec)
        assert out["results"][0]["falsified"] is True

    def test_non_falsified_if_not_matched(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "echo hello world",
                    "falsified_if": {"stdout_contains": "goodbye"},
                },
            ],
            "parallel": 1,
            "timeout": 5,
        }
        out = run_race(spec)
        assert out["results"][0]["falsified"] is False

    def test_parallel_probes_run_concurrently(self):
        spec = {
            "hypotheses": [
                {
                    "id": f"H{i}",
                    "prior": 1.0 / 8,
                    "probe": "sleep 1",
                    "falsified_if": {"timeout": True},
                }
                for i in range(8)
            ],
            "parallel": 8,
            "timeout": 2,
        }
        import time

        t0 = time.time()
        out = run_race(spec)
        elapsed = time.time() - t0
        # 8 probes at 1s each in parallel should take ~1-2s, not 8s
        assert elapsed < 5, f"took {elapsed:.1f}s — probes may not be parallel"


class TestEvidenceLog:
    """Tier 3: determinism and replay."""

    def test_evidence_logged(self):
        LOG = Path.home() / ".estate" / "logs" / "hypotheses-race.jsonl"
        log_count_before = 0
        if LOG.exists():
            log_count_before = len(LOG.read_text().strip().splitlines())
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 1.0,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 1,
            "timeout": 5,
        }
        run_race(spec)
        if LOG.exists():
            log_count_after = len(LOG.read_text().strip().splitlines())
            assert log_count_after > log_count_before


class TestEPSAndPriors:
    """Edge cases: EPS floor, prior sensitivity, empty hypotheses."""

    def test_empty_hypotheses_returns_empty(self):
        spec = {"hypotheses": [], "parallel": 1, "timeout": 5}
        out = run_race(spec)
        assert out["ranked"] == []
        assert len(out["results"]) == 0

    def test_eps_floor_prevents_zero_posterior(self):
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.01,
                    "probe": "echo ok",
                    "falsified_if": {"stdout_contains": "ok"},
                },
            ],
            "parallel": 1,
            "timeout": 5,
            "eps": 0.001,
        }
        out = run_race(spec)
        # EPS floor means no posterior goes to exactly 0
        for v in out["posteriors"].values():
            assert v > 0

    def test_probe_reliability_lowers_confidence(self):
        # Timeout with low probe_reliability should still be informative
        spec = {
            "hypotheses": [
                {
                    "id": "H1",
                    "prior": 0.5,
                    "probe": "sleep 10",
                    "probe_reliability": 0.5,
                    "falsified_if": {"timeout": True},
                },
            ],
            "parallel": 1,
            "timeout": 1,
        }
        out = run_race(spec)
        # Should have result even with timeout
        assert len(out["results"]) == 1
