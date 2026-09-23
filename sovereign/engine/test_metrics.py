"""unittest for sovereign/engine/metrics.py. Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_metrics -v

Both ways, per DoD v3 (verified, not asserted): (1) unconfigured -- no
OTEL_EXPORTER_OTLP_ENDPOINT -- every public function is a real no-op, proved
by patching config so configured() is False and asserting no meter is ever
built. (2) configured -- a real opentelemetry InMemoryMetricReader is wired
in place of the module's own PeriodicExportingMetricReader/OTLPMetricExporter
(no network), and the actual recorded values are read back and asserted,
not merely "did not raise".
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from sovereign import config
from sovereign.engine import metrics


class _ResetMeterState(unittest.TestCase):
    def setUp(self) -> None:
        metrics._meter = None
        metrics._instruments = {}
        metrics._warned = False
        self.addCleanup(self._reset)

    def _reset(self) -> None:
        metrics._meter = None
        metrics._instruments = {}
        metrics._warned = False


class UnconfiguredIsANoOpTest(_ResetMeterState):
    def test_every_public_function_no_ops_and_never_raises(self) -> None:
        with patch.object(config, "OTEL_EXPORTER_OTLP_ENDPOINT", None):
            metrics.turn("claude", "terminal")
            metrics.turn_duration("claude", 1.5)
            metrics.wall_clock("claude", 1.5)
            metrics.tokens("claude", 42)
        # No instrument was ever created -- proves this is a real no-op,
        # not a call that happened to swallow an exception.
        self.assertEqual(metrics._instruments, {})


class ConfiguredRecordsRealValuesTest(_ResetMeterState):
    def setUp(self) -> None:
        super().setUp()
        # Built and bound directly off this test's own provider, never
        # through the global opentelemetry.metrics API -- that registry
        # accepts set_meter_provider() exactly once per process, so a
        # second test's call would silently no-op and every later test
        # would keep reading the first test's meter/reader.
        self.reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[self.reader])
        self.meter = provider.get_meter("sovereign.engine.test")
        p = patch.object(metrics, "_get_meter", lambda: self.meter)
        p.start()
        self.addCleanup(p.stop)

    def _collected(self) -> dict[str, list]:
        data = self.reader.get_metrics_data()
        out: dict[str, list] = {}
        if data is None:
            return out
        for rm in data.resource_metrics:
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    out.setdefault(m.name, []).extend(m.data.data_points)
        return out

    def test_turn_records_one_count_with_runner_and_status_labels(self) -> None:
        metrics.turn("claude", "terminal")
        points = self._collected()["agent_turn_total"]
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].value, 1)
        self.assertEqual(points[0].attributes["runner"], "claude")
        self.assertEqual(points[0].attributes["status"], "terminal")

    def test_turn_duration_records_the_real_elapsed_seconds(self) -> None:
        metrics.turn_duration("claude", 2.75)
        points = self._collected()["agent_turn_duration_seconds"]
        self.assertEqual(points[0].sum, 2.75)

    def test_wall_clock_accumulates_across_calls(self) -> None:
        metrics.wall_clock("claude", 1.0)
        metrics.wall_clock("claude", 2.0)
        points = self._collected()["agent_wall_clock_seconds"]
        self.assertEqual(points[0].value, 3.0)

    def test_tokens_records_the_real_count(self) -> None:
        metrics.tokens("claude", 123)
        points = self._collected()["agent_tokens_total"]
        self.assertEqual(points[0].value, 123)

    def test_negative_duration_and_tokens_are_clamped_not_rejected(self) -> None:
        # A clock skew or a bad estimate must not crash a step; the metric
        # floors at zero rather than raising or recording a negative value
        # a downstream dashboard would render nonsensically.
        metrics.turn_duration("claude", -5.0)
        metrics.tokens("claude", -5)
        self.assertEqual(self._collected()["agent_turn_duration_seconds"][0].sum, 0.0)
        self.assertEqual(self._collected()["agent_tokens_total"][0].value, 0)


if __name__ == "__main__":
    unittest.main()
