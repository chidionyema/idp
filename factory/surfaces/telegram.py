import os, json, time, hashlib, logging, urllib.error, urllib.parse
from pathlib import Path
from .base import Surface
from .. import llm, ledger
from ..net import open_https, https_request

log = logging.getLogger("factory.surfaces.telegram")

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramSurface(Surface):
    id = "telegram"

    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.offset_file = Path(".tg_offset")

    def _offset(self):
        if self.offset_file.exists():
            try:
                return int(self.offset_file.read_text().strip())
            except ValueError:
                return None
        return None

    def _save(self, v):
        self.offset_file.write_text(str(v))

    def _get(self, method, **params):
        url = API.format(token=self.token, method=method)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with open_https(url, timeout=30) as r:
            return json.loads(r.read())

    def _post(self, method, payload):
        url = API.format(token=self.token, method=method)
        req = https_request(
            url,
            method="POST",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with open_https(req, timeout=30) as r:
            return json.loads(r.read())

    def intake(self):
        if not self.token:
            return None
        try:
            data = (
                self._get("getUpdates", offset=self._offset())
                if self._offset()
                else self._get("getUpdates")
            )
        except Exception as e:
            log.warning("telegram getUpdates failed: %s", type(e).__name__)
            return None
        for u in data.get("result", []):
            self._save(u["update_id"] + 1)
            msg = u.get("message") or {}
            if "text" not in msg:
                continue
            text, uid, chat = (
                msg["text"],
                str(msg["from"]["id"]),
                str(msg["chat"]["id"]),
            )
            parsed = llm.decompose(text, tenant=f"per_{uid}")
            oid = (
                "ord_"
                + hashlib.sha256(f"tg:{u['update_id']}".encode())
                .hexdigest()[:26]
                .upper()
            )
            return {
                "order_id": oid,
                "tenant_id": f"per_{uid}",
                "goal": parsed["goal"],
                "capabilities": parsed["capabilities"],
                "chat_id": chat,
                "surface": self.id,
                "raw": text,
            }
        return None

    def deliver(self, order, message):
        if not self.token or not order.get("chat_id"):
            return {"delivered": False, "reason": "no token/chat"}
        delay, last = 1.0, ""
        for attempt in range(5):
            try:
                resp = self._post(
                    "sendMessage",
                    {
                        "chat_id": order["chat_id"],
                        "text": message,
                        "reply_markup": {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "👍",
                                        "callback_data": f"ok:{order['order_id']}",
                                    },
                                    {
                                        "text": "👎",
                                        "callback_data": f"bad:{order['order_id']}",
                                    },
                                ]
                            ]
                        },
                    },
                )
                if resp.get("ok"):
                    ledger.write(
                        "deliveries",
                        {
                            "order_id": order["order_id"],
                            "surface": self.id,
                            "delivered": True,
                            "attempt": attempt + 1,
                        },
                    )
                    return {
                        "delivered": True,
                        "message_id": resp["result"]["message_id"],
                    }
                last = f"api_not_ok: {resp.get('description')}"
            except urllib.error.HTTPError as e:
                last = f"http {e.code}"
            except Exception as e:
                last = type(e).__name__
            time.sleep(min(delay, 30))
            delay *= 2
        ledger.write(
            "dead_letters",
            {"order_id": order["order_id"], "surface": self.id, "error": last},
        )
        return {"delivered": False, "reason": last}

    def receipt(self):
        if not self.token:
            return None
        try:
            data = (
                self._get("getUpdates", offset=self._offset())
                if self._offset()
                else self._get("getUpdates")
            )
        except Exception as e:
            log.warning("telegram receipt poll failed: %s", type(e).__name__)
            return None
        for u in data.get("result", []):
            self._save(u["update_id"] + 1)
            cb = u.get("callback_query")
            if not cb:
                continue
            data_str = cb.get("data", "")
            if ":" not in data_str:
                continue
            verdict, order_id = data_str.split(":", 1)
            if verdict not in ("ok", "bad"):
                continue
            try:
                self._post(
                    "answerCallbackQuery",
                    {"callback_query_id": cb["id"], "text": "recorded"},
                )
            except Exception as e:
                log.debug("answerCallbackQuery failed: %s", type(e).__name__)
            ledger.write(
                "receipts",
                {
                    "order_id": order_id,
                    "surface": self.id,
                    "verdict": verdict,
                    "engagement": 1.0 if verdict == "ok" else 0.5,
                },
            )
            return {"order_id": order_id, "verdict": verdict}
        return None
