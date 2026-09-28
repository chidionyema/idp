import json, hashlib, time
from pathlib import Path
from .base import Surface
from .. import llm, ledger


class VoiceSurface(Surface):
    id = "voice"

    def intake(self):
        inbox = Path("queue/voice_in")
        inbox.mkdir(parents=True, exist_ok=True)
        for f in sorted(inbox.glob("*.json")):
            try:
                payload = json.loads(f.read_text())
            except Exception:
                f.unlink()
                continue
            f.unlink()
            text = payload.get("SpeechResult") or payload.get("text", "")
            caller = payload.get("From") or payload.get("from", "")
            if not text:
                continue
            p = llm.decompose(text, tenant=f"per_{caller}")
            oid = (
                "ord_"
                + hashlib.sha256(f"vo:{caller}:{time.time()}".encode())
                .hexdigest()[:26]
                .upper()
            )
            return {
                "order_id": oid,
                "tenant_id": f"per_{caller}",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": caller,
                "surface": self.id,
                "raw": text,
            }
        return None

    def deliver(self, order, message):
        out = Path("queue/voice_out")
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{order['order_id']}.json").write_text(
            json.dumps(
                {
                    "to": order.get("chat_id"),
                    "twiml": f"<Response><Say voice='Polly.Amy'>{message}</Say></Response>",
                }
            )
        )
        ledger.write(
            "deliveries",
            {
                "order_id": order["order_id"],
                "surface": self.id,
                "delivered": True,
                "queued": True,
            },
        )
        return {"delivered": True, "queued": True}
