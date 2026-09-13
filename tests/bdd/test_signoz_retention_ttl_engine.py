"""The retention knob is applied through the engine SigNoz actually accepts.

Spec: the header of platform/observability/signoz-retention.yaml.

THE DEFECT THIS GRADES. The job ran daily and failed every morning on exactly one
signal:

    FAIL signoz-retention logs 500 {"errors":[{"code":500,"msg":"SetTTLV2 only supported"}]}

`traces` and `metrics` were already at 168h, so the job never had to write them,
and the v1 GET kept answering 200 for all three. A job that writes nothing looks
identical to a job that works, so the failure hid for days behind its own
successful reads.

The v1 POST is refused because this deployment is on the v2 TTL engine. Measured
on the live estate 2026-09-13:

    GET  /api/v1/settings/ttl?type=logs -> 200, logs_ttl_duration_hrs: -1   (unset)
    GET  /api/v2/settings/ttl?type=logs -> 200, default_ttl_days: 15
    POST /api/v2/settings/ttl {"type":"logs","duration":"168h"}
         -> 200 {"message":"custom retention TTL has been successfully set up"}

WHAT IS GRADED HERE, offline, is the contract in the ConfigMap: the write goes to
v2, the read goes to v2, and the two generations are not mixed. The live behaviour
cannot be graded from a unit test -- a test that needs the estate up is skipped
exactly when the estate is down -- so what is pinned is the thing that broke and
the shape that fixes it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "platform" / "observability" / "signoz-retention.yaml"


@pytest.fixture(scope="module")
def apply_source() -> str:
    """The apply.py the Job actually runs, out of the ConfigMap it is mounted from."""
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    cm = next(
        d
        for d in docs
        if d.get("kind") == "ConfigMap"
        and d["metadata"]["name"] == "signoz-retention-apply"
    )
    return cm["data"]["apply.py"]


@pytest.fixture(scope="module")
def apply_module(apply_source: str):
    """The ConfigMap's python, compiled as a module so its own helpers can be called."""
    tree = ast.parse(apply_source)
    ns: dict = {}
    # Everything except the `main()` guard, which would run the job on import.
    body = [
        n
        for n in tree.body
        if not (
            isinstance(n, ast.If)
            and isinstance(getattr(n, "test", None), ast.Compare)
            and getattr(n.test.left, "id", None) == "__name__"
        )
    ]
    module = ast.Module(body=body, type_ignores=[])
    exec(compile(module, "<signoz-retention>", "exec"), ns)  # noqa: S102 -- the manifest is the subject
    return ns


# --- the write target -------------------------------------------------------


def test_the_retention_write_goes_to_v2(apply_source: str) -> None:
    """v1 is refused with `SetTTLV2 only supported`; the write must be v2.

    This is the line that failed. A job whose write is refused on one signal and
    never attempted on the other two reports success for days.
    """
    assert "POST" in apply_source
    posts = re.findall(r'http\(\s*"POST",\s*"([^"]+)"', apply_source)
    assert posts, "the apply must POST somewhere"
    # Only the TTL writes are graded here: the job also POSTs to /api/v2/sessions/email_password
    # to log in, and a login is not a retention change.
    ttl_posts = [p for p in posts if "settings/ttl" in p]
    assert ttl_posts, "the apply must write the TTL somewhere"
    assert all(p.startswith("/api/v2/settings/ttl") for p in ttl_posts), (
        f"the retention write must go to /api/v2/settings/ttl, found {ttl_posts}. The v1 endpoint "
        "answers 500 `SetTTLV2 only supported` on this deployment."
    )


def test_no_v1_ttl_write_survives_anywhere(apply_source: str) -> None:
    """A v1 POST left beside the v2 one would keep failing the same way."""
    assert '"/api/v1/settings/ttl"' not in apply_source.replace(" ", ""), (
        "a v1 TTL write is still in the job; it is refused on this deployment"
    )


def test_the_read_uses_the_same_engine_as_the_write(apply_source: str) -> None:
    """Reading v1 while writing v2 is how a knob lands and the job still reports work daily.

    The two generations disagree about the current value: v1 said `-1` for a logs
    signal v2 had already set.
    """
    gets = re.findall(r'http\(\s*"GET",\s*"([^"]+)"', apply_source)
    ttl_gets = [g for g in gets if "settings/ttl" in g]
    assert ttl_gets, "the plan step must read the current TTL"
    assert all(g.startswith("/api/v2/settings/ttl") for g in ttl_gets), (
        f"the TTL read must be v2 like the write, found {ttl_gets}"
    )


# --- the plan, which is what decides whether a write happens at all ----------


def test_a_signal_already_at_the_knob_is_not_rewritten(apply_module) -> None:
    """`MODIFY TTL` is not free, so a correct estate must produce no writes."""
    calls = []

    def http(method, path, body=None, token=None, params=None):
        calls.append((method, path))
        return 200, {"version": "v2", "status": "success", "default_ttl_days": 7}

    assert apply_module["plan"](http, "tok", 7) == []
    assert all(m == "GET" for m, _ in calls), "planning must not write"


def test_a_signal_at_the_wrong_value_is_planned(apply_module) -> None:
    def http(method, path, body=None, token=None, params=None):
        return 200, {"version": "v2", "status": "success", "default_ttl_days": 15}

    todo = apply_module["plan"](http, "tok", 7)
    assert sorted(s for s, _ in todo) == ["logs", "metrics", "traces"]


def test_a_custom_ttl_already_in_force_is_read_as_the_knob(apply_module) -> None:
    """v2 drops `default_ttl_days` once a custom TTL is set.

    Reading that absence as 'unreadable' would make the job rewrite every signal
    every single day.
    """

    def http(method, path, body=None, token=None, params=None):
        return 200, {"version": "v2", "status": "success", "cold_storage_ttl_days": -1}

    assert apply_module["plan"](http, "tok", 7) == []


def test_a_signal_whose_ttl_cannot_be_read_is_planned_not_skipped(apply_module) -> None:
    """A failed read is a reason to apply, never a reason to stay silent.

    Treating an unreadable TTL as 'fine' is the 2026-09-08 defect in this job's
    own shape: a thing that could not be seen reported as a thing that is correct.
    """

    def http(method, path, body=None, token=None, params=None):
        return 500, {"error": "boom"}

    todo = apply_module["plan"](http, "tok", 7)
    assert sorted(s for s, _ in todo) == ["logs", "metrics", "traces"]


def test_the_write_carries_the_signal_and_the_duration(apply_module) -> None:
    """The v2 write is a JSON body, not query parameters -- that is the v1 shape."""
    seen = []

    def http(method, path, body=None, token=None, params=None):
        seen.append((method, path, body))
        return 200, {"message": "custom retention TTL has been successfully set up"}

    failed = apply_module["apply"](http, "tok", 7, [("logs", 15)])
    assert failed == []
    method, path, body = seen[0]
    assert method == "POST"
    assert path.startswith("/api/v2/settings/ttl")
    assert body == {"type": "logs", "duration": "168h"}


def test_a_refused_write_is_reported_and_never_swallowed(apply_module) -> None:
    """The original defect was a refusal nobody read. It must reach the exit code."""

    def http(method, path, body=None, token=None, params=None):
        return 500, {"errors": [{"code": 500, "msg": "SetTTLV2 only supported"}]}

    failed = apply_module["apply"](http, "tok", 7, [("logs", -1)])
    assert len(failed) == 1
    assert "logs" in failed[0]


def test_a_change_still_running_is_pending_not_failed(apply_module) -> None:
    """409 is ClickHouse mid-ALTER; the next run finishes it. That is not a red job."""

    def http(method, path, body=None, token=None, params=None):
        return 409, {"message": "in progress"}

    assert apply_module["apply"](http, "tok", 7, [("logs", -1)]) == []
