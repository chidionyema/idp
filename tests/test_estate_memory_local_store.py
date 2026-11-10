"""The local memory origin must stay fast and usable from concurrent HTTP handlers."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "platform" / "estate" / "memory" / "local_store.py"


def _module():
    spec = importlib.util.spec_from_file_location("estate_memory_local_store", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_concurrent_handlers_write_through_thread_local_connections(tmp_path):
    store = _module().Store(tmp_path / "memory.db")

    def remember(i: int) -> None:
        result = store.save(
            "estate",
            f"concurrent-{i}",
            {
                "content": f"concurrent memory fact {i}",
                "provenance": {"subject": "concurrency-test"},
            },
            None,
        )
        assert result["_status"] == 200, result

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(remember, range(24)))

    with sqlite3.connect(tmp_path / "memory.db") as conn:
        count = conn.execute(
            "SELECT count(*) FROM memories WHERE key LIKE 'concurrent-%'"
        ).fetchone()[0]
    assert count == 24


def test_healthz_proves_the_store_is_readable_and_does_not_log_success(tmp_path):
    module = _module()
    store = module.Store(tmp_path / "memory.db")
    logs: list[str] = []

    class Handler(module.Handler):
        def log_message(self, fmt: str, *args) -> None:
            logs.append(fmt % args)

    Handler.store = store
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/healthz"
        elapsed = []
        for _ in range(10):
            started = time.perf_counter()
            # noqa: S310 - loopback origin this test started itself, never a remote URL
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                body = json.loads(response.read())
            elapsed.append(time.perf_counter() - started)
            assert body == {"ok": True, "store": "sqlite", "db": "readable"}
    finally:
        server.shutdown()
        server.server_close()

    assert max(elapsed) < 0.25, elapsed
    assert logs == []
