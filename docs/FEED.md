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


## 2026-09-10T12:18:56Z · session 01a08284 · lane wt-dagster-bs
🟢 Done: PR #2901 MERGED at 11:38:25Z (Tools page now shows layer-dagster with "Open the scheduler" link to /dagster); spec verification doc written (/tmp/spec-verification.md, 63 tests across 11 spec rows pass on clean main); implications doc written (/tmp/implications.md, three-part: operator / platform / business)
🟡 Active: nothing in flight — all mergeable work landed, waiting on founder
🔴 Blocked: W4 glass-break — platform/edge/dagster-route.yaml HTTPRoute (today the /dagster proxy targets the in-cluster Service, which works for any browser following the Backstage proxy but a direct URL still hits 127.0.0.1)
⚪ Pending: founder decision on the HTTPRoute; once merged, flip the proxy target to the gateway hostname; and the three spec rows still unmet: W3.4 (live 3 a.m. demo), W0.5 (sign the proof), W0.6 (platform-owned assertions)
🔧 TOUCHES: no further changes planned unless founder directs; scratch worktrees cleaned, on feat/otto-three-homes
🔀 OVERLAP: estate sessions commit on main continuously; I watch the dagster PRs and the spec/two-engine-spine merge (#2892) and the dagster integration
📎 FACTS: the estate feed-guard hooks (Stop/SessionStart/UserPromptSubmit) are wired in ~/.claude/settings.json for Claude Code only — pi sessions get no auto-fire, so I post manually; user asked me to "force the issue" because too much work was getting lost
📍 State: https://github.com/chidionyema/idp/pull/2901 | origin/main at 04475d85


## 2026-09-10T12:26:52Z · session a941270d · lane wt-edge
🟢 Done: PR #2909 opened — home 2 (Cloudflare Worker, door + brain, 20 tests), bin/idp-otto-homes (grades all 3 homes), docs/explanation/otto-survival-matrix.md (3 homes x 16 lanes, and why a fallback chain is the wrong primitive)
🟢 Done: found the one remaining red on PR #2898 — KeyError 'entry', unrelated to Otto's door: a MiniMax registry row deliberately has no estate copy to seed from (vault copies measured revoked, 401 invalid api key 2049). Test now grades entry-less rows as "no seed", pushed 9d9382d7
🟡 Active: watching PR #2898 CI on 9d9382d7 — the one that makes Otto answer again (otto-brain derives sk-sha256(LITELLM_API_KEY)[:40] as master key while the door presents the raw key, so every chat completion 400s "No connected db." while /health/liveliness stays 200)
⚪ Pending: home 2 not deployed (Workers Scripts:Edit scope unconfirmed); headroom lane selection designed not written; NIM/Cerebras/Mistral/Cohere/HF researched not minted; moving the Telegram webhook needs the founder's own words
📍 State: home 1 MEASURED_OK, home 3 MEASURED_OK at its tailnet address (403 at MagicDNS — Ollama refuses an unknown Host), home 2 MEASURED_FAIL not deployed
🔧 TOUCHES: platform/lifeboat, bin/idp-otto-homes, docs/explanation/otto-survival-matrix.md, tests/test_the_human_vault_bridge_addresses_every_key_by_name.py
🔀 OVERLAP: none
📍 METER: 2026-09-10 $78.53 785 req $0.100/req transport 81% | opus-5 100%, haiku-4-5 0% (crew#26)


## 2026-09-10T12:29:28Z · session a941270d · lane wt-edge
🟡 Active: PR #2898 (Otto's door key) head 9d9382d7 — every gate green so far, bdd-suites + offline-gate running; this ends Otto's silence. PR #2909 (the matrix) head 69ea9327, CI in flight, nothing red.
🟢 Done: the last red on #2898 was KeyError 'entry', not Otto — a MiniMax registry row deliberately names no estate copy to seed from because those copies were measured revoked at the vendor (401, invalid api key 2049); seeding would push a dead key over the founder's live one.
🟢 Done: home 2 written (Cloudflare Worker, door + brain, 20 tests), bin/idp-otto-homes grades all three homes, docs/explanation/otto-survival-matrix.md holds the three-homes-by-sixteen-lanes design.
⚪ Pending: deploy home 2 (Workers Scripts:Edit scope unconfirmed, likely blocker); write headroom-based lane selection (designed, not built — a chain drains Groq's measured 1,000/day each afternoon); mint NIM/Cerebras/GitHub Models/Mistral/Cohere/HF; prove Otto from pod logs once #2898 lands.
🔴 Blocked: moving the Telegram webhook to home 2. Telegram allows exactly one webhook URL per bot, so this MOVES Otto's door — a production change needing the founder's own plain words, never a menu.
📍 State: home 1 MEASURED_OK, home 3 MEASURED_OK at its tailnet address, home 2 MEASURED_FAIL not deployed. Founder 2026-09-10: the matrix "nees to be oprational fully", "nission critical", "guanatee eternal life nnow".
📎 FACTS: platform/otto-gateway/deployment.yaml:320 sets OTTO_BRAIN_KEY=sk-$(sha256(LITELLM_API_KEY))[:40] while the door presents the raw key; three-homes.yaml:139 reads it as master_key. Mismatch -> virtual-key lookup -> no DB in the sidecar -> 400 "No connected db." while /health/liveliness stays 200.
🔧 TOUCHES: platform/lifeboat, bin/idp-otto-homes, docs/explanation/otto-survival-matrix.md, platform/otto-gateway/deployment.yaml, platform/vendors/consoles.yaml
🔀 OVERLAP: none


## 2026-09-10T12:43:08Z · session a941270d · lane wt-edge
🟢 Done (the Calico/cross-node repair, posted because the founder asked for it): the week-long cross-node failure was NOT a Calico defect. Flannel was parked as a DaemonSet but its SNAT rules stayed in iptables and kept rewriting the source address of cross-node packets, so Calico saw a source it did not recognise and defaulted to DROP. Local-node policy worked the whole time, which is why it looked like a policy bug.
🟢 Done: measured before touching a rule (break-glass, read-only): on node .197 cali-FORWARD sits at position 1 with 137M packets / 200G bytes, KUBE-FORWARD at 3 with 1250M / 1939G, FLANNEL-FWD at 6 with 7651K / 752M, and the final mark-match ACCEPT at 7 with 0/0. So Calico was upstream of kube-proxy and of Flannel, nothing was short-circuiting, and the ordering was never the fault.
🟢 Done: the leftover Flannel SNAT rules were cleaned out by hand, calico-node was rolling-restarted (which also activated the TCP checksum-offload fix), and cross-node connectivity came back. Proved with a drill workload that spreads pods across nodes and grades pod-to-pod reach and peer discovery, plus a cross-node canary — both passed. This is what the three homes needed underneath them.
🟡 Active: PR #2911 (the estate mints its own Cloudflare Workers token, so home 2 needs no dashboard) and the headroom chooser, now written: 27 tests green, up from 20.
⚪ Pending: the estate-bootstrap button is still BLIND on vault in its preflight job — "not reachable as DEFAULT" — so the live cloudflare mint is skipped as a failed dependency. Fixing that next; it is the last thing between the design and home 2 being live.
📍 State: PR #2909 (the matrix) MERGED to main. Otto's door fix #2898 head 9d9382d7 waiting on CI. Home 2 still MEASURED_FAIL until the Workers token exists.
📎 FACTS: estate-bootstrap.yml preflight had CMD="bin/x --preflight" then "$CMD", which asks for a file with a space in its name — every scope of that button has exited 127 since it was written, and the live job below it was always skipped. Fixed with an array; measured on run 34477655011.
🔧 TOUCHES: platform/lifeboat/src/homes.js, platform/lifeboat/test/lifeboat.test.mjs, bin/idp-bootstrap-cloudflare, .github/workflows/estate-bootstrap.yml
🔀 OVERLAP: none

