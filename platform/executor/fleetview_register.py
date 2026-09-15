#!/usr/bin/env python3
"""The laptop half of the mutations relay: long-polls `fleetview-backend`'s executor door and
answers with the same local calls `mutations.py` already makes correctly on this machine.

Why this exists (see `backstage/plugins/fleetview-backend/src/executor_link.py` for the full
architecture note). `platform/executor/daemon.py`'s `live_worktree()` ties every mutation to the
founder's actual, current, on-disk checkout -- there is no cluster equivalent, so the daemon and
its ledger stay here, unmoved. What was missing was a door: the Backstage board's "Pending
mutations" card runs in the cluster and, before this file, had nothing laptop-side to ask. This
process is that door's laptop end -- it never talks to the executor daemon over anything but the
same local AF_UNIX socket `mutations.py`'s own `approve()`/`reject()` already use; it adds no new
transport (LAW 43), only a network hop between an in-cluster HTTP call and those existing,
unmoved, local calls.

Transport and trust. This dials OUT to `fleetview-backend`'s executor port over the tailnet --
never listens, never opens an inbound port on this machine (LAW 21: "a port would be a network
surface on a laptop"). Reachability of the far end is gated by `platform/tailscale/policy.hujson`'s
deny-by-default ACL, which names this Mac's own tag (`tag:founder-mac`) as the only source
permitted to reach `tag:estate-fleetview-executor` at all -- the same mutual, cryptographic node
authentication (Tailscale/WireGuard) already trusted for every other laptop<->cluster door in this
estate (`platform/jit/deployment.yaml`'s Service comment says this precisely: "the tailnet is the
identity layer that already exists here ... the ACL is the authentication"). An optional
`FLEETVIEW_EXECUTOR_KEY` shared value, when set, is sent as a header on top of that -- named
explicitly as a gap in the PR description when it is not set, never shipped silently unauthenticated
beyond what the ACL alone already provides.

Run:
    FLEETVIEW_EXECUTOR_URL=https://fleetview-executor.<tailnet>.ts.net:8091 \\
        python3 platform/executor/fleetview_register.py

`--selftest` exercises the dispatch table against a fake transport, no network, no daemon socket.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

_MUTATIONS_MODULE = (
    Path(__file__).resolve().parents[1]
    / "backstage"
    / "plugins"
    / "fleetview-backend"
    / "src"
    / "mutations.py"
)

POLL_PATH = "/executor/poll"
REPLY_PATH = "/executor/reply"
POLL_TIMEOUT_SEC = (
    30  # above executor_link.py's own POLL_TIMEOUT_SEC, so a clean idle reply
)
# always arrives before this client's own socket read would time out first
IDLE_RETRY_SEC = 1
ERROR_RETRY_SEC = 5


def _load_mutations():
    spec = importlib.util.spec_from_file_location(
        "fleetview_mutations_impl", _MUTATIONS_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_MUTATIONS_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_dispatch(impl: Any) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    """The verb table `dispatch()` below reads. A module-level function so `--selftest` can
    exercise it against a stub `impl` with no executor socket and no ledger on disk."""

    def _list_pending(_payload: dict[str, Any]) -> dict[str, Any]:
        return {"mutations": impl.list_pending()}

    def _approve(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return impl.approve(payload.get("ledger_id", ""))
        except impl.InvalidQuery as exc:
            return {"ok": False, "error": str(exc)}
        except impl.LedgerUnavailable as exc:
            return {"ok": False, "error": str(exc)}

    def _reject(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return impl.reject(payload.get("ledger_id", ""))
        except impl.InvalidQuery as exc:
            return {"ok": False, "error": str(exc)}

    return {"list_pending": _list_pending, "approve": _approve, "reject": _reject}


def dispatch(
    verb: str, payload: dict[str, Any], table: dict[str, Callable]
) -> dict[str, Any]:
    handler = table.get(verb)
    if handler is None:
        return {"ok": False, "error": f"unknown verb {verb!r}"}
    return handler(payload)


def _post(
    url: str, body: dict[str, Any], key: str | None, timeout: int
) -> dict[str, Any]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")  # noqa: S310 -- fixed, operator-supplied base_url only
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("X-Executor-Key", key)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- fixed, operator-supplied base_url only
        return json.loads(resp.read().decode())


def run(
    base_url: str, key: str | None, table: dict[str, Callable], *, once: bool = False
) -> None:
    poll_url = base_url.rstrip("/") + POLL_PATH
    reply_url = base_url.rstrip("/") + REPLY_PATH
    while True:
        try:
            frame = _post(poll_url, {}, key, timeout=POLL_TIMEOUT_SEC)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"poll failed: {exc}", file=sys.stderr)
            if once:
                raise
            time.sleep(ERROR_RETRY_SEC)
            continue
        if frame.get("idle"):
            if once:
                return
            time.sleep(IDLE_RETRY_SEC)
            continue
        request_id = frame.get("request_id", "")
        verb = frame.get("verb", "")
        payload = frame.get("payload", {})
        result = dispatch(verb, payload, table)
        try:
            _post(
                reply_url, {"request_id": request_id, "result": result}, key, timeout=10
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"reply failed for {request_id}: {exc}", file=sys.stderr)
        if once:
            return


def _selftest() -> int:
    class _StubImpl:
        class InvalidQuery(ValueError):
            pass

        class LedgerUnavailable(RuntimeError):
            pass

        def list_pending(self):
            return [{"ledger_id": "abc123", "status": "pending_verification"}]

        def approve(self, ledger_id):
            if not ledger_id:
                raise self.InvalidQuery("approve needs a ledger_id")
            return {"ok": True, "ledger_id": ledger_id}

        def reject(self, ledger_id):
            if not ledger_id:
                raise self.InvalidQuery("reject needs a ledger_id")
            return {"ok": True, "ledger_id": ledger_id, "rejected": True}

    table = build_dispatch(_StubImpl())
    checks = [
        (
            dispatch("list_pending", {}, table)
            == {
                "mutations": [{"ledger_id": "abc123", "status": "pending_verification"}]
            }
        ),
        (
            dispatch("approve", {"ledger_id": "abc123"}, table)
            == {"ok": True, "ledger_id": "abc123"}
        ),
        (
            dispatch("approve", {}, table)
            == {"ok": False, "error": "approve needs a ledger_id"}
        ),
        (
            dispatch("reject", {"ledger_id": "abc123"}, table)
            == {"ok": True, "ledger_id": "abc123", "rejected": True}
        ),
        (dispatch("bogus", {}, table)["ok"] is False),
    ]
    if all(checks):
        print("ok --selftest: 5/5 dispatch cases pass")
        return 0
    print(f"FAIL --selftest: {checks}", file=sys.stderr)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", default=os.environ.get("FLEETVIEW_EXECUTOR_URL"))
    parser.add_argument("--key", default=os.environ.get("FLEETVIEW_EXECUTOR_KEY"))
    parser.add_argument(
        "--once",
        action="store_true",
        help="answer at most one poll cycle, then exit (used by tests)",
    )
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    if not args.url:
        print("--url or FLEETVIEW_EXECUTOR_URL is required", file=sys.stderr)
        sys.exit(2)

    impl = _load_mutations()
    table = build_dispatch(impl)
    run(args.url, args.key, table, once=args.once)


if __name__ == "__main__":
    main()
