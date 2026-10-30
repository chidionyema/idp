"""A spoken turn is attributable: the session that spoke it reaches the door.

Issue #7579, repair R1. The pod hands a spoken intent to the laptop carrying `session_id`, and
the laptop's `voice_intents.execute()` dropped it: the child was `[exe, intent]` with no
identity, so the intent door resolved nothing and recorded the run as `anonymous`. The founder's
voice was unattributable work at the one door that governs it (idp#7518's blind spot, on the
production path).

These are falsifiers, not documentation: before the fix they FAIL, after it they PASS. They pin
four things the voice path must be true of:

  * the session that spoke reaches the door, twice -- as the explicit `--session` flag the door
    treats as authoritative, and in the child's environment, so a child that re-execs keeps it;
  * the voice session is namespaced (`voice:<id>`), so it can never be mistaken for an agent's
    plan session and refused for having declared no plan;
  * the run is recorded under that namespaced session in the door's own durable ledger, with the
    real door, not a stand-in;
  * a caller with no session is unchanged: identity-less automation still runs, unattributed,
    because a gate that refuses anonymous work is an outage.
"""

import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

from fleetview_backend import voice_intents as vi

REPO = Path(__file__).resolve().parents[4]
DOOR = REPO / "platform" / "estate" / "bin" / "estate-execute"
PLAN = REPO / "platform" / "estate" / "memory" / "plan.py"

CI_STATUS_YAML = """name: ci-status
description: CI status for a branch.
args:
  repo:
    type: string
    default: idp
    description: Which repository.
steps:
  - cmd: echo
"""

PR_STATUS_YAML = """name: pr-status
description: Report one pull request.
args:
  pr:
    type: integer
    description: The pull request number.
  repo:
    type: string
    default: idp
    description: Which repository.
steps:
  - cmd: echo
"""


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture()
def estate(tmp_path, monkeypatch):
    """A stand-in door that records the argv and the environment it was handed."""
    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "ci-status.yaml").write_text(CI_STATUS_YAML)
    (intents / "pr-status.yaml").write_text(PR_STATUS_YAML)
    log = tmp_path / "argv.jsonl"
    exe = tmp_path / "estate-execute"
    exe.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, sys\n"
        "open(" + repr(str(log)) + ", 'a').write(json.dumps({'argv': sys.argv[1:], "
        "'session_env': os.environ.get('ESTATE_SESSION_ID', '')}) + '\\n')\n"
        "print('did the thing')\n"
    )
    exe.chmod(0o755)
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(intents))
    monkeypatch.setenv("ESTATE_EXECUTE", str(exe))
    monkeypatch.setenv("FLEETVIEW_INTENT_LOG", str(tmp_path / "audit.jsonl"))
    vi._PENDING.clear()
    vi._REMOTE_PENDING.clear()
    yield {"log": log, "audit": tmp_path / "audit.jsonl"}
    vi._PENDING.clear()
    vi._REMOTE_PENDING.clear()


def ran(state):
    if not state["log"].exists():
        return []
    return [json.loads(line) for line in state["log"].read_text().splitlines() if line]


# --- the session reaches the child ---------------------------------------
def test_a_spoken_intent_reaches_the_door_naming_its_caller(estate):
    answer = vi.handle("ci status", "s-42")
    assert answer["status"] == "ok", answer
    calls = ran(estate)
    assert len(calls) == 1
    argv = calls[0]["argv"]
    assert argv[:2] == ["ci-status", "--session"]
    assert argv[2] == "voice:s-42"


def test_the_session_also_travels_in_the_childs_environment(estate):
    vi.handle("ci status", "s-42")
    assert ran(estate)[0]["session_env"] == "voice:s-42"


def test_the_confirmation_path_carries_the_same_session(estate):
    asked = vi.handle("pr status", "s-7", {"pr": 42})
    assert asked["status"] == "pending_confirmation"
    assert ran(estate) == []
    vi.handle("yes", "s-7")
    argv = ran(estate)[0]["argv"]
    assert argv[:2] == ["pr-status", "--session"]
    assert argv[2] == "voice:s-7"


def test_the_explicit_session_beats_an_inherited_environment(estate, monkeypatch):
    """The child's environment is rebuilt, so an inherited id cannot outlive the spoken one."""
    monkeypatch.setenv("ESTATE_SESSION_ID", "someone-elses-session")
    vi.handle("ci status", "s-42")
    call = ran(estate)[0]
    assert call["argv"][2] == "voice:s-42"
    assert call["session_env"] == "voice:s-42"


def test_a_caller_with_no_session_stays_identity_less(estate):
    """Automation with no session still runs, and stays unattributed. Nothing here traps it."""
    status, text, rc, _dur = vi.execute("ci-status", {"repo": "idp"})
    assert (status, rc) == ("ok", 0), text
    call = ran(estate)[0]
    assert call["argv"] == ["ci-status", "--repo=idp"]
    assert call["session_env"] == ""


# --- the namespace --------------------------------------------------------
def test_a_voice_session_is_namespaced(estate):
    assert vi.estate_session_id("s-42") == "voice:s-42"
    assert vi.estate_session_id("") == ""
    assert vi.estate_session_id("   ") == ""
    assert vi.estate_session_id("voice:s-42") == "voice:s-42"


def test_a_voice_session_can_never_resolve_to_a_plan_ledger(tmp_path, monkeypatch):
    """The door refuses a session that has a ledger and has declared no plan. A voice session
    must never look like one, or a founder's spoken command would be refused for a plan it
    never had a way to declare."""
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    module = _load("voice_session_plan", PLAN)
    assert module.ledger_exists("voice:s-42") is False
    assert module.ledger_exists("s-42") is False


# --- the real door --------------------------------------------------------
def test_the_real_door_records_the_voice_session_in_its_own_ledger(
    tmp_path, monkeypatch
):
    """End to end: the voice path runs the real door, and the door's durable intent ledger
    names the voice session. A stand-in door would prove only that this file builds an argv."""
    home = tmp_path / "home"
    intents = home / ".estate" / "intents"
    intents.mkdir(parents=True)
    (intents / "probe.yaml").write_text(
        "name: probe\ndescription: reads only\ndoor_s: 20\nsteps:\n"
        "  - name: read\n    cmd: git --version\n"
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(intents))
    monkeypatch.setenv("ESTATE_EXECUTE", str(DOOR))
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(home / ".estate" / "plans"))
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    # The door reads its intents with PyYAML, which this host installs into the USER site
    # packages -- and the user site is derived from HOME, which this test moves aside.
    site = str(Path(yaml.__file__).resolve().parents[1])
    monkeypatch.setenv(
        "PYTHONPATH",
        site
        + (
            os.pathsep + os.environ["PYTHONPATH"]
            if os.environ.get("PYTHONPATH")
            else ""
        ),
    )
    vi._PENDING.clear()

    status, text, rc, _dur = vi.execute("probe", session_id="s-42")
    assert (status, rc) == ("ok", 0), text

    ledger = home / ".estate" / "plans" / "intents.jsonl"
    assert ledger.exists(), "the door recorded nothing"
    lines = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()]
    assert lines[-1]["session"] == "voice:s-42"
    assert lines[-1]["intent"] == "probe"
