"""Acceptance tests for the via-negativa engine.

Per the founder 2026-09-13 spec: build the four primitives
(A: Go proxy, B: regex hook, C: injection, D: async RCA worker)
and prove they work end-to-end against the founder's pasted code.
"""
# ruff: noqa: S101

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROXY_DIR = REPO_ROOT / "bin" / "negative-constraints-proxy"
WORKER_DIR = REPO_ROOT / "bin" / "rca_worker"
GO_BIN = shutil.which("go")


@pytest.mark.skipif(GO_BIN is None, reason="go is not installed")
def test_go_proxy_compiles() -> None:
    """Primitive A: the Go interception sidecar builds cleanly."""
    result = subprocess.run(  # noqa: S603 - fixed argv built in this file, no shell
        [GO_BIN, "build", "-o", "/tmp/via-negativa-proxy-test", "."],  # noqa: S108
        cwd=str(PROXY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"go build failed:\n{result.stderr}\n{result.stdout}"


def test_go_proxy_returns_422_on_banned_tool() -> None:
    """Primitive A: a tool_call whose name contains 'rm_rf' is blocked with 422."""
    binary = "/tmp/via-negativa-proxy-test"  # noqa: S108
    if not os.path.exists(binary):
        pytest.skip("proxy binary not built (run test_go_proxy_compiles first)")

    # Run a dummy upstream that just 200s; we only care about pre-flight block.
    import http.server
    import threading

    class Upstream(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, *_args):  # silence
            pass

    upstream = http.server.HTTPServer(("127.0.0.1", 0), Upstream)
    upstream_port = upstream.server_address[1]
    threading.Thread(target=upstream.serve_forever, daemon=True).start()

    proxy = subprocess.Popen(  # noqa: S603 - fixed argv built in this file, no shell
        [binary],
        env={
            **os.environ,
            "LISTEN_ADDR": "127.0.0.1:18080",
            "UPSTREAM_URL": f"http://127.0.0.1:{upstream_port}",
            "REDIS_URL": "redis://127.0.0.1:1",  # unreachable — must fail-open per spec
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(2)  # wait for startup
        import urllib.request, urllib.error

        body = json.dumps(
            {
                "messages": [{"role": "user", "content": "do it"}],
                "tools": [{"function": {"name": "rm_rf_dangerous"}}],
            }
        ).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:18080/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310 - fixed http:// literal above
        assert exc.value.code == 422, f"expected 422, got {exc.value.code}"
    finally:
        proxy.terminate()
        try:
            proxy.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proxy.kill()
        upstream.shutdown()


def test_python_worker_imports() -> None:
    """Primitive D: the Python RCA worker module is importable."""
    spec = importlib.util.spec_from_file_location(
        "rca_worker_under_test",
        WORKER_DIR / "worker.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "NegativeConstraint")
    assert hasattr(module, "rule_allowed")
    assert hasattr(module, "build_prompt")


def test_negative_constraint_schema_rejects_subjective() -> None:
    """Primitive D guard: subjective rules are dropped (is_deterministic=False)."""
    from bin.rca_worker.worker import NegativeConstraint, rule_allowed

    nc = NegativeConstraint(
        scope="bash",
        signature_regex="EVERYTHING IS BAD",
        semantic_summary="code is broken",
        is_deterministic=False,
        confidence_score=0.99,
    )
    assert not rule_allowed(nc), "subjective rule must be dropped"


def test_negative_constraint_schema_rejects_low_confidence() -> None:
    """Primitive D guard: confidence < 0.6 is dropped per founder spec."""
    from bin.rca_worker.worker import NegativeConstraint, rule_allowed

    nc = NegativeConstraint(
        scope="python",
        signature_regex="ModuleNotFoundError: No module named 'foo'",
        semantic_summary="don't pip install without --break-system-packages",
        is_deterministic=True,
        confidence_score=0.4,
    )
    assert not rule_allowed(nc), "low-confidence rule must be dropped"


def test_negative_constraint_schema_accepts_deterministic_high_confidence() -> None:
    """Primitive D: a deterministic, high-confidence rule passes the guard."""
    from bin.rca_worker.worker import NegativeConstraint, rule_allowed

    nc = NegativeConstraint(
        scope="python",
        signature_regex=r"ModuleNotFoundError: No module named '([^']+)'",
        semantic_summary="declare missing modules in requirements.txt before importing",
        is_deterministic=True,
        confidence_score=0.92,
    )
    assert rule_allowed(nc), "deterministic high-confidence rule must be allowed"
    assert nc.scope == "python"
    assert 0.0 <= nc.confidence_score <= 1.0


def test_build_prompt_includes_command_exit_stderr() -> None:
    """Primitive D: the LLM prompt must contain command, exit code, stderr."""
    from bin.rca_worker.worker import build_prompt

    payload = {"command": "npm test", "exit_code": 1, "stderr": "FAIL: suite broken"}
    prompt = build_prompt(payload)
    assert "npm test" in prompt
    assert "1" in prompt
    assert "FAIL: suite broken" in prompt
