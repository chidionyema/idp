# Olat Estate `ERA_1` Canonical Founder Decisions: Post-OKE Serverless Doctrine & `P0.T2` Backup Unblock

> **Status**: `SEALED_IN_ERA_1_CANON` (`https://github.com/chidionyema/argon.git` @ `main` & `genesis-live`)
> **Effective Timestamp**: `2026-11-02T03:55:00Z`
> **Directive to All Agents (`Codex`, `Claude`, `OTTO-00`, `AURA-00`, `ORACLE-00`, `CUSTODES-00`)**:
> Both legacy `ERA_0` pending items (`(1) Post-OKE Serverless Doctrine + OCI Account` and `(2) P0.T2 Backup Credentials`) are **resolved and closed**. No agent may block on Founder input for either item.

---

## Decision 1: Post-OKE Serverless Doctrine & OCI Account Disposition (`CLOSED`)

1. **`ERA_0` OKE & Handoff Fleet Permanently Retired (`REQ-01` / `mem://genesis/qa/prr10day`)**:
   - Oracle Kubernetes Engine (`oke`), persistent supervisor daemons (`handoff fleet`), and `face` are permanently retired and quarantined to offline evaluation history only.
   - Zero Kubernetes control planes (`kube-apiserver`, `etcd`, node-pool controllers) are permitted in `ERA_1`.
2. **Canonical Post-OKE Serverless Architecture (`REQ-20` / `mem://genesis/econ/zeroburn`)**:
   - **Control Plane & Sequencer**: Stateless GitHub Actions on `chidionyema/argon` (`HOP-03` Airlock Verifier + `HOP-06` Single Sequencer `genesis-main-sequencer`) + stateless Cloud Run / Cloudflare Workers containers.
   - **OCI Account Answer**: Keep the OCI account **strictly for Always-Free Ampere A1 ARM64 stateless worker capacity (`4 OCPUs / 24 GB RAM / $0.00/mo`)** running single-binary hermetic `capsule.toml` workloads pulled from `chidionyema/argon`—**never OKE, never stateful pets, never `$ > 0` paid OCI SKUs**. Any residual OKE cluster resources in OCI must remain terminated.

---

## Decision 2: `P0.T2` Backup Architecture & R2 Credentials (`UNBLOCKED — ZERO R2 BLOCKER`)

1. **Immediate `P0.T2` Unblock Without Waiting on R2 Credentials (`REQ-30` / `mem://genesis/storage/5tb_idp`)**:
   - `P0.T2` backups are **immediately unblocked and active today** using a **Zero-New-Credential 2-Tier WORM Spine**:
     - **Tier 1 (Git + Signed Bundle Mirror — Live Now)**: Full Git history, all `27` `inbox/incoming/*.envelope.json` drops, `/SOURCE_MANIFEST.json` (`Ed25519` signed), and `/public/olat-estate-genesis-main.bundle` mirrored directly on **`https://github.com/chidionyema/argon.git`** (`main`, `genesis-live`, `inbox/incoming`, `archive/oct31-relayops-snapshot`).
     - **Tier 2 (5TB Google Workspace / DriveFS Encrypted Cold Lake — Live Now)**: `XChaCha20-Poly1305` + `Zstd` (`9.4x`) encrypted backups stored on the Founder's existing **5TB Google DriveFS** (`$0/mo` marginal burn, `0` new API tokens required).
2. **Cloudflare R2 Disposition (`OPTIONAL_TIER_3_MIRROR`)**:
   - Cloudflare R2 is **demoted from a `P0.T2` blocker to an optional Tier-3 offsite mirror**.
   - If/when `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_ENDPOINT_URL` are added to Bitwarden, `public/sync-bitwarden-to-github.sh` (`/scripts/secrets/bitwarden-secret-manifest.json`) automatically syncs them to GitHub Actions secrets—**no agent may block `P0` execution waiting for R2 keys**.
