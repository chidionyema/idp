"""An intent's arguments are a schema, and only declared ones are ever passed.

EPIC-IDP-090 slice S1. Before this, `execute()` called `[exe, intent]` and nothing else: an intent
that declared `args` had those declarations read by nobody and passed by nothing, and the catalogue
the Face's deck reads carried a name, a description and a boolean. The tests below pin the four
things that fix has to be true of, each against a real subprocess (a stand-in estate-execute that
records the argv it was handed) rather than a mocked one:

  * the declaration is reachable -- `inputSchema` is the MCP shape, with `required` for the
    arguments that have no default;
  * a supplied value is one argv word, `--k=v`, and only for an argument the intent declares;
  * an undeclared argument or a non-scalar value is refused before anything runs;
  * the audit records the argument NAMES and never the values, because a value can be a token.
"""

import json
import sys

import pytest

from fleetview_backend import voice_intents as vi

# In the spoken catalog: every argument has a default, so naming it is enough.
CI_STATUS_YAML = """name: ci-status
class: read
description: CI status for a branch.
args:
  repo:
    type: string
    default: idp
    description: Which repository.
steps:
  - cmd: echo
"""

# Out of the spoken catalog: `pr` has no default, so an utterance alone cannot reach it. A caller
# that brings the value can.
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


@pytest.fixture()
def estate(tmp_path, monkeypatch):
    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "ci-status.yaml").write_text(CI_STATUS_YAML)
    (intents / "pr-status.yaml").write_text(PR_STATUS_YAML)
    log = tmp_path / "argv.jsonl"
    exe = tmp_path / "estate-execute"
    exe.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"open({str(log)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
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


def test_the_catalogue_carries_the_arguments_the_intent_declares(estate):
    deck = {entry["name"]: entry for entry in vi.catalogue()}
    assert deck["ci-status"]["inputSchema"] == {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Which repository.",
                "default": "idp",
            }
        },
        "required": [],
    }
    assert deck["ci-status"]["args"]["repo"]["default"] == "idp"


def test_an_argument_without_a_default_is_required_and_not_in_the_spoken_catalog(
    estate,
):
    assert "pr-status" not in vi.load_catalog()
    schema = vi.input_schema("pr-status")
    assert schema["required"] == ["pr"]
    assert schema["properties"]["pr"] == {
        "type": "integer",
        "description": "The pull request number.",
    }


def test_a_declared_value_reaches_the_executor_as_one_argv_word(estate):
    status, text, rc, _dur = vi.execute("ci-status", {"repo": "idp"})
    assert (status, rc) == ("ok", 0), text
    assert ran(estate) == [["ci-status", "--repo=idp"]]


def test_the_deck_reaches_a_required_argument_through_the_yes_it_asks_for(estate):
    asked = vi.handle("pr status", "s1", {"pr": 42})
    assert asked["status"] == "pending_confirmation"
    assert "pr 42" in asked["text"], asked["text"]
    assert ran(estate) == []

    ran_it = vi.handle("yes", "s1")
    assert ran_it["status"] == "ok"
    assert ran(estate) == [["pr-status", "--pr=42"]]


def test_an_undeclared_argument_is_refused_before_anything_runs(estate):
    refused = vi.handle("ci status", "s2", {"token": "abc"})
    assert refused["status"] == "error"
    assert refused["text"] == "ci status takes no token."
    assert ran(estate) == []


def test_a_value_that_is_not_a_scalar_is_refused_before_anything_runs(estate):
    status, text, rc, _dur = vi.execute("ci-status", {"repo": {"a": 1}})
    assert status == "error"
    assert rc == 2
    assert "single value" in text
    assert ran(estate) == []


def test_the_audit_records_the_argument_names_and_never_the_values(estate):
    vi.handle("ci status", "s3", {"repo": "secret-looking-token"})
    line = estate["audit"].read_text()
    assert json.loads(line)["arg_names"] == ["repo"]
    assert "secret-looking-token" not in line


def test_an_utterance_alone_still_runs_an_arg_free_intent(estate):
    answer = vi.handle("check ci status", "s4")
    assert answer["status"] == "ok"
    assert ran(estate) == [["ci-status"]]
