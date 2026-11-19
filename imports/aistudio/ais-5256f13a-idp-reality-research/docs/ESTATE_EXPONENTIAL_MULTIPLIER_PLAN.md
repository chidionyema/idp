# IDP ESTATE EXPONENTIAL MULTIPLIER MASTER PLAN & DEVIL’S BARGAIN KERNEL

> **Target Repository**: `https://github.com/chidionyema/idp` (`main` @ `fafb505`, PRs `#7324`–`#7515`)
> **Status**: Ready for Greenlane Submission (`lane/exponential-multiplier-kernel`) & Direct MiniMax / Gemini 3.5 Flash Execution
> **Epistemic Tags**: `[M]` Measured in repo · `[R]` Reported in audit/spec · `[K]` Executable Kernel in `/src/lanes/operationalKernels.ts`

---

## 1. Forensic Synthesis of Past 2 Weeks of Work (`PR #7387` – `PR #7515`)

| Cluster | PR Range & Key Commits | What Was Measured `[M]` | The Missing Multiplier Arrow |
| :--- | :--- | :--- | :--- |
| **1. Otto Front Door, 31-Wish Parity & OCI AD-2 Lifeboat** | `#7515` (`fafb505`), `#7514` (`0892a99`), `#7508` (`f4ef5db`), `#7488`, `#7456`, `#7393`, `#7387` | After OKE deletion (`#7393`, container-engine limit=0), Always-Free OCI AD-2 `VM.Standard.E2.1.Micro` lifeboat router + Cloudflare Tunnel stood up (`#7508`). Bounded SLA tick across slow fetches (`#7515`). 31 founder wishes mapped across Families A–F (`#7514`). | Script automated re-attachment of the 3 preserved AD-1 CSI volumes (250GB: `postgres`, `nats`, `openclaw`) and unify Mac-local Otto with Telegram/Cluster Otto via one governed door. |
| **2. Fleet Comms, Voice-First 2100 Door & Founder Intake Store** | `#7512` (`2f22ef6`), `#7509` (`1857924`), `#7507` (`a2658ab`), `#7500` (`a97704b`), `#7496`, `#7401` | NATS JetStream `ESTATE_FLEET` single envelope live on `:4222`; `bin/estate-fleet-voice` `hear()`/`say()` wired; atomic `inbox --pipe` fixed `ack_wait=60s` voice replay bug (`F1`). `bin/estate-founder-intake` records executable directives with `find_repeat` deduplication. | Wire `estate-dispatchd` launchd daemon (`#7505`) so a directive in `estate-founder-intake` triggers an unattended `idp-agent-orchestrator` run on MiniMax via `exec-daemon` and speaks back the lane verdict. |
| **3. One-Pass Discovery Oracle, Tenets `T1–T9` & Conformance `R0–R8`** | `#7506` (`c89e0a6`), `#7499` (`0952ba6`), `#7492` (`c05a289`), `#7484`, `#7473` | Tenets `T1–T9` (`docs/specs/2026-10-30-estate-tenets.md`) separate observation states (`ABSENT \| READER_UNAVAILABLE \| ACCESS_DENIED \| STALE \| UNMEASURABLE`) from evaluation verdicts (`PASS \| FAIL \| BLIND \| ABSTAIN`). `bin/schema-conformance` enforces `R0–R8`. `#7492` enforces "a receipt keyword is not proof". | Close the **362 installed vs 110 tracked** intent gap (252 untracked laptop tools) via automated `R0–R8` manifest harvesting and enforce pre-flight `HEAD` staleness check (`F2`). |
| **4. Agent League, Model Economics (`ADR 0038`) & Spend Floor (`#7248`)** | `#7513` (`5371c22`), `#7511`, `#7505` (`63deca6`), `#7455`, `#7248` | `consult.gemini` defaulted to `gemini-3.5-flash` (`reasoning_effort=low`) sharing `door_s` bound (`#7513`). Harness assessment (`#7505`) ranked pieces by what *runs*. Spend audit (`#7248`) measured `$29.36/day` vs `$3.00/day` TOML cap (`minimax_m27` 71–78% of spend; `session: "-"` caller blindness). | Enforce router hooks `R0–R4` (`session_id` required, prompt-cache breakpoints, per-session USD ceiling) + export Forge's 97.8% CI-flake classifier to `<2ms` `[A] GATE` pre-refusal. |

---

## 2. Founder Psychology, Wellbeing & "The Devil's Bargain" (5 Immutable Laws)

1. **`LAW-01` — Exceed the Very Best for Pennies (`$0–$150/mo` Hard Cap)**:
   - **Founder Psyche**: The founder does not pay for cloud bloat unless funded. Every subsystem must beat commercial state-of-the-art while living on the **ADR 0034 Free-Tier Placement Ladder** (Rung 1: Laptop launchd + SQLite/DuckDB; Rung 2: OCI Always-Free AD-2 Micro + KEDA scale-to-zero; Rung 3: Modal/Kaggle free GPU bursts) and respecting `[budget.usd_per_day] litellm = 3.00`.
2. **`LAW-02` — Built $\neq$ Operating; A Receipt Keyword Is Not Proof (`#7492`)**:
   - **Founder Psyche**: Broken promises and narrator agents destroy founder trust asymmetrically. "Done" means operating on `/fleet` with a re-executable behavioral receipt (`~/.estate/facts.jsonl` carrying `instrument_cmd`, `measured_at`, `valid_for_s`, `artifact_sha256`) and passing the **NSVEE 5-Property Contract (`P1–P5`)**.
3. **`LAW-03` — Zero Hand-Backs & Zero Repeat Instructions (`#7507`)**:
   - **Founder Psyche**: Protect founder mood and cognitive energy at all costs. Never hand back a manual command (`no_handback.py`) and never force the founder to repeat an instruction (`bin/estate-founder-intake` `find_repeat`).
4. **`LAW-04` — Machine $\to$ Model $\to$ Judgment (`ADR 0044` & Tenet `T8`)**:
   - **Founder Psyche**: Never spend a model call where a `<2ms` deterministic script can decide. Hallucinations vanish when deterministic facts are decided by `machine` gates.
5. **`LAW-05` — Greenlane Only (`lane/<name>`)**:
   - **Founder Psyche**: Zero red PR noise on `main`. Agents never push `main` or hand-raise PRs; agents push signed commits (`X-Idp-Signed: <sha256>`) to `lane/<name>` via `estate-execute lane-submit` and let `greenlane/engine.py` prove and fast-forward `main`.

---

## 3. The 5 Exponential Multiplier Kernels ("The Gifts That Keep Giving")

### Gift 1: Unattended Voice-to-Greenlane Autonomous Loop (`estate-dispatchd` + `estate-execute where`)
- **Solves**: `#7505` Rank 5–6 gap (`idp-linear-dispatch` + `idp-agent-orchestrator` built but unwired) + Frictions `F3`, `F4`, `F6`.
- **Architecture**:
  1. `estate-dispatchd` (launchd `ai.estate.dispatchd`) consumes NATS JetStream `ESTATE_FLEET` directives using atomic `estate-fleet inbox --pipe` at production `ack_wait=60s` (`F1`).
  2. Runs `claim-open` on issue paths (`claim-gate` refuses conflicts), dispatches `idp-agent-orchestrator` through `exec-daemon` on `minimax_m27` (`:4001`), and submits `lane/<name> --wait`.
  3. Replies over `ESTATE_FLEET` and speaks the verified lane verdict via `estate-fleet-voice say()`.
  4. Adds `estate-execute where --json` joining active claims, `origin/lane/*` branches (reaping abandoned lanes), and verdicts in one command.

### Gift 2: One-Pass Flawless Discovery Oracle & Tenet Ratchet (`T1–T9` + `R0–R8` + 15-Min Synthetic Probe)
- **Solves**: Discovery blindness (`F2` stale checkout, `F8` silent voice/comms regressions, and 252 untracked laptop intents).
- **Architecture**:
  1. Pre-flight check refuses execution when local `HEAD` lags `origin/main` (`STALE_CHECKOUT`).
  2. Enforces Tenets `T1–T9` (`eval/estate-context/gate_seed.py`): any unreachable reader or expired SLA emits `BLIND` or `ABSTAIN`, never `PASS`.
  3. Runs a 15-minute launchd synthetic probe (`bin/estate-surface-probe`) sending a directive `founder -> probe` over `ESTATE_FLEET`, verifying `speak` stub playback, atomic ack at `60s`, and `/healthz` bus reachability.

### Gift 3: Surgical ClaimSet + ProofSet Compiler & NSVEE (`P1–P5`) + EFDA (`WCFG` / `safetyProof`) Gate
- **Solves**: Hallucinated completions, tautological unit tests, and unverified destructive actions.
- **Architecture**:
  1. Every directive in `estate-founder-intake` compiles to a typed `ClaimSet` + `ProofSet`.
  2. `docs/research/nsvee_integration_gate.py` enforces:
     - **P1**: Scrubbed subprocess execution (never in-process).
     - **P2**: Rejects self-consistent wrong code + tautological tests.
     - **P3**: Exact 95% Clopper-Pearson upper bound $\epsilon = 1 - 0.05^{1/n} \le 0.05$ requiring $n \ge 60$ zero-survivor mutants.
     - **P4**: Non-generator oracle source $\in \{\text{deployed-artifact}, \text{human}, \text{formal}\}$.
     - **P5**: Re-executable `~/.estate/facts.jsonl` row (`instrument_cmd`, `measured_at`, `valid_for_s`, `artifact_sha256`).
  3. `efda/executor.py` enforces Tier-2 controller-owned WAST/WCFG traversal and Tier-3 formal `safetyProof` on destructive paths.

### Gift 4: Agent League War-Games, Sub-2ms `[A] GATE` Pre-Refusal & `$3/Day` Spend-Floor Governor
- **Solves**: `$29.36/day` vs `$3.00/day` spend overrun (`#7248`) and uncalibrated harness routing (`ADR 0038`).
- **Architecture**:
  1. **Router Remediation `R0–R4`**: Enable Postgres spend ledger on `:4001` (`R0`), reject `session: "-"` (`R1`), inject prompt-cache breakpoints (`R2`, cutting multi-turn loop cost by 68%), and enforce per-session USD caps (`R3`).
  2. **Sub-2ms `[A] GATE`**: Export Forge's 97.8%-accurate CI-flake & intent-failure classifier into `estate-execute` so doomed actions are refused in `<2ms` before spending LLM tokens.
  3. **Agent League Tournament (`forge/agent_league_tournament.py`)**: Continuously ranks `minimax_m27`, `gemini-3.5-flash`, `deepseek-v4-flash`, `glm-5.3-flash`, and `claude-code` on **Verified Claims per USD** and **Truth Rate**, auto-promoting winners and throttling high-slop routes.

### Gift 5: Estate-as-Movie Director Spine, Science Dept Bootstrap & Two-Hats Commercial Factory
- **Solves**: Unwired `voice-router-director` Service (`docs/specs/2026-10-23-estate-as-movie-director-engine.md`), dormant ML/Science loop, and Level-1 link-only portal cards (`docs/specs/backstage-as-a-product.md`).
- **Architecture**:
  1. Upgrades `estate.cinema.cue` to a schema'd JetStream subject and wires `director.go` (`ORBIT_FOCUS | PANORAMIC_SWEEP | MACRO_DOV`) to the 3,019-line Three.js stage (`FleetReactorApp.tsx`) with ledger-bound narration and causal `/nudge` voice steering.
  2. Connects the **Science & ML Dept Loop**: `estate.db (s,a,r,s')` $\to$ `growmos` $\to$ `hypotheses.race` (Bayesian racing) $\to$ `forge/` pre-registered experiment $\to$ NSVEE gate $\to$ DSPy prompt compilation.
  3. Enforces the **Commercial Two-Hats Factory Gate** (`docs/specs/two-hats-tenant-split.md` + `backstage-as-a-product.md`): every surface must meet Level 3 (visual) or Level 4 (interactive) and pass `tenant_id` isolation so the platform is commercially ready for external customers at $0 marginal idle cost.

---

## 4. How to Land This in `chidionyema/idp` via Greenlane

Per `/AGENTS.md` §2, agents never push `main` directly or hand-raise unverified PRs. Execute:

```bash
# Inside your local chidionyema/idp repository:
git checkout -B lane/exponential-multiplier-kernel origin/main
# Copy docs/ESTATE_EXPONENTIAL_MULTIPLIER_PLAN.md -> docs/specs/2026-10-30-estate-exponential-multiplier-plan.md
python3 docs/research/nsvee_integration_gate.py
estate-execute lane-submit --wait
```
