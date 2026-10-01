"""FleetView: is every key the estate expects actually arriving from Bitwarden?

Vendor and service keys travel Bitwarden Secrets Manager -> External Secrets (one `human-<vendor>`
ExternalSecret per vendor per namespace, platform/vendors/templates/externalsecrets.yaml) ->
a Kubernetes Secret the workload reads. The only place a failed hop showed up was
`kubectl get externalsecrets` and its events, which nobody watches; on 2026-10-01 eight bridges
were failing and the founder could not see one of them.

This reads the bridges and their UpdateFailed events, NAMES ONLY -- never a Secret, never a value
-- and turns them into one row per Bitwarden name:

  synced          the name is in Bitwarden and reaching every namespace that asks for it
  missing         Bitwarden has no secret by that exact name ("no secret found ... and name X");
                  the row carries X, the name to create
  stopped         it synced before and is failing now (status.refreshTime is the last success)
  unreachable     the cluster could not reach Bitwarden on the last attempt
  failing         not ready for a reason none of the above matched; the reason is shown

A bridge in `llm` (the router's own keys) that has been not-ready for longer than ALERT_AFTER_S is
an alert, and `publish_alerts` puts each new one on the news desk as it starts.

FleetView runs on the laptop (launchd), so it reads the cluster with the founder's kubectl, the
same way bin/litellm-local reads the bridged keys. A cluster that cannot be read is reported
unavailable with its reason, never as an empty board: zero rows would say "no keys are expected"
when the truth is "nobody could look".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CACHE_S = 30
ALERT_AFTER_S = int(os.environ.get("ESTATE_KEY_SYNC_ALERT_AFTER_S", "300"))
ALERT_NAMESPACES = ("llm",)
PREFIX = "human-"
NEWS_EVERY_S = 60

_cache: dict[str, Any] = {"at": 0.0, "body": None}

_MISSING = re.compile(r"no secret found for project id \S+ and name (\S+)")
_UNREACHABLE = re.compile(
    r"failed to perform http request|failed to do request|failed to list secrets"
    r"|connection refused|i/o timeout|context deadline exceeded|no such host",
    re.I,
)
# worst first: a row takes the worst state of its bridges
_RANK = {"missing": 0, "stopped": 1, "failing": 2, "unreachable": 3, "synced": 4}


def _kubectl() -> str | None:
    explicit = os.environ.get("KUBECTL_BIN")
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which("kubectl")
    if found:
        return found
    # launchd's PATH is minimal; these are where kubectl lives on the founder's laptop
    for p in (
        Path.home() / ".rd/bin/kubectl",
        Path("/opt/homebrew/bin/kubectl"),
        Path("/usr/local/bin/kubectl"),
    ):
        if p.exists():
            return str(p)
    return None


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _latest_failures(events: list[dict]) -> dict[tuple[str, str], dict]:
    """(namespace, bridge) -> its newest UpdateFailed event {message, at}, plus every Bitwarden
    name an event reported missing, each with when it was last reported ({name: at})."""
    out: dict[tuple[str, str], dict] = {}
    for e in events:
        obj = e.get("involvedObject") or {}
        if obj.get("kind") != "ExternalSecret" or not str(
            obj.get("name", "")
        ).startswith(PREFIX):
            continue
        key = (
            obj.get("namespace") or e.get("metadata", {}).get("namespace", ""),
            obj["name"],
        )
        at = _ts(
            e.get("lastTimestamp")
            or e.get("eventTime")
            or e.get("metadata", {}).get("creationTimestamp")
        )
        msg = str(e.get("message", ""))
        rec = out.setdefault(key, {"message": "", "at": None, "missing": {}})
        if rec["at"] is None or (at or 0) > rec["at"]:
            rec["message"], rec["at"] = msg, at or 0
        for name in _MISSING.findall(msg):
            rec["missing"][name] = max(at or 0, rec["missing"].get(name, 0))
    return out


def classify(bridge: dict, failure: dict | None) -> dict[str, Any]:
    """One bridge's state from its status and its newest failure event. Pure; no cluster access."""
    status = bridge.get("status") or {}
    ready = next(
        (c for c in status.get("conditions") or [] if c.get("type") == "Ready"), None
    )
    last_ok = _ts(status.get("refreshTime"))
    since = _ts(ready.get("lastTransitionTime")) if ready else None
    keys = [
        d["remoteRef"]["key"]
        for d in (bridge.get("spec") or {}).get("data") or []
        if (d.get("remoteRef") or {}).get("key")
    ]
    msg = (failure or {}).get("message", "")
    row: dict[str, Any] = {
        "namespace": bridge["metadata"]["namespace"],
        "bridge": bridge["metadata"]["name"],
        "keys": keys,
        "last_ok": last_ok,
        "since": since,
        "missing": [],
        "reason": None,
    }
    if ready and ready.get("status") == "True":
        row["state"] = "synced"
        # a blip that recovered is worth a mark, not a state
        recent = failure and failure.get("at") and since and failure["at"] > since - 1
        row["blip"] = bool(recent and _UNREACHABLE.search(msg))
        return row
    # A name Bitwarden said it does not hold, reported since the bridge last synced, is still a
    # fact while the bridge stays down: a Bitwarden outage on a later retry must not hide it.
    floor = last_ok or 0
    missing = sorted(
        n for n, at in ((failure or {}).get("missing") or {}).items() if at >= floor
    )
    reason = _reason(msg) or (ready or {}).get("message") or "not ready"
    if missing:
        row["state"] = "missing"
        row["missing"] = missing
        if not _MISSING.search(msg):
            reason = f"Bitwarden has no secret named {', '.join(missing)} (latest attempt: {reason[-120:]})"
    elif _UNREACHABLE.search(msg):
        row["state"] = "unreachable"
    elif last_ok:
        row["state"] = "stopped"
    else:
        row["state"] = "failing"
    row["reason"] = reason
    return row


def _reason(msg: str) -> str:
    """The cause, which ESO puts at the END of a long wrapped chain ("failed to get secret: ..." x3)."""
    tail = (msg.split("err: ", 1)[-1] if "err: " in msg else msg).strip()
    if len(tail) <= 200:
        return tail
    cut = tail[-200:]
    # start at a word, not mid-word
    return "…" + cut[cut.find(" ") + 1 :] if " " in cut else "…" + cut


def rows_by_name(bridges: list[dict]) -> list[dict[str, Any]]:
    """One row per Bitwarden name, worst state first."""
    by: dict[str, dict[str, Any]] = {}
    for b in bridges:
        for name in b["keys"]:
            r = by.setdefault(
                name,
                {
                    "name": name,
                    "state": "synced",
                    "namespaces": [],
                    "last_ok": None,
                    "reason": None,
                },
            )
            # a bridge failing on ANOTHER key's absence leaves this key unsynced too, but the
            # name to create is only the one Bitwarden reported missing
            state = b["state"]
            if state == "missing" and name not in b["missing"]:
                state = "failing"
                reason = (
                    f"blocked by missing {', '.join(b['missing'])} in the same bridge"
                )
            else:
                reason = b["reason"]
            r["namespaces"].append(
                {
                    "namespace": b["namespace"],
                    "bridge": b["bridge"],
                    "state": state,
                    "since": b["since"],
                }
            )
            if _RANK[state] < _RANK[r["state"]]:
                r["state"], r["reason"] = state, reason
            if b["last_ok"] and (r["last_ok"] is None or b["last_ok"] > r["last_ok"]):
                r["last_ok"] = b["last_ok"]
            r["blip"] = r.get("blip", False) or bool(b.get("blip"))
    return sorted(by.values(), key=lambda r: (_RANK[r["state"]], r["name"]))


def alerts(bridges: list[dict], now: float) -> list[dict[str, Any]]:
    """Router-key bridges not ready for longer than ALERT_AFTER_S."""
    out = []
    for b in bridges:
        if b["namespace"] not in ALERT_NAMESPACES or b["state"] == "synced":
            continue
        if b["since"] is not None and now - b["since"] < ALERT_AFTER_S:
            continue
        out.append(
            {
                "namespace": b["namespace"],
                "bridge": b["bridge"],
                "state": b["state"],
                "since": b["since"],
                "missing": b["missing"],
                "reason": b["reason"],
            }
        )
    return out


def build(externalsecrets: dict, events: dict, now: float) -> dict[str, Any]:
    """The board from the two kubectl reads. Pure, so the tests drive it with fixtures."""
    failures = _latest_failures(events.get("items") or [])
    bridges = [
        classify(i, failures.get((i["metadata"]["namespace"], i["metadata"]["name"])))
        for i in externalsecrets.get("items") or []
        if i["metadata"]["name"].startswith(PREFIX)
    ]
    rows = rows_by_name(bridges)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {
        "available": True,
        "at": now,
        "rows": rows,
        "counts": counts,
        "bridges": len(bridges),
        "alerts": alerts(bridges, now),
    }


def _read(tool: str, *args: str) -> dict:
    p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [tool, *args, "-o", "json", "--request-timeout=20s"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if p.returncode != 0:
        raise RuntimeError(
            (p.stderr or p.stdout).strip()[-300:] or f"rc={p.returncode}"
        )
    return json.loads(p.stdout)


def key_sync_status(now: float | None = None) -> dict[str, Any]:
    t = now if now is not None else time.time()
    if _cache["body"] is not None and t - _cache["at"] < CACHE_S:
        return _cache["body"]
    tool = _kubectl()
    if not tool:
        body: dict[str, Any] = {
            "available": False,
            "error": "kubectl not found on this host",
        }
    else:
        try:
            es = _read(tool, "get", "externalsecrets", "-A")
            try:
                ev = _read(
                    tool,
                    "get",
                    "events",
                    "-A",
                    "--field-selector",
                    "involvedObject.kind=ExternalSecret,reason=UpdateFailed",
                )
            except Exception:  # noqa: BLE001 - without events the states are coarser, not wrong
                ev = {"items": []}
            body = build(es, ev, t)
        except Exception as exc:  # noqa: BLE001 - unreadable is a fact the board shows
            body = {
                "available": False,
                "error": f"cannot read the cluster: {exc}"[:300],
            }
    _cache.update(at=t, body=body)
    return body


def _story(a: dict, at: str) -> dict[str, Any]:
    what = (
        f"missing {', '.join(a['missing'])} in Bitwarden"
        if a["state"] == "missing"
        else {"unreachable": "Bitwarden unreachable", "stopped": "stopped syncing"}.get(
            a["state"], "not syncing"
        )
    )
    since = (
        datetime.fromtimestamp(a["since"], timezone.utc).strftime("%H:%MZ")
        if a["since"]
        else "unknown"
    )
    entity = f"key-sync/{a['namespace']}/{a['bridge']}"
    headline = f"Router key {a['bridge']} in {a['namespace']}: {what} since {since}"
    return {
        "id": hashlib.sha256(
            f"{entity}|{a['state']}|{a['since']}".encode()
        ).hexdigest()[:16],
        "channel": "metrics",
        "source": "key-sync",
        "severity": "warning",
        "state": "reported",
        "headline": headline,
        "anchor": f"The router's {a['bridge']} key is not reaching the {a['namespace']} namespace: {what}.",
        "entity": entity,
        "evidence": [str(a["reason"] or "")[:200]],
        "score": 3.0,
        "count": 1,
        "breaking": True,
        "first_at": at,
        "at": at,
    }


async def publish_alerts(nats_url: str) -> None:
    """Every NEWS_EVERY_S: publish each alert once, when it starts. Never raises."""
    import asyncio as _asyncio
    import logging

    from fleetview_backend import nats_adapter

    log = logging.getLogger(__name__)
    sent: set[str] = set()
    while True:
        try:
            import nats

            body = await _asyncio.to_thread(key_sync_status)
            at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            fresh = [
                s
                for s in (_story(a, at) for a in body.get("alerts") or [])
                if s["id"] not in sent
            ]
            if fresh:
                nc = await nats.connect(
                    nats_adapter._nats_url(nats_url),
                    max_reconnect_attempts=nats_adapter.CONNECT_MAX_RECONNECT_ATTEMPTS,
                    reconnect_time_wait=nats_adapter.CONNECT_RECONNECT_TIME_WAIT,
                    connect_timeout=nats_adapter.CONNECT_TIMEOUT,
                )
                try:
                    for s in fresh:
                        await nc.publish(
                            f"estate.news.story.{s['channel']}", json.dumps(s).encode()
                        )
                        sent.add(s["id"])
                        log.info("fleetview.key_sync_alert %s", s["headline"])
                finally:
                    await nc.drain()
        except Exception as exc:  # noqa: BLE001 - the news desk never takes the backend down
            log.warning("fleetview.key_sync_alert_failed %s", exc)
        await _asyncio.sleep(NEWS_EVERY_S)
