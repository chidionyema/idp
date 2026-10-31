"""Falsifiers for bin/decision-frame and catalog/decision-protocol.json."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader(
    "decision_frame", str(ROOT / "bin" / "decision-frame")
)
_s = importlib.util.spec_from_loader("decision_frame", _l)
df = importlib.util.module_from_spec(_s)
_l.exec_module(df)
CAT = df.load()


def sit(**kw):
    base = dict(
        decision="d",
        kind="choose-work",
        reversibility="reversible",
        outward_facing=False,
        blast="claim",
        novelty="precedent",
        evidence={"measured": True, "confidence": 0.9},
    )
    base.update(kw)
    return base


def test_missing_perception_is_gather_not_guess():
    s = sit()
    del s["evidence"]
    r = df.frame(s)
    assert r["action"] == "GATHER" and "evidence" in r["perceived"]["missing"]


def test_malformed_value_is_refused():
    assert df.frame(sit(reversibility="maybe"))["action"] == "REFUSE"


def test_hard_law_refuses_and_names_the_law():
    r = df.frame(sit(tags=["push-main"]))
    assert r["action"] == "REFUSE" and r["why"].startswith("L-no-pr-no-main")


def test_irreversible_or_outward_escalates_to_judgment():
    for kw in (dict(reversibility="irreversible"), dict(outward_facing=True)):
        r = df.frame(sit(**kw))
        assert (r["action"], r["decider"], r["irreducibility"]) == (
            "ESCALATE",
            "judgment",
            "irreversible",
        )


def test_unmeasured_is_gather():
    assert df.frame(sit(evidence={"measured": False}))["action"] == "GATHER"


def test_bug_outside_claim_is_recorded_not_fixed():
    r = df.frame(sit(kind="bug-found", claim_paths_ok=False, blocks_work=False))
    assert r["action"] == "PROCEED" and r["record"] == "finding"


def test_blocking_bug_outside_claim_checks_ownership_first():
    r = df.frame(sit(kind="bug-found", claim_paths_ok=False, blocks_work=True))
    assert r["action"] == "GATHER" and "claim" in r["why"]


def test_blocker_without_evidence_is_not_a_blocker():
    assert df.frame(sit(kind="blocker"))["action"] == "GATHER"


def test_reversible_blocker_means_try_another_way_irrevocable_escalates():
    assert (
        df.frame(sit(kind="blocker", blocker_evidence="exit 1: line"))["action"]
        == "PROCEED"
    )
    r = df.frame(sit(kind="blocker", blocker_evidence="exit 1: line", irrevocable=True))
    assert r["action"] == "ESCALATE"


def test_incommensurable_goals_are_a_value_tradeoff():
    r = df.frame(sit(kind="competing-goals", incommensurable=True))
    assert r["irreducibility"] == "value-tradeoff"


def test_no_rule_low_confidence_escalates_and_high_confidence_uses_model():
    low = df.frame(
        sit(rule_decides=False, evidence={"measured": True, "confidence": 0.5})
    )
    assert (low["action"], low["irreducibility"]) == (
        "ESCALATE",
        "low-confidence-escalation",
    )
    high = df.frame(
        sit(rule_decides=False, evidence={"measured": True, "confidence": 0.8})
    )
    assert (high["action"], high["decider"]) == ("PROCEED", "model")
    none = df.frame(sit(rule_decides=False, evidence={"measured": True}))
    assert none["action"] == "ESCALATE"


def test_novel_and_wide_escalates_novel_and_local_probes():
    wide = df.frame(sit(novelty="none", blast="estate"))
    assert wide["irreducibility"] == "novel"
    local = df.frame(sit(novelty="none", blast="local"))
    assert local["action"] == "PROCEED" and local["record"] == "decision"


def test_estate_scope_model_decision_adds_consensus_and_repeat_adds_bandit():
    r = df.frame(sit(rule_decides=False, blast="estate", repeated=True))
    ids = [m["id"] for m in r["methods"]]
    assert "M-consensus-vote" in ids and "M-bandit" in ids


def test_ranking_follows_registry_order_then_claim_then_value():
    rank = df.critical_rank()
    first, second = sorted(rank, key=lambda k: rank[k][0])[:2]
    cands = [
        dict(id="easy", value=9),
        dict(id="b", serves=[second]),
        dict(id="a", serves=[first]),
        dict(id="law", breaks_law=True, serves=[first]),
    ]
    order = [c["id"] for c in df.frame(sit(candidates=cands), rank=rank)["ranking"]]
    assert order == ["a", "b", "easy", "law"]


def test_every_law_has_a_source_that_exists_and_valid_effect():
    for l in CAT["laws"]:
        assert l["effect"] in {"REFUSE", "REQUIRE", "ESCALATE", "ADVISE"}
        src = l["source"]
        assert src.startswith(("AGENTS.md", "founder-judgement")), src
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for l in CAT["laws"]:
        if l["source"].startswith("AGENTS.md section "):
            n = l["source"].split("section ")[1].split()[0]
            assert (
                ("## %s." % n in agents)
                or ("## %s " % n in agents)
                or (" %s. " % n in agents)
            ), l["id"]


def test_every_method_has_a_decider_status_and_existing_impl_when_it_exists():
    for m in CAT["methods"]:
        assert m["decider"] in {"machine", "model", "judgment"} and m["status"] in {
            "exists",
            "proposed",
        }
    for path in (
        "packages/method_selector",
        "bin/estate-diagnose",
        "bin/tlc-check",
        "platform/estate/libexec/jev-decide.py",
    ):
        assert (ROOT / path).exists(), path


def test_every_framed_method_id_is_in_the_catalog():
    ids = {m["id"] for m in CAT["methods"]}
    for kind in CAT["kinds"]:
        for mode in ("machine", "model", "judgment"):
            for m in df.methods_for(kind, sit(), CAT, mode):
                assert m["id"] in ids
