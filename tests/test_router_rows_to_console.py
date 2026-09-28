"""bin/idp-router-rows-to-console moves git lanes to the console and prints no value.

Founder 2026-09-03 "enable the thing": the console's Update API Key form is greyed out on a
row defined in config.yaml. The tool copies each lane into the console with the vendor key the
vault holds. This suite runs it against a fake router and a fake vault: a lane the console owns
is kept, a lane it lacks is posted with the resolved key, a lane whose key the vault lacks is a
FAIL naming the key's NAME, and no key value ever reaches stdout (R49).
"""

import json
import os
import pathlib
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin/idp-router-rows-to-console"

VAULT = {
    "LITELLM_MASTER_KEY": "sk-master-0123456789abcdef",
    "ANTHROPIC_API_KEY": "sk-ant-value-never-printed",
    "DEEPSEEK_API_KEY": "sk-deepseek-value-never-printed",
}

CONFIG = {
    "model_list": [
        {
            "model_name": "claude",
            "litellm_params": {
                "model": "anthropic/claude-x",
                "api_key": "os.environ/ANTHROPIC_API_KEY",
            },
            "model_info": {"max_input_tokens": 200000},
        },
        {
            "model_name": "deepseek",
            "litellm_params": {
                "model": "deepseek/deepseek-chat",
                "api_key": "os.environ/DEEPSEEK_API_KEY",
            },
        },
        {
            "model_name": "mystery",
            "litellm_params": {
                "model": "vendor/m",
                "api_key": "os.environ/MYSTERY_API_KEY",
            },
        },
    ]
}


class FakeRouter(BaseHTTPRequestHandler):
    posted: list[dict] = []
    auth: list[str] = []

    def log_message(self, *_):  # quiet
        pass

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.auth.append(self.headers.get("Authorization", ""))
        if self.path == "/model/info":
            self._send(
                200,
                {
                    "data": [
                        {  # the console already owns claude
                            "model_name": "claude",
                            "litellm_params": {"model": "anthropic/claude-x"},
                            "model_info": {"id": "db-1", "db_model": True},
                        },
                        {  # the git row of deepseek, not console-owned
                            "model_name": "deepseek",
                            "litellm_params": {"model": "deepseek/deepseek-chat"},
                            "model_info": {"id": "cfg-1", "db_model": False},
                        },
                    ]
                },
            )
        else:
            self._send(404, {})

    def do_POST(self):
        self.auth.append(self.headers.get("Authorization", ""))
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n))
        if self.path == "/model/new":
            self.posted.append(body)
            self._send(200, {"model_id": "db-2"})
        else:
            self._send(404, {})


def _serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeRouter)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _fake_cloud(tmp_path: pathlib.Path, doc: dict) -> pathlib.Path:
    vault = tmp_path / "vault.json"
    vault.write_text(json.dumps(doc))
    cloud = tmp_path / "idp-cloud"
    cloud.write_text(
        f'#!/bin/sh\n[ "$1 $2 $3" = "secret get litellm-upstream" ] || exit 1\ncat "{vault}"\n'
    )
    cloud.chmod(cloud.stat().st_mode | stat.S_IXUSR)
    return cloud


def _run(tmp_path, srv, vault=VAULT, extra=()):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump(CONFIG))
    zone = tmp_path / "estate-config.yaml"
    zone.write_text("ESTATE_ZONE: example.test\n")
    env = {
        **os.environ,
        "IDP_CLOUD": str(_fake_cloud(tmp_path, vault)),
        "ROUTER_URL": f"http://127.0.0.1:{srv.server_address[1]}",
    }
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--config",
            str(cfg),
            "--zone-from",
            str(zone),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_moves_the_lanes_the_console_lacks_and_never_prints_a_value(tmp_path):
    FakeRouter.posted.clear()
    srv = _serve()
    try:
        out = _run(tmp_path, srv)
    finally:
        srv.shutdown()
    text = out.stdout + out.stderr
    assert out.returncode == 1, text  # the mystery lane has no key in the vault
    assert "kept    router-rows   claude:" in out.stdout
    assert "ok      router-rows   deepseek:" in out.stdout
    assert (
        "FAIL    router-rows   mystery: litellm-upstream holds no MYSTERY_API_KEY"
        in out.stdout
    )
    assert "1 added, 1 already console-owned, 1 failed of 3 lanes" in out.stdout
    for value in VAULT.values():
        assert value not in text, "a key value reached stdout"
    assert [b["model_name"] for b in FakeRouter.posted] == ["deepseek"]
    posted = FakeRouter.posted[0]
    assert posted["litellm_params"]["api_key"] == VAULT["DEEPSEEK_API_KEY"]
    assert posted["litellm_params"]["model"] == "deepseek/deepseek-chat"
    assert all(a == f"Bearer {VAULT['LITELLM_MASTER_KEY']}" for a in FakeRouter.auth)


def test_dry_run_posts_nothing(tmp_path):
    FakeRouter.posted.clear()
    srv = _serve()
    try:
        out = _run(tmp_path, srv, extra=["--dry-run"])
    finally:
        srv.shutdown()
    assert (
        "plan    router-rows   deepseek: would add deepseek/deepseek-chat" in out.stdout
    )
    assert FakeRouter.posted == []


def test_a_vault_without_the_master_key_is_a_fail_not_a_post(tmp_path):
    FakeRouter.posted.clear()
    srv = _serve()
    try:
        out = _run(tmp_path, srv, vault={"DEEPSEEK_API_KEY": "x"})
    finally:
        srv.shutdown()
    assert out.returncode == 1
    assert "litellm-upstream holds no LITELLM_MASTER_KEY" in out.stdout
    assert FakeRouter.posted == []


def test_the_model_info_keeps_what_the_git_row_declares(tmp_path):
    """model_info (token ceilings the crew#506 test pins) rides along into the console row."""
    FakeRouter.posted.clear()
    srv = _serve()
    try:
        _run(tmp_path, srv, vault={**VAULT, "MYSTERY_API_KEY": "sk-m"})
    finally:
        srv.shutdown()
    by_name = {b["model_name"]: b for b in FakeRouter.posted}
    assert by_name["mystery"]["model_info"] == {}
    assert "claude" not in by_name  # kept, never re-posted
