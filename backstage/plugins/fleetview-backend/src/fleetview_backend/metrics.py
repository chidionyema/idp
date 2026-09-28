"""Voice metrics in Prometheus text format, served at /metrics and scraped by the one Prometheus.

WHY THIS EXISTS. The Helm chart already ships a ServiceMonitor that scrapes `path: /metrics`,
and sets METRICS_ENABLED/METRICS_PORT — but until this module there was NO `/metrics` endpoint in
the process, so Prometheus was told to scrape a port nothing was listening on. A monitor over a
missing exporter is a decoration, not an instrument: voice latency could double tomorrow and the
observability stack would not flinch. This module makes the scrape real.

WHY NO prometheus_client DEPENDENCY. The estate's own elite pattern — the canary gauge
(platform/staging/canary/gauge.yaml) — serves Prometheus text format as static text with no
client library. `prometheus_client` is a 2MB dependency for a job that is a `join()` of name and
value; the canary proves hand-rolled text is the bar, not a shortcut. The metrics here are gauges
read fresh from `sovereign/voice/turnlog.py::summary()`, so they are the SAME numbers the board's
friction view shows — one source, no drift.

THE METRICS, and why these are the ones that matter (each maps to a founder-asked question):
  voice_turns_total                 how much voice has been used            (gauge: count)
  voice_turns_empty_total           how often it heard nothing              ("I had to repeat myself")
  voice_turns_error_total           how often the turn errored
  voice_empty_rate                  fraction of empty turns                 (the friction headline)
  voice_asr_median_seconds          how long transcription takes
  voice_first_clause_median_seconds how long until the person hears speech  (the latency headline)
  voice_first_clause_p90_seconds    the long tail a median hides
  voice_clause_latency_median_seconds{voice="..."}  per-voice speed

All are plain float gauges. A counter would be wrong: the turnlog is a bounded window (default
200 turns), not a monotonic lifetime total, so a Counter whose value drops when a turn ages out
would be a lie. Gauges say "right now, this window" truthfully.
"""

from __future__ import annotations

from typing import Any

# The voice name is a label, and as a label it must be a value the model actually spoke with.
# `turnlog` fills the voice field with the engine name when no voice is set, which is honest; the
# label preserves that rather than inventing a voice id.
_VOICE_LABEL = "voice"


def _fmt(value: float | None) -> str:
    """Prometheus text format for a float: NaN for absent, plain number otherwise.

    A metric that has no measurement must be NaN ("unknown"), never 0 ("fine") — a stalled voice
    loop answering 0 to every latency gauge is exactly the silent lie the estate forbids. Prometheus
    treats NaN as absent in alerting expressions, which is the correct signal: "no data" is a
    different fact from "zero".
    """
    if value is None:
        return "NaN"
    return repr(float(value))


def _gauge(
    name: str, help_text: str, value: float | None, labels: dict[str, str] | None = None
) -> list[str]:
    lines = [f"# HELP {name} {help_text}", f"# TYPE {name} gauge"]
    tag = ""
    if labels:
        parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        tag = f"{{{parts}}}"
    lines.append(f"{name}{tag} {_fmt(value)}")
    return lines


def render(summary: dict[str, Any]) -> str:
    """Render the turnlog summary as a Prometheus text-format body.

    `summary` is the dict `sovereign/voice/turnlog.py::summary()` returns. An empty summary
    (no turns yet) still renders every gauge as NaN so the metric NAMES exist on first scrape —
    a dashboard that references them does not gap out before the first turn.
    """
    out: list[str] = []

    out += _gauge(
        "voice_turns_total",
        "Number of voice turns in the current window.",
        float(summary.get("turns", 0)),
    )
    out += _gauge(
        "voice_turns_empty_total",
        "Voice turns that produced no transcript (heard nothing).",
        float(summary.get("empty", 0)),
    )
    out += _gauge(
        "voice_turns_error_total",
        "Voice turns whose outcome was error.",
        float(summary.get("errors", 0)),
    )
    out += _gauge(
        "voice_empty_rate",
        "Fraction of turns that heard nothing — the voice friction headline.",
        _opt(summary.get("empty_rate")),
    )
    out += _gauge(
        "voice_asr_median_seconds",
        "Median seconds to transcribe an utterance.",
        _opt(summary.get("asr_median_s")),
    )
    out += _gauge(
        "voice_first_clause_median_seconds",
        "Median seconds until the first spoken clause — the latency a person feels.",
        _opt(summary.get("first_clause_median_s")),
    )
    out += _gauge(
        "voice_first_clause_p90_seconds",
        "P90 seconds until the first spoken clause — the long tail a median hides.",
        _opt(summary.get("first_clause_p90_s")),
    )

    by_voice = summary.get("by_voice") or {}
    for voice, stat in sorted(by_voice.items()):
        # A voice label with a comma/quote/etc. is still safe: Prometheus escapes in the name, and
        # voice ids are engine-provided short tokens, never free text.
        out += _gauge(
            "voice_clause_latency_median_seconds",
            "Median first-clause latency for a single voice.",
            _opt(stat.get("first_clause_median_s") if isinstance(stat, dict) else None),
            {_VOICE_LABEL: str(voice)},
        )

    return "\n".join(out) + "\n"


def _opt(value: Any) -> float | None:
    """None stays None (rendered NaN); a number passes through; otherwise None (unknown)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
