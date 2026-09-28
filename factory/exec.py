import json
import subprocess
import sys
from datetime import datetime, timezone
from .nodes import run_node
from . import ledger


def af_run(order: dict, repos_root) -> tuple[str, str]:
    af = repos_root / "agent-foundry"
    cli = af / "af" / "cli.py"
    if not cli.exists():
        return "no_runtime", "af.cli not present"
    order_path = af / f".{order['order_id']}.json"
    order_path.write_text(
        json.dumps({"order_id": order["order_id"], "goal": order["goal"]})
    )
    try:
        r = subprocess.run(
            [sys.executable, "-m", "af.cli", "run", str(order_path)],
            cwd=af,
            capture_output=True,
            text=True,
            timeout=900,
        )
        return ("ok" if r.returncode == 0 else "failed"), (
            r.stdout or r.stderr or ""
        ).strip()[-400:]
    except Exception as e:
        return "failed", f"{type(e).__name__}: {e}"
    finally:
        try:
            order_path.unlink()
        except FileNotFoundError:
            pass


def run_dag(order: dict, resolved: list[dict], repos_root) -> dict:
    started = datetime.now(timezone.utc)
    ctx = {
        "goal": order["goal"],
        "order_id": order["order_id"],
        "tenant": order["tenant_id"],
    }
    steps = []
    for t in resolved:
        nid = t["id"]
        inp = {**ctx}
        for s in steps:
            inp.update(s.get("output", {}) or {})
        out = run_node(nid, inp)
        ok = "error" not in out or out.get("error") is None
        steps.append({"terminal": nid, "ok": ok, "output": out})
        ledger.write(
            "steps",
            {
                "order_id": order["order_id"],
                "terminal": nid,
                "ok": ok,
                "error": out.get("error"),
            },
        )

    runtime_outcome, runtime_detail = af_run(order, repos_root)
    final = steps[-1]["output"] if steps else {}

    if runtime_outcome == "ok" and all(s["ok"] for s in steps):
        outcome = "ok"
    elif runtime_outcome == "no_runtime":
        outcome = "no_runtime"
    else:
        outcome = "partial"

    return {
        "order_id": order["order_id"],
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime_outcome,
        "runtime_detail": runtime_detail,
        "outcome": outcome,
        "steps": steps,
        "final": final,
    }
