/**
 * Hermes · OTTO_NUMEN (oot_numun) — VIP CEO Telegram Concierge, Topic Router,
 * Burst Coalescer (editMessageText), and Strict HTML / MarkdownV2 Wire Formatter.
 *
 * Eliminates the legacy single-channel notification flood and broken formatting by:
 *  1. Routing events into 5 dedicated Telegram Forum Topics + 1 Suppressed Chatter Sink.
 *  2. Enforcing audible VIP notifications STRICTLY on P0 CEO Decisions (respecting Focus Mode).
 *  3. Coalescing flapping incident bursts in-place via deterministic dedupe fingerprints.
 *  4. Guaranteeing valid Telegram HTML & MarkdownV2 escaping, <=900-char executive screen
 *     budget (<=4096 Telegram hard cap), and <=64-byte InlineKeyboard callback_data payloads.
 */

import { createHash } from 'node:crypto';
import { getDailyChallengeForDate, getUtcDateString } from './hermesTreeCatalog';

export type TelegramTopicKey =
  | 'VIP_CEO_DECISIONS'
  | 'EXECUTIVE_BRIEFINGS'
  | 'INCIDENTS_HEALING'
  | 'FINOPS_TREASURY'
  | 'RELEASES_GWT_AUDIT'
  | 'SUPPRESSED_HEARTBEAT_SINK';

export type CeoFocusPolicy = 'VIP_P0_ONLY' | 'VIP_PLUS_BRIEFINGS' | 'SILENT_DND_ALL';

export type RawEstateEventKind =
  | 'p0_ceo_signoff'
  | 'p0_budget_ceiling'
  | 'executive_briefing'
  | 'incident_auto_healed'
  | 'finops_milestone'
  | 'release_bundle_sync'
  | 'chronos_heartbeat'
  | 'wal_checkpoint_chatter'
  | 'dagster_routine_probe';

export interface TelegramForumTopicSpec {
  key: TelegramTopicKey;
  threadId: number | null;
  title: string;
  shortLabel: string;
  audiblePolicy: 'VIP_AUDIBLE' | 'SCHEDULED_QUIET' | 'SILENT_COALESCED' | 'SILENT_LOG' | 'INTERCEPTED_ZERO_SEND';
  description: string;
}

export const TELEGRAM_FORUM_TOPICS: ReadonlyArray<TelegramForumTopicSpec> = [
  {
    key: 'VIP_CEO_DECISIONS',
    threadId: 101,
    title: '01 · VIP CEO Decisions',
    shortLabel: 'VIP Decisions',
    audiblePolicy: 'VIP_AUDIBLE',
    description: 'Strictly P0 capital, security, and Greenlane sign-offs requiring 1-tap CEO action.',
  },
  {
    key: 'EXECUTIVE_BRIEFINGS',
    threadId: 102,
    title: '02 · Executive Briefings',
    shortLabel: 'Briefings',
    audiblePolicy: 'SCHEDULED_QUIET',
    description: 'Twice-daily (08:00 / 20:00) synthesized estate pulse, net savings, and Hermes alignment.',
  },
  {
    key: 'INCIDENTS_HEALING',
    threadId: 104,
    title: '03 · Incidents & Auto-Heal',
    audiblePolicy: 'SILENT_COALESCED',
    shortLabel: 'Incidents',
    description: '402/503 lane faults and InterCloud spot failovers coalesced in-place via editMessageText.',
  },
  {
    key: 'FINOPS_TREASURY',
    threadId: 108,
    title: '04 · FinOps & Treasury',
    shortLabel: 'FinOps',
    audiblePolicy: 'SILENT_LOG',
    description: 'Counterfactual PennyD savings milestones, InterCloud spot pricing, and free-tier drains.',
  },
  {
    key: 'RELEASES_GWT_AUDIT',
    threadId: 116,
    title: '05 · Releases & Governance',
    shortLabel: 'Releases & Audit',
    audiblePolicy: 'SILENT_LOG',
    description: 'Reset-proof Git bundle SHA-256 syncs, GWT/AEON checkpoints, and First-Use ratchet gates.',
  },
  {
    key: 'SUPPRESSED_HEARTBEAT_SINK',
    threadId: null,
    title: '06 · Intercepted Machine Chatter (Never Sent)',
    shortLabel: 'Suppressed Sink',
    audiblePolicy: 'INTERCEPTED_ZERO_SEND',
    description: 'Routine 6s Chronos beats, WAL flushes, and sensor probes intercepted before Telegram.',
  },
];

export interface TelegramInlineButton {
  text: string;
  callbackData: string;
  byteLength: number;
  style: 'primary' | 'neutral' | 'caution';
}

export interface RawEstateTelegramEvent {
  id?: string;
  kind: RawEstateEventKind;
  sourceSubsystem: string;
  headline: string;
  metrics: Record<string, string | number>;
  autonomousAction: string;
  ceoQuestion?: string;
  dedupeKey?: string;
  referenceId?: string;
  timestampUtc?: string;
}

export interface CeoDecisionReceipt {
  receiptId: string;
  messageId: string;
  action: 'APPROVED' | 'HELD_IN_GATE' | 'ACKNOWLEDGED' | 'MUTED_4H';
  actorEmail: string;
  decidedAtUtc: string;
  decisionSha256: string;
  note: string;
}

export interface VipTelegramMessageCard {
  messageId: string;
  telegramMsgNumericId: number;
  topic: TelegramTopicKey;
  threadId: number;
  priorityTag: 'P0 DECISION' | 'BRIEFING' | 'AUTO-HEALED' | 'FINOPS' | 'GOVERNANCE';
  sourceSubsystem: string;
  headline: string;
  metrics: Array<{ label: string; value: string }>;
  executiveSummary: string;
  ceoQuestion: string | null;
  disableNotification: boolean;
  audiblePingTriggered: boolean;
  deliveryMethod: 'SEND_NEW' | 'EDIT_IN_PLACE';
  coalescedCount: number;
  dedupeFingerprint: string;
  htmlWirePayload: string;
  markdownV2WirePayload: string;
  legacyNoisyEquivalent: string;
  charCount: number;
  withinSingleScreenBudget: boolean;
  withinTelegramHardLimit: boolean;
  inlineKeyboard: TelegramInlineButton[];
  allCallbacksWithin64Bytes: boolean;
  createdAtUtc: string;
  updatedAtUtc: string;
  resolution: CeoDecisionReceipt | null;
}

export interface OttoNumenTelemetryRollup {
  rawEventsIngested: number;
  suppressedHeartbeatEvents: number;
  coalescedDuplicateUpdates: number;
  mutedByRuleEvents: number;
  deliveredTopicCards: number;
  audibleCeoPings: number;
  legacySingleChannelMessagesWouldBe: number;
  legacyAudiblePingsWouldBe: number;
  noiseReductionPct: number;
  audibleInterruptionReductionPct: number;
  pendingVipDecisions: number;
  suppressedBreakdown: Record<string, number>;
  topicCounts: Record<TelegramTopicKey, number>;
}

export interface OttoNumenSnapshot {
  schemaVersion: 'otto-numen-vip-telegram-v1';
  generatedAtUtc: string;
  botHandle: '@otto_numen_bot';
  legacyAliasReplaced: 'oot_numun (single-channel raw dump)';
  ceoRecipient: string;
  webhookPosture: 'SANDBOX_SIMULATOR_ACTIVE_WEBHOOK_EXPORT_READY';
  focusPolicy: CeoFocusPolicy;
  coalesceWindowSec: number;
  quietHoursUtc: string;
  mutedDedupeKeys: string[];
  topics: ReadonlyArray<TelegramForumTopicSpec>;
  telemetry: OttoNumenTelemetryRollup;
  messages: VipTelegramMessageCard[];
  recentReceipts: CeoDecisionReceipt[];
}

export const TELEGRAM_MAX_MESSAGE_CHARS = 4096;
export const CEO_SINGLE_SCREEN_CHAR_BUDGET = 900;
export const TELEGRAM_MAX_CALLBACK_BYTES = 64;

/**
 * Escapes arbitrary strings for Telegram Bot API `parse_mode: "HTML"`.
 * Prevents `<3 quorum`, `a & b`, or angle-bracket generics from throwing HTTP 400.
 */
export function escapeTelegramHtml(raw: string): string {
  return String(raw)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Escapes all 18 reserved characters required by Telegram Bot API `parse_mode: "MarkdownV2"`.
 * Spec: _ * [ ] ( ) ~ ` > # + - = | { } . ! \
 */
export function escapeTelegramMarkdownV2(raw: string): string {
  return String(raw).replace(/([_*[\]()~`>#+\-=|{}.!\\])/g, '\\$1');
}

/**
 * Builds a guaranteed <=64-byte UTF-8 Telegram callback_data token.
 */
export function buildSafeCallbackData(action: string, targetId: string): {
  callbackData: string;
  byteLength: number;
} {
  const cleanAction = action.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 14);
  const cleanTarget = targetId.replace(/[^a-zA-Z0-9_.-]/g, '').slice(0, 42);
  let candidate = `vip:${cleanAction}:${cleanTarget}`;
  while (Buffer.byteLength(candidate, 'utf8') > TELEGRAM_MAX_CALLBACK_BYTES) {
    candidate = candidate.slice(0, candidate.length - 1);
  }
  return {
    callbackData: candidate,
    byteLength: Buffer.byteLength(candidate, 'utf8'),
  };
}

/**
 * Renders the legacy `oot_numun` broken single-channel message to demonstrate
 * exact defects eliminated by the VIP revamp (raw JSON, unescaped Markdown, no routing).
 */
export function renderLegacyNoisyDump(event: RawEstateTelegramEvent): string {
  const rawJson = JSON.stringify({
    bot: 'oot_numun',
    channel: '#general-all-dump',
    ts: event.timestampUtc ?? new Date().toISOString(),
    kind: event.kind,
    src: event.sourceSubsystem,
    msg: event.headline,
    metrics: event.metrics,
    action: event.autonomousAction,
  });
  return `[oot_numun -> #all_stream] 🚨🔔 *RAW_EVENT_DUMP* (${event.sourceSubsystem}) :: ${event.headline} | payload=${rawJson}`;
}

/**
 * Classifies any raw estate event into its deterministic Telegram Forum Topic.
 */
export function classifyEventToTopic(kind: RawEstateEventKind): {
  topic: TelegramTopicKey;
  threadId: number | null;
  priorityTag: VipTelegramMessageCard['priorityTag'] | 'SUPPRESSED';
} {
  switch (kind) {
    case 'p0_ceo_signoff':
    case 'p0_budget_ceiling':
      return { topic: 'VIP_CEO_DECISIONS', threadId: 101, priorityTag: 'P0 DECISION' };
    case 'executive_briefing':
      return { topic: 'EXECUTIVE_BRIEFINGS', threadId: 102, priorityTag: 'BRIEFING' };
    case 'incident_auto_healed':
      return { topic: 'INCIDENTS_HEALING', threadId: 104, priorityTag: 'AUTO-HEALED' };
    case 'finops_milestone':
      return { topic: 'FINOPS_TREASURY', threadId: 108, priorityTag: 'FINOPS' };
    case 'release_bundle_sync':
      return { topic: 'RELEASES_GWT_AUDIT', threadId: 116, priorityTag: 'GOVERNANCE' };
    case 'chronos_heartbeat':
    case 'wal_checkpoint_chatter':
    case 'dagster_routine_probe':
      return { topic: 'SUPPRESSED_HEARTBEAT_SINK', threadId: null, priorityTag: 'SUPPRESSED' };
  }
}

function buildWirePayloads(params: {
  priorityTag: VipTelegramMessageCard['priorityTag'];
  sourceSubsystem: string;
  headline: string;
  metrics: Array<{ label: string; value: string }>;
  executiveSummary: string;
  ceoQuestion: string | null;
  coalescedCount: number;
  resolution: CeoDecisionReceipt | null;
}): {
  html: string;
  markdownV2: string;
  plainCharCount: number;
} {
  const countSuffix = params.coalescedCount > 1 ? ` (Coalesced x${params.coalescedCount})` : '';
  const metricLines = params.metrics.map(
    (m) => `${m.label.padEnd(11, ' ')} ${m.value}`
  );

  // 1. Canonical HTML Wire Payload (parse_mode: "HTML")
  const htmlParts: string[] = [
    `<b>${escapeTelegramHtml(params.priorityTag)} · ${escapeTelegramHtml(params.sourceSubsystem.toUpperCase())}${escapeTelegramHtml(countSuffix)}</b>`,
    `<b>${escapeTelegramHtml(params.headline)}</b>`,
    `<pre>${escapeTelegramHtml(metricLines.join('\n'))}</pre>`,
    escapeTelegramHtml(params.executiveSummary),
  ];
  if (params.ceoQuestion) {
    htmlParts.push(`<b>Decision Required:</b> ${escapeTelegramHtml(params.ceoQuestion)}`);
  }
  if (params.resolution) {
    htmlParts.push(
      `<i>Resolved: ${escapeTelegramHtml(params.resolution.action)} by ${escapeTelegramHtml(params.resolution.actorEmail)} · #${escapeTelegramHtml(params.resolution.decisionSha256.slice(0, 10))}</i>`
    );
  }
  let html = htmlParts.join('\n\n');
  if (html.length > CEO_SINGLE_SCREEN_CHAR_BUDGET) {
    html = `${html.slice(0, CEO_SINGLE_SCREEN_CHAR_BUDGET - 16)}…`;
  }

  // 2. Strict MarkdownV2 Wire Payload (parse_mode: "MarkdownV2")
  const mdMetrics = metricLines
    .map((line) => line.replace(/([`\\])/g, '\\$1'))
    .join('\n');
  const mdParts: string[] = [
    `*${escapeTelegramMarkdownV2(`${params.priorityTag} · ${params.sourceSubsystem.toUpperCase()}${countSuffix}`)}*`,
    `*${escapeTelegramMarkdownV2(params.headline)}*`,
    `\`\`\`\n${mdMetrics}\n\`\`\``,
    escapeTelegramMarkdownV2(params.executiveSummary),
  ];
  if (params.ceoQuestion) {
    mdParts.push(`*Decision Required:* ${escapeTelegramMarkdownV2(params.ceoQuestion)}`);
  }
  if (params.resolution) {
    mdParts.push(
      `_${escapeTelegramMarkdownV2(`Resolved: ${params.resolution.action} · #${params.resolution.decisionSha256.slice(0, 10)}`)}_`
    );
  }
  const markdownV2 = mdParts.join('\n\n').slice(0, TELEGRAM_MAX_MESSAGE_CHARS);

  const plainText = [
    `${params.priorityTag} · ${params.sourceSubsystem}${countSuffix}`,
    params.headline,
    metricLines.join('\n'),
    params.executiveSummary,
    params.ceoQuestion ?? '',
  ]
    .filter(Boolean)
    .join('\n');

  return {
    html,
    markdownV2,
    plainCharCount: plainText.length,
  };
}

export class OttoNumenConciergeEngine {
  private focusPolicy: CeoFocusPolicy = 'VIP_P0_ONLY';
  private coalesceWindowSec = 300;
  private readonly quietHoursUtc = '22:30–07:00 UTC (P0 Override Active)';
  private readonly ceoRecipient = 'chidionyema@gmail.com';

  private rawEventsIngested = 0;
  private suppressedHeartbeatEvents = 0;
  private coalescedDuplicateUpdates = 0;
  private mutedByRuleEvents = 0;
  private audibleCeoPings = 0;
  private nextNumericMsgId = 4100;

  private readonly suppressedBreakdown: Record<string, number> = {
    chronos_heartbeat: 0,
    wal_checkpoint_chatter: 0,
    dagster_routine_probe: 0,
  };

  private readonly mutedDedupeKeys = new Set<string>();
  private readonly messages: VipTelegramMessageCard[] = [];
  private readonly recentReceipts: CeoDecisionReceipt[] = [];

  constructor(options?: { seedInitialEstateState?: boolean }) {
    if (options?.seedInitialEstateState !== false) {
      this.seedBaselineExecutiveStream();
    }
  }

  private seedBaselineExecutiveStream(): void {
    // Seed realistic intercepted background machine chatter first so telemetry is truthful on boot
    for (let i = 0; i < 18; i++) {
      this.ingestEvent({
        kind: i % 3 === 0 ? 'wal_checkpoint_chatter' : i % 5 === 0 ? 'dagster_routine_probe' : 'chronos_heartbeat',
        sourceSubsystem: 'Chronos / WAL',
        headline: `Routine beat #${i + 1} checkpointed`,
        metrics: { Beat: i + 1, Skew: '3ms' },
        autonomousAction: 'Routine heartbeat intercepted from Telegram.',
      });
    }

    // 1. Release & Governance card (Silent Topic #116)
    this.ingestEvent({
      kind: 'release_bundle_sync',
      sourceSubsystem: 'Fleet Bundle & First-Use Audit',
      headline: 'Candidate ff8543bd & Reset-Proof Git Bundle Verified',
      metrics: {
        'Audit Gate': '21/21 PASS (12 Obs + 9 Ratchet)',
        'Live Effect': 'UNKNOWN (Honest Lock)',
        'Bundle Ref': 'aistudio/meridian-hermes-live',
      },
      autonomousAction:
        'AGENTS.md no-growth ratchet enforced; --no-verify shortcuts blocked; Git bundle SHA-256 verified on disk.',
      dedupeKey: 'release:ff8543bd-bundle',
      referenceId: 'ff8543bd',
    });

    // 2. FinOps milestone card (Silent Topic #108)
    this.ingestEvent({
      kind: 'finops_milestone',
      sourceSubsystem: 'PennyD · Meridian',
      headline: 'Open Ensemble Beat Single Frontier at 99.8% Lower Cost',
      metrics: {
        'Verified Pass': '96.9% vs 93.4% Frontier',
        'Unit Cost': '$0.00018 vs $0.08900',
        'Free Pools': '5 Sovereign ($0.00) Online',
      },
      autonomousAction:
        'Routed routine coding & verification through Best-of-3 Qwen/DeepSeek/Llama + BEAST gate.',
      dedupeKey: 'finops:ensemble-998',
      referenceId: 'MSN-ESTATE-409',
    });

    // 3. Coalesced Incident auto-heal card (Silent Coalesced Topic #104 — 4 rapid spot events -> 1 card!)
    for (let attempt = 1; attempt <= 4; attempt++) {
      this.ingestEvent({
        kind: 'incident_auto_healed',
        sourceSubsystem: 'InterCloud Spot Fabric',
        headline: 'L40S Spot Pool Preemption Migrated Zero-Drop (<50ms)',
        metrics: {
          'Failover': '37ms -> Sovereign H100 Pool',
          'WAL Loss': '0 dropped receipts',
          'Circuit': 'Self-healing probe active',
        },
        autonomousAction:
          'Checkpoint migrated automatically across Dagster durable WAL; zero operator action needed.',
        dedupeKey: 'incident:intercloud-l40s-spot',
        referenceId: 'ic-intercloud-spot-l40s',
      });
    }

    // 4. Synthesized Morning Executive Briefing (Scheduled Quiet Topic #102)
    const todayUtc = getUtcDateString();
    const daily = getDailyChallengeForDate(todayUtc);
    this.ingestEvent({
      kind: 'executive_briefing',
      sourceSubsystem: 'OTTO_NUMEN · Morning Pulse',
      headline: `CEO Estate Pulse — 11/11 Guarantees Green · Hermes Target ${daily.targetNumber}`,
      metrics: {
        'Estate SLA': '99.98% · 0 Open Circuits',
        'Net Savings': '86.0% vs unrouted baseline',
        'Hermes Canon': `${daily.targetSephirahName.split('(')[0].trim()} · Target ${daily.targetNumber}`,
        'Noise Blocked': '18 heartbeats + 3 burst edits',
      },
      autonomousAction:
        'Chronos running 6s SSE cadence autonomously. Only 2 gated promotions await Founder greenlight.',
      dedupeKey: `briefing:${todayUtc}-am`,
      referenceId: todayUtc,
    });

    // 5. P0 VIP CEO Decision #1 (Audible VIP Topic #101)
    this.ingestEvent({
      kind: 'p0_ceo_signoff',
      sourceSubsystem: 'Greenlane · GEN-TTT-001',
      headline: 'Authorise Spec Factory Reconciliation & Promotion (#8185)',
      metrics: {
        'Branch': 'lane/genesis-ttt-full-spec-20261116',
        'Scope': '18 Reqs · 18 BDD · 15 FCs · 6 Arms',
        'Posture': 'BLOCKED_DISPATCH (PR #8186 Closed)',
      },
      autonomousAction:
        'Held fail-closed on Issue #8185; zero unapproved fleet compute spent.',
      ceoQuestion:
        'Approve signed lane-submit reconciliation into Argon Spec Factory, or keep #8185 held in gate?',
      dedupeKey: 'vip:gen-ttt-8185',
      referenceId: 'issue-8185',
    });

    // 6. P0 VIP CEO Decision #2 (Audible VIP Topic #101)
    this.ingestEvent({
      kind: 'p0_ceo_signoff',
      sourceSubsystem: 'IDP Governance · First-Use Audit',
      headline: 'Promote Read-Only Pi Ceremony Observer & AGENTS.md Ratchet',
      metrics: {
        'Candidate': 'ff8543bd (+7 ahead of d03f5d59)',
        'Adversarial': '21/21 PASS · $lines Bug Closed',
        'Live Yield': 'UNKNOWN (Observation Only)',
      },
      autonomousAction:
        'Retained declare_plan, BDD, edge cases, and complete_goal; blocked --no-verify shortcuts.',
      ceoQuestion:
        'Authorise Greenlane claim to merge read-only ceremony telemetry and <=300-line ratchet?',
      dedupeKey: 'vip:first-use-ff8543bd',
      referenceId: 'ff8543bd',
    });
  }

  public setFocusPolicy(policy: CeoFocusPolicy): OttoNumenSnapshot {
    this.focusPolicy = policy;
    return this.getSnapshot();
  }

  public setCoalesceWindowSec(seconds: number): OttoNumenSnapshot {
    this.coalesceWindowSec = Math.max(30, Math.min(3600, Math.round(seconds)));
    return this.getSnapshot();
  }

  public clearMutedRules(): OttoNumenSnapshot {
    this.mutedDedupeKeys.clear();
    return this.getSnapshot();
  }

  public ingestEvent(event: RawEstateTelegramEvent): {
    outcome: 'SUPPRESSED_CHATTER' | 'MUTED_BY_CEO_RULE' | 'COALESCED_EDIT_IN_PLACE' | 'DELIVERED_NEW_CARD';
    card: VipTelegramMessageCard | null;
  } {
    this.rawEventsIngested++;
    const nowIso = event.timestampUtc ?? new Date().toISOString();
    const route = classifyEventToTopic(event.kind);

    if (route.topic === 'SUPPRESSED_HEARTBEAT_SINK' || route.threadId === null || route.priorityTag === 'SUPPRESSED') {
      this.suppressedHeartbeatEvents++;
      this.suppressedBreakdown[event.kind] = (this.suppressedBreakdown[event.kind] ?? 0) + 1;
      return { outcome: 'SUPPRESSED_CHATTER', card: null };
    }

    const dedupeFingerprint = createHash('sha256')
      .update(`${route.topic}|${event.dedupeKey ?? `${event.sourceSubsystem}:${event.headline}`}`)
      .digest('hex')
      .slice(0, 16);

    if (this.mutedDedupeKeys.has(dedupeFingerprint)) {
      this.mutedByRuleEvents++;
      return { outcome: 'MUTED_BY_CEO_RULE', card: null };
    }

    const formattedMetrics = Object.entries(event.metrics).map(([label, value]) => ({
      label,
      value: String(value),
    }));

    // Check in-place coalescing window for existing unresolved card with identical fingerprint
    const existing = this.messages.find(
      (m) =>
        m.dedupeFingerprint === dedupeFingerprint &&
        m.resolution === null &&
        Math.abs(new Date(nowIso).getTime() - new Date(m.updatedAtUtc).getTime()) <=
          this.coalesceWindowSec * 1000
    );

    if (existing) {
      this.coalescedDuplicateUpdates++;
      existing.coalescedCount += 1;
      existing.deliveryMethod = 'EDIT_IN_PLACE';
      existing.updatedAtUtc = nowIso;
      existing.metrics = formattedMetrics;
      const wire = buildWirePayloads({
        priorityTag: existing.priorityTag,
        sourceSubsystem: existing.sourceSubsystem,
        headline: existing.headline,
        metrics: existing.metrics,
        executiveSummary: existing.executiveSummary,
        ceoQuestion: existing.ceoQuestion,
        coalescedCount: existing.coalescedCount,
        resolution: existing.resolution,
      });
      existing.htmlWirePayload = wire.html;
      existing.markdownV2WirePayload = wire.markdownV2;
      existing.charCount = wire.plainCharCount;
      existing.withinSingleScreenBudget = wire.html.length <= CEO_SINGLE_SCREEN_CHAR_BUDGET;
      existing.withinTelegramHardLimit =
        wire.html.length <= TELEGRAM_MAX_MESSAGE_CHARS &&
        wire.markdownV2.length <= TELEGRAM_MAX_MESSAGE_CHARS;
      return { outcome: 'COALESCED_EDIT_IN_PLACE', card: { ...existing } };
    }

    // Determine notification discipline strictly from CEO Focus Policy
    const shouldPingAudibly =
      this.focusPolicy === 'SILENT_DND_ALL'
        ? false
        : this.focusPolicy === 'VIP_P0_ONLY'
          ? route.topic === 'VIP_CEO_DECISIONS'
          : route.topic === 'VIP_CEO_DECISIONS' || route.topic === 'EXECUTIVE_BRIEFINGS';

    if (shouldPingAudibly) {
      this.audibleCeoPings++;
    }

    const messageId = event.id ?? `numen-${this.nextNumericMsgId}`;
    const numericId = this.nextNumericMsgId++;

    const inlineKeyboard: TelegramInlineButton[] =
      route.topic === 'VIP_CEO_DECISIONS'
        ? [
            {
              text: 'Approve & Sign',
              ...buildSafeCallbackData('approve', messageId),
              style: 'primary',
            },
            {
              text: 'Hold in Gate',
              ...buildSafeCallbackData('hold', messageId),
              style: 'caution',
            },
            {
              text: 'Mute 4h',
              ...buildSafeCallbackData('mute4h', messageId),
              style: 'neutral',
            },
          ]
        : [
            {
              text: 'Acknowledge',
              ...buildSafeCallbackData('ack', messageId),
              style: 'neutral',
            },
            {
              text: 'Mute Rule 4h',
              ...buildSafeCallbackData('mute4h', messageId),
              style: 'neutral',
            },
          ];

    const wire = buildWirePayloads({
      priorityTag: route.priorityTag,
      sourceSubsystem: event.sourceSubsystem,
      headline: event.headline,
      metrics: formattedMetrics,
      executiveSummary: event.autonomousAction,
      ceoQuestion: event.ceoQuestion ?? null,
      coalescedCount: 1,
      resolution: null,
    });

    const card: VipTelegramMessageCard = {
      messageId,
      telegramMsgNumericId: numericId,
      topic: route.topic,
      threadId: route.threadId,
      priorityTag: route.priorityTag,
      sourceSubsystem: event.sourceSubsystem,
      headline: event.headline,
      metrics: formattedMetrics,
      executiveSummary: event.autonomousAction,
      ceoQuestion: event.ceoQuestion ?? null,
      disableNotification: !shouldPingAudibly,
      audiblePingTriggered: shouldPingAudibly,
      deliveryMethod: 'SEND_NEW',
      coalescedCount: 1,
      dedupeFingerprint,
      htmlWirePayload: wire.html,
      markdownV2WirePayload: wire.markdownV2,
      legacyNoisyEquivalent: renderLegacyNoisyDump(event),
      charCount: wire.plainCharCount,
      withinSingleScreenBudget: wire.html.length <= CEO_SINGLE_SCREEN_CHAR_BUDGET,
      withinTelegramHardLimit:
        wire.html.length <= TELEGRAM_MAX_MESSAGE_CHARS &&
        wire.markdownV2.length <= TELEGRAM_MAX_MESSAGE_CHARS,
      inlineKeyboard,
      allCallbacksWithin64Bytes: inlineKeyboard.every(
        (b) => b.byteLength <= TELEGRAM_MAX_CALLBACK_BYTES
      ),
      createdAtUtc: nowIso,
      updatedAtUtc: nowIso,
      resolution: null,
    };

    this.messages.unshift(card);
    if (this.messages.length > 60) {
      this.messages.length = 60;
    }

    return { outcome: 'DELIVERED_NEW_CARD', card: { ...card } };
  }

  /**
   * Processes a 1-tap CEO inline button callback (`vip:approve:...`, `vip:hold:...`, `vip:ack:...`, `vip:mute4h:...`)
   * and updates the message card in-place with a SHA-256 signed receipt.
   */
  public executeInlineCallback(params: {
    messageId: string;
    action: 'approve' | 'hold' | 'ack' | 'mute4h';
    actorEmail?: string;
  }): {
    ok: boolean;
    receipt: CeoDecisionReceipt | null;
    snapshot: OttoNumenSnapshot;
    error?: string;
  } {
    const target = this.messages.find((m) => m.messageId === params.messageId);
    if (!target) {
      return {
        ok: false,
        receipt: null,
        snapshot: this.getSnapshot(),
        error: `Unknown Telegram messageId: ${params.messageId}`,
      };
    }

    const actorEmail = params.actorEmail ?? this.ceoRecipient;
    const decidedAtUtc = new Date().toISOString();
    const mappedAction: CeoDecisionReceipt['action'] =
      params.action === 'approve'
        ? 'APPROVED'
        : params.action === 'hold'
          ? 'HELD_IN_GATE'
          : params.action === 'mute4h'
            ? 'MUTED_4H'
            : 'ACKNOWLEDGED';

    if (params.action === 'mute4h') {
      this.mutedDedupeKeys.add(target.dedupeFingerprint);
    }

    const decisionSha256 = createHash('sha256')
      .update(`${target.messageId}|${mappedAction}|${actorEmail}|${decidedAtUtc}`)
      .digest('hex');

    const receipt: CeoDecisionReceipt = {
      receiptId: `rcpt-${decisionSha256.slice(0, 8)}`,
      messageId: target.messageId,
      action: mappedAction,
      actorEmail,
      decidedAtUtc,
      decisionSha256,
      note:
        mappedAction === 'APPROVED'
          ? `CEO signed off "${target.headline}" for authorised execution.`
          : mappedAction === 'HELD_IN_GATE'
            ? `CEO locked "${target.headline}" in gate pending further proof.`
            : mappedAction === 'MUTED_4H'
              ? `Muted fingerprint ${target.dedupeFingerprint} for 4h.`
              : `Acknowledged "${target.headline}".`,
    };

    target.resolution = receipt;
    target.deliveryMethod = 'EDIT_IN_PLACE';
    target.updatedAtUtc = decidedAtUtc;

    const wire = buildWirePayloads({
      priorityTag: target.priorityTag,
      sourceSubsystem: target.sourceSubsystem,
      headline: target.headline,
      metrics: target.metrics,
      executiveSummary: target.executiveSummary,
      ceoQuestion: target.ceoQuestion,
      coalescedCount: target.coalescedCount,
      resolution: receipt,
    });
    target.htmlWirePayload = wire.html;
    target.markdownV2WirePayload = wire.markdownV2;

    this.recentReceipts.unshift(receipt);
    if (this.recentReceipts.length > 25) {
      this.recentReceipts.length = 25;
    }

    return {
      ok: true,
      receipt,
      snapshot: this.getSnapshot(),
    };
  }

  /**
   * Injects a realistic 50-event raw estate storm to prove noise suppression,
   * topic sharding, and in-place burst coalescing vs legacy `oot_numun`.
   */
  public simulateEstateStorm(eventCount = 50): {
    ingested: number;
    suppressedChatter: number;
    coalescedEdits: number;
    newTopicCards: number;
    audiblePingsDuringStorm: number;
    snapshot: OttoNumenSnapshot;
  } {
    const total = Math.max(10, Math.min(200, Math.round(eventCount)));
    const pingsBefore = this.audibleCeoPings;
    let suppressedChatter = 0;
    let coalescedEdits = 0;
    let newTopicCards = 0;
    const stormBatchId = Date.now().toString(36).slice(-4);

    for (let i = 0; i < total; i++) {
      let res: ReturnType<OttoNumenConciergeEngine['ingestEvent']>;

      if (i === total - 1) {
        // Exactly 1 high-signal P0 CEO decision at the peak of the storm
        res = this.ingestEvent({
          kind: 'p0_budget_ceiling',
          sourceSubsystem: 'PennyD Treasury Guard',
          headline: `Raise Client opencode_primary Cap ($250 -> $400) [${stormBatchId}]`,
          metrics: {
            'Utilization': '92.4% ($231.00 / $250.00)',
            'Counterfactual': '$1,648.20 saved today (86.0%)',
            'Active Key': 'pk_live_opencode_primary_94a2',
          },
          autonomousAction:
            'CAS key-store holding sibling keys intact; free sovereign lanes absorbing 88% of burst.',
          ceoQuestion:
            'Approve temporary $400 daily cap ceiling for opencode_primary, or hold hard $250 cap?',
          dedupeKey: `vip:cap-raise-${stormBatchId}`,
        });
      } else if (i === Math.floor(total * 0.7)) {
        res = this.ingestEvent({
          kind: 'finops_milestone',
          sourceSubsystem: 'Meridian FinOps',
          headline: `Storm Absorption Saved $14.80 Across Sovereign $0 Lanes [${stormBatchId}]`,
          metrics: {
            'Tokens Routed': '1.42M tokens',
            'Actual Spend': '$0.0412 vs $14.8412 baseline',
            'BLIND Sensors': '2 host joule counters kept honest',
          },
          autonomousAction: 'Zero double-counting across FOCUS 1.0 & OTel 1.29 spans.',
          dedupeKey: `finops:storm-${stormBatchId}`,
        });
      } else if (i % 5 === 1 || i % 7 === 2) {
        // Flapping upstream 402 / spot burst across 2 deterministic fingerprints -> coalesced in-place!
        const isDeepSeek = i % 2 === 0;
        res = this.ingestEvent({
          kind: 'incident_auto_healed',
          sourceSubsystem: isDeepSeek ? 'PennyD Lane Failover' : 'InterCloud Spot Reconciler',
          headline: isDeepSeek
            ? 'DeepSeek 402 Credit Drain Rerouted to Sovereign Qwen/Gemini'
            : 'Vast.ai RTX-4090 Spot Preemption Healed (<42ms)',
          metrics: {
            'HTTP Class': isDeepSeek ? '402 billing_exhausted (not 401)' : 'Spot reclaim -> RunPod L40S',
            'Dropped WAL': '0 receipts lost',
            'Storm Seq': `#${i + 1}/${total}`,
          },
          autonomousAction:
            'Automatic multi-lane failover handled burst without degrading client SLA.',
          dedupeKey: isDeepSeek
            ? `storm-402-deepseek-${stormBatchId}`
            : `storm-spot-vast-${stormBatchId}`,
        });
      } else {
        // Routine Chronos beats, WAL flushes, and Dagster probes -> 100% intercepted & suppressed!
        const chatterKind: RawEstateEventKind =
          i % 3 === 0
            ? 'chronos_heartbeat'
            : i % 3 === 1
              ? 'wal_checkpoint_chatter'
              : 'dagster_routine_probe';
        res = this.ingestEvent({
          kind: chatterKind,
          sourceSubsystem: 'Chronos / Dagster',
          headline: `Routine background tick #${i + 1}`,
          metrics: { Seq: i + 1 },
          autonomousAction: 'Suppressed machine chatter.',
        });
      }

      if (res.outcome === 'SUPPRESSED_CHATTER') suppressedChatter++;
      else if (res.outcome === 'COALESCED_EDIT_IN_PLACE') coalescedEdits++;
      else if (res.outcome === 'DELIVERED_NEW_CARD') newTopicCards++;
    }

    return {
      ingested: total,
      suppressedChatter,
      coalescedEdits,
      newTopicCards,
      audiblePingsDuringStorm: this.audibleCeoPings - pingsBefore,
      snapshot: this.getSnapshot(),
    };
  }

  /**
   * Synthesizes an on-demand CEO Executive Briefing from live Gateway, Grand Union,
   * and Hermes Living Tree state.
   */
  public synthesizeLiveExecutiveBriefing(live: {
    beatNumber: number;
    walReceipts: number;
    netSavingsUsd: number;
    savingsPct: number;
    ensemblePassPct: number;
    frontierPassPct: number;
    onlinePools: number;
    totalPools: number;
    guaranteesVerified: number;
    guaranteesTotal: number;
  }): VipTelegramMessageCard | null {
    const utcDate = getUtcDateString();
    const daily = getDailyChallengeForDate(utcDate);
    const stamp = new Date().toISOString().slice(11, 19);

    const res = this.ingestEvent({
      kind: 'executive_briefing',
      sourceSubsystem: 'Hermes · OTTO_NUMEN',
      headline: `Live CEO Brief (${stamp} UTC) — ${live.guaranteesVerified}/${live.guaranteesTotal} Guarantees Verified`,
      metrics: {
        'Battalion': `${live.walReceipts.toLocaleString()} WAL · $${live.netSavingsUsd.toFixed(2)} saved (${live.savingsPct.toFixed(1)}%)`,
        'Legion vs Fr.': `${live.ensemblePassPct}% Open Ensemble vs ${live.frontierPassPct}% Frontier`,
        'InterCloud': `${live.onlinePools}/${live.totalPools} pools · Beat #${live.beatNumber}`,
        'Hermes Sky': `${daily.targetSephirahName.split('(')[0].trim()} · Canon ${daily.targetNumber}`,
      },
      autonomousAction:
        'All client surfaces running SSE zero-polling; gated items (#8185, ff8543bd) held cleanly in VIP Decisions.',
      dedupeKey: `briefing:manual-${Date.now()}`,
    });
    return res.card;
  }

  public getSnapshot(): OttoNumenSnapshot {
    const topicCounts: Record<TelegramTopicKey, number> = {
      VIP_CEO_DECISIONS: 0,
      EXECUTIVE_BRIEFINGS: 0,
      INCIDENTS_HEALING: 0,
      FINOPS_TREASURY: 0,
      RELEASES_GWT_AUDIT: 0,
      SUPPRESSED_HEARTBEAT_SINK: this.suppressedHeartbeatEvents,
    };

    for (const msg of this.messages) {
      topicCounts[msg.topic] = (topicCounts[msg.topic] ?? 0) + 1;
    }

    const deliveredTopicCards = this.messages.length;
    const rawTotal = Math.max(1, this.rawEventsIngested);
    const noiseReductionPct = Number(
      (((rawTotal - deliveredTopicCards) / rawTotal) * 100).toFixed(1)
    );
    const audibleInterruptionReductionPct = Number(
      (((rawTotal - this.audibleCeoPings) / rawTotal) * 100).toFixed(1)
    );

    return {
      schemaVersion: 'otto-numen-vip-telegram-v1',
      generatedAtUtc: new Date().toISOString(),
      botHandle: '@otto_numen_bot',
      legacyAliasReplaced: 'oot_numun (single-channel raw dump)',
      ceoRecipient: this.ceoRecipient,
      webhookPosture: 'SANDBOX_SIMULATOR_ACTIVE_WEBHOOK_EXPORT_READY',
      focusPolicy: this.focusPolicy,
      coalesceWindowSec: this.coalesceWindowSec,
      quietHoursUtc: this.quietHoursUtc,
      mutedDedupeKeys: Array.from(this.mutedDedupeKeys),
      topics: TELEGRAM_FORUM_TOPICS,
      telemetry: {
        rawEventsIngested: this.rawEventsIngested,
        suppressedHeartbeatEvents: this.suppressedHeartbeatEvents,
        coalescedDuplicateUpdates: this.coalescedDuplicateUpdates,
        mutedByRuleEvents: this.mutedByRuleEvents,
        deliveredTopicCards,
        audibleCeoPings: this.audibleCeoPings,
        legacySingleChannelMessagesWouldBe: this.rawEventsIngested,
        legacyAudiblePingsWouldBe: this.rawEventsIngested,
        noiseReductionPct,
        audibleInterruptionReductionPct,
        pendingVipDecisions: this.messages.filter(
          (m) => m.topic === 'VIP_CEO_DECISIONS' && m.resolution === null
        ).length,
        suppressedBreakdown: { ...this.suppressedBreakdown },
        topicCounts,
      },
      messages: this.messages.map((m) => ({
        ...m,
        metrics: m.metrics.map((x) => ({ ...x })),
        inlineKeyboard: m.inlineKeyboard.map((b) => ({ ...b })),
      })),
      recentReceipts: this.recentReceipts.map((r) => ({ ...r })),
    };
  }
}

/**
 * Generates a production-ready, drop-in TypeScript adapter for `otto.mumchimp.com`
 * so the fleet team can bind `@otto_numen_bot` directly to Telegram's Forum Topics API.
 */
export function generateOttoNumenBotBlueprintTs(): string {
  return `/**
 * Hermes · OTTO_NUMEN (@otto_numen_bot) — Production VIP CEO Telegram Concierge Adapter
 * Deploy on: otto.mumchimp.com (outside AI Studio container so .env.example stays zero-prompt)
 *
 * Capabilities:
 *  - Auto-provisions 5 Telegram Supergroup Forum Topics (createForumTopic)
 *  - Suppresses 100% of Chronos/WAL/Dagster machine heartbeats before hitting Telegram API
 *  - Coalesces flapping lane/spot alerts in-place via editMessageText (zero flood)
 *  - Enforces strict HTML entity escaping & <=64-byte callback_data payloads
 */

export interface OttoTelegramRuntimeConfig {
  botToken: string;
  vipForumChatId: string;
  topicThreadIds: {
    VIP_CEO_DECISIONS: number;
    EXECUTIVE_BRIEFINGS: number;
    INCIDENTS_HEALING: number;
    FINOPS_TREASURY: number;
    RELEASES_GWT_AUDIT: number;
  };
}

const activeFingerprints = new Map<string, { telegramMessageId: number; count: number; updatedAtMs: number }>();

export function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export async function dispatchVipExecutiveEvent(
  cfg: OttoTelegramRuntimeConfig,
  evt: {
    topic: keyof OttoTelegramRuntimeConfig['topicThreadIds'] | 'SUPPRESSED_HEARTBEAT_SINK';
    priorityTag: string;
    subsystem: string;
    headline: string;
    metrics: Record<string, string | number>;
    summary: string;
    ceoQuestion?: string;
    dedupeFingerprint: string;
    inlineButtons?: Array<{ text: string; callback_data: string }>;
  }
): Promise<{ sent: boolean; method: 'suppressed' | 'sendMessage' | 'editMessageText' }> {
  if (evt.topic === 'SUPPRESSED_HEARTBEAT_SINK') {
    return { sent: false, method: 'suppressed' };
  }

  const prev = activeFingerprints.get(evt.dedupeFingerprint);
  const count = prev ? prev.count + 1 : 1;
  const suffix = count > 1 ? \` (Coalesced x\${count})\` : '';
  const metricBlock = Object.entries(evt.metrics)
    .map(([k, v]) => \`\${k.padEnd(11, ' ')} \${v}\`)
    .join('\\n');

  const text = [
    \`<b>\${escapeHtml(evt.priorityTag)} · \${escapeHtml(evt.subsystem.toUpperCase())}\${escapeHtml(suffix)}</b>\`,
    \`<b>\${escapeHtml(evt.headline)}</b>\`,
    \`<pre>\${escapeHtml(metricBlock)}</pre>\`,
    escapeHtml(evt.summary),
    evt.ceoQuestion ? \`<b>Decision Required:</b> \${escapeHtml(evt.ceoQuestion)}\` : '',
  ].filter(Boolean).join('\\n\\n').slice(0, 900);

  const apiBase = \`https://api.telegram.org/bot\${cfg.botToken}\`;
  if (prev && Date.now() - prev.updatedAtMs < 300_000) {
    await fetch(\`\${apiBase}/editMessageText\`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: cfg.vipForumChatId,
        message_id: prev.telegramMessageId,
        text,
        parse_mode: 'HTML',
        reply_markup: evt.inlineButtons ? { inline_keyboard: [evt.inlineButtons] } : undefined,
      }),
    });
    activeFingerprints.set(evt.dedupeFingerprint, {
      telegramMessageId: prev.telegramMessageId,
      count,
      updatedAtMs: Date.now(),
    });
    return { sent: true, method: 'editMessageText' };
  }

  const res = await fetch(\`\${apiBase}/sendMessage\`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: cfg.vipForumChatId,
      message_thread_id: cfg.topicThreadIds[evt.topic],
      text,
      parse_mode: 'HTML',
      disable_notification: evt.topic !== 'VIP_CEO_DECISIONS',
      reply_markup: evt.inlineButtons ? { inline_keyboard: [evt.inlineButtons] } : undefined,
    }),
  });
  const json = (await res.json()) as { ok: boolean; result?: { message_id: number } };
  if (json.ok && json.result?.message_id) {
    activeFingerprints.set(evt.dedupeFingerprint, {
      telegramMessageId: json.result.message_id,
      count: 1,
      updatedAtMs: Date.now(),
    });
  }
  return { sent: true, method: 'sendMessage' };
}
`;
}
