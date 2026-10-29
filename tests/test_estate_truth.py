"""The truth instrument's rules, proved offline.

    pytest tests/test_estate_truth.py

The estate had a process for ownership (claims) and a process for code (gates, CI, Greenlane)
and no process for truth: nothing standing said whether the founder's own path answered, so on
2026-10-29 every gate was green while the router answered nothing. These tests pin the rules
that make the instrument worth having -- above all the one the founder stated: UNKNOWN IS NEVER
OK, so the estate cannot be reported healthy by omission.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
ENGINE = IDP / "platform" / "estate" / "libexec" / "estate-truth.py"
CONTRACT = IDP / "catalog" / "truth-contract.json"

OK = "MEASURED_OK"
FAIL = "MEASURED_FAIL"
UNKNOWN = "UNKNOWN"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_truth", str(ENGINE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


truth = _load()


# ---------------------------------------------------------------- the law


def test_unknown_is_never_ok():
    """The whole point: a predicate nobody could measure counts against the verdict."""
    results = [
        {"verdict": OK},
        {"verdict": UNKNOWN},
    ]
    assert truth.verdict_of(results) == UNKNOWN
    assert truth.verdict_of([{"verdict": OK}, {"verdict": OK}]) == OK


def test_a_failure_beats_an_unknown():
    results = [{"verdict": UNKNOWN}, {"verdict": FAIL}, {"verdict": OK}]
    assert truth.verdict_of(results) == FAIL


def test_the_verdict_is_total():
    """Every verdict is one of the three, and an empty set is not a pass."""
    assert truth.verdict_of([]) == OK  # nothing asked is nothing failed
    for verdict in (OK, FAIL, UNKNOWN):
        assert truth.verdict_of([{"verdict": verdict}]) in (OK, FAIL, UNKNOWN)


def test_counts_name_every_verdict():
    counts = truth.counts_of([{"verdict": OK}, {"verdict": FAIL}, {"verdict": UNKNOWN}])
    assert counts == {OK: 1, FAIL: 1, UNKNOWN: 1}


# ---------------------------------------------------------------- the kinds


class _Handler(BaseHTTPRequestHandler):
    status = 200
    payload = b'{"choices": [{"message": {"content": "PONG"}}]}'

    def do_POST(self):  # noqa: N802 -- the http.server API
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *args):  # noqa: D102 -- the test server does not need a log
        return


@pytest.fixture()
def server():
    holder = {}

    def start(status, payload=b'{"choices": [{"message": {"content": "PONG"}}]}'):
        _Handler.status = status
        _Handler.payload = payload
        httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        holder["url"] = (
            "http://127.0.0.1:%d/v1/chat/completions" % httpd.server_address[1]
        )
        holder["server"] = httpd
        return holder["url"]

    yield start
    if "server" in holder:
        holder["server"].shutdown()


def test_a_real_answer_is_ok(server):
    url = server(200)
    verdict, detail, _ = truth.eval_http(
        {
            "url": url,
            "method": "POST",
            "body": {"model": "default"},
            "expect_status": 200,
            "expect_contains": "PONG",
            "timeout_s": 10,
        }
    )
    assert verdict == OK
    assert "200" in detail


def test_a_refusal_is_a_failure_not_an_unknown(server):
    """The verdict is about the ANSWER: a 401 is a measurement of a broken path."""
    url = server(401, b'{"error": "no"}')
    verdict, detail, _ = truth.eval_http(
        {
            "url": url,
            "method": "POST",
            "body": {},
            "expect_status": 200,
            "timeout_s": 10,
        }
    )
    assert verdict == FAIL
    assert "401" in detail


def test_a_path_that_answers_without_the_credential_is_unknown():
    """The endpoint answering is not the founder's credentialed path answering."""
    verdict, detail, _ = truth.eval_http(
        {
            "url": "http://127.0.0.1:1/v1/chat/completions",
            "method": "POST",
            "body": {},
            "expect_status": 200,
            "timeout_s": 2,
            "auth_env": "ESTATE_TRUTH_NO_SUCH_CREDENTIAL",
        }
    )
    assert verdict in (FAIL, UNKNOWN)
    assert "ESTATE_TRUTH_NO_SUCH_CREDENTIAL" in detail or "no answer" in detail


def test_a_command_that_answers_is_ok():
    verdict, detail, _ = truth.eval_command(
        {
            "command": ["/bin/sh", "-c", "echo PONG"],
            "expect_rc": 0,
            "expect_contains": "PONG",
        }
    )
    assert verdict == OK


def test_a_command_that_fails_is_a_failure():
    verdict, detail, _ = truth.eval_command(
        {"command": ["/bin/sh", "-c", "echo boom >&2; exit 3"], "expect_rc": 0}
    )
    assert verdict == FAIL
    assert "exit 3" in detail


def test_a_command_that_is_not_installed_is_unknown():
    verdict, detail, _ = truth.eval_command(
        {"command": ["estate-truth-no-such-binary"]}
    )
    assert verdict == UNKNOWN
    assert "not installed" in detail


# ---------------------------------------------------------------- the ledger


def test_every_declared_lane_is_accounted_for(tmp_path):
    lanes = tmp_path / "lanes.json"
    lanes.write_text(
        json.dumps({"declared": ["a", "b"], "served": ["a"], "refused": ["b"]})
    )
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == OK
    assert "accounted" in detail


def test_a_refusal_that_carries_its_reason_is_still_a_refusal(tmp_path):
    """The router refuses a lane with an OBJECT that names the lane and the reason.

    Measured 2026-10-29: the instrument did set arithmetic over the refusal list as if every
    entry were a plain name, so `set(refused)` raised `TypeError: unhashable type: 'dict'` and
    the predicate answered UNKNOWN -- the instrument could not read a ledger the router had
    just written, because the ledger refused a lane the way it is supposed to: with the reason.
    """
    lanes = tmp_path / "lanes.json"
    lanes.write_text(
        json.dumps(
            {
                "declared": ["a", "b"],
                "served": ["a"],
                "refused": [
                    {
                        "lane": "b",
                        "reason": "credential ZAI_API_KEY absent",
                        "verdict": "MEASURED_FAIL",
                    }
                ],
            }
        )
    )
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == OK, detail
    assert "1 refused" in detail


def test_a_lane_that_is_neither_served_nor_refused_is_a_failure(tmp_path):
    """The defect this instrument exists to catch: a declared capability that is simply absent."""
    lanes = tmp_path / "lanes.json"
    lanes.write_text(json.dumps({"declared": ["voice"], "served": [], "refused": []}))
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == FAIL
    assert "voice" in detail


def test_the_old_flat_lane_list_is_a_failure(tmp_path):
    lanes = tmp_path / "lanes.json"
    lanes.write_text(json.dumps(["claude-*", "default"]))
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == FAIL
    assert "declared" in detail


def test_a_missing_state_file_is_a_failure(tmp_path):
    verdict, detail, _ = truth.eval_file(
        {"path": str(tmp_path / "absent.json"), "assert": "exists"}
    )
    assert verdict == FAIL
    assert "absent" in detail


def test_the_memory_door_needs_a_door(tmp_path):
    manifest = tmp_path / "runtimes.json"
    manifest.write_text(json.dumps({"server": "estate-memory"}))
    verdict, detail, _ = truth.eval_file(
        {"path": str(manifest), "assert": "door_present"}
    )
    assert verdict == FAIL
    assert "door" in detail

    manifest.write_text(json.dumps({"door": {"url": "http://127.0.0.1:9/mcp"}}))
    verdict, detail, _ = truth.eval_file(
        {"path": str(manifest), "assert": "door_present"}
    )
    assert verdict == OK


# ---------------------------------------------------------------- scope


def test_a_predicate_from_another_scope_is_unknown():
    contract = {
        "predicates": [
            {
                "id": "cluster.only",
                "kind": "file",
                "scope": "cluster",
                "path": "/nonexistent",
                "assert": "exists",
            }
        ]
    }
    results = truth.measure(contract, scope="laptop")
    assert len(results) == 1
    assert results[0]["verdict"] == UNKNOWN
    assert "cluster" in results[0]["detail"]


def test_the_aggregate_never_reports_ok_while_something_is_unknown():
    contract = {
        "predicates": [
            {
                "id": "a",
                "kind": "file",
                "scope": "any",
                "path": "/nonexistent",
                "assert": "exists",
            },
            {
                "id": "b",
                "kind": "file",
                "scope": "cluster",
                "path": "/nonexistent",
                "assert": "exists",
            },
        ]
    }
    results = truth.measure(contract, scope="laptop")
    report = truth.snapshot(contract, results, "laptop")
    assert report["verdict"] != OK
    assert report["ok"] is False


# ---------------------------------------------------------------- the contract itself


def test_the_contract_is_well_formed():
    doc = json.loads(CONTRACT.read_text())
    assert doc.get("version")
    ids = [p["id"] for p in doc["predicates"]]
    assert ids, "the contract declares no predicates"
    assert len(ids) == len(set(ids)), "a predicate id is declared twice"
    for pred in doc["predicates"]:
        assert pred.get("kind") in truth.EVALUATORS, pred
        assert pred.get("scope") in ("any", "laptop", "cluster"), pred
        assert pred.get("summary"), pred
    for path, wanted in doc["paths"].items():
        assert path
        for pid in wanted:
            assert pid in ids, "%s names an unknown predicate %s" % (path, pid)


def test_the_contract_does_not_ask_for_a_secret_to_be_printed():
    """No predicate may name a secret VALUE, only the env var that carries it."""
    doc = json.loads(CONTRACT.read_text())
    for pred in doc["predicates"]:
        auth = pred.get("auth_env")
        if auth:
            assert auth.isupper(), auth
        for value in (pred.get("body") or {}).values():
            assert "sk-" not in str(value)
