import os, json, subprocess, shutil, re
from pathlib import Path

from factory.net import open_https, https_request


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
        "spiffe": _spiffe_svid,
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
    req = https_request(url, headers={"X-Vault-Token": token})
    with open_https(req, timeout=10) as r:
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
    sops = shutil.which("sops")
    if not sops:
        raise SecretUnavailable("sops CLI not installed")
    r = subprocess.run(
        [sops, "-d", "--output-type", "yaml", str(p)],
        capture_output=True,
        text=True,
        timeout=30,
    )
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
    op = shutil.which("op")
    if not op:
        raise SecretUnavailable("1Password CLI (op) not installed")
    r = subprocess.run(
        [op, "read", f"op://{path}"], capture_output=True, text=True, timeout=15
    )
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
    req = https_request(
        broker.rstrip("/") + "/vend",
        method="POST",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with open_https(req, timeout=10) as r:
        data = json.loads(r.read())
    if "token" not in data:
        raise SecretError(f"jit-broker response missing token: {data}")
    return data["token"]


def _spiffe_svid(ref: str, path: str, tenant: str) -> str:
    """spiffe://<grant-id> — vend a JWT-SVID via bin/idp-jit, never an env token.

    SPIFFE-primary (docs/reference/security-architecture.md): the credential IS the
    SVID minted by the SPIRE agent from the per-device key, refreshed by
    bin/idp-jit-device-renew every 10 minutes. No env fallback by design.
    """
    idp_bin = Path(__file__).resolve().parent.parent / "bin" / "idp-jit"
    if not idp_bin.exists():
        raise SecretUnavailable("bin/idp-jit not present")
    st = subprocess.run(
        [str(idp_bin), "status"], capture_output=True, text=True, timeout=15
    )
    try:
        status = json.loads(st.stdout or "{}")
    except json.JSONDecodeError as err:
        raise SecretUnavailable(f"idp-jit status not JSON: {err}") from err
    if status.get("state") != "provisioned" or not status.get("has_key"):
        raise SecretUnavailable(
            "device not provisioned (bin/idp-jit status: "
            f"{status.get('state', 'unknown')}) — run 'bin/idp-jit enroll' once per Mac, "
            "or tap the Backstage device-access tile; no env fallback by design"
        )
    if path and path.strip():
        grant = path.split(":", 1)[0]
        r = subprocess.run(
            [str(idp_bin), "ask", "--grant", grant],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode != 0:
            raise SecretError(
                f"idp-jit ask {grant} refused: {(r.stderr or '').strip()[:200]}"
            )
        token = (
            (r.stdout or "").strip().splitlines()[-1].strip()
            if (r.stdout or "").strip()
            else ""
        )
        if not token:
            raise SecretError(f"idp-jit ask {grant} returned no token")
        return token
    r = subprocess.run(
        [str(idp_bin), "renew"], capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        raise SecretError(f"idp-jit renew failed: {(r.stderr or '').strip()[:200]}")
    token = (
        (r.stdout or "").strip().splitlines()[-1].strip()
        if (r.stdout or "").strip()
        else ""
    )
    if not token:
        raise SecretError("idp-jit renew returned no token")
    return token


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
