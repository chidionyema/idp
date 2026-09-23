"""The broker as a service: the agent-facing side and the Telegram webhook, one process.

Two doors, and they are not equally trusted. `/ask` and `/state` face the agents, which are
assumed hostile -- everything arriving there is validated against the catalogue before the
founder's phone is allowed to buzz. `/webhook/telegram` faces Telegram, and what arrives
there is checked twice, once for the shared secret header Telegram sends and once for the
HMAC the broker minted (WJ.6).

That path is Telegram's, not this broker's, and the reason is worth the sentence: a Telegram
bot has exactly one webhook URL, this estate runs exactly one bot, and otto-gateway's door is
where that URL points (platform/otto-gateway/registration-reconciler.yaml, every five
minutes). So the broker does not register anything and does not poll -- the edge hands it a
copy of the same POST otto answers (platform/otto-gateway/telegram-mirror.yaml), and it
arrives on the path Telegram was given.

The kill switch is a file rather than a variable so that a broker restarted in the middle
of an incident comes back still stopped (WJ.10).
"""

from __future__ import annotations

import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from .broker import Broker, Refused
from .collector import sink_from_env
from .telegram import Phone, digest


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


def optional_secret(name: str) -> str:
    """A secret the broker works without, read the same way as one it does not.

    JIT_AGENT_KEY arrives with platform/jit/deployment.yaml's ExternalSecret, and an
    ExternalSecret is a controller reconciling, not an atomic event: between this image
    starting and that key landing there is a window. Raising in that window would put the
    broker in CrashLoopBackOff and take the approval path down with it, to protect a door
    that simply is not open yet. So an absent key means `identity()` refuses every caller,
    and every other door keeps working.
    """
    try:
        return secret(name)
    except (OSError, KeyError):
        return ""


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
    # The secret token Telegram signs every delivery with. It is the value the webhook was
    # registered with, which is flux-telegram's, because that is the bot whose taps arrive
    # here -- not the broker's own entry, which nothing registered anything with.
    webhook_secret: str = ""
    telegram_path: str = "/webhook/telegram"
    #: What the edge puts in front of every path when the request came through the public
    #: door. Empty means there is no public door and every path arrives bare.
    public_prefix: str = ""

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

    def _bearer(self) -> str:
        """The credential out of the Authorization header, or an empty string.

        The key travels in the header rather than the body: it is where a bearer credential
        belongs, this handler's log_message is silenced, and a body is what gets echoed into
        an error message by the next person to add a door.
        """
        sent = self.headers.get("Authorization") or ""
        return sent[7:] if sent.startswith("Bearer ") else ""

    #: Everything the broker answers is reachable from a public door (public-door.yaml), so
    #: every path is behind the agent key except two, and both have a reason. The Telegram
    #: path carries its own credential -- the secret token Telegram signs each delivery with,
    #: plus the HMAC inside callback_data -- and Telegram does not hold the estate's agent
    #: key. `/healthz` is a GET the kubelet makes from the node, which holds no key either,
    #: and it answers with the ledger's own verdict on itself and nothing about the estate.
    AGENT_DOORS = ("/ask", "/state", "/grants", "/identity")

    def path_after_prefix(self) -> str:
        """The path with the public door's prefix removed.

        The edge routes `https://otto.${ESTATE_ZONE}/jit/ask` here, because the shared Gateway
        listener carries one hostname and this broker does not get its own. Stripping the
        prefix in the broker rather than rewriting it at the edge is the smaller road: it is
        one branch here that a test can run, instead of a URLRewrite filter whose behaviour
        belongs to whichever ingress implementation happens to be installed.
        """
        prefix = self.public_prefix
        if prefix and self.path.startswith(prefix + "/"):
            return self.path[len(prefix) :]
        return self.path

    def do_POST(self) -> None:  # noqa: N802
        try:
            path = self.path_after_prefix()
            if path in self.AGENT_DOORS:
                # 401 before the body is even read, and separately from what the door then
                # does, so a bad key reads as "I am not who I said" rather than the 400 that
                # means "what you asked for is not allowed" -- and so an unauthenticated
                # caller learns nothing at all: not which grants exist, not whether a request
                # id is real, not even whether a grant id it named is in the catalogue.
                try:
                    self.broker.authenticate(self._bearer())
                except Refused as exc:
                    return self._reply(401, {"error": str(exc)})
            if path == "/ask":
                b = self._body()
                req = self.broker.ask(
                    b["grant"],
                    b.get("params") or {},
                    b.get("why", ""),
                    b.get("ttl", "10m"),
                    b.get("asked_by", "agent"),
                    attested=True,
                )
                self.phone.send_ask(req, self.broker._load_grant(req.grant_id))
                return self._reply(200, {"request": req.id})
            if path == "/identity":
                # Already authenticated above; identity() checks the key again on its own
                # account because it is also the thing that decides what the key buys, and a
                # Refused from it is still a 401 rather than the 400 every other Refused
                # answers with.
                try:
                    return self._reply(200, self.broker.identity(self._bearer()))
                except Refused as exc:
                    return self._reply(401, {"error": str(exc)})
            if path == "/state":
                req = self.broker.pending.get(self._body().get("request", ""))
                if req is None:
                    return self._reply(404, {"error": "no such request"})
                return self._reply(
                    200,
                    {"state": req.state, "reason": req.reason, "result": req.result},
                )
            if path == self.telegram_path:
                # First of the two checks. A mirrored request reaches this port from the edge
                # rather than from the agents, so the shared token is what separates Telegram
                # from anyone else who found the Service; the HMAC in callback_data is the
                # second, inside handle(), and neither alone is enough. compare_digest because
                # a byte-at-a-time comparison leaks the secret to whoever can time it.
                sent = self.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
                if not (
                    self.webhook_secret
                    and hmac.compare_digest(sent, self.webhook_secret)
                ):
                    # Deliberately not a ledger line. This path is reachable from the public
                    # door, so a line per refusal is a way for a stranger to fill the ledger
                    # volume; the ledger records what the broker *did*, and it did nothing.
                    return self._reply(401, {"error": "not telegram"})
                # Nothing reads this answer: the mirror discards it and Telegram sees otto's.
                # That is the point -- a broker that is down or slow can never make Telegram
                # retry, or fail, a delivery otto already accepted.
                handled = self.phone.handle(self._body())
                # The one line the broker prints per delivery, and the reason it prints it:
                # `log_message` is silenced above, so before this the broker answered a real
                # Telegram tap and left nothing in `kubectl logs` at all -- the ledger held the
                # record, but the ledger is a file on a PVC an operator cannot read from a
                # laptop, so there was no way to show a live round-trip completing (the
                # empirical-proof rule, founder 2026-09-05). Only *accepted* deliveries print:
                # reaching this line costs the shared secret token, so the volume is Telegram's
                # traffic and not a stranger's. `handled` is the broker's own verdict word and
                # carries no chat text, no token and no callback data (LAW 21).
                print(f"jit telegram: mirrored delivery handled: {handled}", flush=True)
                return self._reply(200, {"handled": handled})
            if path == "/grants":
                with open(self.broker.catalogue_path) as fh:
                    return self._reply(200, yaml.safe_load(fh) or {})
        except Refused as exc:
            return self._reply(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._reply(500, {"error": str(exc)[:200]})
        self._reply(404, {"error": "no such door"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path_after_prefix() == "/healthz":
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
        # WJ.7: the record of who was given write access to this estate does not live on
        # one node's disk any more. It is still written there first -- that file is what
        # /healthz verifies the chain of -- and then shipped to the collector every other
        # workload already reports to. None when OTEL_EXPORTER_OTLP_ENDPOINT is unset,
        # which is a laptop run, not the deployment (platform/jit/deployment.yaml sets it).
        ledger_sink=sink_from_env(),
        killswitch=killswitch_reader(
            os.environ.get("JIT_KILLSWITCH", "/var/lib/jit/stopped")
        ),
        agent_key=optional_secret("JIT_AGENT_KEY").encode(),
    )
    phone = Phone(secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID"), broker)
    Handler.broker, Handler.phone = broker, phone
    Handler.webhook_secret = secret("TELEGRAM_WEBHOOK_SECRET")
    Handler.telegram_path = os.environ.get("JIT_TELEGRAM_PATH", "/webhook/telegram")
    Handler.public_prefix = os.environ.get("JIT_PUBLIC_PREFIX", "")
    threading.Thread(
        target=_housekeeping, args=(broker, phone, ledger_path), daemon=True
    ).start()
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
