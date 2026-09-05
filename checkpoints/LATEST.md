# LATEST checkpoint — 2026-09-05 (both Otto bots must answer as themselves)

## RESUME HERE (2026-09-05T20:10Z)

Otto rollout: idp main pins hermes-agent main-84 (85986ab4) but Flux kustomization `otto-gateway`
is stuck on 13476e63 because `Job/otto-memory-store-4` is immutable and its image tag changes on
every bump. Fix in flight: `kustomize.toolkit.fluxcd.io/force: enabled` on
`platform/otto-gateway/memory-store-job.yaml` (branch fix/otto-memory-job-force, worktree
scratchpad/wt-flux-force). After merge: `gh workflow run oke-check --repo chidionyema/idp -f mode=apply`,
`bin/idp-kube rollout status -n otto-gateway deploy/otto-gateway`, then founder messages both bots
and the `worker.answered` lines are quoted. Founder also asked to verify the bot's "unverified"
list (Edge-TTS, screenshot handler, bench, STT, vision) against what is actually wired.

## Founder principle (2026-09-05, verbatim-ish, chat): "that is basically the model we follow for the
enterprise product shaping across platform so founder is both whole estate superadmin and also an
enterprise customer 0." Two hats, one platform: Ottototbot is the superadmin's estate bot, numun_bot is
customer zero's Otto; each must work exactly as a paying tenant's would (LAW 54). Next shaping step,
not started: give customer zero its own tenant row instead of sharing tenant `estate` with the
superadmin bot.
