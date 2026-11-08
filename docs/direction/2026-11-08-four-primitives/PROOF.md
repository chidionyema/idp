# PROOF -- four primitives, what is measured

Every row here is a **command, its exit status, the line it printed, and a sha256**. Nothing in this
file is a narration of intent. Exit codes are the estate's declared codes:

| code | meaning |
|---|---|
| 0 | the thing happened |
| 2 | BLIND -- cannot judge (refused rather than guessed) |
| 3 | MISSING / short of what was preregistered / OVER budget |
| 4 | MISMATCH -- the measurement contradicts the claim |

A row you cannot re-run is not proof. Each row says how to re-run it.

**This file lives outside `idp` on purpose.** The four primitives are artifacts under
`~/.estate/direction/`, not code in a checkout, and nothing here reads a checkout to run: they read
`~/.estate/estate.db` and `~/.estate/science/science-proof.db`, which are the live files. That matters
because the estate has **two idp trees** -- `~/Documents/code/idp` (a working checkout) and
`~/.estate/runtime/idp` (what actually runs, under launchd) -- and they do not share a HEAD. A proof
pinned to either checkout would be measuring the wrong tree half the time.

---

## 0. The artifacts and their bytes

| artifact | bytes | sha256 |
|---|---|---|
| `DESIGN.md` | 13063 | `31ab7680723fdb968c0959e3bf30451f9cf9730f60c8f94affd32a7d070a2790` |
| `artifacts/estate-chronicle` | 22593 | `07e76b4939b71edb7084b73e79a3ced2a8592498ecf0f8c5457aa06e2639c279` |
| `artifacts/pack_genesis_spore` | 23530 | `eea5d896104b9ff3bb287a7aee2b797a5c9cd1b87081294408348a0687d26a02` |
| `artifacts/science_loop` | 15999 | `283bae9d290934c77417d8361aca1173cf027c27992da94c809482de58603387` |
| `artifacts/estate-lane` | 7439 | `29e155e36697948fb0fa4697cc0239491d8a859d8ac5fef950b6ffa3e581aa12` |
| `artifacts/mycelium` | 15001 | `c8b3e170ea045acb0afa8143f43713010310b1709c2d314226d46d6ddfc0b9b7` |
| `artifacts/rederive-verdict` | 8559 | `728234bf13a526bb2b33e5e8dea7cde2ac369b1818e72a413d966675ea3f70e7` |
| `artifacts/GENESIS_SPORE.dna` (core) | 5621 | `6dc7d93d292290cbd80cc94bd089228aaf586f550f5bc654876898560ad1bcef` |
| `artifacts/GENESIS_SPORE.full.dna` | 42299 | `77921fb78049ce96027770309a1bbd4e613d8b596947bccdd99a3d271fa636a0` |
| `verify-proof` | 17862 | `8785bfc3ffd1a39fc733b03f96b3c49e0a5fb62027e082b162c582cb1db82af4` |
| `falsify-proof` | 4928 | `25012063691da1c05dc4457f5dc8d4e8aa2fd80d6fcfbeec3816001c2ad39e40` |
| `isolation_probe.py` | 1663 | `96a5d2c1c6f85260e1a7113e6cae13eb120d5606e9b476edad7f08a814df524e` |

Re-run: `shasum -a 256 ~/.estate/direction/2026-11-08-four-primitives/artifacts/*`

**This file is not allowed to be taken on its word.** `verify-proof` re-runs all 35 falsifiable
claims against the current tree and exits 0 only if every one still holds. `falsify-proof` then
proves that verifier can actually go red. Run both:

```
cd ~/.estate/direction/2026-11-08-four-primitives && ./verify-proof && ./falsify-proof
```

Stdlib-only Python 3.9.6. The only network calls in the whole proof are the two real LLM calls in
`mycelium`'s own claim (sec.7), routed to a free tier; no credential is printed, stored or shipped.

---

## 1. estate-chronicle -- the bi-temporal memory

**Claim: the estate's SQLite state can be bound to git history and the bind can be proved.**

The root is an RFC 6962 Merkle tree over `step_runs` **as the table actually is** -- columns
`id, ticket_id, step_idx, cmd, exit_code, duration_ms, ran_at`. The design named an
`hmac_signature` column; that column does not exist, so nothing is hashed that isn't real.

### 1.1 snapshot -> verify -> rewind

| # | command | exit | printed |
|---|---|---|---|
| 1 | `estate-chronicle snapshot --db ~/.estate/estate.db --dest /tmp/sci-chron` | 0 | `"ledger_rows": 13842, "ledger_merkle_root": "ca58ee93...a69a0e", "git_branch": "recovery/idp-20261031"` |
| 2 | `estate-chronicle verify <snapshot> --db <snapshot>` | 0 | `matches=true` |
| 3 | `estate-chronicle rewind --at <sha>` | 0 | branch file mounted, live DB untouched |
| 4 | `estate-chronicle rewind --at 2020-01-01T00:00:00Z` | 3 | `MISSING no genesis-chronicle pointer at or before ...` |
| 5 | `estate-chronicle status` | 0 | `chronicle recovery/idp-20261031@3679304d rows=13842 root=ca58ee93855a3a58 verified=True rpo=snapshot` |

### 1.2 the falsifiers -- a gate that cannot fail is not a gate

| # | what was broken | command | exit | printed |
|---|---|---|---|---|
| 6 | one ledger row edited in a snapshot copy | `verify` | **4** | root differs from the pointer |
| 7 | a single byte flipped in the page area | `verify` | **4** | `file_sha256` / root mismatch |
| 8 | verify the **live** DB against a snapshot | `verify --file <snap> --db ~/.estate/estate.db` | **4** | `MISMATCH the live database no longer matches this snapshot in: file_sha256, ledger_merkle_root, ledger_rows` (13846 vs 13849 rows) |
| 9 | rewind pointed at a tampered snapshot | `rewind --at <tampered>` | **4** | `refusing to mount a branch whose roots differ` -- **no file mounted** |
| 10 | snapshot taken where git HEAD is unreadable | `cd /tmp && snapshot` | 0 after fix (was **2**) | resolves `recovery/idp-20261031@3679304d` -- see 1.3 |

### 1.3 two defects a real trial found, and their fixes

Running `snapshot` from a directory that is not a git repo printed `BLIND git HEAD unreadable` and
exited **2**. The chronicle's entire job is to bind state to git history, so silently resolving to
the current directory was the bug, not the refusal.

Fixed by `resolve_repo()`: tries `--repo`, then cwd, then `~/Documents/code/idp` and
`~/Documents/code/estate-core`; the first that answers `rev-parse HEAD` wins, and **every candidate
tried is named** if none does. Applied to `snapshot`, `verify`, `rewind`, `status` and `list`.

Proof (row 10): from `/tmp`, exit **0**, bound to
`recovery/idp-20261031@3679304d`. This was found because a *science trial* ran the chronicle from a
non-repo directory -- not because the chronicle was re-read.

**Second defect, found by `verify-proof` re-running row 8.** `verify` accepted a `--db` flag and
**never read it**: it derived the snapshot and compared it to the note pointer, so "verify the live
database against this snapshot" silently verified the snapshot against itself and printed
`matches: true, exit 0`. An option accepted and ignored is a fail-open door -- it reports success for
a measurement that never happened (AGENTS.md sec.9 R1).

Fixed: `--db` on `verify` is `None` by default (it no longer inherits the parent `common()` default,
which had made the phantom value appear even when the flag was absent), a different `--db` is
derived and compared, and live drift **exits 4** with the differing keys named and
`"verified": false` in the object. Rows 8 and 10 are re-run by `verify-proof` on every check.

**RPO class is `snapshot`, and this file says so.** It is not WAL micro-shipping at RPO <= 1s. That
would need credentials this machine does not hold (`rclone`, `litestream`, `aws` are all
NOT INSTALLED), and the design's claim is refused rather than quietly downgraded.

---

## 2. pack_genesis_spore -- the seed

**Claim: the estate's laws, gates and identity can be packed into one self-verifying file.**

| # | command | exit | printed |
|---|---|---|---|
| 11 | `pack_genesis_spore --pack --profile core --budget 8192` | **0** | `"packed_bytes": 5621, "fits": true, "sections": {"laws":1,"boot":1,"identity":4,"gates":0}, "gate_index_len": 26` |
| 12 | `pack_genesis_spore --pack --profile full --budget 8192` | **3** | `"packed_bytes": 42299, "fits": false` -- the complete falsifier set does **not** fit, and says so |
| 13 | `--unpack <spore> --dest <empty>` | 0 | `"files_written": 6, "mismatches": []` |
| 14 | compare all 6 unpacked files to the pack | -- | **6 identical, 0 differ** |
| 15 | all 26 `gate_index` hashes vs `features/gates/` on disk | -- | **all resolve, drift `[]`** |
| 16 | packed `laws/AGENTS.md` vs the live toml block | -- | **byte-identical, 1929 bytes**, contains `[invariants]` and `[merge]` |
| 17 | corrupt one byte of the payload | `--check` | **2** | `BLIND payload sha256 differs from the header` |
| 18 | edit a file body **and** recompute the outer hash | `--unpack` | **4** | `MISMATCH AGENTS.md: sha256 mismatch inside the spore` |
| 19 | scan the whole spore for secret material | `rg` | -- | **0 matches** for `BEGIN ... PRIVATE KEY`, `AGE-SECRET-KEY`, `ghp_`, `sk-` |

### 2.1 the design's 4KB claim was falsified by measurement

The design asserted an irreducible 4096-byte spore. Measured, on the real inputs:

| section | packed cost |
|---|---|
| laws (the toml policy block) | 1360 |
| gate bodies (26 `.feature` files) | 22832 |
| guardian-trust anchor | 555 |
| boot contract (5 facts) | 348 |
| 3 public keys | 329 |
| gate index (26 name+hash) | 1188 |
| chronicle pointer | 234 |

**5621 bytes** for the law set; **42299** for the complete falsifier set. 4KB is not reachable by
content that actually informs a rebuild. Shipping a 4096-byte spore would have meant shipping fewer
laws than the estate has -- a gate that cannot fail -- so the budget became a **reported number**
with two profiles instead of a wish. `--profile core` fits 8192 at exit 0; `--profile full` reports
OVER at exit 3.

### 2.2 defects the packer's own tests found (each fixed)

- `agent.pub.pem` is a genuine `BEGIN PUBLIC KEY` sitting in `~/.estate/keys/`. A `.pem`-suffix rule
  refused **the very key the spore must carry**. The check is now body-authoritative
  (`SECRET_BODY`), and a `.pem` with no public-key marker is refused as *unknown*.
- The identity matcher keyed on the substring `public` and pulled in `keyword.pub.html`,
  `inventory.published-port.json` and a 3.9 KB protocol `.md`. Narrowed to real key filenames.
- The same key was found under two roots and packed twice -> deduplicated on **sha256, not path**.
- `bin/genesis-first-boot` is Python, not shell, so a `FACT_` pattern matched nothing and the
  extractor silently fell back to the whole 5.7 KB script. Now anchored on the real
  `CHECKS = [("GitHub App identity", ...), ...]` block and extracts the five facts in order; if the
  shape changes it **says so** instead of smuggling the script in as information.
- Files are packed as **bytes**, never round-tripped through `str` (a non-UTF-8 byte had exited
  with `surrogates not allowed`).
- Identity scanning was `rglob` over four trees and was SIGTERMed at the 100s ceiling; now `os.walk`
  with pruned dirs and a `MAX_INSPECT` cap -- a full pack takes ~9s.

---

## 3. science_loop -- preregistration-first experiments
**Claim: an experiment loop can reach a verdict at zero marginal cost, and the verdict can be
re-derived from the database alone.**

No science tables exist in the real `estate.db` (verified: no `experiment*`, `prereg*`, `trial*`,
`science*` table), so the loop **creates and owns** three tables in its own `science.db` and never
writes to `estate.db`.

### 3.1 an end-to-end verdict on real measured data

The preregistered question was about this machine: *does a chronicle snapshot of the live
15 MB `estate.db` (VACUUM INTO + Merkle over 13842 rows) finish well inside the 100s ceiling?*
Preregistered threshold 60s, direction `lower`, sample size 3 -- **recorded before any trial ran**.

| # | command | exit | printed |
|---|---|---|---|
| 20 | `science_loop preregister --file prereg2.json` | 0 | `"prereg_id": "a57d3fed9d0cc64f", "rule_sha256": "8d1b671d...be84"` |
| 21 | `science_loop dispatch --prereg <id> --cmd trial.sh` | **0** | `"ran_now": 3, "usable_rows": 3, "required": 3, "complete": true` |
| 22 | `science_loop verdict --prereg <id>` | **0** | `"verdict": "SUPPORTED", "values": [4.57, 7.84, 9.02], "mean": 7.1433, "threshold": 60.0` |
| 23 | re-derive from raw rows, **independent of the tool** | -- | `rows=3 usable=3 mean=7.1433 re-derived verdict: SUPPORTED`; 3 **distinct** output hashes |
| 24 | recorded verdict row | -- | `SUPPORTED|3|7.1433|8d1b671d...|0` |

The three trials were three real chronicle snapshots of the live database. This is also the proof
that the chronicle **works**: 4.57s, 7.84s, 9.02s.

### 3.2 the falsifiers

| # | what was done | exit | printed |
|---|---|---|---|
| 25 | only 1 of 3 preregistered trials ran | **3** | `INCONCLUSIVE`, `usable trials < preregistered` |
| 26 | result on the wrong side of the pre-declared threshold (75s vs 60s) | **4** | `"verdict": "CONTRADICTED"` -- a clean negative is a verdict, not "no result" |
| 27 | rule edited in the DB after data was seen | **4** | `MISMATCH the preregistered rule was edited after it was recorded` |
| 28 | 3 trials all `exit 7` | **3** | `"total_rows": 3, "usable_rows": 0, "complete": false` |
| 29 | verdict for a prereg id that does not exist | **2** | `BLIND no preregistration deadbeef` |
| 30 | a rule type the engine does not implement | **2** | `BLIND rule type 'bayesian_posterior' is not implemented; refusing to invent a verdict` |

**Row 28 was a real defect found by its own falsifier:** `dispatch` first reported
`complete: true` on three *failed* trials, because it counted rows instead of usable data points.
Fixed to count `exit_code = 0 AND value IS NOT NULL`; it now exits 3.

### 3.3 an honest limitation, recorded rather than hidden

The host's `ollama` is **installed but broken**:
`CHECK failed: mlx_array_item_float16_`, `Failed to load MLX dynamic library libmlxc.dylib`,
`Error: exit status 1`. The first preregistration drafted was about ollama latency. Rather than
score that as "the hypothesis is refuted", it was discarded and a question this host *can* answer
was preregistered. **A broken instrument is not a scientific result.**

---

## 4. What this does not prove

Saying which facts are which (AGENTS.md sec.3: *"built" and "operating" are different facts*):

| thing | status | why |
|---|---|---|
| chronicle snapshot/verify/rewind | **operating** | proved against the real 15 MB, 13842-row `estate.db`, including live-DB drift detection |
| chronicle WAL micro-shipping (RPO <= 1s) | **not built, refused** | no credentials on this host; the design claim is refused, not downgraded |
| spore core profile | **built and self-verifying** | 5621 bytes, round-trips byte-for-byte, falsifiers fire |
| spore 4096-byte target | **falsified** | 5621 is the measured floor for the law set; 42299 for the full gate suite |
| science loop | **operating on real data** | a genuine verdict over three real measurements, persisted to `~/.estate/science/science-proof.db` and re-derived from raw rows by a separate script with `science_loop` imports poisoned |
| science loop at "serverless scale" | **not built** | no free-tier remote dispatch exists on this host; the compute tier is the local host, which is the only zero-marginal-cost tier present |
| **mycelium colonizer** | **operating** | real cloud-router LLM calls, one file colonised with exactly one added line, the file still parses and runs, and seven refusal paths each leave the target byte-identical. It colonises **one file per invocation**; fanning it across a repository is a scheduling job with its own budget, not built here |
| mycelium over `ollama` (local, free) | **not built, routed around** | measured: `_mlx_array_item_float16` is **absent from the x86_64 slice** of `libmlxc.dylib` on this i5-7360U and present in the arm64 slice -- MLX does not provide float16 item access on Intel. Not a missing library and not flag-fixable |
| FleetView `/work` + `/kill` board key | **unprotected, deliberate** | measured 2026-11-08: `FLEETVIEW_BOARD_KEY` is unset and the live backend logs `the destructive work/kill chain is UNPROTECTED`. It is *deliberately* fail-open on loopback (`serve.py`: "UNSET MEANS NO ENFORCEMENT, deliberately ... a laptop run must keep working with no vault loaded"). Recorded as a known gap, not claimed as protected; setting it needs a vault entry, which is the estate's secrets work, not this direction |

Three primitives are operational and proved. One is built and honestly measured against a target it
falsifies. None is claimed to be operating at the "serverless scale" the design describes, because
no zero-cost remote compute tier exists on this host to operate it on.

---

## 5. This document verifies itself

`verify-proof` re-runs every claim above against the current tree and exits 0 only if each one
still holds. It is the falsifier for this file: a claim that stops being true turns the verifier red.

```
cd ~/.estate/direction/2026-11-08-four-primitives && ./verify-proof
```

| # | printed |
|---|---|
| 31 | `checked 35 claims, 0 failed` |
| 32 | `PROOF.md reproduces on this tree` |
| 33 | exit **0** |

`verify-proof` sha256: `dba07ed72bcd42bfecb18051cca2f498ae4dbca3d0632b8d7d93432fa456acb9`

It has already earned its keep three times, and every time the finding came from **running** a
claim, never from reading it:

1. **3 claims failed with exit 2** because the *verifier* used the wrong `verify` signature (a
   positional path where the tool wants `--file`). An argument error exits 2 (BLIND), and 2 is not a
   verdict. The claims were right and the checker was wrong -- which is exactly why an independent
   re-run has to exist rather than a re-read of the prose.
2. **1 claim failed with exit 0 where 4 was asserted**, and this one was a real defect in the tool:
   `verify` accepted `--db` and never read it, so "verify the live database against this snapshot"
   silently compared the snapshot with itself and reported success. Fixed; the flag now derives the
   live DB and exits 4 on drift, and rows 8/10 stay under test.
3. **My own isolation check was measuring prose.** It grepped for `science_loop` and counted 4
   matches -- every one a *comment explaining that the tool does not use it*. Replaced with the
   poison probe in sec.8.2, which proves independence by execution.
4. **Every check passed `--db`, so the default was never executed.** A fleet-broadcast fact (the live
   runtime is `~/.estate/runtime/idp`, not `~/Documents/code/*`) prompted a re-read, which found that
   `rederive-verdict` and `science_loop` both defaulted to `~/.estate/science.db` -- the 0-byte
   placeholder deleted earlier in this same session. The command PROOF.md prints for the founder is
   the **bare** one, and the bare one answered `BLIND ... is missing or empty`. Fixed to the file the
   verdict actually lives in, and `verify-proof` now runs the bare invocation (sec.5.1, F3).

### 5.1 the verifier has its own falsifier

A verifier that cannot go red is not a verifier. `./falsify-proof` mutates the artifacts, demands
that `verify-proof` **fail**, then restores the tree and demands it be green again:

- a `rederive-verdict` whose comparison is disabled, i.e. one that **trusts the stored verdict
  instead of computing it** -- the fail-open it was written to exclude;
- a `science_loop` with the tuned-rule guard removed -- the fail-open that was actually found.

- a `rederive-verdict` whose **default path** points at a file that no longer exists, with every
  `--db` check still passing -- the defect found by the fleet broadcast.

All three mutants were chosen because a green run on any of them would mean the verifier had quietly
stopped measuring the thing its claim names.

---

## 6. Reproduce everything from nothing

```sh
A=~/.estate/direction/2026-11-08-four-primitives/artifacts

# chronicle: snapshot, verify, tamper, rewind
$A/estate-chronicle snapshot --db ~/.estate/estate.db --dest /tmp/x
$A/estate-chronicle verify --file /tmp/x/*.db                       # 0
$A/estate-chronicle verify --file /tmp/x/*.db --db ~/.estate/estate.db   # 4 (live has moved on)
$A/estate-chronicle rewind --at 2020-01-01T00:00:00Z --out /tmp/r.db      # 3

# spore: the law set fits, the full gate suite does not, and it says so
$A/pack_genesis_spore --pack --profile core --budget 8192 --out /tmp/c.dna   # 0
$A/pack_genesis_spore --pack --profile full --budget 8192 --out /tmp/f.dna   # 3

# science: preregister, dispatch, verdict
$A/science_loop --db /tmp/s.db init
$A/science_loop --db /tmp/s.db preregister --file prereg2.json
$A/science_loop --db /tmp/s.db dispatch --prereg <id> --cmd /tmp/trial.sh
$A/science_loop --db /tmp/s.db verdict  --prereg <id>                 # 0 SUPPORTED
```

Every one of these runs with no network, no credential and no paid tier.

---

## 7. The mycelium colonizer -- an LLM that can only add verified lines

**Claim: a non-deterministic model can be allowed to write to a file, without ever being trusted.**

The design's mycelium was "an LLM that colonises the estate by adding notes". A single sample from a
model is a coin flip -- measured this session: the same prompt answered at 256 tokens and returned
**empty content** at 2000, because the model spent the budget on reasoning. So the colonizer is
built around one rule: **propose, verify the proposed bytes, and only then write.**

### 7.1 a real colonisation, on a real file

| # | command | exit | printed |
|---|---|---|---|
| 34 | `mycelium --target target.py --anchor 'return hashlib.sha256(b"").hexdigest()' --dry-run` | **0** | `ok attempt=1 (dry-run, nothing written) note='# MYCELIUM: An empty leaves list returns the SHA-256 hash of an empty byte string'` |
| 35 | the same without `--dry-run` | **0** | `new_sha256=e5766f06...c50813 verified_after_write=True (parses)` |
| 36 | `diff pristine.py target.py` | -- | `7a8` / `> # MYCELIUM: With no leaves, the function returns the SHA-256 hex digest of an empty byte string.` -- **exactly one line added** |
| 37 | the colonised file still runs | **0** | `imports_ok=True`, `root_empty=e3b0c442...b855` (sha256 of the empty string -- behaviour unchanged) |
| 38 | dry run writes nothing | -- | `file_unchanged=YES` (cmp against a pristine copy) |

The lane was the **cloud router** (`https://llm.mumchimp.com`), measured at 423 and 764 tokens for
the two runs. `ollama` on this host is not used, because it is broken (sec.3.3).

### 7.2 the verifier had to be rebuilt twice, both times by its own output

This is the part worth reading, because it is the defect class this whole file exists to catch.

1. **`original in proposed` was wrong by construction.** A colonisation INSERTS a line, so the
   original text is split across the insertion point and can never be a contiguous substring. The
   check rejected **three correct answers in a row** and reported "the original text was not
   preserved" -- a verifier blaming the worker for its own arithmetic error. Replaced with a
   **round trip**: remove the added line and the result must equal the original bytes exactly.
2. **Extraction and verification drifted into two parsers for one grammar.** When the model began
   prefixing its note with `#` (so the file would still parse), the extractor learned to skip the
   comment token while the verifier still matched a bare `MYCELIUM:` -- so the verifier located the
   *wrong line* and rejected three more correct answers. Collapsed into one `find_note_line()` used
   by both.
3. **Then it wrote a file that could not run.** With those two fixed, the very first real
   colonisation succeeded -- and produced a `SyntaxError`: a structurally perfect single line added
   inside a function body is still a broken Python file. `verified_after_write=True` was **a
   fail-open**: the tool proved "nothing but the note changed" while the file stopped working. The
   colonizer now runs **the target's own oracle** (`ast.parse` for `.py`, `json.load`, `tomllib`,
   `bash -n`) on the proposed bytes *before* the write and again on the bytes *after* it.
   *"Nothing changed but the note"* and *"the file still works"* are two different facts.

### 7.3 the falsifiers -- every way it must refuse

| # | what was attempted | exit | printed |
|---|---|---|---|
| 39 | target file missing | **4** | `MISMATCH target .../nope.py is not a file` |
| 40 | anchor not present | **4** | `MISMATCH anchor 'NO SUCH ANCHOR' not found` |
| 41 | precondition `--require` unsatisfied | **4** | `MISMATCH target does not contain 'NEVER_PRESENT'; precondition failed` |
| 42 | binary target | **4** | `MISMATCH ... is not UTF-8 text; refusing to colonise a binary` |
| 43 | a requirement no honest fact can satisfy, 2 attempts | **3** | `SHORT 2 attempts produced no answer that passed verification; ... is unchanged (sha256 5b76d096...)` |
| 44 | an unreachable model | **3** | `reject attempt=1 why=empty_response lane_outcome=exhausted` -- the lane outcome is named, so a refusal cannot hide inside a generic SHORT |
| 45 | temp-file debris after a run | -- | `leftover_temp_files=0` -- `.mycelium-*` then `os.replace`, so a kill cannot half-write |

Every non-zero row above leaves the original file **byte-identical**, checked with `cmp`.

---

## 8. The science verdict reproduces from `science.db` alone

**Claim: the SUPPORTED verdict is a measurement, not a program asserting its own conclusion.**

`artifacts/rederive-verdict` opens `science.db` **readonly**, reads only raw rows, re-implements the
rule arithmetic itself, and never imports or spawns `science_loop`.

The evidence database is `~/.estate/science/science-proof.db` (28672 bytes, sha256
`5ce90ef01773c75ea033ffc1fe443a78edb526ca24066196483eeedaa03ed7ca`), holding three real chronicle
snapshots at **2.837s / 2.042s / 1.811s** against a threshold of 60s preregistered before any trial
ran (`rule_sha256 7441850c...a42b`).

| # | command | exit | printed |
|---|---|---|---|
| 46 | `science_loop --db ... verdict --prereg 65f04b1382c4c176` | **0** | `"verdict": "SUPPORTED", "values": [2.837, 2.042, 1.811], "mean": 2.23, "threshold": 60.0` |
| 47 | `rederive-verdict --db ~/.estate/science/science-proof.db` | **0** | `REPRODUCED SUPPORTED from .../science-proof.db alone (readonly, no science_loop code involved)` |
| 48 | the same under a poisoned import hook (see 8.2) | **0** | `PASS ran with science_loop imports poisoned and process spawning disabled` |
| 49 | the database is never written by the checker | -- | `before=after=5ce90ef0...d7ca` -> `I_readonly=YES` |

### 8.1 the falsifiers

| # | what was done | exit | printed |
|---|---|---|---|
| 50 | stored verdict text flipped to CONTRADICTED | **4** | `MISMATCH stored=CONTRADICTED re-derived=SUPPORTED` |
| 51 | **threshold tuned after the data** (60 -> 0.5), verdict text untouched | **4** | `MISMATCH the rule was tuned after the data: the verdict was decided at threshold=60.0 but the preregistration now says threshold=0.5` |
| 52 | `rule_json` edited, registered digest left alone | **4** | `MISMATCH the stored rule_json does not hash to the registered digest` |
| 53 | a trial row deleted (sample short) | **3** | `SHORT 2 usable trials < preregistered 3` |
| 54 | empty database | **2** | `BLIND ... is missing or empty -- there is nothing to re-derive` |
| 55 | the file is not a database at all | **2** | `BLIND cannot read ...: file is not a database` |

**Row 51 was a real defect found by its own falsifier.** The threshold-integrity check was placed
*after* the arithmetic comparison, so when the rule was tuned the re-derivation disagreed on
arithmetic and returned first -- the check that existed to *name* the tuning was dead code that could
never run. Reordered: **provenance first, arithmetic second.** It now reports which lie happened
instead of only that two numbers differ.

### 8.2 independence proved by execution, not by comment

My first isolation check grepped for `science_loop` and counted **4 matches** -- all four were
comments explaining that the tool does not use `science_loop`. A grep over prose is not a proof.
The real check is a **poison probe**: it re-runs `rederive-verdict` in a fresh interpreter with any
import of `science_loop` raising, and `subprocess.run/call/check_output/Popen` plus `os.system`
replaced by functions that raise. The tool still reaches `SUPPORTED` and touches none of them.

### 8.3 a claim I had to withdraw

Earlier this session I reported a SUPPORTED verdict whose evidence file,
`~/.estate/science.db`, was **0 bytes** -- a placeholder the tool creates in place. The verdict was
never re-derivable from it. The claim was re-made only after re-running the loop end to end into a
kept database and re-deriving from that. The 0-byte placeholder was then deleted (one path per
concept), and this file names the real file and its hash.

---

## 9. Reproduce the last two sections

```sh
A=~/.estate/direction/2026-11-08-four-primitives/artifacts

# mycelium: one verified line, on a copy
printf 'def f():\n    return 1\n' > /tmp/t.py
$A/mycelium --target /tmp/t.py --dry-run                       # 0, writes nothing
$A/mycelium --target /tmp/t.py                                 # 0, one line added, still parses
$A/mycelium --target /tmp/nope.py                              # 4 MISMATCH

# science: re-derive the verdict from the database alone
$A/rederive-verdict --db ~/.estate/science/science-proof.db    # 0 REPRODUCED SUPPORTED
cp ~/.estate/science/science-proof.db /tmp/t.db
sqlite3 /tmp/t.db "update science_verdicts set verdict='CONTRADICTED';"
$A/rederive-verdict --db /tmp/t.db                             # 4 MISMATCH
```

## 10. Reproduce the verification of the verification

```sh
cd ~/.estate/direction/2026-11-08-four-primitives
./verify-proof      # 0: checked 35 claims, 0 failed -> PROOF.md reproduces on this tree
./falsify-proof     # 0: mutates the artifacts, verify-proof goes RED, restore goes green
```

`falsify-proof` is the claim that matters most in this file, because it is the only one that can
falsify the document itself. If `verify-proof` ever stays green while an artifact's fail-open is
reintroduced, `falsify-proof` exits non-zero and says so.
