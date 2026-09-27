import json
import os
import stat
import pathlib

from fleetview_backend import voice_intents as vi


CI_STATUS_YAML = (
    'name: ci-status\nargs:\n  pr: {type: string, default: ""}\nsteps:\n  - cmd: echo\n'
)
CI_ERRORS_YAML = (
    'name: ci.errors\nargs:\n  pr: {type: string, default: ""}\nsteps:\n  - cmd: echo\n'
)
STATUS_YAML = "name: status\nsteps:\n  - cmd: echo\n"
GIT_BRANCH_YAML = (
    "name: git.branch\nargs:\n  name: {type: string}\nsteps:\n  - cmd: echo\n"
)
FLUX_RECONCILE_YAML = "name: flux-reconcile\nsteps:\n  - cmd: echo\n"
BROKEN_YAML = ": : not yaml ["

STUB_OK = '#!/bin/sh\necho "running $1"\necho "all green for $1"\n'
STUB_FAIL = "#!/bin/sh\necho boom >&2\nexit 3\n"


def _write_stub(path: pathlib.Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(0o755)


import pytest


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    intents_dir = tmp_path / "intents"
    intents_dir.mkdir()
    (intents_dir / "ci-status.yaml").write_text(CI_STATUS_YAML)
    (intents_dir / "ci.errors.yaml").write_text(CI_ERRORS_YAML)
    (intents_dir / "status.yaml").write_text(STATUS_YAML)
    (intents_dir / "git.branch.yaml").write_text(GIT_BRANCH_YAML)
    (intents_dir / "flux-reconcile.yaml").write_text(FLUX_RECONCILE_YAML)
    (intents_dir / "broken.yaml").write_text(BROKEN_YAML)

    stub = tmp_path / "estate-execute"
    _write_stub(stub, STUB_OK)

    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(intents_dir))
    monkeypatch.setenv("ESTATE_EXECUTE", str(stub))
    monkeypatch.setenv("FLEETVIEW_INTENT_LOG", str(tmp_path / "audit.jsonl"))

    vi._PENDING.clear()
    yield tmp_path
    vi._PENDING.clear()


def test_check_ci_status_matches_ci_status(env):
    catalog = vi.load_catalog()
    assert vi.match("Check CI status!", catalog) == "ci-status"


def test_arg_requiring_intents_never_match(env):
    catalog = vi.load_catalog()
    assert "git.branch" not in catalog
    assert vi.match("git branch", catalog) is None


def test_broken_yaml_is_skipped(env):
    assert vi.load_catalog() == ["ci-status", "ci.errors", "flux-reconcile", "status"]


def test_read_only_runs_at_once(env):
    r = vi.handle("check ci status", "s1")
    assert r == vi.result("ci-status", "ok", "all green for ci-status")
    assert r["visual"] == {"cue": "pulse", "target": "fleet", "severity": "info"}
    assert r["ticket"] is None


def test_risky_asks_then_yes_runs(env):
    r = vi.handle("run flux reconcile", "s2")
    assert r["status"] == "pending_confirmation"
    assert r["text"] == "Run flux-reconcile? Say yes to confirm."
    assert r["visual"]["cue"] == "shield_flash"
    assert r["visual"]["severity"] == "warn"

    r2 = vi.handle("Yes.", "s2")
    assert r2["status"] == "ok"
    assert r2["text"] == "all green for flux-reconcile"
    assert r2["visual"]["cue"] == "pulse"


def test_no_cancels(env):
    vi.handle("run flux reconcile", "s3")
    r = vi.handle("no", "s3")
    assert r["status"] == "cancelled"
    assert r["visual"]["cue"] == "comet_spawn"
    assert r["visual"]["severity"] == "info"

    r2 = vi.handle("yes", "s3")
    assert r2 is None


def test_other_speech_drops_pending(env):
    vi.handle("run flux reconcile", "s4")
    r = vi.handle("how many agents", "s4")
    assert r is None
    r2 = vi.handle("yes", "s4")
    assert r2 is None


def test_pending_expires(env, monkeypatch):
    monkeypatch.setattr(vi, "PENDING_TTL_S", -1.0)
    vi.handle("run flux reconcile", "s5")
    r = vi.handle("yes", "s5")
    assert r is None


def test_pending_is_per_session(env):
    vi.handle("run flux reconcile", "a")
    r = vi.handle("yes", "b")
    assert r is None
    r2 = vi.handle("yes", "a")
    assert r2["status"] == "ok"


def test_missing_binary_is_error(env, monkeypatch):
    monkeypatch.setenv("ESTATE_EXECUTE", str(env / "nope"))
    r = vi.handle("check ci status", "s6")
    assert r == vi.result("ci-status", "error", "Intents run on the laptop only.")
    assert r["visual"]["cue"] == "burn"
    assert r["visual"]["severity"] == "danger"


def test_failing_intent_is_error(env):
    stub = env / "estate-execute"
    _write_stub(stub, STUB_FAIL)
    r = vi.handle("check ci status", "s_fail")
    assert r["status"] == "error"
    assert r["text"] == "ci status failed. boom"
    assert r["visual"]["cue"] == "burn"


def test_audit_line_per_run_and_refusal(env):
    vi.handle("run flux reconcile", "s2")
    vi.handle("Yes.", "s2")

    audit_path = env / "audit.jsonl"
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    for rec in records:
        assert set(rec.keys()) == {
            "ts",
            "session_id",
            "utterance",
            "intent",
            "status",
            "rc",
            "duration_ms",
        }
    assert [r["status"] for r in records] == ["pending_confirmation", "ok"]
    assert [r["rc"] for r in records] == [None, 0]
    assert [r["utterance"] for r in records] == ["run flux reconcile", "Yes."]


def test_no_match_is_none(env):
    r = vi.handle("how are the agents doing", "s7")
    assert r is None
    assert not (env / "audit.jsonl").exists()


def test_real_committed_catalog(env, monkeypatch):
    monkeypatch.delenv("FLEETVIEW_INTENTS_DIR")
    cat = vi.load_catalog()
    assert "router-status" in cat
    assert "git.branch" not in cat


@pytest.fixture
def client():
    import sys
    import types

    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fastapi.testclient import TestClient

    from fleetview_backend import serve

    return TestClient(serve.build_app())


def test_route_runs_intent(env, client):
    r = client.post(
        "/voice/intent", json={"text": "check ci status", "session_id": "r1"}
    )
    assert r.status_code == 200
    assert r.json() == vi.result("ci-status", "ok", "all green for ci-status")


def test_route_no_intent_is_204(env, client):
    r = client.post(
        "/voice/intent", json={"text": "how many agents", "session_id": "r2"}
    )
    assert r.status_code == 204
    assert r.content == b""


def test_route_empty_body_is_204(env, client):
    r = client.post(
        "/voice/intent",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 204


def test_route_confirm_flow(env, client):
    r = client.post(
        "/voice/intent", json={"text": "run flux reconcile", "session_id": "r3"}
    )
    assert r.json()["status"] == "pending_confirmation"

    r2 = client.post("/voice/intent", json={"text": "yes", "session_id": "r3"})
    assert r2.json()["status"] == "ok"
