# LATEST

## RESUME HERE — cyrus delivery door, 2026-09-06 04:50 GMT+1

Founder ask: ", ensure cyruus is working properly lso"
(`~/.claude/docs/founder/2026-09-06T0248Z-deepseek-agent-appeas-stucj-a9476b49.md`)
plus the Live Proof Protocol in
`~/.claude/docs/founder/2026-09-06T0310Z-to-ensure-pr-1954-fully-resolves-these-failure-79fbe16e.md`.

State: cyrus is MEASURED_FAIL. Six walls found and fixed and merged (#1949, #1954, #1957);
a seventh is open.

Wall 7, open: cyrus migrates its own config on boot and writes it back, so the entrypoint's
symlink into the read-only ConfigMap is an EROFS exit:
  [ERROR] [CLI] Failed to start edge application: EROFS: read-only file system,
                open '/var/lib/cyrus/.cyrus/config.json'
Fix in hand, uncommitted: `platform/cyrus/entrypoint.sh` copies instead of linking, and
`platform/cyrus/README.md` gains section 6. Both lint clean, 99 lines.

Next step: worktree `scratchpad/wt-cfg` on branch `fix/cyrus-config-writable` from origin/main,
carrying only those two files. Open the PR, merge, wait for the image build and the Flux
reconcile, then run `scratchpad/cyrus-proof.sh`.

Proved already on image main-5270-51d377a6: the init container clones all three repositories
("cyrus-entrypoint: checkouts ready"), and the vault token is a GitHub App installation token
that reaches idp, crew and hermes-v2 (200/200/200).

Still open after that: move the Linear webhook registration
(id 5c755f6e-c32e-477e-9382-be9eab8921a8) from /webhook to /linear-webhook, then drop the
deprecated alias from httproute.yaml and the gate's open_paths.

## RESUME HERE (2026-09-06T04:15Z, session d6e854d8) — Otto hands + cyrus wall 8
Otto: step 5 (PR 1972) is deployed (otto-gateway-5986cdf7fc, OTTO_TOOLSETS set) but the deployed
command reads `if [ -n "" ] && [ -d "$HERMES_ENV_DIR" ]` — Flux postBuild substitution turned
`${HERMES_ENV_DIR:-}` (platform/otto-gateway/deployment.yaml:156) into "", so the fork's credentials
(GITHUB_TOKEN, EXA, ESTATE_MCP_KEY) are never exported; `gh auth status` in the pod: not logged in.
Fix on branch fix/otto-envdir-substitution (scratchpad wt-otto): test `-d "$HERMES_ENV_DIR"` only.
Cyrus: EROFS wall is past on main-5300; new exit `Repository "idp" is not linked to a Linear
workspace` (cyrus-core requireLinearWorkspaceId). Linear org id ec650f84-2971-4e51-8991-bda953c00d5e
(urlKey crewestate, team MUM). cyrus builds `new LinearClient({accessToken})` = Bearer header, and
Linear refuses a personal API key as Bearer (measured with curl) — so the mounted linear-api-token
cannot drive cyrus's Linear client; needs an OAuth token. Branch fix/cyrus-linear-workspace (wt-cyrus).
Founder doc: ~/.claude/docs/founder/2026-09-06T0355Z-otto-s-observer-writes-json-to-stdout-yet-e68777e1.md

## RESUME HERE (2026-09-06T07:30Z, session d6e854d8)
PR 1978 and 1979 are merged. Main carries `bin/idp-flux-subst-gate` without the
`files_under` root-path skip, so the gate reports 8 false hits on main; the fix is
commit 1e47109d, being re-opened as branch `fix/flux-subst-gate-root-rescan` from
worktree scratchpad/wt-otto. Founder question of 07:21Z (docs/founder/2026-09-06T0721Z-answer-pls-6064aa62.md)
about the oke-check: answer is in the reply, not on a menu.
