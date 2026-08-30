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

## RESUME HERE — session a7b41022 (18:20Z)
Writing docs/reference/incidents/2026-08-29-langfuse-stalled-rollout.md (incident report + audit + trace) on branch docs/incident-langfuse-stalled-rollout in /private/tmp/claude-501/-Users-chidionyema-dev-code/a7b41022-3074-43c7-bb13-a1d7e07adff1/scratchpad/wtinc; monitor bvbqhb87n watches helm-retry 33266882531 then the login drill.

## RESUME HERE — session a7b41022 (18:50Z)
idp#856 incident report open. Building crew#645 CP1+CP2 on branch feat/crew645-capacity-vpa in /private/tmp/claude-501/-Users-chidionyema-dev-code/a7b41022-3074-43c7-bb13-a1d7e07adff1/scratchpad/wtcap: VPA (chart 0.11.0) recommender-only in platform/healing, Kyverno generate VPA Off per workload, cluster-state receipt carries vpa rows, bin/idp-capacity gate + capacity-gate.yml, fake budget test deleted.

## RESUME HERE — session a7b41022 (19:0xZ, science lane on the founder's word)
Founder: "i need all metrics exposed ... on backstage ... always ... numbers for everything we collect" + his Backstage Visibility Plan. Branch feat/crew645-cp5-metrics-on-backstage in $S/wtmet: Roadie prometheus plugin via core-compat-api convertLegacyPlugin, proxy /prometheus/api -> kps-prometheus.monitoring.svc:9090, skipMetricsLookup false, catalog-gen adds backstage.io/kubernetes-* and prometheus.io/* annotations to every cluster entity, PrometheusRule capacity.yaml (pod cpu/memory/restarts/request/peak recording rules + RequestBelowMeasuredPeak alert).

## RESUME HERE — session 14ed6c8b (21:2xZ, cluster fire)
Flux went 41 not-Ready (19:56) -> 7 (20:07); the cascade was the a1-spot node pool resizing, not
the image bot. Remaining reds: (1) chaos Kustomization — Chaos Mesh webhook vworkflow.kb.io
rejects podChaos.duration inside a Workflow template ("use Template#Deadline"); both
platform/chaos/langfuse-alert-drill-first-run.yaml (templates[2] fail-web) and
platform/chaos/langfuse-alert-drill.yaml carry `duration: 8m` beside `deadline: 540s`. Fixing on
branch fix/chaos-workflow-duration-forbidden in $S/chaosfix. (2) commerce, commerce-data,
event-bus: "no Ready condition yet", never reconciled. (3) tailscale operator Deployment Failed —
still no client_id/client_secret in the vault; guacamole blocked behind it.
Also open: iam-policy drift (live statement `manage secret-family` not in
platform/oci/policy/estate-operators.statements.json); catalogue-drift 5 Services with no
backstage.io/kubernetes-id; automerge-stuck idp#726 CONFLICTING.
Founder freeze holds: nothing merged, no cluster change. Founder's Mac OCI session token expired
(1h, not refreshable) — kubectl there needs a fresh browser sign-in.

## RESUME HERE — session 41fd24d8 (code-ad), 2026-08-29 22:2xZ
Founder: "lets prep for the crew migration to cloud" (crew#654; DR crew#300; portability crew#309). Freeze on: local prep only.
Worktree ~/dev/code/.wt-crew654, branch feat/crew654-cloud-session-bootstrap from origin/main: bin/idp-session-bootstrap,
.claude/settings.json SessionStart hook, tests/test_crew654_session_bootstrap_installs_the_guards_on_a_clean_machine.py.
Clean-home drill: 31/32 Mac hooks exit 0 in a fresh clone of claude-estate; prompt-ledger fails closed on the empty payload.
Next: commit locally; post plan + result on crew#654. No push until the freeze lifts.

## RESUME HERE — session a7b41022 (2026-08-30T08:1xZ, science lane)
Founder, direct, 08:0xZ: "first i need all cluster monitoring tools now ... top right of screen backstage ... all monitoring tools". Finding: alertmanager/prometheus never had a hostname (catalogue says "no public address yet"); grafana is off in the chart by design. Building: prospector-main listeners https-alertmanager/https-prometheus (worktree $S/wtedge); idp worktree $S/wtmon: platform/monitoring/httproute.yaml + namespace edge-attach label, catalogue Open links on founder-alerts/founder-metrics (group Watch), probe targets, login-drill OTHER_SURFACES rows, one pinning test. Then oke-check apply and the login drill.

## RESUME HERE — session a7b41022 (2026-08-30T08:14Z) crew#648 estate-state producer
Worktree $S/wt648 branch feat/crew648-estate-state-producer: bin/idp-estate-state-build + .github/workflows/estate-state.yml + sidecar in platform/mcp/estate-mcp.yaml + test. Next: write files, test, PR.

## RESUME HERE — session a7b41022 · 2026-08-30 09:0xZ
crew#648: idp#980 on branch feat/crew648-estate-state-producer (worktree $S/wt648, head 1dedfb68) — build red fixed (--main-sha repo=sha); checks running; merge on green (sidecar in platform/mcp/estate-mcp.yaml is the one cluster-touching file), then prove get_estate_state available:true stale:false.
crew#628 CP1: the CI half shipped in idp#874 (bin/idp-verify-claims, .github/workflows/verify-claims.yml); the missing half is "a hand-typed block fails pr-evidence" — building it in ~/.claude/scripts/pr-evidence.py on branch feat/crew628-cp1-hand-typed-evidence-fails (generated_evidence, run_exists, selftest_generated_block). Open idp PRs with typed fences: 980 977 973 925 802.
idp#977 / prospector#791: green, wait for the founder's APPROVE: 977 / APPROVE: 791.

## RESUME HERE (a7b41022 science, 2026-08-30T08:58:30Z)
- idp#980 MERGED 2ca4dd33; estate-state dispatched on main (task bn6rns6sk polls it with crew#709).
- crew#709 head d9ae942 (pyright fix); merge on green in a foreground call, then tick crew#628 CP1.
- then: prove get_estate_state available:true stale:false; tick crew#648.

## RESUME HERE (a7b41022 science, 2026-08-30T09:14:39Z)
- FIRE: idp#980 sidecar probes fail on extracted mtime (flux pull keeps archive mtime); estate-mcp rollout ProgressDeadlineExceeded, Flux mcp Kustomization Failed (run 33303322556). Fix: worktree wt648fix branch fix/crew648-refresh-probe-grades-the-refresh: touch /data/estate-state.json after a green pull + guard test. Push, PR, merge on green (fire), re-run diagnose, get_estate_state must be available:true.
