"""Every runtime that can reach the door presents a session identity, and the door audits it.

idp#7518, acceptance I2, I4 and I5.

The defect was never "the plan model is wrong". It was that the door could not TELL who was
asking: pi's request carried no session id, the MCP bridge generated one per process, the
Claude hook kept its plan in a transcript, and the intent executor asked no question at all.
So the door could either refuse everything (an outage) or allow everything (the bug).

These tests are the falsifiers for the four seams that fix it:

  * the classifier: `git -C <path> status` is a read, `git diff --output=f` is a write,
  * the intent executor: the OTHER door refuses before `subprocess.run`,
  * the identity: environment first, then a pointer file, then a generated id -- and a later
    owning-runtime pointer WINS over a generated one,
  * the audit: every refusal is a countable line in the estate's own file and a structured
    line on the door's stderr.

Everything runs offline: no daemon, no network, no mutation outside a temporary directory.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO / "platform" / "estate" / "memory"
PLAN_PY = CONTRACT_DIR / "plan.py"
INTENT_EXECUTOR = REPO / "platform" / "estate" / "bin" / "estate-execute"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(
        name, str(path), loader=importlib.machinery.SourceFileLoader(name, str(path))
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = _load("estate_plan_contract_under_test", PLAN_PY)
door = _load(
    "estate_executor_door_under_test", REPO / "mcp" / "plugins" / "estate_executor.py"
)


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    """The plan contract with its ledger pointed at a temporary directory."""
    monkeypatch.setattr(contract, "PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    return contract


# ---------------------------------------------------------------- the classifier


def test_git_global_options_do_not_hide_the_subcommand(ledger):
    """`git -C <path> status` is a read. The door used to refuse it (idp#7518).

    The classifier took toks[1] as the subcommand, so `git -C <path> status` looked like a
    subcommand of `-C` -- unknown, therefore work, therefore REFUSED. A gate that refuses a
    read is an outage, not a gate.
    """
    for command in (
        "git -C /Users/roseonyema/Documents/code/idp status --short --branch",
        "git -C /tmp status",
        "git -c user.name=pi status",
        "git --git-dir=/tmp/.git status",
        "git --no-pager log -1",
    ):
        assert ledger.is_read_only_command(command) is True, command


def test_the_mutating_git_forms_are_work(ledger):
    """The classifier must not be a blanket 'git is a read' (R1: a gate that cannot fail)."""
    for command in (
        "git push origin lane/x",
        "git commit -m 'x'",
        "git config user.name pi",
        "git config --unset core.x",
        "git remote add upstream git@github.com:chidionyema/idp.git",
        "git remote set-url origin git@github.com:chidionyema/idp.git",
        "git branch -d lane/old",
        "git branch -m a b",
        "git branch --set-upstream-to=main lane/x",
        "git diff --output=/tmp/leak.patch",
        "git diff --output=/tmp/leak.patch HEAD",
        "git checkout main",
        "git merge lane/x",
        "git reset --hard HEAD~1",
        "git tag v1",
        "git worktree add /tmp/wt lane/x",
    ):
        assert ledger.is_read_only_command(command) is False, command


def test_the_reading_git_forms_are_reads(ledger):
    for command in (
        "git status",
        "git log --oneline -5",
        "git diff",
        "git diff --stat",
        "git show HEAD",
        "git branch",
        "git branch -a",
        "git remote",
        "git remote -v",
        "git remote show origin",
        "git remote get-url origin",
        "git config --get user.name",
        "git config --list",
    ):
        assert ledger.is_read_only_command(command) is True, command


# -------------------------------------------------------------- the refusal audit


def test_a_refusal_is_a_countable_line_in_the_estates_own_file(ledger):
    assert (
        ledger.record_refusal("rm -rf /tmp/x", "sess-a", reason="plan_not_declared")
        is True
    )
    path = Path(ledger.PLAN_LEDGER_DIR) / ledger.PLAN_REFUSAL_FILE
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert lines[-1]["refused"] is True
    assert lines[-1]["fatal"] is True
    assert lines[-1]["reason"] == "plan_not_declared"
    assert lines[-1]["session"] == "sess-a"
    assert lines[-1]["command"] == "rm -rf /tmp/x"


def test_the_refusal_line_is_structured_json_for_the_daemon_log(ledger):
    line = ledger.refusal_log_line("rm -rf /tmp/x", "sess-a", "plan_not_declared")
    event = json.loads(line)
    assert event["event"] == "plan_gate_refusal"
    assert event["refused"] is True
    assert event["fatal"] is True
    assert event["reason"] == "plan_not_declared"
    assert event["session"] == "sess-a"


def test_the_door_writes_the_refusal_to_the_file_and_to_stderr(
    ledger, monkeypatch, capsys
):
    """The refusal must be visible in the production log, not only in the socket reply."""
    ledger.append_plan_event("sess-a", "session_start", {})
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-a")
    before = capsys.readouterr().err
    assert before == ""
    result = door.execute_command("rm -rf /tmp/plan-gate-marker")
    assert result["accepted"] is False
    assert result["reason"] == "plan_not_declared"
    path = Path(ledger.PLAN_LEDGER_DIR) / ledger.PLAN_REFUSAL_FILE
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert lines[-1]["reason"] == "plan_not_declared"
    assert lines[-1]["source"] == "door"
    # And the daemon's own stderr carries it, so the production log proves the refusal.
    stderr = capsys.readouterr().err
    event = json.loads(stderr.strip().splitlines()[-1])
    assert event["event"] == "plan_gate_refusal"
    assert event["reason"] == "plan_not_declared"
    assert event["session"] == "sess-a"
    assert event["refused"] is True


# ------------------------------------------------------- the intent executor door


def _intent_executor(tmp_path, monkeypatch):
    """The staged intent executor, loaded as a module with its plan contract pointed away."""
    module = _load(
        "estate_intent_executor_under_test",
        INTENT_EXECUTOR,
    )
    monkeypatch.setattr(module, "_PLAN_CONTRACT", contract)
    monkeypatch.setattr(module, "_PLAN_CONTRACT_TRIED", True)
    return module


def test_the_intent_executor_refuses_before_the_command_runs(
    ledger, monkeypatch, tmp_path
):
    """The OTHER door refuses too (idp#7518): a gate that covers one door is walked around."""
    executor = _intent_executor(tmp_path, monkeypatch)
    ledger.append_plan_event("sess-a", "session_start", {})
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-a")
    ran = []
    monkeypatch.setattr(
        executor.subprocess,
        "run",
        lambda *a, **k: ran.append(a) or _fake_result(),
    )
    ok, reason, _detail = executor._plan_gate("rm -rf /tmp/x", "sess-a")
    assert ok is False
    assert reason == "plan_not_declared"
    assert ran == []  # the gate answered the question; nothing was run


def test_the_intent_executor_never_reaches_subprocess_run_when_refused(
    ledger, monkeypatch, tmp_path
):
    """The proof that the refusal is a gate and not a warning: the command never runs."""
    executor = _intent_executor(tmp_path, monkeypatch)
    ledger.append_plan_event("sess-a", "session_start", {})
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-a")
    ran = []
    monkeypatch.setattr(
        executor.subprocess,
        "run",
        lambda *a, **k: ran.append(a) or _fake_result(),
    )
    monkeypatch.setattr(executor, "log_step", lambda *a, **k: None)
    monkeypatch.setattr(executor, "close_ticket", lambda *a, **k: None)
    intent = {"steps": [{"name": "kill", "cmd": "rm -rf /tmp/plan-gate-marker"}]}
    status = executor.run_steps(None, "T-1", intent, {})
    assert status == "halted"  # the default on_fail is halt
    assert ran == []
    path = Path(ledger.PLAN_LEDGER_DIR) / ledger.PLAN_REFUSAL_FILE
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert lines[-1]["source"] == "intent-door"
    assert lines[-1]["reason"] == "plan_not_declared"


def test_the_intent_executor_records_only_unenforced_work(
    ledger, monkeypatch, tmp_path
):
    executor = _intent_executor(tmp_path, monkeypatch)
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-a")
    # A session with NO ledger: its adapter is not live, so the work is allowed and recorded.
    executor._record_unplanned("curl https://example.invalid", "sess-noledger")
    observe = Path(ledger.PLAN_LEDGER_DIR) / ledger.PLAN_OBSERVE_FILE
    lines = [json.loads(x) for x in observe.read_text().splitlines() if x.strip()]
    assert lines[-1]["session"] == "sess-noledger"
    assert lines[-1]["source"] == "intent-door"
    assert "example.invalid" in lines[-1]["command"]


def test_the_intent_executor_records_a_refusal_in_the_estates_own_file(
    ledger, monkeypatch, tmp_path
):
    executor = _intent_executor(tmp_path, monkeypatch)
    executor._plan_refusal(
        "rm -rf /tmp/x", "sess-a", "plan_not_declared", "declare first"
    )
    path = Path(ledger.PLAN_LEDGER_DIR) / ledger.PLAN_REFUSAL_FILE
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert lines[-1]["source"] == "intent-door"
    assert lines[-1]["reason"] == "plan_not_declared"


def test_the_intent_executor_resolves_the_session_from_the_environment(
    ledger, monkeypatch, tmp_path
):
    executor = _intent_executor(tmp_path, monkeypatch)
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-env")
    assert executor._session_identity() == "sess-env"


def _fake_result():
    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    return R()


# ------------------------------------------------------- the canonical publication


def test_publication_writes_the_pointer_the_marker_and_the_calls(ledger):
    out = ledger.publish_session(
        "sess-pub", pid=4242, calls=[["declare_plan", {"goal": "g"}]]
    )
    assert out["ok"] is True
    assert out["pointer"] is True
    assert out["marker"] is True
    assert out["appended"] == 1
    pointer = Path(ledger.session_pointer_path(4242))
    assert json.loads(pointer.read_text())["session_id"] == "sess-pub"
    assert ledger.ledger_exists("sess-pub") is True
    assert ledger.ledger_calls("sess-pub") == [["declare_plan", {"goal": "g"}]]


def test_a_pointer_that_already_names_a_session_is_left_alone(ledger):
    ledger.write_session_pointer("sess-first", pid=4242)
    assert (
        ledger.write_session_pointer("sess-second", pid=4242, overwrite=False) is False
    )
    assert json.loads(Path(ledger.session_pointer_path(4242)).read_text())[
        "session_id"
    ] == ("sess-first")
    # With overwrite the owner may refresh its own pointer.
    assert ledger.write_session_pointer("sess-second", pid=4242, overwrite=True) is True
    assert json.loads(Path(ledger.session_pointer_path(4242)).read_text())[
        "session_id"
    ] == ("sess-second")


def test_publication_appends_only_the_missing_tail(ledger):
    ledger.append_plan_event("sess-pub", "declare_plan", {"goal": "g"})
    appended = ledger.sync_plan_calls(
        "sess-pub",
        [["declare_plan", {"goal": "g"}], ["add_bdd", {"goal_id": "goal_1"}]],
    )
    assert appended == 1
    assert [c[0] for c in ledger.ledger_calls("sess-pub")] == [
        "declare_plan",
        "add_bdd",
    ]


def test_publication_never_erases_a_concurrent_declaration(ledger):
    """A declaration made elsewhere at the same moment survives (idp#7443's durability)."""
    ledger.append_plan_event("sess-pub", "add_bdd", {"goal_id": "goal_9"})
    ledger.publish_session(
        "sess-pub",
        calls=[["declare_plan", {"goal": "g"}]],
    )
    assert [c[0] for c in ledger.ledger_calls("sess-pub")] == [
        "add_bdd",
        "declare_plan",
    ]


def test_the_publish_cli_publishes_pointer_marker_and_calls(ledger, tmp_path):
    out = subprocess.run(
        [
            sys.executable,
            str(PLAN_PY),
            "publish",
            "--session",
            "sess-cli",
            "--pid",
            "4343",
            "--calls",
            json.dumps([["declare_plan", {"goal": "g"}]]),
        ],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ESTATE_PLAN_LEDGER_DIR": str(tmp_path / "plans"),
        },
        check=True,
    )
    summary = json.loads(out.stdout)
    assert summary["ok"] is True
    assert summary["session"] == "sess-cli"
    assert summary["appended"] == 1
    pointer = Path(tmp_path / "plans" / "session-4343.json")
    assert json.loads(pointer.read_text())["session_id"] == "sess-cli"


def test_the_publish_cli_reads_the_calls_from_stdin(ledger, tmp_path):
    out = subprocess.run(
        [sys.executable, str(PLAN_PY), "publish", "--session", "sess-stdin"],
        input=json.dumps([["declare_plan", {"goal": "g"}]]),
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ESTATE_PLAN_LEDGER_DIR": str(tmp_path / "plans"),
        },
        check=True,
    )
    summary = json.loads(out.stdout)
    assert summary["appended"] == 1


# ------------------------------------------------------------ the session identity


def test_the_environment_wins_over_a_pointer(ledger, monkeypatch):
    ledger.write_session_pointer("sess-pointer", pid=os.getpid())
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-env")
    assert ledger.resolve_session_id() == "sess-env"


def test_a_pointer_is_used_when_the_environment_is_silent(ledger, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    ledger.write_session_pointer("sess-pointer", pid=os.getpid())
    assert ledger.resolve_session_id() == "sess-pointer"


def test_no_identity_means_automation_not_a_refusal(ledger, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    monkeypatch.setattr(ledger, "_ancestor_pids", lambda *a, **k: [])
    assert ledger.resolve_session_id() == ""
    gate = ledger.door_plan_gate("rm -rf /tmp/x", "")
    assert gate["ok"] is True
    assert gate["reason"] == "no_session_presented"


# ------------------------------------------------------- the MCP bridge's identity


def _bridge(monkeypatch):
    """The MCP bridge, loaded with the plan contract pointed at a temporary directory."""
    bridge = _load("estate_memory_mcp_under_test", REPO / "bin" / "estate-memory-mcp")
    # The bridge's module-level `plan` IS the contract; its instance attribute `plan` is the
    # plan state. Point the module at the patched contract so the ledger is temporary.
    bridge.plan = contract
    return bridge


def test_the_bridge_takes_the_environment_session_first(ledger, monkeypatch):
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-env")
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    assert instance._resolve_session() == "sess-env"


def test_the_bridge_generates_an_identity_when_there_is_none(ledger, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    monkeypatch.setattr(
        ledger, "session_pointer_path", lambda pid: "/nonexistent/pointer.json"
    )
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    sid = instance._resolve_session()
    assert sid.startswith("mcp-")
    assert sid


def test_the_bridge_publishes_its_own_pointer_and_the_owners(ledger, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    monkeypatch.setattr(
        ledger, "session_pointer_path", lambda pid: "/nonexistent/pointer.json"
    )
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    instance.session_id = "sess-bridge"
    instance.calls = []
    instance._publish()
    assert ledger.ledger_exists("sess-bridge") is True
    assert ledger.ledger_calls("sess-bridge") == []


def test_the_bridge_adopts_a_later_owning_runtime_pointer(ledger, monkeypatch):
    """A pointer that appears AFTER the bridge started owns the session (idp#7518).

    Claude Code's hook writes its real session id when the first tool call happens, which is
    after the bridge started. If the bridge kept its generated id, the door would read a
    ledger nobody declares into -- the session would look unplanned forever. The later
    pointer WINS, and the calls the bridge already served are migrated with it.
    """
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    instance.session_id = "mcp-generated"
    instance.calls = [["declare_plan", {"goal": "g"}]]
    monkeypatch.setattr(instance, "_parent_session", lambda: "sess-owner")
    instance._adopt_parent_session()
    assert instance.session_id == "sess-owner"
    assert ledger.ledger_calls("sess-owner") == [["declare_plan", {"goal": "g"}]]


def test_the_bridge_keeps_its_own_pointer_when_the_owner_already_wrote_one(
    ledger, monkeypatch
):
    """Two ledgers behind one pointer is how a session ends up looking unplanned."""
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    instance.session_id = "sess-bridge"
    instance.calls = []
    parent = os.getppid()
    ledger.write_session_pointer("sess-owner", pid=parent)
    monkeypatch.setattr(instance, "_parent_session", lambda: "sess-owner")
    instance._publish()
    assert json.loads(Path(ledger.session_pointer_path(parent)).read_text())[
        "session_id"
    ] == ("sess-owner")


def test_the_bridge_appends_the_plan_call_in_order(ledger, monkeypatch):
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = None
    instance.session_id = "sess-bridge"
    instance.calls = []
    monkeypatch.setattr(instance, "_parent_session", lambda: "")
    instance.plan_call(
        1,
        "declare_plan",
        {
            "goal": "prove every runtime presents a session identity to the door",
            "subgoals": [{"id": "goal_1", "text": "the identity reaches the door"}],
        },
    )
    instance.plan_call(
        2,
        "add_bdd",
        {
            "goal_id": "goal_1",
            "given": "a runtime with a plan",
            "when": "it reaches the door",
            "then": "the door sees the plan",
        },
    )
    assert [c[0] for c in ledger.ledger_calls("sess-bridge")] == [
        "declare_plan",
        "add_bdd",
    ]


# ----------------------------------------------------- the MCP bridge's forwarding


def test_the_mcp_bridge_forwards_a_memory_call_without_inventing_arguments(
    ledger, monkeypatch
):
    """The gateway's tool schemas are the estate's; the bridge must not extend them.

    Injecting a session id into the forwarded ARGUMENTS would break every client whose
    schema is closed (idp#7518). The identity travels in the bridge's own ledger and pointer,
    not in the payload the gateway validates.
    """
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = contract
    instance.session_id = "sess-bridge"
    instance.calls = []
    instance.secret = "k"  # noqa: S105 - a stub gateway token, not a credential
    captured = {}

    def fake_post(msg, secret, timeout):
        captured["msg"] = msg
        return {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "result": {"content": [{"type": "text", "text": "{}"}]},
        }, 200

    monkeypatch.setattr(bridge.door, "post", fake_post)
    reply = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "recall", "arguments": {"query": "plan gate"}},
        }
    )
    assert reply["id"] == 7
    forwarded = captured["msg"]
    assert forwarded["params"]["arguments"] == {"query": "plan gate"}
    # Nothing was added to the arguments the gateway validates.
    assert set(forwarded["params"]["arguments"]) == {"query"}
    # The identity still exists, in the bridge's own ledger.
    assert instance.session_id == "sess-bridge"


def test_the_mcp_bridge_never_forwards_a_plan_tool_to_the_gateway(ledger, monkeypatch):
    """Plan tools are the bridge's own; the gateway has no such tool to call."""
    bridge = _bridge(monkeypatch)
    instance = bridge.Bridge.__new__(bridge.Bridge)
    instance.plan = None
    instance.session_id = "sess-bridge"
    instance.calls = []
    instance.secret = "k"  # noqa: S105 - a stub gateway token, not a credential
    called = {"n": 0}

    def fake_post(msg, secret, timeout):
        called["n"] += 1
        return {"jsonrpc": "2.0", "id": msg.get("id"), "result": {}}, 200

    monkeypatch.setattr(bridge.door, "post", fake_post)
    reply = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "declare_plan",
                "arguments": {
                    "goal": "prove the plan tools are served by the bridge itself",
                    "subgoals": [{"id": "goal_1", "text": "the bridge answers"}],
                },
            },
        }
    )
    assert called["n"] == 0
    assert reply["result"]["content"][0]["type"] == "text"


# --------------------------------------------------------------- the Claude hook


def _hook(monkeypatch):
    hook = _load(
        "estate_memory_enforce_under_test", REPO / "bin" / "estate-memory-enforce"
    )
    hook.plan = contract
    return hook


def test_the_claude_hook_publishes_the_pointer_for_its_owning_process(
    ledger, monkeypatch
):
    hook = _hook(monkeypatch)
    hook.publish_session(
        {"session_id": "sess-claude"}, [["declare_plan", {"goal": "g"}]]
    )
    # The pointer names the OWNER (the Claude process), not the short-lived hook.
    owner = os.getppid()
    assert json.loads(Path(ledger.session_pointer_path(owner)).read_text())[
        "session_id"
    ] == ("sess-claude")
    assert [c[0] for c in ledger.ledger_calls("sess-claude")] == ["declare_plan"]


def test_the_claude_hook_publication_never_raises(ledger, monkeypatch):
    hook = _hook(monkeypatch)
    monkeypatch.setattr(
        hook.plan,
        "publish_session",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    hook.publish_session({"session_id": "sess-claude"}, [])  # must not raise


def test_the_claude_hook_without_a_session_publishes_nothing(ledger, monkeypatch):
    hook = _hook(monkeypatch)
    hook.publish_session({}, [])
    assert ledger.ledger_calls("") == []


def _transcript(tmp_path, calls):
    """A Claude Code transcript with the given plan-tool calls, in order."""
    path = tmp_path / "transcript.jsonl"
    lines = []
    for name, args in calls:
        lines.append(
            json.dumps(
                {
                    "message": {
                        "content": [{"type": "tool_use", "name": name, "input": args}]
                    }
                }
            )
        )
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_the_claude_hook_publishes_the_call_being_authorised(
    ledger, monkeypatch, tmp_path
):
    """The current tool call is not in the transcript yet: it is the call being authorised."""
    hook = _hook(monkeypatch)
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path / "memory-home"))
    transcript = _transcript(
        tmp_path,
        [
            (
                "declare_plan",
                {
                    "goal": "prove every runtime presents a session identity to the door",
                    "subgoals": [
                        {"id": "goal_1", "text": "the identity reaches the door"}
                    ],
                },
            )
        ],
    )
    hook.plan_gate(
        {
            "session_id": "sess-claude",
            "tool_name": "add_bdd",
            "tool_input": {
                "goal_id": "goal_1",
                "given": "a runtime with a plan",
                "when": "it reaches the door",
                "then": "the door sees the plan",
            },
            "transcript_path": transcript,
        }
    )
    assert [c[0] for c in ledger.ledger_calls("sess-claude")] == [
        "declare_plan",
        "add_bdd",
    ]


def test_the_claude_hook_appends_only_the_missing_tail(ledger, monkeypatch, tmp_path):
    """A second hook run must not duplicate what the first already wrote."""
    hook = _hook(monkeypatch)
    monkeypatch.setenv("ESTATE_MEMORY_HOME", str(tmp_path / "memory-home"))
    transcript = _transcript(
        tmp_path,
        [
            (
                "declare_plan",
                {
                    "goal": "prove every runtime presents a session identity to the door",
                    "subgoals": [
                        {"id": "goal_1", "text": "the identity reaches the door"}
                    ],
                },
            )
        ],
    )
    data = {
        "session_id": "sess-claude",
        "tool_name": "add_bdd",
        "tool_input": {
            "goal_id": "goal_1",
            "given": "a runtime with a plan",
            "when": "it reaches the door",
            "then": "the door sees the plan",
        },
        "transcript_path": transcript,
    }
    hook.plan_gate(data)
    hook.plan_gate(data)
    assert [c[0] for c in ledger.ledger_calls("sess-claude")] == [
        "declare_plan",
        "add_bdd",
    ]


# -------------------------------------------------------------- the opencode plugin


def test_the_opencode_plugin_delegates_to_the_canonical_publisher(ledger, tmp_path):
    """The plugin owns no plan model: it asks plan.py, which owns what a pointer means."""
    plugin = (CONTRACT_DIR / "opencode-estate-memory.js").read_text()
    assert "publish" in plugin
    assert "publishSession" in plugin
    assert "--session" in plugin
    # It must NOT write the ledger itself: one definition of the ledger, not two.
    assert "appendFileSync" not in plugin
    assert "writeFileSync" not in plugin


def test_the_opencode_publish_candidate_order_prefers_the_installed_copy():
    plugin = (CONTRACT_DIR / "opencode-estate-memory.js").read_text()
    assert "HOME_PLAN" in plugin
    assert "PLAN_CANDIDATES" in plugin


def test_the_opencode_plugin_is_valid_javascript():
    out = subprocess.run(
        ["node", "--check", str(CONTRACT_DIR / "opencode-estate-memory.js")],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr


def _opencode(tmp_path, home=None):
    """Run the opencode plugin's publication path for real, in node, against a temp ledger."""
    plugin = tmp_path / "opencode-estate-memory.mjs"
    plugin.write_text((CONTRACT_DIR / "opencode-estate-memory.js").read_text())
    driver = tmp_path / "driver.mjs"
    driver.write_text(
        "import { publishSession } from %s;\n"
        "const ok = await publishSession(process.argv[2]);\n"
        "process.stdout.write(JSON.stringify({ ok }));\n" % json.dumps(plugin.as_uri())
    )
    env = dict(os.environ)
    env["IDP"] = str(REPO)
    env["ESTATE_PLAN_LEDGER_DIR"] = str(tmp_path / "plans")
    if home is not None:
        env["ESTATE_MEMORY_HOME"] = str(home)
    else:
        env.pop("ESTATE_MEMORY_HOME", None)
    out = subprocess.run(
        ["node", str(driver), "sess-opencode"], capture_output=True, text=True, env=env
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout), tmp_path / "plans"


def test_the_opencode_plugin_actually_publishes_a_marker_and_a_pointer(
    ledger, tmp_path
):
    """The plugin's publication is measured, not asserted (idp#7518)."""
    result, plans = _opencode(tmp_path)
    assert result["ok"] is True
    assert (plans / "sess-opencode.jsonl").exists()
    events = [
        json.loads(x)
        for x in (plans / "sess-opencode.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert events[0]["tool"] == "session_start"
    pointers = list(plans.glob("session-*.json"))
    assert pointers, "the plugin published no pointer"


def test_the_opencode_publication_is_idempotent(ledger, tmp_path):
    """Publishing twice must not open a second ledger or duplicate the marker."""
    result, plans = _opencode(tmp_path)
    assert result["ok"] is True
    plugin = tmp_path / "opencode-estate-memory.mjs"
    driver = tmp_path / "driver.mjs"
    driver.write_text(
        "import { publishSession } from %s;\n"
        "await publishSession(process.argv[2]);\n"
        "const ok = await publishSession(process.argv[2]);\n"
        "process.stdout.write(JSON.stringify({ ok }));\n" % json.dumps(plugin.as_uri())
    )
    env = dict(os.environ)
    env["IDP"] = str(REPO)
    env["ESTATE_PLAN_LEDGER_DIR"] = str(tmp_path / "plans")
    env.pop("ESTATE_MEMORY_HOME", None)
    out = subprocess.run(
        ["node", str(driver), "sess-opencode"], capture_output=True, text=True, env=env
    )
    assert out.returncode == 0, out.stderr
    events = [
        json.loads(x)
        for x in (plans / "sess-opencode.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert [e["tool"] for e in events].count("session_start") == 1


def test_the_opencode_plugin_prefers_the_installed_copy_of_the_contract(
    ledger, tmp_path
):
    """The installed copy wins, and the fallback reaches the checkout when it is missing."""
    home = tmp_path / "memory-home"
    installed = home / "platform" / "estate" / "memory"
    installed.mkdir(parents=True)
    marker = tmp_path / "installed-was-used"
    (installed / "plan.py").write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "open(%r, 'a').write('used\\n')\n"
        "sys.exit(0)\n" % str(marker)
    )
    result, _plans = _opencode(tmp_path, home=home)
    assert result["ok"] is True
    assert marker.exists(), "the installed copy of plan.py was not the one used"


def test_the_opencode_publication_failure_is_contained(ledger, tmp_path):
    """A broken contract must never take an opencode session down."""
    plugin = tmp_path / "opencode-estate-memory.mjs"
    plugin.write_text((CONTRACT_DIR / "opencode-estate-memory.js").read_text())
    driver = tmp_path / "driver.mjs"
    driver.write_text(
        "import { publishSession } from %s;\n"
        "const ok = await publishSession(process.argv[2]);\n"
        "process.stdout.write(JSON.stringify({ ok }));\n" % json.dumps(plugin.as_uri())
    )
    env = dict(os.environ)
    env["IDP"] = str(tmp_path / "nowhere")  # no plan.py in the checkout either
    env["ESTATE_PLAN_LEDGER_DIR"] = str(tmp_path / "plans")
    env["ESTATE_MEMORY_HOME"] = str(tmp_path / "no-memory-home")
    out = subprocess.run(
        ["node", str(driver), "sess-opencode"], capture_output=True, text=True, env=env
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["ok"] is False


# --------------------------------------------------------- the pi request identity


def test_the_pi_capability_adapter_sends_the_session_id_with_every_request():
    """The daemon is long-lived: the identity must travel WITH the request."""
    source = (REPO / "extensions" / "estate-capabilities" / "index.ts").read_text()
    assert "session_id" in source
    assert "ESTATE_SESSION_ID" in source
    assert "payload.session_id = sid" in source


_PI_STUBS = {
    "typebox": {
        "package.json": '{"name":"typebox","version":"0.0.0","type":"module",'
        '"exports":"./index.js"}',
        "index.js": (
            "const mk = (t) => (o) => ({ type: t, ...(o || {}) });\n"
            "export const Type = { Object: mk('object'), String: mk('string'), "
            "Number: mk('number'), Integer: mk('integer'), Boolean: mk('boolean'), "
            "Array: mk('array'), Optional: (s) => s };\n"
        ),
    },
    "@earendil-works/pi-coding-agent": {
        "package.json": '{"name":"@earendil-works/pi-coding-agent","version":"0.0.0",'
        '"type":"module","exports":"./index.js"}',
        "index.js": "export default {};\n",
    },
}


def _pi_driver(tmp_path, plans):
    """A node harness that loads the pi extension and talks to a fake executor socket.

    The identity is only worth anything if it survives the transport, so this drives the REAL
    extension: a real socket, a real payload, and the session id the extension resolved.
    """
    for name, files in _PI_STUBS.items():
        pkg = tmp_path / "node_modules" / name
        pkg.mkdir(parents=True, exist_ok=True)
        for filename, body in files.items():
            (pkg / filename).write_text(body)
    (tmp_path / "package.json").write_text('{"name":"pi-probe","type":"module"}')
    (tmp_path / "ext.ts").write_text(
        (REPO / "extensions" / "estate-capabilities" / "index.ts").read_text()
    )
    # A UNIX socket path is limited to about 100 bytes, and pytest's tmp_path is far longer
    # than that, so the socket lives in a short directory of its own.
    sock_dir = tempfile.mkdtemp(dir="/tmp", prefix="pisock")
    socket = os.path.join(sock_dir, "s.sock")
    driver = tmp_path / "driver.mjs"
    driver.write_text(
        """
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
const socket = process.argv[2];
const pointerSession = process.argv[3] || "";
if (pointerSession) {
  const dir = process.env.ESTATE_PLAN_LEDGER_DIR;
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, `session-${process.pid}.json`),
    JSON.stringify({ session_id: pointerSession, ts: "now" }),
  );
}
const captured = [];
const server = net.createServer((conn) => {
  conn.once("data", (chunk) => {
    captured.push(JSON.parse(chunk.toString().trim()));
    conn.write(JSON.stringify({ pid: 4242, ceiling_sec: 100 }) + "\\n");
    conn.end();
  });
});
await new Promise((r) => server.listen(socket, r));
const mod = await import("./ext.ts");
const tools = new Map();
const pi = {
  on() {},
  registerTool(t) { tools.set(t.name, t); },
  getActiveTools() { return []; },
  setActiveTools() {},
  getAllTools() { return [...tools.values()]; },
};
mod.default(pi);
const tool = tools.get("estate_executor_status");
await tool.execute("t1", {});
await new Promise((r) => setTimeout(r, 100));
server.close();
process.stdout.write(JSON.stringify(captured));
"""
    )
    return socket, driver


def _pi_payload(tmp_path, plans, env_session=None, pointer=None):
    socket, driver = _pi_driver(tmp_path, plans)
    env = dict(os.environ)
    env["IDP_EXECUTOR_SOCKET"] = str(socket)
    env["ESTATE_PLAN_LEDGER_DIR"] = str(tmp_path / "plans")
    env.pop("ESTATE_SESSION_ID", None)
    if env_session:
        env["ESTATE_SESSION_ID"] = env_session
    out = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            str(driver),
            str(socket),
            pointer or "",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_the_pi_extension_sends_the_environment_session_over_the_socket(tmp_path):
    """The request that leaves the extension carries the session id (idp#7518)."""
    captured = _pi_payload(tmp_path, tmp_path / "plans", env_session="sess-pi-env")
    assert captured, "the extension never reached the door"
    assert captured[0]["session_id"] == "sess-pi-env"
    assert captured[0]["verb"] == "health"


def test_the_pi_extension_falls_back_to_the_pointer_file(tmp_path):
    """No environment: the pointer the plan-lock extension wrote is the identity."""
    captured = _pi_payload(tmp_path, tmp_path / "plans", pointer="sess-pi-pointer")
    assert captured
    assert captured[0]["session_id"] == "sess-pi-pointer"


# ------------------------------------------------------------- the runtimes manifest


def test_the_manifest_never_claims_a_lock_it_does_not_have():
    manifest = json.loads((CONTRACT_DIR / "runtimes.json").read_text())
    runtimes = manifest["runtimes"]
    # Gemini and Cursor have no native plan lock, and that must stay visible.
    assert runtimes["gemini"]["plan_lock"] is None
    assert runtimes["cursor"]["plan_lock"] is None
    # Codex is tracked, with no lock and no MCP entry the JSON installer would write.
    assert "codex" in runtimes
    assert runtimes["codex"]["plan_lock"] is None
    assert "mcp" not in runtimes["codex"]
    # Every runtime names the owner of its lock, so the installer reports the truth.
    for name, rt in runtimes.items():
        assert rt.get("owner"), name


def test_the_installed_command_of_an_unlocked_runtime_is_reported_with_its_owner():
    installer = (REPO / "bin" / "estate-memory-install").read_text()
    assert 'rt.get("owner")' in installer
    assert "estate_door" in installer
