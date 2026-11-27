"""The next session is told which sessions died, how and when (idp#8624).

Session 21ea7eac (2026-11-26) ended on three consecutive `API Error: Connection refused` messages
after it booted out the listener serving its own ANTHROPIC_BASE_URL; the founder typed "go on" twice
into a dead session, and the next session started blind: the fleet calls all 1984 sessions
`stopped`. bin/estate-brief, which every runtime's session start runs, now names each session of
the last 24 h that did not end cleanly. These cases run the real bin/estate-brief with HOME in a
temp dir holding Claude Code and pi transcripts, so no door, key or network is touched.

    python3 tests/test_brief_names_unclean_endings.py --optimus
        -> optimus.brief.unclean_endings_unreported=<n>   (main: 3, the fix: 0)
"""

from __future__ import annotations

import json
import os
import site
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "bin" / "estate-brief"
sys.path.insert(0, str(ROOT / "platform" / "estate" / "memory"))
HOUR = 3600


def _cc(*entries: dict) -> str:
    return "\n".join(json.dumps(e) for e in entries) + "\n"


def cc_user(text, ts):
    return {
        "type": "user",
        "timestamp": ts,
        "message": {"role": "user", "content": text},
    }


def cc_text(text, ts, synthetic=False):
    e = {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "role": "assistant",
            "model": "<synthetic>" if synthetic else "claude-opus-5-5",
            "stop_reason": "stop_sequence" if synthetic else "end_turn",
            "content": [{"type": "text", "text": text}],
        },
    }
    if synthetic:
        e["isApiErrorMessage"] = True
    return e


def cc_tool(name, ts):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "role": "assistant",
            "model": "claude-opus-5-5",
            "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "name": name, "id": "t1", "input": {}}],
        },
    }


def pi(role, ts, stop=None, error=None, content=None):
    m = {"role": role, "content": content or [{"type": "text", "text": "x"}]}
    if stop:
        m["stopReason"] = stop
    if error:
        m["errorMessage"] = error
    return {"type": "message", "timestamp": ts, "message": m}


ERR = "API Error: Connection refused (ECONNREFUSED)"
SESSIONS = {
    # name: (relative path, body, age seconds, expected verdict)
    "died": (
        ".estate/harness/cc/projects/-Users-x/21ea7eac-0000-0000-0000-000000000001.jsonl",
        _cc(
            cc_user("free the disk", "2026-11-26T18:50:00Z"),
            cc_tool("Bash", "2026-11-26T18:51:46Z"),
            {
                "type": "user",
                "timestamp": "2026-11-26T18:53:41Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
                    ],
                },
            },
            cc_text(ERR, "2026-11-26T18:53:43Z", synthetic=True),
            cc_user("go on", "2026-11-26T18:55:32Z"),
            cc_text(ERR, "2026-11-26T18:55:34Z", synthetic=True),
            cc_user("go on", "2026-11-26T18:55:45Z"),
            cc_text(ERR, "2026-11-26T18:55:47Z", synthetic=True),
        )
        + "{not json\n",
        2 * HOUR,
        "API-ERROR",
    ),
    "killed": (
        ".estate/harness/cc/projects/-Users-x/aaaa1111-0000-0000-0000-000000000002.jsonl",
        _cc(
            cc_user("build it", "2026-11-27T06:00:00Z"),
            cc_tool("Edit", "2026-11-27T06:00:09Z"),
        ),
        3 * HOUR,
        "MID-TURN",
    ),
    "pi-error": (
        ".pi/agent/sessions/--Users-x--/2026-11-27T05-00-00-000Z_bbbb2222.jsonl",
        "\n".join(
            json.dumps(e)
            for e in (
                pi("user", "2026-11-27T05:00:00Z"),
                pi(
                    "assistant",
                    "2026-11-27T05:00:02Z",
                    stop="error",
                    error="502 lane groq down",
                ),
            )
        )
        + "\n",
        4 * HOUR,
        "API-ERROR",
    ),
    "clean": (
        ".estate/harness/cc/projects/-Users-x/cccc3333-0000-0000-0000-000000000003.jsonl",
        _cc(
            cc_user("hi", "2026-11-27T04:00:00Z"),
            cc_text("Done: PR #1 opened.", "2026-11-27T04:00:05Z"),
        ),
        5 * HOUR,
        "ENDED",
    ),
    "live": (
        ".estate/harness/cc/projects/-Users-x/dddd4444-0000-0000-0000-000000000004.jsonl",
        _cc(
            cc_user("hi", "2026-11-27T08:00:00Z"),
            cc_tool("Bash", "2026-11-27T08:00:01Z"),
        ),
        30,
        "MID-TURN",
    ),
    "old": (
        ".estate/harness/cc/projects/-Users-x/eeee5555-0000-0000-0000-000000000005.jsonl",
        _cc(
            cc_user("hi", "2026-11-20T00:00:00Z"),
            cc_tool("Bash", "2026-11-20T00:00:01Z"),
        ),
        72 * HOUR,
        "MID-TURN",
    ),
}
UNCLEAN = ("died", "killed", "pi-error")


def bare_home(tmp: Path) -> Path:
    # a fresh state page, so the brief reads it instead of re-running every law's checks
    page = tmp / ".estate/state/state-page.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("state page (fixture)\n")
    return tmp


def make_home(tmp: Path) -> Path:
    now = time.time()
    bare_home(tmp)
    for rel, body, age, _ in SESSIONS.values():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        os.utime(p, (now - age, now - age))
    return tmp


def brief(home: Path) -> str:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("MCP_GATEWAY", "CLAUDE_CONFIG"))
    }
    # a temp HOME would hide the user site-packages (pydantic, for the write guard)
    env.update(HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    proc = subprocess.run(
        [sys.executable, str(BRIEF), "--timeout", "1"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def short(name: str) -> str:
    return Path(SESSIONS[name][0]).stem.split("_")[-1][:8]


def test_each_verdict_is_read_from_the_transcript_itself(tmp_path):
    import session_end

    home = make_home(tmp_path)
    for name, (rel, _, _, verdict) in SESSIONS.items():
        got = session_end.classify(home / rel)
        assert got["verdict"] == verdict, (name, got)
    died = session_end.classify(home / SESSIONS["died"][0])
    assert died["errors"] == 3 and "ECONNREFUSED" in died["error"]
    assert died["malformed"] == 1, "a malformed line costs that line, and is counted"
    assert died["last_action"] == "Bash"


def test_the_brief_names_every_unclean_ending_and_nothing_else(tmp_path):
    out = brief(make_home(tmp_path))
    for name in UNCLEAN:
        assert short(name) in out, (name, out)
    assert "API-ERROR x3" in out and "ECONNREFUSED" in out
    for name in ("clean", "live", "old"):
        assert short(name) not in out, name


def test_a_missing_or_empty_store_prints_no_section(tmp_path):
    assert "did not end cleanly" not in brief(bare_home(tmp_path))


def test_the_real_dead_session_if_this_laptop_has_it():
    real = (
        Path.home()
        / ".estate/harness/cc/projects/-Users-roseonyema/21ea7eac-af8c-4c71-bd30-e586bc621cf5.jsonl"
    )
    if not real.exists():
        return  # CI: the fixture above is the same shape
    import session_end

    got = session_end.classify(real)
    assert got["verdict"] == "API-ERROR" and got["errors"] >= 3, got


def unreported() -> int:
    with tempfile.TemporaryDirectory(prefix="brief-endings-") as tmp:
        out = brief(make_home(Path(tmp)))
    return sum(short(n) not in out for n in UNCLEAN)


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(f"optimus.brief.unclean_endings_unreported={unreported()}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
