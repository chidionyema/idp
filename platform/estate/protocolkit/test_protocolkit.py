# ruff: noqa
# fmt: off
import pytest

from protocolkit import *  # noqa
from protocolkit import Ctx, FounderPrompt, audit, compile_system_prompt, GenesisError

S = Stage
EV = Evidence("e1", "docs.example/a", "The service rate limit is 100 requests per minute per key.")
EV2 = Evidence("e2", "blog.example/b", "Rate limits were raised to 500 requests per minute in 2025.")


def grounded_up_to_proofset():
    r = Run(GROUNDED_INQUIRY)
    r.submit(S.INVOCATION, Invocation("what is the rate limit?"))
    r.submit(S.INSTRUCTION, Instruction("answer from docs"))
    r.submit(S.DISCOVERY, Discovery((EV,)))
    return r


GOOD_PS = ClaimProofSet(
    (Claim("c1", "The rate limit is 100 requests per minute per key."),),
    (Proof("c1", "e1", "rate limit is 100 requests per minute"),),
)


def test_grounded_happy_path():
    r = grounded_up_to_proofset()
    r.submit(S.CLAIMSET_PROOFSET, GOOD_PS)
    r.submit(S.RESPONSE, Response((Segment("text", text="Per the docs:"), Segment("claim", claim_id="c1"))))
    assert "100 requests per minute" in r.egress()
    assert r.verify_log()


def test_cannot_skip_discovery():
    r = Run(GROUNDED_INQUIRY)
    r.submit(S.INVOCATION, Invocation("q"))
    r.submit(S.INSTRUCTION, Instruction("d"))
    with pytest.raises(ProtocolViolation, match="out of order"):
        r.submit(S.CLAIMSET_PROOFSET, GOOD_PS)


def test_fabricated_quote_rejected():
    r = grounded_up_to_proofset()
    bad = ClaimProofSet(GOOD_PS.claims, (Proof("c1", "e1", "the limit is 9000 requests per minute"),))
    with pytest.raises(ProtocolViolation, match="verbatim"):
        r.submit(S.CLAIMSET_PROOFSET, bad)


def test_evidence_not_retrieved_rejected():
    r = grounded_up_to_proofset()
    bad = ClaimProofSet(GOOD_PS.claims, (Proof("c1", "e99", "rate limit is 100 requests"),))
    with pytest.raises(ProtocolViolation, match="not retrieved"):
        r.submit(S.CLAIMSET_PROOFSET, bad)


def test_claim_without_proof_rejected():
    r = grounded_up_to_proofset()
    with pytest.raises(ProtocolViolation, match="no valid proof"):
        r.submit(S.CLAIMSET_PROOFSET, ClaimProofSet(GOOD_PS.claims, ()))


def test_entailment_hook_can_veto():
    r = Run(GROUNDED_INQUIRY, ctx=Ctx(entailment=lambda claim, ev, quote: False))
    r.submit(S.INVOCATION, Invocation("q"))
    r.submit(S.INSTRUCTION, Instruction("d"))
    r.submit(S.DISCOVERY, Discovery((EV,)))
    with pytest.raises(ProtocolViolation, match="entail"):
        r.submit(S.CLAIMSET_PROOFSET, GOOD_PS)


def test_response_cannot_smuggle_unproved_facts():
    r = grounded_up_to_proofset()
    r.submit(S.CLAIMSET_PROOFSET, GOOD_PS)
    with pytest.raises(ProtocolViolation, match="digits"):
        r.submit(S.RESPONSE, Response((Segment("text", text="It's actually 500 now."), Segment("claim", claim_id="c1"))))
    with pytest.raises(ProtocolViolation, match="not in the proved claimset"):
        r.submit(S.RESPONSE, Response((Segment("claim", claim_id="c2"),)))


def test_egress_blocked_until_finished():
    r = grounded_up_to_proofset()
    with pytest.raises(ProtocolViolation, match="cannot respond"):
        r.egress()


def test_repeated_violations_abort():
    r = Run(GROUNDED_INQUIRY, max_attempts=2)
    for _ in range(2):
        with pytest.raises(ProtocolViolation):
            r.submit(S.RESPONSE, Response((Segment("text", text="hi"),)))
    with pytest.raises(RunAborted):
        r.submit(S.INVOCATION, Invocation("q"))


def test_log_tamper_detected():
    r = grounded_up_to_proofset()
    r.log[0]["ok"] = False
    assert not r.verify_log()


# ---- execution ---------------------------------------------------------
PLAN = Plan((Step("write", "/repo/a.txt"), Step("delete", "/repo/old.txt", reversible=False)))


def exec_up_to_commit(plan=PLAN, keys=None):
    ctx = Ctx(committed_keys=keys if keys is not None else set())
    r = Run(EXECUTION, ctx=ctx)
    r.submit(S.INVOCATION, Invocation("tidy repo"))
    r.submit(S.INSTRUCTION, Instruction("deploy"))
    r.submit(S.STATE_ASSESSMENT, Assessment("snap1", ("/repo/",)))
    r.submit(S.ACTION_PLAN_DRY_RUN, ActionPlanDryRun(plan, DryRunResult(plan.digest(), True, {"no_conflicts": True})))
    return r


def test_execution_happy_path():
    r = exec_up_to_commit()
    r.submit(S.COMMIT, Commit(PLAN.digest(), "snap1", "k1", approvals=("delete:/repo/old.txt",)))
    r.submit(S.RESPONSE, Response((Segment("receipt", text="k1"),)))
    assert "committed k1" in r.egress()


def test_irreversible_needs_approval():
    r = exec_up_to_commit()
    with pytest.raises(ProtocolViolation, match="lacks explicit approval"):
        r.submit(S.COMMIT, Commit(PLAN.digest(), "snap1", "k1"))


def test_plan_swap_and_drift_rejected():
    r = exec_up_to_commit()
    other = Plan((Step("write", "/repo/other.txt"),))
    with pytest.raises(ProtocolViolation, match="differs from the dry-run"):
        r.submit(S.COMMIT, Commit(other.digest(), "snap1", "k1"))
    with pytest.raises(ProtocolViolation, match="drifted"):
        r.submit(S.COMMIT, Commit(PLAN.digest(), "snap2", "k1", approvals=("delete:/repo/old.txt",)))


def test_out_of_scope_and_failed_dry_run_rejected():
    r = Run(EXECUTION)
    r.submit(S.INVOCATION, Invocation("x"))
    r.submit(S.INSTRUCTION, Instruction("x"))
    r.submit(S.STATE_ASSESSMENT, Assessment("snap1", ("/repo/",)))
    p = Plan((Step("write", "/etc/passwd"),))
    with pytest.raises(ProtocolViolation, match="outside permitted scope"):
        r.submit(S.ACTION_PLAN_DRY_RUN, ActionPlanDryRun(p, DryRunResult(p.digest(), True, {"ok": True})))
    p2 = Plan((Step("write", "/repo/x"),))
    with pytest.raises(ProtocolViolation, match="did not pass"):
        r.submit(S.ACTION_PLAN_DRY_RUN, ActionPlanDryRun(p2, DryRunResult(p2.digest(), False, {"ok": False})))
    with pytest.raises(ProtocolViolation, match="digest mismatch"):
        r.submit(S.ACTION_PLAN_DRY_RUN, ActionPlanDryRun(p2, DryRunResult("deadbeef", True, {"ok": True})))


def test_replay_rejected():
    keys = {"k1"}
    r = exec_up_to_commit(keys=keys)
    with pytest.raises(ProtocolViolation, match="replay"):
        r.submit(S.COMMIT, Commit(PLAN.digest(), "snap1", "k1", approvals=("delete:/repo/old.txt",)))


def test_execution_response_needs_matching_receipt():
    r = exec_up_to_commit()
    r.submit(S.COMMIT, Commit(PLAN.digest(), "snap1", "k1", approvals=("delete:/repo/old.txt",)))
    with pytest.raises(ProtocolViolation, match="receipt"):
        r.submit(S.RESPONSE, Response((Segment("text", text="Done."),)))


# ---- deep synthesis ----------------------------------------------------
def synth_up_to_resolution(status):
    r = Run(DEEP_SYNTHESIS)
    r.submit(S.INVOCATION, Invocation("what is the rate limit?"))
    r.submit(S.INSTRUCTION, Instruction("research"))
    r.submit(S.DIVERGENT_DISCOVERY, Discovery((EV, EV2)))
    c = Contradiction("x1", ("e1", "e2"), status,
                      rationale="newer source" if status == "resolved" else "",
                      preferred_evidence_id="e2" if status == "resolved" else None)
    r.submit(S.CONTRADICTION_RESOLUTION, ContradictionReport(("e1", "e2"), (c,)))
    return r


def test_single_source_rejected():
    r = Run(DEEP_SYNTHESIS)
    r.submit(S.INVOCATION, Invocation("q"))
    r.submit(S.INSTRUCTION, Instruction("d"))
    with pytest.raises(ProtocolViolation, match="independent sources"):
        r.submit(S.DIVERGENT_DISCOVERY, Discovery((EV,)))


def test_detector_must_examine_everything():
    r = Run(DEEP_SYNTHESIS)
    r.submit(S.INVOCATION, Invocation("q"))
    r.submit(S.INSTRUCTION, Instruction("d"))
    r.submit(S.DIVERGENT_DISCOVERY, Discovery((EV, EV2)))
    with pytest.raises(ProtocolViolation, match="examined"):
        r.submit(S.CONTRADICTION_RESOLUTION, ContradictionReport(("e1",), ()))


def test_resolved_synthesis_happy_path():
    r = synth_up_to_resolution("resolved")
    ps = ClaimProofSet(
        (Claim("c1", "The current limit is 500 requests per minute."),),
        (Proof("c1", "e2", "raised to 500 requests per minute"),),
    )
    r.submit(S.UNIFIED_CLAIMSET_PROOFSET, ps)
    r.submit(S.RESPONSE, Response((Segment("claim", claim_id="c1"),)))
    assert "500" in r.egress()


def test_resolved_winner_must_be_cited():
    r = synth_up_to_resolution("resolved")
    ps = ClaimProofSet(GOOD_PS.claims, GOOD_PS.proofs)  # cites e1, not the winner e2
    with pytest.raises(ProtocolViolation, match="no proof cites"):
        r.submit(S.UNIFIED_CLAIMSET_PROOFSET, ps)


def test_unresolved_conflict_must_be_disclosed():
    r = synth_up_to_resolution("unresolved")
    ps = ClaimProofSet(
        (Claim("c1", "One source says 100 per minute.", contested=True),), GOOD_PS.proofs
    )
    r.submit(S.UNIFIED_CLAIMSET_PROOFSET, ps)
    with pytest.raises(ProtocolViolation, match="must be disclosed"):
        r.submit(S.RESPONSE, Response((Segment("claim", claim_id="c1"),)))
    r.submit(S.RESPONSE, Response((Segment("claim", claim_id="c1"), Segment("disclosure", contradiction_id="x1"))))
    assert "unresolved conflict x1" in r.egress()


# ---- genesis -----------------------------------------------------------
def test_genesis_requires_binding():
    with pytest.raises(GenesisError, match="Protocol_Binding"):
        compile_system_prompt(FounderPrompt("a1", "You are an agent."))
    out = compile_system_prompt(FounderPrompt("a2", "You are a research agent.", ProtocolId.DEEP_SYNTHESIS))
    assert out.startswith("Protocol_Binding: [deep_synthesis]")


def test_audit_flags_unbound():
    bad = audit([FounderPrompt("ok", "x", ProtocolId.EXECUTION), FounderPrompt("bad", "y")])
    assert list(bad) == ["bad"]
