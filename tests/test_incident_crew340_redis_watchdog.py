"""crew#340: the local Langfuse worker logged "Redis Socket Timeout" every few minutes and
reconnected mid-queue; spans were accepted (HTTP 200) and never flushed. Rung 4, incident test:
the compose file disables the ioredis watchdog on every Langfuse service that shares the env."""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_incident_crew340_redis_watchdog_disabled_on_web_and_worker():
    doc = yaml.safe_load((ROOT / "observability" / "langfuse.yml").read_text())
    for name in ("langfuse-web", "langfuse-worker"):
        svc = doc["services"][name]
        env = svc.get("environment", {})
        if isinstance(env, list):
            env = dict(e.split("=", 1) for e in env)
        assert str(env.get("REDIS_SOCKET_TIMEOUT_MS")) == "0", f"{name}: watchdog not disabled (crew#340)"
