"""A completion sent while Telegram is unreachable is delivered later, never lost (idp#8619).

AGENTS.md: "Every completed task is delivered to Telegram ... Silence is not completion." The
notifier every harness calls (`estate-notify-done`) made one attempt and raised, and lived only in
~/.estate/bin, untracked. A blip at the end of a turn meant the founder never heard the work was
done. These cases run the real script as a subprocess against a local fake Telegram, with HOME in a
temp dir, so no network and no credential is touched.

    python3 tests/test_notify_done_never_loses_a_completion.py --optimus
        -> optimus.notify.completions_lost=<n>   (the one-attempt notifier: 1, this one: 0)
"""

from __future__ import annotations

import ast
import http.server
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(
    os.environ.get("NOTIFY_DONE_SCRIPT") or ROOT / "bin" / "estate-notify-done"
)
TOKEN = "123456:TEST-token-never-printed"  # noqa: S105 - a fixture token, never a credential
SECRET = "sk-" + "A" * 24


class FakeTelegram:
    """Answers each sendMessage with the next code in `script` (then 200); records what landed."""

    def __init__(self, script: list[int] | None = None) -> None:
        self.script = list(script or [])
        self.received: list[str] = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):  # quiet
                pass

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                code = owner.script.pop(0) if owner.script else 200
                if code == 200:
                    from urllib.parse import parse_qs

                    owner.received.append(parse_qs(body)["text"][0])
                    payload = {"ok": True}
                elif code == 429:
                    payload = {"ok": False, "parameters": {"retry_after": 1}}
                else:
                    payload = {"ok": False, "description": f"code {code}"}
                data = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _closed_url() -> str:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


def _home(tmp: Path) -> Path:
    env_file = tmp / ".config/estate/estate.env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text(f"TELEGRAM_BOT_TOKEN={TOKEN}\nTELEGRAM_HOME_CHANNEL=42\n")
    return tmp


def run(
    home: Path, api: str, *args: str, budget: str = "15"
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "ESTATE_TELEGRAM_API": api,
        "ESTATE_NOTIFY_BUDGET_S": budget,
    }
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert TOKEN not in proc.stdout + proc.stderr, "the bot token was printed"
    return proc


def outbox(home: Path) -> list[Path]:
    return sorted((home / ".estate/notifications/telegram-outbox").glob("*.json"))


def test_a_transient_failure_is_retried_inside_the_call(tmp_path):
    home, tg = _home(tmp_path), FakeTelegram([500])
    try:
        proc = run(home, tg.url, "--key", "k1", "--text", "done one")
    finally:
        tg.close()
    assert proc.returncode == 0
    assert tg.received == ["done one"] and outbox(home) == []


def test_a_rate_limit_is_waited_out(tmp_path):
    home, tg = _home(tmp_path), FakeTelegram([429])
    try:
        proc = run(home, tg.url, "--key", "k1", "--text", "done")
    finally:
        tg.close()
    assert proc.returncode == 0 and tg.received == ["done"]


def test_an_outage_queues_it_redacted_and_private_and_does_not_fail_the_turn(tmp_path):
    home = _home(tmp_path)
    proc = run(home, _closed_url(), "--key", "k1", "--text", f"done {SECRET}")
    assert proc.returncode == 0, "a notifier must never fail the work it reports on"
    assert "QUEUED" in proc.stderr
    [entry] = outbox(home)
    assert SECRET not in entry.read_text() and "[REDACTED]" in entry.read_text()
    assert stat.S_IMODE(entry.stat().st_mode) == 0o600


def test_flush_delivers_what_the_outage_kept(tmp_path):
    home = _home(tmp_path)
    run(home, _closed_url(), "--key", "k1", "--text", "done while down")
    tg = FakeTelegram()
    try:
        proc = run(home, tg.url, "--flush")
    finally:
        tg.close()
    assert proc.returncode == 0 and "delivered=1" in proc.stdout
    assert tg.received == ["done while down"] and outbox(home) == []


def test_the_next_completion_carries_the_queued_one(tmp_path):
    home = _home(tmp_path)
    run(home, _closed_url(), "--key", "k1", "--text", "first, while down")
    tg = FakeTelegram()
    try:
        run(home, tg.url, "--key", "k2", "--text", "second")
    finally:
        tg.close()
    assert tg.received == ["first, while down", "second"] and outbox(home) == []


def test_once_per_key_and_text(tmp_path):
    home, tg = _home(tmp_path), FakeTelegram()
    try:
        run(home, tg.url, "--key", "k1", "--text", "same")
        run(home, tg.url, "--key", "k1", "--text", "same")
        run(home, tg.url, "--flush")
    finally:
        tg.close()
    assert tg.received == ["same"]


def test_a_refused_message_is_retired_by_name_not_retried_forever(tmp_path):
    home, tg = _home(tmp_path), FakeTelegram([403] * 40)
    try:
        run(home, tg.url, "--key", "k1", "--text", "bad chat")
        assert len(outbox(home)) == 1
        last = None
        for _ in range(20):
            last = run(home, tg.url, "--flush")
    finally:
        tg.close()
    assert outbox(home) == []
    dead = list((home / ".estate/notifications/telegram-outbox/dead").glob("*.json"))
    assert len(dead) == 1 and "retired" in last.stderr


def test_a_long_outbox_cannot_hold_the_turn_past_its_budget(tmp_path):
    home = _home(tmp_path)
    down = _closed_url()
    for i in range(5):
        run(home, down, "--key", f"k{i}", "--text", f"queued {i}", budget="3")
    start = time.monotonic()
    proc = run(home, down, "--key", "k9", "--text", "one more", budget="4")
    assert time.monotonic() - start < 8, "one probe per call, not one per queued entry"
    assert proc.returncode == 0 and len(outbox(home)) == 6


def test_runtime_sync_installs_it_from_main():
    """The notifier is delivered like every other launcher, so a fix here reaches the laptop."""
    tree = ast.parse((ROOT / "bin" / "estate-runtime-sync").read_text())
    names = next(
        ast.literal_eval(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", "") == "LAUNCHERS" for t in node.targets)
    )
    assert "estate-notify-done" in names


def completions_lost() -> int:
    """Two completions: the first while Telegram is down, the second once it is back."""
    with tempfile.TemporaryDirectory(prefix="notify-optimus-") as tmp:
        home = _home(Path(tmp))
        run(home, _closed_url(), "--key", "a", "--text", "first", budget="6")
        tg = FakeTelegram()
        try:
            run(home, tg.url, "--key", "b", "--text", "second", budget="6")
        finally:
            tg.close()
        return 2 - len(tg.received)


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(f"optimus.notify.completions_lost={completions_lost()}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
