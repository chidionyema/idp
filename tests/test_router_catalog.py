"""platform/llm/router_catalog.py writes the router's catalog into every installed harness."""

from __future__ import annotations

import http.server
import importlib.util
import json
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "router_catalog", ROOT / "platform/llm/router_catalog.py"
)
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

CATALOG = rc.build(
    {"served": ["deepseek", "default", "deepseek/*", "groq/*"]},
    {
        "deepseek": ["deepseek/deepseek-chat"],
        "groq": ["groq/qwen3-32b", "groq/llama-3.3-70b"],
    },
)
EXPECTED = [
    "deepseek",
    "default",
    "deepseek/deepseek-chat",
    "groq/qwen3-32b",
    "groq/llama-3.3-70b",
]


def test_catalog_is_aliases_then_every_discovered_model():
    assert rc.all_models(CATALOG) == EXPECTED


def test_opencode_gets_every_model_and_keeps_its_other_settings(tmp_path):
    cfg = tmp_path / ".config/opencode/opencode.jsonc"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"model": "litellm/deepseek", "theme": "x"}))
    assert rc.opencode(CATALOG, tmp_path) == "5 models"
    data = json.loads(cfg.read_text())
    assert (data["model"], data["theme"]) == ("litellm/deepseek", "x")
    assert list(data["provider"]["litellm"]["models"]) == EXPECTED
    assert data["provider"]["litellm"]["options"]["baseURL"] == rc.ROUTER


def test_pi_gets_an_estate_provider_and_keeps_others(tmp_path):
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"providers": {"ollama": {"baseUrl": "x"}}}))
    assert rc.pi(CATALOG, tmp_path) == "5 models"
    data = json.loads(cfg.read_text())
    assert data["providers"]["ollama"] == {"baseUrl": "x"}
    assert [m["id"] for m in data["providers"]["estate"]["models"]] == EXPECTED
    assert data["providers"]["estate"]["apiKey"] == "$LITELLM_API_KEY"


def test_a_config_with_comments_is_never_rewritten(tmp_path):
    cfg = tmp_path / ".config/opencode/opencode.jsonc"
    cfg.parent.mkdir(parents=True)
    original = '{\n  // mine\n  "model": "x"\n}\n'
    cfg.write_text(original)
    assert rc.opencode(CATALOG, tmp_path).startswith("skipped")
    assert cfg.read_text() == original


def test_an_absent_harness_is_not_created(tmp_path):
    assert rc.sync(CATALOG, tmp_path) == {"opencode": "absent", "pi": "absent"}
    assert list(tmp_path.iterdir()) == []


class _Plan(http.server.BaseHTTPRequestHandler):
    """A subscription endpoint: lists four models, refuses one, falls over on one."""

    def _send(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        ids = ["glm-5.3", "glm-5.3-flashx", "glm-5-turbo", "glm-flaky"]
        self._send(200, {"data": [{"id": i} for i in ids]})

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        model = json.loads(self.rfile.read(n))["model"]
        if self.headers["Authorization"] != "Bearer plan-key":
            self._send(401, {})
        elif model == "glm-5.3-flashx":
            self._send(
                429, {"error": {"code": "1311", "message": "plan does not include"}}
            )
        elif model == "glm-flaky":
            self._send(500, {})
        else:
            self._send(200, {"choices": [{"message": {"content": "1"}}]})

    def log_message(self, *a):
        pass


def test_a_plan_lane_lists_what_the_plan_answers_from_its_own_endpoint(monkeypatch):
    """#5697: the menu is the plan's own listing less what the plan refuses -- never LiteLLM's
    static list, which missed glm-5-turbo and named models the plan never served."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Plan)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("ZAI_API_KEY", "plan-key")
    try:
        got = rc.discover(
            {"zai": ["ZAI_API_KEY"]},
            {"zai": f"http://127.0.0.1:{srv.server_port}/api/coding/paas/v4/"},
        )
    finally:
        srv.shutdown()
    # flashx is refused by the plan; flaky's 500 is the endpoint's trouble, so it stays.
    assert got == {"zai": ["zai/glm-5-turbo", "zai/glm-5.3", "zai/glm-flaky"]}
