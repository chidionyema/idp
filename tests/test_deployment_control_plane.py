from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from greenlane.circuit_breaker import GreenlaneCircuitBreaker, ShipContract

# `platform` is a stdlib module name; the repo directory is not a package, so a
# plain `from platform.deploy...` import resolves to stdlib and fails. Load the
# candidate source by file location instead (reconciliation, not a code change).
_REACH_PATH = (
    Path(__file__).resolve().parent.parent
    / "platform"
    / "deploy"
    / "kustomize_reachability.py"
)
_REACH_SPEC = importlib.util.spec_from_file_location(
    "kustomize_reachability", _REACH_PATH
)
assert _REACH_SPEC and _REACH_SPEC.loader
_reach = importlib.util.module_from_spec(_REACH_SPEC)
_REACH_SPEC.loader.exec_module(_reach)
audit_reachability = _reach.audit_reachability


def test_reachability_rejects_unapplied_platform_dir_and_retired_oke(
    tmp_path: Path,
) -> None:
    (tmp_path / "clusters/zone-b").mkdir(parents=True)
    (tmp_path / "clusters/zone-b/kustomization.yaml").write_text(
        "resources:\n  - ../../platform/wired-svc\n", encoding="utf-8"
    )
    (tmp_path / "platform/wired-svc").mkdir(parents=True)
    (tmp_path / "platform/wired-svc/kustomization.yaml").write_text(
        "resources: []\n", encoding="utf-8"
    )

    # Ghost directory (#8328 failure class: merged manifest never referenced by Flux or targets.json)
    (tmp_path / "platform/ghost-pennyd").mkdir(parents=True)
    (tmp_path / "platform/ghost-pennyd/deployment.yaml").write_text(
        "kind: Deployment\n", encoding="utf-8"
    )

    # Worker target wired cleanly
    (tmp_path / "platform/router-edge").mkdir(parents=True)
    (tmp_path / "platform/router-edge/wrangler.toml").write_text(
        'name = "meridian-router-edge"\n', encoding="utf-8"
    )

    targets = tmp_path / "platform/deploy/targets.json"
    targets.parent.mkdir(parents=True)
    targets.write_text(
        json.dumps(
            {
                "prohibited_patterns": ["oke", "oci-oke"],
                "flux_roots": ["clusters/zone-b/kustomization.yaml"],
                "non_deployable_dirs": ["platform/deploy"],
                "cloudflare_workers": [
                    {"name": "meridian-router-edge", "dir": "platform/router-edge"}
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = audit_reachability(tmp_path, targets)
    assert len(errors) == 1
    assert "UNAPPLIED_PLATFORM_DIR" in errors[0]
    assert "platform/ghost-pennyd" in errors[0]

    # Wiring the directory clears the error
    (tmp_path / "clusters/zone-b/kustomization.yaml").write_text(
        "resources:\n  - ../../platform/wired-svc\n  - ../../platform/ghost-pennyd\n",
        encoding="utf-8",
    )
    assert audit_reachability(tmp_path, targets) == []

    # Introducing retired OKE path fails closed (#7387)
    (tmp_path / "platform/oci-oke-legacy").mkdir(parents=True)
    (tmp_path / "platform/oci-oke-legacy/kustomization.yaml").write_text(
        "resources: []\n", encoding="utf-8"
    )
    (tmp_path / "clusters/zone-b/kustomization.yaml").write_text(
        "resources:\n  - ../../platform/wired-svc\n  - ../../platform/ghost-pennyd\n  - ../../platform/oci-oke-legacy\n",
        encoding="utf-8",
    )
    oke_errors = audit_reachability(tmp_path, targets)
    assert any("PROHIBITED_FLUX_PATH" in e for e in oke_errors)


def test_greenlane_ship_contract_retry_cap_pr_closure_and_karma_verdict(
    tmp_path: Path,
) -> None:
    cb = GreenlaneCircuitBreaker(
        tmp_path / "greenlane.sqlite3", max_retries_across_mains=2
    )
    contract = ShipContract(
        issue_number=8383,
        owner="codex-1",
        target_service="meridian-router-edge",
        probe_url="https://llm.meridianlabs.cloud/health",
        expected_metric="blackbox_prober_5_of_5",
    )

    # 1. Missing contract rejected (#8350)
    rejected = cb.admit_lane("lane/no-contract", "aaa1111", contract=None)
    assert not rejected.admitted
    assert rejected.state == "REJECTED_NO_CONTRACT"

    # 2. Valid contract admitted + duplicate hand-raised PR scheduled for closure (#8331)
    admitted = cb.admit_lane(
        "lane/router-fix", "bbb2222", contract=contract, hand_raised_pr_numbers=[8207]
    )
    assert admitted.admitted
    assert any(
        a["type"] == "CLOSE_ADOPTED_PR" and a["pr_number"] == 8207
        for a in admitted.actions
    )

    # 3. Fails across 2 advancing mains -> notifies owner (#8303) and parks lane (#8289)
    f1 = cb.record_lane_failure(
        "lane/router-fix", "bbb2222", "main001", "RED", "pytest_fail", 8383, "codex-1"
    )
    assert not f1["parked"]
    assert f1["actions"][0]["type"] == "COMMENT_CLAIM_ISSUE"

    f2 = cb.record_lane_failure(
        "lane/router-fix", "bbb2222", "main002", "RED", "pytest_fail", 8383, "codex-1"
    )
    assert f2["parked"]

    blocked = cb.admit_lane("lane/router-fix", "bbb2222", contract=contract)
    assert not blocked.admitted
    assert blocked.state == "PARKED_RETRY_CAP"

    # 4. KARMA Firewall: merge without receipt stays FLOW_PENDING (yield=0)
    pending = cb.evaluate_post_merge_receipt("ccc3333", contract, release_receipt=None)
    assert pending.verdict == "FLOW_PENDING"
    assert pending.operational_yield == 0

    # 5. Failed deploy receipt -> NOT_OPERATIONAL + deduplicated incident (#8301)
    failed_receipt = {
        "commit_sha": "ccc3333",
        "status": "NOT_OPERATIONAL",
        "error": "probe_3_failed",
        "rollback_executed": True,
        "rollback_verified": True,
        "probes": [{"round": 1, "passed": False}],
    }
    v_fail = cb.evaluate_post_merge_receipt(
        "ccc3333", contract, release_receipt=failed_receipt
    )
    assert v_fail.verdict == "NOT_OPERATIONAL"
    assert v_fail.operational_yield == 0
    assert any(a["type"] == "OPEN_INCIDENT" for a in v_fail.actions)

    # Second identical failure updates existing incident instead of spawning duplicate
    v_fail_2 = cb.evaluate_post_merge_receipt(
        "ddd4444", contract, release_receipt={**failed_receipt, "commit_sha": "ddd4444"}
    )
    assert any(
        a["type"] == "UPDATE_INCIDENT" and a["occurrences"] == 2
        for a in v_fail_2.actions
    )

    # 6. Matching SHA + 3/3 passed blackbox rounds -> OPERATIONAL (yield=1)
    ok_receipt = {
        "commit_sha": "eee5555",
        "status": "OPERATIONAL",
        "probes": [
            {"round": 1, "passed": True},
            {"round": 2, "passed": True},
            {"round": 3, "passed": True},
        ],
    }
    v_ok = cb.evaluate_post_merge_receipt(
        "eee5555", contract, release_receipt=ok_receipt
    )
    assert v_ok.verdict == "OPERATIONAL"
    assert v_ok.operational_yield == 1
