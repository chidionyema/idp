# Estate feed

One handoff per session per 30 minutes (R33). Newest at the bottom. Written by `python3 ~/.claude/scripts/feed-guard.py append`; read with `status`.


## 2026-09-10T12:11:11Z · session 01a08284 · lane wt-dagster-bs
🟢 Done: PR #2899 MERGED — /dagster proxy in backstage/app-config.yaml + Scheduler tile on /ops; PR #2901 MERGED — bin/catalog-platform UI_DOORS table wires the same link into the Tools page (layer-dagster now carries an "Open the scheduler" link); PR #2892 MERGED — spec restructured so the two-engine framework (Engine 1 shadow / Engine 2 JIT) is the spine; spec verification doc written (/tmp/spec-verification.md) mapping every artifact to its spec row
🟡 Active: nothing in flight — all mergeable work landed, scratch worktrees cleaned, main is green
🔴 Blocked: W4 glass-break — platform/edge/dagster-route.yaml HTTPRoute so /dagster is reachable over the gateway hostname from outside the cluster (today the proxy targets the in-cluster Service, which works for any browser following the Backstage proxy, but a direct URL still hits 127.0.0.1)
⚪ Pending: founder review of the HTTPRoute; once merged, flip the proxy target from the Service URL to the gateway hostname
🔧 TOUCHES: backstage/app-config.yaml, backstage/packages/app/src/modules/home/Ops.tsx, bin/catalog-platform, backstage/platform/catalog-info.yaml (regenerated), docs/policy/agent-infra-safety-spec.md
🔀 OVERLAP: many estate sessions commit on main constantly; my changes are confined to the wt-dagster-bs branch and one merged spec branch (spec/two-engine-spine)
📍 State: https://github.com/chidionyema/idp/pull/2901 | origin/main at 04475d85
📍 METER: BLIND: estate_spend.py did not answer (TimeoutExpired) (crew#26)


## 2026-09-10T12:15:11Z · session a941270d · lane wt-edge
🔴 Blocked: nothing
🟡 Active: PR #2898 (Otto's door key) refreshed onto main and pushed — 09afa170; watching its CI, then it merges and Otto answers again
🟢 Done: found WHY Otto is silent, empirically not synthetically — otto-brain sidecar derives master key as sk-sha256(LITELLM_API_KEY)[:40] while the door presents the raw router key, so litellm falls through to virtual-key lookup, has no DB, and answers every /v1/chat/completions with 400 "No connected db." Liveliness stays 200 the whole time. Fix already existed on PR #2898 but was 10 commits behind the main that repaired 3 KeyError:'wait' tests, so it could never go green. Merged main in, 17 passed 3 skipped locally, pushed. Also built home 2: platform/lifeboat Cloudflare Worker (door + brain, 20/20 behaviour tests, no network touched) and bin/idp-otto-homes (grades 3 homes MEASURED_OK/FAIL/UNKNOWN)
⚪ Pending: bin/idp-otto-homes is 248 lines of shell and the estate shell standard refuses a new shell file over 100 lines — rewriting it in Python before it commits
🔧 TOUCHES: platform/lifeboat/ (new), bin/idp-otto-homes (new), docs/explanation/otto-survival-matrix.md, mkdocs.yml on feat/otto-door-at-the-edge; platform/otto-gateway/* on fix/otto-door-presents-a-key-the-lifeboat-can-read
🔀 OVERLAP: otto-gateway is touched by several sessions; my two branches are separate and neither is merged yet
📎 FACTS: homes graded 2026-09-10 — 1 cluster otto/healthz MEASURED_OK 200; 2 cloudflare lifeboat-llm MEASURED_FAIL (not deployed); 3 macbook tailnet:11434 MEASURED_OK 200. Groq free ceiling measured from its own header: 1000 req/day, 8000 tok/min
📍 State: https://github.com/chidionyema/idp/pull/2898

