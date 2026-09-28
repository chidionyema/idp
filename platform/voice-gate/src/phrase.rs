//! The phrase compiler and span shrink (spec §15, HANDOFF item 2).
//!
//! register_lint compiles every BANNED/ADVISORY phrase through a lookbehind/lookahead pair
//!
//! ```text
//! (?<![\w-]){body}(?![\w-])   # register_lint.py:_phrase_re
//! ```
//! where `body` is each phrase word regex-escaped and joined with `\s+`, so a phrase cut
//! across two source lines still matches, and it is refused only when a word *or hyphen*
//! sits directly beside it. `regex-automata` cannot compile lookaround, so this module
//! emits the equivalent DFA-safe form
//!
//! ```text
//! (?:^|[^\w-]){body}(?:[^\w-]|$)
//! ```
//! and then **shrinks the reported span to the inner capture group**, discarding whichever
//! guard characters matched on either side. That recovered span is what register_lint
//! reports (its lookaround consumed nothing), and the corpus match-set diff compares these
//! spans byte-for-byte on both runtimes — so shrink-or-not is the whole parity question.
//!
//! Apostrophes: register_lint runs `_normalise` first, which maps every curly form
//! (`…’…‘…‛`) to the straight `'` before any matching. To reproduce that **without changing
//! the byte length of the prose** (a finding's span maps back to the original text), each
//! straight apostrophe in a phrase token is compiled as a class that also accepts the three
//! curly forms — the net judgement of "curly equals straight" with positions intact.
//!
//! Cases a phrase must *not* fire on live here too: the phrase as a bare substring of a
//! longer word (`turn` in `downturn`), adjacent to a hyphen (`seamless` in
//! `fully-seamless`), and a phrase followed by a word suffix (`seamless` vs `seamlessly`).
//! The caller passes already-prose-only text (fences/URLs/tables/quotes stripped); phrase
//! matching assumes it, exactly as register_lint runs on its own `_normalise`d text.

use regex_automata::meta::Regex;

/// A phrase compiled to a DFA the same shape a deny pattern uses. Apostrophes: the token
/// class below lets a straight `'` stand for any of the curly forms register_lint's
/// `_normalise` maps to straight before matching, at unchanged byte positions.
pub struct CompiledPhrase {
    re: Regex,
}

/// A single spans-free phrase occurrence in the prose.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PhraseSpan {
    pub start: usize,
    pub end: usize,
}

impl CompiledPhrase {
    /// Build the DFA for a register_lint phrase. `phrase` is `"a testament to"` shaped:
    /// tokens are split on whitespace and re-joined by an any-whitespace-run matcher.
    ///
    /// * Case-insensitive (register_lint compiles phrases with `re.I`).
    /// * `^`/`$` are string anchors (register_lint applies no `re.M` to phrases; a newline
    ///   between the guards is a `[^\w-]` character and matches the guard normally).
    ///
    /// Returns `Err` when the phrase collapses to nothing (no non-whitespace token) or the
    /// pattern is not DFA-expressible (should be impossible for escaped literals).
    pub fn new(phrase: &str) -> Result<Self, String> {
        let tokens: Vec<&str> = phrase.split_whitespace().collect();
        if tokens.is_empty() {
            return Err("phrase has no tokens".to_string());
        }
        let body: Vec<String> = tokens.iter().map(|w| escape_token(w)).collect();
        let joined = body.join(r"\s+");
        // `(?:^|[^\w-])(BODY)(?:[^\w-]|$)` — group 1 is the guards-free phrase. The `m`
        // flag is intentionally absent (see module doc). Compiled with `i` for parity.
        let pat = format!("(?i)(?:^|[^\\w-])({joined})(?:[^\\w-]|$)");
        let re =
            Regex::new(&pat).map_err(|e| format!("phrase `{phrase}` failed to compile: {e}"))?;
        Ok(Self { re })
    }

    /// Run the compiled phrase over prose-only text, returning every guards-free span in
    /// scan order. `text` is expected prose-only (no fences/URLs/etc.); newlines are
    /// allowed and a token break may straddle one.
    pub fn find(&self, text: &str) -> Vec<PhraseSpan> {
        let mut out = Vec::new();
        let mut last = 0usize;
        for caps in self.re.captures_iter(text) {
            if let Some(g) = caps.get_group(1) {
                if g.start >= last {
                    out.push(PhraseSpan { start: g.start, end: g.end });
                    last = g.end;
                }
            }
        }
        out
    }
}

/// Escaped phrase token with apostrophes widened. `re.escape` in register_lint leaves a
/// straight `'` literal in the body (it is not a metacharacter); here that literal is
/// replaced so it also matches the three curly apostrophe code points, reproducing
/// `_normalise`'s curly→straight sweep without shifting any byte offset.
fn escape_token(s: &str) -> String {
    let escaped = regex_escape(s);
    if !escaped.contains('\'') {
        return escaped;
    }
    let mut out = String::with_capacity(escaped.len() + 16);
    for c in escaped.chars() {
        if c == '\'' {
            // straight + right/left single quote + single high-reversed-9
            out.push_str("[\\u2018\\u2019\\u201B']");
        } else {
            out.push(c);
        }
    }
    out
}

fn regex_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '\\' | '.' | '+' | '*' | '?' | '(' | ')' | '|' | '[' | ']' | '{' | '}' | '^'
            | '$' | '#' | '&' | '-' | '~' => {
                out.push('\\');
                out.push(c);
            }
            _ => out.push(c),
        }
    }
    out
}
