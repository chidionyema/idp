"""idp#3525 CP5, ORCH-03 (trace-query test).

Binds sovereign/engine/config_experiment.py against the spec's own
ACCEPT line: "run 2 configs, query returns per-config cost/pass/latency
table." No real Langfuse server exists in this sandbox, so the client is
a stub shaped exactly like the real SDK surface confirmed against the
downloaded langfuse==2.53.0 wheel: `client.api.trace.list(tags=...)` ->
object with `.data: list[trace-like]`, each trace-like carrying
`total_cost`, `latency`, `output`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sovereign.engine.config_experiment import query_config_row, query_config_table


@dataclass
class FakeTrace:
    total_cost: float
    latency: float
    output: dict[str, Any]
    tags: list[str] = field(default_factory=list)


@dataclass
class FakeTraces:
    data: list[FakeTrace]


class FakeTraceClient:
    def __init__(self, by_tag: dict[str, list[FakeTrace]]) -> None:
        self._by_tag = by_tag

    def list(self, *, tags: str) -> FakeTraces:
        return FakeTraces(data=self._by_tag.get(tags, []))


class FakeApi:
    def __init__(self, by_tag: dict[str, list[FakeTrace]]) -> None:
        self.trace = FakeTraceClient(by_tag)


class FakeLangfuseClient:
    def __init__(self, by_tag: dict[str, list[FakeTrace]]) -> None:
        self.api = FakeApi(by_tag)


def _client_with_two_configs() -> FakeLangfuseClient:
    return FakeLangfuseClient(
        {
            "config_id:cheap": [
                FakeTrace(total_cost=0.001, latency=0.8, output={"status": "done"}),
                FakeTrace(total_cost=0.002, latency=1.2, output={"status": "done"}),
                FakeTrace(total_cost=0.001, latency=0.9, output={"status": "failed"}),
            ],
            "config_id:frontier": [
                FakeTrace(total_cost=0.5, latency=3.0, output={"status": "done"}),
            ],
        }
    )


def test_query_config_row_computes_cost_pass_rate_and_latency_for_one_config() -> None:
    row = query_config_row(_client_with_two_configs(), "cheap")
    assert row.config_id == "cheap"
    assert row.n == 3
    assert row.cost_usd_total == 0.004
    assert row.pass_rate == 2 / 3
    assert row.latency_avg_s == (0.8 + 1.2 + 0.9) / 3


def test_query_config_table_returns_one_row_per_config_in_order() -> None:
    client = _client_with_two_configs()
    table = query_config_table(client, ["cheap", "frontier"])
    assert [row.config_id for row in table] == ["cheap", "frontier"]
    assert table[0].n == 3
    assert table[1].n == 1
    assert table[1].pass_rate == 1.0


def test_a_config_with_no_traces_yet_reports_n_zero_and_no_rates() -> None:
    row = query_config_row(_client_with_two_configs(), "never-run")
    assert row.n == 0
    assert row.cost_usd_total == 0.0
    assert row.pass_rate is None
    assert row.latency_avg_s is None
