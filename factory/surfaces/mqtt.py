import os, json, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
from .base import Surface
from .. import llm, ledger

INBOX = Path("queue/mqtt_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


class MQTTSurface(Surface):
    id = "mqtt"

    def __init__(self):
        self.broker = os.environ.get("MQTT_BROKER")
        self.topic_in = os.environ.get("MQTT_TOPIC_IN", "factory/in")
        self.topic_out = os.environ.get("MQTT_TOPIC_OUT", "factory/out")

    def intake(self):
        for f in sorted(INBOX.glob("mqtt_*.json")):
            try:
                data = json.loads(f.read_text())
            except Exception:
                f.unlink()
                continue
            f.unlink()
            payload = data.get("payload", {})
            content = (
                payload.get("text")
                or payload.get("command")
                or json.dumps(payload)[:500]
            )
            p = llm.decompose(content, tenant="per_mqtt")
            oid = (
                "ord_"
                + hashlib.sha256(f"mq:{time.time()}".encode()).hexdigest()[:26].upper()
            )
            return {
                "order_id": oid,
                "tenant_id": "per_mqtt",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": data.get("topic", "mqtt"),
                "surface": self.id,
                "raw": content,
            }

    def deliver(self, order, message):
        try:
            import paho.mqtt.publish as publish
        except ImportError:
            import subprocess, sys

            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "paho-mqtt"], check=True
            )
            import paho.mqtt.publish as publish
        if not self.broker:
            return {"delivered": False, "reason": "NO_MQTT_BROKER"}
        try:
            publish.single(
                f"{self.topic_out}/{order['order_id']}",
                payload=message,
                hostname=self.broker,
            )
            ledger.write(
                "deliveries",
                {"order_id": order["order_id"], "surface": self.id, "delivered": True},
            )
            return {"delivered": True}
        except Exception as e:
            ledger.write(
                "dead_letters",
                {
                    "order_id": order["order_id"],
                    "surface": self.id,
                    "error": str(e)[:200],
                },
            )
            return {"delivered": False, "reason": type(e).__name__}


def client(surface_id, broker, topic_in):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "paho-mqtt"], check=True
        )
        import paho.mqtt.client as mqtt

    def on_message(c, u, msg):
        try:
            payload = json.loads(msg.payload)
        except Exception:
            payload = {"raw": msg.payload.decode(errors="ignore")}
        (
            INBOX / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
        ).write_text(
            json.dumps({"surface": surface_id, "topic": msg.topic, "payload": payload})
        )

    c = mqtt.Client(client_id=f"factory-{surface_id}")
    c.on_message = on_message
    c.connect(broker, 1883, 60)
    c.subscribe(topic_in)
    c.loop_start()
    return c
