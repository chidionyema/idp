# ruff: noqa: S603,S607
"""Always-on DSH Web surface on Modal.

The Node harness binds loopback inside the container. A small proxy owns Modal's
public port and preserves the DSH authentication and WebSocket contract. Both
the DSH home and workspace live on Modal Volumes, so sessions survive a
container replacement.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import pathlib
import re
import socket
import subprocess
import threading
import time
import urllib.request

import modal


DSH_VERSION = "0.2.1-rc.5"
CONTRACT_ID = "estate.dsh-web"
SCHEMA_VERSION = "1.0.0"
RELEASE_ID = "dsh-web-2026.11.08.2"
RELEASE_VERSION = "0.2.1-rc.5+estate.2"
RELEASE_AUTHORITY = "work-surface"
DSH_HOME = "/root/.dsh"
DSH_PORT = 3080
PUBLIC_PORT = 8080

PROFILE_PACKAGE = {
    "name": "dsh-profile-web",
    "private": True,
    "dependencies": {},
    "dsh": {
        "profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}
    },
}

ROUTER_BASE_URL = os.environ.get(
    "ESTATE_ROUTER_URL", "https://llm.mumchimp.com/v1"
).rstrip("/")
MODEL_CATALOG_URL = os.environ.get(
    "ESTATE_MODEL_CATALOG_URL", ROUTER_BASE_URL + "/models"
)

GATEWAY = r"""
import http from "node:http";
import net from "node:net";

const targetHost = "127.0.0.1";
const targetPort = 3080;
const health = __ESTATE_HEALTH__;

function upstreamHeaders(req) {
  const headers = { ...req.headers, host: `${targetHost}:${targetPort}` };
  if (headers.origin !== undefined) headers.origin = `http://${targetHost}:${targetPort}`;
  return headers;
}

const server = http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, {"content-type": "application/json"});
    res.end(JSON.stringify(health));
    return;
  }
  const outbound = http.request({
    host: targetHost,
    port: targetPort,
    method: req.method,
    path: req.url,
    headers: upstreamHeaders(req),
  }, (upstream) => {
    res.writeHead(upstream.statusCode || 502, upstream.headers);
    upstream.pipe(res);
  });
  outbound.on("error", (error) => {
    res.writeHead(502, {"content-type": "text/plain; charset=utf-8"});
    res.end(`DSH upstream unavailable: ${error.message}`);
  });
  req.pipe(outbound);
});

server.on("upgrade", (req, socket, head) => {
  const upstream = net.connect(targetPort, targetHost, () => {
    const headers = upstreamHeaders(req);
    const lines = [`${req.method} ${req.url} HTTP/1.1`];
    for (const [name, value] of Object.entries(headers)) {
      if (Array.isArray(value)) {
        for (const item of value) lines.push(`${name}: ${item}`);
      } else if (value !== undefined) {
        lines.push(`${name}: ${value}`);
      }
    }
    upstream.write(lines.join("\r\n") + "\r\n\r\n");
    if (head.length) upstream.write(head);
    socket.pipe(upstream).pipe(socket);
  });
  upstream.on("error", () => socket.destroy());
  socket.on("error", () => upstream.destroy());
});

server.listen(8080, "0.0.0.0");
"""

image = (
    modal.Image.from_registry("node:22-bookworm-slim", add_python="3.12")
    .apt_install("bash", "ca-certificates", "curl", "git", "procps", "ripgrep")
    .run_commands(
        f"npm install --global @deepseek-ai/dsh@{DSH_VERSION}",
        # DSH normally mints a process-random launch token. A cloud work surface
        # needs one stable bootstrap token so a cookie obtained once survives
        # container replacements. The token still comes from a Modal Secret.
        "node -e \"const fs=require('node:fs');"
        "const p='/usr/local/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/"
        "dsh-client-connection/lib/index.js';"
        "const s=fs.readFileSync(p,'utf8');"
        "const old='const created = encodeBase64Url(randomBytes(SECRET_BYTES));';"
        "const replacement='const launchToken = process.env.DSH_LAUNCH_TOKEN;\\n"
        "\\tdelete process.env.DSH_LAUNCH_TOKEN;\\n"
        "\\tconst created = launchToken || encodeBase64Url(randomBytes(SECRET_BYTES));';"
        "if(!s.includes(old)) throw new Error('DSH launch-token patch site missing');"
        'fs.writeFileSync(p,s.replace(old,replacement));"',
    )
    .add_local_dir(
        os.path.dirname(os.path.abspath(__file__)),
        remote_path="/root/dsh-cloud",
        ignore=["__pycache__", "*.pyc"],
    )
)

state = modal.Volume.from_name("estate-dsh-state", create_if_missing=True)
workspace = modal.Volume.from_name("estate-dsh-workspace", create_if_missing=True)
runtime = modal.Secret.from_name("estate-dsh-runtime")
app = modal.App("estate-dsh-web")


def router_catalog() -> tuple[list[dict], str]:
    last = None
    for _ in range(6):
        try:
            request = urllib.request.Request(  # noqa: S310 - production HTTPS router
                MODEL_CATALOG_URL,
                headers={"User-Agent": "estate-dsh-cloud/1.0"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                payload = json.load(response)
            models: list[dict] = []
            for row in payload.get("data", []):
                model_id = str(row.get("id", "")).strip()
                if not model_id:
                    continue
                model = {"id": model_id, "name": model_id}
                context_window = row.get("max_input_tokens")
                if isinstance(context_window, int) and context_window > 0:
                    model["contextWindow"] = context_window
                max_tokens = row.get("max_output_tokens")
                if isinstance(max_tokens, int) and max_tokens > 0:
                    model["maxTokens"] = max_tokens
                models.append(model)
            models.sort(key=lambda item: item["id"])
            if not models:
                raise RuntimeError(f"router catalogue {MODEL_CATALOG_URL} is empty")
            configured = os.environ.get("DSH_DEFAULT_MODEL", "").strip()
            ids = {model["id"] for model in models}
            if configured and configured not in ids:
                raise RuntimeError(
                    f"DSH_DEFAULT_MODEL={configured!r} is not served by {MODEL_CATALOG_URL}"
                )
            default_model = configured or (
                "default" if "default" in ids else models[0]["id"]
            )
            return models, default_model
        except Exception as exc:
            last = exc
            time.sleep(5)
    raise RuntimeError(f"router catalogue unavailable after 6 probes: {last}")


def profile_patch(models: list[dict], default_model: str) -> list[dict]:
    return [
        {
            "id": "sandbox-policy",
            "name": "@deepseek-ai/dsh-sandbox-policy",
            "config": {"mode": "danger-full-access", "workspaceRoot": "/workspace"},
        },
        {
            "id": "approval",
            "name": "@deepseek-ai/dsh-user-approval",
            "config": {"policy": "never"},
        },
        {
            "id": "permission",
            "name": "@deepseek-ai/dsh-permission-presets",
            "config": {
                "presets": {
                    "danger-full-access": {
                        "sandbox": "danger-full-access",
                        "approval": "never",
                    }
                },
                "defaultPreset": "danger-full-access",
            },
        },
        {
            "id": "llm-pi-ai",
            "name": "@deepseek-ai/dsh-llm-pi-ai",
            "config": {
                "providers": {
                    "estate": {
                        "displayName": "Estate Router",
                        "apiKeyEnv": "LITELLM_API_KEY",
                        "api": "openai-completions",
                        "baseURL": ROUTER_BASE_URL,
                        "defaultContextWindow": 262144,
                        "defaultMaxTokens": 32768,
                        "models": models,
                    }
                }
            },
        },
        {
            "id": "agent-default-model",
            "name": "@deepseek-ai/dsh-agent-default-model",
            "config": {
                "provider": "estate",
                "model": default_model,
                "reasoningEffort": "low",
            },
        },
    ]


def runtime_health(models: list[dict], default_model: str) -> dict:
    source_sha = os.environ.get("DSH_SOURCE_SHA", "")
    deployed_at = os.environ.get("DSH_DEPLOYED_AT", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise RuntimeError("estate-dsh-runtime is missing a valid DSH_SOURCE_SHA")
    if not deployed_at:
        raise RuntimeError("estate-dsh-runtime is missing DSH_DEPLOYED_AT")
    effective_profile = profile_patch(models, default_model)
    config_bytes = (
        DSH_VERSION
        + "\n"
        + json.dumps(PROFILE_PACKAGE, sort_keys=True, separators=(",", ":"))
        + "\n"
        + json.dumps(effective_profile, sort_keys=True, separators=(",", ":"))
    ).encode()
    return {
        "ok": True,
        "service": "estate-dsh-web",
        "surface": "cloud",
        "upstream": "dsh",
        "contractId": CONTRACT_ID,
        "schemaVersion": SCHEMA_VERSION,
        "release": {
            "id": RELEASE_ID,
            "version": RELEASE_VERSION,
            "sourceSha": source_sha,
            "configDigest": "sha256:" + hashlib.sha256(config_bytes).hexdigest(),
            "deployedAt": deployed_at,
            "authority": RELEASE_AUTHORITY,
            "router": "estate.model-router",
            "modelRoute": "estate-router",
            "catalogSource": MODEL_CATALOG_URL,
            "modelCount": len(models),
            "defaultModel": default_model,
        },
    }


def prepare_profile(health: dict, models: list[dict], default_model: str) -> None:
    root = pathlib.Path(DSH_HOME, "profiles", "web")
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(json.dumps(PROFILE_PACKAGE, indent=2) + "\n")
    (root / "cordis.yml").write_text(
        "# composed from package.json bundles and cordis.patch.yml\n[]\n"
    )
    (root / "cordis.patch.yml").write_text(
        json.dumps(profile_patch(models, default_model), indent=2) + "\n"
    )
    pathlib.Path("/root/dsh-cloud/gateway.mjs").write_text(
        GATEWAY.replace(
            "__ESTATE_HEALTH__",
            json.dumps(health, separators=(",", ":")),
        )
    )


def port_ready(port: int, timeout_s: int = 180) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(1)
    raise RuntimeError(f"DSH did not bind 127.0.0.1:{port} within {timeout_s}s")


def commit_loop() -> None:
    while True:
        time.sleep(30)
        try:
            state.commit()
            workspace.commit()
        except Exception:  # noqa: S110 - volume commit is retried on the next cycle
            # A transient Volume commit failure must not kill the live surface.
            pass


@app.function(
    image=image,
    secrets=[runtime],
    volumes={DSH_HOME: state, "/workspace": workspace},
    cpu=1.0,
    memory=1024,
    min_containers=1,
    max_containers=1,
)
@modal.web_server(port=PUBLIC_PORT, startup_timeout=300)
def web() -> None:
    if not os.environ.get("LITELLM_API_KEY"):
        raise RuntimeError("estate-dsh-runtime is missing LITELLM_API_KEY")
    if not os.environ.get("DSH_LAUNCH_TOKEN"):
        raise RuntimeError("estate-dsh-runtime is missing DSH_LAUNCH_TOKEN")

    models, default_model = router_catalog()
    health = runtime_health(models, default_model)
    prepare_profile(health, models, default_model)
    env = {
        **os.environ,
        "HOME": "/root",
        "DSH_HOME": DSH_HOME,
        "TERM": "xterm-256color",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }
    dsh = subprocess.Popen(
        [
            "dsh",
            "--profile",
            "web",
            "--no-open",
            "--host",
            "127.0.0.1",
            "--port",
            str(DSH_PORT),
        ],
        cwd="/workspace",
        env=env,
    )
    port_ready(DSH_PORT)
    gateway = subprocess.Popen(
        ["node", "/root/dsh-cloud/gateway.mjs"],
        cwd="/root/dsh-cloud",
        env=env,
    )
    port_ready(PUBLIC_PORT, timeout_s=30)
    if gateway.poll() is not None:
        raise RuntimeError(f"DSH gateway exited {gateway.returncode}")
    threading.Thread(target=commit_loop, daemon=True).start()

    # Modal's web_server entrypoint must finish initialization after the public
    # listener is ready. Both servers are child processes of this container and
    # continue serving after this function returns.
    def cleanup() -> None:
        dsh.terminate()
        try:
            dsh.wait(timeout=15)
        except subprocess.TimeoutExpired:
            dsh.kill()
        if gateway.poll() is None:
            gateway.terminate()
        state.commit()
        workspace.commit()

    atexit.register(cleanup)
