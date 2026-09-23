"""Fail fast: refuse to start half-configured, and say what is missing in one sentence.

THE DEFECT THIS REMOVES (measured 2026-09-18). A FleetView backend was launched on a laptop
with an empty environment. It started, bound its port and served traffic, and every feature
that needed the cluster answered with a 502 or a 503:

    POST /nudge   200   (claude-code writes a file: no env needed)
    POST /approve 502   (sovereign dispatch: needs a Temporal workflow)
    POST /deny    502
    POST /stop    404, then 500
    GET  /trace   503   (needs LANGFUSE_HOST)
    POST /check-receipts 503

Nothing about that process said "I am not configured." It said "the operation failed", once per
button, from the outside. The 12-factor rule is the one this module enforces: validate
configuration at startup and exit with a clear error, rather than accepting traffic you cannot
serve. A process that cannot do its job must not present itself as one that can.

WHY NOT JUST REQUIRE EVERYTHING. Because most of these really are optional, and a guard that
demands a value the estate does not always provide is a guard people route around:

  required   ESTATE_DB      the catalog the board reads. Without it every read is empty, and
                            an empty board is indistinguishable from a fleet with no work.
  optional   NATS_URL       the live event stream. Unset means no SSE and no otter/claude-code
                            adapters; the board still reads its store, so this is a degraded
                            mode, not a broken one.
  optional   LANGFUSE_HOST  trace and receipt checks. Their routes already answer 503 with the
                            reason, which is the honest answer and not a startup failure.
  optional   LINEAR_API_KEY cyrus steering only.
  optional   JIT_AGENT_KEY  device identity; not this process's concern.

So `required` is the short list of things whose absence makes the process a liar. Everything
else is checked at the point of use, where the answer can name the specific feature.

CONFIG (LAW 46): the names live here and nowhere else in this plugin's startup path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Vars whose absence means this process cannot serve its purpose at all. Each carries the
#: sentence a reader needs, because "ESTATE_DB is unset" is not actionable on its own.
REQUIRED: dict[str, str] = {
    "ESTATE_DB": (
        "the catalog the board reads. Without it every session read returns nothing, and an "
        "empty board looks exactly like a fleet with no work -- the one failure this service "
        "must never present."
    ),
}

#: Vars that change what works rather than whether it works. Named here so the startup banner
#: can say what is off, and so a reader does not have to discover it by clicking.
#: `route` is the surface that degrades, and `why` is what a user would see.
OPTIONAL: dict[str, tuple[str, str]] = {
    "NATS_URL": (
        "the live event stream (/stream, SSE)",
        "the board will not update live; adapters that publish to the bus are off",
    ),
    "LANGFUSE_HOST": (
        "trace and receipt checks (/trace, /check-receipts)",
        "the live-mind graph and receipt verdicts will answer 'unavailable'",
    ),
    "LINEAR_API_KEY": (
        "cyrus steering (steer to a Linear issue)",
        "steering a cyrus session will be refused with 'no live signal path'",
    ),
}


class ConfigError(RuntimeError):
    """Raised at startup when a required var is missing.

    Deliberately an exception rather than an `exit(1)`: the caller decides how to die, and a
    test can assert the message without spawning a process. `require_config` is what a launcher
    calls, and it prints before raising.
    """


@dataclass(frozen=True)
class Config:
    """The validated configuration. Constructing this IS the check."""

    db_path: Path
    nats_url: str | None
    langfuse_host: str | None
    linear_api_key: str | None

    @property
    def degraded(self) -> list[tuple[str, str, str]]:
        """(name, surface, consequence) for each optional var this config did not receive.

        Derived from the fields the Config was CONSTRUCTED with, not from `os.environ` at the
        time the banner is printed. The first version read the environment directly and the
        test suite caught it immediately: a config built from an explicit env still reported
        NATS_URL as unset, so the banner would have lied about a process that had it. A report
        that ignores the values it is reporting on is worse than no report.
        """
        provided = {
            "NATS_URL": self.nats_url,
            "LANGFUSE_HOST": self.langfuse_host,
            "LINEAR_API_KEY": self.linear_api_key,
        }
        return [
            (name, surface, consequence)
            for name, (surface, consequence) in OPTIONAL.items()
            if not provided.get(name)
        ]


def missing_required(env: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """(name, why-it-matters) for every required var that is unset or blank.

    Split out so a test can assert the list without triggering the exit path, and so a
    preflight tool can reuse it without importing the app.
    """
    source = env if env is not None else os.environ
    return [
        (name, why)
        for name, why in REQUIRED.items()
        if not (source.get(name) or "").strip()
    ]


def format_missing(missing: list[tuple[str, str]]) -> str:
    """The one message a person reads. Names the cause, the consequence and the fix."""
    lines = [
        "refusing to start: this process would accept traffic it cannot serve.",
        "",
    ]
    for name, why in missing:
        lines.append(f"  {name} is not set -- {why}")
    lines += [
        "",
        "  fix   set it, or start through the launcher that already does:",
        "        bin/serve-fleetview  (local) or the sidecar's env (cluster)",
        "",
        "  note  NATS_URL and LANGFUSE_HOST are NOT required. Unset, the board still",
        "        reads its store and those routes answer 'unavailable' with the reason.",
    ]
    return "\n".join(lines)


def require_config(env: dict[str, str] | None = None) -> Config:
    """Validate, then return the configuration. Raises ConfigError when a required var is absent.

    Called from `build_app`, which is the single place both the launcher and the tests go
    through -- so a test that builds an app exercises the same check production does, rather
    than a parallel one that can drift.
    """
    missing = missing_required(env)
    if missing:
        raise ConfigError(format_missing(missing))

    source = env if env is not None else os.environ
    return Config(
        db_path=Path(source["ESTATE_DB"]),
        nats_url=(source.get("NATS_URL") or "").strip() or None,
        langfuse_host=(source.get("LANGFUSE_HOST") or "").strip() or None,
        linear_api_key=(source.get("LINEAR_API_KEY") or "").strip() or None,
    )


def startup_banner(config: Config) -> str:
    """What the process says when it starts. Names what is off, so nobody has to click to find out.

    A degraded start is not a failure and must not read like one -- but it must be visible,
    because "the trace pane is empty" is otherwise a mystery someone debugs for an hour.
    """
    lines = [f"fleetview: catalog {config.db_path}"]
    if config.nats_url:
        lines.append(f"fleetview: live stream via {config.nats_url}")
    for name, surface, consequence in config.degraded:
        lines.append(f"fleetview: {name} unset -- {surface} off ({consequence})")
    return "\n".join(lines)
