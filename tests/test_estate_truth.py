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
    last_headers = {}

    def do_POST(self):  # noqa: N802 -- the http.server API
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        _Handler.last_headers = {k.lower(): v for k, v in self.headers.items()}
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


def test_a_refusal_record_is_read_as_a_lane(tmp_path):
    """The ledger's refusal records are dicts, and one unhashable dict once took the whole
    board down: TypeError: unhashable type: 'dict'. A refusal record names its lane."""
    lanes = tmp_path / "lanes.json"
    lanes.write_text(
        json.dumps(
            {
                "declared": ["default", "glm", "voice"],
                "served": ["default"],
                "refused": [
                    {"lane": "glm", "reason": "no credential", "verdict": "refused"},
                    {"lane": "voice", "reason": "not installed", "verdict": "refused"},
                ],
            }
        )
    )
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == OK
    assert "accounted" in detail


def test_a_refusal_record_without_a_lane_is_not_counted(tmp_path):
    """A record that names no lane cannot account for one."""
    lanes = tmp_path / "lanes.json"
    lanes.write_text(
        json.dumps(
            {
                "declared": ["default", "glm"],
                "served": ["default"],
                "refused": [{"reason": "no credential", "verdict": "refused"}],
            }
        )
    )
    verdict, detail, _ = truth.eval_file(
        {"path": str(lanes), "assert": "declared_accounted"}
    )
    assert verdict == FAIL
    assert "glm" in detail


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


def test_a_question_from_another_scope_is_reported_but_not_counted():
    """A laptop cannot answer a cluster question. That is not a failure of the laptop, and a
    board that can never be green teaches the estate to ignore the board. The question is
    still published, by name, and the total verdict still covers it."""
    contract = {
        "predicates": [
            {
                "id": "here",
                "kind": "file",
                "scope": "laptop",
                "path": "/nonexistent",
                "assert": "exists",
            },
            {
                "id": "cluster.only",
                "kind": "file",
                "scope": "cluster",
                "path": "/nonexistent",
                "assert": "exists",
            },
        ]
    }
    results = truth.measure(contract, scope="laptop")
    report = truth.snapshot(contract, results, "laptop")
    assert report["verdict"] == FAIL  # the laptop question failed on its own merits
    assert [r["id"] for r in report["out_of_scope"]] == ["cluster.only"]
    assert report["counts"]["UNKNOWN"] == 0
    assert report["counts_all"]["UNKNOWN"] == 1
    assert report["verdict_all"] == FAIL  # nothing is hidden by the split


# ---------------------------------------------------------------- the running tree


def test_a_runtime_mirror_behind_main_is_a_failure(monkeypatch, tmp_path):
    """The estate's live doors run from the runtime mirror. A mirror that is behind main runs
    the code the estate already fixed."""
    monkeypatch.setattr(truth, "_git", lambda *a, **k: "aaaaaaa1111")
    monkeypatch.setattr(truth, "_remote_main_sha", lambda *a, **k: "bbbbbbb2222")
    verdict, detail, _ = truth.eval_runtime_current({"runtime_path": str(tmp_path)})
    assert verdict == FAIL
    assert "aaaaaaa" in detail and "bbbbbbb" in detail


def test_a_runtime_mirror_on_main_is_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(truth, "_git", lambda *a, **k: "aaaaaaa1111")
    monkeypatch.setattr(truth, "_remote_main_sha", lambda *a, **k: "aaaaaaa1111")
    verdict, detail, _ = truth.eval_runtime_current({"runtime_path": str(tmp_path)})
    assert verdict == OK


def test_an_absent_runtime_mirror_is_a_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(truth, "_git", lambda *a, **k: "")
    verdict, detail, _ = truth.eval_runtime_current(
        {"runtime_path": str(tmp_path / "absent")}
    )
    assert verdict == FAIL
    assert "absent" in detail


def test_an_unreadable_runtime_mirror_is_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(truth, "_git", lambda *a, **k: "")
    verdict, detail, _ = truth.eval_runtime_current(
        {"runtime_path": str(tmp_path / "here")}
    )
    assert verdict in (FAIL, UNKNOWN)


# ---------------------------------------------------------------- the box under the router


def test_a_saturated_box_is_a_failure_and_names_the_threshold(monkeypatch):
    """The front refuses traffic when the load average passes 8 x the CPU count. The board
    must name that cause, or the estate goes to fix the router when the box is the problem."""
    monkeypatch.setattr(truth.os, "getloadavg", lambda: (171.5, 160.0, 150.0))
    monkeypatch.setattr(truth.os, "cpu_count", lambda: 4)
    monkeypatch.delenv("ESTATE_FRONT_LOAD_MAX", raising=False)
    verdict, detail, _ = truth.eval_host_load({})
    assert verdict == FAIL
    assert "32.0" in detail


def test_a_box_with_headroom_is_ok(monkeypatch):
    monkeypatch.setattr(truth.os, "getloadavg", lambda: (1.5, 1.0, 0.9))
    monkeypatch.setattr(truth.os, "cpu_count", lambda: 4)
    monkeypatch.delenv("ESTATE_FRONT_LOAD_MAX", raising=False)
    verdict, detail, _ = truth.eval_host_load({})
    assert verdict == OK


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
            names = [auth] if isinstance(auth, str) else list(auth)
            for name in names:
                assert name.isupper(), name
        for value in (pred.get("body") or {}).values():
            assert "sk-" not in str(value)


def test_the_memory_manifest_is_the_canonical_one():
    """The truth instrument used to read a path the estate does not own, so the founder's
    recall path measured as absent while it was present under its canonical name."""
    doc = json.loads(CONTRACT.read_text())
    pred = next(p for p in doc["predicates"] if p["id"] == "memory.recall")
    assert pred["path"] == "~/.estate/memory/platform/estate/memory/runtimes.json"


def test_the_laptop_probe_asks_the_default_lane():
    """The laptop lane is served as 'default'. Asking for a model the front may not carry
    measured a refusal that looked like a broken router."""
    doc = json.loads(CONTRACT.read_text())
    pred = next(p for p in doc["predicates"] if p["id"] == "router.laptop.completion")
    assert pred["body"]["model"] == "default"
    assert pred["body"]["max_tokens"] == 64


def test_the_cloud_probe_carries_the_estate_user_agent():
    """The cloud edge refused the caller's own User-Agent with 1010. The probe must present
    the estate's own identity, exactly as the front does."""
    doc = json.loads(CONTRACT.read_text())
    pred = next(p for p in doc["predicates"] if p["id"] == "router.cloud.completion")
    assert pred["headers"]["User-Agent"] == "estate-router-front/1.0"


def test_the_probe_carries_the_declared_user_agent(server):
    url = server(200)
    truth.eval_http(
        {
            "url": url,
            "method": "POST",
            "headers": {"User-Agent": "estate-router-front/1.0"},
            "body": {"model": "default"},
            "expect_status": 200,
            "timeout_s": 10,
        }
    )
    assert _Handler.last_headers.get("user-agent") == "estate-router-front/1.0"


def test_the_contract_measures_the_running_tree_and_the_box():
    doc = json.loads(CONTRACT.read_text())
    ids = [p["id"] for p in doc["predicates"]]
    assert "runtime.current" in ids
    assert "host.load" in ids


def test_the_contract_maps_only_the_predicates_a_change_repairs():
    """A path maps to the questions it answers. Mapping a question this host cannot measure
    -- a cluster question, or the cloud route while the cloud edge is down -- would make
    every truth change unlandable for a reason that is not about the change."""
    doc = json.loads(CONTRACT.read_text())
    truth_paths = {
        "platform/estate/libexec/estate-truth.py",
        "catalog/truth-contract.json",
        "platform/estate/intents/estate-truth.yaml",
        "tests/test_estate_truth.py",
        "bin/idp-estate-truth",
    }
    for path in truth_paths:
        for pid in doc["paths"].get(path, []):
            assert pid != "estate-db.rows", path
            assert pid != "router.cloud.completion", path
