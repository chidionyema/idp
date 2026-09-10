"""HolmesGPT, made active: the estate asks its own investigator, unprompted.

HolmesGPT has run in the robusta namespace since 2026-09-05 with its own router
key, and until now nothing could ask it anything. It is an investigator you talk
to, and the estate had no mouth. This module gives it one.

WHY IT IS NOT A ROBUSTA PLAYBOOK. Robusta ships an `ask_holmes` action and can
fire it from a schedule, and that was the first road tried. It is a dead end
here, measured in the upstream source on 2026-09-05: the action wraps Holmes'
answer in a HolmesResultsBlock, and only two things in Robusta know how to
render that block -- the Slack sender and the uploader to the Robusta SaaS
database (`gh search code 'HolmesResultsBlock repo:robusta-dev/robusta'`: five
files, neither the Telegram sink nor the shared markdown transformer among
them). The estate has neither Slack nor the SaaS UI, so the Telegram sink would
post a title with an empty body and the whole investigation would be dropped in
silence. Holmes' own scheduled-prompts engine is no better: its executor starts
only `if self.dal.enabled`, the same SaaS data layer
(holmes/core/scheduled_prompts/executor.py).

So the estate asks Holmes directly over its documented HTTP API and delivers the
answer through the notify layer it already runs. Three services that already
exist, no new component and no shell script:

  kps-alertmanager.monitoring   what is on fire right now (GET /api/v2/alerts)
  robusta-holmes.robusta        the investigator      (POST /api/chat -> analysis)
  apprise.notify                publish once, deliver everywhere

ACTIVE, NOT NOISY. The sensor investigates only when something is actually
firing, and Dagster's own run_key deduplication means one distinct set of firing
alerts is investigated exactly once, however long it burns. A quiet cluster
costs nothing: no run, no model call, no message. That matters because the
investigator's brain is the estate router and its budget is real
(AGENTS.md [budget.usd_per_day] litellm = 3.0).

Every message names its sender, because several programs share the founder's
one chat and a message that does not say who is speaking is a defect.
"""

import hashlib
import os
from typing import Any, Dict, List

import requests

from dagster import (
    Config,
    DefaultSensorStatus,
    Failure,
    RunRequest,
    SkipReason,
    job,
    op,
    sensor,
)

# Cluster DNS, measured 2026-09-05 (`get svc -n monitoring/robusta/notify`):
# kps-alertmanager 9093, robusta-holmes 80 -> 5050, apprise 8000. Every one is
# overridable by environment so this file names no machine (LAW 46).
ALERTMANAGER_URL = os.environ.get(
    "ESTATE_ALERTMANAGER_URL", "http://kps-alertmanager.monitoring.svc:9093"
)
HOLMES_URL = os.environ.get(
    "ESTATE_HOLMES_URL", "http://robusta-holmes.robusta.svc.cluster.local"
)
APPRISE_URL = os.environ.get(
    "ESTATE_APPRISE_URL", "http://apprise.notify.svc.cluster.local:8000"
)
NOTIFY_CHANNEL = os.environ.get("ESTATE_NOTIFY_CHANNEL", "founder-telegram")

# The sender's name, first thing in every message it sends.
SENDER = "HOLMESGPT"

# Watchdog fires forever on purpose -- it is how the estate proves the alert path
# is alive -- and InfoInhibitor exists only to suppress other alerts. Neither is
# a thing to investigate.
NEVER_INVESTIGATE = {"Watchdog", "InfoInhibitor", "InfoInhibitorAlert"}

POLL_SECONDS = int(os.environ.get("ESTATE_HOLMES_POLL_SECONDS", "300"))
HOLMES_TIMEOUT_S = int(os.environ.get("ESTATE_HOLMES_TIMEOUT_SECONDS", "600"))
HTTP_TIMEOUT_S = int(os.environ.get("ESTATE_HOLMES_HTTP_TIMEOUT_SECONDS", "20"))

# Telegram refuses a message over 4096 characters and Apprise does not split for
# us, so the analysis is cut with a line that says it was cut.
BODY_LIMIT = 3500


def _get_json(url: str, timeout: int) -> Any:
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _post_json(url: str, payload: dict, timeout: int) -> Any:
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        return r.text


def firing_alerts(url: str = ALERTMANAGER_URL) -> List[Dict[str, str]]:
    """The alerts Alertmanager says are firing now, flattened to what a person reads.

    Alertmanager's v2 API returns every alert including the silenced and inhibited
    ones, so both are dropped here: an alert somebody has already silenced is not
    something to wake the founder about.
    """
    query = "active=true&silenced=false&inhibited=false"
    out = []
    for a in _get_json(f"{url}/api/v2/alerts?{query}", HTTP_TIMEOUT_S) or []:
        labels = a.get("labels") or {}
        name = labels.get("alertname", "")
        if not name or name in NEVER_INVESTIGATE:
            continue
        if (a.get("status") or {}).get("state") != "active":
            continue
        out.append(
            {
                "alertname": name,
                "namespace": labels.get("namespace", "")
                or labels.get("object_namespace", ""),
                "severity": labels.get("severity", ""),
                "summary": (a.get("annotations") or {}).get("summary", ""),
            }
        )
    return out


def alert_fingerprint(alerts: List[Dict[str, str]]) -> str:
    """One id for one situation.

    Dagster refuses a second run for a run_key it has already seen, so this is
    what stops the same outage being investigated every five minutes for a day.
    It is built from what is firing, not from when: the same set of alerts is
    the same situation, and a new alert joining makes it a new one worth a
    fresh look.
    """
    key = "|".join(sorted(f"{a['alertname']}/{a['namespace']}" for a in alerts))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def question(alerts: List[Dict[str, str]]) -> str:
    lines = [
        f"- {a['alertname']}"
        + (f" in namespace {a['namespace']}" if a["namespace"] else "")
        + (f": {a['summary']}" if a["summary"] else "")
        for a in alerts
    ]
    return (
        "These alerts are firing on this Kubernetes cluster right now:\n"
        + "\n".join(lines)
        + "\n\nInvestigate. Use the cluster and Prometheus tools to find out what is "
        "actually wrong, then answer in this shape and nothing else:\n"
        "WHAT IS WRONG: one sentence.\n"
        "WHY: the root cause, with the specific evidence you found.\n"
        "FIX: the exact change that ends it.\n"
        "Be concise; this is read on a phone. Do not repeat the alert text back."
    )


def ask_holmes(prompt: str, url: str = HOLMES_URL) -> str:
    answer = _post_json(f"{url}/api/chat", {"ask": prompt}, HOLMES_TIMEOUT_S)
    if isinstance(answer, dict) and answer.get("analysis"):
        return str(answer["analysis"]).strip()
    raise Failure(f"HolmesGPT answered without an analysis: {str(answer)[:300]}")


def publish(
    title: str, body: str, url: str = APPRISE_URL, channel: str = NOTIFY_CHANNEL
) -> None:
    if len(body) > BODY_LIMIT:
        body = (
            body[:BODY_LIMIT]
            + "\n\n[cut here; the whole answer is in the Dagster run log]"
        )
    _post_json(
        f"{url}/notify/{channel}",
        {"title": title, "body": body, "type": "warning", "format": "text"},
        HTTP_TIMEOUT_S,
    )


# --- MUM-285: persist the Holmes finding so it never goes void. ---
#
# A real Holmes spend whose answer only ever publishes to a chat is a finding
# that scrolls past: the moment the channel is muted the model-spend is gone.
# A down or misconfigured memory store is logged and the investigation is
# allowed to complete; a finder that double-pages the founder because its
# note-taker is offline is worse than a finder that lets the note vanish for
# this run. Endpoint, payload shape, env keys, byte ceiling and fail-open
# posture mirror mcp/plugins/estate_memory.do_remember exactly, so a finding
# written here is indistinguishable to the recall side.


MEMORY_TIMEOUT_S = float(os.environ.get("ESTATE_MEMORY_TIMEOUT_S", "5"))
MEMORY_BYTE_CEILING = int(os.environ.get("ESTATE_MEMORY_BYTE_CEILING", "8000"))
MEMORY_URL = os.environ.get("ESTATE_MEMORY_URL", "").strip()
MEMORY_ORG = os.environ.get("ESTATE_MEMORY_ORG", "default")
MEMORY_BANK = os.environ.get("ESTATE_MEMORY_BANK", "hermes")


def _memory_endpoint() -> str:
    base = MEMORY_URL.rstrip("/")
    return f"{base}/v1/{MEMORY_ORG}/banks/{MEMORY_BANK}/memories"


def _truncate_to_bytes(text: str, ceiling: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= ceiling:
        return text
    return raw[:ceiling].decode("utf-8", "ignore") + "\n\n[truncated to byte ceiling]"


def _build_finding(
    analysis: str, fingerprint: str, alert_names: List[str]
) -> Dict[str, Any]:
    """The structured finding the op persists: subject, kind, tags and the
    analysis body, in the same shape ``mcp/plugins/estate_memory.do_remember``
    accepts."""
    names = sorted({str(n).strip() for n in (alert_names or []) if str(n).strip()})
    subject = "Holmes finding for " + (", ".join(names) if names else "firing alerts")
    tags = ["holmes", "finding", "alert"]
    if fingerprint:
        tags.append("fp-" + str(fingerprint).lower())
    for n in names:
        tags.append("alert:" + n.lower())
    return {
        "analysis": analysis,
        "subject": subject,
        "kind": "incident.investigation",
        "tags": tags,
        "fingerprint": fingerprint or "",
    }


def _retain(
    analysis: str,
    subject: str,
    kind: str,
    tags: List[str],
    fingerprint: str,
) -> Dict[str, Any]:
    """POST one Holmes finding to the estate memory bank. Never raises.

    Returns ``{"written": True, ...}`` on success or ``{"written": False,
    "error": "..."}`` on every failure path. The investigation caller logs
    ``error`` and continues.
    """
    import json as _json
    import urllib.error as _urllib_error
    import urllib.request as _urllib_request

    if not MEMORY_URL:
        return {"written": False, "error": "ESTATE_MEMORY_URL is unset"}
    if not analysis or not analysis.strip():
        return {"written": False, "error": "analysis is empty; nothing to retain"}

    clean_tags = sorted(
        {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    )
    tag_field = ",".join(clean_tags) if clean_tags else None
    body = _truncate_to_bytes(analysis.strip(), MEMORY_BYTE_CEILING)
    payload = {
        "items": [
            {
                "content": body,
                "context": subject or None,
                "metadata": {
                    "subject": subject,
                    "kind": kind,
                    "tags": tag_field,
                    "fingerprint": fingerprint,
                    "source": "holmes_watch",
                },
            }
        ],
        "async": True,
    }

    endpoint = _memory_endpoint()
    if not endpoint.startswith(("http://", "https://")):
        return {"written": False, "error": "ESTATE_MEMORY_URL is not http(s)"}

    try:
        request = _urllib_request.Request(  # noqa: S310
            endpoint,
            data=_json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with _urllib_request.urlopen(request, timeout=MEMORY_TIMEOUT_S) as response:  # noqa: S310
            response.read()
        return {
            "written": True,
            "endpoint": endpoint,
            "fingerprint": fingerprint,
        }
    except (_urllib_error.URLError, TimeoutError, OSError, ValueError) as exc:  # type: ignore[name-defined]
        return {
            "written": False,
            "error": "memory store unreachable: "
            + type(exc).__name__
            + ": "
            + str(exc),
        }


class InvestigationConfig(Config):
    alerts: List[Dict[str, str]] = []
    fingerprint: str = ""


@op(
    name="investigate_firing_alerts",
    description=(
        "Asks HolmesGPT what is actually wrong with the alerts Alertmanager says are "
        "firing, and publishes its answer to the founder's channel through Apprise."
    ),
)
def investigate_firing_alerts(context, config: InvestigationConfig) -> None:
    alerts = config.alerts
    if not alerts:
        context.log.info("nothing firing; nothing to investigate")
        return

    names = ", ".join(sorted({a["alertname"] for a in alerts}))
    context.log.info("asking HolmesGPT about %s alert(s): %s", len(alerts), names)
    analysis = ask_holmes(question(alerts))
    context.log.info(analysis)

    publish(f"{SENDER} - investigated {names}", analysis)
    context.log.info("published to %s/%s", APPRISE_URL, NOTIFY_CHANNEL)

    # Persist the finding so it never goes void (MUM-285). A down memory store
    # is logged and the investigation is allowed to complete; a finder that
    # double-pages the founder because its note-taker is offline is worse than
    # a finder that takes the investigation and lets the note vanish for this run.
    finding = _build_finding(
        analysis=analysis,
        fingerprint=config.fingerprint,
        alert_names=[a["alertname"] for a in alerts],
    )
    written = _retain(
        finding["analysis"],
        subject=finding["subject"],
        kind=finding["kind"],
        tags=finding["tags"],
        fingerprint=finding["fingerprint"],
    )
    if written["written"]:
        context.log.info("finding retained (fingerprint %s)", finding["fingerprint"])
    else:
        context.log.warning("finding NOT retained: %s", written["error"])


@job(
    name="holmes_investigation",
    description=(
        "HolmesGPT investigates whatever is firing and sends what it found to the "
        "founder, and persists its analysis to the estate memory bank so the finding "
        "is recoverable later (MUM-285). Started by holmes_alert_sensor, never on a "
        "clock: a quiet cluster costs nothing."
    ),
    metadata={
        "asks": f"{HOLMES_URL}/api/chat",
        "reads": f"{ALERTMANAGER_URL}/api/v2/alerts",
        "publishes to": f"{APPRISE_URL}/notify/{NOTIFY_CHANNEL}",
        "retains to": "$ESTATE_MEMORY_URL/v1/$ESTATE_MEMORY_ORG/banks/$ESTATE_MEMORY_BANK/memories",
        "defined in": "scheduler/estate_scheduler/holmes_watch.py",
    },
    tags={"estate/label": "ai.estate.holmes-investigation", "estate/owner": "estate"},
)
def holmes_investigation():
    investigate_firing_alerts()


@sensor(
    name="holmes_alert_sensor",
    job=holmes_investigation,
    minimum_interval_seconds=POLL_SECONDS,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        f"Every {POLL_SECONDS}s, reads the alerts Alertmanager says are firing and starts one "
        "HolmesGPT investigation for each distinct set of them. Skips while the cluster is "
        "quiet, and never investigates the same set twice."
    ),
)
def holmes_alert_sensor(context):
    try:
        alerts = firing_alerts()
    except (requests.RequestException, ValueError) as e:
        return SkipReason(f"Alertmanager did not answer: {e}")
    if not alerts:
        return SkipReason("nothing is firing")

    key = alert_fingerprint(alerts)
    context.log.info(
        "firing: %s (fingerprint %s)", ", ".join(a["alertname"] for a in alerts), key
    )
    return RunRequest(
        run_key=key,
        run_config={
            "ops": {
                "investigate_firing_alerts": {
                    "config": {"alerts": alerts, "fingerprint": key}
                }
            }
        },
        tags={"estate/alert-fingerprint": key},
    )
