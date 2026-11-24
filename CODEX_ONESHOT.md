# CODEX ONE-SHOT MISSION: idp#8416 Router & Credential Delivery Unblock

Token budget is hard-capped. Zero narration. Zero Drive JSON reads. Zero Zone A/Mac edits.

## Step 1 (1 command only)
Run `python3 bin/oneshot_router_unblock.py --repo-root . --out oneshot_verdict.json` from the `idp` repo root and read ONLY `oneshot_verdict.json`.

## Step 2 (Execute ONLY the single matched `decision.branch`)
- **BRANCH_1_WORKFLOW_WIRING_BUG**: Open ONLY the single workflow file named in `decision.next_action`. Fix the missing `environment:` binding or `CLOUDFLARE_API_TOKEN` / `SEED_CLOUDFLARE_WORKERS_TOKEN` secret mapping. Run local workflow lint/tests, commit, and push through Greenlane. Do NOT mint new tokens.
- **BRANCH_2_BOOTSTRAP_DISPATCH_NEEDED**: Inspect ONLY `github_state.bitwarden_sync_failure.tail_15_lines` and the workflow calling `bin/idp-bootstrap-cloudflare`. If a 1-line delivery bug exists in the workflow, patch it via Greenlane; otherwise hand off directly to Cline to dispatch the bootstrap workflow on `main`.
- **BRANCH_3_CLOUDFLARE_ZONE_OR_SCOPE_BLOCK**: STOP immediately. Do NOT edit code. Print ONLY the 10-line raw error from `latest_failed_run.tail_20_lines` and escalate to Founder (Cloudflare account `4912457480997df81450b3ea614ccf3c`, zone `meridianlabs.cloud`).
- **BRANCH_4_DEPLOY_AND_VERIFY**: Make zero code edits. Hand off immediately to Cline to dispatch the Zone B deploy workflow on `main`.
- **BRANCH_0_ALREADY_OPERATIONAL**: Make zero code edits. Hand off to Cline for `/v1/chat/completions` pool probe.

## Hard Stop Rules
1. Never infer "secret missing from estate" from an empty CI env var.
2. Never stamp any issue `OPERATIONAL` on a `raw.githubusercontent.com` check.
3. Max 2 tool passes after reading `oneshot_verdict.json`; halt and output raw stdout/stderr if blocked.
