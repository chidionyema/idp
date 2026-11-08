"""Falsification tests for the one estate SRE signal plane."""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "bin" / "estate-sre"
SPEC = importlib.util.spec_from_loader(
    "estate_sre",
    SourceFileLoader("estate_sre", str(ENGINE)),
)
assert SPEC and SPEC.loader
sre = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sre)


def _source(
    source_id: str,
    state: str,
    *,
    required: bool = True,
    failure_domain: str = "test",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "kind": "test",
        "state": state,
        "summary": f"{source_id} is {state}",
        "observedAt": sre.iso(),
        "ageSeconds": 0,
        "vantage": "cloud",
        "failureDomain": failure_domain,
        "required": required,
        "evidence": evidence or {},
    }


def _contract() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "contractId": "estate.sre",
        "release": {"id": "test", "version": "1.0.0"},
        "history": {
            "minimumSamples": 6,
            "retain": 24,
            "predictionSamples": 12,
        },
        "planes": [
            {
                "id": "critical",
                "title": "Critical plane",
                "weight": 3,
                "critical": True,
                "requiredSources": ["critical-source"],
                "requiredByVantage": {"cloud": ["critical-source"]},
            }
        ],
        "slos": [
            {
                "id": "critical-availability",
                "title": "Critical availability",
                "target": 0.999,
                "windowHours": 720,
                "sources": ["critical-source"],
                "sourcesByVantage": {"cloud": ["critical-source"]},
            }
        ],
        "priority": {
            "proactiveConsecutiveFailures": 3,
            "burnRateWarning": 1.0,
            "burnRateCritical": 4.0,
        },
    }


def test_healthy_projection_has_one_verified_hash_and_can_claim_healthy() -> None:
    snapshot = sre.synthesize(
        _contract(),
        [_source("critical-source", "OK")],
        [],
        "cloud",
    )

    digest = snapshot["integrity"]["digest"]
    assert snapshot["state"] == "HEALTHY"
    assert snapshot["coveragePercent"] == 100.0
    assert snapshot["agent"]["canClaimHealthy"] is True
    assert snapshot["agent"]["snapshotHash"] == digest
    assert snapshot["founder"]["snapshotHash"] == digest
    assert sre.snapshot_hash(snapshot) == digest
    schema = json.loads(
        (ROOT / "catalog" / "sre-snapshot.v1.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(snapshot, schema)


def test_one_blind_required_source_prevents_a_healthy_claim() -> None:
    snapshot = sre.synthesize(
        _contract(),
        [_source("critical-source", "BLIND")],
        [],
        "cloud",
    )

    assert snapshot["state"] == "BLIND"
    assert snapshot["coveragePercent"] == 0.0
    assert snapshot["agent"]["canClaimHealthy"] is False
    assert snapshot["blindSpots"] == [
        {
            "source": "critical-source",
            "state": "BLIND",
            "summary": "critical-source is BLIND",
            "vantage": "cloud",
        }
    ]
    assert any(row["code"] == "VISIBILITY_GAP" for row in snapshot["findings"])


def test_stale_and_conflict_are_not_collapsed_into_green_or_blind() -> None:
    stale = sre.synthesize(
        _contract(),
        [_source("critical-source", "STALE")],
        [],
        "cloud",
    )
    conflict = sre.synthesize(
        _contract(),
        [_source("critical-source", "CONFLICT")],
        [],
        "cloud",
    )

    assert stale["state"] == "STALE"
    assert conflict["state"] == "CONFLICT"
    assert stale["coveragePercent"] == conflict["coveragePercent"] == 0.0


def test_shared_oci_failure_is_one_correlated_finding() -> None:
    contract = _contract()
    contract["planes"] = [
        {
            "id": "public-edge",
            "title": "Public edge",
            "weight": 3,
            "critical": True,
            "requiredSources": ["dns", "oci-lb", "estate-lanes"],
        }
    ]
    contract["slos"] = []
    sources = [
        _source(
            "dns",
            "OK",
            failure_domain="dns",
            evidence={
                "sharedAddresses": [
                    {
                        "address": "193.123.184.22",
                        "hosts": [
                            "api.mumchimp.com",
                            "auth.mumchimp.com",
                            "mcp.mumchimp.com",
                        ],
                    }
                ]
            },
        ),
        _source(
            "oci-lb",
            "DOWN",
            failure_domain="oci-lb",
            evidence={
                "backendSets": {
                    "TCP-80": {
                        "state": "DOWN",
                        "criticalBackends": ["10.0.148.221:30562"],
                    },
                    "TCP-443": {
                        "state": "DOWN",
                        "criticalBackends": ["10.0.148.221:30537"],
                    },
                }
            },
        ),
        _source(
            "estate-lanes",
            "DOWN",
            failure_domain="public-edge",
            evidence={"affected": []},
        ),
    ]

    snapshot = sre.synthesize(contract, sources, [], "cloud")
    correlated = [
        row for row in snapshot["findings"] if row["code"] == "CORRELATED_FAILURE"
    ]

    assert len(correlated) == 1
    assert correlated[0]["failureDomain"] == "oci-lb"
    assert len(correlated[0]["affected"]) == 3


def test_slo_is_learning_until_the_sample_floor() -> None:
    current = {
        "generatedAt": sre.iso(),
        "sourceStates": {"critical-source": "OK"},
    }
    results = sre.build_slos(_contract(), [], current, "cloud")

    assert results[0]["state"] == "LEARNING"
    assert results[0]["samples"] == 1
    assert results[0]["observedAvailability"] == 1.0
    assert results[0]["burnRate"] is None


def test_read_state_marks_old_or_tampered_snapshots_non_green(tmp_path: Path) -> None:
    snapshot = sre.synthesize(
        _contract(),
        [_source("critical-source", "OK")],
        [],
        "cloud",
    )
    snapshot["generatedAt"] = "2026-01-01T00:00:00Z"
    snapshot["integrity"]["digest"] = sre.snapshot_hash(snapshot)
    path = tmp_path / "current.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    stale = sre.read_state(path, 60)
    assert stale["state"] == "STALE"
    assert stale["agent"]["canClaimHealthy"] is False
    assert stale["founder"]["state"] == "STALE"

    snapshot["headline"] = "tampered after signing"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    conflict = sre.read_state(path, 10**10)
    assert conflict["state"] == "CONFLICT"
    assert conflict["read"]["integrityValid"] is False
    assert conflict["agent"]["canClaimHealthy"] is False


def test_cloud_agent_visibility_never_fabricates_capacity(tmp_path: Path) -> None:
    state = {
        "version": 1,
        "generated_at": sre.iso(),
        "overview": {
            "sessions": [
                {
                    "id": "s1",
                    "lane": "repair",
                    "last_handoff_at": sre.iso(),
                }
            ]
        },
        "delivery": {"open_p0": [], "failed_runs": [], "open_prs": []},
        "runtime": {
            "clusters": [{"name": "oke", "role": "production", "state": "ok"}],
            "surfaces": [],
            "router_lanes": [],
            "incidents": [],
        },
        "docs_apis": {"standards_page": "x", "diagrams": []},
        "security": {"open_findings": [], "vendor_roots": []},
    }
    path = tmp_path / "estate-state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    source = {
        "id": "cloud-agent-fabric",
        "kind": "cloud-agent-fabric",
        "path": str(path),
        "maxAgeSeconds": 1800,
        "staleAfterSeconds": 7200,
        "failureDomain": "agent-fabric",
        "required": True,
    }

    result = sre.collect_cloud_agent_fabric(source, ROOT, "cloud")

    assert result["state"] == "DEGRADED"
    assert result["evidence"]["capacity"] == "UNMEASURED"
    assert "unmeasured" in result["summary"]


def test_duplicate_verdicts_in_one_lane_service_are_down() -> None:
    body = {
        "generated_at": sre.iso(),
        "summary": {
            "total": 3,
            "alive": 1,
            "down": 2,
            "unknown": 0,
            "not_provisioned": 0,
        },
        "lanes": [
            {
                "service": "estate-doors",
                "leg": "llm",
                "provider": "oracle-oke",
                "verdict": "MEASURED_OK",
                "detail": "HTTP 200",
            },
            {
                "service": "estate-doors",
                "leg": "mcp",
                "provider": "oracle-oke",
                "verdict": "MEASURED_FAIL",
                "detail": "TLS EOF",
            },
            {
                "service": "estate-doors",
                "leg": "auth",
                "provider": "oracle-oke",
                "verdict": "MEASURED_FAIL",
                "detail": "TLS EOF",
            },
        ],
        "ladders": [],
    }
    original = sre.run_command
    try:
        sre.run_command = lambda *args, **kwargs: {
            "rc": 2,
            "stdout": json.dumps(body),
            "stderr": "",
            "timedOut": False,
        }
        result = sre.collect_estate_lanes(
            {
                "id": "estate-lanes",
                "kind": "estate-lanes",
                "command": ["python3", "bin/idp-estate-homes", "--json"],
                "failureDomain": "public-edge",
                "required": True,
            },
            ROOT,
            "laptop",
        )
    finally:
        sre.run_command = original

    assert result["state"] == "DOWN"
    assert "2 lane(s) failed" in result["summary"]


def test_estate_truth_measured_fail_is_down(tmp_path: Path) -> None:
    body = {
        "generated_at": sre.iso(),
        "verdict": "MEASURED_FAIL",
        "predicates": [
            {
                "id": "router.cloud.completion",
                "verdict": "MEASURED_FAIL",
                "detail": "HTTP 401",
            }
        ],
    }
    script = tmp_path / "truth.py"
    script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    original = sre.run_command
    try:
        sre.run_command = lambda *args, **kwargs: {
            "rc": 1,
            "stdout": json.dumps(body),
            "stderr": "",
            "timedOut": False,
        }
        result = sre.collect_truth(
            {
                "id": "founder-path",
                "kind": "estate-truth",
                "command": ["python3", str(script), "--json"],
                "failureDomain": "public-edge",
                "required": True,
            },
            ROOT,
            "cloud",
        )
    finally:
        sre.run_command = original

    assert result["state"] == "DOWN"
    assert "1 of 1 predicates" in result["summary"]


def test_issue_domain_is_stable_not_one_issue_per_symptom() -> None:
    snapshot = sre.synthesize(
        _contract(),
        [_source("critical-source", "OK")],
        [],
        "cloud",
    )
    findings = [
        {"severity": "critical", "code": "PLANE_DOWN", "title": "one"},
        {"severity": "high", "code": "CHRONIC_FAILURE", "title": "two"},
    ]
    body = sre.domain_issue_body(snapshot, "oci-lb", findings)

    assert "<!-- estate-sre-domain:oci-lb -->" in body
    assert "[SRE] oci-lb" in body
    assert snapshot["integrity"]["digest"] in body
    assert body.count("<!-- estate-sre-domain:") == 1


def test_secret_shaped_evidence_is_redacted_before_projection() -> None:
    fake_value = "abc" + "defghijk" + "12345"
    result = sre.source_result(
        {
            "id": "upstream",
            "kind": "test",
            "failureDomain": "provider",
            "required": True,
        },
        state="DOWN",
        summary=f"upstream rejected api_key={fake_value}",
        vantage="cloud",
        evidence={
            "body": f"Authorization: Bearer {fake_value}",
            "nested": [f"secret={fake_value}"],
            "count": 2,
        },
    )
    serialized = json.dumps(result)

    assert fake_value not in serialized
    assert "<redacted>" in serialized
    assert result["evidence"]["count"] == 2
