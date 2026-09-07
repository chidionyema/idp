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
import urllib.error
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310 -- API is an https literal
            return json.load(fh)
    except urllib.error.HTTPError as exc:
        # urlopen raises before anything reads the body, and the body is the only place
        # Telegram says what it refused. `HTTP Error 409: Conflict` is equally true of a
        # webhook that is already registered and of a second reader on the same bot, and
        # those want opposite repairs -- on 2026-09-07 the broker printed that bare line
        # every five seconds for hours and named neither. The token travels in the URL and
        # never in the body, so the body is safe to carry into a log line (LAW 21).
        said = exc.read().decode("utf-8", "replace")[:500]
        try:
            said = json.loads(said).get("description") or said
        except ValueError:
            pass
        raise RuntimeError(f"telegram {method}: {exc.code} {said}") from None


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
