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

## 2026-09-06 00:40Z — showcase lane, resumed (pi session)
Branch feat/backstage-showcase-sandbox in scratchpad wt-showcase. Sandbox plumbing finished and
the 9-row pin green: fixed the workflow YAML (unquoted colon) and the HelmRelease's duplicated
seeded Service; generated the portal button (bin/idp-portal-buttons); rewrote the runbook to the
button design. Design correction on top of the 23:55Z note: the shop's namespace and HTTPRoute
moved to the STANDING launch lane (platform/sandbox/launch) — external-dns publishes only from
routes that exist, and cert-manager re-validates every listener hostname at each renewal, so a
route pruned with the sandbox would fail the whole edge certificate between sandboxes (crew#684).
Next: bin/idp-ci green, PR, then the prospector https-sandbox listener (merge after the idp PR),
then the /showcase page itself (research: scratchpad showcase-marketing.md).

## 2026-09-06 01:20Z — showcase lane, sandbox plumbing shipped for review
idp PR #1926 (PASS idp-ci on the committed tree), prospector PR #818 (https-sandbox, own cert,
merges second), spec PR #1918. Merge order and first-launch steps are in #1926's body and on
crew#805. Next unit of work: the /showcase page itself per spec #1918, research in this
scratchpad's showcase-marketing.md (7 sections, claims table with file receipts).
