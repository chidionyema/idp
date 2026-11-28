"""Independent settlement certifier (MERIDIAN-CTRL-001 B08, B10, section 11).

The worker and the engine cannot certify their own effects. This module is the other half of
the control wired in `activities.rust_gate_verify_settlement` and `verify_instruction_yield`:
it runs OUTSIDE the worker, observes the declared production effect itself, and signs

  1. the MERIDIAN-SETTLEMENT-V1 receipt that the compiled `meridian-gate` verifies, and
  2. the `meridian/instruction-yield-v1` yield receipt that the worker verifies,

then signals `submit_independent_yield` on the instruction's workflow. It adds no verdict
logic of its own: the compiled gate and the activity remain the deciders. It refuses to sign
when its own observation does not match the acceptance predicate, so a missing or failing
effect produces no receipt and the workflow's bounded wait fails closed.

Key custody: the Ed25519 seed is read from an environment variable NAMED by the caller and is
never printed, logged or placed in a receipt. The matching public keys are what the worker
host pins (`ESTATE_YIELD_VERIFIER_PUBKEY_HEX`, `ESTATE_SETTLEMENT_CERTIFIERS_HEX`).
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

# Same grammar as the claim guard's SHIP-CONTRACT accept line (bin/claim-gate ACCEPT).
ACCEPT = re.compile(
    r"^GET (?P<url>https://[\w.-]+(?::\d+)?/\S*) expect (?P<code>[1-5]\d\d)"
    r"(?: contains \"(?P<needle>[^\"]+)\")? within (?P<mins>\d{1,4})m$"
)
# GitHub serves source, never production; the compiled gate refuses these too.
_SOURCE_HOSTS = frozenset(
    {
        "github.com",
        "www.github.com",
        "raw.githubusercontent.com",
        "gist.githubusercontent.com",
        "api.github.com",
        "objects.githubusercontent.com",
    }
)
_SETTLEMENT_ORDER = (
    "instruction_id",
    "attempt_id",
    "execution_epoch",
    "objective_hash",
    "acceptance_predicate_hash",
    "target_identity",
    "artifact_digest",
    "observed_at_utc",
    "evidence_expires_utc",
    "observation_url",
    "policy_hash",
)
EVIDENCE_TTL_S = 3600
OBSERVE_TIMEOUT_S = 15
MAX_BODY = 1 << 20


class CertifierRefusal(Exception):
    """The certifier will not sign. The message names the reason and carries no secret."""


@dataclass(frozen=True)
class Accept:
    url: str
    status: int
    needle: str | None

    @property
    def predicate_hash(self) -> str:
        # Bound into the signature, so a receipt for one predicate cannot settle another.
        text = f"GET {self.url} expect {self.status} contains {self.needle or ''}"
        return hashlib.sha256(text.encode()).hexdigest()


def parse_accept(line: str) -> Accept:
    m = ACCEPT.match(line.strip())
    if not m:
        raise CertifierRefusal("accept line is not a declarative HTTPS GET")
    return Accept(m.group("url"), int(m.group("code")), m.group("needle"))


def refuse_proxy_target(url: str) -> str:
    """Return the target host, or raise for anything that is not a production origin."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        raise CertifierRefusal("target is not an https origin")
    if host in _SOURCE_HOSTS or host.endswith(".github.io"):
        raise CertifierRefusal("target is GitHub source, not production")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise CertifierRefusal("target is loopback, not production")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified:
        raise CertifierRefusal("target is a non-public address")
    return host


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None  # a redirect could move the observation off the declared origin


def _require_https(url: str) -> str:
    """Refuse any scheme but https before a URL is opened (file:, ftp:, custom schemes)."""
    if urllib.parse.urlsplit(url).scheme != "https":
        raise CertifierRefusal("only https URLs are opened")
    return url


def fetch(url: str) -> tuple[int, bytes]:
    """The certifier's own observation: one GET, no redirects, bounded body."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(  # noqa: S310 -- https enforced by _require_https
        _require_https(url), headers={"User-Agent": "estate-certifier"}
    )
    try:
        with opener.open(req, timeout=OBSERVE_TIMEOUT_S) as resp:
            return resp.status, resp.read(MAX_BODY)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(MAX_BODY)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CertifierRefusal(f"observation failed: {type(exc).__name__}") from exc


def observe(accept: Accept, getter: Callable[[str], tuple[int, bytes]] = fetch) -> str:
    """Return the artifact digest, or raise when the effect is not observed."""
    refuse_proxy_target(accept.url)
    status, body = getter(accept.url)
    if status != accept.status:
        raise CertifierRefusal(
            f"observed status {status}, predicate wants {accept.status}"
        )
    if accept.needle and accept.needle.encode() not in body:
        raise CertifierRefusal(
            "observed body does not contain the predicate's invariant"
        )
    return hashlib.sha256(body).hexdigest()


def expected_from_state(state: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Rebuild the workflow's own `expected` (workflow.py `_request_verification`)."""
    task = state.get("task")
    if not isinstance(task, str) or not task or not state.get("instruction_id"):
        raise CertifierRefusal("workflow state has no instruction to certify")
    return {
        "instruction_id": state["instruction_id"],
        "run_id": run_id,
        "epoch": state.get("step"),
        "goal_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "commit_sha": state.get("commit"),
    }


SEED_FILE = "certifier.seed"


def mint_or_load_seed(key_dir: str) -> str:
    """The certifier's own key: minted here on first use, never shown, never leaves `key_dir`.

    Nobody generates, pastes or sees the seed. The file is created exclusively with mode 0600, so
    two sweeps that start together cannot end up holding different keys. Only the public half is
    ever published (`public_key_hex`).
    """
    path = os.path.join(key_dir, SEED_FILE)
    os.makedirs(key_dir, mode=0o700, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        with open(path, encoding="ascii") as fh:
            return fh.read().strip()
    seed = os.urandom(32).hex()
    with os.fdopen(fd, "w", encoding="ascii") as fh:
        fh.write(seed)
    return seed


def public_key_hex(key_dir: str) -> str:
    """The public half, safe to publish and to pin in the worker's trust configuration."""
    return _signer("", key_dir).public_key().public_bytes_raw().hex()


def _signer(seed_env: str, key_dir: str | None = None):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if key_dir:
        seed = mint_or_load_seed(key_dir)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", seed):
            raise CertifierRefusal(
                "certifier key file does not hold a 32-byte hex seed"
            )
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
    seed = os.environ.get(seed_env, "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", seed):
        raise CertifierRefusal(f"{seed_env} does not hold a 32-byte hex Ed25519 seed")
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))


def build_envelope(
    expected: dict[str, Any],
    accept: Accept,
    *,
    seed_env: str,
    policy_hash: str,
    getter: Callable[[str], tuple[int, bytes]] = fetch,
    now: int | None = None,
    key_dir: str | None = None,
) -> dict[str, Any]:
    """Observe, then sign. Raises CertifierRefusal and signs nothing when the effect is absent."""
    if not re.fullmatch(r"[0-9a-f]{64}", policy_hash):
        raise CertifierRefusal("policy hash must be a sha256 hex digest")
    if type(expected.get("epoch")) is not int:
        raise CertifierRefusal("workflow has no integer execution epoch")
    signer = _signer(seed_env, key_dir)
    host = refuse_proxy_target(accept.url)
    artifact = observe(accept, getter)
    observed = int(time.time()) if now is None else now
    fields: dict[str, Any] = {
        "instruction_id": expected["instruction_id"],
        "attempt_id": expected["run_id"],
        "execution_epoch": expected["epoch"],
        "objective_hash": expected["goal_sha256"],
        "acceptance_predicate_hash": accept.predicate_hash,
        "target_identity": host,
        "artifact_digest": artifact,
        "observed_at_utc": observed,
        "evidence_expires_utc": observed + EVIDENCE_TTL_S,
        "observation_url": accept.url,
        "policy_hash": policy_hash,
    }
    digest = hashlib.sha256(
        (
            "MERIDIAN-SETTLEMENT-V1|"
            + "|".join(str(fields[k]) for k in _SETTLEMENT_ORDER)
        ).encode()
    ).digest()
    receipt_fields = dict(fields)
    receipt_fields["verifier_pubkey_hex"] = signer.public_key().public_bytes_raw().hex()
    receipt_fields["signature_hex"] = signer.sign(digest).hex()

    yield_receipt = {
        **expected,
        "action": "settle",
        "ok": True,
        "effect_ref": f"{accept.url}@{artifact}"[:512],
        "reconciled": True,
    }
    subject = (
        b"meridian/instruction-yield-v1:"
        + json.dumps(
            yield_receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    )
    return {
        "receipt": yield_receipt,
        "signature": signer.sign(subject).hex(),
        "settlement": {
            "obligation": {
                "acceptance_predicate_hash": fields["acceptance_predicate_hash"],
                "policy_hash": policy_hash,
            },
            "receipt": receipt_fields,
        },
    }


async def certify_instruction(
    client: Any,
    instruction_id: str,
    accept: Accept,
    *,
    seed_env: str,
    policy_hash: str,
    getter: Callable[[str], tuple[int, bytes]] = fetch,
    workflow_id: str | None = None,
    key_dir: str | None = None,
) -> dict[str, Any]:
    """Certify one live instruction and deliver the envelope to its workflow.

    In production the workflow id IS the instruction id (sovereign/engine/client.py start()).
    """
    handle = client.get_workflow_handle(workflow_id or instruction_id)
    state = await handle.query("state")
    description = await handle.describe()
    if state.get("instruction_id") != instruction_id:
        raise CertifierRefusal("workflow instruction does not match the one named")
    if state.get("status") in ("done", "failed", "stopped"):
        raise CertifierRefusal(
            f"instruction is already terminal ({state.get('status')})"
        )
    expected = expected_from_state(state, description.run_id)
    envelope = build_envelope(
        expected,
        accept,
        seed_env=seed_env,
        policy_hash=policy_hash,
        getter=getter,
        key_dir=key_dir,
    )
    await handle.signal("submit_independent_yield", envelope)
    return {
        "instruction_id": instruction_id,
        "run_id": description.run_id,
        "signalled": True,
    }


# The settlement policy the estate runs under. Pinned on the worker through the trust ConfigMap, so
# a receipt signed under any other policy is refused by the compiled gate.
POLICY_NAME = "meridian-settlement-policy-v1"
DEFAULT_POLICY_HASH = hashlib.sha256(POLICY_NAME.encode()).hexdigest()
WORKER_IDENTITY_FILE = "worker-identity.pub"
TRUST_CONFIGMAP = "settlement-trust"
_SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


def worker_identity_hex(key_dir: str) -> str:
    """A public identity for the worker, whose private half does not exist.

    The settlement obligation names the worker so the gate can refuse a receipt signed by it. The
    worker never signs anything, so this keypair is minted, its public half kept and its private
    half discarded at once: no key anywhere can speak as the worker, and it cannot equal the
    certifier's key.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    path = os.path.join(key_dir, WORKER_IDENTITY_FILE)
    os.makedirs(key_dir, mode=0o700, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        with open(path, encoding="ascii") as fh:
            return fh.read().strip()
    pub = Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()
    with os.fdopen(fd, "w", encoding="ascii") as fh:
        fh.write(pub)
    return pub


def trust_values(
    key_dir: str, policy_hash: str = DEFAULT_POLICY_HASH
) -> dict[str, str]:
    """The public trust anchors the worker pins. Public values only."""
    pub = public_key_hex(key_dir)
    worker = worker_identity_hex(key_dir)
    if worker == pub or not re.fullmatch(r"[0-9a-f]{64}", worker):
        raise CertifierRefusal("worker identity must be a distinct public key")
    return {
        "yield_verifier_pubkey_hex": pub,
        "certifiers_hex": pub,
        "worker_pubkey_hex": worker,
        "policy_hash": policy_hash,
    }


def _kube(method: str, url: str, body: bytes | None = None) -> tuple[int, bytes]:
    import ssl

    with open(os.path.join(_SA_DIR, "token"), encoding="ascii") as fh:
        token = fh.read().strip()
    ctx = ssl.create_default_context(cafile=os.path.join(_SA_DIR, "ca.crt"))
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/merge-patch+json"
    req = urllib.request.Request(  # noqa: S310 -- https enforced by _require_https
        _require_https(url), data=body, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(  # noqa: S310 -- request built from an https URL
            req, timeout=OBSERVE_TIMEOUT_S, context=ctx
        ) as r:
            return r.status, r.read(MAX_BODY)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(MAX_BODY)
    except (urllib.error.URLError, OSError) as exc:
        raise CertifierRefusal(f"cluster call failed: {type(exc).__name__}") from exc


def publish_trust(
    key_dir: str,
    *,
    namespace: str | None = None,
    policy_hash: str = DEFAULT_POLICY_HASH,
    kube: Callable[[str, str, bytes | None], tuple[int, bytes]] = _kube,
) -> str:
    """Write the public trust anchors into the settlement-trust ConfigMap; no human step.

    Returns `unchanged` or `published`. It touches the ConfigMap only when a value differs, so the
    worker restarts (the reloader watches the ConfigMap) only when the trust really changed.
    """
    if namespace is None:
        with open(os.path.join(_SA_DIR, "namespace"), encoding="ascii") as fh:
            namespace = fh.read().strip()
    want = trust_values(key_dir, policy_hash)
    url = (
        "https://kubernetes.default.svc/api/v1/namespaces/"
        f"{namespace}/configmaps/{TRUST_CONFIGMAP}"
    )
    status, body = kube("GET", url, None)
    if status != 200:
        raise CertifierRefusal(f"trust ConfigMap read answered {status}")
    have = json.loads(body).get("data") or {}
    if all(have.get(k) == v for k, v in want.items()):
        return "unchanged"
    status, _ = kube("PATCH", url, json.dumps({"data": want}).encode())
    if status != 200:
        raise CertifierRefusal(f"trust ConfigMap write answered {status}")
    return "published"


ISSUE_REF = re.compile(r"(?:chidionyema/idp)?#(\d{2,7})\b")
CONTRACT_ACCEPT = re.compile(r"^\s*accept:\s*(GET .+)$", re.MULTILINE)
REPO = "chidionyema/idp"


def governing_issue(task: str) -> int:
    """The one issue an instruction names. Zero or several refuse: the certifier never guesses."""
    refs = {int(n) for n in ISSUE_REF.findall(task or "")}
    if len(refs) != 1:
        raise CertifierRefusal(
            f"instruction names {len(refs)} issues; exactly one governs its acceptance"
        )
    return refs.pop()


def accept_from_comments(
    comments: list[dict[str, Any]], authors: frozenset[str]
) -> Accept:
    """The newest SHIP-CONTRACT accept line written by a trusted author (newest wins)."""
    if not authors:
        raise CertifierRefusal("no trusted contract authors configured")
    for comment in sorted(
        comments, key=lambda c: c.get("created_at", ""), reverse=True
    ):
        body = comment.get("body") or ""
        if "SHIP-CONTRACT" not in body:
            continue
        if (comment.get("user") or {}).get("login") not in authors:
            continue
        found = CONTRACT_ACCEPT.search(body)
        if found:
            return parse_accept(found.group(1))
    raise CertifierRefusal("no SHIP-CONTRACT accept line from a trusted author")


def fetch_comments(issue: int) -> list[dict[str, Any]]:
    """Read the issue's comments from the GitHub API (public read; token only if present)."""
    headers = {
        "User-Agent": "estate-certifier",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{REPO}/issues/{issue}/comments?per_page=100"
    req = urllib.request.Request(  # noqa: S310 -- https enforced by _require_https
        _require_https(url), headers=headers
    )
    try:
        with urllib.request.urlopen(  # noqa: S310 -- request built from an https URL
            req, timeout=OBSERVE_TIMEOUT_S
        ) as resp:
            return json.loads(resp.read(MAX_BODY))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CertifierRefusal(f"contract read failed: {type(exc).__name__}") from exc


async def sweep(
    client: Any,
    *,
    key_dir: str,
    policy_hash: str,
    authors: frozenset[str],
    comments_for: Callable[[int], list[dict[str, Any]]] = fetch_comments,
    getter: Callable[[str], tuple[int, bytes]] = fetch,
) -> dict[str, str]:
    """Certify every live instruction whose declared effect is observable. No human in the loop.

    Per instruction the outcome is `signalled` or `refused: <reason>`. A refusal signs nothing,
    so the workflow's bounded wait fails that instruction closed. A workflow that is not waiting
    for a yield ignores the signal, so repeating the sweep is safe.
    """
    outcomes: dict[str, str] = {}
    async for execution in client.list_workflows('ExecutionStatus="Running"'):
        handle = client.get_workflow_handle(execution.id)
        try:
            state = await handle.query("state")
            instruction_id = state.get("instruction_id")
            if not instruction_id:
                continue
            accept = accept_from_comments(
                comments_for(governing_issue(state.get("task", ""))), authors
            )
            await certify_instruction(
                client,
                instruction_id,
                accept,
                seed_env="",
                policy_hash=policy_hash,
                getter=getter,
                workflow_id=execution.id,
                key_dir=key_dir,
            )
            outcomes[instruction_id] = "signalled"
        except CertifierRefusal as exc:
            outcomes[str(getattr(execution, "id", "?"))] = f"refused: {exc}"
    return outcomes


def main(argv: list[str] | None = None) -> int:
    import argparse
    import asyncio

    p = argparse.ArgumentParser(
        description="Certify production effects of instructions"
    )
    p.add_argument("--instruction-id")
    p.add_argument(
        "--accept",
        help='e.g. GET https://host/path expect 200 contains "ok" within 30m',
    )
    p.add_argument(
        "--seed-env",
        default="ESTATE_CERTIFIER_SEED_HEX",
        help="NAME of the env var holding the seed (ignored with --key-dir)",
    )
    p.add_argument(
        "--key-dir",
        default=os.environ.get("ESTATE_CERTIFIER_KEY_DIR"),
        help="directory where the certifier mints and keeps its own key",
    )
    p.add_argument(
        "--print-pubkey", action="store_true", help="print the PUBLIC key hex and exit"
    )
    p.add_argument(
        "--sweep",
        action="store_true",
        help="certify every live instruction from its issue's SHIP-CONTRACT accept line",
    )
    p.add_argument(
        "--policy-hash",
        default=os.environ.get("ESTATE_SETTLEMENT_POLICY_HASH") or DEFAULT_POLICY_HASH,
    )
    p.add_argument(
        "--publish-trust",
        action="store_true",
        help="write the public trust anchors into the settlement-trust ConfigMap first",
    )
    args = p.parse_args(argv)

    if args.print_pubkey:
        if not args.key_dir:
            print("CERTIFIER_REFUSED: --print-pubkey needs --key-dir")
            return 2
        try:
            print(public_key_hex(args.key_dir))
        except CertifierRefusal as exc:
            print(f"CERTIFIER_REFUSED: {exc}")
            return 2
        return 0

    async def run() -> Any:
        from sovereign.engine.client import get_client

        if args.publish_trust:
            if not args.key_dir:
                raise CertifierRefusal("--publish-trust needs --key-dir")
            print(
                json.dumps(
                    {"trust": publish_trust(args.key_dir, policy_hash=args.policy_hash)}
                )
            )
            if not args.sweep and not args.instruction_id:
                return {}
        client = await get_client()
        if args.sweep:
            authors = frozenset(
                a.strip()
                for a in os.environ.get("ESTATE_CERTIFIER_CONTRACT_AUTHORS", "").split(
                    ","
                )
                if a.strip()
            )
            if not args.key_dir:
                raise CertifierRefusal("--sweep needs --key-dir")
            return await sweep(
                client,
                key_dir=args.key_dir,
                policy_hash=args.policy_hash,
                authors=authors,
            )
        if not args.instruction_id or not args.accept:
            raise CertifierRefusal("--instruction-id and --accept are required")
        return await certify_instruction(
            client,
            args.instruction_id,
            parse_accept(args.accept),
            seed_env=args.seed_env,
            policy_hash=args.policy_hash,
            key_dir=args.key_dir,
        )

    try:
        print(json.dumps(asyncio.run(run()), sort_keys=True))
    except CertifierRefusal as exc:
        print(f"CERTIFIER_REFUSED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
