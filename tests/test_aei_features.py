"""features/assurance/aei.feature, bound to the real AEI library.

A feature that cannot run is prose. Every step here runs against packages/aei/src/aei -- the same
code the laptop collector and the OKE collector run -- and nothing is mocked except the two places
a scenario is ABOUT a failure: an unreachable collector, and a router that answers.

The AEI package uses the estate's src layout, so the library is put on the path here rather than
installed: the same rule packages/idp_concurrency/tests/conftest.py follows.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "packages" / "aei" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aei.analysis import analyse, compare  # noqa: E402
from aei.client import Emitter  # noqa: E402
from aei.contract import validate_manifest  # noqa: E402
from aei.core import Store, make_event, validate  # noqa: E402
from aei.estate import identity, router_call  # noqa: E402

scenarios("../features/assurance/aei.feature")

IDENTITY = identity(
    run_id="run-bdd",
    task_id="task-bdd",
    agent_id="agent-bdd",
    harness_id="harness-bdd",
    revision="sha-bdd",
    trace_id="trace-bdd",
)


@pytest.fixture
def store(tmp_path: Path):
    s = Store(tmp_path / "aei.sqlite3")
    yield s
    s.close()


@pytest.fixture
def event() -> dict:
    return make_event("task.started", **IDENTITY)


# --- the library's own scenarios -------------------------------------------------------------------


@given("a valid task event", target_fixture="event")
def _valid_task_event() -> dict:
    return make_event("task.started", **IDENTITY)


@then("the event carries run, task, agent, harness, trace and revision identifiers")
def _carries_identifiers(event: dict) -> None:
    for key in ("run_id", "task_id", "agent_id", "harness_id", "trace_id", "revision"):
        assert event[key], f"{key} is empty"


@given("an event with an unclassified attribute", target_fixture="event")
def _unclassified_event(event: dict) -> dict:
    event["attributes"]["raw_prompt"] = "sensitive"
    return event


@when("the event is validated")
def _validate(event: dict) -> None:
    with pytest.raises(ValueError):
        validate(event)


@then("the event is refused")
def _validation_failed() -> None:
    assert True  # the raise inside the previous step is the assertion


@given("a stored event", target_fixture="event")
def _stored_event(store: Store, event: dict) -> dict:
    assert store.append(event)["accepted"]
    return event


@when("the same event is appended again")
def _append_again(store: Store, event: dict) -> dict:
    return store.append(event)


@then("the store records only one event")
def _one_event(store: Store) -> None:
    assert len(store.events(IDENTITY["run_id"])) == 1


@then("a conflicting event with the same id is rejected")
def _conflict_rejected(store: Store, event: dict) -> None:
    conflicting = dict(event)
    conflicting["attributes"] = {"status": "changed"}
    with pytest.raises(ValueError):
        store.append(conflicting)


@given("an unreachable collector", target_fixture="unreachable")
def _unreachable_collector() -> str:
    return "http://127.0.0.1:1"


@when("an agent emits an event")
def _emit(unreachable: str) -> None:
    client = Emitter(unreachable, "invalid", IDENTITY, timeout=0.05)
    started = time.monotonic()
    assert client.emit("task.started") is not None
    assert time.monotonic() - started < 0.5, "the emit waited for the collector"
    client.close()


@then("the emit returns without waiting for the collector")
def _emit_did_not_wait() -> None:
    assert True


@given("a trace without cost observations", target_fixture="trace")
def _trace_without_cost(event: dict) -> list:
    return [event]


@when("the trace is analysed", target_fixture="evaluation")
def _analyse(trace: list) -> dict:
    return analyse(trace)


@then("cost is unknown rather than zero")
def _cost_unknown(evaluation: dict) -> None:
    assert evaluation["metrics"]["observed_cost_usd"] is None
    assert evaluation["metrics"]["cost_samples"] == 0


@given("a component manifest without a visualisation", target_fixture="manifest")
def _manifest_without_visualisation() -> dict:
    path = _REPO_ROOT / "packages" / "aei" / "examples" / "router.manifest.json"
    manifest = json.loads(path.read_text())
    manifest["visualisations"] = []
    return manifest


@when("the manifest is validated")
def _validate_manifest(manifest: dict) -> None:
    with pytest.raises(ValueError):
        validate_manifest(manifest)


@then("the manifest is refused")
def _manifest_rejected() -> None:
    assert True


@given("two runs of the same task without verification", target_fixture="runs")
def _two_unverified_runs(event: dict) -> tuple:
    left = dict(event)
    right = dict(event)
    right["event_id"] = event["event_id"] + "-b"
    return left, right


@when("their performance is compared", target_fixture="comparison")
def _compare(runs: tuple) -> dict:
    return compare(list(runs), list(runs))


@then("the comparison is not declared verified")
def _not_comparable(comparison: dict) -> None:
    assert comparison["comparable"] is False


@given("a stored run")
def _stored_run(store: Store, event: dict) -> None:
    store.append(event)


@when("the store is reopened", target_fixture="reopened")
def _reopen(tmp_path: Path, store: Store):
    store.close()
    return Store(tmp_path / "aei.sqlite3")


@then("its events remain readable in append order")
def _readable(reopened: Store) -> None:
    events = reopened.events(IDENTITY["run_id"])
    assert len(events) == 1
    assert events[0]["seq"] >= 1
    reopened.close()


# --- the estate adapter's own scenarios ------------------------------------------------------------


class _RouterHandler(BaseHTTPRequestHandler):
    payload = {
        "id": "chatcmpl-bdd",
        "model": "minimax/minimax-m2",
        "choices": [{"message": {"role": "assistant", "content": "PONG"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    }

    def log_message(self, *args):  # noqa: D102 - silence the default stderr logging
        pass

    def do_POST(self):  # noqa: N802 - the http.server API names it so
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        body = json.dumps(self.payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def router():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RouterHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@given("a router that answers with a usage payload")
def _router(router: str) -> str:
    return router


@when("the estate adapter calls the router", target_fixture="emitted")
def _call_router(router: str) -> list:
    # The emitter's transport is replaced by a list, so the assertion is about WHAT THE ADAPTER
    # EMITS -- its attributes -- and not about the network. The transport itself is covered by
    # the collector scenarios above.
    client = Emitter("http://127.0.0.1:1", "invalid", IDENTITY, timeout=0.05)
    emitted: list = []
    client.emit = lambda event_type, **kwargs: emitted.append(
        make_event(event_type, **IDENTITY, **kwargs)
    )
    result = router_call(
        client,
        IDENTITY,
        [{"role": "user", "content": "the prompt that must not be stored"}],
        router_url=router,
        api_key="test-key",
    )
    assert result["usage"]["prompt_tokens"] == 11
    return emitted


@then("the ledger records the observed model, tokens and latency")
def _ledger_records_observation(emitted: list) -> None:
    completed = [e for e in emitted if e["type"] == "model.completed"]
    assert completed, "the adapter never emitted model.completed"
    attributes = completed[0]["attributes"]
    assert attributes["model"] == "minimax/minimax-m2"
    assert attributes["input_tokens"] == 11
    assert attributes["output_tokens"] == 3
    assert attributes["latency_ms"] >= 0
    assert attributes["evidence_grade"] in ("observed", "derived", "unknown")


@then("the prompt and the answer are absent from the ledger")
def _no_prompt_in_ledger(emitted: list) -> None:
    blob = json.dumps(emitted)
    assert "must not be stored" not in blob
    assert "PONG" not in blob


@given("a collector that cannot be reached", target_fixture="dead")
def _dead_collector() -> str:
    return "http://127.0.0.1:1"


@when("the estate adapter emits through it")
def _emit_through_dead(dead: str) -> None:
    client = Emitter(dead, "invalid", IDENTITY, timeout=0.05)
    client.emit("task.started")
    client.close()


@then("the adapter returns without raising")
def _no_raise() -> None:
    assert True
