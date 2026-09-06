# Voice Gate — what is built, what is left

Handoff for the next agent. Written 2026-09-06 from the working tree of branch
`fix/cyrus-webhook-routes`. Every claim below names the file and line that carries it.

## The frame (founder, 2026-09-06)

Two engines, not one, and the regex one is not a mistake:

> "gex s for old propsteor which we are still supporting and needs to power live site
> until new engine is tied in the new research engine. we just need to get ultimately we
> are going to be using one way once proven"

So Tier 1 (deterministic, `regex-automata` DFA) is the **sustaining** engine. It has to
reach parity with the Python linters in `prospector-main`, because those linters power the
live site today and the Rust gate replaces them in place. Tier 2 (local semantic model) is
the **new** engine and the product; the earlier note in
`specs/voice-gate-execution-2026-09-06.md:87` — "we are building enterprise level product
not regex" — is about what makes the product, not a ban on Tier 1.

Both run until the corpus diff is empty and Tier 2 is proven. Then one way.

## Built — 686 lines, 12 tests green

Commits `3e566b54` and `9a07722d`, branch `fix/cyrus-webhook-routes`.

| file | lines | what it does |
|---|---|---|
| `src/tier1.rs` | 94 | one `regex_automata::meta::Regex` per rule; `grade()` blanks non-prose then `find_iter`, emitting `Finding{rule_id, lane, field, span, detail, tier}` |
| `src/policy.rs` | 151 | policy load, lane inheritance resolved at load, `exclude_fields` |
| `src/server.rs` | 128 | axum; `/v1/health`, `/v1/grade` single or `{items:[…]}`, `MAX_BATCH = 500`, unknown lane → 422 |
| `src/prose.rs` | 51 | span-preserving stripper: fences, inline code, URLs, table rows, quotes, headings blanked to spaces, `\n` preserved |
| `src/main.rs` | 35 | refuses a non-loopback `VOICE_GATE_BIND` (R20); default `127.0.0.1:8420` |
| `voice-policy.yaml` | 45 | EE1–EE5 only; `tier2`/`tier3` blocks declared but unread |
| `docs/RULE-SEMANTICS-INVENTORY.md` | 41 | census of every `re.compile` in the four Python linter modules, classified |
| `tests/gate.rs` | 111 | 12 fixtures, all passing |

## Left to do

### 0. Unblock — do this first, nothing else is visible until it is done

The whole thing is 12 commits ahead of `origin/main` and **has never been pushed**. It
exists on one laptop. Push the branch and open a pull request before touching anything else.

### 1. Tier 1 parity — the sustaining path for the live site

1. **The boundary rewrite is specified but not implemented.**
   `docs/RULE-SEMANTICS-INVENTORY.md` names one rule that covers the entire R9 lexicon:
   `register_lint._phrase_re` (register_lint.py:193) compiles every banned phrase through
   `(?<![\w-]){phrase}(?![\w-])`, which `regex-automata` cannot compile. The equivalent is
   `(^|[^\w-]){phrase}([^\w-]|$)` **then shrink the reported span by any guard character
   matched**. `src/tier1.rs:80-89` pushes `m.start()`/`m.end()` raw — there is no shrink and
   no phrase compiler. Write both.
2. **The lexicon is empty.** `voice-policy.yaml:5` is `storefront: deny_patterns: []` and
   line 32 is `rules: {}`. Only EE1–EE5 exist. The R9 lexicon and the compound rules at
   `register_lint.py:214-239` have not been moved.
3. **Build the corpus match-set diff harness.** The inventory's own cutover rule:
   *no pattern ships in the Rust gate until its class is settled here and its corpus
   match-set diff is empty.* Python linters are the oracle; corpus is 312,886 words plus
   the live JSONs. Per phrase, both engines' match sets must be byte-identical.
4. **Port the two hand-rolled pieces.** `_SENT_SPLIT_RE` (register_lint.py:276) is sentence
   splitting — Rust code with property tests against the Python oracle, not a pattern.
   `_ORPHAN_OPEN_RE` (house_style.py:140) is the one remaining lookbehind outside the
   rewrite rule.
5. **Port the two non-regex checks.** `copy_lint.check_grammar` (copy_lint.py:381+) shells
   out to the `harper` binary — the gate shells out identically. `prose_target` band
   measures are arithmetic against `prose_target.json`, not patterns.

### 2. Tier 2 — the new engine, the product

Not started. `/v1/health` reports `tier2: "disabled"`. `voice-policy.yaml:33-38` already
declares the contract: `Llama-3.2-1B-Instruct-Q4_K_M.gguf`, fallback
`Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`, `confidence_floor: 0.8`, `frontier_alias: cheap`,
`max_prompt_exemplars: 6`. Nothing reads that block yet.

Product track named in the spec: **tree-sitter** for the parse tree, **GLiNER** for span
labelling, **Extism** as the plugin host.

### 3. Tier 3 — bounded rewrite

Not started. `voice-policy.yaml:39-45` declares `max_iterations: 2` and
`preserve: [numbers, named_entities, urls, dates]`. Nothing reads it. Quarantine is the
last resort after Tier 3, and there is no quarantine path either.

### 4. Platform wiring — none of it exists

`grep -rl voice-gate .github catalog bin` returns nothing. That means:

- no Backstage catalog entity and no owner;
- not in `bin/idp-ci` — the Rust build and `cargo test` run nowhere but a laptop;
- no container image, no Flux kustomization, no namespace fence (default-deny
  NetworkPolicy, ResourceQuota, LimitRange, DNS exception — AGENTS.md, crew#191);
- no emission to the central collector, which under LAW 50 means admission refuses the
  workload;
- `src/main.rs:*` refuses a non-loopback bind by design (R20), so how prospector reaches it
  is an open decision: sidecar in the same pod, or a gateway route with the bind rule
  revisited.

### 5. The cutover

Write the switch criterion down before either engine moves: the diff is empty for every
phrase, Tier 2 clears its confidence floor on a held-out set, and the live site is served
by one engine. Until then both run.

## Commands

    cd platform/voice-gate
    cargo test                 # 12 tests, currently green
    cargo run                  # serves 127.0.0.1:8420
    curl -s localhost:8420/v1/health

Specs, in `~/dev/code/prospector-main` and safely on its `origin/main`:
`specs/voice-gate-2026-09-06.md` (`95b5db80`) and
`specs/voice-gate-execution-2026-09-06.md` (`08f8c7af`).
