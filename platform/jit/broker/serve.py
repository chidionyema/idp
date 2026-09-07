"""The broker as a service: the agent-facing side and the Telegram webhook, one process.

Two doors, and they are not equally trusted. `/ask` and `/state` face the agents, which are
assumed hostile -- everything arriving there is validated against the catalogue before the
founder's phone is allowed to buzz. `/telegram` faces Telegram, and what arrives there is
checked twice, once for the shared secret header Telegram sends and once for the HMAC the
broker minted (WJ.6).

The kill switch is a file rather than a variable so that a broker restarted in the middle
of an incident comes back still stopped (WJ.10).
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from .broker import Broker, Refused
from .telegram import Phone, digest, poll_forever


def secret(name: str) -> str:
    """One secret value, read from the file the kubelet wrote, never from the environment.

    A secret in an env var leaves the process's control the moment anything prints its
    environment -- a crash dump, `kubectl describe pod`, a library's start-up log -- which is
    why kyverno's secrets-not-from-env-vars refuses that shape at admission. The Secret is
    mounted instead, one file per key, and this reads it once at start.

    The environment is still the fallback, and only for the tests and a local run: nothing
    in the cluster reaches it, because platform/jit/deployment.yaml sets no such variable.
    """
    path = os.path.join(os.environ.get("JIT_SECRETS", "/etc/jit-secrets"), name)
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return os.environ[name]


def killswitch_reader(path: str):
    def read() -> str | None:
        try:
            with open(path) as fh:
                return fh.read().strip() or "stopped"
        except FileNotFoundError:
            return None

    return read


class Handler(BaseHTTPRequestHandler):
    broker: Broker
    phone: Phone

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _reply(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):  # the ledger is the record, not stderr noise
        return

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/ask":
                b = self._body()
                req = self.broker.ask(
                    b["grant"],
                    b.get("params") or {},
                    b.get("why", ""),
                    b.get("ttl", "10m"),
                    b.get("asked_by", "agent"),
                )
                self.phone.send_ask(req, self.broker._load_grant(req.grant_id))
                return self._reply(200, {"request": req.id})
            if self.path == "/state":
                req = self.broker.pending.get(self._body().get("request", ""))
                if req is None:
                    return self._reply(404, {"error": "no such request"})
                return self._reply(
                    200,
                    {"state": req.state, "reason": req.reason, "result": req.result},
                )
            if self.path == "/grants":
                with open(self.broker.catalogue_path) as fh:
                    return self._reply(200, yaml.safe_load(fh) or {})
        except Refused as exc:
            return self._reply(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._reply(500, {"error": str(exc)[:200]})
        self._reply(404, {"error": "no such door"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            ok, why = self.broker.ledger.verify()
            return self._reply(200 if ok else 500, {"ledger": why})
        self._reply(404, {"error": "no such door"})


def _housekeeping(broker: Broker, phone: Phone, ledger_path: str) -> None:
    """Two jobs on one thread: retire requests nobody answered (WJ.3), and send the morning
    summary once a day (WJ.11). Neither is load-bearing for security -- the token expiry is
    -- so a thread that dies costs a message, never an open door."""
    last_digest = 0.0
    while True:
        time.sleep(30)
        try:
            broker.expire_stale()
            if time.time() - last_digest > 86400:
                phone_text = digest(ledger_path, time.time() - 86400)
                if last_digest:
                    from .telegram import _call

                    _call(
                        phone.token,
                        "sendMessage",
                        {"chat_id": phone.chat_id, "text": phone_text},
                    )
                last_digest = time.time()
        except Exception as exc:  # noqa: BLE001
            # Swallowing this is deliberate, and is why it is safe: housekeeping only
            # sends messages. Access ends because the token expires, never because this
            # thread ran, so a failure here costs a summary and never leaves a door open.
            print(f"jit housekeeping: {exc}", flush=True)  # noqa: T201


def main() -> None:
    root = os.environ.get("IDP_ROOT", ".")
    key = secret("JIT_SIGNING_KEY").encode()
    ledger_path = os.environ.get("JIT_LEDGER", "/var/lib/jit/ledger.jsonl")
    broker = Broker(
        catalogue=os.environ.get(
            "JIT_GRANTS", os.path.join(root, "platform/jit/grants.yaml")
        ),
        key=key,
        ledger_path=ledger_path,
        killswitch=killswitch_reader(
            os.environ.get("JIT_KILLSWITCH", "/var/lib/jit/stopped")
        ),
    )
    phone = Phone(secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID"), broker)
    Handler.broker, Handler.phone = broker, phone
    threading.Thread(
        target=_housekeeping, args=(broker, phone, ledger_path), daemon=True
    ).start()
    # His taps arrive here, on a connection this process opens outward -- see
    # telegram.poll_forever for why the broker pulls rather than being pushed to. Daemon,
    # because the HTTP server below is what holds the process open: if the agent-facing
    # door is gone there is nothing left worth approving.
    threading.Thread(target=poll_forever, args=(phone,), daemon=True).start()
    # S104: an in-cluster Service must answer the kubelet probe and the gateway, and
    # neither arrives on loopback. R20 admits exactly this shape, because the namespace
    # carries a both-ways default-deny NetworkPolicy (platform/jit/fence.yaml): "all
    # interfaces" is the two the fence lets through.
    ThreadingHTTPServer(
        ("0.0.0.0", int(os.environ.get("PORT", "8080"))),  # noqa: S104
        Handler,
    ).serve_forever()


if __name__ == "__main__":
    main()
