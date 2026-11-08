# Direction: four architectural primitives (as submitted 2026-11-08)

**Status: REVIEWED AGAINST THE ESTATE -- the premise does not hold.**
Saved verbatim below, then falsified section by section with the command and exit status that
proved each verdict. Artifacts that *can* be built on what actually exists are in `artifacts/`
and are proven in `PROOF.md`.

Source of this text: the founder's direction of 2026-11-08, copied unedited into section 0.

---

## 0. The direction as submitted

> Four architectural primitives are currently partially built across idp and argon, but
> disconnected from a unified execution loop. Connecting them requires four concrete engineering
> designs: a cryptographic time-machine, a holographic Kolmogorov bootstrap seed, a symbiotic
> zero-cost LLM colonizer, and a serverless verification-driven science engine.
>
> ### 1. Does idp / genesis Support Point-in-Time Recovery (Time Travel)?
>
> Current Estate Audit (genesis-kernel v0.5.3 & estate.db):
>
> Right now, you have half of a time machine:
>
> What works: Code and infrastructure manifests in idp, argon, and argon-sync are immutable Git
> Merkle DAGs (you can git checkout <sha> any historical code state). Furthermore, genesis-kernel
> (src/certifier.rs) already implements Gate 4 (compute_ledger_merkle_root), which hashes step_runs
> (ticket_id, step_idx, hmac_signature) into a pairwise RFC 6962 binary SHA-256 Merkle root, and
> your BDD spec (Demonstration 3) defines an RPO of <=5s and RTO of <=12s.
>
> What is missing: estate.db (step_runs, memory_store, people_graph, catechism_antibodies,
> experiment_preregistrations) runs in SQLite WAL mode on local/worker disks, but SQLite WAL alone
> overwrites pages on checkpoint and is not coupled to your Git SHA history. If you roll argon code
> back to Tuesday at 14:00, estate.db is still stuck on Sunday's mutated schema and rows.
>
> The Ingenious Solution: Bi-Temporal Merkle-WAL Chronicle (git-notes + Content-Addressable SQLite
> Pages) ... continuous WAL micro-shipping (RPO <=1s) ... refs/notes/genesis-chronicle ... Every
> time Greenlane promotes a commit or CifKernel certifies a step, the kernel writes a tiny 128-byte
> receipt ... `estate-chronicle checkout` ... Counterfactual Branching.
>
> ### 2. The Holographic "Genesis Spore": Minimal Info to Recreate the Entire Platform
>
> ... the Kolmogorov complexity K(Estate) ... irreducible: Root Cryptographic Identity
> (FOUNDER_ED25519_PUBLIC_KEY, 32 bytes); The Formal Laws & Invariants (the TLA+ safety properties
> GenesisSplitAuthorityCertifier.tla and the 6 Gherkin BDD acceptance trials
> six_certification_trials.feature ~2 KB compressed); the latest Merkle state pointer + encrypted
> vault bootstrap; the self-assembly compiler prompt + micro-loader.
>
> 4KB GENESIS_SPORE.dna ... Stage 0 wakeup ... Stage 1 state hydration ... Stage 2 epigenetic
> synthesis.
>
> ### 3. Colonising All LLM Platforms: The Symbiotic "Mycelium" Workforce
>
> Zero-socket symbiotic mycelium (WASI + steganographic Git/clipboard relay + proof-of-execution).
> Symbiont header binds each surface to the Oracle Rationing Protocol (Pass 1 batched execution)
> and 3-Shield Decision Council. Lane A connected CLI; Lane B browser Userscript "Genesis Symbiont
> Bridge"; Lane C air-gapped GENESIS-PACKET:// receipt via Telegram. Byzantine fault tolerance:
> free LLM surfaces are Proposal Generators only, accepted only through CifKernel. Viral
> self-upgrade against a held-out 6-trial suite via welch_t_stat and cvar_99_gbp.
>
> ### 4. Resurrecting the Specialist Research, ML & Data Science Plane
>
> Scrap Argo + MLflow + Postgres. Native estate.db science tables (experiment_preregistrations,
> experiment_trial_runs, cost_telemetry_ledger). GitOps preregistration trigger
> specs/experiments/EXP-*.yaml -> bin/science_burst_dispatcher.py -> Kaggle/Modal/OKE burst ->
> CifKernel::evaluate_empirical_experiment (Welch t-test) -> promotion_audit_log.
>
> ### Drop-in implementation spec
> bin/estate-chronicle.sh, spore/pack_genesis_spore.py, bin/science_burst_dispatcher.py, wired
> into release/otto-unified-20261107.

---

## 1. Verdict

Every one of the four designs rests on a stated precondition. Measured on this machine
(2026-11-08, executor alive pid 562, ceiling 100s):

| # | Precondition the design states | Measured | Verdict |
|---|---|---|---|
| 1 | `genesis-kernel v0.5.3` repo with `src/certifier.rs` | no such repo on disk; no `certifier*.rs` anywhere under `~/Documents/code` or `~/.estate` | **ABSENT** |
| 1 | `compute_ledger_merkle_root()` exists (Gate 4) | zero code hits; the only hits are this session's own transcript, plan and prompt logs | **ABSENT** |
| 1 | `step_runs` has `hmac_signature` to Merkle-hash | real column set is `id, ticket_id, step_idx, cmd, exit_code, duration_ms, ran_at` -- **no hmac_signature** | **ABSENT** |
| 2 | `GENESIS_SPORE`, `six_certification_trials.feature`, `GenesisSplitAuthorityCertifier.tla` | 0 files each; no `.tla` in idp | **ABSENT** |
| 3 | `mycelium`, colonizer, `refs/notes/genesis-mycelium` | 0 files | **ABSENT** |
| 4 | `experiment_preregistrations`, `experiment_trial_runs`, `cost_telemetry_ledger`, Welch/CVaR certifier, `science_burst_dispatcher.py` | 0 tables in `estate.db`, 0 code hits, 0 files | **ABSENT** |
| 1 | `estate.db` runs in SQLite WAL mode | `journal_mode = wal` on `~/.estate/estate.db` (15 MB, 3732 pages, 13812 `step_runs` rows) | **TRUE** |
| all | the work targets branch `release/otto-unified-20261107` | idp is on `recovery/idp-20261031`, 79 dirty entries; argon on `estate/cockpit-pin-and-mirror`, 104 dirty entries | **FALSE** |

So the direction is not "partially built and disconnected". Three of the four primitives have **no
implementation at all** on this machine, and the fourth (the science plane) has no tables, no
certifier and no runner. What does exist is real but different from the claim:

- `~/.estate/estate.db` -- a genuine CIF-style kernel database: `intent_tickets`, `step_runs`
  (13,812 rows), `ticket_fences`, `outbox_events`, `policy_decisions`, `patch_receipts`,
  `read_receipts`, `instruction_ledger`, `surface_yield_ledger`, `wwfd_decisions`, `mem_pointers`,
  `cockpit_config`, `optimus_evidence`.
- `idp/catalog/estate.db` -- a catalogue view: `assets`, `sessions`, `session_events`, `voice_turns`,
  `jev_decisions`, `provider_coupling`, `fleetview_*`, `meta`.
- Backup reality: `~/.estate/bin/estate-data-backup.sh` is a **restic snapshot to Google DriveFS**,
  and `backup-r2.yaml` is the R2 restic job. Restic is point-in-time *for files as a set*, at
  snapshot granularity, and is **not coupled to a git SHA**. That is exactly the gap the direction
  correctly identifies -- and it is the one gap that is real.

Per AGENTS.md sec.6, building the four designs verbatim would create a **fifth parallel
implementation** of layers the estate already has (a backup plane, a verification plane, a memory
plane). So the direction is revised rather than implemented as written.

---

## 2. Law it violates, and the law that is missing

Root cause of the direction's errors, per AGENTS.md sec.0: **the direction was written from a
transcript of an earlier session, not from the estate.** That is root cause R9 (fixes and rulings
stay in one session) and R11 (assertion instead of proof) in sec.9. A design that names
`src/certifier.rs` should be reading it.

The missing law, written here so it is written once:

> **D-LAW-1 -- A design that names a file, a table or a symbol must cite a read of it.** Before a
> design is accepted, every named path is resolved and every named symbol grepped; the resolution
> output is attached. A design whose cited artifacts do not resolve is a *proposal*, not a plan,
> and is labelled as such in its first line.

The existing law it broke: sec.3 ("Proof, not assertion") and sec.10 ("Do not guess. Search.").

---

## 3. What is actually buildable today, and what is not

### Buildable on real estate state (built and proven -- see `artifacts/` and `PROOF.md`)

1. **`estate-chronicle`** -- the honest half of the time machine. Snapshot `~/.estate/estate.db` with
   `VACUUM INTO`, hash the snapshot (sha256 over the file, plus a content Merkle root over
   `step_runs` rows as they actually are), attach the pointer to `refs/notes/genesis-chronicle`
   next to the git HEAD that produced it, and verify a restore by re-deriving both roots. This
   binds DB state to git SHA history, which is the real gap. It does **not** claim RPO <=1s: a
   `VACUUM INTO` snapshot is at-a-moment, not a WAL stream, and the command says which it is.

   Proven by: `artifacts/estate-chronicle` run against the live `~/.estate/estate.db`, giving a
   15 MB snapshot, an RFC 6962 Merkle root over the 13,812 real `step_runs` rows, a git note
   written and read back, and a `verify` that recomputes the root from the restored file and
   matches it -- and a `verify` that *fails* on a deliberately corrupted copy (the falsifier).

2. **`pack_genesis_spore`** -- the spore pattern, compiled from files that exist: the estate's laws
   as they actually exist (`AGENTS.md` sec.11 policy TOML, `idp/features/gates/*.feature` as the BDD
   body, `idp/bin/genesis-first-boot` as the micro-loader, the real Ed25519/founder identity if one
   is on disk, the chronicle Merkle pointer). Brotli when available, zlib otherwise, with the codec
   named in the 4-byte header. Proven by an unpack that reproduces every input byte-for-byte and
   re-verifies the embedded Merkle root.

   It does **not** claim Stage-2 "epigenetic synthesis": there is no TLA+ spec and no 6-trial
   Gherkin suite on disk to constrain an LLM, so the spore packs the gates that do exist and says
   so in its manifest.

3. **`science_loop`** -- the epistemic engine built against tables that are *created by this change*
   (`experiment_preregistrations`, `experiment_trial_runs`) in the real `~/.estate/estate.db`, with
   the guards the direction names because they are correct and cheap: backdated-trial rejection
   (`trial_ts > prereg_ts`), `min_n >= 2`, Welch's t with a Welch-Satterthwaite df guard, CVaR at
   99% in GBP, and a signed verdict. Proven by a full loop on a real row: preregister -> dispatch a
   local worker -> write BASELINE and CANDIDATE trials -> verdict PROMOTE or FALSIFY.

### Not buildable, with the reason (not a "remaining work" list -- these are refused)

- **WAL micro-shipping with RPO <=1s** to R2/OCI: no R2/OCI credentials on this Mac
  (`env` has no `R2_*`/`S3_*`), no `rclone`, no `aws` CLI, no `zstd`, no `litestream` binary
  (the single `litestream` hit is a text mention in `idp/rescued_patches2/temp-work.patch`).
  A shipper cannot be proven at 1s RPO without a destination, and a shipper that proves nothing is
  not shipped. `estate-chronicle`'s snapshot + git-note coupling is the part that needs no
  credentials and is proved.
- **`hmac_signature` ledger root**: the column does not exist. Adding it is a change to the
  executor's writer, which is a different claim on a different layer.
- **Stage-2 spore synthesis of `genesis-kernel`**: the kernel does not exist to re-synthesize, and
  the 6-trial suite it would be constrained by does not exist. Packing a constraint set that is
  empty would produce a spore that can never fail -- the sec.9 R2 defect, a gate that cannot fail.
- **Browser userscript "Symbiont Bridge" (Lane B)** and **`GENESIS-PACKET://` -> Telegram ingest
  (Lane C)**: both are founder-surface integrations and both depend on endpoints that do not exist
  (`genesis-founder-surface.pages.dev/api/mycelium/lease`). Building a client for an unbuilt server
  is the stitching sec.6 forbids. What is built instead is the **contract** they will speak, and it is
  exercised by the science loop's signed-receipt path.

---

## 4. Founder surface integration (the part that was asked for)

The founder reaches a capability through `/fleet` and by voice (AGENTS.md sec.3 and sec.9). So each built
artifact exposes itself as **one line of machine state** that /fleet can render and that voice can
speak, and nothing else:

- `estate-chronicle status --json` -> `{db, git_head, merkle_root, snapshot_path, snapshot_age_s,
  wal_bytes, verified}` -- one object, no prose.
- `pack_genesis_spore --check` -> `{bytes, codec, merkle_root, git_head, sections:[...], fits:bool}`.
- `science_loop status --json` -> `{preregistrations, trials, promoted, falsified, latest_verdict}`.

These three objects are the whole founder surface: rendered on /fleet as three rows, spoken as one
sentence each. Anything richer is a report to read later, which sec.9 forbids.

---

## 5. Files

```
~/.estate/direction/2026-11-08-four-primitives/
  DESIGN.md              this file (direction + review verdict)
  artifacts/
    estate-chronicle     python3, stdlib only, exit-code verdict
    pack_genesis_spore   python3, stdlib only (brotli if importable)
    science_loop         python3, stdlib only, sqlite3
  PROOF.md               machine output for every claim: command, exit, line, sha256
```
