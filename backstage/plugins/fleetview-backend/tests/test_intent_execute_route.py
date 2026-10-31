"""The laptop's programmatic intent door: one committed intent, one credential, one owner.

Issue #7579, repair R2. The estate-mcp pod ships the intent LIBRARY and no executor and no plan
ledger, so the production `estate_invoke` had no gate at all -- the production intent path was
not the governed door. The laptop owns the gate, the ledger and the audit, so the pod asks the
laptop over ONE authenticated, intent-scoped route: `POST /intent/execute`.

These are falsifiers, not documentation: before the route they FAIL (404), after it they PASS.
They pin six things this door must be true of:

  * the door is CLOSED without a configured credential, and a wrong credential is refused --
    a door that opens itself is not a door;
  * a request that names no committed intent, an undeclared argument or a non-scalar value is a
    BAD REQUEST (400), refused before anything runs;
  * a committed intent runs through the laptop's own door, with the caller's session travelling
    UNCHANGED -- a programmatic session is not a voice session and is never namespaced as one;
  * a governed REFUSAL is reported, not swallowed: HTTP 200 with `ok: false`, the door's stderr
    and its exit code, because the refusal is a fact and it is already in the durable ledger;
  * the arguments reach the door in the door's own `k=v` form, never as `--k=v`;
  * no session at all is not a crime: the run is attributed to nobody rather than refused.
"""

import json
import sys

import pytest
from fastapi.testclient import TestClient

from fleetview_backend import serve

INTENTS = {
    "read-intent": """name: read-intent
description: Read something harmless.
args:
  who:
    type: string
    default: estate
    description: Whose report.
steps:
  - cmd: echo
""",
    "mutate-intent": """name: mutate-intent
description: Change something.
args: {}
steps:
  - cmd: echo
""",
}

TOKEN = "intent-door-token-for-tests"  # noqa: S105 -- a test credential, not a secret


@pytest.fixture()
def door(tmp_path, monkeypatch):
    """The laptop's door: a committed catalogue, a stand-in executor, and a credential."""
    intents = tmp_path / "intents"
    intents.mkdir()
    for name, body in INTENTS.items():
        (intents / (name + ".yaml")).write_text(body)
    log = tmp_path / "argv.jsonl"
    exe = tmp_path / "estate-execute"
    exe.write_text(
        "#!" + sys.executable + "\n"
        "import json, os, sys\n"
        "open(" + repr(str(log)) + ", 'a').write(json.dumps({'argv': sys.argv[1:], "
        "'session_env': os.environ.get('ESTATE_SESSION_ID', '')}) + '\\n')\n"
        "if os.environ.get('STAND_IN_REFUSES'):\n"
        "    sys.stderr.write('refused by the gate\\n'); sys.exit(3)\n"
        "print('did the thing')\n"
    )
    exe.chmod(0o755)
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(intents))
    monkeypatch.setenv("ESTATE_EXECUTE", str(exe))
    monkeypatch.setenv("FLEETVIEW_INTENT_TOKEN", TOKEN)
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    return {"log": log, "client": TestClient(serve.build_app())}


def _post(client, body, token=TOKEN):  # noqa: S107 -- a test credential
    headers = {"Authorization": "Bearer " + token} if token else {}
    return client.post("/intent/execute", json=body, headers=headers)


def test_the_door_is_closed_without_a_configured_credential(door, monkeypatch):
    """No credential configured means the door does not open -- for anybody."""
    monkeypatch.delenv("FLEETVIEW_INTENT_TOKEN", raising=False)
    response = _post(door["client"], {"intent": "read-intent"})
    assert response.status_code == 401
    assert not door["log"].exists()


def test_a_wrong_credential_is_refused(door):
    response = _post(
        door["client"],
        {"intent": "read-intent"},
        token="not-the-token",  # noqa: S106 -- a test credential
    )
    assert response.status_code == 401
    assert not door["log"].exists()


def test_a_missing_credential_is_refused(door):
    response = _post(door["client"], {"intent": "read-intent"}, token="")
    assert response.status_code == 401
    assert not door["log"].exists()


def test_an_unknown_intent_is_a_bad_request(door):
    response = _post(door["client"], {"intent": "no-such-intent"})
    assert response.status_code == 400
    assert not door["log"].exists()


def test_an_undeclared_argument_is_a_bad_request(door):
    response = _post(door["client"], {"intent": "read-intent", "args": {"nope": "x"}})
    assert response.status_code == 400
    assert not door["log"].exists()


def test_a_non_scalar_argument_is_a_bad_request(door):
    response = _post(
        door["client"], {"intent": "read-intent", "args": {"who": {"a": 1}}}
    )
    assert response.status_code == 400
    assert not door["log"].exists()


def test_a_malformed_body_is_a_bad_request(door):
    response = door["client"].post(
        "/intent/execute",
        content=b"not json at all",
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 400
    assert not door["log"].exists()


def test_a_committed_intent_runs_through_the_laptops_door(door):
    response = _post(door["client"], {"intent": "read-intent"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["exit_code"] == 0
    assert "did the thing" in body["stdout"]


def test_the_session_travels_unchanged(door):
    """A programmatic session is NOT a voice session: it is never namespaced as one."""
    response = _post(
        door["client"], {"intent": "read-intent", "session_id": "prog-session-1"}
    )
    assert response.status_code == 200
    record = json.loads(door["log"].read_text().strip())
    assert record["argv"][:1] == ["read-intent"]
    assert "--session" in record["argv"]
    assert record["argv"][record["argv"].index("--session") + 1] == "prog-session-1"
    assert record["session_env"] == "prog-session-1"
    assert "voice:" not in " ".join(record["argv"])


def test_arguments_reach_the_door_in_the_doors_own_form(door):
    response = _post(
        door["client"], {"intent": "read-intent", "args": {"who": "founder"}}
    )
    assert response.status_code == 200
    record = json.loads(door["log"].read_text().strip())
    assert "who=founder" in record["argv"]
    assert "--who=founder" not in record["argv"]


def test_a_governed_refusal_is_reported_not_swallowed(door, monkeypatch):
    monkeypatch.setenv("STAND_IN_REFUSES", "1")
    response = _post(door["client"], {"intent": "mutate-intent"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["exit_code"] == 3
    assert "refused by the gate" in body["stderr"]


def test_no_session_is_not_a_crime(door):
    """Identity-less automation is recorded as unattributed, not refused: a gate that refuses
    anonymous work is an outage."""
    response = _post(door["client"], {"intent": "read-intent"})
    assert response.status_code == 200
    record = json.loads(door["log"].read_text().strip())
    assert "--session" not in record["argv"]
    assert record["session_env"] == ""
