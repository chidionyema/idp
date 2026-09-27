# harv: a shelf of sealed, pre-tested building blocks harvested from open source

**Status:** built and run on the laptop, 2026-09-27 (kronos `feat/harv`). Operating = the
funnel below, measured through the `harv` intent. Design source: the founder's `harv` spec (z.ai session
`c46e97b9`, pasted into the idp Claude session 2026-09-27). Context:
`docs/synthesis/2026-09-27-fractal-factory-review-brief.md`.

**One sentence:** it turns existing open-source code into a shelf of sealed, pre-tested building
blocks, so building software becomes picking parts instead of writing them.

## The pipeline, in plain terms

1. **It picks what's worth taking.** It doesn't crawl everything. It reads the popularity lists
   (downloads, stars) and the licenses, and only looks at code millions of people already trust.
   The world's users already voted; we read the results.
2. **It takes inventory.** For each library: what functions it offers, what tests ship with it,
   and whether it has any way to touch the outside world.
3. **It seals the code in a box with no doors.** Each piece is compiled to WebAssembly that
   physically cannot reach the internet, your files, or the clock. Not "we checked and it
   probably doesn't": it *can't*, because the doors aren't in the walls. If a piece still works
   with no doors, that proves it never needed them. If it fails to start, it wanted the outside
   world, which is also worth knowing.
4. **It interrogates the code.** First, it runs the library's own tests inside the box. Second,
   the same job (say, CRC32) exists in dozens of independent libraries, so it feeds identical
   inputs to all of them and compares the answers. Where every implementation agrees, the
   behaviour is confirmed by independent witnesses. Where they disagree, someone has a bug, found
   without writing a single test.
5. **It shelves the survivors with paperwork.** Every accepted piece goes into a registry with an
   unforgeable fingerprint (change one byte and the fingerprint changes), a signed certificate of
   exactly where it came from, its test results and its license. Tamper-evident, forever.

When you or an agent needs "normalize this email" or "compute this checksum", it doesn't get
written. It gets pulled off the shelf: already tested, already sealed, already documented.

**What it deliberately doesn't do yet:** it doesn't *assemble* anything; this fills the
warehouse. The composer (pick parts, wire them, verify the connections) is phase 2, worth
building only once we know what's on the shelves. It doesn't promise the code is perfect. It
promises you know exactly what's there, that it passed its tests, that it's sealed, and that
nobody quietly swapped it since.

**The number to watch:** of ~10,000 candidate functions, how many survive every gate? That one
funnel printout tells us whether the idea works, before anything is built on top of it.

## Why the estate wants it

| Use case | What it fixes |
|---|---|
| Agents pick parts instead of writing utility code | Plausible-but-wrong generated code |
| An intent step can be a sealed block with declared grants | "Agents act only through intents" is a convention today (0 of 264 intent runs came from Claude Code); the runtime would enforce it |
| Fractal factory **Produce**: a need with no current terminal triggers a harvest | Nothing produces today (`crystallize` has 0 runs) |
| Fractal factory **Grade/Shed**: rival implementations compared on the same inputs; a better verified one re-binds the need | Grade and Shed exist only in the schema |
| One artifact runs on laptop, arm64 free-tier cluster, phone, browser | Per-arch images; free-tier ceiling; client-side voice |
| The funnel is a measured, publishable result | R71: Research has nothing to show |

## Where it lives (§6: one of each layer)

`harv` adds **harvest, build and differential verification**. It reuses what exists:

| `harv` part | Use the existing |
|---|---|
| Sandbox (wasmtime, deny by omission, fuel, timeout) | `kronos/crates/ring1-wasm` |
| Evidence log (append-only executions) | `kronos/crates/ring4-ledger` |
| Registry / catalogue | `factory/registry.py`: each shelved block is emitted as a `capability.yaml` terminal, its tier as `grade` |
| Signing trust root | keys from `estate-secrets`, referenced by name |

## Build checklist (the spec's code, as fixed in kronos `crates/harv`)

- [x] Differential passes the payload into the module (`harv_alloc`/`harv_run`); the
      `crc32-buggy` fixture (one polynomial bit off) produces a disagreement with the exact input
      (acceptance test 4).
- [x] Signatures verify against a trust store of allowed keys by role, never the embedded key (I2).
- [x] Tier derived from signed reports only; reports signed; `ring4-ledger` append-only by
      trigger; `artifacts` is `INSERT OR IGNORE` with an UPDATE trigger (I5).
- [x] `verify-all` re-hashes every blob file (I1, test 6).
- [x] `recipe_hash` covers toolchain, target, flags, wrapper source, lockfile and every crate
      source file; rebuilds at the same path are compared byte for byte (I6, test 7).
- [x] Deny probe calls the ABI export in a module with zero imports.
- [x] Test scan descends into `mod tests` and `tests/`; multiple test binaries are data.
- [x] Trap kinds classified by type (`Trap::OutOfFuel`, `Trap::Interrupt`, `I32Exit`).

Deviations, documented in code: a binary harv_abi payload instead of JSON and WIT; no coverage
measurement; one crate with modules instead of seven. (Since kronos `73af7b2` the public API comes
from rustdoc JSON, as the spec asked, not `syn`.)

## First step and what counts as done

1. Seal **one real intent step** as a harvested wasm block, run through `ring1-wasm`, evidence in
   `ring4-ledger`, the block registered as a terminal. Done = the intent's ticket shows the
   sealed run.
2. Then the funnel on the crates.io top 100, printed. Done = the printout, measured, in this
   ticket.

## Results (measured 2026-09-27, laptop, `estate-execute harv`)

Acceptance: `cargo test -p harv`: 8 of 8 pass (sign_roundtrip, deny_probe_pure,
deny_probe_impure, differential_divergence, fuel_timeout, registry_persistence,
rebuild_equality, class_gate).

Funnel, crates.io top 100 by downloads (two runs: top 20, then 21 to 100):

| stage | top 20 | 21 to 100 |
|---|---:|---:|
| crates indexed / license ok / fetched | 20 / 20 / 20 | 80 / 80 / 80 |
| public fns | 79 | 592 |
| flat-signature fns | 7 | 18 |
| crates whose wrapper built | 2 | 6 |
| fns compiled, zero imports, smoke pass (t1) | 6 | 11 |
| fns whose crate's tests pass in the sandbox (t2) | 3 | 6 |
| crates reproducible (byte-equal rebuild) | 2 | 6 |
| shelved | 6 | 11 |

Most of the top 100 is generic or trait API (serde, syn, rand_core...), so it has no flat
function to seal. That is the main attrition, and the number to widen next (generic
instantiation, `char`/`Option` in the ABI).

Differential on real code (run `only=regex,regex-syntax,strsim,levenshtein`): 2 clusters, 1,000
generated inputs each, 0 disagreements. `regex::escape` agreed with `regex_syntax::escape`, and
`strsim::levenshtein` with `levenshtein::levenshtein`. `regex-syntax-escape` and
`strsim-levenshtein` reached **t3**: smoke, own tests and an independent witness.

Shelf: 18 parts (t1 9, t2 7, t3 2), 25 signed manifests counting re-shelves with new evidence;
`verify-all` 100 blobs re-hashed, 25 artifacts good, 0 bad; 67 evidence entries in ring4-ledger.

Pulled off the shelf through the intent, in deny mode:
`estate-execute harv verb=run name=strsim-levenshtein hex=<"kitten","sitting">` gives `= 3`
(fuel 8657).

Terminals: `harv export-capabilities` output passes `factory/registry.collect()`: 18 admitted,
one per part, 0 warnings. The t3 parts are exported as `state: current`, the rest as `incubating`.

### Second funnel: rustdoc front end, harv_abi v2, generic menu, fusion (kronos `73af7b2`)

Measured 2026-09-27, one run of the top 100 through `estate-execute harv verb=harvest limit=100`
(ticket `INTENT-20260927-101226-2fe22c01`, 73.6 min):

| stage | first funnel (top 100) | second funnel |
|---|---:|---:|
| public fns + methods seen | 671 (syn) | 6,253 (rustdoc) |
| wrappable entries | 25 | 2,107 (75 instantiated generics, 1,988 fused ctor+method) |
| crates whose wrapper built | 8 | 35 of 97 inventoried |
| compiled | 17 | 1,891 |
| zero imports | 17 | 1,385 |
| smoke pass (t1) = shelved | 17 | 1,352 |
| own tests pass (t2) | 9 | 118 (28 crates' tests built, 12 passed) |
| independent witness agrees (t3) | 2 | 13 |
| byte-equal rebuild | 8 crates | 35 crates |

Survival: 17 of 671 (2.5%) before, 1,352 of 6,253 (21.6%) now. The 1,352 parts are 712 distinct
callables: a method fused with up to 8 constructors is one part per constructor. The shelf leans on
`time` (359 parts), `bytes` (270) and `regex-automata` (149).

`verify-all`: 3,131 blobs re-hashed, 1,377 artifacts good, 0 bad.

Differential: 60 clusters, 124 parts. A member now passes only if at least 1 input in 10 produced a
value, so clusters that agree only on rejections (random strings never parse as `log::Level`,
`serde_json::Value` or `toml::Value`) grant nothing. Two clusters disagreed, both different
semantics under one name, not bugs: `log` vs `tracing-core` `LevelFilter::to_string` (111 of 1,000
inputs), `version_check` vs `semver` `Version::parse.to_string` (3). Most agreeing clusters are
`regex-automata` vs `aho-corasick` `PatternID`/`StateID`, shared code by one author: a weak witness.

Still open:
- Witness independence: shared-author clusters should not count as independent.
- Other languages (Python via componentize-py, JS via componentize-js, C via wasi-sdk, Go via
  TinyGo) share the shelf and make the differential cross-lingual.
- The export is not yet in a directory the live collector scans.
- No existing estate intent step has been replaced by a shelved block yet.
