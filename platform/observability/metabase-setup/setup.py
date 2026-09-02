"""Kill the Metabase first-run wizard by machine (decision 0016).

GET /api/session/properties for the setup token; if one exists, POST /api/setup with the
founder's email and the vault-minted password from the mounted files. An instance that is
already set up publishes no token: exit 0, saying so, so the Job is idempotent.
"""

import json
import sys
import time
import urllib.request

BASE = "http://metabase.observability.svc.cluster.local:3000"


def http_open(req, timeout):
    """One audited door for every request; BASE above pins the scheme to in-cluster http."""
    url = req if isinstance(req, str) else req.full_url
    if not url.startswith(BASE):
        raise ValueError(f"refusing non-cluster URL: {url}")
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 - scheme pinned above


def read_secret(name: str) -> str:
    with open(f"/run/secrets/metabase/{name}", encoding="utf-8") as fh:
        return fh.read().strip()


def get_json(path: str) -> dict:
    with http_open(BASE + path, timeout=10) as resp:
        return json.load(resp)


def main() -> int:
    for attempt in range(60):
        try:
            props = get_json("/api/session/properties")
            break
        except Exception as exc:  # noqa: BLE001 - any failure here is "not up yet"
            print(f"waiting for metabase ({attempt + 1}/60): {exc}", flush=True)
            time.sleep(10)
    else:
        print("metabase never answered /api/session/properties", flush=True)
        return 1

    token = props.get("setup-token")
    if not token:
        print("already set up: no setup token published; nothing to do", flush=True)
        return 0

    body = {
        "token": token,
        "prefs": {"site_name": "Estate", "allow_tracking": "false"},
        "user": {
            "email": read_secret("METABASE_ADMIN_EMAIL"),
            "password": read_secret("METABASE_ADMIN_PASSWORD"),
            "first_name": "Founder",
            "last_name": "Admin",
        },
    }
    req = urllib.request.Request(  # noqa: S310 - BASE pins the scheme to in-cluster http
        BASE + "/api/setup",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with http_open(req, timeout=30) as resp:
        print(f"admin seeded, wizard gone (HTTP {resp.status})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
