#!/usr/bin/env python3
"""infra/recovery/bws-sync.py -- the missing direction: Bitwarden Secrets Manager -> the estate vault.

The estate has vault-seed (GitHub secret -> OCI vault) and vault-bootstrap (creates the Bitwarden
project), but nothing that pulls a secret *from* Bitwarden into the vault the cluster reads. That
is why a credential the founder rotated in Bitwarden never reached the estate, and why a deploy
failed eleven days later.

    bws-sync.py --plan                 which named secrets would move (names only, never values)
    bws-sync.py --apply                write them into the vault
    bws-sync.py --plan --json          the same, machine-readable for a surface

Names come from infra/recovery/secret-map.json: {"<bws secret name>": "<vault entry name>"}. Only
mapped names move -- an unmapped secret in Bitwarden is never copied by accident, and a value is
never printed, logged or passed as an argument.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

MAP = Path(__file__).with_name("secret-map.json")


def run(cmd: list[str], stdin: str | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=120)  # noqa: S603
    return p.returncode, (p.stdout if p.returncode == 0 else p.stderr)


def bws_secrets() -> dict[str, str]:
    """name -> id, from `bws secret list`. Values are fetched one at a time, only when applying."""
    rc, out = run(["bws", "secret", "list", "--output", "json"])
    if rc != 0:
        raise RuntimeError(f"bws secret list failed: {out.strip()[:200]}")
    found = {}
    for item in json.loads(out or "[]"):
        name = item.get("key") or item.get("name")
        if name:
            found[name] = item.get("id", "")
    return found


def bws_value(secret_id: str) -> str:
    rc, out = run(["bws", "secret", "get", secret_id, "--output", "json"])
    if rc != 0:
        raise RuntimeError("bws secret get failed")
    data = json.loads(out or "{}")
    return data.get("value", "")


def vault_write(entry: str, key: str, value: str) -> bool:
    """Write through the estate's own door: bin/idp-vault-put <entry> <key>=ENV.

    The value travels in the child's environment, never on the command line, so it cannot appear
    in a process listing or a log line.
    """
    env = dict(os.environ)
    env["BWS_SYNC_VALUE"] = value
    p = subprocess.run(  # noqa: S603 - fixed argv
        ["bin/idp-vault-put", entry, f"{key}=BWS_SYNC_VALUE"],
        capture_output=True, text=True, timeout=120, env=env,
    )
    return p.returncode == 0


def plan(mapping: dict[str, dict]) -> list[dict]:
    have = bws_secrets()
    return [{"bws": name, "vault": spec["entry"], "key": spec["key"],
             "present": name in have, "id": have.get(name, "")}
            for name, spec in mapping.items()]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    mapping = json.loads(MAP.read_text())
    rows = plan(mapping)
    missing = [r["bws"] for r in rows if not r["present"]]
    if a.json:
        print(json.dumps({"mapped": len(rows), "missing": missing, "rows": [
            {k: v for k, v in r.items() if k != "id"} for r in rows]}, indent=1))
    else:
        for r in rows:
            print(f"  {'ok  ' if r['present'] else 'MISS'}  {r['bws']:32} -> vault:{r['vault']}")
    if missing:
        print(f"  REFUSED: {len(missing)} mapped secret(s) absent from Bitwarden", file=sys.stderr)
        return 1
    if a.plan:
        return 0
    if not a.apply:
        print("  nothing changed (pass --apply to write)", file=sys.stderr)
        return 0
    failed = 0
    for r in rows:
        value = bws_value(r["id"])
        if not value or not vault_write(r["vault"], r["key"], value):
            failed += 1
            print(f"  FAILED {r['bws']}", file=sys.stderr)
    print(f"  {len(rows) - failed}/{len(rows)} written")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
