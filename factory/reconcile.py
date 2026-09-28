#!/usr/bin/env python3
"""
Reconciliation daemon. Runs forever on an interval; emits reports to ledger.
Exit non-zero only if --once and drift found.
"""

from __future__ import annotations
import argparse, json, logging, os, signal, sys, time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from factory import ledger, secrets as S
from factory.net import open_https, https_request

log = logging.getLogger("factory.reconcile")

ROOT = Path(os.environ.get("FACTORY_ROOT", Path.home() / "Documents" / "code"))
REGISTRY = Path(os.environ.get("FACTORY_REGISTRY", ROOT / "idp" / "registry.json"))
ORDERS = Path(os.environ.get("FACTORY_ORDERS", "orders"))
ALERT_URL = os.environ.get("FACTORY_ALERT_URL")

STOP = False


def _stop(*_):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def check_registry_fresh(ttl_seconds: int = 7200) -> list[dict]:
    if not REGISTRY.exists():
        return [{"kind": "REGISTRY_MISSING", "detail": str(REGISTRY)}]
    try:
        reg = json.loads(REGISTRY.read_text())
    except Exception as e:
        return [{"kind": "REGISTRY_UNPARSEABLE", "detail": str(e)[:200]}]
    gen = reg.get("generated_at")
    if not gen:
        return [{"kind": "REGISTRY_NO_TIMESTAMP"}]
    try:
        age = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(gen.replace("Z", "+00:00"))
        ).total_seconds()
    except Exception:
        return [{"kind": "REGISTRY_BAD_TIMESTAMP"}]
    if age > ttl_seconds:
        return [{"kind": "REGISTRY_STALE", "age_seconds": int(age), "ttl": ttl_seconds}]
    return []


def check_shed_vs_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    try:
        reg = json.loads(REGISTRY.read_text())
    except Exception as e:
        log.debug("registry unreadable in shed check: %s", e)
        return []
    current = {t["id"] for t in reg.get("terminals", []) if t.get("state") == "current"}
    shed = {
        e.get("capability_id") for e in ledger.read("sheds") if e.get("capability_id")
    }
    drift = sorted(current & shed)
    return [{"kind": "SHED_STILL_CURRENT", "capabilities": drift}] if drift else []


def check_secret_leaks() -> list[dict]:
    issues = []
    for repo in sorted(ROOT.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue
        for name in ("capability.yaml", "terminal.yaml"):
            p = repo / name
            if not p.exists():
                continue
            try:
                raw = p.read_bytes()
            except Exception as e:
                log.debug("cannot read %s: %s", p, e)
                continue
            try:
                S.refuse_literal_secrets(raw, f"{repo.name}/{name}")
            except S.SecretError as e:
                issues.append(
                    {"kind": "LITERAL_SECRET", "file": str(p), "detail": str(e)[:200]}
                )
    return issues


def check_order_backlog(max_age_seconds: int = 900) -> list[dict]:
    if not ORDERS.exists():
        return []
    stuck = []
    for f in ORDERS.glob("ord_*.json"):
        try:
            order = json.loads(f.read_text())
        except Exception as e:
            log.debug("order %s unparseable: %s", f, e)
            continue
        created = order.get("created_at")
        if not created:
            continue
        try:
            age = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(created.replace("Z", "+00:00"))
            ).total_seconds()
        except Exception as e:
            log.debug("order %s bad created_at: %s", f, e)
            continue
        if age < max_age_seconds:
            continue
        oid = order["order_id"]
        if not any(e.get("order_id") == oid for e in ledger.read("executions")):
            stuck.append({"order_id": oid, "age_seconds": int(age)})
    return (
        [{"kind": "ORDERS_STUCK", "count": len(stuck), "sample": stuck[:3]}]
        if stuck
        else []
    )


CHECKS = [
    check_registry_fresh,
    check_shed_vs_registry,
    check_secret_leaks,
    check_order_backlog,
]


def alert(drift):
    if not drift or not ALERT_URL:
        return
    try:
        body = json.dumps({"source": "factory-reconcile", "drift": drift}).encode()
        req = https_request(
            ALERT_URL,
            method="POST",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        open_https(req, timeout=10).close()
    except Exception as e:
        log.warning("alert delivery failed: %s", type(e).__name__)


def run_checks():
    out = []
    for fn in CHECKS:
        try:
            out.extend(fn())
        except Exception as e:
            out.append(
                {
                    "kind": "CHECK_FAILED",
                    "check": fn.__name__,
                    "err": f"{type(e).__name__}: {e}"[:200],
                }
            )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    while not STOP:
        started = time.time()
        drift = run_checks()
        report = {
            "at": datetime.now(timezone.utc).isoformat(),
            "drift_count": len(drift),
            "drift": drift,
            "duration_ms": int((time.time() - started) * 1000),
        }
        ledger.write("reconcile", report)
        if drift:
            print(f"[{report['at']}] DRIFT {len(drift)}")
            for d in drift:
                print(f"  {d}")
            alert(drift)
        elif args.verbose:
            print(f"[{report['at']}] clean in {report['duration_ms']}ms")
        if args.once:
            return 1 if drift else 0
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
