"""[10] the router's read shunt: every harness's whole-file read becomes a digest, the same one forever."""

import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = "".join(f"{i:>6}\tline {i}\n" for i in range(1, 801))


def _gw(
    monkeypatch,
    tmp_path,
    digest="PURPOSE: x\nSTRUCTURE: L1-L800 y\nREAD EXACTLY: L1-L5",
):
    monkeypatch.setenv("ESTATE_READ_SHUNT_DIR", str(tmp_path / "shunt"))
    spec = importlib.util.spec_from_file_location(
        "gw_read_shunt", os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")
    )
    gw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gw)
    seen = []

    def worker(path, text, lines):
        seen.append(path)
        if isinstance(digest, Exception):
            raise digest
        return digest

    monkeypatch.setattr(gw, "_shunt_digest", worker)
    return gw, seen


def _openai(name, args, text=BIG):
    return {
        "messages": [
            {"role": "user", "content": "look"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "t1", "type": "function",
                     "function": {"name": name, "arguments": json.dumps(args)}}
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "content": text},
        ]
    }  # fmt: skip


def _anthropic(args, text=BIG):
    return {
        "messages": [
            {"role": "user", "content": "look"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "Read", "input": args}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": [{"type": "text", "text": text}]}]},
        ]
    }  # fmt: skip


def _result(data):
    m = data["messages"][2]
    return m["content"] if m["role"] == "tool" else m["content"][0]["content"]


def test_opencode_pi_and_claude_code_reads_all_become_the_digest(monkeypatch, tmp_path):
    gw, seen = _gw(monkeypatch, tmp_path)
    for data in (
        _openai("read", {"filePath": "/a.py"}),  # opencode
        _openai("read", {"path": "/b.py"}),  # pi
        _anthropic({"file_path": "/c.py"}),  # Claude Code
    ):
        step = gw._shunt_reads(data)
        assert step["action"] == "shunted" and step["bytes"] > 0
        assert "router read-shunt" in _result(data) and "STRUCTURE" in _result(data)
    assert seen == [
        "/a.py"
    ]  # one content hash, one worker call, one digest for all three


def test_ranged_small_and_other_tools_pass_untouched(monkeypatch, tmp_path):
    gw, seen = _gw(monkeypatch, tmp_path)
    for data in (
        _openai("read", {"filePath": "/a.py", "offset": 100, "limit": 50}),
        _anthropic({"file_path": "/a.py", "limit": 2000}),
        _openai("read", {"filePath": "/a.py"}, text="short\n" * 10),
        _openai("bash", {"command": "cat /a.py"}),
    ):
        sent = json.dumps(data)
        assert gw._shunt_reads(data)["action"] == "none"
        assert json.dumps(data) == sent
    assert seen == []


def test_every_later_call_sends_the_same_bytes_even_when_the_worker_failed(
    monkeypatch, tmp_path
):
    gw, _ = _gw(monkeypatch, tmp_path)
    a, b = (
        _openai("read", {"filePath": "/a.py"}),
        _openai("read", {"filePath": "/a.py"}),
    )
    gw._shunt_reads(a)
    monkeypatch.setattr(
        gw, "_shunt_digest", lambda *x: "PURPOSE STRUCTURE READ EXACTLY other"
    )
    gw._shunt_reads(b)
    assert _result(a) == _result(b)  # decided once: the prefix cache still hits

    gw2, _ = _gw(monkeypatch, tmp_path / "2", digest=TimeoutError("slow"))
    c = _openai("read", {"filePath": "/z.py"}, text=BIG + "z\n")
    assert gw2._shunt_reads(c)["action"] == "none" and _result(c) == BIG + "z\n"
    monkeypatch.setattr(
        gw2, "_shunt_digest", lambda *x: "PURPOSE STRUCTURE READ EXACTLY"
    )
    assert (
        gw2._shunt_reads(c)["action"] == "none"
    )  # a pass is persisted too, never flips
