"""#7387: candidate-only recovery must never remove a live production tunnel route."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "plan_tunnel_ingress", ROOT / "platform/oci/recovery/plan_tunnel_ingress.py"
)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


def original():
    return {
        "success": True,
        "result": {
            "config": {
                "originRequest": {"connectTimeout": 30},
                "ingress": [
                    {"hostname": "llm.mumchimp.com", "service": "http://127.0.0.1:4000",
                     "originRequest": {"noTLSVerify": False}},
                    {"hostname": "another.mumchimp.com", "service": "http://127.0.0.1:8080"},
                    {"hostname": "llm-recovery.mumchimp.com", "service": "http://old:4000"},
                    {"service": "http_status:404"},
                ],
            }
        },
    }


def test_candidate_only_preserves_exact_production_and_all_other_rules():
    before = original()
    saved = copy.deepcopy(before)
    result = planner.plan_candidate(before)
    assert before == saved
    assert result["config"]["originRequest"] == saved["result"]["config"]["originRequest"]
    rules = result["config"]["ingress"]
    assert rules[0] == {
        "hostname": "llm-recovery.mumchimp.com",
        "service": "http://127.0.0.1:4000",
    }
    assert rules[1:] == [
        saved["result"]["config"]["ingress"][0],
        saved["result"]["config"]["ingress"][1],
        saved["result"]["config"]["ingress"][3],
    ]


def test_candidate_only_does_not_invent_a_production_cutover():
    before = original()
    before["result"]["config"]["ingress"] = [
        {"hostname": "llm-recovery.mumchimp.com", "service": "http://old:4000"},
        {"service": "http_status:404"},
    ]
    rules = planner.plan_candidate(before)["config"]["ingress"]
    assert [r.get("hostname") for r in rules] == [
        "llm-recovery.mumchimp.com", None,
    ]


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(success=False),
    lambda d: d["result"].update(config=None),
    lambda d: d["result"]["config"].update(ingress=[]),
    lambda d: d["result"]["config"]["ingress"].append({"service": "http_status:404"}),
    lambda d: d["result"]["config"]["ingress"].insert(0, {"service": "http_status:404"}),
    lambda d: d["result"]["config"]["ingress"].append(
        {"hostname": "llm.mumchimp.com", "service": "http://wrong:4000"}
    ),
    lambda d: d["result"]["config"]["ingress"][-1].update(service="http://unknown:4000"),
])
def test_unattested_ambiguous_or_duplicate_config_refuses_without_a_plan(mutate):
    before = original()
    mutate(before)
    with pytest.raises(ValueError, match="BLIND"):
        planner.plan_candidate(before)


def test_workflow_blocks_production_cutover_before_cloudflare_mutation():
    workflow = (ROOT / ".github/workflows/router-recovery.yml").read_text()
    guard = workflow.index('if [ "$CUTOVER" = true ]; then')
    token_mint = workflow.index('out=$(curl -sS -X POST')
    assert guard < token_mint
    assert 'exit 70' in workflow[guard:token_mint]
    assert 'hosts=\'["llm-recovery.mumchimp.com"]\'' in workflow
    assert 'hosts=\'["llm-recovery.mumchimp.com","llm.mumchimp.com"]\'' not in workflow
    assert 'plan_tunnel_ingress.py' in workflow
    assert 'old_prod' in workflow and 'new_prod' in workflow


def test_workflow_refuses_530_and_000_and_requires_real_auth_and_wrong_key():
    workflow = (ROOT / ".github/workflows/router-recovery.yml").read_text()
    health = workflow.split("      - name: The candidate answers", 1)[1]
    assert 'echo "::error::FAIL candidate HTTP $c' in health
    assert 'exit 1' in health.split("      - name: Candidate authenticates", 1)[0]
    assert "v1/chat/completions" in health
    assert "deliberately-invalid-estate-caller" in health
    assert 'for n in 1 2; do' in health
    assert "sleep 30" in health
    assert "bundle-sha256" in health
