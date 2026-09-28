"""Pub/sub for IoT: smart home, vehicles, sensors, drones, wearables."""

import json
from pathlib import Path
from datetime import datetime, timezone

INBOX = Path("queue/mqtt_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


def client(surface_id: str, broker: str, topic_in: str, topic_out: str, tenant: str):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "paho-mqtt"], check=True
        )
        import paho.mqtt.client as mqtt

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except Exception:
            payload = {"raw": msg.payload.decode(errors="ignore")}
        fname = (
            INBOX / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
        )
        fname.write_text(
            json.dumps({"surface": surface_id, "topic": msg.topic, "payload": payload})
        )

    c = mqtt.Client(client_id=f"factory-{surface_id}")
    c.on_message = on_message
    c.connect(broker, 1883, 60)
    c.subscribe(topic_in)
    c.loop_start()
    return c
