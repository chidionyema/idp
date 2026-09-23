"""Founder, 2026-09-03 04:1xZ: "no agent can proceed without [the estate snapshot], furthermore I
need to know exactly what it contains", then "it could contain more useful info", then "and any
recent decision or changes". The night before, two vendor roots were refused by their vendors and
every session learned it by re-running apply, though the apply log had said so at 03:42Z; the
founder hit a dead router lane from aider before any board row named it.

Version 2 of the document (docs/founder/estate-snapshot-is-mandatory.md) adds seven fields inside
the five tabs. Each parser is graded here on the shape the workflow fetches, and on the rule that
an unread source is UNKNOWN or empty, never ok.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import pathlib
import sys

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin" / "lib"))
_loader = importlib.machinery.SourceFileLoader(
    "estate_state_build", str(ROOT / "bin" / "idp-estate-state-build")
)
_spec = importlib.util.spec_from_loader("estate_state_build", _loader)
B = importlib.util.module_from_spec(_spec)
_loader.exec_module(B)

SCHEMA = json.loads((ROOT / "platform/estate-state/schema.json").read_text())
NOW = dt.datetime(2026, 9, 3, 4, 30, tzinfo=dt.timezone.utc)
STAMP = "2026-09-03T04:30:00Z"

APPLY_LOG = """bin/idp-bootstrap-tailscale (crew#66 phase 1): FAIL tailscale no OAuth client answered
bin/idp-bootstrap-vendors (crew#579, R52): ok      anthropic            kept
bin/idp-bootstrap-vendors (crew#579, R52): FAIL    deepseek             SEED_DEEPSEEK_API_KEY refused by https://api.deepseek.com/models: HTTP 401; the vendor does not accept this key
bin/idp-bootstrap-vendors (crew#579, R52): FAIL    kimi                 SEED_KIMI_API_KEY refused by https://api.moonshot.ai/v1/models, https://api.kimi.com/coding/v1/models: HTTP 401
bin/idp-bootstrap-vendors (crew#579, R52): BLIND   vendors              2 written, 5 kept, 2 failed
"""
REGISTRY = {
    "vendors": {
        "kimi": {"kind": "secret", "secret": "SEED_KIMI_API_KEY"},
        "deepseek": {"kind": "secret", "secret": "SEED_DEEPSEEK_API_KEY"},
        "anthropic": {"kind": "secret", "secret": "SEED_ANTHROPIC_API_KEY"},
        "gemini": {"kind": "secret", "secret": "SEED_GEMINI_API_KEY"},
        "telegram": {"kind": "bot"},
    }
}
SECRETS = [
    {"name": "SEED_KIMI_API_KEY", "updatedAt": "2026-09-02T21:20:53Z"},
    {"name": "SEED_DEEPSEEK_API_KEY", "updatedAt": "2026-09-02T20:38:17Z"},
]


def test_a_vendor_root_carries_when_it_was_set_and_the_vendors_own_answer():
    rows = {
        r["vendor"]: r
        for r in B.parse_vendor_roots(
            REGISTRY, SECRETS, APPLY_LOG, "2026-09-03T03:29:00Z"
        )
    }
    assert rows["kimi"]["set_at"] == "2026-09-02T21:20:53Z"
    assert rows["kimi"]["verdict"] == "FAIL"
    assert "api.kimi.com/coding/v1/models" in rows["kimi"]["detail"]
    assert (
        rows["deepseek"]["verdict"] == "FAIL"
        and "HTTP 401" in rows["deepseek"]["detail"]
    )
    assert rows["anthropic"]["verdict"] == "ok"
    # a vendor the seeder did not name is UNKNOWN, never ok; one without a SEED root is not a row
    assert rows["gemini"]["verdict"] == "UNKNOWN" and "set_at" not in rows["gemini"]
    assert "telegram" not in rows


def test_no_apply_log_and_no_secret_list_is_unknown_everywhere_never_ok():
    rows = B.parse_vendor_roots(REGISTRY, [], "", None)
    assert rows and all(r["verdict"] == "UNKNOWN" for r in rows)
    assert all("set_at" not in r and "measured_at" not in r for r in rows)


def test_the_last_apply_run_names_its_failed_steps_and_every_fail_or_blind_line():
    run = {
        "databaseId": 33711941272,
        "url": "https://github.com/chidionyema/idp/actions/runs/33711941272",
        "createdAt": "2026-09-03T03:29:00Z",
        "conclusion": "failure",
        "jobs": [
            {
                "name": "check",
                "steps": [
                    {
                        "name": "bin/idp-bootstrap-vendors (crew#579, R52)",
                        "conclusion": "failure",
                    },
                    {"name": "bin/idp-oke-rebuild --apply", "conclusion": "success"},
                ],
            }
        ],
    }
    la = B.parse_last_apply(run, APPLY_LOG)
    assert la["run"] == 33711941272 and la["conclusion"] == "failure"
    assert la["failed_steps"] == [
        {"job": "check", "step": "bin/idp-bootstrap-vendors (crew#579, R52)"}
    ]
    assert len(la["lines"]) == 4 and all(
        ": FAIL" in ln or ": BLIND" in ln for ln in la["lines"]
    )
    assert B.parse_last_apply(None, "") == {
        "conclusion": "UNKNOWN",
        "failed_steps": [],
        "lines": [],
    }


def test_open_pull_requests_grade_the_newest_run_of_each_check_not_the_cancelled_twin():
    rollup = [
        {
            "name": "ci",
            "status": "COMPLETED",
            "conclusion": "CANCELLED",
            "startedAt": "2026-09-03T01:00:00Z",
        },
        {
            "name": "ci",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "2026-09-03T02:00:00Z",
        },
        {
            "name": "gate",
            "status": "IN_PROGRESS",
            "conclusion": None,
            "startedAt": "2026-09-03T02:00:00Z",
        },
        {"context": "legacy", "state": "FAILURE"},
    ]
    prs = B.parse_open_prs(
        [
            {
                "repo": "idp",
                "number": 1206,
                "title": "otto gateway manifests",
                "headRefName": "otto/gateway",
                "updatedAt": "2026-09-03T03:50:00Z",
                "mergeStateStatus": "BLOCKED",
                "isDraft": False,
                "url": "https://github.com/chidionyema/idp/pull/1206",
                "statusCheckRollup": rollup,
            }
        ]
    )
    assert prs[0]["checks"] == {"ok": 1, "fail": 1, "pending": 1}, prs[0]["checks"]
    assert prs[0]["merge_state"] == "BLOCKED" and prs[0]["branch"] == "otto/gateway"


def test_a_founder_blocker_is_a_live_session_waiting_on_him_or_a_founder_request_issue():
    sessions = [
        {
            "id": "2c88870e",
            "lane": ".wt-vendor-probe",
            "last_handoff_at": "2026-09-03T04:07:00Z",
            "active": "nothing until a new root lands",
            "blocked": "waiting on the founder to re-set SEED_KIMI_API_KEY and say go",
        },
        {
            "id": "a14fc078",
            "lane": ".wt-reports",
            "last_handoff_at": "2026-09-03T04:04:00Z",
            "active": "superset",
            "blocked": "none",
        },
        {
            "id": "a2aed3c9",
            "lane": ".wt-kimi",
            "last_handoff_at": "2026-09-02T22:34:00Z",
            "active": "parked: no handoff for 314 min",
            "blocked": "founder rejected the credentials page",
        },
    ]
    issues = [
        {
            "repo": "crew",
            "number": 801,
            "title": "Approve the OKE node pool",
            "labels": ["founder-request"],
            "created_at": "2026-09-02T10:00:00Z",
        },
        {
            "repo": "crew",
            "number": 802,
            "title": "P1 something",
            "labels": ["p1"],
            "created_at": "2026-09-02T10:00:00Z",
        },
    ]
    rows = B.parse_founder_blockers(sessions, issues)
    assert [(r["source"], r.get("session") or r.get("number")) for r in rows] == [
        ("session", "2c88870e"),
        ("issue", 801),
    ]
    assert rows[0]["waits_for"].startswith("waiting on the founder")


def test_incidents_keep_the_open_and_the_recent_and_drop_the_old_resolved():
    ledger = [
        {
            "id": "I1",
            "title": "old and resolved",
            "detected": "2026-08-29T23:36Z",
            "resolved": "2026-08-30T01:26Z",
            "classes": ["x"],
        },
        {"id": "I2", "title": "still open", "detected": "2026-08-31T10:00Z"},
        {
            "id": "I3",
            "title": "resolved tonight",
            "detected": "2026-09-03T01:00Z",
            "resolved": "2026-09-03T02:00Z",
            "classes": ["silent-green"],
        },
    ]
    rows = B.parse_incidents(ledger, NOW, 24)
    assert [r["id"] for r in rows] == ["I3", "I2"]
    assert rows[0]["classes"] == ["silent-green"] and "resolved" not in rows[1]


def test_recent_decisions_are_rulings_of_the_day_and_commits_to_decision_records():
    rulings = [
        {"id": "R52", "date": "2026-08-29", "text": "One root per provider"},
        {
            "id": "R75",
            "date": "2026-09-03",
            "text": "No agent proceeds without the estate snapshot",
            "record": "docs/founder/estate-snapshot-is-mandatory.md",
        },
    ]
    commits = [
        {
            "repo": "idp",
            "sha": "04c78f5d9999",
            "title": "docs: decision 0019",
            "at": "2026-09-02T12:22:45Z",
        }
    ]
    rows = B.parse_decisions(rulings, commits, NOW, 24)
    assert [(r["kind"], r.get("id") or r.get("sha")) for r in rows] == [
        ("ruling", "R75"),
        ("record", "04c78f5d"),
    ]
    assert rows[0]["record"].endswith("estate-snapshot-is-mandatory.md")


def test_changes_are_every_merge_to_main_newest_first_with_a_short_sha():
    rows = B.parse_changes(
        [
            {
                "repo": "idp",
                "sha": "d32f49f4aaaa",
                "title": "image update",
                "at": "2026-09-03T04:05:33Z",
            },
            {
                "repo": "idp",
                "sha": "723a239cbbbb",
                "title": "platform(otto): reconciler (#1200)",
                "at": "2026-09-03T04:23:54Z",
            },
        ]
    )
    assert [r["sha"] for r in rows] == ["723a239c", "d32f49f4"]


def test_router_lanes_keep_the_schema_keys_and_an_unknown_verdict_stays_unknown():
    rows = B.parse_router_lanes(
        [
            {
                "lane": "kimi",
                "verdict": "FAIL",
                "status": 500,
                "detail": "HTTP 500 MoonshotException",
                "measured_at": STAMP,
                "ms": 300,
                "secret": "never",
            },
            {
                "lane": "deepseek",
                "verdict": "weird",
                "status": None,
                "detail": "",
                "measured_at": STAMP,
            },
        ]
    )
    assert rows[0]["lane"] == "deepseek" and rows[0]["verdict"] == "UNKNOWN"
    assert rows[1]["lane"] == "kimi" and "secret" not in rows[1]


def test_the_whole_document_with_every_v2_input_missing_validates_and_says_blind(
    tmp_path,
):
    out = tmp_path / "doc.json"
    rc = B.main(["--now", STAMP, "--out", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text())
    jsonschema.validate(doc, SCHEMA, format_checker=jsonschema.FormatChecker())
    assert doc["delivery"]["last_apply"]["conclusion"] == "UNKNOWN"
    assert (
        doc["runtime"]["router_lanes"] == [] and doc["security"]["vendor_roots"] == []
    )
    assert (
        doc["overview"]["decisions"] == [] and doc["overview"]["founder_blockers"] == []
    )


def test_the_whole_document_with_every_v2_input_present_validates(tmp_path):
    files = {
        "registry.yaml": "vendors:\n  kimi: {kind: secret, secret: SEED_KIMI_API_KEY}\n",
        "secrets.json": json.dumps(SECRETS),
        "apply-run.json": json.dumps(
            {
                "databaseId": 1,
                "url": "u",
                "createdAt": STAMP,
                "conclusion": "failure",
                "jobs": [],
            }
        ),
        "apply.log": APPLY_LOG,
        "lanes.json": json.dumps(
            [
                {
                    "lane": "kimi",
                    "verdict": "FAIL",
                    "status": 500,
                    "detail": "HTTP 500",
                    "measured_at": STAMP,
                    "ms": 1,
                }
            ]
        ),
        "prs.json": json.dumps(
            [
                {
                    "repo": "idp",
                    "number": 1,
                    "title": "t",
                    "headRefName": "b",
                    "updatedAt": STAMP,
                    "mergeStateStatus": "CLEAN",
                    "isDraft": False,
                    "url": "u",
                    "statusCheckRollup": [],
                }
            ]
        ),
        "incidents.json": json.dumps(
            [{"id": "I9", "title": "t", "detected": "2026-09-03T01:00Z"}]
        ),
        "decisions.json": json.dumps(
            [{"repo": "idp", "sha": "abcdef12", "title": "docs: decision", "at": STAMP}]
        ),
        "changes.json": json.dumps(
            [{"repo": "idp", "sha": "abcdef12", "title": "merge", "at": STAMP}]
        ),
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    out = tmp_path / "doc.json"
    rc = B.main(
        [
            "--now",
            STAMP,
            "--out",
            str(out),
            "--registry",
            str(tmp_path / "registry.yaml"),
            "--secrets",
            str(tmp_path / "secrets.json"),
            "--apply-run",
            str(tmp_path / "apply-run.json"),
            "--apply-log",
            str(tmp_path / "apply.log"),
            "--lanes",
            str(tmp_path / "lanes.json"),
            "--prs",
            str(tmp_path / "prs.json"),
            "--incidents",
            str(tmp_path / "incidents.json"),
            "--decision-commits",
            str(tmp_path / "decisions.json"),
            "--changes",
            str(tmp_path / "changes.json"),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text())
    jsonschema.validate(doc, SCHEMA, format_checker=jsonschema.FormatChecker())
    assert doc["security"]["vendor_roots"][0]["verdict"] == "FAIL"
    assert doc["runtime"]["router_lanes"][0]["lane"] == "kimi"
    assert doc["delivery"]["open_prs"][0]["number"] == 1
    assert doc["runtime"]["incidents"][0]["id"] == "I9"
    assert doc["overview"]["decisions"][0]["kind"] == "record"


def test_the_schema_refuses_a_document_missing_a_v2_field():
    import pytest

    example = json.loads((ROOT / "platform/estate-state/example.json").read_text())
    for tab, field in (
        ("security", "vendor_roots"),
        ("delivery", "last_apply"),
        ("overview", "decisions"),
    ):
        bad = json.loads(json.dumps(example))
        del bad[tab][field]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, SCHEMA)


def test_the_lane_probe_reads_a_scoped_key_as_unmeasured_and_a_vendor_error_as_fail(
    monkeypatch,
):
    """Measured 2026-09-03 04:43Z: a kimi-only virtual key read HTTP 403 key_model_access_denied
    on fourteen live lanes. That is the key's scope, not fourteen dead lanes."""
    import io
    import urllib.error
    import urllib.request

    _pl = importlib.machinery.SourceFileLoader(
        "router_lanes", str(ROOT / "bin" / "idp-router-lanes")
    )
    _ps = importlib.util.spec_from_loader("router_lanes", _pl)
    P = importlib.util.module_from_spec(_ps)
    _pl.exec_module(P)

    def refuse(req, timeout=0):
        lane = json.loads(req.data)["model"]
        if lane == "claude":
            body = b'{"error":{"type":"key_model_access_denied","code":"403"}}'
            raise urllib.error.HTTPError(
                req.full_url, 403, "Forbidden", {}, io.BytesIO(body)
            )
        body = b'{"error":{"message":"litellm.AuthenticationError: MoonshotException"}}'
        raise urllib.error.HTTPError(req.full_url, 500, "Error", {}, io.BytesIO(body))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    scoped = P.call("https://llm.example/v1/chat/completions", "k", "claude", 1)
    dead = P.call("https://llm.example/v1/chat/completions", "k", "kimi", 1)
    assert scoped["verdict"] == "UNKNOWN" and scoped["status"] == 403
    assert dead["verdict"] == "FAIL" and "MoonshotException" in dead["detail"]
