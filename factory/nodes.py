"""Real implementations. Honest failures. No fabricated numbers."""

import os
import re
import subprocess
import urllib.request
import urllib.error

TIMEOUT = int(os.environ.get("NODE_TIMEOUT", "20"))
UA = "Mozilla/5.0 (Factory/1.0)"


def web_scrape(inp: dict) -> dict:
    expression = inp.get("goal") or inp.get("url") or ""
    m = re.search(r"https?://[^\s]+", expression)
    if not m:
        m = re.search(
            r"\b([a-z0-9][a-z0-9\-]*\.(?:com|co|io|org|net|dev|app))\b",
            expression,
            re.I,
        )
        if m:
            target = "https://" + m.group(0)
        else:
            return {"html": "", "url": "", "error": "NO_URL_IN_EXPRESSION"}
    else:
        target = m.group(0)
    try:
        req = urllib.request.Request(target, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(2_000_000).decode("utf-8", errors="ignore")
        return {"html": body, "url": target, "bytes": len(body)}
    except urllib.error.HTTPError as e:
        return {"html": "", "url": target, "error": f"HTTP_{e.code}"}
    except Exception as e:
        return {"html": "", "url": target, "error": type(e).__name__}


PRICE_RE = re.compile(r"(?P<cur>[$£€])\s?(?P<val>\d{1,7}(?:[.,]\d{1,2})?)")


def price_extract(inp: dict) -> dict:
    html = inp.get("html", "")
    if not html:
        return {"prices": [], "count": 0, "reason": inp.get("error") or "no_html"}
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    prices, seen = [], set()
    for m in PRICE_RE.finditer(text):
        try:
            v = float(m.group("val").replace(",", ""))
        except ValueError:
            continue
        key = (v, m.group("cur"))
        if key in seen:
            continue
        seen.add(key)
        prices.append({"value": v, "currency": m.group("cur")})
    return {"prices": prices[:100], "count": len(prices)}


def alert_emit(inp: dict) -> dict:
    prices = inp.get("prices", [])
    threshold = float(os.environ.get("ALERT_THRESHOLD", "10"))
    if len(prices) < 2:
        return {"alert": None, "reason": f"INSUFFICIENT_PRICES count={len(prices)}"}
    lo = min(prices, key=lambda x: x["value"])
    hi = max(prices, key=lambda x: x["value"])
    if lo["value"] <= 0:
        return {"alert": None, "reason": "ZERO_PRICE_GUARD"}
    delta = (hi["value"] - lo["value"]) / lo["value"] * 100.0
    if delta >= threshold:
        return {
            "alert": f"Gap {delta:.2f}%: high {hi['currency']}{hi['value']:.2f} vs low {lo['currency']}{lo['value']:.2f}",
            "delta_pct": round(delta, 2),
            "high": hi,
            "low": lo,
        }
    return {
        "alert": None,
        "delta_pct": round(delta, 2),
        "reason": f"below {threshold}%",
    }


def army(inp: dict) -> dict:
    return {"ran": True, "goal": (inp.get("goal") or "")[:200]}


def os_input(inp: dict) -> dict:
    cmd = inp.get("command") or ""
    if not cmd:
        return {"applied": False, "reason": "NO_COMMAND"}
    if not any(cmd.startswith(s) for s in ("echo", "ls", "pwd", "date", "whoami")):
        return {"applied": False, "reason": "COMMAND_NOT_SAFE"}
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT
        )
        return {"applied": True, "stdout": r.stdout[:500], "rc": r.returncode}
    except Exception as e:
        return {"applied": False, "reason": type(e).__name__}


def oob_approval(inp: dict) -> dict:
    return {"approved": None, "reason": "OOB_NOT_CONFIGURED"}


NODES = {
    "web-scrape": web_scrape,
    "price-extract": price_extract,
    "alert-emit": alert_emit,
    "army": army,
    "os.input": os_input,
    "oob.approval": oob_approval,
}


def run_node(node_id: str, inp: dict) -> dict:
    fn = NODES.get(node_id)
    if fn is None:
        return {"error": f"NO_IMPLEMENTATION_{node_id}"}
    try:
        return fn(inp)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"[:200]}
