"""[#6675] every runtime, not only pi, declares a plan before it works.

platform/estate/memory/plan.py is the Python copy of extensions/pi-plan-lock/plan.ts. Both replay
extensions/pi-plan-lock/cases.json, so the two copies are held to one contract. The bridge serves
the plan tools to every MCP runtime; the hook refuses Claude Code's work tools until the plan the
transcript records allows them.
"""

import importlib.machinery
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "platform", "estate", "memory"))
import plan  # noqa: E402

CASES = json.load(open(os.path.join(ROOT, "extensions", "pi-plan-lock", "cases.json")))[
    "cases"
]
GOAL = {"goal": "ship the feature", "subgoals": [{"id": "g1", "text": "first step"}]}
BDD = {
    "goal_id": "g1",
    "given": "no button",
    "when": "the page loads",
    "then": "the button shows",
}


def _script(name):
    loader = importlib.machinery.SourceFileLoader(
        name.replace("-", "_"), os.path.join(ROOT, "bin", name)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_the_python_copy_honours_every_shared_case(case):
    v = plan.authorize(case["tool"], plan.replay(case["calls"]))
    assert v["ok"] is case["expect"]
    if "reason" in case:
        assert case["reason"] in v["reason"]


def test_apply_never_mutates_the_plan_it_is_given():
    p = plan.apply(None, "declare_plan", GOAL)["plan"]
    before = json.dumps(p, sort_keys=True)
    plan.apply(p, "add_bdd", BDD)
    assert json.dumps(p, sort_keys=True) == before


def test_a_plan_carries_its_instruction_and_its_founder_prompt():
    r = plan.apply(
        None,
        "declare_plan",
        dict(
            GOAL,
            instruction="lane-submit",
            prompt="prompt-20261030T101500Z-abc123",
        ),
    )
    assert r["ok"] is True
    assert r["plan"]["instruction"] == "lane-submit"
    assert r["plan"]["prompt"] == "prompt-20261030T101500Z-abc123"
    assert "lane-submit" in r["message"]
    # A revision keeps the links it does not restate: the work is still the same work.
    again = plan.apply(r["plan"], "revise_plan", GOAL)
    assert again["plan"]["instruction"] == "lane-submit"
    assert again["plan"]["prompt"] == "prompt-20261030T101500Z-abc123"


def test_a_link_that_is_present_and_wrong_is_refused():
    for bad in (
        {"instruction": ""},
        {"instruction": "not an intent"},
        {"prompt": ""},
        {"prompt": "no such id"},
    ):
        r = plan.apply(None, "declare_plan", dict(GOAL, **bad))
        assert r["ok"] is False, bad
        assert r["reason"], bad


def test_the_cli_fails_open_on_garbage():
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "platform/estate/memory/plan.py"),
            "authorize",
            "Edit",
        ],
        input="not json",
        capture_output=True,
        text=True,
    )
    assert json.loads(r.stdout)["ok"] is True


# --- the bridge: plan tools for every MCP runtime, with no door and no key -----------------------


def _call(b, i, name, args):
    return b.handle(
        {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }
    )


def test_the_bridge_serves_the_plan_tools_even_when_the_door_is_down(monkeypatch):
    bridge = _script("estate-memory-mcp")

    def down(*a, **k):
        raise OSError("door down")

    monkeypatch.setattr(bridge.door, "post", down)
    monkeypatch.setattr(bridge.door, "key", lambda: "")
    b = bridge.Bridge()
    listed = b.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert set(plan.PLAN_TOOLS) <= {t["name"] for t in listed["result"]["tools"]}

    refused = _call(b, 2, "complete_goal", {"goal_id": "g1"})
    assert (
        refused["result"]["isError"]
        and "declare_plan" in refused["result"]["content"][0]["text"]
    )
    ok = _call(b, 3, "declare_plan", GOAL)
    assert (
        not ok["result"].get("isError")
        and "add_bdd for g1" in ok["result"]["content"][0]["text"]
    )
    early = _call(b, 4, "complete_goal", {"goal_id": "g1"})
    assert (
        early["result"]["isError"]
        and "add_bdd" in early["result"]["content"][0]["text"]
    )


# --- the hook: Claude Code's work tools refused until the transcript's plan allows them ----------


def _transcript(tmp_path, calls):
    lines = [
        json.dumps(
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "name": n, "input": a}],
                }
            }
        )
        for n, a in calls
    ]
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return str(p)


def _hook(tmp_path, tool, calls, env=None, tool_input=None):
    e = {
        **os.environ,
        "HOME": str(tmp_path),
        "ESTATE_MEMORY_HOME": str(tmp_path / "mem"),
    }
    e.pop("ESTATE_PLAN_LOCK", None)
    e.pop("ESTATE_MEMORY_ENFORCE", None)
    e.update(env or {})
    data = {
        "tool_name": tool,
        "tool_input": tool_input or {},
        "session_id": "s",
        "cwd": ROOT,
        "transcript_path": _transcript(tmp_path, calls),
    }
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "estate-memory-enforce"), "plan"],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        env=e,
    )
    assert r.returncode == 0, r.stderr
    return (
        json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        if r.stdout.strip()
        else None
    )


def test_the_hook_refuses_work_with_no_plan_and_names_declare_plan(tmp_path):
    assert "declare_plan" in _hook(tmp_path, "Bash", [])


def test_the_hook_refuses_work_until_the_active_sub_goal_has_a_bdd(tmp_path):
    declared = [("mcp__estate-memory__declare_plan", GOAL)]
    assert "add_bdd" in _hook(tmp_path, "Edit", declared)
    assert (
        _hook(tmp_path, "Edit", declared + [("mcp__estate-memory__add_bdd", BDD)])
        is None
    )


def test_the_hook_never_blocks_the_plan_tools_or_loading_them(tmp_path):
    for tool in (
        "mcp__estate-memory__declare_plan",
        "ToolSearch",
        "mcp__estate-memory__brief",
    ):
        assert _hook(tmp_path, tool, []) is None, tool


# --- the shell door: a session whose bridge did not load can still declare its plan ---------------


def _sh(tool, args):
    return "estate-plan " + tool + " " + shlex.quote(json.dumps(args))


def test_the_shell_door_is_the_plan_tool_it_names():
    assert plan.shell_plan_call(_sh("declare_plan", GOAL)) == ["declare_plan", GOAL]
    assert plan.shell_plan_call("/x/bin/" + _sh("add_bdd", BDD)) == ["add_bdd", BDD]


@pytest.mark.parametrize(
    "command",
    [
        _sh("declare_plan", GOAL) + " && rm -rf x",
        _sh("declare_plan", GOAL) + "; ls",
        _sh("declare_plan", GOAL) + " | tee f",
        "estate-plan declare_plan $(cat plan.json)",
        "estate-plan declare_plan `cat plan.json`",
        _sh("declare_plan", GOAL) + "\nls",
        "estate-plan rm_rf '{}'",
        "estate-plan declare_plan 'not json'",
        "estate-plan declare_plan '[1]'",
        "echo estate-plan declare_plan '{}'",
    ],
)
def test_anything_but_exactly_one_estate_plan_is_ordinary_work(command):
    assert plan.shell_plan_call(command) is None
    assert not plan.authorize("Bash", None, {"command": command})["ok"]


def test_the_hook_lets_a_plan_be_declared_through_the_shell_and_then_honours_it(
    tmp_path,
):
    cmd = _sh("declare_plan", GOAL)
    assert "estate-plan" in _hook(tmp_path, "Bash", [])
    assert _hook(tmp_path, "Bash", [], tool_input={"command": cmd}) is None
    declared = [("Bash", {"command": cmd})]
    assert "add_bdd" in _hook(tmp_path, "Edit", declared)
    with_bdd = declared + [("Bash", {"command": _sh("add_bdd", BDD)})]
    assert _hook(tmp_path, "Edit", with_bdd) is None


def test_the_hook_refuses_a_shell_plan_call_that_does_not_apply_and_says_why(tmp_path):
    bad = {"goal": "ship the feature", "subgoals": []}
    assert "sub-goal" in _hook(
        tmp_path, "Bash", [], tool_input={"command": _sh("declare_plan", bad)}
    )
    early = _hook(tmp_path, "Bash", [], tool_input={"command": _sh("add_bdd", BDD)})
    assert "declare_plan" in early


def test_the_estate_plan_command_checks_a_plan_and_acknowledges():
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, os.path.join(ROOT, "bin", "estate-plan"), *a],
        capture_output=True,
        text=True,
    )
    ok = run("declare_plan", json.dumps(GOAL))
    assert ok.returncode == 0 and "Plan declared" in ok.stdout
    assert run("declare_plan", json.dumps({"goal": "x"})).returncode == 1
    assert run("nope", "{}").returncode == 2


def test_the_hook_honours_the_opt_out(tmp_path):
    assert _hook(tmp_path, "Bash", [], env={"ESTATE_PLAN_LOCK": "off"}) is None


# --- opencode: the plugin refuses through tool.execute.before ------------------------------------

OPENCODE = """
const { EstateMemory } = await import(process.argv[1]);
const h = await EstateMemory();
const run = async (sessionID, tool) => {
  try { await h["tool.execute.before"]({ sessionID, tool }, {}); return "allowed"; }
  catch (e) { return "refused " + e.message; }
};
const out = { none: await run("s", "bash"), declare: await run("s", "estate-memory_declare_plan") };
await h["tool.execute.after"]({ sessionID: "s", tool: "estate-memory_declare_plan", args: GOAL });
out.nobdd = await run("s", "edit");
await h["tool.execute.after"]({ sessionID: "s", tool: "estate-memory_add_bdd", args: BDD });
out.bdd = await run("s", "edit");
out.other = await run("t", "bash");
process.env.ESTATE_PLAN_LOCK = "off";
out.optout = await run("t", "bash");
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_opencode_refuses_work_until_the_sessions_plan_allows_it():
    script = OPENCODE.replace("GOAL", json.dumps(GOAL)).replace("BDD", json.dumps(BDD))
    plugin = os.path.join(
        ROOT, "platform", "estate", "memory", "opencode-estate-memory.js"
    )
    r = subprocess.run(
        ["node", "--input-type=module", "-e", script, plugin],
        capture_output=True,
        text=True,
        env={**os.environ, "IDP": ROOT, "ESTATE_PLAN_LOCK": ""},
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["none"].startswith("refused") and "declare_plan" in out["none"]
    assert out["declare"] == "allowed"
    assert out["nobdd"].startswith("refused") and "add_bdd" in out["nobdd"]
    assert out["bdd"] == "allowed"
    assert out["other"].startswith("refused"), (
        "one session's plan must not open another's"
    )
    assert out["optout"] == "allowed"


# --- the fleet: every runtime is named by the door, and every runtime can comply -------------


def test_the_door_names_an_agent_runtime_from_the_process_tree(monkeypatch):
    """A runtime with no adapter is identified from its OWN PROCESS, not from what it says."""
    monkeypatch.setattr(plan, "_ancestor_pids", lambda limit=6: [4242, 4243])
    monkeypatch.setattr(
        plan,
        "_process_argv",
        lambda pid: ["/usr/local/bin/node", "cli.js"] if pid == 4243 else [],
    )
    monkeypatch.setattr(plan, "harness_of_argv", lambda argv: "claude" if argv else "")
    assert plan.harness_session_id() == "harness:claude:4243"


def test_a_node_runtime_is_named_by_the_package_it_runs():
    assert (
        plan.harness_of_argv(
            ["node", "/x/node_modules/@anthropic-ai/claude-code/cli.js"]
        )
        == "claude"
    )
    assert (
        plan.harness_of_argv(["node", "/x/node_modules/@openai/codex/bin/x.js"])
        == "codex"
    )
    assert plan.harness_of_argv(["/usr/local/bin/claude", "--print"]) == "claude"
    assert plan.harness_of_argv(["/usr/bin/python3", "worker.py"]) == ""
    assert plan.harness_of_argv([]) == ""


def test_an_agent_session_with_no_plan_is_refused_and_is_told_the_one_command(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(plan, "PLAN_LEDGER_DIR", str(tmp_path))
    gate = plan.door_plan_gate("rm -rf ./build", "harness:claude:4242")
    assert gate["ok"] is False
    assert gate["reason"] == "plan_not_declared"
    assert "estate-plan" in gate["detail"] and "declare_plan" in gate["detail"]


def test_automation_with_no_session_is_still_allowed(monkeypatch, tmp_path):
    monkeypatch.setattr(plan, "PLAN_LEDGER_DIR", str(tmp_path))
    gate = plan.door_plan_gate("rm -rf ./build", "")
    assert gate["ok"] is True
    assert gate["reason"] == "no_session_presented"


def test_the_door_honours_the_opt_out(monkeypatch, tmp_path):
    monkeypatch.setattr(plan, "PLAN_LEDGER_DIR", str(tmp_path))
    monkeypatch.setenv("ESTATE_PLAN_LOCK", "off")
    gate = plan.door_plan_gate("rm -rf ./build", "harness:claude:4242")
    assert gate["ok"] is True
    assert gate["reason"] == "plan_lock_disabled"


def _plan_cli(*args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "estate-plan"), *args],
        capture_output=True,
        text=True,
        env=e,
    )


def test_the_shell_door_declares_the_plan_for_a_runtime_with_no_bridge(
    monkeypatch, tmp_path
):
    """Compliance is one command on every machine: the ledger is the plan, whoever writes it."""
    monkeypatch.setattr(plan, "PLAN_LEDGER_DIR", str(tmp_path))
    env = {"ESTATE_PLAN_LEDGER_DIR": str(tmp_path)}
    sid = "harness:codex:777"
    ok = _plan_cli("--session", sid, "declare_plan", json.dumps(GOAL), env=env)
    assert ok.returncode == 0, ok.stderr
    assert "Plan declared" in ok.stdout
    bdd = _plan_cli("--session", sid, "add_bdd", json.dumps(BDD), env=env)
    assert bdd.returncode == 0, bdd.stderr
    gate = plan.door_plan_gate("rm -rf ./build", sid)
    assert gate["ok"] is True, gate
    assert plan.ledger_plan(sid)["bdd"]["g1"]["then"] == "the button shows"


def test_the_shell_door_refuses_a_call_that_does_not_apply(monkeypatch, tmp_path):
    monkeypatch.setattr(plan, "PLAN_LEDGER_DIR", str(tmp_path))
    bad = _plan_cli(
        "--session",
        "harness:codex:778",
        "add_bdd",
        json.dumps(BDD),
        env={"ESTATE_PLAN_LEDGER_DIR": str(tmp_path)},
    )
    assert bad.returncode == 1
    assert "no plan declared" in bad.stderr
