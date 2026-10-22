"""Throwaway: read-only. Is the live concierge web app still deployed, and does it answer?"""
import json
import subprocess
import urllib.request

out = subprocess.run(["modal", "app", "list", "--json"], capture_output=True, text=True)
print("APPS", out.stdout[:3000] or out.stderr[:600])
try:
    import modal

    fn = modal.Cls.from_name("mums-concierge-web", "YarnVoice")
    print("YARN lookup ok")
except Exception as exc:  # noqa: BLE001
    print("YARN lookup", type(exc).__name__, str(exc)[:300])
for app in json.loads(out.stdout or "[]"):
    if app.get("Description") == "mums-concierge-web" or app.get("description") == "mums-concierge-web":
        print("WEB row", json.dumps(app))
r = subprocess.run(["modal", "app", "logs", "mums-concierge-web", "--timestamps"], capture_output=True, text=True, timeout=20) if False else None
ws = subprocess.run(["modal", "profile", "current"], capture_output=True, text=True).stdout.strip()
print("WORKSPACE", ws)
for path in ("/health", "/"):
    url = f"https://{ws}--mums-concierge-web-web.modal.run{path}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            print("HTTP", url, resp.status, resp.read(200))
    except Exception as exc:  # noqa: BLE001
        print("HTTP", url, type(exc).__name__, str(exc)[:200])
