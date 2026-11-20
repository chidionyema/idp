//! The injection is the contract (issue #8302, claim #8345).
use genesis_ground_truth::role_chat::system_message;

#[test]
fn the_live_brief_is_carried_verbatim_before_the_role() {
    let brief = "fence=7 seq=42 merkle_root=abc";
    let msg = system_message("architect", brief);
    assert!(msg.contains(brief), "the brief must appear verbatim");
    assert!(msg.find(brief) < msg.find("architect"), "brief precedes the role");
}

#[test]
fn the_role_may_not_outrank_the_ground_truth() {
    let msg = system_message("any-role", "fence=1");
    assert!(msg.contains("GROUND TRUTH (live, authoritative)"));
    assert!(msg.contains("refused, not returned"));
}
