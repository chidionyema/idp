# Rule-semantics inventory — Python `re` → Rust `regex-automata` (phase-1 safety artefact, spec §15 mechanism 3)

Date: 2026-09-06. Method: census of every `re.compile` in the four linter modules, then classification.
Cutover rule: no pattern ships in the Rust gate until its class is settled here and its corpus
match-set diff (§15 mechanism 4) is empty.

## The one rewrite rule that covers the lexicon

`register_lint._phrase_re` (line 193) compiles **every** banned phrase through the boundary idiom
`(?<![\w-]){phrase}(?![\w-])` — lookbehind + lookahead, which regex-automata does not support.
DFA-expressible equivalent with identical semantics:

    (^|[^\w-]){phrase}([^\w-]|$)        # then shrink the reported span by any guard char matched

The corpus match-set diff (312,886-word engine corpus + live JSONs) proves equivalence per phrase
before the phrase moves. This single rewrite covers the entire R9 lexicon and every future
phrase added to the policy.

## Census

| module | pattern | file:line | class |
|---|---|---|---|
| register_lint | `_phrase_re` boundary idiom (ALL banned phrases) | register_lint.py:193 | REWRITE — the rule above |
| register_lint | `not just` / `-ing` tail / `Ultimately…` openers / `it's not X, it's` / `not only…but also` / `whether you're` / `? Absolutely` / `the beauty of` (R9 compounds) | :214-239 | REWRITE — same idiom |
| register_lint | strip set: fence, inline code, URL, table row, quote, heading | :248-255 | DFA-EXPRESSIBLE (ported verbatim in `prose.rs`) |
| register_lint | `_APOS_RE`, `_ABBREV_GUARD`, `_WORD_RE` | :257,275,278 | DFA-EXPRESSIBLE |
| register_lint | `_SENT_SPLIT_RE` sentence splitter `(?<=[.!?])…` | :276 | HAND-ROLLED — sentence splitting is code in Rust, not regex |
| house_style | list, figure, source, vague, orphan, prediction, furniture, quote checks | :70-191 | DFA-EXPRESSIBLE except `_ORPHAN_OPEN_RE` (:140, one lookbehind — census: 1) |
| house_style | `_SPLICE_GLUED`, `_SPLICE_ELLIPSIS` | :178-179 | DFA-EXPRESSIBLE |
| copy_lint | URL/ident/fence/inline/skip-span/word-token/harper-rule/hedge | :62,162-166,266,345,514,556-558 | DFA-EXPRESSIBLE (census: 0 lookarounds) |
| copy_lint | `check_grammar` (harper binary) | :381+ | NOT-A-REGEX — external engine; pack lane keeps calling harper, gate shells out identically |
| prose_target | band measures | (4 `re.` uses) | NOT-A-REGEX — numeric band comparisons vs `prose_target.json`; ported as arithmetic, not patterns |

Census totals (grep, 2026-09-06): lookbehinds `?<!`/`?<=` — register_lint 7, house_style 1, copy_lint 0, prose_target 0; lookaheads `?=` — register_lint 1, others 0. Every lookaround is covered by the rewrite rule or the hand-rolled sentence splitter.

## Class definitions

- **DFA-EXPRESSIBLE** — compiles in regex-automata as-is; ships after the match-set diff is empty.
- **REWRITE** — lookaround present; converted by the rewrite rule above, then proved by the diff.
- **HAND-ROLLED** — logic, not a pattern (sentence splitting); ported as code with property tests against the Python oracle.
- **NOT-A-REGEX** — numeric/structural checks (bands, grammar engine); ported as arithmetic or a subprocess call, unchanged semantics.
