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


def fetch(url: str) -> tuple[int, bytes]:
    """The certifier's own observation: one GET, no redirects, bounded body."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "estate-certifier"})
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


def _signer(seed_env: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
) -> dict[str, Any]:
    """Observe, then sign. Raises CertifierRefusal and signs nothing when the effect is absent."""
    if not re.fullmatch(r"[0-9a-f]{64}", policy_hash):
        raise CertifierRefusal("policy hash must be a sha256 hex digest")
    if type(expected.get("epoch")) is not int:
        raise CertifierRefusal("workflow has no integer execution epoch")
    signer = _signer(seed_env)
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
        expected, accept, seed_env=seed_env, policy_hash=policy_hash, getter=getter
    )
    await handle.signal("submit_independent_yield", envelope)
    return {
        "instruction_id": instruction_id,
        "run_id": description.run_id,
        "signalled": True,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import asyncio

    p = argparse.ArgumentParser(
        description="Certify one instruction's production effect"
    )
    p.add_argument("--instruction-id", required=True)
    p.add_argument(
        "--accept",
        required=True,
        help='e.g. GET https://host/path expect 200 contains "ok" within 30m',
    )
    p.add_argument(
        "--seed-env",
        default="ESTATE_CERTIFIER_SEED_HEX",
        help="NAME of the env var holding the seed",
    )
    p.add_argument(
        "--policy-hash", default=os.environ.get("ESTATE_SETTLEMENT_POLICY_HASH", "")
    )
    args = p.parse_args(argv)

    async def run() -> dict[str, Any]:
        from sovereign.engine.client import get_client

        return await certify_instruction(
            await get_client(),
            args.instruction_id,
            parse_accept(args.accept),
            seed_env=args.seed_env,
            policy_hash=args.policy_hash,
        )

    try:
        print(json.dumps(asyncio.run(run()), sort_keys=True))
    except CertifierRefusal as exc:
        print(f"CERTIFIER_REFUSED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
