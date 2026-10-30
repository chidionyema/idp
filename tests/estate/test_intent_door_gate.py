"""The intent door must present the session that calls it, and reads must stay available.

Issue #7576. The MCP plugin `mcp/plugins/estate_mcp.py::_estate_invoke` shells out to
`~/.estate/bin/estate-execute` WITHOUT a session, so the intent door resolved no identity of
its own and a planless live session could reach work through an intent while the gate believed
it was talking to anonymous automation (idp#7518's blind spot).

These are falsifiers, not documentation: before the fix they FAIL (the mutating intent ran,
the refusal was never written, the child never saw a session), after it they PASS.

They cover three things the door must do:
  1. carry identity (explicit argument -> environment -> pointer -> anonymous);
  2. refuse work from a live session that declared no plan, and say so durably;
  3. keep reads, plan declarations and housekeeping available -- a gate that refuses reads is
     worse than no gate, because the estate learns to route around it.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
DOOR = REPO / "platform" / "estate" / "bin" / "estate-execute"
PLUGIN = REPO / "mcp" / "plugins" / "estate_mcp.py"


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture()
def plan(tmp_path, monkeypatch):
    """The real plan contract, with its ledger pointed at a temporary directory."""
    module = _load(
        "intent_door_plan", REPO / "platform" / "estate" / "memory" / "plan.py"
    )
    monkeypatch.setattr(module, "PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    return module


# --- classification ------------------------------------------------------
def test_leading_cd_is_not_work(plan):
    """`cd <dir> && git log` is a read. Treating the cd as a chain refused plain reads."""
    assert plan.is_read_only_command("cd /tmp && git log --oneline") is True
    assert plan.is_read_only_command("cd /tmp; git status") is True
    assert plan.is_read_only_command("cd /tmp && cd /var && git log") is True


def test_output_into_a_file_is_work(plan):
    """`git show x > out.yml` writes a file. The old classifier had no notion of redirection."""
    assert plan.is_read_only_command("git show HEAD:file > out.yml") is False
    assert (
        plan.is_read_only_command("cd /tmp && git show HEAD:file >> out.yml") is False
    )


def test_descriptor_duplication_is_not_a_write(plan):
    """`2>&1` moves a descriptor; it does not create a file."""
    assert plan.is_read_only_command("git status 2>&1") is True
    assert plan.is_read_only_command("git status >&2") is True


def test_a_chain_after_a_cd_is_still_work(plan):
    assert plan.is_read_only_command("cd /tmp && git log | head") is False


# --- the durable intent record -------------------------------------------
def test_every_invocation_is_recorded_with_a_session(plan, tmp_path):
    assert plan.record_intent("gh-api", "sess-1", source="intent-door") is True
    assert plan.record_intent("gh-api", "", source="intent-door") is True
    lines = [
        json.loads(x)
        for x in (tmp_path / "plans" / "intents.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert [x["session"] for x in lines] == ["sess-1", "anonymous"]
    assert lines[0]["intent"] == "gh-api"


# --- the door ------------------------------------------------------------
def _intents_dir(tmp_path, yaml_text):
    d = tmp_path / ".estate" / "intents"
    d.mkdir(parents=True, exist_ok=True)
    (d / "probe.yaml").write_text(yaml_text)
    return d


MUTATING = """
name: probe
description: writes a file
door_s: 20
steps:
  - name: write
    cmd: touch {marker}
"""

READING = """
name: probe
description: reads only
door_s: 20
steps:
  - name: read
    cmd: git --version
"""


def _run_door(tmp_path, yaml_text, session, marker=None):
    _intents_dir(tmp_path, yaml_text)
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["ESTATE_PLAN_LEDGER_DIR"] = str(tmp_path / "plans")
    env.pop("ESTATE_SESSION_ID", None)
    # The door reads its intents with PyYAML, which this host installs into the USER site
    # packages -- and the user site is derived from HOME, which the test moves aside. Say where
    # PyYAML lives instead of losing it.
    site = str(Path(yaml.__file__).resolve().parents[1])
    env["PYTHONPATH"] = site + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    cmd = [sys.executable, str(DOOR)]
    if session:
        cmd.extend(["--session", session])
    cmd.append("probe")
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=env, timeout=60, check=False
    )
    return proc


def _publish_live(tmp_path, monkeypatch, session):
    """Make the session a LIVE adapter session: it has a ledger, and no plan in it.

    The ledger's existence is what proves the runtime adapter is live for that session, so it
    is what makes a planless session REFUSABLE (idp#7518). Without it the door allows the work
    and records it, on purpose: a fence a correct machine cannot satisfy is an outage.
    """
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    module = _load(
        "intent_door_plan_live", REPO / "platform" / "estate" / "memory" / "plan.py"
    )
    assert module.publish_session(session)["ok"] is True
    assert module.ledger_exists(session) is True


def test_planless_live_session_is_refused_and_audited(tmp_path, monkeypatch):
    marker = tmp_path / "written.txt"
    _publish_live(tmp_path, monkeypatch, "sess-live")
    proc = _run_door(tmp_path, MUTATING.format(marker=marker), "sess-live")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "REFUSED" in proc.stderr
    assert "plan_not_declared" in proc.stderr
    assert not marker.exists(), "the refused command ran anyway"
    refusals = (tmp_path / "plans" / "refusals.jsonl").read_text()
    assert "sess-live" in refusals
    assert "plan_not_declared" in refusals


def test_the_refused_invocation_is_recorded_too(tmp_path, monkeypatch):
    marker = tmp_path / "written.txt"
    _publish_live(tmp_path, monkeypatch, "sess-live")
    _run_door(tmp_path, MUTATING.format(marker=marker), "sess-live")
    lines = [
        json.loads(x)
        for x in (tmp_path / "plans" / "intents.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert lines and lines[-1]["session"] == "sess-live"
    assert lines[-1]["intent"] == "probe"


def test_a_read_only_intent_stays_available_without_a_plan(tmp_path):
    proc = _run_door(tmp_path, READING, "sess-live")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "REFUSED" not in proc.stderr


def test_a_plan_declaration_is_not_work(tmp_path):
    yaml_text = """
name: probe
description: declares a plan
door_s: 20
steps:
  - name: declare
    cmd: estate-plan declare_plan '{"goal": "a goal long enough to count"}'
"""
    proc = _run_door(tmp_path, yaml_text, "sess-live")
    assert "REFUSED" not in proc.stderr, proc.stdout + proc.stderr


def test_anonymous_automation_is_allowed_and_recorded(tmp_path):
    marker = tmp_path / "written.txt"
    proc = _run_door(tmp_path, MUTATING.format(marker=marker), None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [
        json.loads(x)
        for x in (tmp_path / "plans" / "intents.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert lines[-1]["session"] == "anonymous"


# --- the plugin that shells out to the door ------------------------------
@pytest.fixture()
def plugin(tmp_path, monkeypatch):
    _intents_dir(tmp_path, READING)
    monkeypatch.setenv("ESTATE_INTENTS_DIR", str(tmp_path / ".estate" / "intents"))
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    module = _load("estate_mcp_under_test", PLUGIN)

    # No session is resolvable here: this process has no pointer file, and the real ledger dir
    # must not decide what this test means by "anonymous".
    class _NoSession:
        @staticmethod
        def resolve_session_id():
            return ""

    monkeypatch.setattr(module, "_PLAN_CONTRACT", _NoSession)
    monkeypatch.setattr(module, "_PLAN_CONTRACT_TRIED", True)
    return module


def test_the_plugin_schema_accepts_an_optional_session(plugin):
    schema = [t for t in plugin.TOOL_DEFS if t["name"] == "estate_invoke"][0][
        "inputSchema"
    ]
    assert "session_id" in schema["properties"]
    assert "session_id" not in schema.get("required", [])


def test_the_plugin_hands_the_session_to_the_child(plugin, monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env")
        return _Proc()

    monkeypatch.setattr(plugin.subprocess, "run", _run)
    plugin._estate_invoke({"intent": "probe", "session_id": "sess-explicit"})
    assert "--session" in seen["cmd"]
    assert seen["cmd"][seen["cmd"].index("--session") + 1] == "sess-explicit"
    assert seen["env"]["ESTATE_SESSION_ID"] == "sess-explicit"


def test_the_plugin_leaves_anonymous_automation_unattributed(plugin, monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env")
        return _Proc()

    monkeypatch.setattr(plugin.subprocess, "run", _run)
    plugin._estate_invoke({"intent": "probe"})
    assert "--session" not in seen["cmd"]
