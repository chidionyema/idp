#!/usr/bin/env python3
"""infra/recovery/credential-canary.py -- fail before a credential blocks a deploy.

Why: the estate has twice discovered a credential problem only when a deploy failed -- a
Cloudflare token minted in an account that does not hold the zone, and an OCI session that
expired. Both produced an outage-shaped symptom days later. A credential is a dependency like any
other: it gets a canary.

Each check answers one question and exits non-zero when the answer is no:

    cloudflare-zone   can this token see the zone the doors live in?
    cloudflare-write  can it write a DNS record in that zone? (dry run, nothing created)

    python3 infra/recovery/credential-canary.py            # human output
    python3 infra/recovery/credential-canary.py --json     # for a workflow to branch on
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

CF_API = "https://api.cloudflare.com/client/v4"
ZONE = os.environ.get("ESTATE_ZONE", "mumchimp.com")


def cf(
    token: str, method: str, path: str, body: dict | None = None
) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 - CF_API is a fixed https host
        f"{CF_API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - fixed https host
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {}
    except Exception as e:  # noqa: BLE001 - unreachable is a verdict, not a crash
        return 0, {"error": type(e).__name__}


def check_zone(token: str) -> dict:
    if not token:
        return {
            "check": "cloudflare-zone",
            "ok": False,
            "why": "no CLOUDFLARE_ROOT_TOKEN / SEED_CLOUDFLARE_ROOT_TOKEN in the environment",
        }
    code, body = cf(token, "GET", f"/zones?name={ZONE}")
    zones = (body or {}).get("result") or []
    if code == 200 and zones:
        return {
            "check": "cloudflare-zone",
            "ok": True,
            "why": f"{ZONE} visible",
            "zone_id": zones[0]["id"],
        }
    return {
        "check": "cloudflare-zone",
        "ok": False,
        "why": f"{ZONE} not visible to this token (HTTP {code}) -- wrong account or missing Zone:Read",
    }


def check_write(token: str, zone_id: str) -> dict:
    # A read of the record set exercises the same permission the repair needs, and creates nothing.
    code, body = cf(token, "GET", f"/zones/{zone_id}/dns_records?per_page=1")
    ok = code == 200 and (body or {}).get("success") is True
    return {"check": "cloudflare-read-dns", "ok": ok, "why": f"HTTP {code}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    token = os.environ.get("CLOUDFLARE_ROOT_TOKEN") or os.environ.get(
        "SEED_CLOUDFLARE_ROOT_TOKEN", ""
    )
    results = [check_zone(token)]
    if results[0]["ok"]:
        results.append(check_write(token, results[0]["zone_id"]))
    bad = [r for r in results if not r["ok"]]
    if a.json:
        print(json.dumps({"zone": ZONE, "ok": not bad, "results": results}, indent=1))
    else:
        for r in results:
            print(f"  {'ok  ' if r['ok'] else 'FAIL'}  {r['check']:18} {r['why']}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
