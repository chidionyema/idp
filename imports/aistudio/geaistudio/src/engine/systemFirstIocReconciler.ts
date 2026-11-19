import fs from 'node:fs';
import path from 'node:path';
import {
  BoundaryManifestValidation,
  evaluateEstateTargetAdmission,
  evaluateZeroGaslightAdmission,
  ExternalComponentProbeInput,
  MeasuredEstateHostRow,
  R_ZAI_01_MEASURED_HOSTS,
} from './meridianCapabilityCalculus';
import { pureSha256Hex } from './pureSha256';

export const SYSTEM_FIRST_IOC_LAW_ID = 'LAW_SYSTEM_FIRST_IOC_RECONCILER' as const;
export const MAX_GENESIS_SPORE_BYTES = 4096;

export type InterchangeableActuatorId =
  | 'gemini'
  | 'glm-5.3'
  | 'deepseek'
  | 'kimi'
  | 'claude'
  | 'chatgpt';

export interface InterchangeableActuatorDescriptor {
  id: InterchangeableActuatorId;
  label: string;
  transportLane: string;
  statelessRole: string;
}

export const INTERCHANGEABLE_ACTUATORS: readonly InterchangeableActuatorDescriptor[] = [
  {
    id: 'gemini',
    label: 'Gemini 4 Carbon / Pro',
    transportLane: 'AI Studio Build + pennyd :4200',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
  {
    id: 'glm-5.3',
    label: 'GLM 5.3 (Z.ai)',
    transportLane: 'pennyd 127.0.0.1:4200 + BR-ZAI-01',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek V3 / R1',
    transportLane: 'pennyd 127.0.0.1:4200 + BR-DEEPSEEK-01',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
  {
    id: 'kimi',
    label: 'Kimi K2 (Moonshot)',
    transportLane: 'pennyd 127.0.0.1:4200 + BR-KIMI-01',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
  {
    id: 'claude',
    label: 'Claude Sonnet / Opus',
    transportLane: 'pennyd 127.0.0.1:4200 + BR-CLAUDE-01',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
  {
    id: 'chatgpt',
    label: 'ChatGPT / OpenAI o-Series',
    transportLane: 'pennyd 127.0.0.1:4200 + BR-CHATGPT-01',
    statelessRole: 'Stateless compute actuator bound to repo DNA + OMNIFLOW',
  },
];

export interface AntiConfusionLedgerRow {
  domainId: string;
  domain: string;
  retiredTombstoned: string;
  canonicalLiveTruth: string;
  enforcementGate: string;
}

export const ANTI_CONFUSION_LEDGER: readonly AntiConfusionLedgerRow[] = [
  {
    domainId: 'DOM-01-ROUTER',
    domain: 'Local & Cloud Router',
    retiredTombstoned: 'LiteLLM on :4000, :4001, :4002; com.estate.litellm-* plists',
    canonicalLiveTruth: 'pennyd on 127.0.0.1:4200 (local) and llm.mumchimp.com (cloud Lane 2)',
    enforcementGate: 'ROUTER.md, estate-router-sweep (46 files swept, 0 listeners on 4000–4002)',
  },
  {
    domainId: 'DOM-02-CREDENTIAL',
    domain: 'Router Credential',
    retiredTombstoned: 'LITELLM_API_KEY (kept solely as a compatibility alias at the DSH boundary)',
    canonicalLiveTruth:
      'PENNYD_API_KEY validated by live max_tokens:0 probe (keys.toml fallback if vault key is stale)',
    enforcementGate: 'dsh-web-launchd probe-before-use + commit ac497a97f (INS-00018)',
  },
  {
    domainId: 'DOM-03-KUBERNETES',
    domain: 'Kubernetes Cluster',
    retiredTombstoned:
      'Oracle OKE (193.123.184.22, 141.147.80.229:6443, oke-direct, config-estate using dead oci plugin)',
    canonicalLiveTruth:
      'Self-managed k3s on OCI Always Free Ampere A1 VM (4 OCPU, 24 GB RAM, 200 GB storage; /etc/rancher/k3s/k3s.yaml)',
    enforcementGate: 'F31 Ghost IP denylist (193.123.184.22), ~/.kube/retired-20261117/, ADR-0017',
  },
  {
    domainId: 'DOM-04-LOCAL-WEB',
    domain: 'Local Web Surface',
    retiredTombstoned: 'GUI-only LaunchAgent dying on logout or wedged processes holding :3080',
    canonicalLiveTruth:
      'system/ai.estate.dsh-web + system/ai.estate.dsh-web-heal (30s active HTTP healer, runs after FileVault unlock)',
    enforcementGate: 'dsh-web-heal-selftest (crash + bootout falsifiers passing)',
  },
  {
    domainId: 'DOM-05-SHADOW-DB',
    domain: 'Shadow CI Database',
    retiredTombstoned: 'Replacing in-cluster DNS with mock/ephemeral GitHub Actions Postgres',
    canonicalLiveTruth:
      'Real in-cluster k3d + Flux + CloudNativePG stand-in (estate-rw.estate-db.svc) + router-recovery.yml callback fix',
    enforcementGate: 'R-ZAI-01 remediation table & test_the_shadow_stands_in_*',
  },
  {
    domainId: 'DOM-06-CAPABILITY-STATUS',
    domain: 'Capability Status',
    retiredTombstoned: 'Grading merged PRs or static deploys as OPERATING ("fake yield")',
    canonicalLiveTruth:
      'DECLARED_UNPROBED until bin/estate-live-probe returns a fresh outside-in MEASURED_OK receipt',
    enforcementGate: 'defect/live-services-failed-while-declared-2026-11-16 & R-010',
  },
  {
    domainId: 'DOM-07-TASK-ADMISSION',
    domain: 'Task Admission',
    retiredTombstoned: 'Dispatch -> Spend tokens -> Generate 3-subsystem diff -> Reject at Proof 2',
    canonicalLiveTruth:
      'Validate -> Decompose -> Execute -> Verify -> Deliver (1 to 5 files, exactly 1 top-level subsystem, 0 guarded paths)',
    enforcementGate: 'evaluateZeroGaslightAdmission (HTTP 422 at 0 tokens spent, RFCE #8188)',
  },
  {
    domainId: 'DOM-08-AGENT-BUS',
    domain: 'Cross-Agent Bus',
    retiredTombstoned:
      'Manual Founder copy-pasting between tabs or competing Durable Object leases',
    canonicalLiveTruth:
      'Canonical OMNIFLOW SSE/HTTPS Bus (estate-bus DO scoped strictly as stateless edge adapter, competingAuthority: false)',
    enforcementGate: 'Monotonic fence tokens (409), 10s TTL recovery, KARMA 403 self-verify block',
  },
];

export interface AntiConfusionViolation {
  domainId: string;
  domain: string;
  matchedRetiredGhost: string;
  canonicalReplacement: string;
  enforcementGate: string;
}

interface GhostPatternRule {
  domainId: string;
  pattern: RegExp;
  allowIfContains?: RegExp;
  matchedLabel: string;
}

const GHOST_PATTERN_RULES: readonly GhostPatternRule[] = [
  {
    domainId: 'DOM-01-ROUTER',
    pattern: /(?:127\.0\.0\.1|localhost|0\.0\.0\.0)?:400[012]\b|\bcom\.estate\.litellm(?:-[a-z0-9_-]+)?\b/i,
    matchedLabel: 'Retired LiteLLM port (:4000/:4001/:4002) or com.estate.litellm-* plist',
  },
  {
    domainId: 'DOM-02-CREDENTIAL',
    pattern: /\bLITELLM_API_KEY\b/,
    allowIfContains: /\bdsh[-_\s]?(?:alias|boundary|compat)/i,
    matchedLabel: 'Direct LITELLM_API_KEY usage outside DSH compatibility alias boundary',
  },
  {
    domainId: 'DOM-03-KUBERNETES',
    pattern: /\b(?:193\.123\.184\.22|141\.147\.80\.229(?::6443)?|oke-direct|config-estate)\b/i,
    matchedLabel: 'Retired Oracle OKE cluster ghost (193.123.184.22 / 141.147.80.229 / oke-direct / config-estate)',
  },
  {
    domainId: 'DOM-04-LOCAL-WEB',
    pattern: /\bLaunchAgents\/.*3080\b|\bgui-only\s+launchagent\b/i,
    allowIfContains: /ai\.estate\.dsh-web-heal/i,
    matchedLabel: 'GUI-only :3080 LaunchAgent without system/ai.estate.dsh-web-heal',
  },
  {
    domainId: 'DOM-05-SHADOW-DB',
    pattern: /\bmock[-_\s]?postgres[-_\s]?dns\b|\bephemeral\s+actions\s+postgres\b/i,
    matchedLabel: 'Mock/ephemeral CI Postgres overriding estate-rw.estate-db.svc',
  },
  {
    domainId: 'DOM-08-AGENT-BUS',
    pattern: /\bcompetingAuthority\s*:\s*true\b/i,
    matchedLabel: 'Competing Durable Object lease authority (competingAuthority: true)',
  },
];

export function scanAntiConfusionGhostViolations(input: {
  taskPrompt?: string;
  proposedFiles?: string[];
  targetHosts?: string[];
}): AntiConfusionViolation[] {
  const corpus = [
    input.taskPrompt ?? '',
    ...(input.proposedFiles ?? []),
    ...(input.targetHosts ?? []),
  ].join('\n');

  const violations: AntiConfusionViolation[] = [];
  for (const rule of GHOST_PATTERN_RULES) {
    if (rule.pattern.test(corpus)) {
      if (rule.allowIfContains && rule.allowIfContains.test(corpus)) {
        continue;
      }
      const row = ANTI_CONFUSION_LEDGER.find((r) => r.domainId === rule.domainId)!;
      violations.push({
        domainId: row.domainId,
        domain: row.domain,
        matchedRetiredGhost: rule.matchedLabel,
        canonicalReplacement: row.canonicalLiveTruth,
        enforcementGate: row.enforcementGate,
      });
    }
  }
  return violations;
}

export interface GenesisSporeDnaDocument {
  schema: string;
  law: string;
  updated_at_utc: string;
  interchangeable_actuators: string[];
  active_merkle_root: string;
  monotonic_fencing_token: number;
  reversible_state_journal: {
    checkpoint_id: string;
    canonical_local_router: string;
    canonical_cloud_router: string;
    canonical_k8s_cluster: string;
    canonical_bus: string;
    bundle_path: string;
    agents_md_ceiling_lines: number;
    max_spore_bytes: number;
    clean_room_stages: number;
    closed_loop_fsms: number;
  };
  constitutional_invariants: string[];
  catechism_antibodies: Array<{
    id: string;
    code: string;
    block: string;
    enforced_truth: string;
  }>;
}

export interface ZeroDependencyContinuityReport {
  verified: boolean;
  law: typeof SYSTEM_FIRST_IOC_LAW_ID;
  agentsMdPresent: boolean;
  agentsMdLines: number;
  agentsMdWithinCeiling: boolean;
  routerMdPresent: boolean;
  routerMdEnforcesPennyd4200: boolean;
  routerMdTombstonesLiteLlm4000: boolean;
  genesisSporePresent: boolean;
  genesisSporeBytes: number;
  genesisSporeWithin4Kb: boolean;
  activeMerkleRoot: string | null;
  monotonicFencingToken: number | null;
  constitutionalInvariantsCount: number;
  catechismAntibodiesCount: number;
  sporeSha256: string | null;
  sporeDocument: GenesisSporeDnaDocument | null;
  violations: string[];
}

export function verifyRepositoryZeroDependencyContinuity(
  repoRoot: string
): ZeroDependencyContinuityReport {
  const violations: string[] = [];

  const agentsAbs = path.join(repoRoot, 'AGENTS.md');
  const agentsMdPresent = fs.existsSync(agentsAbs);
  const agentsContent = agentsMdPresent ? fs.readFileSync(agentsAbs, 'utf8') : '';
  const agentsMdLines = agentsMdPresent ? agentsContent.split('\n').length : 0;
  const agentsMdWithinCeiling = agentsMdPresent && agentsMdLines >= 1 && agentsMdLines <= 300;
  if (!agentsMdWithinCeiling) {
    violations.push(`AGENTS.md must exist and be 1..300 lines (got ${agentsMdLines}).`);
  }

  const routerAbs = path.join(repoRoot, 'ROUTER.md');
  const routerMdPresent = fs.existsSync(routerAbs);
  const routerContent = routerMdPresent ? fs.readFileSync(routerAbs, 'utf8') : '';
  const routerMdEnforcesPennyd4200 = routerContent.includes('127.0.0.1:4200') && routerContent.includes('pennyd');
  const routerMdTombstonesLiteLlm4000 = routerContent.includes(':4000') && routerContent.includes('LiteLLM');
  if (!routerMdPresent || !routerMdEnforcesPennyd4200 || !routerMdTombstonesLiteLlm4000) {
    violations.push('ROUTER.md missing or fails to enforce pennyd 127.0.0.1:4200 + LiteLLM :4000 tombstone.');
  }

  const sporeAbs = path.join(repoRoot, 'GENESIS_SPORE.dna');
  const genesisSporePresent = fs.existsSync(sporeAbs);
  const sporeRaw = genesisSporePresent ? fs.readFileSync(sporeAbs, 'utf8') : '';
  const genesisSporeBytes = genesisSporePresent ? Buffer.byteLength(sporeRaw, 'utf8') : 0;
  const genesisSporeWithin4Kb =
    genesisSporePresent && genesisSporeBytes > 0 && genesisSporeBytes <= MAX_GENESIS_SPORE_BYTES;
  if (!genesisSporeWithin4Kb) {
    violations.push(
      `GENESIS_SPORE.dna must exist and be <= ${MAX_GENESIS_SPORE_BYTES} bytes (got ${genesisSporeBytes}).`
    );
  }

  let sporeDoc: GenesisSporeDnaDocument | null = null;
  if (genesisSporePresent) {
    try {
      sporeDoc = JSON.parse(sporeRaw) as GenesisSporeDnaDocument;
    } catch (err) {
      violations.push(
        `GENESIS_SPORE.dna invalid JSON: ${err instanceof Error ? err.message : 'parse failed'}`
      );
    }
  }

  const invariantsCount = sporeDoc?.constitutional_invariants?.length ?? 0;
  const antibodiesCount = sporeDoc?.catechism_antibodies?.length ?? 0;
  const merkleOk = Boolean(sporeDoc?.active_merkle_root && /^[0-9a-f]{64}$/.test(sporeDoc.active_merkle_root));
  const fenceOk = typeof sporeDoc?.monotonic_fencing_token === 'number' && sporeDoc.monotonic_fencing_token >= 1;

  if (invariantsCount !== 12) {
    violations.push(`GENESIS_SPORE.dna must carry 12 constitutional_invariants (got ${invariantsCount}).`);
  }
  if (antibodiesCount !== 10) {
    violations.push(`GENESIS_SPORE.dna must carry 10 catechism_antibodies (got ${antibodiesCount}).`);
  }
  if (!merkleOk || !fenceOk || !sporeDoc?.reversible_state_journal) {
    violations.push('GENESIS_SPORE.dna missing 64-hex active_merkle_root, monotonic_fencing_token, or reversible_state_journal.');
  }

  return {
    verified: violations.length === 0,
    law: SYSTEM_FIRST_IOC_LAW_ID,
    agentsMdPresent,
    agentsMdLines,
    agentsMdWithinCeiling,
    routerMdPresent,
    routerMdEnforcesPennyd4200,
    routerMdTombstonesLiteLlm4000,
    genesisSporePresent,
    genesisSporeBytes,
    genesisSporeWithin4Kb,
    activeMerkleRoot: sporeDoc?.active_merkle_root ?? null,
    monotonicFencingToken: sporeDoc?.monotonic_fencing_token ?? null,
    constitutionalInvariantsCount: invariantsCount,
    catechismAntibodiesCount: antibodiesCount,
    sporeSha256: genesisSporePresent ? pureSha256Hex(sporeRaw) : null,
    sporeDocument: sporeDoc,
    violations,
  };
}

export interface IocPreTokenGateRow {
  gateId: string;
  title: string;
  verdict: 'PASSED' | 'AUTO_DECOMPOSED' | 'BLOCKED';
  detail: string;
}

export interface SystemFirstIocAdmissionInput {
  actuatorModel?: InterchangeableActuatorId;
  workerId?: string;
  workerQuadAttested?: boolean;
  taskPrompt?: string;
  proposedFiles?: string[];
  targetHosts?: string[];
  expectedBaseSha?: string;
  observedBaseSha?: string;
  observedDiffFiles?: string[];
  autoDecompose?: boolean;
}

export interface SystemFirstIocAdmissionResult {
  law: typeof SYSTEM_FIRST_IOC_LAW_ID;
  actuatorModel: InterchangeableActuatorId;
  workerId: string;
  admitted: boolean;
  httpStatus: 200 | 403 | 422;
  verdictCode:
    | 'ADMITTED_ZERO_GASLIGHT'
    | 'ADMITTED_VIA_AUTO_DECOMPOSITION'
    | 'ANTI_CONFUSION_RETIRED_GHOST_BLOCKED'
    | string;
  tokensSpent: 0;
  gateRows: IocPreTokenGateRow[];
  antiConfusionViolations: AntiConfusionViolation[];
  boundaryValidation: BoundaryManifestValidation | null;
  decomposedChildLanes: Array<{
    laneId: string;
    subsystem: string;
    files: string[];
  }>;
  blockedComponents: Array<{ componentId: string; status: string; reason: string }>;
  summary: string;
  receiptSha256: string;
}

export function evaluateSystemFirstIocGate(
  input: SystemFirstIocAdmissionInput
): SystemFirstIocAdmissionResult {
  const actuatorModel: InterchangeableActuatorId = input.actuatorModel ?? 'glm-5.3';
  const workerId = (input.workerId ?? `actuator-${actuatorModel}`).trim() || `actuator-${actuatorModel}`;
  const workerQuadAttested = input.workerQuadAttested !== false;
  const proposedFiles = Array.isArray(input.proposedFiles)
    ? input.proposedFiles.map((f) => String(f ?? '').trim()).filter(Boolean)
    : [];
  const targetHosts = Array.isArray(input.targetHosts)
    ? input.targetHosts.map((h) => String(h ?? '').trim()).filter(Boolean)
    : [];
  const autoDecompose = Boolean(input.autoDecompose);

  // Build live outside-in component probe list from R_ZAI_01_MEASURED_HOSTS
  const requiredComponents: ExternalComponentProbeInput[] = targetHosts.map((h) => {
    const clean = h.toLowerCase().replace(/^https?:\/\//, '');
    const match = R_ZAI_01_MEASURED_HOSTS.find(
      (row) =>
        row.host.toLowerCase() === clean ||
        clean.startsWith(`${row.host.toLowerCase()}/`) ||
        row.host.toLowerCase().startsWith(clean)
    );
    if (!match) {
      return {
        componentId: h,
        status: 'NOT_PROBED',
        errorDetail: `Target "${h}" is DECLARED_UNPROBED — requires fresh bin/estate-live-probe MEASURED_OK receipt.`,
      };
    }
    return {
      componentId: match.host,
      status: match.probeStatus,
      retiredOkeIpDetected: match.retiredOkeIpDetected,
      targetUrl: `https://${match.host}`,
      errorDetail: match.detail,
    };
  });

  // Also cross-verify via evaluateEstateTargetAdmission when hosts are present
  if (targetHosts.length > 0 && workerQuadAttested) {
    evaluateEstateTargetAdmission({
      workerId,
      targetHosts,
      proposedFiles: proposedFiles.length > 0 ? proposedFiles : ['src/placeholder.ts'],
    });
  }

  const baseDecision = evaluateZeroGaslightAdmission({
    workerId,
    workerQuadAttested,
    proposedFiles,
    expectedBaseSha: input.expectedBaseSha,
    observedBaseSha: input.observedBaseSha,
    observedDiffFiles: input.observedDiffFiles,
    requiredComponents,
  });

  const ghostViolations = scanAntiConfusionGhostViolations({
    taskPrompt: input.taskPrompt,
    proposedFiles,
    targetHosts,
  });

  const bv = baseDecision.boundaryValidation;
  const decomposedChildLanes = (bv?.decomposedLanes ?? []).map((lane, idx) => ({
    laneId: `LANE-${String(idx + 1).padStart(2, '0')}-${lane.subsystem}`,
    subsystem: lane.subsystem,
    files: lane.files,
  }));

  const onlyMultiSubsystemFailure =
    bv !== null &&
    !bv.boundaryValid &&
    bv.invalidCanonicalPaths.length === 0 &&
    bv.guardedPathsTriggered.length === 0 &&
    bv.fileCount >= 1 &&
    decomposedChildLanes.length > 1 &&
    baseDecision.failedGates.every((g) => g === 'BOUNDARY_INVALID_NO_ADMISSION') &&
    ghostViolations.length === 0;

  const admittedViaDecompose = autoDecompose && onlyMultiSubsystemFailure;
  const admitted = (baseDecision.admitted && ghostViolations.length === 0) || admittedViaDecompose;

  const httpStatus: 200 | 403 | 422 = admitted
    ? 200
    : !workerQuadAttested
      ? 403
      : 422;

  const verdictCode = admittedViaDecompose
    ? 'ADMITTED_VIA_AUTO_DECOMPOSITION'
    : ghostViolations.length > 0
      ? 'ANTI_CONFUSION_RETIRED_GHOST_BLOCKED'
      : baseDecision.status;

  const gateRows: IocPreTokenGateRow[] = [
    {
      gateId: 'GATE-1-ATTESTATION',
      title: 'Gate 1 · Worker QUAD Attestation',
      verdict: workerQuadAttested ? 'PASSED' : 'BLOCKED',
      detail: workerQuadAttested
        ? `Actuator "${actuatorModel}" (${workerId}) presented attested QUAD identity.`
        : 'HTTP 403 WORKER_UNATTESTED_NO_ADMISSION — unattested workers blocked pre-token.',
    },
    {
      gateId: 'GATE-2-MANIFEST',
      title: 'Gate 2 · Explicit Change Manifest',
      verdict: proposedFiles.length > 0 ? 'PASSED' : 'BLOCKED',
      detail:
        proposedFiles.length > 0
          ? `${proposedFiles.length} proposed file(s) declared explicitly before model invocation.`
          : 'HTTP 422 MANIFEST_REQUIRED_NO_ADMISSION — tasks missing proposedFiles rejected.',
    },
    {
      gateId: 'GATE-3-PROOF2-CLOSURE',
      title: 'Gate 3 · Proof-2 Mathematical Closure (1..5 Files, 1 Subsystem)',
      verdict: bv?.boundaryValid
        ? 'PASSED'
        : admittedViaDecompose
          ? 'AUTO_DECOMPOSED'
          : 'BLOCKED',
      detail: bv?.boundaryValid
        ? `BoundaryValid(M)=true (${bv.fileCount}/5 files in single subsystem "${bv.subsystems[0] ?? 'root'}").`
        : admittedViaDecompose
          ? `Multi-subsystem prompt automatically split into ${decomposedChildLanes.length} compliant child lanes (${decomposedChildLanes.map((l) => l.laneId).join(', ')}) at 0 wasted tokens.`
          : bv?.summary ?? 'Manifest missing or violates 1..5 unguarded single-subsystem law.',
    },
    {
      gateId: 'GATE-4-BASE-SCOPE',
      title: 'Gate 4 · Pinned Base SHA & Worktree Jail',
      verdict:
        baseDecision.failedGates.includes('BASE_INADMISSIBLE_NO_ADMISSION') ||
        baseDecision.failedGates.includes('RUNTIME_SCOPE_ESCAPE')
          ? 'BLOCKED'
          : 'PASSED',
      detail:
        baseDecision.scopeEscapeFiles.length > 0
          ? `HTTP 422 RUNTIME_SCOPE_ESCAPE: ${baseDecision.scopeEscapeFiles.join(', ')}`
          : baseDecision.failedGates.includes('BASE_INADMISSIBLE_NO_ADMISSION')
            ? 'HTTP 422 BASE_INADMISSIBLE_NO_ADMISSION — expectedBaseSha !== observedBaseSha.'
            : 'Worktree base SHA pinned and post-execution scope contained within manifest.',
    },
    {
      gateId: 'GATE-5-6-HOST-SHIELD',
      title: 'Gates 5 & 6 · Live Outside-In Host Shield (R_ZAI_01_MEASURED_HOSTS)',
      verdict: baseDecision.blockedComponents.length === 0 ? 'PASSED' : 'BLOCKED',
      detail:
        baseDecision.blockedComponents.length === 0
          ? targetHosts.length > 0
            ? `All ${targetHosts.length} target host(s) verified MEASURED_OK (${targetHosts.join(', ')}).`
            : 'Zero dead/ghost external hosts targeted.'
          : `HTTP 422 COMPONENT_UNPROBED_NO_ADMISSION: ${baseDecision.blockedComponents
              .map((c) => `${c.componentId} (${c.status})`)
              .join('; ')}`,
    },
    {
      gateId: 'GATE-7-ANTI-CONFUSION',
      title: 'Anti-Confusion Ledger · Retired OKE / LiteLLM Tombstone Gate',
      verdict: ghostViolations.length === 0 ? 'PASSED' : 'BLOCKED',
      detail:
        ghostViolations.length === 0
          ? '0 retired OKE (193.123.184.22 / oke-direct) or LiteLLM (:4000–:4002) ghosts referenced.'
          : `HTTP 422 ANTI_CONFUSION_RETIRED_GHOST_BLOCKED: ${ghostViolations
              .map((v) => `${v.domain}: ${v.matchedRetiredGhost}`)
              .join(' | ')}`,
    },
  ];

  const summary = admittedViaDecompose
    ? `AUTO-DECOMPOSED & ADMITTED (HTTP 200, 0 wasted tokens): Split ${proposedFiles.length}-file multi-subsystem manifest into ${decomposedChildLanes.map((l) => l.laneId).join(', ')} for interchangeable actuator ${actuatorModel}.`
    : admitted
      ? `ADMITTED_ZERO_GASLIGHT (HTTP 200, 0 wasted tokens): Actuator ${actuatorModel} cleared all 6 pre-token containment gates + Anti-Confusion Ledger.`
      : `REJECTED PRE-TOKEN (HTTP ${httpStatus}, 0 tokens spent): ${verdictCode}.${
        ghostViolations.length > 0
          ? ` Canonical replacement: ${ghostViolations.map((g) => g.canonicalReplacement).join(' | ')}.`
          : ''
      }`;

  return {
    law: SYSTEM_FIRST_IOC_LAW_ID,
    actuatorModel,
    workerId,
    admitted,
    httpStatus,
    verdictCode,
    tokensSpent: 0,
    gateRows,
    antiConfusionViolations: ghostViolations,
    boundaryValidation: bv,
    decomposedChildLanes,
    blockedComponents: baseDecision.blockedComponents,
    summary,
    receiptSha256: pureSha256Hex(
      `ioc:${actuatorModel}:${workerId}:${verdictCode}:${proposedFiles.join(',')}:${targetHosts.join(',')}:${ghostViolations.map((v) => v.domainId).join(',')}`
    ),
  };
}

export interface IocSandboxPreset {
  presetId: string;
  label: string;
  expectedOutcome: string;
  actuatorModel: InterchangeableActuatorId;
  workerQuadAttested: boolean;
  autoDecompose: boolean;
  taskPrompt: string;
  proposedFiles: string[];
  targetHosts: string[];
}

export const IOC_SANDBOX_PRESETS: readonly IocSandboxPreset[] = [
  {
    presetId: 'PRESET_VALID_SINGLE_LANE',
    label: '1. Canonical Single-Subsystem Admit (HTTP 200)',
    expectedOutcome: 'ADMITTED_ZERO_GASLIGHT (0 tokens wasted)',
    actuatorModel: 'glm-5.3',
    workerQuadAttested: true,
    autoDecompose: false,
    taskPrompt:
      'Route via pennyd on 127.0.0.1:4200 using PENNYD_API_KEY and update passkey verifier capability contract.',
    proposedFiles: ['catalog/capabilities.yaml', 'catalog/policies.yaml'],
    targetHosts: ['passkey.mumchimp.com'],
  },
  {
    presetId: 'PRESET_GHOST_OKE_LITELLM',
    label: '2. Retired OKE 193.x + LiteLLM :4000 Ghost Trap (HTTP 422)',
    expectedOutcome: 'BLOCKED PRE-TOKEN · ANTI_CONFUSION_RETIRED_GHOST_BLOCKED',
    actuatorModel: 'claude',
    workerQuadAttested: true,
    autoDecompose: false,
    taskPrompt:
      'Point com.estate.litellm-proxy at http://127.0.0.1:4000 with LITELLM_API_KEY and deploy to oke-direct 193.123.184.22.',
    proposedFiles: ['catalog/routing.yaml'],
    targetHosts: ['passkey.mumchimp.com'],
  },
  {
    presetId: 'PRESET_MULTI_SUBSYSTEM_8194',
    label: '3. #8194 3-Subsystem Prompt Auto-Decomposition',
    expectedOutcome: 'Splits into LANE-01-catalog, LANE-02-docs, LANE-03-tests',
    actuatorModel: 'deepseek',
    workerQuadAttested: true,
    autoDecompose: true,
    taskPrompt:
      'Update capability catalog, operator runbook docs, and boundary unit tests in one request.',
    proposedFiles: [
      'catalog/capabilities.yaml',
      'docs/runbook.md',
      'tests/test_boundary.py',
    ],
    targetHosts: ['passkey.mumchimp.com'],
  },
  {
    presetId: 'PRESET_DEAD_EXTERNAL_HOST',
    label: '4. Dead/Ghost External Host Shield (HTTP 422)',
    expectedOutcome: 'BLOCKED PRE-TOKEN · COMPONENT_UNPROBED_NO_ADMISSION',
    actuatorModel: 'kimi',
    workerQuadAttested: true,
    autoDecompose: false,
    taskPrompt: 'Dispatch live cloud traffic to llm.mumchimp.com and otto.mumchimp.com/healthz.',
    proposedFiles: ['src/router/cloudLane.ts'],
    targetHosts: ['llm.mumchimp.com', 'otto.mumchimp.com/healthz'],
  },
];

export interface SystemFirstIocStateSnapshot {
  schemaVersion: 'meridian-system-first-ioc-v1';
  generatedAtUtc: string;
  law: typeof SYSTEM_FIRST_IOC_LAW_ID;
  continuity: ZeroDependencyContinuityReport;
  actuators: readonly InterchangeableActuatorDescriptor[];
  antiConfusionLedger: readonly AntiConfusionLedgerRow[];
  measuredHosts: readonly MeasuredEstateHostRow[];
  presets: readonly IocSandboxPreset[];
  defaultEvaluation: SystemFirstIocAdmissionResult;
}

export function buildSystemFirstIocSnapshot(repoRoot: string): SystemFirstIocStateSnapshot {
  const continuity = verifyRepositoryZeroDependencyContinuity(repoRoot);
  const ghostPreset = IOC_SANDBOX_PRESETS[1];
  const defaultEvaluation = evaluateSystemFirstIocGate({
    actuatorModel: ghostPreset.actuatorModel,
    workerQuadAttested: ghostPreset.workerQuadAttested,
    autoDecompose: ghostPreset.autoDecompose,
    taskPrompt: ghostPreset.taskPrompt,
    proposedFiles: ghostPreset.proposedFiles,
    targetHosts: ghostPreset.targetHosts,
  });

  return {
    schemaVersion: 'meridian-system-first-ioc-v1',
    generatedAtUtc: new Date().toISOString(),
    law: SYSTEM_FIRST_IOC_LAW_ID,
    continuity,
    actuators: INTERCHANGEABLE_ACTUATORS,
    antiConfusionLedger: ANTI_CONFUSION_LEDGER,
    measuredHosts: R_ZAI_01_MEASURED_HOSTS,
    presets: IOC_SANDBOX_PRESETS,
    defaultEvaluation,
  };
}
