"""Falsifier for meridian-fitness partial-secret admission (idp#8759, idp#3525).

Measured on run 46132706055 (2026-11-28): `openrouter` passed `FIT (readiness-1)`, yet
`meridian-fitness` exited 1 (`ESCALATE/1 founder secret boundary`) because other optional
providers (`SEED_DEEPSEEK_API_KEY`, `SEED_GROQ_API_KEY`, `SEED_ZAI_API_KEY`) were unset in
the runner environment. That halted cloud admission even when a FIT route existed.

Contract:
- If at least one route is FIT, unset/refused optional provider secrets are reported in the
  JSON summary (`missing_or_refused`) and stderr notice, and the binary exits 0 so
  `bin/legion-admit --harness auto` can admit the fit route.
- If zero routes are FIT and any secret is missing/refused, the binary STILL fails closed
  with exit 1 and `ESCALATE/1 founder secret boundary: missing_or_refused=...`.
- If zero routes exist in the registry, the binary fails closed with exit 1 and `ESCALATE/1`.
"""

from __future__ import annotations

import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN_RS = ROOT / "crates" / "meridian-fitness" / "src" / "main.rs"


class _MockOpenAIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        auth = self.headers.get("Authorization", "")
        if auth == "Bearer bad-key":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error":"unauthorized"}')
            return
        body = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "legion_ready",
                                        "arguments": '{"ready": true}',
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def fitness_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    rustc = shutil.which("rustc")
    if not rustc:
        pytest.skip("rustc not installed on this host")
    out = tmp_path_factory.mktemp("meridian_fitness_bin") / "meridian-fitness"
    res = subprocess.run(
        [rustc, "--edition", "2021", str(MAIN_RS), "-o", str(out)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return out


def _write_provider(providers_dir: Path, name: str, base: str, key_env: str) -> None:
    providers_dir.mkdir(parents=True, exist_ok=True)
    (providers_dir / f"{name}.toml").write_text(
        f'id = "{name}"\n'
        f'dialect = "openai"\n'
        f'base_url = "{base}"\n'
        f'request_path = "/chat/completions"\n'
        f"\n"
        f"[auth]\n"
        f'kind = "bearer"\n'
        f'key_env = "{key_env}"\n'
        f"\n"
        f"[[models]]\n"
        f'id = "{name}/free-test"\n'
        f'class = "free"\n'
        f"context_window = 131072\n"
        f"price_in_per_mtok = 0\n"
        f"price_out_per_mtok = 0\n",
        encoding="utf-8",
    )


def _start_server() -> tuple[socketserver.TCPServer, str]:
    srv = socketserver.TCPServer(("127.0.0.1", 0), _MockOpenAIHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_fit_route_admits_even_when_optional_provider_secret_is_unset(
    fitness_bin: Path, tmp_path: Path
) -> None:
    """Regression (#8759): 1 FIT route + 1 unset optional key must exit 0, not ESCALATE/1."""
    srv, base = _start_server()
    try:
        providers = tmp_path / "providers"
        fitness_dir = tmp_path / "fitness"
        _write_provider(providers, "openrouter", base, "OPENROUTER_API_KEY")
        _write_provider(providers, "groq", base, "GROQ_API_KEY")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "MERIDIAN_FITNESS_PYTHON": sys.executable,
            "MERIDIAN_FITNESS_ALLOW_LOOPBACK": "1",
            "OPENROUTER_API_KEY": "good-key",
        }
        res = subprocess.run(
            [
                str(fitness_bin),
                "--fitness-dir",
                str(fitness_dir),
                "--providers-dir",
                str(providers),
                "--secret-name-template",
                "SEED_{key_env}",
                "--timeout",
                "10",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        srv.shutdown()
        srv.server_close()

    assert res.returncode == 0, res.stdout + res.stderr
    assert "ESCALATE/1" not in res.stdout
    summary = json.loads(res.stdout.strip().splitlines()[0])
    assert summary["fit"] == 1
    assert summary["written"] == 1
    assert summary["missing_or_refused"] == ["SEED_GROQ_API_KEY"]
    assert "SEED_GROQ_API_KEY" in res.stderr


def test_zero_fit_routes_with_missing_secret_still_escalates(
    fitness_bin: Path, tmp_path: Path
) -> None:
    """Falsifier: when zero routes are FIT and a secret is missing, exit 1 + ESCALATE/1."""
    providers = tmp_path / "providers"
    fitness_dir = tmp_path / "fitness"
    _write_provider(providers, "groq", "http://127.0.0.1:9", "GROQ_API_KEY")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "MERIDIAN_FITNESS_PYTHON": sys.executable,
        "MERIDIAN_FITNESS_ALLOW_LOOPBACK": "1",
    }
    res = subprocess.run(
        [
            str(fitness_bin),
            "--fitness-dir",
            str(fitness_dir),
            "--providers-dir",
            str(providers),
            "--secret-name-template",
            "SEED_{key_env}",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert (
        "ESCALATE/1 founder secret boundary: missing_or_refused=SEED_GROQ_API_KEY"
        in res.stdout
    )


def test_empty_registry_fails_closed(fitness_bin: Path, tmp_path: Path) -> None:
    """Falsifier: empty provider registry exits 1 with ESCALATE/1."""
    providers = tmp_path / "providers"
    providers.mkdir()
    fitness_dir = tmp_path / "fitness"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "MERIDIAN_FITNESS_PYTHON": sys.executable,
        "MERIDIAN_FITNESS_ALLOW_LOOPBACK": "1",
    }
    res = subprocess.run(
        [
            str(fitness_bin),
            "--fitness-dir",
            str(fitness_dir),
            "--providers-dir",
            str(providers),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert "ESCALATE/1" in res.stdout
