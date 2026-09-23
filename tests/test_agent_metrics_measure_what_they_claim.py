"""The agent-metrics collector reports what it measured, and nothing it did not.

The defect these tests exist for (measured 2026-09-23, while building it): the first version
computed `coverage_pct` from a top-15 slice of the tool histogram, so it read 100.0% once an
agent had touched fifteen tool names -- a metric that saturates at perfect is the
unmeasured-looks-optimal defect this estate forbids. The second version divided by a hardcoded
denominator and printed `tools_used: 29 of 13` -- a denominator smaller than the set it was
dividing. Both are assertion-shaped numbers. These tests pin the measurement instead:
the counts come from records, and a degenerate denominator is named as observational rather
than shown as a score.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import importlib.util

MOD_PATH = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "skills"
    / "metrics"
    / "collect_metrics.py"
)


def _load():
    spec = importlib.util.spec_from_loader(
        "collect_metrics",
        importlib.machinery.SourceFileLoader("collect_metrics", str(MOD_PATH)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_session(tmp: Path, name: str, tools: list[str], infra: bool = False) -> Path:
    p = tmp / "proj" / f"{name}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for i, t in enumerate(tools):
            inp = {"command": "kubectl get pods"} if (infra and i == 0) else {"x": 1}
            fh.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "timestamp": "2026-09-23T10:00:00Z",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "tool_use", "name": t, "input": inp}],
                        },
                    }
                )
                + "\n"
            )
    return p


def test_counts_come_from_records_not_estimates(tmp_path, monkeypatch):
    """Every number is a count of records that exist. Two sessions, 5 calls -> 5, and an
    invocation rate of 2.5, not a rounded feeling."""
    m = _load()
    _write_session(tmp_path, "a", ["Bash", "Read", "Edit"])
    _write_session(tmp_path, "b", ["Bash", "Write"])
    monkeypatch.setattr(
        m, "_files", lambda days: sorted((tmp_path / "proj").glob("*.jsonl"))
    )

    r = m.collect(90, tmp_path)
    assert r["sessions"] == 2
    assert r["tool_calls"] == 5
    assert r["invocation_rate"] == 2.5
    assert r["usage_dist"]["Bash"] == 2


def test_coverage_cannot_exceed_one_hundred_percent(tmp_path, monkeypatch):
    """The `29 of 13` regression: a denominator smaller than the numerator is a broken gauge.
    Coverage is clamped, and the raw pair is exposed so the contradiction is visible."""
    m = _load()
    _write_session(tmp_path, "a", [f"Tool{i}" for i in range(29)])
    monkeypatch.setattr(
        m, "_files", lambda days: sorted((tmp_path / "proj").glob("*.jsonl"))
    )

    r = m.collect(90, tmp_path)
    assert r["tools_used"] == 29
    assert r["tools_available"] >= r["tools_used"], (
        "denominator must not be smaller than the set"
    )
    assert r["coverage_pct"] <= 100.0


def test_observational_coverage_is_named_not_scored(tmp_path, monkeypatch):
    """When there is no registry to grade against, coverage is 100% by construction. That must
    be labelled, so no dashboard reads it as perfect tool use."""
    m = _load()
    _write_session(tmp_path, "a", ["Bash", "Read"])
    monkeypatch.setattr(
        m, "_files", lambda days: sorted((tmp_path / "proj").glob("*.jsonl"))
    )

    r = m.collect(90, tmp_path)
    if r["coverage_is_observational"]:
        assert "observational" in m.as_markdown(r)


def test_infrastructure_review_is_measured_from_commands(tmp_path, monkeypatch):
    """`infra_review_pct` is the share of sessions that touched infrastructure, derived from the
    command text -- not a label an agent applies to itself."""
    m = _load()
    _write_session(tmp_path, "infra", ["Bash"], infra=True)
    _write_session(tmp_path, "other", ["Bash", "Read"], infra=False)
    monkeypatch.setattr(
        m, "_files", lambda days: sorted((tmp_path / "proj").glob("*.jsonl"))
    )

    r = m.collect(90, tmp_path)
    assert r["sessions"] == 2
    assert r["infra_review_pct"] == 50.0


def test_empty_window_is_zero_sessions_not_a_failure(tmp_path, monkeypatch):
    """No transcripts is an honest zero, never an exception and never a fake number."""
    m = _load()
    monkeypatch.setattr(m, "_files", lambda days: [])
    r = m.collect(90, tmp_path)
    assert r["sessions"] == 0
    assert r["tool_calls"] == 0
    assert r["invocation_rate"] == 0.0


def test_prometheus_output_is_well_formed(tmp_path, monkeypatch):
    """The line the spec draws to the one store: Layer 1 (Coroot) and Layer 2 (this) both land
    in Prometheus. A metric family without a HELP/TYPE pair is not scrapable."""
    m = _load()
    _write_session(tmp_path, "a", ["Bash"])
    monkeypatch.setattr(
        m, "_files", lambda days: sorted((tmp_path / "proj").glob("*.jsonl"))
    )

    text = m.as_prometheus(m.collect(90, tmp_path))
    assert "# HELP idp_agent_sessions" in text
    assert "# TYPE idp_agent_tool_calls counter" in text
    assert "idp_agent_invocation_rate " in text
