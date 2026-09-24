import os, json, hashlib, time, logging
from pathlib import Path
from .base import Surface
from .. import llm, ledger
from ..net import open_https, https_request

log = logging.getLogger("factory.surfaces.slack")


class SlackSurface(Surface):
    id = "slack"

    def __init__(self):
        self.token = os.environ.get("SLACK_BOT_TOKEN")

    def intake(self):
        inbox = Path("queue/slack_in")
        inbox.mkdir(parents=True, exist_ok=True)
        for f in sorted(inbox.glob("*.json")):
            try:
                payload = json.loads(f.read_text())
            except Exception as e:
                log.debug("slack inbox %s unparseable: %s", f, e)
                f.unlink()
                continue
            f.unlink()
            ev = payload.get("event", {})
            if ev.get("type") != "message" or ev.get("bot_id"):
                continue
            text = ev.get("text", "")
            user, channel = ev.get("user", ""), ev.get("channel", "")
            if not text:
                continue
            p = llm.decompose(text, tenant=f"per_{user}")
            oid = (
                "ord_"
                + hashlib.sha256(f"sl:{user}:{time.time()}".encode())
                .hexdigest()[:26]
                .upper()
            )
            return {
                "order_id": oid,
                "tenant_id": f"per_{user}",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": channel,
                "surface": self.id,
                "raw": text,
            }
        return None

    def deliver(self, order, message):
        if not self.token or not order.get("chat_id"):
            return {"delivered": False, "reason": "SLACK_NOT_CONFIGURED"}
        body = json.dumps({"channel": order["chat_id"], "text": message}).encode()
        delay, last = 1.0, ""
        for attempt in range(5):
            try:
                req = https_request(
                    "https://slack.com/api/chat.postMessage",
                    method="POST",
                    data=body,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                )
                with open_https(req, timeout=30) as r:
                    resp = json.loads(r.read())
                if resp.get("ok"):
                    ledger.write(
                        "deliveries",
                        {
                            "order_id": order["order_id"],
                            "surface": self.id,
                            "delivered": True,
                            "ts": resp.get("ts"),
                            "attempt": attempt + 1,
                        },
                    )
                    return {"delivered": True, "ts": resp.get("ts")}
                last = f"slack_error: {resp.get('error')}"
                if resp.get("error") in (
                    "channel_not_found",
                    "not_in_channel",
                    "invalid_auth",
                ):
                    break
            except Exception as e:
                last = type(e).__name__
            time.sleep(min(delay, 30))
            delay *= 2
        ledger.write(
            "dead_letters",
            {"order_id": order["order_id"], "surface": self.id, "error": last},
        )
        return {"delivered": False, "reason": last}
