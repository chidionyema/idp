"""The estate's strict contracts (estate_contract): every kind refuses what the estate's gates refuse.

Founder 2026-11-14 20:43: strict Pydantic schemas for everything, estate-wide. Each test uses a real
estate record where one exists (CLAIM comments, commit trailers, proof blocks and defect records as they
appear on idp and argon today) and a falsifier for every rule.
"""

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from estate_contract import (  # noqa: E402
    KINDS,
    AgentTurn,
    ClaimComment,
    CommitTrailers,
    DefectControl,
    FounderAsk,
    ModelLane,
    ProofBlock,
)
from estate_contract.models import RUNNER_LINES  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "estate_contract"
ASK = {
    "question": "Put the backup model router live now?",
    "why": "Your coding tools keep working when the Mac sleeps.",
    "choices": [
        {
            "label": "Yes, put it live",
            "url": "https://github.com/chidionyema/idp/pull/1",
        }
    ],
    "if_no_answer": "Nothing changes and I ask again tomorrow.",
}
TURN = {
    "protocol": "GEN-PROTO-001",
    "instruction": "I-0047",
    "role": "agent",
    "act": "inform",
    "command": None,
    "claims": [],
    "action_url": None,
    "payload": None,
    "ask": None,
}


def test_every_kind_is_strict_and_frozen():
    for name, model in KINDS.items():
        cfg = model.model_config
        assert cfg.get("extra") == "forbid" and cfg.get("frozen") is True, name


def test_exported_schemas_match_the_models():
    for name, model in KINDS.items():
        committed = json.loads(
            (ROOT / "schema" / "estate-contract" / f"{name}.schema.json").read_text()
        )
        assert committed == model.model_json_schema(by_alias=True), (
            f"{name}: run bin/estate-contract schema schema/estate-contract"
        )


# ----------------------------------------------------------------- founder ask


def test_a_plain_one_tap_ask_validates():
    FounderAsk.model_validate(ASK)
    phone = dict(
        ASK,
        choices=[
            {
                "label": "Make it private",
                "url": "https://github.com/o/r/settings",
                "code": "66",
            }
        ],
    )
    FounderAsk.model_validate(phone)


@pytest.mark.parametrize(
    "change, why",
    [
        ({"question": "Merge the PR now?"}, "machine words"),
        ({"why": "See bin/idp-otto-homes for the fix."}, "file path"),
        ({"why": "It lands 21b3d47f8050 today."}, "hex id"),
        ({"question": "Put it live now"}, "question mark"),
        (
            {"choices": [{"label": "Yes", "url": "https://x.example/1"}] * 4},
            "at most 3",
        ),
        ({"choices": [{"label": "Yes", "url": "http://x.example/1"}]}, "pattern"),
        (
            {
                "choices": [
                    {
                        "label": "Approve",
                        "url": "https://github.com/o/r",
                        "code": "123456",
                    }
                ]
            },
            "pattern",
        ),
        (
            {
                "choices": [
                    {
                        "label": "Approve",
                        "url": "https://elsewhere.example/r",
                        "code": "12",
                    }
                ]
            },
            "approval app",
        ),
        ({"extra": "field"}, "Extra inputs"),
    ],
)
def test_an_ask_outside_the_founder_voice_is_refused(change, why):
    with pytest.raises(ValidationError) as e:
        FounderAsk.model_validate(dict(ASK, **change))
    assert why.lower() in str(e.value).lower()


# ----------------------------------------------------------------- agent turn


def test_a_turn_validates_and_its_rules_hold():
    AgentTurn.model_validate(TURN)
    ask = dict(ASK)
    AgentTurn.model_validate(
        dict(TURN, act="request", ask=ask, action_url=ask["choices"][0]["url"])
    )
    with pytest.raises(ValidationError, match="carries an ask"):
        AgentTurn.model_validate(dict(TURN, act="request"))
    with pytest.raises(ValidationError, match="only a request"):
        AgentTurn.model_validate(dict(TURN, ask=ask))
    with pytest.raises(ValidationError, match="action_url"):
        AgentTurn.model_validate(
            dict(TURN, act="request", ask=ask, action_url="https://elsewhere.example/x")
        )
    with pytest.raises(ValidationError):
        AgentTurn.model_validate(dict(TURN, instruction="0047"))
    with pytest.raises(ValidationError, match="Extra inputs"):
        AgentTurn.model_validate(dict(TURN, narration="all good"))


def test_types_are_never_coerced():
    payload = {
        "status": "DEMO_STAGED",
        "instruction_id": "I-0047",
        "branch": "lane/x",
        "commit": "21b3d47f8050",
        "remote_verified": True,
        "tests_passed": "12",
        "tests_failed": 0,
        "demo_manifest": "d",
        "yield_endpoint": "y",
        "proof_hash": None,
    }
    with pytest.raises(ValidationError):
        AgentTurn.model_validate(dict(TURN, payload=payload))  # "12" is not 12
    with pytest.raises(ValidationError):
        AgentTurn.model_validate(
            dict(TURN, payload=dict(payload, tests_passed=12, tests_failed=1))
        )
    AgentTurn.model_validate(dict(TURN, payload=dict(payload, tests_passed=12)))


# ----------------------------------------------------------------- claims, trailers, proof

REAL_CLAIMS = [  # as posted on idp issues on 2026-11-14
    "CLAIM agent=claude paths=bin/idp-otto-homes,bin/idp-bootstrap-cloudflare,tests/test_otto_homes_resolve_account.py heartbeat=2026-11-14T20:21:40Z",
    "CLAIM agent=codex-retired-substrate-20261114 paths=bin/idp-oke-break-glass,bin/idp-oke-rebuild,bin/idp-oke-surge-node heartbeat=2026-11-14T14:54:57Z",
]


@pytest.mark.parametrize("text", REAL_CLAIMS)
def test_real_claim_comments_validate(text):
    assert ClaimComment.parse(text).paths


@pytest.mark.parametrize(
    "text",
    [
        "CLAIM agent=claude paths=/etc/passwd heartbeat=2026-11-14T20:21:40Z",
        "CLAIM agent=claude paths=bin/../../x heartbeat=2026-11-14T20:21:40Z",
        "CLAIM agent=claude paths=bin/x heartbeat=2026-11-14T20:21:40+01:00",
        "CLAIM agent=c paths=bin/x heartbeat=2026-11-14T20:21:40Z",
        "I claim bin/x",
    ],
)
def test_bad_claim_comments_are_refused(text):
    with pytest.raises((ValidationError, ValueError)):
        ClaimComment.parse(text)


def test_commit_trailers_mirror_the_gates():
    real = "fix(x): y\n\nGenesis-Resolves: estate_executor\nClaim: chidionyema/idp#7814\nAgent: claude\nX-Idp-Signed: 6027127996d7eca0563d79e35c\n"
    t = CommitTrailers.parse(real)
    assert (
        t.claims == ["chidionyema/idp#7814"] and t.genesis_resolves == "estate_executor"
    )
    assert CommitTrailers.parse("x\n\nClaim: #7467\nAgent: claude\n").claims == [
        "#7467"
    ]
    for bad in (
        "x\n\nAgent: claude\n",
        "x\n\nClaim: #1\nAgent: a1\nAgent: b2\n",
        "x\n\nClaim: idp-7814\nAgent: claude\n",
    ):
        with pytest.raises((ValidationError, ValueError)):
            CommitTrailers.parse(bad)


def test_proof_blocks_need_a_head_and_a_runner_or_lander_line():
    assert ProofBlock.parse(
        "BDD-PROOF\nhead: 21b3d47f8050\n12 passed in 0.09s\nEND-BDD-PROOF"
    ).proves("21b3d47f80501234")
    ProofBlock.parse(
        "BDD-PROOF\nhead: abc1234\nrequired checks green on candidate 1d09575c8600: fast-gate, bdd\nEND-BDD-PROOF"
    )
    for bad in (
        "no block",
        "BDD-PROOF\n12 passed in 1s\nEND-BDD-PROOF",
        "BDD-PROOF\nhead: abc1234\ntests passed\nEND-BDD-PROOF",
        "BDD-PROOF\nhead: abc1234\n0 passed in 1s\nEND-BDD-PROOF",
    ):
        with pytest.raises((ValidationError, ValueError)):
            ProofBlock.parse(bad)


def test_the_proof_contract_and_the_proof_gate_are_one_rule():
    path = str(ROOT / "bin" / "idp-bdd-proof-gate")
    loader = importlib.machinery.SourceFileLoader("idp_bdd_proof_gate", path)
    spec = importlib.util.spec_from_loader("idp_bdd_proof_gate", loader)
    gate = importlib.util.module_from_spec(spec)
    loader.exec_module(gate)
    assert [(p.pattern, p.flags) for p in gate.PASS_PATTERNS] == [
        (p.pattern, p.flags) for p in RUNNER_LINES
    ]


# ----------------------------------------------------------------- governance records


def test_real_argon_defect_records_validate_and_a_bad_status_does_not():
    records = json.loads((FIX / "argon-defects.json").read_text())
    assert len(records) == 3
    for r in records:
        DefectControl.model_validate(r)
    with pytest.raises(ValidationError):
        DefectControl.model_validate(dict(records[0], status="DONE"))
    with pytest.raises(ValidationError):
        DefectControl.model_validate(dict(records[0], note="prose"))


def test_a_model_lane_names_a_provider_and_a_model():
    ModelLane.model_validate({"provider": "minimax", "model": "MiniMax-M3.1-Flash"})
    with pytest.raises(ValidationError):
        ModelLane.model_validate({"provider": "MiniMax Inc", "model": "x"})


# ----------------------------------------------------------------- the one CLI


def test_the_cli_exits_by_verdict():
    cli = [sys.executable, str(ROOT / "bin" / "estate-contract"), "validate"]
    ok = subprocess.run(
        cli + ["ClaimComment", "-"],
        input=REAL_CLAIMS[0],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ok.returncode == 0 and ok.stdout.strip() == "ok ClaimComment"
    bad = subprocess.run(
        cli + ["FounderAsk", "-"],
        input=json.dumps(dict(ASK, question="Merge the PR?")),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert bad.returncode == 1 and json.loads(bad.stdout)["ok"] is False
    unknown = subprocess.run(
        cli + ["Essay", "-"], input="{}", capture_output=True, text=True, timeout=60
    )
    assert unknown.returncode == 2
