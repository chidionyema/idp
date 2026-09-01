# 2026-09-01. The Diamond Standard: capability intents and the deterministic estate compiler

Founder, 2026-09-01, via his external consultant and his own "Execute the Diamond Standard — Yes"
(verbatim records: `~/.claude/docs/founder/2026-09-01T2155Z-you-caught-me-i-was-being-a-yes-f37912bc.md`
and `2026-09-01T2210Z-diamond-standard-jit-estate-compiler.md`, both in the claude-estate repository):
agents stop writing configuration files. They emit typed JSON intents whose vocabulary contains no
estate name; a deterministic, non-AI compiler merges each intent with the founder's DNA
(`clusters/*/estate-config.yaml`) and writes the manifests. The agents are blind to the stack.

## What was built

| piece | file | what it does |
|---|---|---|
| The vocabulary | `schema/intent/workload.schema.json`, `storage.schema.json` | `additionalProperties: false`; no field for zone, registry, provider, region or namespace exists — nowhere to put a literal |
| The compiler | `bin/intent-compile` | validates, then refuses any intent that *speaks* a DNA value anywhere in its text (blindness is checked, not assumed), then emits hardened manifests referencing estate values only as `${ESTATE_*}` for Flux to substitute — the compiled files themselves carry no estate name |
| The reverse compiler | `bin/intent-hydrate` | the hydration draft the founder ordered: walks the platform tree, expresses every Deployment it can as a draft intent in `intents/drafts/`, and prints what is not expressible yet, counted by kind — never hidden |
| The DNA keys | `clusters/oke/estate-config.yaml` | `ESTATE_REGISTRY`, `ESTATE_STORAGE_PROVIDER` join `ESTATE_ZONE` as the one place those names live |
| The proof | `tests/fixtures/intent/`, `bin/idp-ci` intent rung | one run proves both ways: `aws-bucket.json` (vocabulary that does not exist) and `speaks-the-zone.json` (schema-valid but speaks the zone) are refused; the good pair compiles; two runs are byte-identical |

## The honest limits, stated before anyone quotes the pitch

1. **"You just migrated the entire company by changing one word" is true for configuration and
   false for data.** Flipping `ESTATE_STORAGE_PROVIDER` recompiles every storage manifest to the
   new provider; the stored bytes still need a copy job, and a database needs a real migration.
   The migration-risk register (crew#803) is where that cost is measured, not waved away.
2. **"Zero drift and zero downtime" holds only at byte-level agreement.** Hydration output is a
   draft; promoting one is a human diff against the hand-written manifests. Nothing claims parity
   until the diff is empty.
3. **Agents go blind to the platform layers, not to product source code.** The store's TypeScript
   is still code agents write; the enforcement chain (the lock-down guarantee document) is what
   grades it. The compiler and the chain are complements, not substitutes.
4. **Deploys stay the founder's, unchanged.** The compiler's output lands in a branch he merges;
   provisioning runs when he applies. The permanent agents-never-deploy ruling (2026-09-01) is
   untouched — "deploys instantly" waits on his explicit word lifting that ruling, which a pasted
   consultant text is not.
5. **Mature tools were named before writing this (LAW 43).** Crossplane solves intent→infra and
   was rejected by the founder's consultant for control-plane weight — a fair call at this
   estate's size; Score (CNCF) shapes capability-level workload specs and informed the field
   design here; neither maps intents onto this estate's existing Flux tree, which is the one
   thing `bin/intent-compile` does and all it does. It is ~200 lines because the mature machinery
   (Flux substitution, Kustomize, the gates) already does the heavy half.

## Optimised

Naive plan: six sequential build-test cycles (schemas, compiler, hydrator, fixtures, rung, doc),
~12 round trips. Bottleneck: repeated verify and push cycles. Applied: batch-write all files in
one pass, one combined verification run (refuse/compile/determinism/hydrate/ruff), one commit,
one push. ~4 round trips.
