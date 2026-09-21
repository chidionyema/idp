"""A process that cannot do its job must not present itself as one that can.

THE DEFECT (measured 2026-09-18). A FleetView backend was launched on a laptop with an empty
environment. It started, bound its port and served traffic. Every button that needed the cluster
then answered from the outside:

    POST /nudge          200   (claude-code writes a file: no env needed)
    POST /approve        502   (sovereign dispatch)
    POST /deny           502
    POST /stop           404, then 500
    GET  /trace          503   (needs LANGFUSE_HOST)
    POST /check-receipts 503

Nothing in that process said "I am not configured". It said "the operation failed", once per
button. Twelve-factor's rule is the one this grades: validate configuration at startup and fail
clearly, rather than accepting traffic you cannot serve.

THE SECOND HALF, WHICH MATTERS AS MUCH. A guard that demands everything is a guard people route
around, and this estate does run without NATS and Langfuse. So the tests below assert BOTH
directions: a missing required var refuses, and a missing optional var degrades and says what
is off. A guard that made NATS_URL required would break the local board; a guard that made
ESTATE_DB optional would let the empty-board-looks-like-no-work failure through.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GUARD_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "config_guard.py"
)
SERVE_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "serve.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # `sys.modules` before exec: config_guard uses @dataclass, which resolves cls.__module__
    # through sys.modules at decoration time.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def guard():
    return _load(GUARD_MODULE, "fleetview_config_guard_under_test")


# --------------------------------------------------------------- the refusal that matters


def test_a_missing_required_var_refuses_to_start(guard):
    """ESTATE_DB absent: the one case where the process would be a liar."""
    with pytest.raises(guard.ConfigError):
        guard.require_config({})


def test_the_refusal_names_the_var_the_consequence_and_the_fix(guard):
    """A refusal a reader can act on. 'ESTATE_DB is unset' alone is not actionable."""
    with pytest.raises(guard.ConfigError) as exc:
        guard.require_config({})
    msg = str(exc.value)
    assert "ESTATE_DB" in msg
    assert "refusing to start" in msg
    # The consequence, in the words a person would use.
    assert "empty board" in msg
    # And a fix that is not 'read the source'.
    assert "fix" in msg
    assert len(msg.splitlines()) > 3, "one terse line is not a readable refusal"


def test_a_blank_value_counts_as_missing(guard, tmp_path):
    """An empty string is the shape a broken launcher actually produces, not a synonym for set."""
    with pytest.raises(guard.ConfigError):
        guard.require_config({"ESTATE_DB": "   "})


# ------------------------------------------------ the degradation, which is equally load-bearing


def test_nats_and_langfuse_are_not_required(guard, tmp_path):
    """The local board runs without them; making them required would break it.

    This is the test that keeps the guard from being routed around: a `require everything`
    version would be deleted by the first person it annoyed.
    """
    config = guard.require_config({"ESTATE_DB": str(tmp_path / "estate.db")})
    assert config.nats_url is None
    assert config.langfuse_host is None


def test_a_degraded_start_says_what_is_off_and_what_it_costs(guard, tmp_path):
    """'The trace pane is empty' must be decidable without clicking anything."""
    config = guard.require_config({"ESTATE_DB": str(tmp_path / "estate.db")})
    banner = guard.startup_banner(config)
    assert str(tmp_path / "estate.db") in banner
    assert "NATS_URL unset" in banner
    assert "LANGFUSE_HOST unset" in banner
    # Each line carries the user-visible consequence, not just the variable name.
    assert "unavailable" in banner, "name what a reader would actually see"
    assert "not update live" in banner


def test_a_fully_configured_start_reports_no_degradation(guard, tmp_path):
    config = guard.require_config(
        {
            "ESTATE_DB": str(tmp_path / "estate.db"),
            "NATS_URL": "nats://bus:4222",
            "LANGFUSE_HOST": "https://langfuse.test",
            "LINEAR_API_KEY": "x",
        }
    )
    banner = guard.startup_banner(config)
    assert "unset" not in banner
    assert "nats://bus:4222" in banner


def test_the_degraded_list_names_the_route_that_suffers(guard, tmp_path):
    """(name, surface, consequence) -- so a banner can be specific, not a list of vars."""
    config = guard.require_config({"ESTATE_DB": str(tmp_path / "estate.db")})
    degraded = {
        name: (surface, consequence) for name, surface, consequence in config.degraded
    }
    assert "NATS_URL" in degraded
    assert "/stream" in degraded["NATS_URL"][0]
    assert "LANGFUSE_HOST" in degraded
    assert "/trace" in degraded["LANGFUSE_HOST"][0]


# ---------------------------------------------------- the wiring, so the guard cannot be bypassed


def test_build_app_validates_before_it_serves(guard):  # noqa: ARG001
    """The check runs in build_app, which every startup path goes through.

    Asserted by reading serve.py: a guard that exists but is never called is the same failure
    as no guard, and it is invisible to every test that constructs a Config directly.
    """
    src = SERVE_MODULE.read_text()
    assert "require_config()" in src, (
        "build_app does not call require_config, so a half-configured process would still start"
    )
    # And before the app is constructed, so no route can be reached first.
    assert src.index("require_config()") < src.index("app = FastAPI("), (
        "the config check must run before the app exists, or a request could land first"
    )


def test_the_missing_list_is_reusable_without_the_exit_path(guard, tmp_path):
    """A preflight tool can ask without dying, which is what makes this check composable."""
    missing = guard.missing_required({})
    assert [name for name, _why in missing] == ["ESTATE_DB"]
    assert guard.missing_required({"ESTATE_DB": str(tmp_path / "x")}) == []


def test_every_required_var_carries_a_reason(guard):
    """A required var with no explanation is a rule without a reason, and gets removed."""
    for name, why in guard.REQUIRED.items():
        assert len(why) > 40, f"{name} has no real explanation: {why!r}"


def test_the_banner_reports_the_config_it_was_given_not_the_ambient_environment(
    guard, tmp_path
):
    """The bug the suite found on 2026-09-18, kept as a case.

    `degraded` first read `os.environ` directly, so a Config constructed with an explicit env
    still reported those vars as unset. A report that ignores the values it is reporting on is
    worse than no report: it would tell an operator that the live stream was off on a process
    that had NATS_URL all along, and the first thing they would do is stop trusting the banner.
    """
    import os as _os

    # Ambient environment deliberately the opposite of what we pass, so reading the wrong
    # source cannot pass by luck.
    for name in ("NATS_URL", "LANGFUSE_HOST", "LINEAR_API_KEY"):
        _os.environ.pop(name, None)

    config = guard.require_config(
        {
            "ESTATE_DB": str(tmp_path / "estate.db"),
            "NATS_URL": "nats://bus:4222",
            "LANGFUSE_HOST": "https://langfuse.test",
            "LINEAR_API_KEY": "present",
        }
    )
    assert config.degraded == [], (
        f"a fully-configured Config reported degradation from the environment instead: "
        f"{config.degraded}"
    )
    assert "unset" not in guard.startup_banner(config)


def test_a_partial_config_reports_only_what_is_actually_missing(guard, tmp_path):
    """And the converse: exactly the missing one, not all of them."""
    config = guard.require_config(
        {"ESTATE_DB": str(tmp_path / "estate.db"), "NATS_URL": "nats://bus:4222"}
    )
    names = [name for name, _s, _c in config.degraded]
    assert names == ["LANGFUSE_HOST", "LINEAR_API_KEY"], (
        f"expected only the two that are missing, got {names}"
    )
