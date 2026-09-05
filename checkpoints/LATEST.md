# LATEST — session 2c88870e (.wt-vendor-probe, Kimi/aider lane)

## RESUME HERE

Kimi lane is blocked on the root itself: apply run 33711941272 (2026-09-03 03:42Z) proved
SEED_KIMI_API_KEY refused at all three Kimi homes and SEED_DEEPSEEK_API_KEY refused by DeepSeek.
PR 1201 (e7d2e684) merged: the seeder probes every Kimi home and writes MOONSHOT_API_BASE.
Waiting on the founder to re-set both repo secrets from his own tab (Telegram 21834) and say
"go"; then: gh workflow run oke-check.yml --ref main -f mode=apply, read the kimi seeder line,
wait ~10 min for the ExternalSecret, one router call with model kimi, report MEASURED.

Switching now (2026-09-03 04:1xZ) to record the founder's ruling "no agent can proceed without
the estate snapshot" as docs/founder/estate-snapshot-is-mandatory.md on branch
docs/founder-estate-snapshot-mandatory, then back to the Kimi wait.

## RESUME HERE (2026-09-05 12:55Z, Headlamp)
Headlamp credential prompt: the minted kubeconfig now carries the absolute oci path and SUPPRESS_LABEL_WARNING in its exec block (bin/idp-kube), and bin/idp-headlamp-mac links it into the desktop app store and ~/.kube/estate.yaml. PR fix/headlamp-exec-plugin.

## RESUME HERE (2026-09-05 13:25Z, Otto lanes)
Probe otto-answer-probe-29810160: bulk and verify lanes point at deepseek, which the router does not serve (400); Otto key allowlist was kimi,minimax,deepseek so gemini and embed were 403. PR fix/otto-lanes-gemini moves bulk+verify to gemini in the three lane files and sets the key rows in bin/idp-estate-seed to minimax,gemini,embed (agent-workforce: minimax,fast,embed). After merge: gh workflow run oke-check.yml -f mode=apply so idp-router-key updates the live keys.

## RESUME HERE — 2026-09-05T20:5xZ, idp session 2eb24bf7 (specs lane)

**Doing:** writing the two build specs the founder asked for
(`~/.claude/docs/founder/2026-09-05T2025Z-ok-need-do-addrees-quicck-wwe-have-deepseek-29766295.md`):
`docs/specs/key-ingest-door.md` and `docs/specs/two-hats-tenant-split.md`, plus the ADR 0020
amendment recording that Bitwarden cannot be written to.

**Why a worktree:** this checkout is shared. At ~20:50Z another session stashed my tracked edits
(`stash@{0}`, "wip before sync branch") and a `git clean` deleted my untracked new files —
`bin/idp-human-vault-probe`, `docs/specs/key-ingest-door.md`,
`docs/specs/two-hats-tenant-split.md` — which had to be rewritten. Branch:
`spec/two-hats-and-key-ingest`. Worktree under the session scratchpad. Nothing of another
session's is carried: `stash@{0}` also holds their `checkpoints/LATEST.md` and is left alone.

**Measured, and it is the load-bearing fact:** Bitwarden Secrets Manager refuses a plaintext write
(`400 Key is not a valid encrypted string`) because it is zero-knowledge, and the estate project
holds zero secrets while the machine account reads it fine. So the portal's one-shot ingest road
writes to `estate-vault`; a zero-knowledge store is a source to sync from, never a destination.
Re-measure with `bin/idp-human-vault-probe --write`.

**Still down:** `cyrus-webhook` is `SecretSyncedError` on `cyrus-linear-api-token`. The fix is the
door, not a fourth trip to Bitwarden's web interface.

**Next:** commit the specs in the worktree, push, open the PR.
