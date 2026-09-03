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

## RESUME HERE (2026-09-02T19:25Z, lane .wt-dagster-port)
Founder instruction: user-deployment probe timeouts to 30s. Measured in-pod: exec health-check healthy path = 5s wall at 250m CPU, so the handler moves to the kubelet-native gRPC probe (server answers grpc.health.v1 SERVING, measured). Branch fix/dagster-probe-grpc-30s off origin/main carries platform/dagster/dagster.yaml probe block + tests/test_incident_dagster_user_deployment_probe_defaults.py (6/6 local green). Next: push, PR, green, founder merges. Cluster note: dagster kustomization+HelmRelease read CONVERGED-GREEN at 19:2xZ under the 5s exec probe — the flap class is still live until this lands.

## RESUME HERE (2026-09-03T00:0xZ, session a14fc078, lane idp)
Founder said "ship it" for feat/techdocs-publish-under-tmp (52d9acd7 — Docs tabs publish under /tmp, fixes the founder-gods-view ENOENT/404 he pasted). Main moved bb4b2113→116e8b63 so a fast-forward is impossible; next step: isolated worktree at scratchpad/ship-techdocs on 116e8b63, merge 52d9acd7 with estate-agents[bot] identity, push HEAD:main (fall back to PR+--admin if the ruleset refuses direct push). feat/reports-tab (f901d8c4) still awaits his word — do NOT ship it on this word.

## RESUME HERE (54539261, 2026-09-03T02:58Z)
Fix in flight: otto-golden never rolls — platform/otto-golden/kustomization.yaml has no images: block, so the untagged hermes-agent image (IfNotPresent) is frozen at first pull; days of merges never reached the pod. Branch otto-image-roll (worktree scratchpad/idp-pin) adds the images: block pinned to main-63-9fdff657c3ad225f7b7b7e107214103b5fe49157 with the flux-system:hermes-agent:tag marker (same pattern as platform/hermes-agent/kustomization.yaml:32). Then PR, green, founder word.

## RESUME HERE (2026-09-03T10:16Z, session 54539261)
Otto-golden allowlist SHIPPED: PR 1234 merged 2fbdd965, chain verified live 10:07Z (pods rolled, fail-loud config parsed) — founder can message @numun_bot but boot has NO live model yet (deterministic stub; router lanes exist unwired).
Live thread: founder wants KIMI as PRIMARY, refuses terminal steps (R73) and ruled "founder = enterprise client zero" (recording as R75 in crew docs/rulings now). His existing Kimi key: ~/.kimi-code holds only OAuth tokens (not a root). One answer chosen: he pastes his key in the LiteLLM console (llm.mumchimp.com/ui alive, 200/200, SSO), model row `kimi`; follow-up = remove env-based kimi row from llm config once DB row live, then wire otto router (needs his "wire it").
Open: crew#819/#820 DO NOT START; kimi lane overlap with session 2c88870e flagged on feed 10:10Z.

## RESUME HERE (2026-09-03T10:50Z, session 54539261)
R76 purge mandate (founder doc 2026-09-03T1036Z...25579e42.md + explicit "Do it now"): worktree .wt-purge off origin/main — delete prose-pinning tests via one AST pass, AGENTS.md No-Prose rule + gate, push PR. Merge stays the founder's.
