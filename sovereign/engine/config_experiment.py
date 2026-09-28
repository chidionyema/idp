"""Per-config experiment table over existing Langfuse traces (idp#3525
CP5, ORCH-03).

"Every routed call SHALL carry a config_id tag; experiment results SHALL
be answerable as a Langfuse query over existing traces. No new
dashboard." ACCEPT: run 2 configs, query returns per-config cost/pass/
latency table. METHOD: trace-query test.

query_config_table() is that query. It filters the same traces
sovereign.engine.tracing.trace_session() already writes -- tagged
f"config_id:{config_id}" when a caller passes config_id -- using
Langfuse's own tags= containment filter (confirmed against the real
langfuse==2.53.0 SDK: TraceClient.list(tags=...) issues GET
api/public/traces with all listed tags required present). No new store,
no new dashboard: one query, per THE HEADLINE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DONE_STATUS = "done"


@dataclass(frozen=True)
class ConfigRow:
    config_id: str
    n: int
    cost_usd_total: float
    pass_rate: float | None
    latency_avg_s: float | None


def _trace_status(trace: Any) -> str:
    output = getattr(trace, "output", None)
    if not isinstance(output, dict):
        return ""
    return str(output.get("status", ""))


def query_config_row(client: Any, config_id: str) -> ConfigRow:
    """One config's row. `client` is anything shaped like the real
    Langfuse SDK client: `client.api.trace.list(tags=...)` returning an
    object with a `.data` list of trace-like objects carrying
    `total_cost`, `latency` and `output`."""
    result = client.api.trace.list(tags=f"config_id:{config_id}")
    traces = list(getattr(result, "data", None) or [])
    n = len(traces)
    if n == 0:
        return ConfigRow(
            config_id=config_id,
            n=0,
            cost_usd_total=0.0,
            pass_rate=None,
            latency_avg_s=None,
        )
    cost_total = sum(float(getattr(t, "total_cost", 0) or 0) for t in traces)
    passed = sum(1 for t in traces if _trace_status(t) == DONE_STATUS)
    latencies = [float(getattr(t, "latency", 0) or 0) for t in traces]
    return ConfigRow(
        config_id=config_id,
        n=n,
        cost_usd_total=cost_total,
        pass_rate=passed / n,
        latency_avg_s=sum(latencies) / len(latencies),
    )


def query_config_table(client: Any, config_ids: list[str]) -> list[ConfigRow]:
    """One row per config_id, in the order given -- the table ORCH-01's
    ACCEPT asks a Langfuse query to answer, no new dashboard involved."""
    return [query_config_row(client, config_id) for config_id in config_ids]
