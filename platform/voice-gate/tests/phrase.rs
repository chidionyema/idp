//! Phrase compiler + span-shrink fixtures (spec §15, HANDOFF item 2).
//!
//! A `voice-policy.yaml` *phrase* is register_lint's BANNED/ADVISORY lexicon shape: a
//! string whose tokens must match case-insensitively, a space in the phrase matching any
//! run of whitespace (so a phrase split across two source lines still fires), on a word /
//! hyphen boundary at both ends. regex-automata has no lookaround, so the compiler
//! emits `(?:^|[^\w-]){body}(?:[^\w-]|$)` and the reported span is the inner capture —
//! the phrase itself, *not* the guard characters that matched around it. That recovered
//! span is what the corpus match-set diff compares, so it must equal register_lint's
//! lookbehind output byte-for-byte on both runtimes.

use voice_gate::phrase::CompiledPhrase;

fn spans(phrase: &str, text: &str) -> Vec<(usize, usize)> {
    CompiledPhrase::new(phrase)
        .expect("complies to a DFA")
        .find(text)
        .into_iter()
        .map(|s| (s.start, s.end))
        .collect()
}

#[test]
fn multiword_phrase_matches_and_reports_inner_span() {
    // Guards (the surrounding space and the trailing "that") are dropped from the span,
    // matching register_lint's `(?<![\w-])... (?![\w-])` which consumes nothing.
    let hits = spans("a testament to", "This draft is a testament to the team.");
    assert_eq!(hits, vec![(14, 28)]); // "a testament to" — 14 characters, 14..28 (guards-free)
    let t = "This draft is a testament to the team.";
    assert_eq!(&t[14..28], "a testament to");
}

#[test]
fn phrase_does_not_fire_inside_a_hyphenated_or_longer_word() {
    // A hyphen is a boundary character for register_lint too: `word-{phrase}` must not
    // match the tail, and `{phrase}word` must not match the head.
    assert_eq!(spans("seamless", "fully-seamless-and-clean"), vec![]);
    assert_eq!(spans("seamless", "coseamlessd"), vec![]);
}

#[test]
fn whitespace_run_across_lines_still_matches() {
    // register_lint joins phrase words with `\s+`, so a line break in the middle of a
    // banned phrase still matches. prose.rs blanks non-prose but preserves `\n`.
    let t = "it's worth\nnoting that the numbers hold";
    let hits = spans("it's worth noting", t);
    assert_eq!(hits.len(), 1);
    let (s, e) = hits[0];
    assert_eq!(&t[s..e], "it's worth\nnoting");
}

#[test]
fn three_token_phrase_reports_trailing_space_guard_correctly() {
    // The end bracket "that" is a guard; the phrase body ends at "noting".
    let t = "It is worth noting that the facts stand.";
    let hits = spans("it is worth noting that", t);
    assert_eq!(hits, vec![(0, 23)]);
    assert_eq!(&t[0..23], "It is worth noting that");
}

#[test]
fn adjective_guard_prevents_false_boundary_on_plural_or_suffix() {
    // "seamlessly" must not be caught by the phrase "seamless": the trailing "ly" is a
    // word char, so the `(?![\w-])` side in register_lint refuses — the `([^\w-]|$)`
    // guard consumes no match and nothing fires.
    assert_eq!(spans("seamless", "integrates seamlessly"), vec![]);
    // ...but the bare word still fires:
    let t = "a seamless integration";
    assert_eq!(spans("seamless", t), vec![(2, 10)]);
}

#[test]
fn case_insensitive_by_default() {
    let t = "DOUBLE DOWN on the plan.";
    let hits = spans("double down", t);
    assert_eq!(hits, vec![(0, 11)]);
}

#[test]
fn phrase_at_text_start_and_end_needs_no_guard_magic() {
    // Zero-width anchors replace both guards, so no character is consumed to shrink.
    let starty = spans("moving forward", "moving forward, we cut costs.");
    assert_eq!(starty, vec![(0, 14)]);
    let endy = spans("look no further", "then look no further");
    assert_eq!(endy, vec![(5, 20)]);
}

#[test]
fn phrase_token_inside_another_word_never_fires() {
    // A token that is merely a substring of a longer word must not match: the guard
    // characters beside the phrase forbid a `[\w-]` neighbour on either side. The
    // caller is responsible for fencing/URL stripping before this runs.
    assert_eq!(spans("turn", "a hard downturn this quarter"), vec![]);
    assert_eq!(spans("sure", "it is not a measure"), vec![]);
    assert_eq!(spans("able", "a separate and reliable source"), vec![]);
}

#[test]
fn phrase_after_leading_punctuation_or_quote_still_matches() {
    // register_lint consumes no guard characters, so the phrase right after punctuation
    // (a `[^\w-]` guard) is found and reported without the guard in the span.
    let t = "Nowhere else: seamless is the only word we sell.";
    let hits = spans("seamless", t);
    assert_eq!(hits, vec![(14, 22)]);
    assert_eq!(&t[14..22], "seamless");
}

#[test]
fn curly_apostrophe_equals_straight_at_unchanged_offsets() {
    // register_lint `_normalise` maps curly → straight before matching. The deny gate and
    // the harness do NOT pre-normalise (that would shift a span's byte offsets and break
    // the diff, which slices the original text). So the phrase compiler reproduces the
    // judge-MENTS as a position-preserving class: a straight `'` in the body also accepts
    // the three curly code points, and the span keeps pointing at the source bytes.
    let t = "the child’s seamless shoes";
    let hits = spans("child's", t);
    assert_eq!(hits, vec![(4, 13)]); // ’ occupies bytes 9..12, so phrase ends after s at 13
    assert_eq!(&t[hits[0].0..hits[0].1], "child’s");

    let straight = "the child's seamless shoes";
    assert_eq!(spans("child's", straight), vec![(4, 11)]);
}
