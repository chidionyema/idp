# Incident report: the Calico cutover turned the fences on, and every public site answered 504

Date: 2026-09-06. Board: crew#102. Founder record that named the cause:
`~/.claude/docs/founder/2026-09-06T2037Z-the-gateway-timeout-504-confirms-that-calico-is-fac00c2b.md`.
Later founder record from the same evening, cited by the lockdown follow-up:
`~/.claude/docs/founder/2026-09-06T2057Z-he-unverified-tags-appear-because-the-bot-s-5d38fa3f.md`.

Every line below was read from the cluster, traefik's access log, a pod's own log or GitHub in
the hour it was written. Cluster reads went through `bin/idp-kube`; no agent wrote to the
cluster by hand (the lockdown refuses it), every apply went through git or the oke-check
break-glass workflow.

## What the founder saw

mumchimp.com, www, api.mumchimp.com, cyrus and the catalogue all answered `Gateway Timeout`.
His read, verbatim from the record above: the 504 confirms that Calico is enforcing, punch the
hole in `platform/ns-fences/allowances.yaml`, regenerate, verify in traefik's log and with
`curl -Iv https://mumchimp.com/`.

## Timeline (UTC)

| When | What | Receipt |
|------|------|---------|
| earlier 09-06 | Raw operatorless Calico v3.32.2 lands in kube-system next to flannel (#2112, #2113). New pods get Calico addresses (10.244.117.0/24, 10.244.3.0/24) and, for the first time, a NetworkPolicy is enforced on them. Pods still on flannel addresses are unenforced. | `kubectl get pods -A -o wide`: traefik on 10.244.2.x/10.244.1.x, store-web on 10.244.3.14 |
| 20:37 | Founder names the cause: the fences were a default-deny floor with holes nobody had exercised. | founder record above |
| 20:40 | #2115 (84aa96dc) declares `ingress_from: [edge]` for prospector and cyrus; Flux applies it. | traefik: `2026-09-06T20:40:32Z mumchimp.com / 200 10.244.3.14:3000 origin_ms=10517` |
| 20:4x | Pages answer 200 but take 10.5 s: store-web cannot reach store-api inside its own namespace. | `wget` from the store-web pod: `download timed out`; Calico drop counter `[18:1080] -A cali-tw-cali302c84c5405 ... "End of tier default. Drop"` |
| 21:0x | #2119 (27e7b959, merged c638d5a7): every namespace gets `allow-same-namespace`; edge gets `ingress_public: [8000, 8443]`; the oke-check `ns-fences` playbook applies it live (run 34058851667, 39 policies). | `kubectl get networkpolicy -n prospector`: `allow-same-namespace` present; `wget` store-web to store-api answers in 0.00 s |
| 21:17 | Still 10.5 s. store-web fetches its own public name. `allow-internet-egress` on 443 (also in c638d5a7) is live and does not help: the load balancer address is a Service, kube-proxy rewrites the destination to the traefik pod before Calico judges it, and a pod address is private. | store-web log: `ConnectTimeoutError api.mumchimp.com:443 timeout 10000ms`, 3 in two minutes; traefik `21:17:40Z 200 origin_ms=10529` |
| 21:3x | #2128 declares `egress: [edge]` for prospector. Proof line to be added after Flux applies: a traefik line for `mumchimp.com /` with origin_ms under 1000 and no ConnectTimeoutError in store-web. | #2128 |

## Root cause

The namespace fences were written and merged as a default-deny floor plus declared holes at a
time when the CNI enforced nothing. No hole was ever exercised, so `allowances.yaml` described
the estate's east-west traffic as someone imagined it, not as it runs: no ingress to the served
products from the gateway, no pod-to-pod traffic inside a namespace, no public ingress to the
gateway's own listeners, and no path for a storefront that calls itself by its public name. The
Calico cutover switched every one of those omissions on at once.

Class of mistake: a guard merged without a both-ways proof in production (LAW 15, LAW 45). The
gate `bin/ns-fence-gate platform` proves the files declare a fence; nothing proved a declared
fence let the real traffic through.

## What changed so it cannot repeat

- The generator emits `allow-same-namespace` for every namespace and `allow-public-ingress`
  from `ingress_public`, and `tests/test_incident_crew102_calico_cutover_blacked_out_every_public_site.py`
  holds it to the three flows the outage lacked.
- `bin/idp-oke-break-glass ns-fences` applies the fences from a branch through the oke-check
  workflow, so the next fence change can be proved live before it is merged.
- The remaining gap, on purpose: nothing yet reads Calico's deny counters after a fence change.
  `platform/calico`'s README and the `calico_denyflow_gate` row in AGENTS.md hold that work.

## Side findings from the same evening

- The founder's own OCI user was refused by `flux-only-writes` on `kubectl annotate kustomization
  cyrus`. The 2026-09-05 exception never rendered: the edge row had no `postBuild.substituteFrom`,
  so the live ClusterPolicy carried the literal `${ESTATE_FOUNDER_USER}`. Fixed and widened in
  #2127.
- The hermes-agent bot tags its GitHub statements "unverified" because its terminal tool strips
  `GITHUB_TOKEN` and `GH_TOKEN` from the shell it gives the model
  (`tools/environments/local.py`, blocklist), and `gh` has no stored login under `/data`. Its
  process holds the minted token and `gh auth status` inside the pod logs in as
  `estate-agents[bot]` when given it. The fix is a `gh auth login --with-token` in the image's
  entrypoint; not landed in this session.
