#!/usr/bin/env python3
"""consult.gemini: ask Gemini for an architectural review of the estate, through the router.

Usage (via the intent): consult_gemini.py question=<text> [files=a,b] [model=gemini/gemini-3.8-flash]
                        [max_bytes=400000] [timeout=85]

One door. The call goes to the estate router (llm.mumchimp.com), never to Google direct, so
spend lands on the router ledger and under its daily ceiling. If the consultant lane refuses or
is slow the helper retries once on the neutral `default` lane and SAYS SO in the output: a
consultant that quietly answers as a different model is worse than one that fails loudly.

The reply is saved to docs/reviews/<date>-consult-<slug>.md in the repo so it outlives the
terminal, and printed with a footer naming the model that actually answered.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROUTER = os.environ.get("ESTATE_ROUTER_URL", "https://llm.mumchimp.com")
# The router's `gemini` lane is pinned to gemini-2.5-flash, which Google now 404s for new users
# (measured 2026-10-30), so it silently falls back to MiniMax. Ask for the live model by name.
DEFAULT_MODEL = "gemini/gemini-3.8-flash"
FALLBACK_MODEL = "default"
DEFAULT_MAX_BYTES = 400_000
SYSTEM = (
    "You are the long-term architectural consultant to a one-founder engineering estate. "
    "Answer from the context supplied. Name trade-offs and a measurable baseline delta, say "
    "what you could not verify, and never invent files or numbers."
)


class ConsultError(Exception):
    """A named failure: the caller gets the reason, not a hang."""


def parse_args(argv):
    out = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k] = v
    return out


def build_context(paths, max_bytes, brief=""):
    """Join brief + files under an explicit byte budget; say so when something is cut."""
    parts, used, cut = [], 0, []
    if brief:
        b = brief.encode()[: max_bytes // 4].decode(errors="ignore")
        parts.append(f"## estate brief\n{b}")
        used += len(b.encode())
    for p in paths:
        path = Path(p).expanduser()
        if not path.is_file():
            raise ConsultError(f"context file not found: {p}")
        raw = path.read_bytes()
        room = max_bytes - used
        if room <= 0:
            cut.append(p)
            continue
        chunk = raw[:room].decode(errors="ignore")
        note = (
            "" if len(raw) <= room else f"\n[TRUNCATED at {room} of {len(raw)} bytes]"
        )
        if note:
            cut.append(p)
        parts.append(f"## {p}\n{chunk}{note}")
        used += len(chunk.encode())
    if cut:
        parts.append("[context budget reached; cut or skipped: " + ", ".join(cut) + "]")
    return "\n\n".join(parts), cut


def _post(url, key, payload, timeout):
    req = urllib.request.Request(  # noqa: S310 - ROUTER is an https constant, not user input
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ConsultError(
            f"router answered HTTP {e.code}: {e.read()[:200].decode(errors='ignore')}"
        ) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ConsultError(f"router unreachable or timed out: {e}") from e


def ask(model, question, context, key, timeout, post=_post):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"{question}\n\n---\n{context}" if context else question,
            },
        ],
    }
    d = post(f"{ROUTER}/v1/chat/completions", key, body, timeout)
    try:
        text = d["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ConsultError(f"router reply had no answer: {str(d)[:200]}") from e
    if not text or not text.strip():
        raise ConsultError("router reply was empty")
    return text, d.get("model", model)


def consult(question, files, model, max_bytes, timeout, key, brief="", post=_post):
    """Returns (answer, replied_model, requested_model, notes)."""
    if not question.strip():
        raise ConsultError("question is empty")
    if not key:
        raise ConsultError(
            "no router key: set LITELLM_API_KEY or ESTATE_AGENT_KEY (by name, from the vault)"
        )
    context, cut = build_context(files, max_bytes, brief)
    notes = [f"context cut or skipped: {', '.join(cut)}"] if cut else []
    try:
        text, replied = ask(model, question, context, key, timeout, post)
    except ConsultError as first:
        if model == FALLBACK_MODEL:
            raise
        notes.append(f"{model} failed ({first}); retried on {FALLBACK_MODEL}")
        text, replied = ask(FALLBACK_MODEL, question, context, key, timeout, post)
    return text, replied, model, notes


def save(out_dir, question, text, replied, requested, notes, now=None):
    now = now or datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")[:48] or "consult"
    path = Path(out_dir) / f"{now:%Y-%m-%d}-consult-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    footer = f"\n\n---\nanswered by: {replied} (asked: {requested})"
    if notes:
        footer += "\n" + "\n".join(f"note: {n}" for n in notes)
    path.write_text(f"# Consult: {question}\n\n{text}{footer}\n")
    return path, footer


def _brief():
    try:
        r = subprocess.run(
            ["growmos", "context", "--brief"],  # noqa: S607 - PATH lookup is intended
            capture_output=True,
            text=True,
            timeout=20,
        )
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _repo_reviews_dir():
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],  # noqa: S607 - PATH lookup is intended
            capture_output=True,
            text=True,
            timeout=10,
        )
        if top.returncode == 0:
            return Path(top.stdout.strip()) / "docs" / "reviews"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path.home() / ".estate" / "consults"


def main(argv):
    a = parse_args(argv)
    files = [f for f in a.get("files", "").split(",") if f]
    key = os.environ.get("LITELLM_API_KEY") or os.environ.get("ESTATE_AGENT_KEY", "")
    try:
        text, replied, requested, notes = consult(
            a.get("question", ""),
            files,
            a.get("model", DEFAULT_MODEL),
            int(a.get("max_bytes", DEFAULT_MAX_BYTES)),
            int(a.get("timeout", 85)),
            key,
            brief=_brief(),
        )
    except ConsultError as e:
        print(f"consult.gemini FAILED: {e}")
        return 2
    path, footer = save(
        _repo_reviews_dir(), a["question"], text, replied, requested, notes
    )
    print(text + footer)
    print(f"saved: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
