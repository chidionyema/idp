# LATEST — session a0d64ea4 (crew#66 founder lane)

## RESUME HERE

Branch `feat/crew66-root-trust` (from crew459-portal-polish worktree): root-trust gate PR
for crew#66 ruling 5453747447 / crew#580. Files: bin/idp-root-trust (+ test
tests/test_incident_crew66_root_trust_register.py, 5 passed), docs/reference/policy/root-trust.md
(register, 33 entries, MEETS 11 / PARTIAL 1 / MISS 19), bin/idp-bootstrap-tailscale (written,
not run end to end), security-policy row, idp-ci + verify-drill rows, stale comments fixed,
vault-seed tailscale entry refused. Next: commit, push, bin/pr-report, PR (Tracked: crew#66,
Drill: root-trust), then tell the founder `bin/idp-bootstrap-tailscale` is ready to run.
Then the bootstrappers PR (#575–#579): bin/idp-estate-seed, router keys, github-app tokens,
bin/idp-bootstrap-cloudflare, bin/idp-bootstrap-vendors, umbrella bin/idp-bootstrap-estate.
Founder plan recorded crew#66 5453918598 (one-shot, "just you").

## RESUME HERE — crew#839, the namespace fence, 2026-09-04T18:0xZ (session 85f840c5)

The fence generator is built and the estate is measured. What is left is the pull request.

Built, all uncommitted in the working tree at the moment of this note:
- `bin/idp-ns-fence-gen` — one pass over `platform/ns-fences/allowances.yaml` + `measured.json`,
  writes 38 namespaces' LimitRange + ResourceQuota into `platform/ns-fences/` and their
  NetworkPolicies into `platform/ns-fences/network/`. Idempotent, proved byte-identical.
- `platform/ns-fences/allowances.yaml` — the input data: sizing headroom, five exemptions each
  with a reason, per-namespace declared flows, and the hand-tuned staging and otto-golden
  ceilings moved in as `overrides` (their `quota.yaml` files were deleted; the generator owns them).
- `bin/ns-fence-gate` — `--live` now refuses to report a pass when no CNI enforces policy;
  manifest mode's ok line says it graded files, not protection.
- `bin/idp-ci` — new blocking step 6b runs the gate over `platform/`. Until now it ran only on
  two fixture files, which is why 38 namespaces went unfenced with the gate green.
- `clusters/oke/platform.yaml` — Flux row for `platform/ns-fences` (the quota half only).
- `platform/observability/superset.yaml:189` and `docs/how-to/onboarding/ns-fence-gate.md` —
  both stopped claiming a protection that does not exist.

The finding that reshaped the ticket, measured on the live cluster: **the CNI is flannel and
nothing enforces NetworkPolicy.** 16 policies already in the cluster, including otto-golden's
both-ways default-deny of 41 hours, have never denied a packet. Staged for the founder
(Telegram message_id=22884): install Calico in policy-only mode beside flannel. Until that
lands, `platform/ns-fences/network/` stays unwired.

Next step: branch off `origin/main` (do NOT commit on `deepseek-build-lane`, which is where the
edits currently sit), commit the paths listed above, open the pull request with `Closes #839`,
a `Drill:` line, `# large-pr-intended`, and auto-merge on.

## RESUME HERE — 2026-09-04T18:40Z, session 5f6f4e72, lane idp

Leaving the estate-db work finished and picking up crew#838 CP1 on the founder's word
("finish itt", after a review of DeepSeek's report).

Estate-db, closed: idp#1537 and idp#1546 are merged, so all ten `estate-db` copy Jobs are
fixed in git. otto-gateway's copy is `Complete 1/1 7s`. The last one, hindsight `-r5`, runs
once Flux applies idp#1546; `estate-db-migrate` goes Ready behind it and the 23 Flux objects
waiting on it — llm, then research-engine — reconcile. Nothing on me there.

crew#838 CP1, what is being finished: DeepSeek adopted `survival-stack/scripts/migrate-domain.mjs`
into `bin/idp/migrate-domain/` but never pushed it (`a6cddf73` is local to this checkout, and
`origin/deepseek-build-lane` does not contain it) and opened no pull request. Six gaps to close:
push it as a branch off main, port the tool's own tests (`survival-stack/test/cf-auth.test.js`
and `test/helpers/mock-cf-api.mjs`), strip the Telegram helpers still in
`bin/idp/migrate-domain/console/checks.mjs:76-97`, delete the survival-stack original so there is
one copy, add the drill row and the catalogue entity, and arm auto-merge.

Worktree: `$SCRATCH/md` on branch `feat/crew838-cp1-migrate-domain`.
