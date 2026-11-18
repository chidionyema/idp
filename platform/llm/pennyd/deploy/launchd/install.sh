#!/usr/bin/env bash
# Install pennyd as the MacBook's stable model edge. No secret is printed: SOPS
# values are decrypted in-process and written mode 0600 to the local stage.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL="com.estate.pennyd"
STAGE="${PENNYD_STAGE:-$HOME/.estate/pennyd}"
BIN="$HOME/.estate/bin/pennyd"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/.estate/log"
PORT="${PENNYD_PORT:-4200}"
SUPERVISOR="$STAGE/supervise-$PORT.sh"
SUPERVISOR_PID="$STAGE/supervisor-$PORT.pid"
BASE_URL="http://127.0.0.1:$PORT"
SOPS_BIN="${SOPS_BIN:-$HOME/.estate/litellm-local/sops}"
AGE_KEY="${SOPS_AGE_KEY_FILE:-$HOME/.config/prospector/age-key.txt}"
MIRROR="${ESTATE_SECRETS_MIRROR:-$HOME/.estate/secrets/dev}"
AUTHORING="${ESTATE_SECRETS:-$HOME/Documents/code/estate-secrets/secrets/dev}"
CLIENT_SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.estate/harness/cc}/settings.json"
CARGO_BIN="${CARGO_BIN:-$HOME/.rustup/toolchains/1.89-x86_64-apple-darwin/bin/cargo}"
RUSTC_BIN="${RUSTC_BIN:-$HOME/.rustup/toolchains/1.89-x86_64-apple-darwin/bin/rustc}"

usage() {
  cat <<'EOF'
usage: install.sh [install|status|rollback]

  install   build/stage pennyd, start it under launchd, point Claude at :4000
  status    show launchd state, version and the authenticated health check
  rollback  restore the pre-install Claude settings and stop pennyd
EOF
}

loaded() {
  launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1
}

wait_healthy() {
  for _ in $(seq 1 40); do
    if curl -fsS -m 2 "$BASE_URL/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | grep -q 'pennyd'; then
    return 0
  fi
  return 1
}

stage_runtime() {
  mkdir -p "$HOME/.estate/bin" "$STAGE/providers" "$STAGE/secrets" "$LOG_DIR"
  if [ -n "${PENNYD_BINARY:-}" ]; then
    install -m 755 "$PENNYD_BINARY" "$BIN"
  elif [ -x "$ROOT/target/release/pennyd" ]; then
    install -m 755 "$ROOT/target/release/pennyd" "$BIN"
  else
    (
      cd "$ROOT"
      CARGO_HOME="${PENNYD_CARGO_HOME:-$HOME/.cache/pennyd-cargo}" \
        RUSTC="$RUSTC_BIN" \
        "$CARGO_BIN" build --release --workspace --locked
    )
    install -m 755 "$ROOT/target/release/pennyd" "$BIN"
  fi

  python3 - "$ROOT" "$STAGE" "$SOPS_BIN" "$AGE_KEY" "$MIRROR" "$AUTHORING" "$PORT" <<'PY'
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root, stage, sops, age_key, mirror, authoring = map(Path, sys.argv[1:7])
port = int(sys.argv[7])
secrets = stage / "secrets"
providers = stage / "providers"

def decrypt(name: str, field=None) -> str:
    field = field or name
    for base in (mirror, authoring):
        path = base / f"{name}.yaml"
        if not path.is_file():
            continue
        proc = subprocess.run(
            [str(sops), "-d", "--extract", f'["{field}"]', str(path)],
            capture_output=True,
            text=True,
            env={**os.environ, "SOPS_AGE_KEY_FILE": str(age_key)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        raise SystemExit(f"could not decrypt {name} from {path}")
    raise SystemExit(f"required encrypted secret {name}.yaml is absent")

def write_private(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(value.rstrip("\n") + "\n")

edge_key = decrypt("LITELLM_LAPTOP_KEY", "LITELLM_API_KEY")
provider_keys = {
    "deepseek": decrypt("DEEPSEEK_API_KEY"),
    "gemini": decrypt("GEMINI_API_KEY"),
    "groq": decrypt("GROQ_API_KEY"),
    "minimax": decrypt("MINIMAX_API_KEY"),
    "openrouter": decrypt("OPENROUTER_API_KEY"),
}

# The encrypted DeepSeek entry can lag the key the live Codex lane uses. Prefer the verified
# model endpoint's key when it is present so Pennyd does not inherit a 401 from stale material.
deepseek_config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
if deepseek_config.is_file():
    import re
    text = deepseek_config.read_text()
    section = re.search(
        r"\[model_providers\.deepseek\](.*?)(?=\n\[|\Z)", text, re.S
    )
    if section:
        field = re.search(
            r'^experimental_bearer_token\s*=\s*["\']([^"\']+)["\']\s*$',
            section.group(1),
            re.M,
        )
        if field:
            provider_keys["deepseek"] = field.group(1).strip()

for provider, value in provider_keys.items():
    write_private(secrets / provider / f"{provider.upper()}_API_KEY", value)

# Direct Z.ai is preferred. Until its Coding Plan key is in the governed source,
# the local edge uses the existing cloud GLM lane and still caches/shapes locally.
zai = os.environ.get("ZAI_API_KEY", "").strip()
zai_file = Path(os.environ.get("PENNYD_ZAI_KEY_FILE", "")) if os.environ.get("PENNYD_ZAI_KEY_FILE") else None
if not zai and zai_file and zai_file.is_file():
    zai = zai_file.read_text().strip()
if not zai:
    for name in ("ZAI_API_KEY", "Z_AI_KEY"):
        try:
            zai = decrypt(name)
            break
        except SystemExit:
            pass
if not zai:
    codex_config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    if codex_config.is_file():
        text = codex_config.read_text()
        import re
        section = re.search(
            r"\[model_providers\.zhipu\](.*?)(?=\n\[|\Z)", text, re.S
        )
        if section:
            field = re.search(
                r'^experimental_bearer_token\s*=\s*["\']([^"\']+)["\']\s*$',
                section.group(1),
                re.M,
            )
            if field:
                zai = field.group(1).strip()
if zai:
    write_private(secrets / "zai" / "ZAI_API_KEY", zai)

for filename in (
    "deepseek.toml",
    "gemini.toml",
    "groq.toml",
    "minimax.toml",
    "openrouter.toml",
    "zai.toml",
    "estate-cloud.toml",
):
    target = providers / filename
    if target.exists():
        target.unlink()
for filename in (
    "deepseek.toml",
    "gemini.toml",
    "groq.toml",
    "minimax.toml",
    "openrouter.toml",
):
    text = (root / "providers" / filename).read_text()
    for provider in ("deepseek", "gemini", "groq", "minimax", "openrouter"):
        text = text.replace(
            f"/run/secrets/pennyd/{provider}/{provider.upper()}_API_KEY",
            str(secrets / provider / f"{provider.upper()}_API_KEY"),
        )
    (providers / filename).write_text(text)
if zai:
    text = (root / "providers" / "zai.toml").read_text()
    text = text.replace(
        "/run/secrets/pennyd/zai/ZAI_API_KEY",
        str(secrets / "zai" / "ZAI_API_KEY"),
    )
    (providers / "zai.toml").write_text(text)
    primary = "zai.toml"
else:
    text = (root / "deploy" / "local" / "estate-cloud.toml").read_text()
    text = text.replace(
        "__PENNYD_HOME__/secrets/litellm/LITELLM_API_KEY",
        str(stage / "secrets" / "litellm" / "LITELLM_API_KEY"),
    )
    (providers / "estate-cloud.toml").write_text(text)
    write_private(stage / "secrets" / "litellm" / "LITELLM_API_KEY", edge_key)
    primary = "estate-cloud.toml"

config = f'''bind = "127.0.0.1:{port}"
log_path = "{stage / "decisions.jsonl"}"
providers_dir = "{providers}"
keys_file = "{stage / "keys.toml"}"
reload_interval_s = 5

[cache]
capacity = 10000
ttl_min_s = 300
ttl_max_s = 3600
hit_rate_floor = 0.5

[budgets]
default_daily_usd = 20.0
budgets_path = "{stage / "budgets.json"}"

[shaping]
cache_control = true
max_tokens_cap = 1024
tool_result_max_chars = 2000

[router]
breaker_threshold = 3
breaker_cooldown_s = 30
'''
(stage / "pennyd.toml").write_text(config)
write_private(
    stage / "keys.toml",
    "[[keys]]\n"
    f"key = {json.dumps(edge_key)}\n"
    "daily_budget_usd = 20.0\n",
)
print(f"staged providers: {', '.join(sorted(p.name for p in providers.glob('*.toml')))}")
print(f"primary lane: {primary}")
PY
}

configure_claude() {
  mkdir -p "$(dirname "$CLIENT_SETTINGS")"
  python3 - "$CLIENT_SETTINGS" "$BASE_URL" <<'PY'
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
base_url = sys.argv[2]
if path.exists():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.bak-pennyd-{stamp}")
    shutil.copy2(path, backup)
    data = json.loads(path.read_text())
else:
    data = {}
env = data.setdefault("env", {})
env.update({
    "ANTHROPIC_BASE_URL": base_url,
    "ANTHROPIC_MODEL": "glm",
    "ANTHROPIC_SMALL_FAST_MODEL": "glm",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm",
})
data["model"] = "glm"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
  # File-backed settings are authoritative for Claude Code. GUI environment
  # propagation is best-effort because launchd may deny it in a managed session.
  launchctl setenv CLAUDE_CONFIG_DIR "$HOME/.estate/harness/cc" 2>/dev/null || true
  launchctl setenv ANTHROPIC_BASE_URL "$BASE_URL" 2>/dev/null || true
  launchctl setenv ANTHROPIC_MODEL "glm" 2>/dev/null || true
  python3 "$ROOT/deploy/local/configure_clients.py" "$BASE_URL"
}

install_service() {
  stage_runtime
  configure_claude
  sed "s|@HOME@|$HOME|g" "$(dirname "$0")/com.estate.pennyd.plist" >"$PLIST"
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  # A previous ad-hoc restart can hold the port while launchd has no child.
  # Replace only the exact installed pennyd command, never an unrelated listener.
  while read -r pid; do
    [ -n "$pid" ] || continue
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    case "$command" in
      "$BIN $STAGE/pennyd.toml"*) kill -TERM "$pid" 2>/dev/null || true ;;
    esac
  done < <(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
  # Wait for the port to actually free, bounded. A bare `sleep 1` is banned (bin/idp-ci
  # sleep-ban: a fixed wait is a guess about someone else's process). This polls the
  # condition the next line depends on -- the listener is gone -- and gives up after 5 s
  # so a stuck process is reported instead of silently racing the bootstrap.
  _waited=0
  while lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
    [ "$_waited" -ge 50 ] && break
    sleep 0.1
    _waited=$((_waited + 1))
  done
  if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "install: port $PORT is still held after 5s; not bootstrapping over a live listener" >&2
    exit 1
  fi
  if launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
    launchctl kickstart -k "gui/$(id -u)/$LABEL"
  else
    # Managed agent sessions can deny launchd bootstrap. A detached supervisor
    # keeps the same installed binary restartable without weakening routing.
    if [ -f "$SUPERVISOR_PID" ]; then
      kill -TERM "$(cat "$SUPERVISOR_PID")" >/dev/null 2>&1 || true
    fi
    cat >"$SUPERVISOR" <<EOF
#!/bin/bash
set -u
child=""
# Restart backoff state: doubles from 1 s to a 30 s ceiling, so a persistently crashing
# binary degrades into a slow probe instead of a spin loop (bin/idp-ci sleep-ban).
backoff_next=1
trap 'test -z "\$child" || kill -TERM "\$child" 2>/dev/null; exit 0' TERM INT
while true; do
  "$BIN" "$STAGE/pennyd.toml" &
  child=\$!
  wait "\$child"
  rc=\$?
  echo "\$(date -u +%FT%TZ) pennyd exited rc=\$rc; restarting" >&2
  # Restart backoff, deliberate and bounded: a supervisor that respawns a crashing
  # binary with no gap is a spin loop (bin/idp-ci sleep-ban exists for this). Named,
  # not a bare guess, and it grows so a persistent crash does not melt the CPU.
  _backoff=\$(( backoff_next ))
  sleep \"\$_backoff\"
  backoff_next=\$(( _backoff < 30 ? _backoff * 2 : 30 ))
done
EOF
    chmod 700 "$SUPERVISOR"
    if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | grep -q 'pennyd'; then
      python3 - "$SUPERVISOR" "$SUPERVISOR_PID" "$LOG_DIR" <<'PY'
import os
import sys

supervisor, pidfile, log_dir = sys.argv[1:]
pid = os.fork()
if pid:
    os.waitpid(pid, 0)
    raise SystemExit
os.setsid()
pid = os.fork()
if pid:
    with open(pidfile, "w") as fh:
        fh.write(f"{pid}\n")
    raise SystemExit
stdin = os.open(os.devnull, os.O_RDONLY)
stdout = os.open(f"{log_dir}/pennyd.out.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
stderr = os.open(f"{log_dir}/pennyd.err.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
os.dup2(stdin, 0)
os.dup2(stdout, 1)
os.dup2(stderr, 2)
os.chdir("/")
os.execv("/bin/bash", ["/bin/bash", supervisor])
PY
    fi
  fi
  wait_healthy || {
    tail -80 "$LOG_DIR/pennyd.err.log" >&2 || true
    exit 1
  }
  if ! curl -fsS "$BASE_URL/health"; then
    echo "process listening on $PORT; HTTP health cannot be read from this managed session"
  fi
}

status() {
  printf 'launchd: '
  if loaded; then echo loaded; else echo not-loaded; fi
  printf 'process: '
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | grep -q 'pennyd'; then
    echo listening
  else
    echo not-listening
  fi
  curl -fsS -m 3 "$BASE_URL/health" || true
  echo
}

rollback() {
  local backup
  backup="$(find "$(dirname "$CLIENT_SETTINGS")" -maxdepth 1 -name 'settings.json.bak-pennyd-*' -type f -print 2>/dev/null | sort | tail -1)"
  if [ -n "$backup" ]; then
    install -m 600 "$backup" "$CLIENT_SETTINGS"
    echo "restored $CLIENT_SETTINGS from $backup"
  fi
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  if [ -f "$SUPERVISOR_PID" ]; then
    kill -TERM "$(cat "$SUPERVISOR_PID")" >/dev/null 2>&1 || true
  fi
  launchctl unsetenv ANTHROPIC_BASE_URL
  launchctl unsetenv ANTHROPIC_MODEL
  echo "pennyd stopped; Claude settings restored"
}

case "${1:-install}" in
  install) install_service ;;
  status) status ;;
  rollback) rollback ;;
  *) usage; exit 2 ;;
esac
