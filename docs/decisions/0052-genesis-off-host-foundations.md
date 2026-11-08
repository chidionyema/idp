# ADR 0052 — Genesis off-host foundations; IDP history is science evidence

Date: 2026-11-08. Status: FOUNDER DECISION, SOURCE CANDIDATE ONLY pending governed review/release.
Owners: IDP #7794 admission, #7771 FLOW, #7452 FCR, #7372 Science, #7334 infra; Argon #47/#62 Genesis.
Supersedes: ADR 0004 OKE target, ADR 0034 laptop-placement rung and assumed cluster. Preserves ADR 0034 **ZERO UNAPPROVED INCREMENTAL COST**.

## Constitutional invariants

1. NO LOCAL INFRASTRUCTURE. Laptop, desktop, homelab, localhost, local tunnel, local launchd/cron, sole local disk, operator GUI, local NATS/Temporal/memory/router/worker and founder-held processes are NEVER production authority, required executor, primary, fallback or recovery home. Local editing and disposable tests may be non-authoritative clients only. Demonstrate operation and recovery with the founder's devices powered off.
2. NO OKE. OCI OKE entitlement is gone; all historic OKE manifests, bootstrap scripts, tests, ADRs, PRs and incidents are ARCHAEOLOGY, not recommended deployment action. Agent context must never turn their presence into active instructions.
3. NO NEW PAID INFRA without separate exact-resource authenticated founder approval. Source-listed free tiers do not establish real quota, physical capacity, service durability or cost-free usage. Unavailable resource means CAPACITY_UNAVAILABLE, not speculative provisioning, laptop fallback, hidden card or invented uptime.
4. NO FALSE TOPOLOGY. Current OCI E2.1.Micro is a tiny router-only resource, not stateful estate capacity; A1/k3s is candidate architecture until live A1 allocation and independent running node/restore observations. Three surviving AD-1 50GB data volumes are preservation only until independent off-provider backup. Do not destroy the router host to gamble on A1.
5. ONE ARCHITECTURE. Use existing cloud GitHub Actions as bounded batch and external custody, Cloudflare Free for short stateless edge operations, *existing proven remote free capacity* for durable services. No second bus, ledger, scheduler, memory or policy engine. Remote operations must survive a laptop outage AND have independently verified recovery custody.
6. NO ABSOLUTE CLAIMS. Engineering can prevent known failure classes through negative tests, independent runtime evidence and FCR adoption. No system can prove no conceivable incident can ever recur; novel faults get BLIND/UNKNOWN and bounded recovery.

## Post-OKE decision ladder

- BATCH -> existing off-host GitHub Actions within independently verified free quota, checkpoints and artifacts durably kept off runner.
- STATELESS_EDGE -> existing Cloudflare Free Workers/Pages within measured quota, no fake backend claims.
- STATELESS_ROUTER -> existing OCI E2 recovery host ONLY with measured capacity and an actual authenticated LLM transaction.
- STATEFUL_CORE -> OCI A1 or other off-host **already allocated** free resource, only when independently verified adequate, backed up and capable of durable recovery; never assume k3s exists because code describes it.
- NO FIT -> CAPACITY_UNAVAILABLE and assigned remote capacity/architecture recovery task. No local, no OKE, no unauthorized paid resources.

## Existing contradictions, ownership and migration

Main AGENTS.md, ADR 0034, bin/estate-context-compile local fallback, bin/idp-session-bootstrap local bootstrap and false applied ACK, bin/idp-admission-policies OKE source, historic Science launchd scheduler and Argon seeded dashboard data contain paths back into known failure classes. These are explicit RETIREMENT WORK ORDERS under their existing issue owners, not proof of already deployed change. Keep historic files as evidence, but stop exporting them as active instructions in #7794 context. Existing trusted gates/claims/reviews still govern remediation; no new mandatory global hold without automated remediation.

## Genesis science loop and productisation

Record original IDP incident/PR/run with date and negative evidence -> stable FCR failure class -> preregister hypothesis, null, baseline and falsifier in EXISTING Science (#7372) -> safe OFF-HOST experiment -> independent replication -> guarded permanent correction -> cross-provider agent memory/admission regression -> operational FLOW yield -> Founder Surface -> tenant-isolated, supported product -> verified revenue. Count measured prevented recurrence, fewer founder interruptions, recovered time, independently successful customer deployment, actual revenue and cost; not PR count or synthetic congruence.

The Genesis science lane exists to derive asymmetric advantage from expensive lived engineering mistakes; its prior OKE carnage fixtures are *test inputs* and must not be mistaken for live telemetry. A recurrence of a known class is PREVENTION_GAP, not a new unlimited research activity.

## Machine-readable policy, single source

<!-- GENESIS_OFFHOST_POLICY_BEGIN -->
{
  "version": "genesis.offhost.v1",
  "incremental_monthly_gbp_ceiling": 0,
  "retired": ["oke", "local", "laptop", "homelab", "localhost", "paid"],
  "placement_roles": {
    "github_actions": ["batch"],
    "cloudflare_free": ["stateless_edge"],
    "oci_e2_existing": ["stateless_router"],
    "oci_a1_existing": ["stateful_core"],
    "other_remote_free": ["batch", "stateless_edge", "stateless_router", "stateful_core"]
  }
}
<!-- GENESIS_OFFHOST_POLICY_END -->

## Acceptance

- Fresh agent one-hop context contains policy SHA, source vs runtime, verified physical free capacity and remote durable custody, forbidden local/OKE/paid paths, current evidence age and next safe action.
- A developer/agent may never turn its self-reported observation into permission. Source policy preflight only emits REFUSED or CANDIDATE_NEEDS_TRUSTED_VERIFICATION. Existing authenticated admission/review/DoF action doors independently verify real provider and spender evidence.
- Negative tests deny OKE, local infra, paid infra, source-only A1, E2 stateful core, Cloudflare database, GitHub Actions always-on, missing quota proof, lost remote custody, stale evidence and self-approved effects.
- Shut down founder laptop/Tailscale and kill an off-host worker during a real instruction: durable continuation, effect dedupe, independent off-host monitoring, source SHA and founder readback must survive.
- Science reenacts an IDP incident off-host, independently proves the corrected class cannot replay through the admitted route, and later measures real effect.
- External commercial customer can deploy with zero founder-device ties and receives tenant isolation, documented upgrade/rollback, support, licensed dependencies and bounded costs.

Until separately governed release and independent deployed readback, this ADR is a candidate; the GitHub issue #7794 is the current explicit founder correction. Existing retired paths are not technically removed by documentation alone.
