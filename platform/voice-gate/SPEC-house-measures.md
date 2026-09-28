# Voice-gate house-measure parity — items 5 & 6 (spec for the builder)

Objective authority: `HANDOFF.md` item 5 (`prose_target` band measures ported as
arithmetic) and item 6 (hand-written `_SENT_SPLIT_RE`/`_ORPHAN_OPEN_RE`).
Reference implementation (the oracle these numbers were measured against):
`~/Documents/code/prospector/prospector/prose_measure.py` and
`~/Documents/code/prospector/prospector/prose_target.py`, plus the committed target
`~/Documents/code/prospector/prospector/data/prose_target.json`.

Scope discipline: this is a run-per-field grade surface, so it ports
`document_measures` + the ARMED `grade` bands (the six measures enforcement is armed
on). It does NOT port the whole-corpus `profile()` (that is corpus-tool receipting over
many documents, out of the per-field diff). Do not touch semantic tier2. Do not port
deny/register again — that surface is already closed by items 1-4.

## Deliverable

Two new Rust modules in this crate, exposed from `src/lib.rs`:

1. `house_measure` — a faithful Rust mirror of the deterministic measurement that item
   5's prose_target bands read:
   - `pub struct BandArmature { measure: String, p5: f64, p95: f64, human_mean: f64,
     human_sd: f64, side: Option<String>, value: f64, z: Option<f64> }` — one armed band.
   - `pub fn document_measures(text: &str) -> BTreeMap<String, f64>` mirroring
     `prose_measure.document_measures` for the six ARMED keys AND the intermediate keys
     the grade needs. Exact semantics are in the reference module; nothing here is a
     pattern — it is arithmetic and counting (Token: words `[a-z][a-z'’-]*` over the
     lowercased text, dropping numbers; Sentence: paragraph split on `\n\s*\n` +
     `_SENT_END` after `_ABBREV` guard; MATTR 100-word rolling mean type/token; the
     punct per-1k counts seperating em-dash/hyphen from comma/semicolon exactly as
     prose_measure does).
   - `pub fn grade(measures: &BTreeMap<String,f64>) -> Vec<BandArmature>` mirroring
     `prose_target.grade`: per ARMED measure compare value to [p5,p95], emit above/below
     entries with `value` round to 3, `z = (value-human_mean)/human_sd` round to 2 (None
     when human_sd is zero), sort by descending |z|. The p5/p95/human_mean/human_sd
     come from the SHIPPED `prose_target.json` ARMED block (see below) — mirror them as
     the same constants, keyed by measure name.
   - `pub fn sentences(text) -> Vec<&String>/Vec<String>` mirroring `sentences()`
     without lookbehind (item 6), and `pub fn orphan_open_quotes(text) -> Vec<(usize,usize)>`.

2. `harper` — item 5's grammar half. `pub fn check_grammar(texts:&[(&str,&str)])
   -> GrammarReport` shells out to the SAME binary and arguments Python uses:
   `harper-cli lint --no-color <files>`, writing each piece of prose over ≥60 chars
   (after stripping codes) to a temp `.md` file, summing counts of only the
   `HARPER_GRAMMAR_RULES` set, per whole invocation budget `min(timeout*len(files),600)`
   — and returns the words>=200 wall + rate exactly like `copy_lint.check_grammar`
   (fail-open). Same rule set, same `_HARPER_RULE_RE = <(\w+): (\d+)>` parse.

The grade arithmetic, hedges set, SUBORDINATOR set, comma-or-more heavy threshold,
_ABBREV set, punctuation membership and MATTR window are ALL given verbatim in the
reference modules. The Rust port may not invent a constant; every number is copied from
`prose_measure.py`/`prose_target.py`/`prose_target.json`.

## "Done" — in commands (these must be green; nothing else counts)

`cargo test house_measure` and `cargo test harper` inside this crate exit 0. The test
file `tests/house_measure.rs` (committed, protected) locks the five Oracle probes below
and asserts Rust `document_measures` returns the exact ARMED key values and Rust
`grade` returns exactly the (measure, side, z) tuples the Python oracle produced (both
captured below under `Oracle lock`). `tests/harper_grammar.rs` asserts the shell-out
return equals `copy_lint.check_grammar` on shared temp files when harper-cli is
present, and degrades to `unavailable` (a clean, non-failing signal) when it is not.

Property tests against the oracle (item 6): over a small corpus of deterministic
sentences (contractions, abbreviations `Ltd.`/`e.g.`, nested quotes/parens, em-dashes,
£/digits at sentence start), Rust `sentences()` must split identically to Python
`prose_measure.sentences`. The builder generates the expected splits by running the real
Python and embeds them (do NOT guess). The orphan-open-quote check must equal
`house_style._ORPHAN_OPEN_RE` behaviour; port that single lookbehind as guard-handling
code and property-test it against the Python oracle on the same corpus.

## ARMED band constants (from committed prose_target.json, verbatim)

measure | human_mean | human_sd | p5 | p95
--- | --- | --- | --- | ---
heavy_sentence_rate | 0.1572 | 0.0856 | 0.0312 | 0.3036
hedges_per_1k | 13.7885 | 5.9086 | 5.6711 | 23.0516
mattr | 0.6718 | 0.0239 | 0.6317 | 0.7083
punct_comma_per_1k | 31.8337 | 10.4331 | 13.267 | 49.1096
punct_semicolon_per_1k | 0.7489 | 1.3553 | 0.0 | 3.7244
punct_hyphen_per_1k | 2.7199 | 2.57 | 0.694 | 7.0547

## Oracle lock (locked numbers — generate more by running real Python, never by hand)

`~/Documents/code/prospector` has the reference. Pattern to regenerate the expected
payload for a probe corpus:
```
python3 - <<'PY'
from prospector.prose_measure import document_measures
from prospector.prose_target import grade
...
PY
```
The five probe strings delivered in `tests/house_measure.rs` under `Oracle lock` were
measured by exactly this path (this repo's prose_target.json), so port until Rust prints
the same numbers.

Note the Python contract quirks to reproduce exactly — they are tested by the lock:
- `mattr` is ABSENT from the map when the doc is shorter than one 100-word window (NaN
  dropped in `as_row`, never zeroed).
- value rounding: grade `value` round(value,3); `z` round(...,2); `side` = "above"/"below"/None.
- grade order is descendant |z|; ties keep Python's sort stability irrelevant (distinct z).
- hedge words and `to some extent` etc all come from the HEDGES/NOMINALIZATION-lists in
  prose_measure/copy_lint; only the armed 6 keys are unlocked here.

## Verify command

From `/Users/chidionyema/dev/code/idp/platform/voice-gate`: `cargo test`. That is the
only green the implementation may claim.
