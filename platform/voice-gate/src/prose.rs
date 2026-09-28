//! Prose extraction: strip non-prose spans before grading (spec §15).
//!
//! This is a *span-preserving* stripper: removed regions are replaced by spaces so every
//! surviving byte keeps its original offset and a finding's span maps back to the source
//! string exactly. The strip definitions mirror the estate's tested ones in
//! `prospector/register_lint.py` (fence, inline code, URL, table row, quote, heading) —
//! the same semantics on both runtimes, which is what the corpus match-set diff measures.
//! The tree-sitter swap (structure-aware nodes) is a phase-1 task-2 enhancement gated on
//! that diff staying empty.

use regex_automata::meta::Regex;

/// Compiled once; every pattern here is DFA-expressible by construction.
pub struct ProseStripper {
    rules: Vec<Regex>,
}

impl ProseStripper {
    pub fn new() -> Self {
        // Same classes as register_lint.py:248-255, rewritten without lookaround.
        let patterns = [
            r"(?s)```.*?```",                 // fenced code
            r"`[^`\n]+`",                     // inline code
            r"https?://\S+|www\.\S+",         // URLs
            r"(?m)^\s*\|.*\|\s*$",            // table rows
            r"(?m)^\s*>.*$",                  // quote lines
            r"(?m)^\s{0,3}#{1,6}\s.*$",       // headings
        ];
        let rules = patterns
            .iter()
            .map(|p| Regex::new(p).expect("strip patterns are DFA-expressible"))
            .collect();
        Self { rules }
    }

    /// Return a copy of `text` with every non-prose span blanked to spaces
    /// (newlines preserved so line numbers stay stable in findings).
    pub fn prose_only(&self, text: &str) -> String {
        let mut out: Vec<u8> = text.as_bytes().to_vec();
        for rule in &self.rules {
            for m in rule.find_iter(text) {
                for b in &mut out[m.start()..m.end()] {
                    if *b != b'\n' {
                        *b = b' ';
                    }
                }
            }
        }
        String::from_utf8(out).expect("blanking preserves UTF-8 boundaries of ASCII patterns")
    }
}
