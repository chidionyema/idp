# CLINE ONE-SHOT MISSION: idp#8416 Live Dispatch & Edge Verification

Token budget is hard-capped. Zero narration. Zero repo-wide search.

## Step 1 (Read Codex verdict or run discriminator once)
If `oneshot_verdict.json` does not exist, run `python3 bin/oneshot_router_unblock.py --repo-root . --out oneshot_verdict.json`.

## Step 2 (Execute ONLY based on `decision.branch`)
- **BRANCH_2_BOOTSTRAP_DISPATCH_NEEDED**: Trigger the Cloudflare bootstrap workflow on `main` via `gh workflow run`, watch it to completion (`gh run watch --exit-status`). If it fails, print ONLY `gh run view <id> --log-failed | tail -n 25` and STOP. If it succeeds, proceed immediately to BRANCH_4.
- **BRANCH_4_DEPLOY_AND_VERIFY**: Trigger the `router-edge` Zone B deploy workflow on `main` via `gh workflow run`, wait for completion, then run `curl -sS -i https://llm.meridianlabs.cloud/health`.
- **BRANCH_0_ALREADY_OPERATIONAL** (or after HTTP 200 + `zone-b-cloudflare-edge` above):
  1. Verify `GET https://llm.meridianlabs.cloud/health` returns HTTP `200` containing `zone-b-cloudflare-edge`.
  2. Run one authenticated `POST https://llm.meridianlabs.cloud/v1/chat/completions` (`model: role:coder`, `max_tokens: 32`).
  3. If `deepseek-flash` returns HTTP `402 Insufficient Balance`, confirm failover to `zai-glm-flash` or `openrouter-nemotron-free` returns HTTP `200`; if not, demote `deepseek-flash` priority via `PUT /admin/v1/roles` so `zai`/`openrouter` serve traffic immediately.
- **BRANCH_1** or **BRANCH_3**: Do NOT dispatch or retry. Stop immediately and report the exact blocker line.

## Done Contract
Done ONLY when `GET https://llm.meridianlabs.cloud/health` returns HTTP `200` with `zone-b-cloudflare-edge` AND `POST /v1/chat/completions` returns HTTP `200` (with exact UTC timestamp and `cf-ray`). Otherwise output `NOT_OPERATIONAL` + exact last 15 error lines and stop.
