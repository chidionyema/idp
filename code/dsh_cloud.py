# ruff: noqa: S603,S607
"""Always-on DSH Web surface on Modal.

The Node harness binds loopback inside the container. A small proxy owns Modal's
public port and preserves the DSH authentication and WebSocket contract. Both
the DSH home and workspace live on Modal Volumes, so sessions survive a
container replacement.
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import threading
import time

import modal


DSH_VERSION = "0.2.1-rc.5"
DSH_HOME = "/root/.dsh"
DSH_PORT = 3080
PUBLIC_PORT = 8080

PROFILE_PACKAGE = {
    "name": "dsh-profile-web",
    "private": True,
    "dependencies": {},
    "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}},
}

PROFILE_PATCH = """\
- id: sandbox-policy
  name: "@deepseek-ai/dsh-sandbox-policy"
  config:
    mode: workspace-write
    workspaceRoot: /workspace
- id: approval
  name: "@deepseek-ai/dsh-user-approval"
  config:
    policy: never
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config:
    providers:
      estate:
        displayName: Estate Router
        apiKeyEnv: LITELLM_API_KEY
        api: openai-completions
        baseURL: https://llm.mumchimp.com/v1
        defaultContextWindow: 200000
        defaultMaxTokens: 32768
        models:
          - id: glm
            name: GLM 5.3
            contextWindow: 200000
            maxTokens: 32768
            reasoningEfforts:
              off:
              low: low
              medium: medium
              high: high
      zai:
        displayName: Z.AI
        apiKeyEnv: ZAI_API_KEY
        api: openai-completions
        baseURL: https://api.z.ai/api/coding/paas/v4
        defaultContextWindow: 200000
        defaultMaxTokens: 32768
        models:
          - id: glm-5.3
            name: GLM 5.3
            contextWindow: 200000
            maxTokens: 32768
            reasoningEfforts:
              off:
              low: low
              medium: medium
              high: high
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: !!js "process.env.ZAI_API_KEY ? 'zai' : 'deepseek-official'"
    model: !!js "process.env.ZAI_API_KEY ? 'glm-5.3' : 'deepseek-flash'"
    reasoningEffort: low
"""

GATEWAY = r"""
import http from "node:http";
import net from "node:net";

const targetHost = "127.0.0.1";
const targetPort = 3080;

function upstreamHeaders(req) {
  const headers = { ...req.headers, host: `${targetHost}:${targetPort}` };
  if (headers.origin !== undefined) headers.origin = `http://${targetHost}:${targetPort}`;
  return headers;
}

const server = http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, {"content-type": "application/json"});
    res.end(JSON.stringify({ok: true, service: "estate-dsh-web", upstream: "dsh"}));
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
        "const replacement='const created = process.env.DSH_LAUNCH_TOKEN || "
        "encodeBase64Url(randomBytes(SECRET_BYTES));';"
        "if(!s.includes(old)) throw new Error('DSH launch-token patch site missing');"
        "fs.writeFileSync(p,s.replace(old,replacement));\"",
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


def prepare_profile() -> None:
    root = pathlib.Path(DSH_HOME, "profiles", "web")
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(json.dumps(PROFILE_PACKAGE, indent=2) + "\n")
    (root / "cordis.yml").write_text(
        "# composed from package.json bundles and cordis.patch.yml\n[]\n"
    )
    (root / "cordis.patch.yml").write_text(PROFILE_PATCH)
    pathlib.Path("/root/dsh-cloud/gateway.mjs").write_text(GATEWAY)


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
        except Exception:
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
    if not (os.environ.get("ZAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")):
        raise RuntimeError("estate-dsh-runtime is missing both ZAI_API_KEY and DEEPSEEK_API_KEY")
    if not os.environ.get("DSH_LAUNCH_TOKEN"):
        raise RuntimeError("estate-dsh-runtime is missing DSH_LAUNCH_TOKEN")

    prepare_profile()
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
    try:
        port_ready(DSH_PORT)
        gateway = subprocess.Popen(
            ["node", "/root/dsh-cloud/gateway.mjs"],
            cwd="/root/dsh-cloud",
            env=env,
        )
        threading.Thread(target=commit_loop, daemon=True).start()
        returncode = gateway.wait()
        if returncode:
            raise RuntimeError(f"DSH gateway exited {returncode}")
    finally:
        dsh.terminate()
        try:
            dsh.wait(timeout=15)
        except subprocess.TimeoutExpired:
            dsh.kill()
        state.commit()
        workspace.commit()
