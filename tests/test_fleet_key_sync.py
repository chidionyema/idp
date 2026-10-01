"""Key sync on Fleet (backstage/plugins/fleetview-backend/src/fleetview_backend/key_sync.py).

key_sync turns ExternalSecret status + UpdateFailed events into one row per Bitwarden name. The
messages below are the real strings External Secrets wrote on 2026-10-01. No cluster is read.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src" / "fleetview_backend"


def _member(name: str):
    full = f"fleetview_backend.{name}"
    if full in sys.modules:
        return sys.modules[full]
    pkg = sys.modules.setdefault(
        "fleetview_backend", types.ModuleType("fleetview_backend")
    )
    if not hasattr(pkg, "__path__"):
        pkg.__path__ = [str(PKG)]
    spec = importlib.util.spec_from_file_location(full, PKG / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "fleetview_backend"
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    setattr(pkg, name, mod)
    return mod


key_sync = _member("key_sync")

NOW = 1_790_900_000.0  # 2026-10-02T...Z
P = "18e57b2f-d5c6-4c0b-9ba9-b4b900e1d792"


def _iso(t: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _es(
    ns,
    name,
    keys,
    ready,
    since,
    refresh=None,
    msg="could not get secret data from provider",
):
    status = {
        "conditions": [
            {
                "type": "Ready",
                "status": "True" if ready else "False",
                "message": "secret synced" if ready else msg,
                "lastTransitionTime": _iso(since),
            }
        ]
    }
    if refresh:
        status["refreshTime"] = _iso(refresh)
    return {
        "metadata": {"namespace": ns, "name": name},
        "spec": {"data": [{"secretKey": k, "remoteRef": {"key": k}} for k in keys]},
        "status": status,
    }


def _ev(ns, name, message, at):
    return {
        "metadata": {"namespace": ns},
        "involvedObject": {"kind": "ExternalSecret", "namespace": ns, "name": name},
        "message": message,
        "lastTimestamp": _iso(at),
    }


MISSING_TWILIO = (
    "error processing spec.data[2] (key: PUBLIC_SERVER_URL), err: no secret found for project id "
    f"{P} and name PUBLIC_SERVER_URL"
)
UNREACHABLE = (
    "error processing spec.data[0] (key: GROQ_API_KEY), err: failed to get secret: failed to get all "
    "secrets: failed to list secrets: failed to perform http request, got response: failed to get "
    "secret: API error: Received error message from server: [503 Service Unavailable] upstream "
    "connect error or disconnect/reset before headers. reset reason: connection timeout"
)
TIMEOUT = (
    "error processing spec.data[0] (key: COHERE_API_KEY), err: failed to get secret: failed to get all "
    'secrets: failed to list secrets: failed to do request: Get "https://bitwarden-sdk-server.'
    'external-secrets.svc.cluster.local:9998/rest/api/1/secrets": context deadline exceeded'
)


def _board(items, events):
    return key_sync.build({"items": items}, {"items": events}, NOW)


def test_synced_bridge_is_synced_and_values_never_appear():
    b = _board(
        [_es("llm", "human-kimi", ["MOONSHOT_API_KEY"], True, NOW - 3600, NOW - 30)], []
    )
    assert b["available"] and b["counts"] == {"synced": 1}
    row = b["rows"][0]
    assert row["name"] == "MOONSHOT_API_KEY" and row["state"] == "synced"
    assert row["namespaces"] == [
        {
            "namespace": "llm",
            "bridge": "human-kimi",
            "state": "synced",
            "since": NOW - 3600,
        }
    ]
    assert b["alerts"] == []


def test_missing_names_the_exact_key_and_only_that_key():
    keys = ["GUARDIAN_PHONE_NUMBER", "PUBLIC_SERVER_URL", "TWILIO_AUTH_TOKEN"]
    b = _board(
        [_es("concierge", "human-twilio", keys, False, NOW - 86400)],
        [_ev("concierge", "human-twilio", MISSING_TWILIO, NOW - 60)],
    )
    by = {r["name"]: r for r in b["rows"]}
    assert by["PUBLIC_SERVER_URL"]["state"] == "missing"
    # the other keys in the bridge are blocked, not missing: the name to create is only one
    assert by["TWILIO_AUTH_TOKEN"]["state"] == "failing"
    assert "blocked by missing PUBLIC_SERVER_URL" in by["TWILIO_AUTH_TOKEN"]["reason"]
    assert b["rows"][0]["name"] == "PUBLIC_SERVER_URL"  # worst state sorts first


def test_unreachable_is_bitwarden_not_the_key():
    for msg in (UNREACHABLE, TIMEOUT):
        b = _board(
            [
                _es(
                    "dagster",
                    "human-groq",
                    ["GROQ_API_KEY"],
                    False,
                    NOW - 120,
                    NOW - 200,
                )
            ],
            [_ev("dagster", "human-groq", msg, NOW - 100)],
        )
        row = b["rows"][0]
        assert row["state"] == "unreachable", msg
        # the cause from the end of ESO's wrapped chain, not "failed to get secret" x3
        assert row["reason"].endswith(
            ("connection timeout", "context deadline exceeded")
        )


def test_stopped_when_it_synced_before_and_the_reason_is_unknown():
    b = _board(
        [
            _es(
                "prospector",
                "human-openrouter",
                ["OPENROUTER_API_KEY"],
                False,
                NOW - 600,
                NOW - 700,
            )
        ],
        [],
    )
    row = b["rows"][0]
    assert row["state"] == "stopped" and row["last_ok"] == NOW - 700


def test_never_synced_with_no_event_is_failing():
    b = _board(
        [_es("dagster", "human-typesafe", ["TYPESAFE_API_KEY"], False, NOW - 600)], []
    )
    assert b["rows"][0]["state"] == "failing"


def test_newest_event_wins():
    b = _board(
        [_es("llm", "human-groq", ["GROQ_API_KEY"], False, NOW - 900, NOW - 1000)],
        [
            _ev("llm", "human-groq", UNREACHABLE, NOW - 800),
            _ev(
                "llm",
                "human-groq",
                MISSING_TWILIO.replace("PUBLIC_SERVER_URL", "GROQ_API_KEY"),
                NOW - 10,
            ),
        ],
    )
    assert b["rows"][0]["state"] == "missing"


def test_a_bitwarden_outage_does_not_hide_a_missing_name():
    keys = ["PUBLIC_SERVER_URL", "TWILIO_AUTH_TOKEN"]
    b = _board(
        [_es("concierge", "human-twilio", keys, False, NOW - 86400)],
        [
            _ev("concierge", "human-twilio", MISSING_TWILIO, NOW - 300),
            _ev(
                "concierge", "human-twilio", UNREACHABLE, NOW - 5
            ),  # newer, but only an outage
        ],
    )
    by = {r["name"]: r for r in b["rows"]}
    assert by["PUBLIC_SERVER_URL"]["state"] == "missing"
    assert "latest attempt" in by["PUBLIC_SERVER_URL"]["reason"]


def test_a_missing_report_from_before_the_last_sync_is_history():
    b = _board(
        [_es("llm", "human-groq", ["GROQ_API_KEY"], False, NOW - 60, NOW - 120)],
        [
            _ev(
                "llm",
                "human-groq",
                MISSING_TWILIO.replace("PUBLIC_SERVER_URL", "GROQ_API_KEY"),
                NOW - 3600,
            ),
            _ev("llm", "human-groq", UNREACHABLE, NOW - 30),
        ],
    )
    assert b["rows"][0]["state"] == "unreachable"


def test_row_takes_the_worst_namespace():
    b = _board(
        [
            _es("llm", "human-groq", ["GROQ_API_KEY"], True, NOW - 3600, NOW - 30),
            _es(
                "otto-gateway",
                "human-groq",
                ["GROQ_API_KEY"],
                False,
                NOW - 600,
                NOW - 700,
            ),
        ],
        [],
    )
    row = b["rows"][0]
    assert row["state"] == "stopped"
    assert {n["namespace"] for n in row["namespaces"]} == {"llm", "otto-gateway"}
    assert row["last_ok"] == NOW - 30


def test_alert_only_for_router_keys_past_the_threshold():
    items = [
        _es(
            "llm",
            "human-groq",
            ["GROQ_API_KEY"],
            False,
            NOW - key_sync.ALERT_AFTER_S - 1,
            NOW - 9999,
        ),
        _es(
            "llm", "human-gemini", ["GEMINI_API_KEY"], False, NOW - 60, NOW - 9999
        ),  # too recent
        _es(
            "dagster", "human-exa", ["EXA_API_KEY"], False, NOW - 9999, NOW - 99999
        ),  # not router
    ]
    b = _board(items, [_ev("llm", "human-groq", UNREACHABLE, NOW - 30)])
    assert [a["bridge"] for a in b["alerts"]] == ["human-groq"]
    assert b["alerts"][0]["state"] == "unreachable"


def test_non_bridge_externalsecrets_are_ignored():
    other = _es("backstage", "verdict-key-wall", ["verdict-hmac-key"], False, NOW - 60)
    assert _board([other], [])["rows"] == []


def test_alert_story_is_news_desk_shaped_and_stable():
    a = {
        "namespace": "llm",
        "bridge": "human-groq",
        "state": "missing",
        "since": NOW - 600,
        "missing": ["GROQ_API_KEY"],
        "reason": "no secret found",
    }
    s1, s2 = (
        key_sync._story(a, "2026-10-02T00:00:00Z"),
        key_sync._story(a, "2026-10-02T00:01:00Z"),
    )
    assert s1["id"] == s2["id"]  # published once per alert, not once per tick
    assert "missing GROQ_API_KEY in Bitwarden" in s1["headline"]
    assert s1["channel"] == "metrics" and s1["breaking"] is True


def test_unreadable_cluster_is_unavailable_not_empty(monkeypatch):
    monkeypatch.setattr(key_sync, "_cache", {"at": 0.0, "body": None})
    monkeypatch.setattr(key_sync, "_kubectl", lambda: None)
    body = key_sync.key_sync_status(now=NOW)
    assert body["available"] is False and "kubectl" in body["error"]
