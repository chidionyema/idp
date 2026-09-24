import json
import os
import urllib.request


def decompose(expression: str, tenant: str) -> dict:
    api, key = os.environ.get("LLM_ENDPOINT"), os.environ.get("LLM_API_KEY")
    if api and key:
        try:
            return _call(
                api, key, os.environ.get("LLM_MODEL", "gpt-4o-mini"), expression
            )
        except Exception:
            pass
    return _heuristic(expression)


def _call(api, key, model, expression):
    prompt = (
        "Parse the customer expression into a factory order. JSON only.\n"
        '{"goal":"...", "capabilities":[{"id":"...","mode":"function"}]}\n'
        "Capability ids available: web-scrape, price-extract, alert-emit, army, os.input, oob.approval.\n"
        f"Expression: {expression}"
    )
    req = urllib.request.Request(
        f"{api}/chat/completions",
        method="POST",
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
        ).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    return json.loads(out["choices"][0]["message"]["content"])


def _heuristic(expression: str) -> dict:
    e = expression.lower()
    if any(w in e for w in ("price", "competitor", "cheaper", "dearer", "watch")):
        caps = [
            {"id": "web-scrape", "mode": "function"},
            {"id": "price-extract", "mode": "function"},
            {"id": "alert-emit", "mode": "function"},
        ]
    elif any(w in e for w in ("click", "type", "run", "execute")):
        caps = [{"id": "os.input", "mode": "function"}]
    elif any(w in e for w in ("approve", "authorize")):
        caps = [{"id": "oob.approval", "mode": "function"}]
    else:
        caps = [{"id": "army", "mode": "function"}]
    return {"goal": expression[:200], "capabilities": caps}
