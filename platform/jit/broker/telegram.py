"""WJ.2, WJ.3, WJ.10 and WJ.11: the founder's whole interface to the broker is his phone.

LAW 54 makes this non-negotiable -- he is enterprise client zero, so there is no terminal
step, no YAML and no repository in the approval path. What he gets is one message with the
three things WJ.2 names (why, what, how long) and two buttons.

The signature is the security, not the chat. `callback_data` comes back to us from Telegram
and is therefore attacker-shaped input; it carries the HMAC the broker minted, and
`Broker.decide` verifies it before anything happens. The second check is `_from_founder`:
even a correct signature is refused from a chat that is not his, so a leaked callback in
another chat is inert.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request

from .broker import Broker, Refused, Request

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, payload: dict, timeout: int = 20) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(  # noqa: S310 -- API is an https literal
        API.format(token=token, method=method),
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310 -- API is an https literal
        return json.load(fh)


def ask_text(req: Request, grant: dict) -> str:
    """The three things WJ.2 names, in the order a person reads them on a lock screen: what
    is wrong, what will be done about it, and how long the door stays open."""
    # Kubernetes grants describe themselves as a verb on a resource; the layers below have no
    # verbs, they have operations. Either way the founder is shown the act, never "a grant".
    what = grant.get("describes") or " ".join(
        (grant.get("verbs") or [])[:1] + (grant.get("resources") or [])[:1]
        or (grant.get("operations") or [grant.get("id", "?")])[:1]
    )
    params = ", ".join(f"{k}={v}" for k, v in sorted(req.params.items()))
    # WJ.15: ten minutes on the cluster and ten minutes on the tenancy are not the same risk,
    # so the layer is on the lock screen rather than inferred from the grant's name.
    provider = str(grant.get("provider") or "kubernetes")
    where = "" if provider == "kubernetes" else f" on *{provider}*"
    holds = (
        "*Ends* by itself after {ttl}, whatever happens next."
        if grant.get("mode") == "token"
        else "*Ends* when this one change is done; nothing is handed over."
    ).format(ttl=req.ttl)
    return (
        f"*{req.asked_by}* needs {req.ttl} of write access{where}.\n\n"
        f"*Why* {req.why}\n"
        f"*What* {what} — {params}\n"
        f"{holds}"
    )


def ask_keyboard(broker: Broker, req: Request) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"Approve {req.ttl}",
                    "callback_data": broker.callback_data(req.id, "approve"),
                },
                {"text": "Deny", "callback_data": broker.callback_data(req.id, "deny")},
            ],
            [
                {"text": "Stop the broker", "callback_data": "j:stop"},
            ],
        ]
    }


class Phone:
    def __init__(self, token: str, chat_id: str, broker: Broker):
        self.token, self.chat_id, self.broker = token, str(chat_id), broker

    def _from_founder(self, update: dict) -> bool:
        """WJ.6: accepted only from the founder's own chat. An agent that somehow obtained a
        valid signature still cannot spend it, because it cannot be him."""
        cb = update.get("callback_query") or {}
        return str((cb.get("message") or {}).get("chat", {}).get("id")) == self.chat_id

    def send_ask(self, req: Request, grant: dict) -> None:
        _call(
            self.token,
            "sendMessage",
            {
                "chat_id": self.chat_id,
                "parse_mode": "Markdown",
                "text": ask_text(req, grant),
                "reply_markup": ask_keyboard(self.broker, req),
            },
        )

    def handle(self, update: dict) -> str:
        cb = update.get("callback_query") or {}
        data = cb.get("data") or ""
        if not data.startswith("j:"):
            return "ignored"
        if not self._from_founder(update):
            self.broker.ledger.append("callback-from-elsewhere", data=data[:64])
            return "refused: not the founder's chat"
        if data == "j:stop":
            return self.stop("the founder pressed stop")
        try:
            req = self.broker.decide_callback(data)
        except Refused as exc:
            return f"refused: {exc}"
        if req.state == "granted":
            return "granted"
        return req.state if req.state != "failed" else f"failed: {req.reason}"

    # WJ.10 -------------------------------------------------------------------

    def stop(self, reason: str) -> str:
        """One tap halts everything, pending and standing. It is a file rather than a
        process flag so that a broker restarted mid-incident comes back still stopped --
        a kill switch that forgets is not a kill switch."""
        path = os.environ.get("JIT_KILLSWITCH", "/var/lib/jit/stopped")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(reason)
        for req in self.broker.pending.values():
            if req.state == "pending":
                req.state = "denied"
        self.broker.ledger.append("stopped", reason=reason)
        return "stopped"


def poll_forever(phone: Phone) -> None:
    """How his tap actually reaches the broker: the broker pulls it, nothing pushes.

    Telegram delivers either way -- a webhook it POSTs to, or getUpdates the bot calls. The
    webhook road wants a public hostname, a listener, a certificate and a DNS record in front
    of the one workload in this estate that can mint write access, and the estate's single
    Gateway lives in the prospector repository, so it is also a second pull request in a second
    repository before one tap can arrive. This road wants none of that: nothing inbound reaches
    namespace jit at all, which is the shape platform/jit/fence.yaml already wants (LAW 23, the
    smaller road; LAW 21, secure by default).

    It is also the stronger provenance, not a weaker one. A webhook proves "Telegram sent this"
    with a shared header that a leak spends; here the broker opens the TLS connection to
    api.telegram.org itself, so there is nothing for anyone else to send. The check that carries
    the security is unchanged either way: every callback_data holds the HMAC the broker minted
    and `Broker.decide_callback` verifies it, and `_from_founder` refuses any chat but his.

    One replica is what makes this correct rather than merely convenient: getUpdates hands each
    update to exactly one reader, and platform/jit/deployment.yaml holds the broker at one for
    the separate reason that pending requests live in memory.
    """
    # A webhook left registered by an earlier run turns every getUpdates into a 409 and this
    # loop into a silent no-op -- the failure where he taps, nothing happens, and nothing says
    # so. Clearing it first makes exactly one delivery road live.
    try:
        _call(phone.token, "deleteWebhook", {"drop_pending_updates": False})
    except Exception as exc:  # noqa: BLE001
        print(f"jit telegram: deleteWebhook failed: {exc}", flush=True)
    offset = 0
    while True:
        try:
            # A 50-second long poll, so an idle broker costs about one request a minute rather
            # than a busy loop, and a tap is picked up the moment it is made.
            got = _call(
                phone.token,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 50,
                    "allowed_updates": ["callback_query"],
                },
                timeout=70,
            )
        except Exception as exc:  # noqa: BLE001
            # Never fatal. A broker that exits on a network blip is a broker that stops asking,
            # and WJ.3 already reads a silence as a no -- so the safe direction is to keep
            # trying rather than to die quietly.
            print(f"jit telegram: getUpdates failed: {exc}", flush=True)
            time.sleep(5)
            continue
        if not got.get("ok"):
            print(
                f"jit telegram: getUpdates refused: {got.get('description')}",
                flush=True,
            )
            time.sleep(5)
            continue
        for update in got.get("result") or []:
            # Advance the offset before handling: an update that makes the handler throw must
            # not be re-delivered forever, and the ledger already holds what happened to it.
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            try:
                print(f"jit telegram: {phone.handle(update)}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"jit telegram: update {offset - 1} failed: {exc}", flush=True)


# WJ.11 -----------------------------------------------------------------------


def digest(ledger_path: str, since: float) -> str:
    """The morning summary. The spec calls this the cheapest item and the one that decides
    whether he trusts the broker -- because a thing that acts while he is asleep and never
    says what it did is a thing he will turn off."""
    counts: dict[str, list[str]] = {}
    if os.path.exists(ledger_path):
        with open(ledger_path) as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("at", 0) < since or rec.get("event") == "asked":
                    continue
                counts.setdefault(rec["event"], []).append(rec.get("request", "")[:8])
    if not counts:
        return "The broker granted nothing overnight. Nothing asked for write access."
    say = {
        "granted": "approved",
        "denied": "denied",
        "failed": "failed after approval",
        "expired": "expired unused",
        "stopped": "stopped by you",
        "forged": "rejected as unsigned",
        "callback-from-elsewhere": "rejected from another chat",
    }
    lines = [f"{len(v)} {say.get(k, k)}" for k, v in sorted(counts.items())]
    return "Overnight: " + ", ".join(lines) + "."
