import type { FormationId } from './estateRules.ts';

// ============================================================================
// FACE & FLEET — REGISTER PROJECTOR & D.1 FALSIFIER ENGINE
// "Render the register, not the narrative. The agents are already alive;
//  you are building the projector, not the life."
// ============================================================================

export const PIPELINE_STAGES = [
  'RECEIVED',
  'PLANNED',
  'DRAFTING',
  'REVIEWING',
  'ACTUATING',
  'QUEUED',
  'VERIFIED_DONE',
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];
export type TerminalExceptionStage = 'FAILED' | 'ROLLED_BACK';
export type PacketStage = PipelineStage | TerminalExceptionStage;

export type EvidenceVerdict = 'pass' | 'fail' | 'awaiting_seal' | 'revoked';

export type PacketSurface =
  | 'MV3 Browser Symbiont'
  | 'Legion Cloud Harness'
  | 'Telegram 3327'
  | 'D1 Edge Bus'
  | 'Greenlane CI'
  | 'Optimus Verifier';

export type ActorMood = 'working' | 'celebrating' | 'failing' | 'awaiting' | 'revoked_dead';

export interface OpsEvidenceFile {
  seq: number;
  insId: string;
  title: string;
  repo: string;
  ts: string;
  surface: PacketSurface;
  formation: FormationId;
  stage: PacketStage;
  verdict: EvidenceVerdict;
  revoked: 0 | 1;
  leaseEpoch: number;
  command: string;
  exitCode: number;
  collectedCount: number | null;
  stdoutTail: string;
  ruleHits: string[];
  decision: string;
  capabilityGrants: string[];
  agentNarrationUnverified: string | null;
}

export interface OpsRegisterEntry {
  seq: number;
  insId: string;
  title: string;
  repo: string;
  ts: string;
  surface: PacketSurface;
  formation: FormationId;
  stage: PacketStage;
  verdict: EvidenceVerdict;
  revoked: 0 | 1;
  leaseEpoch: number;
  evidenceFile: string;
  evidenceSha256: string;
}

export interface ActorScriptLine {
  seq: number;
  ts: string;
  timeShort: string;
  stage: PacketStage;
  verdict: EvidenceVerdict;
  revoked: 0 | 1;
  command: string;
  exitCode: number;
  collectedCount: number | null;
  stdoutTail: string;
  ruleHits: string[];
  decision: string;
  evidenceSha256: string;
  formattedLine: string;
  agentNarrationUnverified: string | null;
}

export interface ProjectorActorState {
  insId: string;
  title: string;
  repo: string;
  surface: PacketSurface;
  formation: FormationId;
  stage: PacketStage;
  stageIndex: number; // 0..6 along the 7-stage pipeline
  verdict: EvidenceVerdict;
  revoked: 0 | 1;
  leaseEpoch: number;
  mood: ActorMood;
  speechBubble: string;
  capabilityGrants: string[];
  latestSeq: number;
  firstTs: string;
  latestTs: string;
  elapsedSec: number;
  errorCount: number;
  latestEvidenceFile: string;
  latestEvidenceSha256: string;
  scriptLines: ActorScriptLine[];
}

export interface ProjectorSceneState {
  cursorSeq: number;
  maxSeq: number;
  sceneTimestamp: string;
  totalPackets: number;
  inFlightCount: number;
  verifiedDoneCount: number;
  failingCount: number;
  revokedCount: number;
  actors: ProjectorActorState[];
}

export interface RenderedActorClaim {
  insId: string;
  seq: number;
  stage: PacketStage;
  verdict: EvidenceVerdict;
  revoked: 0 | 1;
  evidenceSha256: string;
}

export interface FalsifierDiscrepancy {
  rule: 'R1_EVIDENCE_HASH' | 'R2_VERDICT_AGREEMENT' | 'R3_COUNT_AGREEMENT';
  subject: string;
  expectedTruth: string;
  renderedClaim: string;
  detail: string;
}

export interface FalsifierReconciliationReport {
  passed: boolean;
  checkedAt: string;
  cursorSeq: number;
  r1HashAgreement: { passed: boolean; checkedFiles: number; mismatches: number };
  r2VerdictAgreement: { passed: boolean; checkedActors: number; mismatches: number };
  r3CountAgreement: { passed: boolean; registerInFlight: number; renderedInFlight: number };
  discrepancies: FalsifierDiscrepancy[];
}

export const STAGE_METADATA: Record<
  PipelineStage,
  { index: number; shortLabel: string; buildingName: string; role: string }
> = {
  RECEIVED: { index: 0, shortLabel: 'Received', buildingName: 'Intake Gate', role: 'D1 mint & Outbox firewall' },
  PLANNED: { index: 1, shortLabel: 'Planned', buildingName: 'Planning Foundry', role: '7-Gate scope & capability grant' },
  DRAFTING: { index: 2, shortLabel: 'Drafting', buildingName: 'Drafting Loom', role: 'HELM bounded patch synthesis' },
  REVIEWING: { index: 3, shortLabel: 'Reviewing', buildingName: 'Geburah Tribunal', role: 'Adversarial counterexample audit' },
  ACTUATING: { index: 4, shortLabel: 'Actuating', buildingName: 'Actuation Forge', role: 'estate_execute & test runner' },
  QUEUED: { index: 5, shortLabel: 'Queued', buildingName: 'Greenlane Queue', role: 'Optimus dual-root CI lock' },
  VERIFIED_DONE: { index: 6, shortLabel: 'Verified Done', buildingName: 'Verified Vault', role: 'Sealed merge & signed yield' },
};

export function stageToPipelineIndex(stage: PacketStage, previousStageIndex: number = 0): number {
  if (stage in STAGE_METADATA) {
    return STAGE_METADATA[stage as PipelineStage].index;
  }
  if (stage === 'FAILED') {
    return Math.max(0, Math.min(6, previousStageIndex));
  }
  // ROLLED_BACK returns toward Intake/Planning
  return Math.max(0, previousStageIndex - 1);
}

export function deriveActorMood(
  stage: PacketStage,
  verdict: EvidenceVerdict,
  revoked: 0 | 1
): ActorMood {
  if (revoked === 1 || verdict === 'revoked') return 'revoked_dead';
  if (verdict === 'fail' || stage === 'FAILED') return 'failing';
  if (verdict === 'pass' && stage === 'VERIFIED_DONE') return 'celebrating';
  if (verdict === 'awaiting_seal') return 'awaiting';
  if (verdict === 'pass') return 'working';
  return 'working';
}

function formatUtcClock(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return '00:00:00';
  return parsed.toISOString().slice(11, 19);
}

export function formatEvidenceScriptLine(
  entry: OpsRegisterEntry,
  evidence?: OpsEvidenceFile
): ActorScriptLine {
  const timeShort = formatUtcClock(entry.ts);
  const command = evidence?.command ?? `stage:${entry.stage.toLowerCase()}`;
  const exitCode = evidence?.exitCode ?? (entry.verdict === 'fail' ? 1 : 0);
  const collectedCount = evidence?.collectedCount ?? null;
  const ruleHits = evidence?.ruleHits ?? [];
  const stdoutTail = evidence?.stdoutTail ?? `${entry.stage} (${entry.verdict})`;
  const decision = evidence?.decision ?? 'awaiting next packet transition';

  const collectedSegment =
    collectedCount !== null ? ` · collected ${collectedCount}` : '';
  const verdictUpper = entry.revoked === 1 ? 'REVOKED' : entry.verdict.toUpperCase();
  const rulesSegment = ruleHits.length > 0 ? ` (${ruleHits.join(', ')})` : '';

  const formattedLine = `[seq ${entry.seq} · ${timeShort}] ${command} → exit ${exitCode}${collectedSegment} → verdict ${verdictUpper}${rulesSegment} → next: ${decision}`;

  return {
    seq: entry.seq,
    ts: entry.ts,
    timeShort,
    stage: entry.stage,
    verdict: entry.verdict,
    revoked: entry.revoked,
    command,
    exitCode,
    collectedCount,
    stdoutTail,
    ruleHits,
    decision,
    evidenceSha256: entry.evidenceSha256,
    formattedLine,
    agentNarrationUnverified: evidence?.agentNarrationUnverified ?? null,
  };
}

export function isPacketInFlight(stage: PacketStage, revoked: 0 | 1): boolean {
  if (revoked === 1) return false;
  return stage !== 'VERIFIED_DONE' && stage !== 'FAILED' && stage !== 'ROLLED_BACK';
}

/**
 * Pure Actor Model Reducer (~200 LOC):
 * Projects `.ops/register.jsonl` + `.ops/evidence/*.json` into deterministic scene state.
 * Idempotent on duplicate `seq` frames; supports exact historical replay via `scrubSeq`.
 */
export function reduceRegisterToScene(
  registerEntries: readonly OpsRegisterEntry[],
  evidenceBySeq: Readonly<Record<number, OpsEvidenceFile>>,
  options?: { scrubSeq?: number | null }
): ProjectorSceneState {
  // 1. Idempotent deduplication by monotonic `seq`
  const bySeq = new Map<number, OpsRegisterEntry>();
  for (const entry of registerEntries) {
    if (entry && typeof entry.seq === 'number' && Number.isFinite(entry.seq)) {
      if (!bySeq.has(entry.seq)) {
        bySeq.set(entry.seq, entry);
      }
    }
  }

  const orderedAll = [...bySeq.values()].sort((a, b) => a.seq - b.seq);
  const maxSeq = orderedAll.length > 0 ? orderedAll[orderedAll.length - 1].seq : 0;
  const cursorSeq =
    typeof options?.scrubSeq === 'number' && Number.isFinite(options.scrubSeq)
      ? Math.max(1, Math.min(maxSeq, Math.floor(options.scrubSeq)))
      : maxSeq;

  const visibleEntries = orderedAll.filter((e) => e.seq <= cursorSeq);
  const sceneTimestamp =
    visibleEntries.length > 0
      ? visibleEntries[visibleEntries.length - 1].ts
      : new Date(0).toISOString();

  // 2. Fold events per INS-XXXXX packet in strict seq order
  const actorMap = new Map<string, ProjectorActorState>();

  for (const entry of visibleEntries) {
    const ev = evidenceBySeq[entry.seq];
    const scriptLine = formatEvidenceScriptLine(entry, ev);
    const existing = actorMap.get(entry.insId);

    const nextStageIdx = stageToPipelineIndex(entry.stage, existing?.stageIndex ?? 0);
    const effectiveRevoked: 0 | 1 = existing?.revoked === 1 || entry.revoked === 1 ? 1 : 0;
    const effectiveVerdict: EvidenceVerdict =
      effectiveRevoked === 1 ? 'revoked' : entry.verdict;
    const mood = deriveActorMood(entry.stage, effectiveVerdict, effectiveRevoked);

    const ruleSummary =
      scriptLine.ruleHits.length > 0 ? ` [${scriptLine.ruleHits[0]}]` : '';
    const speechBubble =
      effectiveRevoked === 1
        ? `LEASE REVOKED (epoch ${entry.leaseEpoch}) — AFTER UPDATE trigger halted actor`
        : `${scriptLine.stdoutTail}${ruleSummary}`;

    const firstTs = existing ? existing.firstTs : entry.ts;
    const elapsedMs = Math.max(0, Date.parse(entry.ts) - Date.parse(firstTs));
    const elapsedSec = Number.isFinite(elapsedMs) ? Math.round(elapsedMs / 1000) : 0;
    const errorCount = (existing?.errorCount ?? 0) + (effectiveVerdict === 'fail' ? 1 : 0);

    const updated: ProjectorActorState = {
      insId: entry.insId,
      title: entry.title || ev?.title || entry.insId,
      repo: entry.repo || ev?.repo || 'chidionyema/idp',
      surface: entry.surface,
      formation: entry.formation,
      stage: entry.stage,
      stageIndex: nextStageIdx,
      verdict: effectiveVerdict,
      revoked: effectiveRevoked,
      leaseEpoch: entry.leaseEpoch,
      mood,
      speechBubble,
      capabilityGrants: ev?.capabilityGrants ?? existing?.capabilityGrants ?? ['fs:read'],
      latestSeq: entry.seq,
      firstTs,
      latestTs: entry.ts,
      elapsedSec,
      errorCount,
      latestEvidenceFile: entry.evidenceFile,
      latestEvidenceSha256: entry.evidenceSha256,
      scriptLines: existing ? [...existing.scriptLines, scriptLine] : [scriptLine],
    };

    actorMap.set(entry.insId, updated);
  }

  const actors = [...actorMap.values()].sort((a, b) => b.latestSeq - a.latestSeq);
  const inFlightCount = actors.filter((a) => isPacketInFlight(a.stage, a.revoked)).length;
  const verifiedDoneCount = actors.filter(
    (a) => a.stage === 'VERIFIED_DONE' && a.revoked === 0 && a.verdict === 'pass'
  ).length;
  const failingCount = actors.filter((a) => a.verdict === 'fail' && a.revoked === 0).length;
  const revokedCount = actors.filter((a) => a.revoked === 1).length;

  return {
    cursorSeq,
    maxSeq,
    sceneTimestamp,
    totalPackets: actors.length,
    inFlightCount,
    verifiedDoneCount,
    failingCount,
    revokedCount,
    actors,
  };
}

/**
 * D.1 Falsifier & Continuous Reconciliation Gate (R1 + R2 + R3):
 * Verifies that every rendered pixel claim agrees with `.ops/register.jsonl`
 * and raw `.ops/evidence/*.json` SHA-256 digests on disk.
 */
export function reconcileSceneAgainstRegister(params: {
  cursorSeq?: number | null;
  renderedInFlightCount: number;
  renderedActors: readonly RenderedActorClaim[];
  diskRegisterEntries: readonly OpsRegisterEntry[];
  diskEvidenceBySeq: Readonly<Record<number, OpsEvidenceFile>>;
  diskSha256BySeq: Readonly<Record<number, string>>;
  nowIso?: string;
}): FalsifierReconciliationReport {
  const truthScene = reduceRegisterToScene(
    params.diskRegisterEntries,
    params.diskEvidenceBySeq,
    { scrubSeq: params.cursorSeq ?? null }
  );

  const discrepancies: FalsifierDiscrepancy[] = [];
  let r1Mismatches = 0;
  let r2Mismatches = 0;

  const truthByInsId = new Map(truthScene.actors.map((a) => [a.insId, a]));

  for (const claim of params.renderedActors) {
    const truthActor = truthByInsId.get(claim.insId);
    if (!truthActor) {
      r1Mismatches++;
      discrepancies.push({
        rule: 'R1_EVIDENCE_HASH',
        subject: claim.insId,
        expectedTruth: 'ABSENT_FROM_REGISTER',
        renderedClaim: `seq ${claim.seq} (${claim.evidenceSha256.slice(0, 12)})`,
        detail: `Actor ${claim.insId} is rendered on screen but has zero entries in .ops/register.jsonl up to seq ${truthScene.cursorSeq}.`,
      });
      continue;
    }

    // R1: Re-read disk SHA-256 of `.ops/evidence/*.json` vs rendered frame SHA-256
    const diskHash = params.diskSha256BySeq[truthActor.latestSeq] ?? truthActor.latestEvidenceSha256;
    if (claim.evidenceSha256 !== diskHash || claim.seq !== truthActor.latestSeq) {
      r1Mismatches++;
      discrepancies.push({
        rule: 'R1_EVIDENCE_HASH',
        subject: `${claim.insId} @ seq ${truthActor.latestSeq}`,
        expectedTruth: `${diskHash.slice(0, 16)}… (seq ${truthActor.latestSeq})`,
        renderedClaim: `${claim.evidenceSha256.slice(0, 16)}… (seq ${claim.seq})`,
        detail: `Rendered frame hash/seq for ${claim.insId} does not match .ops/evidence file digest on disk.`,
      });
    }

    // R2: Visual verdict color/state must strictly equal `evidence.verdict`
    const diskEvidence = params.diskEvidenceBySeq[truthActor.latestSeq];
    const authoritativeVerdict: EvidenceVerdict =
      truthActor.revoked === 1
        ? 'revoked'
        : diskEvidence?.verdict ?? truthActor.verdict;

    if (claim.verdict !== authoritativeVerdict || claim.revoked !== truthActor.revoked) {
      r2Mismatches++;
      discrepancies.push({
        rule: 'R2_VERDICT_AGREEMENT',
        subject: `${claim.insId} @ seq ${truthActor.latestSeq}`,
        expectedTruth: `verdict=${authoritativeVerdict} (revoked=${truthActor.revoked})`,
        renderedClaim: `verdict=${claim.verdict} (revoked=${claim.revoked})`,
        detail: `Renderer claimed "${claim.verdict}" for ${claim.insId}, but signed evidence record specifies "${authoritativeVerdict}". Visual optimism refused.`,
      });
    }
  }

  // Also detect omitted truth actors
  for (const truthActor of truthScene.actors) {
    const wasRendered = params.renderedActors.some((c) => c.insId === truthActor.insId);
    if (!wasRendered) {
      r1Mismatches++;
      discrepancies.push({
        rule: 'R1_EVIDENCE_HASH',
        subject: truthActor.insId,
        expectedTruth: `present @ seq ${truthActor.latestSeq}`,
        renderedClaim: 'OMITTED_FROM_SCENE',
        detail: `Register actor ${truthActor.insId} exists at seq ${truthActor.latestSeq} but was omitted by renderer.`,
      });
    }
  }

  // R3: "N packets in flight" must equal `SELECT count(*) FROM packets WHERE stage NOT IN ('VERIFIED_DONE','FAILED','ROLLED_BACK') AND revoked=0`
  const r3Passed = params.renderedInFlightCount === truthScene.inFlightCount;
  if (!r3Passed) {
    discrepancies.push({
      rule: 'R3_COUNT_AGREEMENT',
      subject: 'in_flight_packet_count',
      expectedTruth: `${truthScene.inFlightCount} packets in flight`,
      renderedClaim: `${params.renderedInFlightCount} packets in flight`,
      detail: `HUD count (${params.renderedInFlightCount}) drifted from register query count (${truthScene.inFlightCount}).`,
    });
  }

  const r1Passed = r1Mismatches === 0;
  const r2Passed = r2Mismatches === 0;

  return {
    passed: r1Passed && r2Passed && r3Passed,
    checkedAt: params.nowIso ?? new Date().toISOString(),
    cursorSeq: truthScene.cursorSeq,
    r1HashAgreement: {
      passed: r1Passed,
      checkedFiles: truthScene.actors.length,
      mismatches: r1Mismatches,
    },
    r2VerdictAgreement: {
      passed: r2Passed,
      checkedActors: truthScene.actors.length,
      mismatches: r2Mismatches,
    },
    r3CountAgreement: {
      passed: r3Passed,
      registerInFlight: truthScene.inFlightCount,
      renderedInFlight: params.renderedInFlightCount,
    },
    discrepancies,
  };
}

/**
 * Telegram 3327 Pocket Cockpit Projection:
 * Emits the exact phone-sized pinned status message from the same pure Actor Model reducer.
 */
export function projectTelegram3327PinnedMessage(
  scene: ProjectorSceneState,
  reconciliation?: FalsifierReconciliationReport | null
): string {
  const header = `GENESIS 3327 PIN · SEQ #${scene.cursorSeq}/${scene.maxSeq}`;
  const counts = `IN-FLIGHT: ${scene.inFlightCount} · DONE: ${scene.verifiedDoneCount} · FAIL: ${scene.failingCount} · REVOKED: ${scene.revokedCount}`;
  const seal = reconciliation
    ? reconciliation.passed
      ? `RECONCILE R1-R3: VERIFIED (${reconciliation.r1HashAgreement.checkedFiles} hashes)`
      : `RECONCILE R1-R3: DRIFT REFUSED (${reconciliation.discrepancies.length} mismatch)`
    : 'RECONCILE R1-R3: READY';

  const rows = scene.actors.slice(0, 6).map((actor) => {
    const tag =
      actor.revoked === 1
        ? '[REVOKED]'
        : actor.verdict === 'pass'
          ? '[PASS]'
          : actor.verdict === 'fail'
            ? '[FAIL]'
            : '[WAIT]';
    const lastLine = actor.scriptLines[actor.scriptLines.length - 1];
    const rule = lastLine?.ruleHits[0] ? ` · ${lastLine.ruleHits[0]}` : '';
    return `${tag} ${actor.insId} → ${actor.stage} (${actor.formation})${rule}`;
  });

  return [header, counts, seal, '----------------------------------------', ...rows].join('\n');
}
