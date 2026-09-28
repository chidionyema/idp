# The Estate — a snapshot for the external consultant

**Date.** 2026-09-20 · **Author.** the crew, for the founder
**Status.** The estate is substantially larger than any single document describes. This is a
*way in*, not a complete inventory. Where a number is measured it carries the command that
produced it; where something is designed but not built it says **SPEC**; where it is running it
says **LIVE**.

---

## 0. Read this first

This is **not a company with some agents in it.** It is a **platform industry that has been built
by one person and an agent crew**, in public repos, on free-tier infrastructure, in roughly three
months, with a governance system that machine-checks its own truthfulness.

The correct comparison is not "another AI startup." The correct comparison is **an operating
system for autonomous software organisations** — and it is further along than the size of the team
would suggest, and less finished than the number of designs would suggest. Both of those facts
matter commercially.

**The headline asymmetry, stated plainly:** the estate's moat is not that it uses AI. It is that
it treats **agent authority, evidence and refusal as infrastructure primitives** — and everything
else in the estate is downstream of that one decision.

---

## 1. Shape and scale

| Layer | Reality | Evidence |
|---|---|---|
| Platform layers | **105 entries** under `platform/` — see the full inventory, `PLATFORM-LAYERS-FULL-INVENTORY.md` | `ls idp/platform/ \| wc -l` |
| Kubernetes manifests | **598** yaml files | `find idp/platform idp/clusters -name '*.yaml' \| wc -l` |
| Executable acceptance specs (BDD) | **354 `.feature` files** | `find idp -name '*.feature' \| wc -l` |
| Application code (TS/Go/Rust) | **501 source files** | `find idp -name '*.ts*' -o -name '*.go' -o -name '*.rs'` |
| Estate CLI tooling | **357 scripts** in `idp/bin/` | `ls idp/bin \| wc -l` |
| Architecture Decision Records | **48** | `ls idp/docs/decisions/*.md \| wc -l` |
| Design/ops documents | **~1,870** `.md` | `git ls-files '*.md' \| wc -l` |
| Numbered laws | **52** | `grep -rhoE 'LAW [0-9]+'` |
| Guards + policies | **163** files, **18** Rego | `ls claude-guards`, `find -name '*.rego'` |
| Repos with commits in 7 days | **25** of 49 | `git log -1 --format=%ct` |
| Merged PRs, estate-wide, 7 days | **964** | `gh search prs` |

**Do not read those as maturity.** §5 explains why. Read them as *surface area already paid for*.

---

## 2. What the platform actually is

```
FOUNDER SURFACE (voice-first, terminal-hostile — ADR 0022, 0008)
  Telegram · voice · portal buttons · "The Room" (spatial UI) · FleetView
  Constraint upstream of architecture: "business people do not use a command line"
        │
FRONT DOOR  — Gateway API (Traefik) + OIDC + Authelia + Keycloak realms-as-code
  Authorization is a property of the PATH, never of application code.  (ADR 0023)
  Zero-Regret Test: RCE inside Customer 0's agent cannot reach Customer 1's
  memory door, nor the Founder Control Plane.
        │
TENANCY      customers · two-hats tenant split · ns-fences (51 manifests)
IDENTITY     SPIRE/SPIFFE SVID mTLS · GitHub OIDC → OCI WIF · passkeys · JIT broker
SECRETS      Bitwarden = the human door · OCI Vault = the machine store
             SOPS+age · ESO · LAW 34: no vendor key on the Mac, ever
MODEL ROUTER LiteLLM — every model is a ROUTE, not a key. Anthropic · OpenAI ·
             DeepSeek · Kimi · MiniMax · local · Jev
             Hard severing spend breaker ($150/mo) — request_ceiling.py
MESSAGING    NATS JetStream behind a transactional outbox (ADR 0012)
DURABLE EXECUTION  Temporal
SCHEDULING   Dagster under launchd → Argo on OKE
AGENTS       Hermes · Architect · maestro · Otto · crew · agent-workforce ·
             agent-foundry · sovereign bus · ironcage research kernel
POLICY       Kyverno CEL at admission · Rego + shell gates in CI · 52 laws
EVIDENCE     Aevum — Ed25519 + ML-DSA-65 (post-quantum), COSE_Sign1,
             RFC 3161 timestamps, hash-chained, standalone verifier   (ADR 0028)
OBSERVABILITY SigNoz (ClickHouse) traces/metrics/logs + Langfuse (GenAI) + Superset
             Every routed call is traced BY the router, never by an SDK
DELIVERY     git is the only road. PR → multi-arch build → Trivy → cosign → GHCR
             → Flux image-automation → auto-merge on green → cluster
SUBSTRATE    Oracle OKE (Always Free, 4 OCPU) · Flux · Crossplane + OpenTofu ·
             Calico · Chaos Mesh · gVisor · Kyverno · Tailscale · k3d for local
SURVIVAL     survival-stack: whole control plane in one Cloudflare Worker;
             Lighthouse static page loads when every server is ash
```

### The decisions a consultant should attack

| ADR | Decision | The asymmetry |
|---|---|---|
| **0023** | Boundary enforced by **infrastructure, never application code** | Most agent platforms check permission *inside* the agent. Here that is structurally impossible. "The moment you write `if is_founder():` you accrue technical debt." |
| **0028** | **Aevum** replaces POPDD as evidence layer | Agent actions carry **third-party-verifiable, post-quantum** receipts with trusted timestamps. Almost everyone's "audit log" is symmetric HMAC or vendor-held rows — not evidence a third party can check |
| **0024** | Otto runs every tool, asks only for **what cannot be undone** | Principled reversibility gate, not a blanket confirm prompt |
| **0025** | **Agents hold no write on production**; Greenlane grows one row at a time | Removes the entire "the agent broke prod" failure class |
| **0006** | The platform answers for itself over **one** MCP server | One door; a second server is forbidden |
| **0029** | Definition of Done v3: five checks, **none self-graded**, three planes | Engineering cannot tick its own box |
| **0020** | An API key has a **lifecycle**, the client chooses every road on it | Multi-vendor key governance as a first-class model |
| **LAW 34** | One router key per identity, no vendor keys on the Mac | Credential blast radius is a design constant |

---

## 3. The systems under construction — this is the actual estate

This section is what a repo count completely misses. Each is a **specified system**, most with
executable acceptance criteria, several already running.

### 3.1 **The Battalion — Asymmetric Compute Leverage** (`docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md`)

The founder's naming directive: *"all options in one super intelligent super configurable
battalion — that's how we squash this problem forever."* Not a menu of tools: **one system where
every tier, axis and mechanism is a config cell with a live enable/disable toggle.**

- Hard **$150/month ceiling that SEVERS traffic**, not warns — because an 86.5M-token/hour
  incident proved warn-only is false security.
- Traceability matrix: every pasted source item maps to a REQ or an explicit OPEN/WONT. Coverage
  is a **mechanical grep check**, not a vibe.
- JIT/point-of-use, no 24h standing compute, no laptop dependency, no GPU.
- Grounded in arXiv receipts (TTS volume > size; BoN multi-verifier; verifier ceiling).

### 3.2 **The World Model — simulate before execute** (`docs/specs/2026-09-08-estate-world-model-simulate-before-execute.md`)

A founder-pasted design (Z3 solver + eBPF causal graph + dark factory + GPU) was **re-derived into
what the estate already owns**: the cluster's own admission chain run without persisting, plus
four graders already present.

`simulate_change()` → `{admission, laws, blast, network, placement, converge, verdict, expires_at}`
`execute_change(proposal_id, cluster_state_hash)` → refuses on hash mismatch or expiry.

**`UNKNOWN` is a real verdict and is not `SAFE`.** A probe that could not run **fails closed.**
Ten edge cases, each with the test that pins it. Rejected outright: a standing admin SA, any GPU
pool, manifests written to `/tmp`.

### 3.3 **estate-twin / FleetView — stop running the estate blind** (`docs/specs/2026-09-12-estate-twin-complete-spec.md`)

Founder verbatim: *"i need to capture everything one time, tired of running my whole estate
blind."*

The diagnosis is exact and it is the estate's central defect: **three inventories (457 / 194 / 211
rows) all report *declared* state as if it were *actual* state.** Measured blind spots:
**1,523 unmerged branches · 178 worktrees · 722+ files on unmerged branches absent from main ·
28 pods not ready · 5 secrets rotated but never reaching a consumer.**

> "A dead pod is declared nowhere. That is the whole failure: the estate's memory of itself is a
> memory of its intentions, not of its state."

FleetView is the live mind + board view; the twin is the mutable replica.

### 3.4 **The Room** (`docs/specs/2026-09-19-the-room-founders-spec.md`) — **the most commercially interesting artefact in the estate**

Founder's own words at the top: *"come on we had great ideas here."* A **model-agnostic,
cloud-first, voice-first** spatial interface. TypeScript, production-structured:
`core/ models/ routing/ voice/ memory/ failure/ cost/ fleet/ ui/` with `Result<T,E>` types — **no
exceptions in the hot path**; the router, voice layer and model layer never throw on user input.

### 3.5 **Voice conversation pipeline** (`docs/specs/2026-09-18-voice-conversation-pipeline.md`)

Real duplex conversation, not dictation. Silero VAD v5 → Faster-Whisper large-v3-turbo → streaming
LLM → Kokoro TTS, with **micro-clause chunking** (synthesise clause *n* while the LLM produces
*n+1*) and **barge-in** (~100ms of speech cancels the stream and flushes playback).
**Glass-to-glass budget: <400ms.**

### 3.6 **Ironcage — research kernel** (Rust, separate repo, **LIVE on Oracle Free Tier**)

MCTS + formal verification + immutable hash-chained ledger, **2 OCPU / 12 GB, zero GPU**.
5 crates, 18 tests passing, gVisor RuntimeClass, Kyverno-compliant. A real-time Sigma.js proof
graph UI. *"Production Ready"* per its own README. **This is the "asymmetric compute" thesis in
working code** — frontier-shaped capability on free hardware.

### 3.7 **survival-stack — the estate's own lifeboat** (Cloudflare Worker, **LIVE**)

Founder's requirement: the recovery path must not contain a machine that can die and take the
recovery tooling with it. Everything — Telegram bot, provider drivers, secrets, cron — in one
Worker. Includes a static **Lighthouse** page that loads *when every server is ash*, and RFC 6238
TOTP on WebCrypto with zero dependencies.

### 3.8 **The Conscience** (`idp/conscience/tenets.yaml`) — the founder's ethos as gradable rows

Founder, 2026-08-28: *"founder need ethos engrained always … a Conscience — an eternal, ambient,
active presence that keeps everyone and everything in the estate aligned."*

Each tenet carries the **command that measures it** and the value that is green. A tenet with no
command is **refused by the loader** ("a tenet is a row here or it is a wish"). `pr_rule` names the
Rego rule that judges a pull request against it; **a rule is born `warn` and earns `deny` at zero
false positives.**

Live tenets: *portable* (never locked in, `deny`) · *secure* (invisible security, `deny`) ·
*enterprise* (baseline is the highest standard).

### 3.9 Other live systems already named in the estate

| System | What it does |
|---|---|
| **epistemic-fabric** | Evidence grading across the estate |
| **via-negativa** | RCA · red-team promoter · proxy — the adversarial loop |
| **otto-gateway / otto-golden** | The tool-executing agent with a golden-path sandbox |
| **orchestration / intent-* ** | Capability intents → **deterministic estate compiler** |
| **forge** | Experiment tracker replaced by a rig that writes research records + Brier-scored forecasts |
| **eval / rule-coverage** | Judge-drift detection; every rule proves it refuses its bad fixture |
| **human-vault / human-vault-bridge** | The one door where a human pastes a secret |
| **jit / executor** | Short-lived grants; the credential-less below-Kubernetes executor |
| **lifeboat / drills** | 13 rebuild-and-restore drills, incl. `oke-rebuild`, `key-escrow-restore`, `github-gone` |
| **acg** | Asymmetric Compute Grid — OpenAI-compatible inference gateway |
| **agent-foundry** | Ordered goal → army of specialised micro-node jobs over NATS |
| **customer-identity** | Keycloak realm-as-code, reconciler-owned |

---

## 4. The governance model (why this is not a pile of scripts)

The estate has a **constitution**, and it is enforced by machines:

- **52 numbered laws**, each with a must-fail and a must-pass fixture. *"A rule that has no gate is
  not a rule here."*
- **Every PR that changes code also changes an executable spec** (a `.feature`, a test, or a
  generator) — or `spec-gate` refuses it. **354 feature files** are that covenant.
- **No PR is self-graded.** `crew verify` refuses the role that posted the evidence.
- **LAW 22:** a screenshot on every PR, committed under `docs/evidence/pr-<n>/`, so it leaves in the
  git bundle with the code.
- **LAW 23 (the friction default):** if two paths solve the problem and one is >3× the work, take
  the smaller one — *unless* it loses data, opens a security hole, or breaks the crew loop.
- **LAW 44:** a law without a protocol is a wish. A horizon with no experiment is a wish.
- **EMPIRICAL PROOF RULE:** never declare WORKING from synthetic probes, CI gates or HTTP 200.
  A real production log line or it is not proven.
- **Reversibility gate:** mutation delivery + reversibility + typed multidomain mutation ledger.

**This governance layer is itself the productisable asset.** It is what makes an agent fleet
auditable rather than merely impressive.

---

## 5. The honest weakness register

Not hedged. These are measured, and a consultant will find them in an afternoon.

| # | Weakness | Measured |
|---|---|---|
| **W1** | **The estate is a design factory whose build rate lags badly.** Founder's own spec: *"every single line of code production ready"* for The Room "is 20,000+ lines" — and what follows is the core, not the whole | 675 planned checkpoints, **670 with no date**, **0 blocking, 0 active**; 138 issues |
| **W2** | **Declared ≠ actual is the estate's core defect, and it is self-diagnosed** | 3 inventories all reporting intentions as state; 1,523 unmerged branches; 178 worktrees; 28 pods not ready |
| **W3** | **Standardisation is declared but not adopted** — three unstandardised front ends exist against a stated one-platform standard | `docs/SHOWCASE.md` standards table: most rows "to adopt"/"migrating" |
| **W4** | **Identity is incomplete** | SPIFFE: **1 proof pod, 0 catalog services, 0 mTLS calls**; `static-secret-gate = 25`; passkeys unverified |
| **W5** | **Drills are stale** — 12 drill entities GAP at **age 390.7h**, far past bar | `docs/SHOWCASE.md` gaps table |
| **W6** | **Guards are unobserved** — 16 guard entities BLIND: `last-status absent; never observed`. The guard may be fine; **nothing proves it ever ran** | `docs/SHOWCASE.md` BLIND table |
| **W7** | **Cluster degraded** | **46 of 86** Flux Kustomizations not ready; **2 of 3** nodes Ready |
| **W8** | **Delivery quality is bimodal** | change-failure rate: idp **0.4%** vs crew **23.5%**; MTTR 10.28h (crew), idp unmeasured |
| **W9** | **Measurement ≫ grading.** Massive sensing, near-zero scoring | 15 forecasts, **0 scored**; `velocity.jsonl` stopped at 8 rows; warehouse 0 dbt models |
| **W10** | **Revenue has never been measured** | `revenue.jsonl`: `measured: false` — token not set |
| **W11** | **Founder attention is the binding constraint, and it is measured but not attributed** | 197 msgs/day, 2.0% complaint rate; no per-agent attribution |
| **W12** | **Founder visibility is an open P1, in the founder's own words** | crew#718: *"The founder cannot open five of the eight monitoring tools, and nothing human reads any of them"* |
| **W13** | **Open work never falls** | crew#526; **30 open P1s** |
| **W14** | **Bus factor 1** | Every law, guard, ADR and credential root traces to one person |
| **W15** | **Our one predictive model barely beats noise** | foresight holdout **0.602** vs base **0.593**; Brier 0.246; red-precision **0.512** |
| **W16** | **Adoption outruns completion** | 25 repos touched in 7 days; elite-grade **25 GAP, 16 BLIND** of 434 |
| **W17** | **Some live systems carry "Production Ready ✅" self-assertions** (Ironcage) that have **not** been graded by the estate's own Definition of Done | Ironcage README vs ADR 0029 |

**W17 is worth the consultant's attention specifically:** the estate's own law says nothing is
"done" without five independent checks — and at least one system in the portfolio asserts
production readiness in its README instead. That is the estate's most common failure mode in
miniature.

---

## 6. Where the asymmetric value sits

The estate has already paid for the hard, uncopyable parts. The question is not capability — it is
**conversion**. Ranked by (asymmetry already in hand) × (time to a paid result):

| Rank | Wedge | The moat already standing | What "captured" looks like |
|---|---|---|---|
| **1** | **Auditable autonomy for buyers who cannot accept a black box** | Aevum third-party-verifiable post-quantum receipts · infra-enforced tenancy · agents hold no prod write · **every routed call traced by the router** | A buyer's security engineer independently verifies one agent action with **our** verifier, sharing **no code** with our runtime. If that works, the SSO / audit / residency / tenancy objections all collapse at once |
| **2** | **Governance-as-a-product: the machine-checked constitution** | 52 laws with fixtures · spec-gate · 354 feature files · no-self-grading · Conscience rows | Sell the *operating model* — how to run an agent organisation that cannot lie to you. Almost nobody has this; almost everybody will need it |
| **3** | **Frontier capability on free-tier hardware** | Ironcage: MCTS + formal verification + hash-chained ledger on **2 OCPU, zero GPU** · £0-infra estate · Aevum | Cost structure incumbents cannot match without re-architecting |
| **4** | **Voice-first, spatial, terminal-free control** | The Room (model-agnostic, `Result`-typed) · <400ms duplex voice with barge-in · ADR 0022 | The only demo a non-technical board understands in 30 seconds |
| **5** | **Simulate-before-execute as a trust product** | World model on the cluster's real admission chain; `UNKNOWN` fails closed | "We can show you what a change does *before* it happens, or refuse to guess." Directly answers enterprise change-management |
| **6** | **Sovereign / air-gap-optional deployment** | Self-hosted everything; survival-stack; portability drill exists | Buyers who legally cannot use cloud |
| **7** | **Survivability** | survival-stack in one Worker; Lighthouse page; 13 drills | Uptime story that does not depend on any machine |

**Explicit anti-goal:** do **not** add a tenth observability plane. W12 says five of eight already
go unopened. The failure mode is more sensing, not less; the fix is **fusion and closure**.

---

## 7. What we want the consultant to answer

1. **Which of §6 is a moat and which is merely unusual?** Our own suspicion: 1, 2 and 3 are
   durable; 5 and 7 are features; 6 is a segment, not a product. We want that challenged.
2. **Is wedge 1 real?** Does third-party-verifiable post-quantum agent receipting clear a
   regulated buyer's *actual* procurement — or is it a beautiful answer to a problem they do not
   have?
3. **Should the estate narrow?** 95 platform layers and 30 open P1s against one person's attention.
   Which **five** things survive? What gets deleted?
4. **Why does adoption outrun completion here?** W1, W3, W16 persist across many agents and many
   months. Is "closure" a discipline problem, an incentive problem, or an architecture problem?
5. **Is the governance layer sellable on its own** (wedge 2), separate from the platform?
6. **What is the shortest path from §6 to a paid invoice?** Not the best product — the *shortest*.
7. **Does the "everything is a config toggle" Battalion directive** (3.1) risk building a machine
   nobody can operate, given W12?

---

## 8. Regenerating this document

```bash
# estate map + knowledge graph
cat crew/STATE.md
growmos --root ~/Documents/code/estate-graph context --brief

# the inventory that grades the estate
cat idp/docs/SHOWCASE.md            # 434 entities: ELITE / GAP / BLIND
cat idp/docs/NEXT.md                # 675 planned checkpoints

# the truth map
python3 crew/science/datamap.py --check

# delivery + measurability
tail -3 crew/science/dora.jsonl
tail -5 crew/science/predictions.jsonl
tail -2 crew/science/revenue.jsonl

# surface area
ls idp/platform/ | wc -l
find idp -name '*.feature' | wc -l
ls idp/docs/decisions/*.md | wc -l

# what is actually live
kubectl get kustomizations -A | grep -c False
```

**Rule for readers:** if a number here cannot be reproduced by a command in this section, treat it
as stale and say so. That rule is the estate's own, and this document is held to it.

---

## 9. The one-sentence version

**One person and an agent crew have built a self-hosting, provider-agnostic, voice-first platform
where agent authority is infrastructure rather than code, every action can be independently
verified post-quantum, and the governing rules are machine-checked against their own fixtures — and
the strategic problem is not capability, it is that the estate builds far faster than one person
can close, grade and sell.**

*Prepared by the crew for the founder. Every claim cites a command or is marked SPEC / NOT
MEASURED. Corrections are the point — the previous draft of this document described the estate with
a repo count and was correctly rejected for it.*
