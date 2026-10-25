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


LISTED = """\
provider  model                 context  max-out  thinking  images
deepseek  deepseek              200K     384K     yes       yes
deepseek  deepseek-flash        1M       384K     yes       yes
minimax   MiniMax-M2.7          204.8K   131.1K   yes       no
minimax   MiniMax-M3            1M       512K     yes       yes
estate    deepseek              128K     16.4K    no        no
"""


def test_pi_list_models_table_is_read_as_windows():
    assert rc.parse_list_models(LISTED) == {
        "deepseek": {"deepseek": 200_000, "deepseek-flash": 1_000_000},
        "minimax": {"MiniMax-M2.7": 204_800, "MiniMax-M3": 1_000_000},
        "estate": {"deepseek": 128_000},
    }


def test_pis_direct_provider_models_are_capped_to_the_ceiling(tmp_path, monkeypatch):
    """7,912 of 7,936 over-ceiling pi calls went straight to deepseek/minimax with pi's own
    keys, compacting against those models' native 1M windows. Every direct model above the
    ceiling is overridden down to it; one already below keeps its own window."""
    monkeypatch.setattr(rc, "working_window", lambda: 200_000)
    monkeypatch.setattr(rc, "pi_listed", lambda: rc.parse_list_models(LISTED))
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps(
            {
                "providers": {
                    "minimax": {"modelOverrides": {"MiniMax-M3": {"name": "M3"}}}
                }
            }
        )
    )
    assert rc.pi(CATALOG, tmp_path) == "5 models, 3 direct capped"
    providers = json.loads(cfg.read_text())["providers"]
    assert providers["deepseek"]["modelOverrides"] == {
        "deepseek-flash": {"contextWindow": 200_000}
    }
    assert providers["minimax"]["modelOverrides"] == {
        "MiniMax-M2.7": {"contextWindow": 200_000},
        "MiniMax-M3": {"name": "M3", "contextWindow": 200_000},
    }


def test_a_second_run_keeps_its_own_caps(tmp_path, monkeypatch):
    """After the first run pi lists capped models at the ceiling, not their native 1M. The
    second run must not read that as "fits already" and drop or miscount them."""
    monkeypatch.setattr(rc, "working_window", lambda: 200_000)
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{}")
    monkeypatch.setattr(rc, "pi_listed", lambda: rc.parse_list_models(LISTED))
    rc.pi(CATALOG, tmp_path)
    first = json.loads(cfg.read_text())["providers"]
    monkeypatch.setattr(
        rc, "pi_listed", lambda: {"deepseek": {"deepseek-flash": 200_000}}
    )
    assert rc.pi(CATALOG, tmp_path) == "5 models, 1 direct capped"
    assert json.loads(cfg.read_text())["providers"]["deepseek"] == first["deepseek"]


def test_pi_unreachable_leaves_direct_overrides_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "pi_listed", lambda: None)
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    kept = {"modelOverrides": {"deepseek-flash": {"contextWindow": 200_000}}}
    cfg.write_text(json.dumps({"providers": {"deepseek": kept}}))
    assert rc.pi(CATALOG, tmp_path) == "5 models, direct not checked (pi not found)"
    assert json.loads(cfg.read_text())["providers"]["deepseek"] == kept


def test_pi_gets_an_estate_provider_and_keeps_others(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "pi_listed", lambda: {})
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"providers": {"ollama": {"baseUrl": "x"}}}))
    assert rc.pi(CATALOG, tmp_path) == "5 models, 0 direct capped"
    data = json.loads(cfg.read_text())
    assert data["providers"]["ollama"] == {"baseUrl": "x"}
    assert [m["id"] for m in data["providers"]["estate"]["models"]] == EXPECTED
    assert data["providers"]["estate"]["apiKey"] == "$LITELLM_API_KEY"


def test_pi_is_told_the_routers_working_window_not_its_own_default(
    tmp_path, monkeypatch
):
    """pi falls back to contextWindow=128000 when the model omits it, so it compacted against a
    number the router never set. Every model carries the router's ceiling instead."""
    monkeypatch.setattr(rc, "working_window", lambda: 200_000)
    cfg = tmp_path / ".pi/agent/models.json"
    cfg.parent.mkdir(parents=True)
    rc.pi(CATALOG, tmp_path)
    models = json.loads(cfg.read_text())["providers"]["estate"]["models"]
    assert models and all(m["contextWindow"] == 200_000 for m in models)


def test_the_window_pi_is_given_is_the_ceiling_the_router_enforces():
    s = importlib.util.spec_from_file_location(
        "request_ceiling_src", ROOT / "platform/llm/request_ceiling.py"
    )
    ceiling = importlib.util.module_from_spec(s)
    s.loader.exec_module(ceiling)
    assert rc.working_window() == ceiling.MAX_INPUT_TOKENS == 200_000


def test_pi_is_found_without_nvm_on_path(tmp_path, monkeypatch):
    """launchd gives the router PATH=/usr/bin:/bin:/usr/sbin:/sbin; pi lives under nvm."""
    exe = tmp_path / ".nvm/versions/node/v22.15.1/bin/pi"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.delenv("ESTATE_PI_BIN", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    monkeypatch.setattr(rc.Path, "home", lambda: tmp_path)
    assert rc.pi_bin() == str(exe)


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
