"""
Real adapter for agent-foundry's af.cli.
Discovers subcommands and the accepted order shape. Caches result.
If the interface changes, this reports exactly what it tried.
"""

from __future__ import annotations

import json, subprocess, sys, os, tempfile
from pathlib import Path

_CACHED_SHAPE: dict | None = None


def _run(args, cwd, timeout=30):
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def discover_shape(af_dir: Path) -> dict:
    global _CACHED_SHAPE
    if _CACHED_SHAPE is not None:
        return _CACHED_SHAPE
    cli = af_dir / "af" / "cli.py"
    if not cli.exists():
        _CACHED_SHAPE = {"error": "af/cli.py not present"}
        return _CACHED_SHAPE
    r = _run([sys.executable, "-m", "af.cli", "--help"], af_dir)
    if r is None or r.returncode != 0:
        _CACHED_SHAPE = {
            "error": f"af.cli --help failed: {r.stderr[:200] if r else 'timeout'}"
        }
        return _CACHED_SHAPE
    help_text = (r.stdout or "") + (r.stderr or "")
    subcommands = [w for w in ("validate", "plan", "run") if w in help_text]
    fields_tried = [
        ["order_id", "goal", "terminals"],
        ["order_id", "goal", "capabilities"],
        ["order_id", "goal"],
        ["goal"],
    ]
    accepted_fields = None
    for fields in fields_tried:
        sample = {
            f: ("x" if f not in ("terminals", "capabilities") else []) for f in fields
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(sample, tf)
            path = tf.name
        try:
            probe = _run([sys.executable, "-m", "af.cli", "plan", path], af_dir)
            if probe and probe.returncode == 0:
                accepted_fields = fields
                break
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    _CACHED_SHAPE = {
        "subcommand": "run"
        if "run" in subcommands
        else (subcommands[0] if subcommands else None),
        "subcommands": subcommands,
        "order_fields": accepted_fields,
        "order_required": accepted_fields,
    }
    return _CACHED_SHAPE


def run_order(
    af_dir: Path, order: dict, dag_nodes: list[dict] | None = None
) -> tuple[str, str]:
    if not af_dir.exists():
        return "no_runtime", f"{af_dir} missing"
    cli = af_dir / "af" / "cli.py"
    if not cli.exists():
        return "no_runtime", "af/cli.py not present"
    shape = discover_shape(af_dir)
    if "error" in shape:
        return "no_runtime", shape["error"]
    if shape.get("subcommand") is None:
        return "no_runtime", f"no run subcommand; found: {shape.get('subcommands')}"
    if shape.get("order_fields") is None:
        return "shape_mismatch", "could not find a working order shape"
    fields = shape["order_fields"]
    order_obj: dict = {}
    for f in fields:
        if f == "order_id":
            order_obj[f] = order["order_id"]
        elif f == "goal":
            order_obj[f] = order["goal"]
        elif f == "terminals":
            order_obj[f] = [n["id"] for n in (dag_nodes or [])] or [
                t["id"] for t in order.get("capabilities", [])
            ]
        elif f == "capabilities":
            order_obj[f] = order.get("capabilities", [])
        else:
            order_obj[f] = None
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, dir=str(af_dir)
    ) as tf:
        json.dump(order_obj, tf)
        order_path = tf.name
    try:
        r = _run(
            [sys.executable, "-m", "af.cli", shape["subcommand"], order_path],
            af_dir,
            timeout=900,
        )
        if r is None:
            return "failed", "af.cli timeout"
        if r.returncode == 0:
            return "ok", (r.stdout or "").strip()[-400:]
        return "failed", f"rc={r.returncode}: {(r.stderr or '').strip()[:400]}"
    finally:
        try:
            os.unlink(order_path)
        except OSError:
            pass
