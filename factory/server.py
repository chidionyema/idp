#!/usr/bin/env python3
"""
Serving layer. Stdlib only. Runs on :8080.
  POST /orders            create an order; returns order_id + status_url
  GET  /orders/<id>       status of that order
  GET  /orders            recent orders
  POST /webhook/<name>    webhook receiver for any HTTP-push surface
  GET  /health            liveness + version + registry hash
  GET  /                  HTML form for humans to place orders
"""

from __future__ import annotations

import hashlib, json, os, sys, time, threading, traceback, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factory.registry import collect, save
from factory.resolver import resolve
from factory.exec import run_dag
from factory.surfaces.registry import all_surfaces
from factory import ledger, secrets as S, llm

ROOT = Path(os.environ.get("FACTORY_ROOT", Path.home() / "Documents" / "code"))
REGISTRY_PATH = Path(os.environ.get("FACTORY_REGISTRY", ROOT / "idp" / "registry.json"))
VERSION = "factory/1.0"

ORDERS = Path(os.environ.get("FACTORY_ORDERS", "orders"))
ORDERS.mkdir(parents=True, exist_ok=True)


def save_order(order: dict) -> None:
    (ORDERS / f"{order['order_id']}.json").write_text(json.dumps(order, indent=2))


def load_order(oid: str) -> dict | None:
    p = ORDERS / f"{oid}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def recent_orders(n=50) -> list[dict]:
    files = sorted(
        ORDERS.glob("ord_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    out = []
    for f in files[:n]:
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out


def build_status(order_id: str) -> dict:
    order = load_order(order_id)
    if not order:
        return {"order_id": order_id, "status": "unknown"}
    executions = [e for e in ledger.read("executions") if e.get("order_id") == order_id]
    deliveries = [d for d in ledger.read("deliveries") if d.get("order_id") == order_id]
    receipts = [r for r in ledger.read("receipts") if r.get("order_id") == order_id]
    return {
        "order_id": order_id,
        "status": "delivered"
        if deliveries
        else ("executed" if executions else "created"),
        "order": order,
        "executions": executions,
        "deliveries": deliveries,
        "receipts": receipts,
    }


def process_order(order: dict) -> None:
    try:
        registry = collect(ROOT)
        save(registry, REGISTRY_PATH)
        resolution = resolve(order, registry)
        ledger.write(
            "resolutions",
            {
                "order_id": order["order_id"],
                "resolved": [t["id"] for t in resolution["resolved"]],
                "unresolved": resolution["unresolved"],
                "chain_errors": resolution["chain_errors"],
            },
        )
        if resolution["chain_errors"]:
            ledger.write(
                "errors",
                {
                    "where": "chain",
                    "order_id": order["order_id"],
                    "detail": resolution["chain_errors"],
                },
            )
            return
        execution = run_dag(order, resolution["resolved"], ROOT)
        ledger.write(
            "executions",
            {
                "order_id": order["order_id"],
                "outcome": execution["outcome"],
                "runtime": execution["runtime"],
                "steps": len(execution["steps"]),
            },
        )
        final = execution.get("final", {}) or {}
        message = (
            final.get("alert") or f"Order {order['order_id']} — {execution['outcome']}"
        )
        if final.get("reason") and execution["outcome"] != "ok":
            message += f": {final['reason']}"
        for s in all_surfaces():
            if s.id == order.get("surface"):
                s.deliver(order, message)
                break
    except Exception as e:
        ledger.write(
            "errors",
            {
                "where": "process_order",
                "order_id": order.get("order_id"),
                "err": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-500:],
            },
        )


class Handler(BaseHTTPRequestHandler):
    server_version = "factory"

    def _json(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload, default=str).encode())

    def _html(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _read_body(self):
        n = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(n) if n else b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Tenant-Id")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/health":
            reg = {}
            try:
                reg = json.loads(REGISTRY_PATH.read_text())
            except Exception:
                pass
            reg_hash = hashlib.sha256(
                json.dumps(reg.get("terminals", []), sort_keys=True).encode()
            ).hexdigest()[:12]
            return self._json(
                200,
                {
                    "ok": True,
                    "version": VERSION,
                    "registry": {
                        "terminals": reg.get("count", 0),
                        "seed": reg.get("seed_repo"),
                        "hash": reg_hash,
                        "generated_at": reg.get("generated_at"),
                    },
                    "at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if path.startswith("/orders/"):
            return self._json(200, build_status(path[len("/orders/") :]))
        if path == "/orders":
            return self._json(200, {"orders": recent_orders(50)})
        if path == "/":
            return self._html(200, INDEX_HTML)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        raw = self._read_body()
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/webhook/"):
            name = path[len("/webhook/") :]
            try:
                try:
                    secret = S.vend(
                        f"env://{name.upper()}_WEBHOOK_SECRET", tenant="factory"
                    )
                    import hmac

                    sig = self.headers.get("X-Signature") or self.headers.get(
                        "X-Hub-Signature-256", ""
                    )
                    expected = (
                        "sha256="
                        + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
                    )
                    if not hmac.compare_digest(sig, expected):
                        return self._json(401, {"error": "signature"})
                except S.SecretUnavailable:
                    pass
                except Exception:
                    pass
                payload = json.loads(raw) if raw else {}
            except Exception:
                payload = {"raw": raw.decode(errors="ignore")}
            inbox = Path("queue/webhook_inbox")
            inbox.mkdir(parents=True, exist_ok=True)
            (inbox / f"{name}_{time.time():.6f}.json").write_text(
                json.dumps({"surface": name, "payload": payload})
            )
            ledger.write("webhooks", {"surface": name, "size": len(raw)})
            return self._json(200, {"ok": True})
        if path == "/orders":
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                return self._json(400, {"error": "invalid json"})
            goal = (body.get("goal") or "").strip()
            if not goal:
                return self._json(400, {"error": "goal required"})
            tenant = (
                body.get("tenant_id") or self.headers.get("X-Tenant-Id") or "per_anon"
            )
            surface = body.get("surface") or "cli"
            parsed = llm.decompose(goal, tenant=tenant)
            oid = (
                "ord_"
                + hashlib.sha256(f"{tenant}:{goal}:{time.time()}".encode())
                .hexdigest()[:26]
                .upper()
            )
            order = {
                "order_id": oid,
                "tenant_id": tenant,
                "goal": parsed["goal"],
                "capabilities": parsed["capabilities"],
                "surface": surface,
                "chat_id": body.get("chat_id"),
                "raw": goal,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            save_order(order)
            ledger.write(
                "orders",
                {
                    "order_id": oid,
                    "tenant_id": tenant,
                    "surface": surface,
                    "goal": goal[:200],
                },
            )
            threading.Thread(target=process_order, args=(order,), daemon=True).start()
            return self._json(202, {"order_id": oid, "status_url": f"/orders/{oid}"})
        return self._json(404, {"error": "not found"})

    def log_message(self, *args):
        pass


INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Factory</title>
<style>
 body{font:14px/1.4 system-ui,sans-serif;max-width:720px;margin:4rem auto;padding:0 1rem;color:#111}
 input,textarea,button{font:inherit;width:100%;box-sizing:border-box;padding:.6rem;margin:.3rem 0;border:1px solid #ccc;border-radius:6px}
 button{background:#111;color:#fff;cursor:pointer}
 code{background:#f5f5f5;padding:2px 4px;border-radius:3px}
 pre{background:#f5f5f5;padding:1rem;border-radius:6px;overflow:auto}
</style></head>
<body>
<h1>Factory</h1>
<p>Express a need. The factory resolves it to terminals, runs the DAG, and delivers on your surface.</p>
<form id="f"><label>Tenant</label><input id="tenant" value="per_local" required>
<label>Surface</label><input id="surface" value="cli" required>
<label>Need</label><textarea id="goal" rows="3" required placeholder="watch competitors of example.com and alert if 10% dearer"></textarea>
<button type="submit">Place order</button></form>
<pre id="out">—</pre>
<script>
document.getElementById('f').addEventListener('submit', async e => {
  e.preventDefault();
  const body = {tenant_id: document.getElementById('tenant').value, surface: document.getElementById('surface').value, goal: document.getElementById('goal').value};
  const r = await fetch('/orders', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const j = await r.json();
  const out = document.getElementById('out');
  out.textContent = JSON.stringify(j, null, 2);
  if (j.order_id) setTimeout(refresh, 1500);
  async function refresh(){ const s = await (await fetch('/orders/'+j.order_id)).json(); out.textContent = JSON.stringify(s, null, 2); if (s.status !== 'delivered' && s.executions.length === 0) setTimeout(refresh, 2000); }
});
</script></body></html>"""


def main():
    port = int(os.environ.get("PORT", "8080"))
    try:
        reg = collect(ROOT)
        save(reg, REGISTRY_PATH)
        print(
            f"[server] registry: {reg['count']} terminals from {reg['repos_seen']} repos; warnings: {len(reg['warnings'])}"
        )
    except Exception as e:
        print(f"[server] WARNING: initial collect failed: {e}", file=sys.stderr)
    print(f"[server] listening on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
