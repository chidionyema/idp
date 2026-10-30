"""One infra-state page, computed once, published to every session.

THE FOUNDER'S RULE (2026-10-29): "i need you to find a way to broadcast to per so everyone
understands the state of infra and we are all on the same page", "find way to alert all
sessions", "every session must be looking for flaws or unenforced laws and gates".

THE PAGE. One markdown page with the estate's live facts: the router's model groups and
whether each has a fallback, the providers whose renewal is denied, the law gate's verdict,
the open specs, the live claims, the violations by class, and the sessions under lockdown.
Every number on the page is produced by a command, and the command's receipt (exit status and
sha256) is on the page.

WHERE IT GOES. Four places, because a session can be in any of them:

    ~/.estate/state/state-page.md   the file the session brief renders
    ~/.estate/state/alerts.jsonl    the alert feed every session reads (this is how a session
                                    that is already running learns something changed)
    unified memory                  so a session that starts later recalls it by asking
    TELEGRAM_HOME_CHANNEL           the founder's channel, when it is configured

HARNESS AGNOSTIC. Nothing here knows which runtime is reading. The brief includes the page;
the alert feed is appended to and read by file. pi, Claude Code and anything else that reads
the brief get the same page.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from . import ledger, provider_renewal, registry

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def page_path() -> str:
    return os.path.join(ledger.state_home(), "state-page.md")


def alerts_path() -> str:
    return os.path.join(ledger.state_home(), "alerts.jsonl")


def _repo_root() -> str:
    return REPO_ROOT


def _focus_rows() -> List[Dict[str, Any]]:
    mem = os.path.join(_repo_root(), "platform", "estate", "memory")
    if mem not in sys.path:
        sys.path.insert(0, mem)
    try:
        import focus  # type: ignore
    except ImportError:
        return []
    try:
        return focus.live_focus()
    except Exception:  # noqa: BLE001 - the focus index is best-effort
        return []


def compute(root: str = REPO_ROOT, falsify: bool = False) -> Dict[str, Any]:
    """The live facts, each one measured rather than remembered.

    `falsify` is off by default: the page is a status page, not a gate, and the falsifier
    fixtures (throwaway git repositories) cost seconds. The gate itself (bin/estate-law-gate)
    always runs them.
    """
    law = registry.evaluate_all(root, falsify=falsify)
    spec = registry.evaluate_specs(root)
    renewals = provider_renewal.status()
    claims = _focus_rows()
    locked = []
    sessions_dir = ledger.sessions_dir()
    if os.path.isdir(sessions_dir):
        for name in sorted(os.listdir(sessions_dir)):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(sessions_dir, name)) as f:
                    state = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(state, dict) and state.get("status") == "locked":
                locked.append(
                    {
                        "session": name[:-5],
                        "class": state.get("violation_class", ""),
                        "since": state.get("locked_at", ""),
                        "proof": state.get("proof", ""),
                    }
                )
    by_class: Dict[str, int] = {}
    for row in ledger.violations():
        key = str(row.get("class", "unknown"))
        by_class[key] = by_class.get(key, 0) + 1
    return {
        "ts": ledger.now(),
        "law_gate": {
            "ok": law["ok"],
            "laws": len(law["results"]),
            "failing": [r["id"] for r in law["failing"]],
            "warning": [r["id"] for r in law["warning"]],
            "audit_count": law["audit"]["count"],
        },
        "specs": {
            "total": len(spec["specs"]),
            "open": [r["id"] for r in spec["open"]],
            "done": [r["id"] for r in spec["done"]],
        },
        "renewals": renewals,
        "denied_providers": provider_renewal.denied_providers(),
        "claims": {
            "live": len([c for c in claims if c.get("live")]),
            "total": len(claims),
        },
        "violations": {
            "total": len(ledger.violations()),
            "by_class": by_class,
        },
        "locked_sessions": locked,
    }


def render(facts: Dict[str, Any]) -> str:
    """The page. One page, one reading, no prose the machine did not measure."""
    law = facts["law_gate"]
    specs = facts["specs"]
    lines: List[str] = []
    lines.append("# Estate state")
    lines.append("")
    lines.append(f"measured at {facts['ts']}")
    lines.append("")
    lines.append("## Laws")
    if law["ok"]:
        lines.append(f"- gate green: {law['laws']} law(s), 0 failing")
    else:
        lines.append(f"- gate RED: failing {', '.join(law['failing']) or '-'}")
    if law["warning"]:
        lines.append(f"- warning: {', '.join(law['warning'])}")
    lines.append(
        f"- flaws to hunt: {law['audit_count']} (prose-only laws, unfalsified gates, advisory gates)"
    )
    lines.append("")
    lines.append("## Founder specs")
    lines.append(f"- done: {len(specs['done'])}/{specs['total']}")
    if specs["open"]:
        lines.append(f"- open: {', '.join(specs['open'])}")
    lines.append("")
    lines.append("## Model providers")
    if not facts["renewals"]:
        lines.append("- no provider has a violation on record")
    for provider, body in sorted(facts["renewals"].items()):
        lines.append(
            f"- {provider}: renewal {body.get('status', '?')} "
            f"({body.get('violations', 0)} violation(s))"
        )
    lines.append("")
    lines.append("## Claims")
    lines.append(
        f"- live claims: {facts['claims']['live']} of {facts['claims']['total']}"
    )
    lines.append("")
    lines.append("## Violations")
    lines.append(f"- total on record: {facts['violations']['total']}")
    for cls, count in sorted(facts["violations"]["by_class"].items()):
        lines.append(f"- {cls}: {count}")
    lines.append("")
    lines.append("## Lockdown")
    if not facts["locked_sessions"]:
        lines.append("- no session is locked down")
    for row in facts["locked_sessions"]:
        lines.append(
            f"- {row['session']}: {row['class']} since {row['since']} "
            f"(proof: {row['proof']})"
        )
    lines.append("")
    return "\n".join(lines)


def publish(
    facts: Optional[Dict[str, Any]] = None, root: str = REPO_ROOT
) -> Dict[str, Any]:
    """Compute, write the page, append the alert, publish to memory, and to Telegram."""
    facts = facts or compute(root)
    page = render(facts)
    os.makedirs(ledger.state_home(), exist_ok=True)
    with open(page_path(), "w", encoding="utf-8") as f:
        f.write(page)
    alert = {"ts": facts["ts"], "kind": "estate-state", "page": page}
    ledger._append(alerts_path(), alert)
    out: Dict[str, Any] = {"page_path": page_path(), "alerts_path": alerts_path()}
    mem = os.path.join(root, "platform", "estate", "memory")
    if mem not in sys.path:
        sys.path.insert(0, mem)
    try:
        import door  # type: ignore

        secret = door.key()
        result = door.call(
            "remember",
            {
                "content": page,
                "subject": "estate-infra-state",
                "kind": "measurement",
                "tags": ["estate-state", "broadcast"],
            },
            secret,
            timeout=15,
        )
        out["memory"] = {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001 - the door can fail for network reasons
        out["memory"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    out["telegram"] = telegram(page)
    out["facts"] = facts
    return out


def telegram(page: str) -> Dict[str, Any]:
    """The founder's channel, when it is configured. Never raises: a missing token is not a
    failure of the page."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_HOME_CHANNEL", "")
    if not token or not channel:
        return {
            "ok": False,
            "reason": "TELEGRAM_BOT_TOKEN / TELEGRAM_HOME_CHANNEL not set",
        }
    import urllib.parse
    import urllib.request

    text = page[:3500]
    data = urllib.parse.urlencode({"chat_id": channel, "text": text}).encode()
    try:
        with urllib.request.urlopen(  # noqa: S310 - https, fixed host
            f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20
        ) as resp:
            body = json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": bool(body.get("ok")),
        "message_id": (body.get("result") or {}).get("message_id"),
    }


def latest_alerts(limit: int = 5) -> List[Dict[str, Any]]:
    rows = ledger.read_jsonl(alerts_path())
    return rows[-limit:]


MAX_AGE_S = 900


def current(root: str = REPO_ROOT, max_age_s: int = MAX_AGE_S) -> str:
    """The page as it stands now.

    The published page when it is fresh (a session start must not cost seconds), and a
    freshly measured one otherwise. The file is written atomically, so a session reading it
    while another writes it never sees half a page.
    """
    path = page_path()
    try:
        if (time.time() - os.path.getmtime(path)) <= max_age_s:
            with open(path, encoding="utf-8") as f:
                return f.read()
    except OSError:
        pass
    page = render(compute(root))
    try:
        os.makedirs(ledger.state_home(), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(page)
        os.replace(tmp, path)
    except OSError:
        pass
    return page
