# harv: a shelf of sealed, pre-tested building blocks harvested from open source

**Status:** open, 2026-09-27. Design source: the founder's `harv` spec (z.ai session
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

## Build checklist (found reading the spec's code, 2026-09-27; not compiled)

- [ ] Differential engine passes `payload` into the module (`harv_alloc`/`harv_run`); today it
      runs every member with the same args and no stdout, so everything "agrees". A mutant
      fixture must produce a disagreement, or the check isn't a check.
- [ ] Signatures verify against an allow-list of trusted keys, not the key embedded in the
      signature (I2).
- [ ] Tier is derived from signed reports, never set in the manifest; reports are signed;
      `executions` is append-only in fact; `artifacts` never `INSERT OR REPLACE` (I5).
- [ ] `verify-all` re-hashes every blob file (I1; acceptance test 6 depends on it).
- [ ] `recipe_hash` covers the real inputs (commit, lockfile, adapter source); rebuilds use the
      same path (I6). Fix the adapter WIT (`export` inside an interface) and the `{wit-dir}`
      placeholder.
- [ ] Deny probe for `wasm32v1-none` invokes the ABI export, not `_start`.
- [ ] Test scan descends into `mod tests`; rustdoc JSON runs as `cargo +nightly rustdoc`;
      coverage parses the real `llvm-cov` export shape; multiple test binaries are data, not an
      abort.
- [ ] Trap kinds classified by type, not error-string matching.

## First step and what counts as done

1. Seal **one real intent step** as a harvested wasm block, run through `ring1-wasm`, evidence in
   `ring4-ledger`, the block registered as a terminal. Done = the intent's ticket shows the
   sealed run.
2. Then the funnel on the crates.io top 100, printed. Done = the printout, measured, in this
   ticket.
