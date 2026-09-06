//! Gate fixtures: bad/good pairs for EE1–EE5 (spec §2), enum-field exclusion
//! (the 2026-09-06 phase-0 boundary decision), prose stripping, batch, lanes, schema.

use voice_gate::policy::VoicePolicy;
use voice_gate::tier1::Tier1;

const POLICY: &str = include_str!("../voice-policy.yaml");

fn gate() -> (VoicePolicy, Tier1) {
    let policy = VoicePolicy::from_str(POLICY).expect("fixture policy is valid");
    let tier1 = Tier1::new(&policy).expect("fixture patterns compile");
    (policy, tier1)
}

fn grade(t: &Tier1, p: &VoicePolicy, lane: &str, field: &str, text: &str) -> usize {
    let l = p.lane(lane).expect("lane exists");
    t.grade(lane, l, field, text).len()
}

#[test]
fn ee1_verdict_label_fails() {
    let (p, t) = gate();
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "Do incumbents already own the space?\nSUPPORTED\nNo passage shows a dominant UK incumbent."), 2);
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "The niche is open and rivals are fragmented."), 0);
}

#[test]
fn ee1_english_verb_never_fires_but_caps_label_does() {
    let (p, t) = gate();
    // "supported" the verb is ordinary prose; SUPPORTED the caps label is scaffolding.
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "having supported over 100,000 students"), 0);
    assert!(grade(&t, &p, "evidence-export", "reason", "SUPPORTED") >= 1);
    assert!(grade(&t, &p, "evidence-export", "reason", "Verdict: refuted.") >= 1);
}

#[test]
fn ee2_passage_speak_fails() {
    let (p, t) = gate();
    assert!(grade(&t, &p, "evidence-export", "reason", "No passage shows a funded rival.") >= 1);
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "No funded rival showed up in our research."), 0);
}

#[test]
fn ee3_diligence_framing_fails() {
    let (p, t) = gate();
    assert!(grade(&t, &p, "evidence-export", "premortem", "The strongest case against this idea is cost.") >= 1);
    assert_eq!(grade(&t, &p, "evidence-export", "premortem", "The biggest risk is acquisition cost."), 0);
}

#[test]
fn ee4_numbered_citation_line_fails() {
    let (p, t) = gate();
    assert!(grade(&t, &p, "evidence-export", "reason", "Sources checked:\n1 acas.org.uk\n2 iwgb.org.uk") >= 1);
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "Acas offers broad free advice, not a specialist appeal engine."), 0);
}

#[test]
fn ee5_hedged_research_speak_fails() {
    let (p, t) = gate();
    assert!(grade(&t, &p, "evidence-export", "reason", "No evidence establishes affordability, and the niche appears open in these passages.") >= 1);
}

#[test]
fn enum_fields_are_never_graded() {
    let (p, t) = gate();
    // The phase-0 boundary decision: `gate: "SUPPORTED"` is structured data, not prose.
    assert_eq!(grade(&t, &p, "evidence-export", "gate", "SUPPORTED"), 0);
    assert_eq!(grade(&t, &p, "evidence-export", "gateLabel", "SUPPORTED"), 0);
    assert_eq!(grade(&t, &p, "evidence-export", "verdict", "SUPPORTED"), 0);
    // ...but the same token in a prose field still fires.
    assert!(grade(&t, &p, "evidence-export", "reason", "SUPPORTED") >= 1);
}

#[test]
fn non_prose_spans_are_ignored() {
    let (p, t) = gate();
    // Banned token inside fenced code, inline code and a URL must not fire...
    assert_eq!(grade(&t, &p, "evidence-export", "reason", "```\nSUPPORTED\n```\nsee https://x.test/SUPPORTED for `passages` detail"), 0);
    // ...while the same token in a paragraph does.
    assert!(grade(&t, &p, "evidence-export", "reason", "Verdict: SUPPORTED as written.") >= 1);
}

#[test]
fn spans_map_to_original_text() {
    let (p, t) = gate();
    let text = "See `code` first.\nThen SUPPORTED here.";
    let l = p.lane("evidence-export").unwrap();
    let findings = t.grade("evidence-export", l, "reason", text);
    assert_eq!(findings.len(), 1);
    let span = &findings[0].span;
    assert_eq!(&text[span.start..span.end], "SUPPORTED");
}

#[test]
fn storefront_lane_inherited_by_export_lane() {
    let (p, _t) = gate();
    let export = p.lane("evidence-export").unwrap();
    assert!(export.deny_patterns.len() >= 5, "inheritance resolved");
}

#[test]
fn invalid_policy_is_rejected() {
    assert!(VoicePolicy::from_str("version: 1\nlanes: {}\n").is_err(), "missing rules key fails schema");
    assert!(VoicePolicy::from_str("version: 1\nrules: {}\nlanes:\n  x:\n    deny_patterns:\n      - id: ee1\n        pattern: 'a'\n        message: 'm'\n").is_err(), "lowercase id fails schema");
}

#[test]
fn unknown_lane_is_distinct_from_clean() {
    let (p, _t) = gate();
    assert!(p.lane("does-not-exist").is_none(), "server maps this to 422");
}
