"""platform/llm/active_memory.py: the router gives every agent's chat call the estate memory, run on real call shapes."""

import asyncio
import importlib.util
import json
import os
import sys
import time
import types

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(
    monkeypatch,
    tmp_path,
    url="http://memory.test:8000",
    focus_url="http://focus.test/claims",
):
    token = tmp_path / "token"
    token.write_text("surface-token\n")
    monkeypatch.setenv("ESTATE_MEMORY_URL", url)
    monkeypatch.setenv("ESTATE_MEMORY_TOKEN_FILE", str(token))
    monkeypatch.setenv("ESTATE_FOCUS_URL", focus_url)
    spec = importlib.util.spec_from_file_location(
        "active_memory", os.path.join(ROOT, "platform", "llm", "active_memory.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["active_memory"] = mod
    spec.loader.exec_module(mod)
    return mod


BRIEF = {
    "namespace": "estate",
    "relevant": [
        {
            "key": "edge.acme",
            "content": "meridian serves the Traefik default cert; HTTP-01 fails",
            "provenance": {"kind": "incident"},
        }
    ],
    "recent": [
        {
            "key": "d.1",
            "content": "router owns memory injection",
            "provenance": {"kind": "decision"},
        }
    ],
    "search_by_meaning": True,
}
# fleetview claims.claims_snapshot's row shape: `live` is its verdict, `reason` when not live.
FOCUS = {
    "available": True,
    "claims": [
        {
            "issue": 6645,
            "agent": "claude",
            "paths": ["platform/llm/active_memory.py"],
            "live": True,
        },
        {
            "issue": 6525,
            "agent": "otto",
            "paths": ["edge/x.yaml"],
            "live": False,
            "reason": "stale heartbeat",
        },
    ],
}


def _call(content, ua="claude-cli/2.1", extra_msgs=()):
    return {
        "model": "default",
        "messages": [
            {"role": "system", "content": "you are an agent"},
            *extra_msgs,
            {"role": "user", "content": content},
        ],
        "proxy_server_request": {"headers": {"user-agent": ua}},
    }


def _wire(mod, brief=BRIEF, focus=FOCUS):
    seen = {"brief": [], "focus": 0, "posts": []}

    def post(route, body, timeout):
        seen["posts"].append((route, body))
        if route == "/memories/brief":
            seen["brief"].append(body["task"])
            if isinstance(brief, Exception):
                raise brief
            return brief
        return {"memory_stats": {}}

    def get(url, timeout):
        seen["focus"] += 1
        if isinstance(focus, Exception):
            raise focus
        return focus

    mod._memory_post = post
    mod._get_json = get
    return seen


def _pre(mod, data, call_type="acompletion"):
    return asyncio.run(
        mod.proxy_handler_instance.async_pre_call_hook(None, None, data, call_type)
    )


def test_a_chat_call_carries_memory_and_only_live_focus(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod)
    out = _pre(mod, _call("fix the meridian cert"))
    last = out["messages"][-1]["content"]
    assert last.startswith(
        'fix the meridian cert\n\n<estate-memory agent="claude-cli">'
    )
    assert "[incident] meridian serves the Traefik default cert" in last
    assert "[decision] router owns memory injection" in last
    assert "#6645 claude: platform/llm/active_memory.py" in last
    # A stale claim is the ghost focus idp#6543 removed: never shown as held.
    assert "6525" not in last
    # The system prompt -- the client's cached prefix -- is byte-identical.
    assert out["messages"][0] == {"role": "system", "content": "you are an agent"}
    assert out["metadata"]["active_memory"]["agent"] == "claude-cli"


def test_a_tool_loop_asks_once_per_human_turn(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    _pre(mod, _call("fix the meridian cert"))
    # The agent's next call: the human turn, an assistant tool_use, then a tool_result user message.
    loop = _call(
        [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}],
        extra_msgs=[
            {"role": "user", "content": "fix the meridian cert"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}
                ],
            },
        ],
    )
    out = _pre(mod, loop)
    assert seen["brief"] == ["fix the meridian cert"], (
        "one brief per human turn, not per call"
    )
    assert seen["focus"] == 1, "focus is cached FOCUS_TTL_S"
    assert any(
        b.get("type") == "text" and "<estate-memory" in b["text"]
        for b in out["messages"][-1]["content"]
    )


def test_list_content_gets_a_text_block_in_its_own_shape(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod)
    out = _pre(mod, _call([{"type": "text", "text": "what is stuck?"}]))
    blocks = out["messages"][-1]["content"]
    assert blocks[0] == {"type": "text", "text": "what is stuck?"}
    assert blocks[-1]["type"] == "text" and blocks[-1]["text"].startswith(
        "<estate-memory"
    )


def test_a_memory_outage_costs_memory_not_the_answer(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod, brief=TimeoutError("timed out"), focus=OSError("connection refused"))
    data = _call("fix the meridian cert")
    out = _pre(mod, data)
    assert out["messages"][-1]["content"] == "fix the meridian cert"


def test_focus_still_rides_when_only_the_brief_fails(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod, brief=TimeoutError("timed out"))
    out = _pre(mod, _call("fix it"))
    assert "#6645 claude" in out["messages"][-1]["content"]


def test_a_slow_brief_does_not_cost_the_focus_that_answered(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTIVE_MEMORY_BUDGET_S", "0.2")
    mod = _load(monkeypatch, tmp_path)
    _wire(mod)
    slow = mod._memory_post
    mod._memory_post = lambda *a: time.sleep(1.5) or slow(*a)

    async def timed():
        # Timed inside the loop: asyncio.run's own exit waits for the leftover worker thread,
        # which the router's long-lived loop never does.
        t = time.time()
        out = await mod.proxy_handler_instance.async_pre_call_hook(
            None, None, _call("fix it"), "acompletion"
        )
        return out, time.time() - t

    out, took = asyncio.run(timed())
    assert took < 1.2, "the call waited for the slow brief"
    assert "#6645 claude" in out["messages"][-1]["content"]


def test_unreadable_focus_is_said_not_shown_as_free(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod, focus={"available": False, "error": "gh rate limited", "claims": []})
    out = _pre(mod, _call("fix it"))
    assert (
        "Active Focus: unreadable right now (gh rate limited)"
        in out["messages"][-1]["content"]
    )
    assert "no live claims" not in out["messages"][-1]["content"]


def _expire_focus(mod, age):
    mod._focus_cache[0] -= age
    mod._focus_tried[0] -= age


def test_an_expired_focus_is_served_while_one_read_replaces_it(monkeypatch, tmp_path):
    # The laptop door's gh search takes ~3.6 s, past the read deadline: a caller that waited
    # for it at every expiry lost the focus (idp#6678).
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    first = mod.fetch_focus()
    release = __import__("threading").Event()
    newer = dict(FOCUS, claims=[])

    def slow(url, timeout):
        seen["focus"] += 1
        release.wait(5)
        return newer

    mod._get_json = slow
    _expire_focus(mod, mod.FOCUS_TTL_S + 1)
    started = time.monotonic()
    assert mod.fetch_focus() is first, "the expired answer is served, not waited for"
    assert mod.fetch_focus() is first
    assert time.monotonic() - started < 1
    release.set()
    for _ in range(50):
        if mod._focus_cache[1] is newer:
            break
        time.sleep(0.02)
    assert mod.fetch_focus() is newer
    assert seen["focus"] == 2, "one background read, however many callers"


def test_an_unreadable_refresh_keeps_the_last_good_focus(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    good = mod.fetch_focus()
    mod._get_json = lambda url, timeout: {
        "available": False,
        "error": "gh",
        "claims": [],
    }
    _expire_focus(mod, mod.FOCUS_TTL_S + 1)
    mod._read_focus(time.time())
    assert mod.fetch_focus() is good
    assert seen["focus"] == 1


def test_a_focus_too_old_to_show_is_waited_for(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    _wire(mod)
    mod.fetch_focus()
    mod._get_json = lambda url, timeout: {
        "available": False,
        "error": "gh",
        "claims": [],
    }
    _expire_focus(mod, mod.FOCUS_STALE_S + 1)
    assert mod.fetch_focus()["available"] is False, (
        "past FOCUS_STALE_S it says unreadable"
    )


def test_calls_that_must_not_carry_memory_are_left_alone(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    # The memory server embeds through this router: a brief on an embedding would ask for itself.
    assert mod.skip_reason(_call("x"), "aembedding") == "call_type=aembedding"
    internal = _call("x")
    internal["metadata"] = {"estate_internal": mod.INTERNAL}
    assert mod.skip_reason(internal, "acompletion") == "internal"
    assert (
        mod.skip_reason(_call("x", ua="Python-urllib/3.12"), "acompletion")
        == "graph drain"
    )
    optout = _call("x")
    optout["proxy_server_request"]["headers"]["x-estate-memory"] = "off"
    assert mod.skip_reason(optout, "acompletion") == "caller opted out"
    for data, ct in (
        (_call("x"), "aembedding"),
        (internal, "acompletion"),
        (optout, "acompletion"),
    ):
        before = json.dumps(data, sort_keys=True)
        _pre(mod, data, ct)
        assert json.dumps(data, sort_keys=True) == before
    assert seen["posts"] == []


def test_a_request_that_already_carries_a_brief_is_not_briefed_twice(
    monkeypatch, tmp_path
):
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    once = _pre(mod, _call("fix it"))
    twice = _pre(mod, json.loads(json.dumps(once)))
    assert twice["messages"][-1]["content"].count("<estate-memory") == 1
    assert len(seen["brief"]) == 1


def test_unset_memory_url_is_a_no_op(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path, url="")
    seen = _wire(mod)
    out = _pre(mod, _call("fix it"))
    assert out["messages"][-1]["content"] == "fix it" and seen["posts"] == []


def test_identity_is_explicit_first_and_never_invented(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    named = _call("x", ua="OpenAI/Python 1.40")
    named["proxy_server_request"]["headers"]["X-Estate-Agent"] = "otto"
    assert mod.agent(named) == "otto"

    class Key:
        key_alias = "face-voice"

    assert mod.agent(_call("x", ua="OpenAI/Python 1.40"), Key()) == "face-voice"
    assert mod.agent(_call("x", ua="OpenAI/Python 1.40")) == "openai"
    assert mod.agent({"messages": []}) == "unknown"


def test_the_block_is_bounded(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    many = {
        "available": True,
        "claims": [
            {
                "issue": n,
                "agent": "a",
                "paths": [f"p{i}" for i in range(9)],
                "live": True,
            }
            for n in range(20)
        ],
    }
    block = mod.render({"relevant": [{"key": "k", "content": "x" * 5000}]}, many, "a")
    assert len(block) <= mod.MAX_CHARS + 60
    assert "+6 more" in block and "+12 more live claims" in block


def test_a_turn_is_written_once_as_untrusted_scratchpad(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    seen = _wire(mod)
    kwargs = {
        "call_type": "acompletion",
        "messages": [
            {
                "role": "user",
                "content": 'fix it\n\n<estate-memory agent="x">…</estate-memory>',
            }
        ],
        "litellm_params": {
            "proxy_server_request": {"headers": {"user-agent": "claude-cli/2.1"}}
        },
    }
    reply = {"choices": [{"message": {"content": "done"}}]}
    for _ in range(3):  # three tool-loop calls of one human turn
        asyncio.run(
            mod.proxy_handler_instance.async_log_success_event(kwargs, reply, 0, 0)
        )
    writes = [
        p for p in seen["posts"] if p[0].startswith("/harness/memory/consolidate")
    ]
    assert len(writes) == 1
    route, body = writes[0]
    # Rule B (harness.py): untrusted_external can never write a global preference.
    assert "provenance=untrusted_external" in route
    assert body[0]["scope"] == "ephemeral_turn" and body[0]["subject"] == "claude-cli"
    # The task is the human's words, not the brief the router appended.
    assert json.loads(body[0]["object"]) == {"asked": "fix it", "answered": "done"}


def test_the_token_is_read_per_call_so_a_rotation_lands(monkeypatch, tmp_path):
    mod = _load(monkeypatch, tmp_path)
    assert mod._token() == "surface-token"
    (tmp_path / "token").write_text("rotated")
    assert mod._token() == "rotated"


# --- laptop: the MCP door and the shared focus reader, never a second client


def _door_mode(monkeypatch, tmp_path, rows, key="gw-key"):
    import types

    monkeypatch.setenv("ESTATE_MEMORY_DOOR", "mcp")
    mod = _load(monkeypatch, tmp_path, url="", focus_url="")
    calls = []
    door = types.SimpleNamespace(
        MANIFEST={"door": {"key_env": "MCP_GATEWAY_KEY"}},
        key=lambda: key,
        call=lambda tool, args, secret, timeout: (
            calls.append((tool, args, secret)) or json.loads(json.dumps(BRIEF))
        ),
    )
    focus = types.SimpleNamespace(
        live_focus=lambda: rows,
        drop_stale=lambda items: ([i for i in items if i.get("key") != "d.1"], []),
    )
    mod._lib = lambda: (door, focus)
    mod._memory_post = lambda *a: (_ for _ in ()).throw(
        AssertionError("no REST on the laptop")
    )
    return mod, calls


def test_the_laptop_briefs_through_the_door_with_the_shared_focus_rules(
    monkeypatch, tmp_path
):
    rows = [
        {
            "claim": "idp#6597",
            "agent": "claude",
            "paths": "platform/llm/active_memory.py",
            "live": True,
        },
        {"claim": "idp#6525", "agent": "otto", "paths": "edge/x.yaml", "live": False},
    ]
    mod, calls = _door_mode(monkeypatch, tmp_path, rows)
    out = _pre(mod, _call("fix the meridian cert"))
    last = out["messages"][-1]["content"]
    assert calls == [
        ("brief", {"task": "fix the meridian cert", "limit": mod.BRIEF_LIMIT}, "gw-key")
    ]
    assert "#6597 claude: platform/llm/active_memory.py" in last and "6525" not in last
    # focus.drop_stale ran on the brief: the same ghost rule as bin/estate-brief.
    assert "router owns memory injection" not in last
    assert "meridian serves the Traefik default cert" in last


def test_the_laptop_says_when_the_ledger_is_unreadable(monkeypatch, tmp_path):
    mod, _ = _door_mode(monkeypatch, tmp_path, rows=None, key="")
    out = _pre(mod, _call("fix it"))
    # No key: no brief, but focus still rides -- and an unread ledger is said, not shown as free.
    assert "Active Focus: unreadable right now" in out["messages"][-1]["content"]


def test_the_laptop_writes_no_turn(monkeypatch, tmp_path):
    mod, _ = _door_mode(monkeypatch, tmp_path, rows=[])
    kwargs = {
        "call_type": "acompletion",
        "messages": [{"role": "user", "content": "fix it"}],
    }
    assert (
        mod.turn_record(kwargs, {"choices": [{"message": {"content": "done"}}]}) is None
    )


# --- wiring: a module the router cannot import, or cannot reach, is one that does nothing


def test_the_router_imports_it_from_a_mounted_configmap_on_its_path():
    cfg = yaml.safe_load(open(os.path.join(ROOT, "platform", "llm", "config.yaml")))
    assert (
        "active_memory.proxy_handler_instance" in cfg["litellm_settings"]["callbacks"]
    )
    kust = yaml.safe_load(
        open(os.path.join(ROOT, "platform", "llm", "kustomization.yaml"))
    )
    gen = {g["name"]: g["files"] for g in kust["configMapGenerator"]}
    assert "active_memory.py" in gen["litellm-request-ceiling"]
    deploy = open(os.path.join(ROOT, "platform", "llm", "litellm.yaml")).read()
    assert "/etc/litellm/ceilings" in deploy and "ESTATE_MEMORY_TOKEN_FILE" in deploy
    # The token is a file outside the /run/secrets/litellm/*/* export glob, never env.
    assert "/run/secrets/estate-memory/MEMORY_SURFACE_TOKEN" in deploy


def test_the_fence_lets_the_router_reach_the_memory_server_both_ways():
    allow = yaml.safe_load(
        open(os.path.join(ROOT, "platform", "ns-fences", "allowances.yaml"))
    )
    rows = allow["flows"]
    assert "unified-memory" in rows["llm"]["egress"]
    assert "llm" in rows["unified-memory"]["ingress_from"]
    fence = open(
        os.path.join(ROOT, "platform", "ns-fences", "network", "llm.yaml")
    ).read()
    assert "kubernetes.io/metadata.name: unified-memory" in fence


def test_a_stdlib_caller_that_names_itself_is_not_the_graph_drain(
    monkeypatch, tmp_path
):
    # fleetview-voice calls the cluster router with urllib and its own virtual key: it is an
    # agent, not the drain (docs/diagnoses/2026-10-20-stdlib-callers-skipped-as-graph-drain.yaml)
    mod = _load(monkeypatch, tmp_path)
    by_alias = _call("x", ua="Python-urllib/3.12")
    by_alias["metadata"] = {"user_api_key_alias": "fleetview-voice-20261008T193433Z"}
    assert mod.skip_reason(by_alias, "acompletion") == ""
    by_header = _call("x", ua="Python-urllib/3.12")
    by_header["proxy_server_request"]["headers"]["x-estate-agent"] = "newsroom"
    assert mod.skip_reason(by_header, "acompletion") == ""
    by_key = types.SimpleNamespace(key_alias="fleetview-voice-20261008T193433Z")
    assert (
        mod.skip_reason(_call("x", ua="Python-urllib/3.12"), "acompletion", by_key)
        == ""
    )
    # the drain itself (keyless laptop router, growmos cannot set a header) is still left alone
    assert (
        mod.skip_reason(_call("x", ua="Python-urllib/3.9"), "acompletion", None)
        == "graph drain"
    )
