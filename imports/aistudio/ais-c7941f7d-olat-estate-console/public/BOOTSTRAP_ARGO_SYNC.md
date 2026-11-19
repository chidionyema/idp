# `chidionyema/argon` — Zero-Friction GitHub Sync & Day-0 Bootstrap Guide

## Why Couldn't the Container Push to `github.com/chidionyema/argon` by Itself Yet?

Here is the exact technical reason without jargon:

1. **Where I Run**: I run inside an isolated Google Cloud Run container (`ais-dev-...run.app`) managed by AI Studio.
2. **What the Container Has**: It has `git 2.34.1`, `node v22.22.0`, full source history, and outbound HTTPS access to `api.github.com` (`HTTP/2`).
3. **What the Container Requires for Remote Push**: Your private GitHub repository (`https://github.com/chidionyema/argon.git`) requires authentication (`HTTP 401/404` when unauthenticated). The token (`ARGON_GITHUB_PAT`, `GITHUB_TOKEN`, or `ARGO_SYNC_PAT`) is read from AI Studio Secrets and used via a secure non-argv Authorization header.
4. **What We Wired**:
   - Updated `npm run sync:github` so that **on every sync/build**, the container pushes `genesis-live`, `inbox/incoming`, and `--tags` directly to `https://github.com/chidionyema/argon.git` **strictly without `--force`**.

---

## How to Unlock 100% Automatic Direct Push Forever (Takes 30 Seconds Once)

### Step 1: Add `ARGON_GITHUB_PAT` in AI Studio Secrets (Set Once, Never Touch Again)
1. On GitHub, create a **Fine-Grained Personal Access Token** (`Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens`) scoped to **`chidionyema/argon`** with **`Contents: Read and write`** and **`Workflows: Read and write`**.
2. In **Google AI Studio**, open the **Secrets / Environment Variables** panel (the **Key icon** in the sidebar) and add:
   - **Name**: `ARGON_GITHUB_PAT` (or `GITHUB_TOKEN`)
   - **Value**: `github_pat_...`
3. **That’s it.** From that moment on, every sync pushes straight to `https://github.com/chidionyema/argon.git` (`genesis-live`, `inbox/incoming`, and `--tags`) automatically—zero reminders, zero laptop commands.

---

## Or: Seed `chidionyema/argon` Right Now in 1 Single Line

If you want `chidionyema/argon` populated right this second from any terminal where you are already logged into GitHub (`gh` / SSH / HTTPS credential helper), paste this **one line**:

```bash
curl -fsSL https://ais-pre-pnuj6ysc7lwv3pfgp5xuxv-534240513427.europe-west3.run.app/bootstrap-argo-sync.sh | bash
```

### What That 1 Line Does Automatically:
1. Downloads the Ed25519-signed `/SOURCE_MANIFEST.json` and full Git repository bundle (`/olat-estate-genesis-main.bundle`) from the live container.
2. Clones the full Git repository (`main`, `genesis-live`, `inbox/*`, and all tags) into `/tmp/argo-sync-bootstrap/repo`.
3. Runs `npm ci`, `npm test` (`141/141 PASS`), `npm run enforce` (`8/8` Laws `I1–I8` + `8/8` mutation falsifiers), and `npm run verify:release`.
4. Pushes `genesis-live`, `inbox/incoming`, and `--tags` directly to **`https://github.com/chidionyema/argon.git`** without `--force`.

---

## Everything Included in `argon` to Bootstrap from Scratch

Once pushed to `chidionyema/argon`, any developer, CI runner, or autonomous agent (`OTTO-00`, `AURA-00`, `ORACLE-00`, `CUSTODES-00`, `Codex`) can clone and bootstrap the entire estate with standard Git:

```bash
git clone https://github.com/chidionyema/argon.git
cd argon
npm ci
npm test          # Runs all 141 deterministic unit tests (REQ-01 .. REQ-52)
npm run enforce   # Runs all 8 physical on-disk Law Enforcers (I1..I8) + 8 Mutation Falsifiers
npm run verify:release # Non-mutating release verification
npm run dev       # Launches the full Genesis Console on http://localhost:3000
```

### Key Bootstrap Manifests & Specs in Root of `argon`:
- `/AGENTS.md` — 110-line (`<= 120` cap) Single-Pass `mem://genesis/*` BBHash + Roaring64 Constitutional Spine (`REQ-01` .. `REQ-52`).
- `/GENESIS_SPEC.md` — Full Canonical Architecture & Engineering Specification (`v1.0.27`).
- `/laws.yaml` — Machine-readable Constitutional Laws (`I1–I8`) bound to physical on-disk enforcers.
- `/SOURCE_MANIFEST.json` — Out-of-process `Ed25519` + `SHA-256` signed manifest covering all core artifacts.
- `/scripts/enforcers/enforce_i1_to_i8.ts` — Real out-of-process Law Enforcers + Counterfactual Mutation Falsifiers (`B0–B2` cured).
- `/scripts/sync/sync_genesis_live_to_github.ts` — Automatic headless GitHub sync daemon (`argo-sync` + `argon` + `private-inbox`).
- `/public/bootstrap-argo-sync.sh` — 1-command turnkey bootstrap script.
- `/inbox/incoming/*.envelope.json` — Conflict-free `G-Set` instruction & audit envelopes (`DROP-2026-1049` .. `DROP-2026-1072`).
