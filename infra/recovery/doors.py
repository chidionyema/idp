#!/usr/bin/env python3
"""infra/recovery/doors.py -- the recovery loop for the estate's door endpoints, as code.

    doors.py                     probe every door and print what is wrong
    doors.py --repair --target <host>   repoint dead/missing doors at a live substrate

Why this exists: the estate-doors outage was diagnosed by hand on 9 November (five hostnames
pointing at a retired load balancer, two with no record at all) and the diagnosis died with the
session. This is that diagnosis as a program: it probes each door, says which failure class it is
in, and can repair the DNS half in one run once a target exists.

It never pretends a door is up: a door is OK only when its host answers over TLS.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOORS = ["llm", "otto", "auth", "api", "mcp", "catalogue", "deck", "lifeboat"]
ZONE = os.environ.get("ESTATE_ZONE", "mumchimp.com")
CF_API = "https://api.cloudflare.com/client/v4"


def resolve(host: str) -> list[str]:
    try:
        return sorted({a[4][0] for a in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
    except OSError:
        return []


def answers(host: str) -> tuple[bool, str]:
    req = urllib.request.Request(f"https://{host}/", method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:  # noqa: S310
            return r.status < 500, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        # A 4xx is an answer: the host is serving, the door just has no route at /. Counting it
        # as down is how "13 of 14 doors are dead" overstated the outage by one.
        return e.code < 500, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - every other failure is a verdict
        return False, type(e).__name__


def probe() -> list[dict]:
    out = []
    for d in DOORS:
        host = f"{d}.{ZONE}"
        ips = resolve(host)
        ok, why = answers(host) if ips else (False, "NO RECORD")
        out.append({"door": d, "host": host, "ips": ips, "ok": ok, "why": why})
    return out


def cf(env_token: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{CF_API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {env_token}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - fixed https host
        return json.loads(r.read().decode())


def repair(rows: list[dict], target: str) -> int:
    token = os.environ.get("CLOUDFLARE_ROOT_TOKEN", "")
    if not token:
        print("BLIND: no CLOUDFLARE_ROOT_TOKEN; cannot repair DNS", file=sys.stderr)
        return 2
    zones = cf(token, "GET", f"/zones?name={ZONE}")
    if not zones.get("result"):
        print(f"REFUSED: {ZONE} is not a zone this token can see (wrong account or missing Zone:Read)",
              file=sys.stderr)
        return 3
    zid = zones["result"][0]["id"]
    changed = 0
    for row in rows:
        if row["ok"]:
            continue
        name = row["host"]
        recs = cf(token, "GET", f"/zones/{zid}/dns_records?name={name}")["result"]
        body = {"type": "A", "name": name, "content": target, "proxied": True, "ttl": 1}
        if recs:
            cf(token, "PUT", f"/zones/{zid}/dns_records/{recs[0]['id']}", body)
            print(f"  repointed {name} -> {target}")
        else:
            cf(token, "POST", f"/zones/{zid}/dns_records", body)
            print(f"  created   {name} -> {target}")
        changed += 1
    return 0 if changed or all(r["ok"] for r in rows) else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repair", action="store_true")
    ap.add_argument("--target", default="")
    a = ap.parse_args(argv)
    rows = probe()
    print(f"doors of {ZONE}")
    for r in rows:
        print(f"  {'OK  ' if r['ok'] else 'DOWN'}  {r['host']:28} {','.join(r['ips']) or '-':32} {r['why']}")
    down = [r for r in rows if not r["ok"]]
    print(f"  {len(rows) - len(down)} of {len(rows)} door(s) answering")
    if not a.repair:
        return 0 if not down else 1
    if not a.target:
        print("REFUSED: --repair needs --target <ip-or-host> to point the doors at", file=sys.stderr)
        return 2
    return repair(down, a.target)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
