//! House-measure parity (HANDOFF item 5 prose_target bands + item 6 sentence split).
//!
//! A faithful Rust mirror of the ARMED grade path of `prospector/prose_measure.py`
//! (`document_measures`, `sentences`) and `prose_target.grade`, with the armed band
//! constants taken verbatim from `prospector/data/prose_target.json`. Deterministic
//! counting and arithmetic over buyer-facing prose — never a hand-written number. The
//! oracle lock proving parity is `tests/house_measure.rs` (SPEC-house-measures.md), whose
//! fixtures were measured by the real Python.
//!
//! Every pattern Python runs with an engine that tolerates lookbehind (`_HYPHEN`,
//! `_SENT_END`, `_ABBREV`) is reproduced here by char scanning to the same result — no
//! lookbehind, which regex-automata's compile could not hold anyway (item 6's reason for
//! hand-writing these).

use std::collections::BTreeMap;

// ---------------------------------------------------------------------------
// Measured constants (verbatim from prose_measure.py / prose_target.json).
// ---------------------------------------------------------------------------

const MATTR_WINDOW: usize = 100;
const HEAVY_SENTENCE_COMMAS: usize = 2;
/// Sentinel swapping in for a protected abbreviation terminal dot during sentence split.
const SENTINEL: char = '\u{0}';

/// Hedges counted per 1,000 words (prose_measure.HEDGES, verbatim).
const HEDGES: &[&str] = &[
    "may", "might", "could", "would", "should", "possibly", "probably", "perhaps",
    "likely", "unlikely", "apparently", "seems", "seem", "seemed", "appears", "appear",
    "appeared", "suggests", "suggest", "suggested", "indicates", "indicate", "arguably",
    "potentially", "generally", "typically", "usually", "often", "sometimes", "somewhat",
    "relatively", "broadly", "largely", "mostly", "partly", "presumably", "conceivably",
    "plausibly", "tends", "tend", "tended",
];

/// Abbreviation words (prose_measure._ABBREV), lowercased, dotted literal for e.g/i.e.
const ABBREVS: &[&str] = &[
    "mr", "mrs", "ms", "dr", "prof", "ltd", "plc", "inc", "co", "no", "vs", "e.g",
    "i.e", "etc", "approx", "fig", "para",
];

/// Arithmetic parity for the six ARMED bands (prose_target.json measures[*]):
/// (p5, p95, human_mean, human_sd). Authorised constants — do not round or shorten them.
fn band_spec() -> BTreeMap<&'static str, (f64, f64, f64, f64)> {
    let mut m = BTreeMap::new();
    m.insert("heavy_sentence_rate", (0.0312, 0.3036, 0.1572, 0.0856));
    m.insert("hedges_per_1k", (5.6711, 23.0516, 13.7885, 5.9086));
    m.insert("mattr", (0.6317, 0.7083, 0.6718, 0.0239));
    m.insert("punct_comma_per_1k", (13.267, 49.1096, 31.8337, 10.4331));
    m.insert("punct_semicolon_per_1k", (0.0, 3.7244, 0.7489, 1.3553));
    m.insert("punct_hyphen_per_1k", (0.694, 7.0547, 2.7199, 2.57));
    m
}

// ---------------------------------------------------------------------------
// Tokenisation (mirrors prose_measure.tokens).
// ---------------------------------------------------------------------------

/// `[a-z][a-z'’-]*` over the lowercased text (str.lower() ASCII-lowered, same as Python's
/// casefold for ASCII). Requires a leading ASCII lowercase, so numbers/currency are dropped.
pub fn word_tokens(text: &str) -> Vec<String> {
    let lc: Vec<char> = text.chars().map(|c| c.to_ascii_lowercase()).collect();
    let (mut out, n) = (Vec::new(), lc.len());
    let mut i = 0;
    while i < n {
        if lc[i].is_ascii_lowercase() {
            let start = i;
            i += 1;
            while i < n
                && (lc[i].is_ascii_lowercase()
                    || lc[i] == '\''
                    || lc[i] == '\u{2019}'
                    || lc[i] == '-')
            {
                i += 1;
            }
            out.push(lc[start..i].iter().collect());
        } else {
            i += 1;
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Sentence segmentation (mirrors prose_measure.sentences / _SENT_END / _ABBREV).
// ---------------------------------------------------------------------------

/// Guard abbreviation terminal dots by swapping them (and the internal dots of a dotted
/// token, exactly as `_ABBREV.sub(replace, text)` does) for the in-band sentinel.
fn guard_abbrevs(text: &str) -> Vec<char> {
    let chars: Vec<char> = text.chars().collect();
    let n = chars.len();
    let mut guarded = chars.clone();
    let mut i = 0usize;
    while i < n {
        if chars[i] == '.' && i > 0 {
            // walk back over the token chars ([A-Za-z.]) ending just before the dot
            let mut j = i;
            while j > 0
                && (chars[j - 1].is_ascii_alphabetic() || chars[j - 1] == '.')
            {
                j -= 1;
            }
            let token: String = chars[j..i].iter().collect();
            let lower: String = token.chars().map(|c| c.to_ascii_lowercase()).collect();
            // remove a trailing dot inside the token (dotted forms keep none at the cut)
            let key = lower.trim_end_matches('.').to_string();
            if ABBREVS.contains(&key.as_str()) {
                for idx in j..=i {
                    if chars[idx] == '.' {
                        guarded[idx] = SENTINEL;
                    }
                }
            }
        }
        i += 1;
    }
    guarded
}

/// Apply `_SENT_END.split` semantics over one (already guarded) paragraph, returning the
/// non-empty sentence strings, sentinel restored and whitespace-stripped. `re.split`
/// drops the separator, keeps a sentence's trailing `.`/`!`/`?`.
fn split_part_sentences(guard: &[char]) -> Vec<String> {
    let n = guard.len();
    let mut out = Vec::new();
    let mut piece_start = 0usize;
    let mut i = 1usize;
    while i < n {
        if matches!(guard[i - 1], '.' | '!' | '?') {
            // consume optional closing run then \s+
            let mut k = i;
            while k < n && matches!(guard[k], '"' | '\'' | ')' | ']') {
                k += 1;
            }
            let wsp = k;
            while k < n && guard[k].is_whitespace() {
                k += 1;
            }
            if k > wsp {
                // lookahead: optional open run then ASCII [A-Z0-9]
                let mut o = k;
                while o < n && matches!(guard[o], '"' | '\'' | '(' | '[') {
                    o += 1;
                }
                let lead_ok = o < n && (guard[o].is_ascii_uppercase() || guard[o].is_ascii_digit());
                if lead_ok {
                    // boundary at i: prior piece is [piece_start, i)
                    let raw: String = guard[piece_start..i].iter().collect();
                    let s = raw.replace(SENTINEL, ".").trim().to_string();
                    if !s.is_empty() {
                        out.push(s);
                    }
                    piece_start = k; // separator (closer + space) consumed
                    i = k;
                    continue;
                }
            }
        }
        i += 1;
    }
    let tail: String = guard[piece_start..n].iter().collect();
    let s = tail.replace(SENTINEL, ".").trim().to_string();
    if !s.is_empty() {
        out.push(s);
    }
    out
}

/// Mirror prose_measure.sentences(text): guard abbreviation dots in the whole text, split
/// paragraphs on blank lines (`\n\s*\n`), then `_SENT_END`-split each paragraph.
pub fn split_sentences(text: &str) -> Vec<String> {
    let guard = guard_abbrevs(text);
    let mut result = Vec::new();
    let n = guard.len();
    let mut start = 0usize;
    let mut i = 0usize;
    while i < n {
        if guard[i] == '\n' {
            let mut j = i + 1;
            // consume spaces/tabs between the two newlines
            while j < n && (guard[j] == ' ' || guard[j] == '\t' || guard[j] == '\u{a0}') {
                j += 1;
            }
            if j < n && guard[j] == '\n' {
                if start < i {
                    let mut part = split_part_sentences(&guard[start..i]);
                    result.append(&mut part);
                }
                start = j + 1;
                i = j + 1;
                continue;
            }
        }
        i += 1;
    }
    let mut part = split_part_sentences(&guard[start..n]);
    result.append(&mut part);
    result
}

/// Public sentence API mirroring prose_measure.sentences.
pub fn sentences(text: &str) -> Vec<String> {
    split_sentences(text)
}

// ---------------------------------------------------------------------------
// One-document measures (mirrors document_measures).
// ---------------------------------------------------------------------------

/// Python `\w` in Unicode mode: any letter, digit, underscore, or combining mark.
fn is_word_char_unicode(c: char) -> bool {
    c == '_' || c.is_alphanumeric() || (c as u32) > 0x7f
}

/// Mean type/token ratio over every 100-token sliding window (prose_measure.mattr).
/// Returns None when the text is shorter than one window (Python NaN, dropped).
fn mattr(toks: &[String]) -> Option<f64> {
    use std::collections::HashMap;
    if toks.len() < MATTR_WINDOW {
        return None;
    }
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for t in &toks[..MATTR_WINDOW] {
        *counts.entry(t.as_str()).or_insert(0) += 1;
    }
    let span_count = toks.len() - MATTR_WINDOW + 1;
    let mut sum = counts.len() as f64; // first window's distinct count
    for end in MATTR_WINDOW..toks.len() {
        let out_tok = toks[end - MATTR_WINDOW].as_str();
        if let Some(c) = counts.get_mut(out_tok) {
            *c -= 1;
            if *c == 0 {
                counts.remove(out_tok);
            }
        }
        let in_tok = toks[end].as_str();
        *counts.entry(in_tok).or_insert(0) += 1;
        sum += counts.len() as f64;
    }
    Some(sum / span_count as f64 / MATTR_WINDOW as f64)
}

/// One document's ARMED measures. `mattr` is ABSENT for text shorter than one MATTR window
/// (Python drops NaN in as_row; never zero). Values match Python document_measures.
pub fn document_measures(text: &str) -> BTreeMap<String, f64> {
    let toks = word_tokens(text);
    let words = toks.len();

    let mut commas = 0usize;
    let mut semicolons = 0usize;
    let mut hyphens = 0usize;
    let chars: Vec<char> = text.chars().collect();
    let n = chars.len();
    for i in 0..n {
        match chars[i] {
            ',' => commas += 1,
            ';' => semicolons += 1,
            '-' => {
                if i > 0
                    && i + 1 < n
                    && is_word_char_unicode(chars[i - 1])
                    && is_word_char_unicode(chars[i + 1])
                {
                    hyphens += 1;
                }
            }
            _ => {}
        }
    }

    let hedge_count = toks.iter().filter(|t| HEDGES.contains(&t.as_str())).count();

    let mut heavy = 0usize;
    let mut heavy_total = 0usize;
    for s in split_sentences(text) {
        if word_tokens(&s).is_empty() {
            continue;
        }
        heavy_total += 1;
        if s.matches(',').count() >= HEAVY_SENTENCE_COMMAS {
            heavy += 1;
        }
    }

    let per_1k = if words > 0 { 1000.0 / words as f64 } else { 0.0 };
    let mut m = BTreeMap::new();
    m.insert(
        "heavy_sentence_rate".to_string(),
        if heavy_total > 0 { heavy as f64 / heavy_total as f64 } else { 0.0 },
    );
    m.insert("hedges_per_1k".to_string(), hedge_count as f64 * per_1k);
    m.insert("punct_comma_per_1k".to_string(), commas as f64 * per_1k);
    m.insert("punct_semicolon_per_1k".to_string(), semicolons as f64 * per_1k);
    m.insert("punct_hyphen_per_1k".to_string(), hyphens as f64 * per_1k);
    if let Some(v) = mattr(&toks) {
        m.insert("mattr".to_string(), v);
    }
    m
}

// ---------------------------------------------------------------------------
// orphan-open-quote (house_style R8): a sentence opener that cites nothing earned.
// ---------------------------------------------------------------------------

/// Mirror house_style._ORPHAN_OPEN_RE.match against ONE already-split sentence.
/// A hit is a sentence that BEGINS (`\b`) with That|Which|And that|So that but whose next
/// whitespace-delimited word is not an excluded copula/exophoric (is|was|said|way|much|
/// aside) standing on a word boundary. Lookahead-free scanner over the same three rules.
pub fn orphan_openers(sentence: &str) -> bool {
    const EXCLUDED: [&str; 6] = ["is", "was", "said", "way", "much", "aside"];
    const OPENERS: [&str; 4] = ["That", "Which", "And that", "So that"];
    let s = sentence.trim_start();
    for opener in OPENERS {
        if let Some(rest) = s.strip_prefix(opener) {
            // `\b` after the opener: the next char must be non-word, or end of string.
            if !rest.is_empty() && is_py_word(rest.chars().next().unwrap()) {
                continue; // opener glued to a letter/digit (e.g. "Thatched", "Thats")
            }
            // `(?!\s+(is|was|said|way|much|aside)\b)`: exclude only when whitespace then
            // one of the six, with that word ending on a word boundary.
            let after_ws = rest.trim_start_matches(is_py_space);
            if after_ws.len() < rest.len() {
                let w = read_py_word(after_ws);
                let w_end = &after_ws[w.len()..];
                let w_boundary = match w_end.chars().next() {
                    None => true,
                    Some(c) => !is_py_word(c),
                };
                if EXCLUDED.contains(&w) && w_boundary {
                    continue;
                }
            }
            return true;
        }
    }
    false
}

/// Python `\w` (Unicode letter, digit or underscore) drives `\b`.
fn is_py_word(c: char) -> bool {
    c == '_' || c.is_alphanumeric()
}

fn is_py_space(c: char) -> bool {
    c.is_whitespace()
}

/// First `\w+` run of `text` (bounded by non-word or end).
fn read_py_word(text: &str) -> &str {
    let end = text
        .char_indices()
        .find(|(_, c)| !is_py_word(*c))
        .map(|(i, _)| i)
        .unwrap_or(text.len());
    &text[..end]
}

// ---------------------------------------------------------------------------
// grade
// ---------------------------------------------------------------------------

/// One ARMED measure a document sits outside [p5, p95] on.
#[derive(Debug, Clone)]
pub struct BandArmature {
    pub measure: String,
    pub value: f64,
    /// "above" or "below".
    pub side: Option<String>,
    /// (value - human_mean) / human_sd, rounded to 2; None when human_sd is zero.
    pub z: Option<f64>,
}

fn rnd(x: f64, scale: f64) -> f64 {
    (x * scale).round() / scale
}

/// Port of prose_target.grade: one entry per ARMED measure the document falls outside the
/// human interval on, sorted by descending absolute z. Values rounded like Python.
pub fn grade(measures: &BTreeMap<String, f64>) -> Vec<BandArmature> {
    let specs = band_spec();
    let mut out: Vec<BandArmature> = Vec::new();
    for (name, value) in measures.iter() {
        let (p5, p95, mean, sd) = match specs.get(name.as_str()) {
            Some(s) => *s,
            None => continue, // not an armed measure in the shipped target
        };
        let kind = if *value > p95 {
            "above"
        } else if *value < p5 {
            "below"
        } else {
            continue;
        };
        out.push(BandArmature {
            measure: name.clone(),
            value: rnd(*value, 1000.0),
            side: Some(kind.to_string()),
            z: if sd != 0.0 {
                Some(rnd((*value - mean) / sd, 100.0))
            } else {
                None
            },
        });
    }
    out.sort_by(|a, b| {
        let za = a.z.map(f64::abs).unwrap_or(0.0);
        let zb = b.z.map(f64::abs).unwrap_or(0.0);
        zb.partial_cmp(&za).unwrap_or(std::cmp::Ordering::Equal)
    });
    out
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn round_fields_are_stable() {
        // f64 round on clean decimals must not decay.
        let m = rnd(1.23456, 1000.0);
        assert!((m - 1.235).abs() < 1e-9);
        let z = rnd(-1.062032, 100.0);
        assert!((z - -1.06).abs() < 1e-9);
    }

    #[test]
    fn word_tokens_drops_numbers_and_keeps_hyphens() {
        assert_eq!(
            word_tokens("2024 well-founded don't 42 £1,299"),
            vec!["well-founded", "don't"]
        );
    }

    #[test]
    fn mattr_absent_below_window() {
        let t: Vec<String> = (0..50).map(|i| format!("w{i}")).collect();
        assert!(mattr(&t).is_none());
        let t2: Vec<String> = (0..120).map(|i| format!("w{}", i % 12)).collect();
        assert!(mattr(&t2).is_some());
    }

    #[test]
    fn sentences_guard_abbrevs() {
        let s = sentences("The firm, Acme Ltd. The rival is Dr. Smith.");
        // Abbreviation terminal dots are guarded, so this is ONE sentence (matches Python).
        assert!(s.len() == 1, "got {s:?}");
        assert!(s[0].contains("Ltd.") && s[0].contains("Dr."));
    }

    #[test]
    fn flat_doc_heavy_zero() {
        let text = "The buyer pays the monthly amount. The committee reduced the investment.";
        let m = document_measures(text);
        // two short, comma-free sentences -> no heavy sentences
        assert_eq!(m.get("heavy_sentence_rate").copied().unwrap(), 0.0);
    }

    #[test]
    fn orphan_open_quotes_locked_to_python_oracle() {
        // (sentence, house_style._ORPHAN_OPEN_RE.match outcome measured by Python)
        let cases: [(&str, bool); 13] = [
            ("That is a risk we accept and should you proceed.", false),
            ("That said, the buyer accepted.", false),
            ("That arrangement would not survive scrutiny.", true),
            ("Which is why the second contract matters.", false),
            ("Which contract matters then?", true),
            ("And that is nonsense in this context.", false),
            ("And that decision was reversed.", true),
            ("So that the supplier remains liable, we keep the clause.", true),
            ("That was a fine outcome.", false),
            ("That way we avoid the trap.", false),
            ("So that is settled and we proceed.", false),
            ("Nobody noticed the change.", false),
            ("So that much is true as well.", false),
        ];
        for (sent, expect) in cases {
            assert_eq!(
                orphan_openers(sent),
                expect,
                "orphan_openers mismatch on {:?}",
                sent
            );
        }
    }
}
