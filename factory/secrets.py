import os, json, subprocess, urllib.request, urllib.parse, base64, re
from pathlib import Path


class SecretError(Exception):
    pass


class SecretUnavailable(SecretError):
    pass


_CACHE: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300  # 5 minutes


def vend(ref: str, tenant: str = "factory") -> str:
    """Resolve a secret reference. Every backend must produce a real value or raise."""
    if not isinstance(ref, str):
        raise SecretError(f"secret ref must be a string, got {type(ref).__name__}")
    if not ref:
        raise SecretError("empty secret ref")
    import time

    if ref in _CACHE:
        val, exp = _CACHE[ref]
        if time.time() < exp:
            return val
    val = _resolve(ref, tenant)
    _CACHE[ref] = (val, time.time() + CACHE_TTL)
    return val


def _resolve(ref: str, tenant: str) -> str:
    scheme, _, path = ref.partition("://")
    if not scheme:
        raise SecretError(f"ref must include scheme://: {ref}")
    fn = {
        "vault": _hashicorp_vault,
        "sops": _sops_file,
        "op": _onepassword,
        "env": _env,
        "file": _file,
        "jit": _jit_broker,
    }.get(scheme)
    if fn is None:
        raise SecretError(f"unsupported secret scheme: {scheme}")
    if scheme == "env" and os.environ.get("ALLOW_ENV_SECRETS") != "1":
        raise SecretUnavailable("env scheme disabled; set ALLOW_ENV_SECRETS=1 to allow")
    return fn(ref, path, tenant)


def _hashicorp_vault(ref: str, path: str, tenant: str) -> str:
    addr = os.environ.get("VAULT_ADDR")
    token = os.environ.get("VAULT_TOKEN")
    if not (addr and token):
        raise SecretUnavailable("VAULT_ADDR / VAULT_TOKEN not set")
    key = None
    if "#" in path:
        path, key = path.split("#", 1)
    url = addr.rstrip("/") + "/v1/" + path.lstrip("/")
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    node = data.get("data", {})
    if "data" in node:
        node = node["data"]
    if key:
        if key not in node:
            raise SecretError(f"key {key} not in {path}")
        return str(node[key])
    return json.dumps(node)


def _sops_file(ref: str, path: str, tenant: str) -> str:
    key = None
    if "#" in path:
        path, key = path.split("#", 1)
    p = Path(path).expanduser()
    if not p.exists():
        raise SecretUnavailable(f"sops file not found: {p}")
    try:
        r = subprocess.run(
            ["sops", "-d", "--output-type", "yaml", str(p)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise SecretUnavailable("sops CLI not installed")
    if r.returncode != 0:
        raise SecretError(f"sops failed: {r.stderr.strip()[:200]}")
    import yaml

    data = yaml.safe_load(r.stdout)
    if not key:
        return json.dumps(data)
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise SecretError(f"key path {key} not in {p}")
        node = node[part]
    return str(node)


def _onepassword(ref: str, path: str, tenant: str) -> str:
    try:
        r = subprocess.run(
            ["op", "read", f"op://{path}"], capture_output=True, text=True, timeout=15
        )
    except FileNotFoundError:
        raise SecretUnavailable("1Password CLI (op) not installed")
    if r.returncode != 0:
        raise SecretError(f"op read failed: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def _env(ref: str, path: str, tenant: str) -> str:
    if path not in os.environ:
        raise SecretUnavailable(f"env var not set: {path}")
    return os.environ[path]


def _file(ref: str, path: str, tenant: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise SecretUnavailable(f"file not found: {p}")
    mode = p.stat().st_mode & 0o777
    if mode & 0o077:
        import sys

        print(
            f"WARNING: secret file {p} has loose perms ({oct(mode)})", file=sys.stderr
        )
    return p.read_text().strip()


def _jit_broker(ref: str, path: str, tenant: str) -> str:
    broker = os.environ.get("JIT_BROKER_URL")
    if not broker:
        raise SecretUnavailable("JIT_BROKER_URL not set")
    body = json.dumps({"ref": ref, "tenant": tenant}).encode()
    req = urllib.request.Request(
        broker.rstrip("/") + "/vend",
        method="POST",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    if "token" not in data:
        raise SecretError(f"jit-broker response missing token: {data}")
    return data["token"]


SECRET_PATTERNS = [
    re.compile(rb"Bearer\s+[A-Za-z0-9\-_\.=]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"ghp_[A-Za-z0-9]{36,}"),
    re.compile(rb"xoxb-[A-Za-z0-9-]{20,}"),
    re.compile(rb"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
]


def refuse_literal_secrets(raw: bytes, source: str) -> None:
    for pat in SECRET_PATTERNS:
        m = pat.search(raw)
        if m:
            raise SecretError(f"literal secret detected in {source}: {pat.pattern!r}")
