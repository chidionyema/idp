# Voice Gate — what exists, and what is left to finish it

Written 2026-09-06. Supersedes the first version of this file, which understated the work
by looking only at this directory. Two claims in that version were wrong and are corrected
below. Every claim here names the file that carries it.

## The decision that frames this

Founder, 2026-09-06:

> "regex is for old prospector which we are still supporting and needs to power live site
> until new engine is tied in the new research engine... ultimately we are going to be
> using one way once proven"

and then, on the semantic second engine:

> "why do we need second engine anyway... seems pointless... best just complete the real one"

**So: one engine. Finish the deterministic gate to full parity with the Python linters,
put it on the live site, and do not start the semantic tier.** The `tier2:` block in
`voice-policy.yaml` stays declared and unread. Revisit only if the corpus run below shows
the word list missing enough to justify it — that number will be a by-product of the work,
not a separate project.

## What exists — the two halves

### Python half — DONE and MERGED on prospector `main`

Pull request #819, merged. This is not a prototype; it is wired into the live publish path.

| file | what it is |
|---|---|
| `prospector/voice_gate/deny.py` (145 lines) | the deny gate: `findings_for`, `grade_fields`, `excise`, `walk_prose`; lane `evidence-export`; `EXCLUDE_FIELDS = {gate, gatelabel, verdict}` |
| `prospector/voice_gate/__init__.py` | package seam |
| `tests/unit/test_voice_gate_deny.py` | its unit tests |
| `tools/voice_gate_conformance.py` (265 lines) | **the conformance harness** |

Wiring already landed on the same branch: the deny gate runs in `make_sample_report`, in
`make_kill_log`, and in `publish_pass` — the estate's single publish gate. The backfill of
the old packs was done through it: commit `4f57ebe2` measured 186 stored kill reasons,
repaired the research cadence (`passages` → `sources`, plural-preserving) through
`plainEnglish`, and left all 1007 store-web tests green. Commit `a87ebdeb` put `walk_prose`
over every leaf so a field list can never hide a string again, with six hand-written
overrides, and the live sample report came out 100% prose-clean.

### Rust half — the port, in this directory

686 lines, 3 commits, branch `fix/cyrus-webhook-routes` (pushed). **12 tests pass** — run
today, not quoted from a commit message:

    test result: ok. 12 passed; 0 failed; 0 ignored

`Cargo.toml` + committed `Cargo.lock`; `src/policy.rs` (loader, lane inheritance resolved
at load); `src/policy.schema.json` (a bad policy is rejected, not ignored); `src/prose.rs`
(strips fences, inline code, URLs, table rows, quotes, headings **while preserving byte
positions**); `src/tier1.rs` (one automaton per rule, so a finding names its rule);
`src/server.rs` (single + batch, 500 cap, 422 on unknown lane); `src/main.rs` (refuses any
bind but loopback); `tests/gate.rs`.

## Corrections to the first version of this file

1. **"There is no proof harness" — wrong.** `tools/voice_gate_conformance.py` exists, is
   merged, and was built to drive *this* Rust service: its default is
   `--gate http://127.0.0.1:8420`, which is exactly what `src/main.rs` binds. It has three
   modes, and `rust_grade()` already POSTs to the gate's batch endpoint.
   - `diff` — corpus match-set diff, Python oracle versus the Rust gate, over every prose
     leaf of the storefront data **and the pre-scrub git-history versions**. Empty diff or
     the Rust gate does not ship.
   - `fuzz` — differential fuzzing, 2000 mutated real strings, seed 42: dash insertion,
     banned-token injection.
   - `golden` — golden samples versus the oracle.
2. **"Nothing else exists / no wiring" — wrong.** The Python half is merged and is running
   the live publish path today, and the old packs have already been backfilled through it.

## What is left, exactly

### 1. Run the harness. It has never been run against the Rust gate.

This is one command and it replaces guesswork with a list:

    cd ~/dev/code/idp/platform/voice-gate && cargo run &
    cd ~/dev/code/prospector-main && tools/voice_gate_conformance.py all

Everything below is what we already know it will report. Run it first anyway — the diff is
the specification of the remaining work, and it writes receipts to `store/voice_gate`.

### 2. The phrase compiler and the span shrink — the one blocker on the lexicon

`register_lint.py:193` compiles every banned phrase as
`(?<![\w-]){body}(?![\w-])`, where `body` joins the phrase's words with `\s+` so a phrase
broken across two lines of a paragraph still matches. `regex-automata` has no lookbehind.
The equivalent is `(^|[^\w-]){body}([^\w-]|$)` **and then shrinking the reported span by
whichever guard character matched**.

`src/tier1.rs:80-89` pushes `m.start()` and `m.end()` raw. There is no shrink and no
phrase-to-pattern compiler. Until both are written, **not one phrase can move**, which is
why the Rust policy still holds only the five export rules.

Acceptance: `diff` mode empty for every phrase.

### 3. Move the lexicon and the constructions

- `BANNED_SPEC` at `register_lint.py:77` and `ADVISORY_SPEC` at `:157` — roughly a hundred
  phrases between them; take the exact count from `_parse_spec`, not from a line count.
- `CONSTRUCTIONS` at `:212` — eight shapes, each with a name and a reason. These are the
  half a word list cannot reach: `not_just`, `trailing_participle`, `adverb_opener`,
  `negation_reveal`, `not_only_but_also`, `whether_youre`, `rhetorical_answer`,
  `the_beauty_of`. Four of the eight use lookbehind and go through the rewrite in item 2.
- Apostrophes are normalised by `_normalise` before matching, so only the straight form
  appears in a pattern. The Rust side must normalise identically or the diff will not close.

The Rust `voice-policy.yaml` currently has `storefront: deny_patterns: []` and `rules: {}`.
Both fill from this step.

### 4. Land `golden.jsonl`

`tools/voice_gate_conformance.py:207` skips golden mode with
`"golden.jsonl not landed yet (B1 in flight)"`. It belongs at
`prospector/voice_gate/golden.jsonl`. Until it lands, one of the three proof modes is dark.

### 5. The two checks that are not patterns

- `copy_lint.check_grammar` shells out to the `harper` binary. The Rust gate shells out
  identically — same binary, same arguments — or the diff will never close.
- `prose_target` band measures are arithmetic against `prose_target.json`. Ported as
  arithmetic, not as patterns.

### 6. The two that must be hand-written

- `_SENT_SPLIT_RE` (`register_lint.py:276`) — sentence splitting is logic, not a pattern.
  Rust code with property tests against the Python oracle.
- `_ORPHAN_OPEN_RE` (`house_style.py:140`) — the one lookbehind outside the rewrite rule.

Census, measured today: lookbehinds — `register_lint` 8, `house_style` 1, `copy_lint` 0,
`prose_target` 0. Lookaheads — 7, 2, 0, 0. Every one is covered by item 2 or by this item.

### 7. Then, and only then, the platform wiring

Nothing here exists yet: no catalogue entity and no owner; not in `bin/idp-ci`, so the
build and tests run nowhere but a laptop; no image, no deployment, no namespace fence, no
telemetry to the central collector — which under the estate's rules means the workload
would be refused admission. `src/main.rs` refuses any non-loopback bind by design, so how
prospector reaches it is an open decision: sidecar in the same pod, or a route with that
rule revisited.

### 8. The switch-over, written down

`diff` empty, `fuzz` clean over 2000 cases, `golden` passing, and the Python linters and
the Rust gate agreeing on a full publish run. Then prospector calls the Rust gate, the
Python path becomes the oracle used only by the harness, and it is one engine.

## Commands

    cargo test                                   # 12 tests, green today
    cargo run                                    # serves 127.0.0.1:8420
    tools/voice_gate_conformance.py all          # from prospector-main; writes store/voice_gate

Specs: `~/dev/code/prospector-main/specs/voice-gate-2026-09-06.md` and
`specs/voice-gate-execution-2026-09-06.md`, both on that repo's `main`.

---

## Milestone status (2026-09-06, recorded per objective), branch `fix/cyrus-webhook-routes`

Up to date: `cargo test` runs 35 tests green in this directory today. Items 1-4 were closed
by the earlier commits below; items 5-6 primitives added oracle locks this session.

| item | state | evidence (commit/worktree) |
|---|---|---|
| 1 receipts | done | `store/voice_gate/conformance-{diff,fuzz,golden}.json` (prospector) |
| 2 phrase compiler + span shrink | done | `638b452c` |
| 3 lexicons into policy, diff empty | done | `256eee16`,`9e7168b7`,`4abc6a28`,`82a71bfb` (1758 leaves, diff & fuzz empty) |
| 4 golden.jsonl live | done | `prospector/prospector/voice_gate/golden.jsonl` |
| 5a prose_target bands | done, ORACLE-EQUAL | `0b929ead` (`house_measure.rs` + `tests/house_measure.rs`, fixtures measured by Python) |
| 5b harper `check_grammar` shell-out | NOT BUILT - deferred. Grammar lane has no live grader until item 7 wiring; a faithful un-wired wrapper is an instrument nobody reads (LAW 28). Harper is installed (`/usr/local/bin/harper-cli`) so it is buildable on the item-7 decision. |
| 6 splitting + orphan-open-quote | done, ORACLE-EQUAL | `de026d5b` (`split_sentences` locked word-for-word over 24 python sentences in `tests/sentence_split.rs`; `orphan_openers` locked to 13; both lookbehind-free) |
| 7 platform wiring | not started (catalogue entity, gate ownership, namespace fence, collector telemetry, bind decision) |
| 8 cutover | not started |
| semantic tier2 | not started, as decided |

Policy source of truth stays one: `voice-policy.yaml` here is byte-identical to
`prospector/prospector/voice_policy.yaml`.

### Four acceptance greens, re-verified this session (2026-09-06)

Read from the receipts on disk, run today, not quoted from a commit:

    store/voice_gate/conformance-diff.json    {"leaves":1758,"diffs":[],"ok":true}
    store/voice_gate/conformance-fuzz.json    {"cases":2000,"mismatch_count":0,"ok":true}
    store/voice_gate/conformance-golden.json  {"rows":17,"agreement":1.0,"ok":true}
    cargo test (this directory)               35 passed; 0 failed (run, not asserted)

What the harness grades — a scoping fact that governs item 5b: `voice_gate_conformance.py`
compares only the deny lane (`findings_for` / register_lint lexicons over `evidence-export`
leaves). It has NO grammar/copy_lint mode, and no grammar output enters any diff. So item 5b
(a Rust harper shell-out) has no oracle or receipt that could prove parity until the item-7
wiring decides whether grammar joins the graded lane at all — the Python half itself treats
harper as a self-described debug tool, fail-open and advisory (`copy_lint.py:385`,
`grammar_check_unavailable`). Building an un-read harper mirror now would be an instrument
nobody reads (LAW 28) with no empirical signal to converge (empirical-proof rule). Its port
belongs to the item 7/8 decision, with harper already installed at `/usr/local/bin/harper-cli`.
