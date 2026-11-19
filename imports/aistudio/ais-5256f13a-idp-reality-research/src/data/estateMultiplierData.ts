/**
 * Canonical synthesis of https://github.com/chidionyema/idp (PRs #7324..#7515, Oct 2026)
 * Grounded in measured repository state [M], reported audits [R], and executable kernel contracts [K].
 */

export interface EstatePrCluster {
  clusterId: string;
  title: string;
  prRange: string;
  keyPrs: { pr: string; sha: string; summary: string; stateTag: '[M] OPERATING' | '[M] BUILT_UNWIRED' | '[M] LANDED_GATE' }[];
  bottleneckSolved: string;
  remainingGapToClose: string;
}

export interface FounderPsycheLaw {
  code: string;
  lawTitle: string;
  sourceDoc: string;
  founderPsychologyAndFriction: string;
  mathematicalGateEnforcement: string;
  violationVerdict: string;
}

export interface ExponentialGiftSpec {
  id: string;
  rank: number;
  name: string;
  subtitle: string;
  targetRepoPaths: string[];
  governingPrsAndSpecs: string[];
  multiplierEffect: string;
  penniesEconomics: string;
  commercialCustomerPath: string;
  acceptanceProofCmd: string;
  downstreamCheapModelPrompt: string;
}

export interface AutonomousDepartmentSpec {
  deptId: string;
  name: string;
  charterDoc: string;
  currentBaselineMeasured: string;
  coreLoopArchitecture: string;
  sharedComponentsReused: string[];
  commercialSurfaceOutput: string;
}

export const ESTATE_TWO_WEEK_PR_CLUSTERS: EstatePrCluster[] = [
  {
    clusterId: 'CLUSTER-OTTO-DOOR',
    title: 'Otto Front Door, 31-Wish Parity & OCI AD-2 Lifeboat Recovery',
    prRange: 'PR #7387 – #7515',
    keyPrs: [
      {
        pr: '#7515 / #7514',
        sha: 'fafb505 / 0892a99',
        summary: 'Bounded Otto SLA tick across slow state fetches; live proof for 31 founder wishes across Families A–F.',
        stateTag: '[M] LANDED_GATE',
      },
      {
        pr: '#7508 / #7488 / #7470',
        sha: 'f4ef5db / eeb9165',
        summary: 'After OKE cluster deletion (#7393, limit=0), stood up Always-Free OCI AD-2 VM.Standard.E2.1.Micro recovery host (#7387) with LiteLLM + Cloudflare Tunnel.',
        stateTag: '[M] OPERATING',
      },
      {
        pr: '#7456',
        sha: 'docs/specs/2026-10-29-otto-is-the-estates-front-door.md',
        summary: 'Single front-door contract: every capability Otto has on the Mac must exist on Telegram/Cluster via one governed door.',
        stateTag: '[M] LANDED_GATE',
      },
    ],
    bottleneckSolved:
      'Eliminated split-brain between Mac-local Otto and Telegram Otto after the OKE cluster loss (#7393) while paying $0/mo on Always-Free OCI AD-2.',
    remainingGapToClose:
      'Re-attach the 3 preserved AD-1 CSI block volumes (250GB: postgres, nats, openclaw) once AD-1 micro capacity opens or cross-AD attach is scripted.',
  },
  {
    clusterId: 'CLUSTER-VOICE-FLEET',
    title: 'Fleet Comms, Voice-First 2100 Door & Founder Intake Store',
    prRange: 'PR #7485 – #7512',
    keyPrs: [
      {
        pr: '#7512 / #7500 / #7496',
        sha: '2f22ef6 / a97704b',
        summary: 'One envelope on JetStream ESTATE_FLEET; bin/estate-fleet-voice hear()/say(); atomic inbox --pipe fixing ack_wait=60s voice replay bug (F1).',
        stateTag: '[M] OPERATING',
      },
      {
        pr: '#7509 / #7507 / #7503',
        sha: '1857924 / a2658ab',
        summary: 'bin/estate-founder-intake executable instruction store with find_repeat deduplication so the founder never has to repeat a directive.',
        stateTag: '[M] OPERATING',
      },
      {
        pr: '#7401',
        sha: 'docs/departments/m0-capability-matrix.json',
        summary: 'Media Dept M0 capability matrix & Estate-as-Movie Director Engine (ORBIT_FOCUS, PANORAMIC_SWEEP, MACRO_DOV over Three.js /fleet room).',
        stateTag: '[M] BUILT_UNWIRED',
      },
    ],
    bottleneckSolved:
      'Replaced fragmented ad-hoc agent messaging with a single JetStream envelope (`ESTATE_FLEET`) and atomic voice read-ack (`--pipe`).',
    remainingGapToClose:
      'Wire `estate-dispatchd` launchd daemon (#7505) so a voice directive in `estate-founder-intake` automatically triggers an unattended MiniMax orchestrator run and speaks back the lane verdict.',
  },
  {
    clusterId: 'CLUSTER-ORACLE-TENETS',
    title: 'One-Pass Discovery Oracle, Estate Tenets T1–T9 & Conformance R0–R8',
    prRange: 'PR #7473 – #7506',
    keyPrs: [
      {
        pr: '#7506',
        sha: 'c89e0a6',
        summary: 'bin/schema-conformance enforcing R0–R8 across intent YAMLs (typed args, no free-text where enum fits, valid host_path).',
        stateTag: '[M] LANDED_GATE',
      },
      {
        pr: '#7499',
        sha: '0952ba6',
        summary: 'Tenets T1–T9 (docs/specs/2026-10-30-estate-tenets.md) & failing-capable discovery seed grader (eval/estate-context/gate_seed.py).',
        stateTag: '[M] LANDED_GATE',
      },
      {
        pr: '#7492 / #7484 / #7473',
        sha: 'c05a289 / 07ba954',
        summary: '"A receipt keyword is not proof" (#7492); guardian reports measured delta not cleaner claim (#7473); founder laws compiled into failing gates (#7484).',
        stateTag: '[M] LANDED_GATE',
      },
    ],
    bottleneckSolved:
      'Stopped agents from fabricating PASS verdicts when instruments are unreachable (`BLIND` / `UNMEASURABLE`) or writing keyword-only `Verified:` lines.',
    remainingGapToClose:
      'Close the 362-installed vs 110-tracked intent gap (252 untracked laptop tools) via automated R0–R8 manifest harvesting into `platform/estate/intents`.',
  },
  {
    clusterId: 'CLUSTER-HARNESS-ECONOMICS',
    title: 'Agent League, Model Economics (ADR 0038) & Spend-Floor Governor',
    prRange: 'PR #7248 – #7513',
    keyPrs: [
      {
        pr: '#7513 / #7511 / #7510',
        sha: '5371c22 / 6416c8f',
        summary: 'Default consult.gemini to gemini-3.5-flash with reasoning_effort=low sharing door_s latency bound.',
        stateTag: '[M] OPERATING',
      },
      {
        pr: '#7505 / #7497',
        sha: '63deca6',
        summary: 'Agent harness ranking (evidence-based, not line counts), Friction Register F1–F8, and direct MiniMax estate-dispatchd specification.',
        stateTag: '[M] LANDED_GATE',
      },
      {
        pr: '#7455 / #7248',
        sha: 'docs/specs/2026-10-26-the-estate-llm-spend-floor.md',
        summary: 'AEE G5 concurrency envelope (#7455) & spend floor audit ($29.36/d measured vs $3.00/d cap due to session: "-" blindness & uncached loops).',
        stateTag: '[M] LANDED_GATE',
      },
    ],
    bottleneckSolved:
      'Identified exact root cause of the 9.8x daily LLM spend overrun ($29.36/day vs $3/day cap) and promoted high-yield MiniMax M2.7 + Gemini 3.5 Flash routes.',
    remainingGapToClose:
      'Enforce R0–R4 router hooks (`session_id` required at `:4001`, prompt-cache breakpoints, and `<2ms` `[A] GATE` pre-refusal before frontier token spend).',
  },
];

export const FOUNDER_DEVILS_BARGAIN_LAWS: FounderPsycheLaw[] = [
  {
    code: 'LAW-01 · THE DEVIL’S BARGAIN ($0 BLOAT)',
    lawTitle: 'Exceed the Very Best Industry Standard for Pennies ($0–$150/mo Cap)',
    sourceDoc: 'AGENTS.md §Living Policy + ADR 0034 (Free-Tier Placement Ladder) + ADR 0038',
    founderPsychologyAndFriction:
      'The founder does not pay for idle cloud infrastructure unless funded. Paying for SaaS bloat or uncached frontier token loops ($29.36/day vs $3.00/day cap) is an immediate breach of trust.',
    mathematicalGateEnforcement:
      'Rung 1: Laptop launchd + SQLite/DuckDB ($0). Rung 2: OCI Always-Free AD-2 Micro + KEDA scale-to-zero ($0). Rung 3: Modal/Kaggle free GPU bursts ($0). Router enforces [budget.usd_per_day] litellm = 3.00.',
    violationVerdict: 'DEVILS_BARGAIN_BREACH (Router HTTP 429 / Pre-Gate Refusal)',
  },
  {
    code: 'LAW-02 · BUILT != OPERATING',
    lawTitle: 'A Receipt Keyword Is Not Proof; Done = Operational on /fleet',
    sourceDoc: 'AGENTS.md §1 + PR #7492 + docs/research/nsvee_integration_gate.py (P1–P5)',
    founderPsychologyAndFriction:
      'Nothing angers the founder more than an agent narrating victory ("Done! Verified: ok") when the daemon is unwired, tested at ack_wait=1s instead of 60s, or backed by a tautological test.',
    mathematicalGateEnforcement:
      'NSVEE P1–P5 contract: isolated process execution (P1), mutant kill on self-consistent wrong code (P2), Clopper-Pearson upper bound <= 0.05 with n >= 60 zero-survivor mutants (P3), non-generator oracle (P4), and re-executable facts.jsonl row (P5).',
    violationVerdict: 'FALSE_DONE / RECEIPT_KEYWORD_WITHOUT_PROOF',
  },
  {
    code: 'LAW-03 · ZERO HAND-BACKS & ZERO REPEATS',
    lawTitle: 'Never Hand Back Work to the Founder; Never Force a Second Prompt',
    sourceDoc: 'AGENTS.md §No hand-back + PR #7507 (bin/estate-founder-intake find_repeat)',
    founderPsychologyAndFriction:
      'Prioritize founder mood and cognitive wellbeing. Telling the founder "you can now run X" or forcing the founder to ask twice for the same fix drains founder energy.',
    mathematicalGateEnforcement:
      'no_handback.py scans agent outputs for hand-back phrases and blocks completion. estate-founder-intake hashes and indexes every voice/text directive; repeat directives escalate priority and penalize the prior agent.',
    violationVerdict: 'REFUSED_HANDBACK / REPEAT_DIRECTIVE_ESCALATION',
  },
  {
    code: 'LAW-04 · MACHINE -> MODEL -> JUDGMENT',
    lawTitle: 'Never Spend a Model Call Where a <2ms Deterministic Machine Rule Decides',
    sourceDoc: 'ADR 0044 + docs/specs/2026-10-30-estate-tenets.md (Tenet T8)',
    founderPsychologyAndFriction:
      'Hallucinations happen when LLMs are asked to guess file paths, schema conformance, or CI state that a 1ms deterministic script knows with 100% certainty.',
    mathematicalGateEnforcement:
      'Every gate declares decider = "machine" | "model" | "judgment". If canMachineDecide === true and decider !== "machine", schema-conformance refuses the intent.',
    violationVerdict: 'T8_DECIDER_HIERARCHY_VIOLATION',
  },
  {
    code: 'LAW-05 · GREENLANE ONLY (NEVER PUSH MAIN)',
    lawTitle: 'Agents Push lane/<name> Only; Greenlane Proves & Fast-Forwards Main',
    sourceDoc: 'AGENTS.md §2 + greenlane/engine.py + .github/workflows/greenlane.yml',
    founderPsychologyAndFriction:
      'Agents raising broken PRs or pushing directly to main caused 53% CI failure noise (F7: 513/961 runs not ok). The founder wants zero red PR spam.',
    mathematicalGateEnforcement:
      'Commit carries X-Idp-Signed: <sha256> trailer. Agent executes estate-execute lane-submit -> pushes lane/<name> -> Greenlane verifies on top of HEAD and fast-forwards main.',
    violationVerdict: 'UNSIGNED_OR_DIRECT_MAIN_PUSH_REFUSED',
  },
];

export const EXPONENTIAL_MULTIPLIER_GIFTS: ExponentialGiftSpec[] = [
  {
    id: 'GIFT-01-DISPATCHD-LOOP',
    rank: 1,
    name: 'Gift 1: Unattended Voice-to-Greenlane Autonomous Loop (`estate-dispatchd` + `estate-execute where`)',
    subtitle: 'Closes the #1 gap in PR #7505: wires live JetStream ESTATE_FLEET (items 1–4) to built-unwired orchestrator (items 5–6) on MiniMax M2.7.',
    targetRepoPaths: [
      'bin/estate-dispatchd',
      'bin/estate-execute',
      'launchd/ai.estate.dispatchd.plist',
    ],
    governingPrsAndSpecs: [
      'PR #7505 (docs/audits/2026-10-30-harness-assessment.md §3)',
      'PR #7512 / #7500 (ESTATE_FLEET atomic inbox --pipe)',
      'PR #7507 (bin/estate-founder-intake)',
    ],
    multiplierEffect:
      'Turns the estate from "warship built, nothing operational" into a self-driving fleet: Founder speaks -> `hear()` -> `founder-intake` -> `ESTATE_FLEET` -> `estate-dispatchd` claims paths -> runs MiniMax via `exec-daemon` -> submits `lane/<name>` -> speaks verdict back via `say()`. Also adds `estate-execute where` (fixing Friction F3/F4) to show active claims, 67 lane branches, and verdicts in one command.',
    penniesEconomics:
      'Runs 100% on laptop launchd + NATS :4222 + LiteLLM :4001 (`minimax_m27` + `gemini-3.5-flash` consult door). Zero new cloud brokers.',
    commercialCustomerPath:
      'Packages as the core "Autonomous SRE / DevEx Dispatcher" product surface in `factory/surfaces/autonomous-dispatch` with strict `tenant_id` isolation.',
    acceptanceProofCmd:
      'estate-fleet send dispatch --kind directive --issue 7497 && estate-fleet inbox dispatch --pipe --ack-wait 60 && estate-execute where --json',
    downstreamCheapModelPrompt: `Build Task (Gift 1 — estate-dispatchd & estate-execute where):
1. Read docs/audits/2026-10-30-harness-assessment.md §3.
2. Implement bin/estate-dispatchd consuming NATS JetStream ESTATE_FLEET for agent 'dispatch' using atomic 'estate-fleet inbox --pipe' at production ack_wait=60s.
3. Before editing, invoke 'claim-open' on target issue paths; abort if 'claim-gate' refuses.
4. Execute 'idp-agent-orchestrator provision|submit|poll' via 'exec-daemon' using model 'minimax' on LiteLLM :4001. Never run 'git branch -D'.
5. Implement 'estate-execute where --json' joining active claims, origin lane/* branches (flagging stale lanes >24h), and latest Greenlane verdicts.
6. Fail loud: if NATS, exec-daemon, LiteLLM, or FleetView is unreachable, print 'BLIND' and exit 2.`,
  },
  {
    id: 'GIFT-02-ONE-PASS-ORACLE',
    rank: 2,
    name: 'Gift 2: One-Pass Flawless Discovery Oracle & Tenet Ratchet (`T1–T9` + `R0–R8` + 15-Min Synthetic Probe)',
    subtitle: 'Eliminates agent discovery blindness (F2, F8) and closes the 362-installed vs 110-tracked intent gap.',
    targetRepoPaths: [
      'eval/estate-context/gate_seed.py',
      'bin/schema-conformance',
      'bin/estate-surface-probe',
    ],
    governingPrsAndSpecs: [
      'PR #7499 (docs/specs/2026-10-30-estate-tenets.md T1–T9)',
      'PR #7506 (bin/schema-conformance R0–R8)',
      'PR #7505 §4 (F8 Founder-surface 15-min synthetic regression gate)',
    ],
    multiplierEffect:
      'Gives every agent a 1-ms pre-flight oracle that guarantees: (a) checkout is not behind `origin/main` (fixing F2), (b) observation failures (`ABSENT | READER_UNAVAILABLE | STALE | UNMEASURABLE`) return `BLIND` or `ABSTAIN` instead of hallucinated `PASS`, and (c) a 15-minute synthetic voice/bus probe continuously verifies founder surfaces so the founder never discovers a broken mic/inbox.',
    penniesEconomics:
      '100% deterministic Python/TypeScript machine deciders (`decider: machine`, `<15ms` execution, `$0.00` LLM token cost).',
    commercialCustomerPath:
      'Exposes the Tenet Conformance & Epistemic Discovery Grader as a verifiable compliance scorecard for enterprise IDP tenants.',
    acceptanceProofCmd:
      'python3 eval/estate-context/gate_seed.py --strict && bin/schema-conformance --all && bin/estate-surface-probe --once',
    downstreamCheapModelPrompt: `Build Task (Gift 2 — One-Pass Discovery Oracle & F8 Synthetic Probe):
1. Extend bin/schema-conformance (#7506) with --harvest-untracked to scan the 252 untracked laptop tools and emit R0-R8 compliant intent YAML stubs.
2. Add a pre-flight HEAD staleness guard (Friction F2): if local HEAD is behind origin/main, print STALE_CHECKOUT and refuse tool execution unless --allow-stale is passed.
3. Implement bin/estate-surface-probe (Friction F8): every 15 minutes send a synthetic directive founder -> probe agent over ESTATE_FLEET, read back via speak with stub player, assert ack at ack_wait=60s, and assert /healthz bus reachability.`,
  },
  {
    id: 'GIFT-03-CLAIMSET-PROOFSET-NSVEE',
    rank: 3,
    name: 'Gift 3: Surgical ClaimSet + ProofSet Compiler & NSVEE + EFDA Formal Verification Gate',
    subtitle: 'Compiles every founder voice/text prompt into a mathematical ClaimSet requiring Clopper-Pearson <= 0.05 (n>=60) and EFDA WCFG proofs.',
    targetRepoPaths: [
      'docs/research/nsvee_integration_gate.py',
      'efda/executor.py',
      'bin/idp-verdict',
    ],
    governingPrsAndSpecs: [
      'docs/research/nsvee_integration_gate.py (P1–P5)',
      'docs/specs/2026-10-26-verified-completion-v2.md (Tier 1–3)',
      'PR #7492 ("a receipt keyword is not proof") & PR #7484',
    ],
    multiplierEffect:
      'Makes hallucinated completions mathematically impossible. Every founder directive in `estate-founder-intake` produces a locked `ClaimSet`. An agent cannot mark an issue `VERIFIED` unless `nsvee_integration_gate.py` passes P1–P5 in a clean worktree (`agent-countercheck` pattern) and destructive operations carry an EFDA Tier-3 `safetyProof` certificate.',
    penniesEconomics:
      'Runs stdlib-only mutation & WCFG state-machine verification in scrubbed subprocesses (`<2s` CPU, `$0` API spend).',
    commercialCustomerPath:
      'Differentiates the IDP commercially as the only agentic platform with mathematical Clopper-Pearson & WCFG safety guarantees for regulated industries.',
    acceptanceProofCmd:
      'python3 docs/research/nsvee_integration_gate.py && bin/idp-verdict verify --claim-id CP-7507 --require-facts-row',
    downstreamCheapModelPrompt: `Build Task (Gift 3 — ClaimSet + ProofSet + NSVEE Gate Wiring):
1. Wire docs/research/nsvee_integration_gate.py (P1-P5) into bin/idp-verdict so any code change claim requires:
   - P1: Scrubbed subprocess execution (never in-process).
   - P2: Rejection of self-consistent wrong code + tautological tests.
   - P3: Exact Clopper-Pearson upper bound <= 0.05 (n >= 60 mutants with 0 survivors).
   - P4: Declared non-generator oracle source in {deployed-artifact, human, formal}.
   - P5: Re-executable ~/.estate/facts.jsonl row (instrument_cmd, measured_at, valid_for_s, artifact_sha256).
2. Wire EFDA Tier-2 controller-owned WCFG edge check and Tier-3 safetyProof into efda/executor.py.`,
  },
  {
    id: 'GIFT-04-AGENT-LEAGUE-SPEND-SHIELD',
    rank: 4,
    name: 'Gift 4: Agent League War-Games, Sub-2ms `[A] GATE` Pre-Refusal & $3/Day Spend-Floor Shield',
    subtitle: 'Cuts LLM spend from $29.36/day to <$3.00/day (#7248) while continuously tournament-ranking agents and prompts via DSPy & Forge.',
    targetRepoPaths: [
      'platform/litellm/request_ceiling.py',
      'platform/litellm/efficiency_gateway.py',
      'forge/agent_league_tournament.py',
    ],
    governingPrsAndSpecs: [
      'docs/specs/2026-10-26-the-estate-llm-spend-floor.md (#7248 R0–R4)',
      'docs/specs/2026-09-29-machine-learning-dept.md ([A] GATE + JevLayer)',
      'ADR 0038 (Model Performance Review) & PR #7513 (Gemini 3.5 Flash)',
    ],
    multiplierEffect:
      'Combines the ML Department’s `<2ms` `[A] GATE policy.predict(intent, args, ctx)` (which refuses doomed actions before a single token is spent) with mandatory `session_id` router attribution (`R1`), prompt-cache breakpoints (`R2`), and an automated **Agent League War-Game** where harnesses (`minimax_m27`, `gemini-3.5-flash`, `deepseek-v4-flash`, `glm-5.3-flash`, `claude-code`) compete on real falsifiable tasks for token budget allocation.',
    penniesEconomics:
      'Directly saves ~$26.36/day ($790/month) by enforcing the founder’s `[budget.usd_per_day] litellm = 3.0` TOML law and shifting classification/grading to `gemini-3.5-flash` (`reasoning_effort=low`).',
    commercialCustomerPath:
      'Powers the "FinOps & Multi-Model Fin-Router" commercial module—proving to enterprise buyers that the platform delivers frontier quality at 1/10th the token spend.',
    acceptanceProofCmd:
      'estate-execute llm-spend-audit --assert-under-daily-cap 3.00 && python3 forge/agent_league_tournament.py --dry-run',
    downstreamCheapModelPrompt: `Build Task (Gift 4 — Spend-Floor Shield R0-R4 & Agent League Tournament):
1. Implement R0-R4 from docs/specs/2026-10-26-the-estate-llm-spend-floor.md in efficiency_gateway.py & request_ceiling.py:
   - Refuse any /v1/chat/completions call missing a valid caller session_id (reject session: "-").
   - Inject prompt-cache breakpoints on system/repo-map prefixes.
   - Enforce per-session token & USD ceiling aligned with [budget.usd_per_day] litellm = 3.0.
2. Export the trained Forge CI-flake & intent-failure classifier (97.8% agreement) into [A] GATE so doomed intents are refused in <2ms before LLM invocation.
3. Build forge/agent_league_tournament.py to score harnesses weekly on Verified Claims / USD and auto-update router weights.`,
  },
  {
    id: 'GIFT-05-MOVIE-DIRECTOR-SCIENCE-COMMERCIAL',
    rank: 5,
    name: 'Gift 5: Estate-as-Movie Director Spine, Science Dept Bootstrap & Two-Hats Commercial Factory',
    subtitle: 'Wires `director.go` (`ORBIT_FOCUS | PANORAMIC_SWEEP | MACRO_DOV`) to `/fleet` Three.js room, Science `hypotheses.race`, and Level 3–4 Customer Surfaces.',
    targetRepoPaths: [
      'platform/voice-router/internal/director/director.go',
      'backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx',
      'factory/surfaces/tenant_gate.py',
    ],
    governingPrsAndSpecs: [
      'docs/specs/2026-10-23-estate-as-movie-director-engine.md',
      'docs/specs/backstage-as-a-product.md (Level 3–4 surface bar)',
      'docs/specs/two-hats-tenant-split.md & PR #7401 (Media Dept M0/M1)',
    ],
    multiplierEffect:
      'Delivers the founder’s 2100 vision: the estate is watched as a live, truthful film on `/fleet` and `/face` where every sentence is template-over-ledger (zero hallucinated narration) and the founder’s spoken word causally re-cuts the Three.js camera (`cinecam.ts`) and steers agents via `/nudge`. Simultaneously enforces the `two-hats-tenant-split.md` & Level 3–4 visual/interactive bar so every surface is immediately customer-demoable.',
    penniesEconomics:
      'Renders client-side in WebGL/Three.js (`FleetReactorApp.tsx`) over existing NATS WebSocket frames (`estate.cinema.cue` upgraded to JetStream) for $0 GPU video-generation cost.',
    commercialCustomerPath:
      'Turns Backstage + `/fleet` into a flagship commercial product ("Backstage-as-a-Product" + Live Autonomous Operations Room) ready for customer tenants at any moment.',
    acceptanceProofCmd:
      'estate-execute movie-director-smoke --verify-causal-nudge && bin/schema-conformance --check-surface-levels --min-level 3',
    downstreamCheapModelPrompt: `Build Task (Gift 5 — Movie Director Engine, Science Loop & Commercial Two-Hats Gate):
1. Promote 'estate.cinema.cue' from ephemeral core NATS to a JSON-schema'd JetStream subject backed by platform/voice-router/internal/director/director.go.
2. Declare the missing Kubernetes/launchd Service for voice-router-director so FleetReactorApp.tsx (:1587) receives deterministic ORBIT_FOCUS, PANORAMIC_SWEEP, and MACRO_DOV camera cuts driven by real estate.agent.<runtime>.<session_id>.<kind> events.
3. Enforce docs/specs/backstage-as-a-product.md Level 3 (visual) and Level 4 (interactive) across founder & customer cards, and verify tenant_id isolation per docs/specs/two-hats-tenant-split.md.`,
  },
];

export const AUTONOMOUS_DEPARTMENTS_MATRIX: AutonomousDepartmentSpec[] = [
  {
    deptId: 'DEPT-SCIENCE-ML',
    name: 'Science & Machine Learning Department (The Self-Improving Brain)',
    charterDoc: 'docs/specs/2026-09-29-machine-learning-dept.md + docs/research/nsvee_all_in_one.py',
    currentBaselineMeasured:
      '1,753 intent_tickets in ~/.estate/estate.db (20% halted/broken); 33,761 efficiency-ledger rows; Forge CI-flake model at 97.8% agreement (trained, awaiting export to [A] GATE); growmos graph at 128 nodes with 577 sources pending.',
    coreLoopArchitecture:
      'Observation (estate-execute (s,a,r,s’) log) -> Hypothesis Generation (growmos + Science Dept) -> Bayesian Racing (libexec/hypotheses-race.py) -> Pre-Registered Forge Experiment (forge/experiment_record.py + cost_gate) -> NSVEE P1–P5 Verification -> Sub-2ms Policy Export ([A] GATE).',
    sharedComponentsReused: [
      '~/.estate/estate.db (intent_tickets & step_runs)',
      'libexec/hypotheses-race.py (Bayesian racing engine)',
      'forge/ (Modal + Kaggle zero-cost GPU launchers)',
      '.growmos/ (shared epistemic knowledge graph)',
    ],
    commercialSurfaceOutput:
      'Self-Healing CI & Pre-Execution Policy Gate (`factory/surfaces/ml-policy-gate`)',
  },
  {
    deptId: 'DEPT-MEDIA-DIRECTOR',
    name: 'Autonomous Media & Virtual World Department (Estate-as-Movie M0/M1)',
    charterDoc: 'docs/specs/2026-10-23-estate-as-movie-director-engine.md + PR #7401 (m0-capability-matrix.json)',
    currentBaselineMeasured:
      'FleetReactorApp.tsx (3,019 lines Three.js room + cinecam.ts tested); director.go shot grammar (ORBIT_FOCUS, PANORAMIC_SWEEP, MACRO_DOV); Whisper STT + Kokoro local TTS operating on laptop.',
    coreLoopArchitecture:
      'Event Spine (`estate.agent.<runtime>.<session>.<kind>`) -> `director.go` Coalesce & Shot Planner -> Ledger-Bound Narrator (template-over-ledger, zero generative hallucination) -> Three.js WebGL Stage (`/fleet` & `/face`) -> Causal Voice Steering (`/nudge` -> `ESTATE_FLEET`).',
    sharedComponentsReused: [
      'platform/voice-router/internal/director/director.go',
      'backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx',
      'bin/estate-fleet-voice (Whisper + Kokoro voice door)',
    ],
    commercialSurfaceOutput:
      '2100 Spatial Operations Command Center & Live Artifact Stage (`catalogue.mumchimp.com/face/`)',
  },
  {
    deptId: 'DEPT-COMMERCIAL-FACTORY',
    name: 'Commercialisation & Customer Factory Department (Two-Hats Product Spine)',
    charterDoc: 'docs/specs/backstage-as-a-product.md + docs/specs/two-hats-tenant-split.md',
    currentBaselineMeasured:
      '52 founder-surface components in backstage/founder/catalog-info.yaml; 7 surfaces already at Level 3–4 (Catalogue, Tools, Ops, Investigate, Reports, Pair Phone, Screen); OCI AD-2 Always-Free lifeboat live (#7387/#7508).',
    coreLoopArchitecture:
      'Internal Capability Built for Pennies -> Schema Conformance R0–R8 (#7506) -> Level 3–4 Visual/Interactive Upgrade (refusing Level 1 link-only cards) -> Two-Hats `tenant_id` Isolation Check -> Instant Customer Tenant Provisioning.',
    sharedComponentsReused: [
      'backstage/founder/catalog-info.yaml',
      'factory/surfaces/* (customer tenant surface templates)',
      'efda/executor.py (tenant_id isolation invariant)',
    ],
    commercialSurfaceOutput:
      'Turnkey Enterprise Internal Developer Portal & Autonomous Fleet-in-a-Box',
  },
];
