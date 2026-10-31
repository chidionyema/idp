import json
import pathlib

from fleetview_backend import voice_intents as vi


CI_STATUS_YAML = 'name: ci-status\nclass: read\nargs:\n  pr: {type: string, default: ""}\nsteps:\n  - cmd: echo\n'
CI_ERRORS_YAML = 'name: ci.errors\nclass: read\nargs:\n  pr: {type: string, default: ""}\nsteps:\n  - cmd: echo\n'
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


# --- Face audit §8.5: the confirmation ladder is intent data, not a set ---


def test_undeclared_class_asks_first(env):
    # flux-reconcile declares no class: the safe default is to ask.
    assert vi.intent_class("flux-reconcile", env / "intents") == "mutate"
    # an intent that does not exist at all asks too.
    assert vi.intent_class("no-such-intent", env / "intents") == "mutate"
    r = vi.handle("run flux reconcile", "s-data-1")
    assert r["status"] == "pending_confirmation"


def test_class_read_runs_without_confirmation(env):
    (env / "intents" / "cost-today.yaml").write_text(
        "name: cost-today\nclass: read\nargs: {}\nsteps:\n  - cmd: echo\n"
    )
    assert vi.intent_class("cost-today", env / "intents") == "read"
    r = vi.handle("cost today", "s-data-2")
    assert r == vi.result("cost-today", "ok", "all green for cost-today")


def test_the_legacy_read_intents_are_stamped_in_their_own_yaml(monkeypatch):
    # The eight intents the deleted READ_ONLY set named must now carry the
    # stamp in their own YAML on the repo tree, or the voice would start
    # asking permission for reads that never needed it.
    monkeypatch.delenv("FLEETVIEW_INTENTS_DIR")
    for name in [
        "ci.errors",
        "ci.status",
        "cost-today",
        "friction-report",
        "git-log",
        "lane",
        "router-status",
        "voice-turns",
        "ledger-verify",
    ]:
        assert vi.intent_class(name) == "read", name


# --- Face audit §8.6: the voice agent target is config, not a literal ---


def test_agent_job_target_comes_from_config(env, monkeypatch):
    from fleetview_backend import agent_jobs

    seen = []

    def spy_validate(task, agent):
        seen.append(("validate", agent))
        return task, agent

    def spy_submit(task, agent, by=""):
        seen.append(("submit", agent))
        return {"run_id": "run-123", "duplicate": False}, 200

    monkeypatch.setattr(agent_jobs, "validate", spy_validate)
    monkeypatch.setattr(agent_jobs, "submit", spy_submit)
    monkeypatch.setenv("FLEETVIEW_VOICE_AGENT", "claude-code")

    r = vi.handle("give an agent a job list the lanes", "s-data-3")
    assert r["status"] == "pending_confirmation"
    r2 = vi.handle("yes", "s-data-3")
    assert r2["status"] == "ok"
    assert seen == [("validate", "claude-code"), ("submit", "claude-code")]


def test_agent_job_target_outside_the_registry_is_refused(env, monkeypatch):
    # The configured name must still be one the registry knows.
    monkeypatch.setenv("FLEETVIEW_VOICE_AGENT", "otto")
    r = vi.handle("give an agent a job list the lanes", "s-data-4")
    assert r["status"] == "error"
    assert "Harness must be one of" in r["text"]


def test_agent_job_target_defaults_to_pi(env, monkeypatch):
    from fleetview_backend import agent_jobs

    seen = []
    monkeypatch.setattr(agent_jobs, "validate", lambda t, a: seen.append(a) or (t, a))
    monkeypatch.delenv("FLEETVIEW_VOICE_AGENT", raising=False)
    r = vi.handle("give an agent a job list the lanes", "s-data-5")
    assert r["status"] == "pending_confirmation"
    assert seen == ["pi"]


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
    # An expired yes used to fall through to the model, which answered with nothing (HTTP 204 and an
    # empty body) -- measured on the public path 2026-10-23T07:47Z, two minutes after an
    # intent+args confirmation. Silence is not an answer; the expiry is said out loud instead.
    monkeypatch.setattr(vi, "PENDING_TTL_S", -1.0)
    vi.handle("run flux reconcile", "s5")
    r = vi.handle("yes", "s5")
    assert r["status"] == "expired"
    assert "expired" in r["text"]
    assert vi.handle("yes", "s5") is None


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
            # EPIC-IDP-090 S1: a run may carry arguments, and the audit has to show that it did
            # without recording a value (a value can be a token). No arguments, empty list.
            "arg_names",
        }
        assert rec["arg_names"] == []
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


def test_how_is_the_lane_runs_the_lane_intent_but_never_steals_longer_names(
    monkeypatch,
):
    monkeypatch.delenv("FLEETVIEW_INTENTS_DIR", raising=False)
    cat = vi.load_catalog()
    assert "lane" in cat and vi.intent_class("lane") == "read"
    assert vi.match("How's the lane?", cat) == "lane"
    assert vi.match("router lane health", cat) == "router-lane-health"


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


def _frames(text: str) -> list[tuple[str, dict]]:
    out = []
    for frame in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_stream_runs_a_named_intent(env, client):
    # The face talks to /voice/stream, not /voice/intent: a named intent must run there too.
    r = client.post(
        "/voice/stream", json={"question": "check ci status", "session_id": "s1"}
    )
    assert r.status_code == 200
    frames = _frames(r.text)
    assert frames[0] == (
        "intent",
        vi.result("ci-status", "ok", "all green for ci-status"),
    )
    assert frames[1] == ("delta", {"text": "all green for ci-status"})
    assert frames[-1][0] == "done"


def test_stream_risky_intent_waits_for_spoken_yes(env, client):
    r = client.post(
        "/voice/stream", json={"question": "run flux reconcile", "session_id": "s2"}
    )
    assert _frames(r.text)[0][1]["status"] == "pending_confirmation"
    r = client.post("/voice/stream", json={"question": "yes", "session_id": "s2"})
    assert _frames(r.text)[0][1]["status"] == "ok"


def test_a_json_answer_is_spoken_by_its_summary(env):
    _write_stub(
        env / "estate-execute",
        '#!/bin/sh\nprintf \'{\\n  "summary": "CI on main: 38 passed, all green.",\\n  "failed": 0\\n}\\n\'\n',
    )
    r = vi.handle("check ci status", "s9")
    assert r["text"] == "CI on main: 38 passed, all green."


def test_catalogue_lists_arg_free_intents_with_read_only_flag(env):
    cat = {c["name"]: c for c in vi.catalogue()}
    assert "ci-status" in cat and cat["ci-status"]["read_only"] is True
    assert cat["flux-reconcile"]["read_only"] is False
    # an intent that needs an argument, and a malformed file, are not offered
    assert "git.branch" not in cat and "broken" not in cat
    assert [c["name"] for c in vi.catalogue()] == sorted(cat)


def test_catalogue_is_empty_not_an_error_when_the_directory_is_missing(env, tmp_path):
    assert vi.catalogue(tmp_path / "nope") == []


def test_catalogue_route(env, client):
    r = client.get("/voice/intents")
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["intents"]]
    assert "ci-status" in names and "git.branch" not in names
