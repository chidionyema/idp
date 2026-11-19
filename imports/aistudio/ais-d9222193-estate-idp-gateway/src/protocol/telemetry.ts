/**
 * Canonical Delivery Friction Telemetry & Surface Agreement Registry
 * Resolves MUM-300 / MUM-301 delivery friction metrics:
 * - 33 sessions/day overhead tracker (19 min/day wasted deciding things already decided)
 * - True surface acks (Argon Genesis authority vs local self-reporting dial)
 * - Agreement states: Agreed / Deferred / Blind
 * - Action ledger (~/.estate/action-ledger.jsonl)
 */

import { SurfaceAck, TelemetryMetric } from './types';

export interface RecurringSessionMetric {
  id: string;
  cronSchedule: string;
  taskName: string;
  dailyRunCount: number;
  averageDurationSec: number;
  emptyStatusRuns: number; // Runs returning "nothing changed"
  overheadMinutesPerDay: number;
  recommendation: string;
}

export const INITIAL_RECURRING_METRICS: RecurringSessionMetric[] = [
  {
    id: 'cron_guard_check',
    cronSchedule: '0 * * * * (Hourly)',
    taskName: 'Estate Guard / Gate Evaluator',
    dailyRunCount: 24,
    averageDurationSec: 36,
    emptyStatusRuns: 22,
    overheadMinutesPerDay: 14.4,
    recommendation: 'Run on cluster Dagster clock directly without spinning up fresh agent sessions.',
  },
  {
    id: 'cron_ack_publisher',
    cronSchedule: '0 */3 * * * (Every 3h)',
    taskName: 'Acknowledgement Heartbeat Poller',
    dailyRunCount: 8,
    averageDurationSec: 42,
    emptyStatusRuns: 7,
    overheadMinutesPerDay: 5.6,
    recommendation: 'Eliminate agent invocation; emit lightweight one-time token ping from broker.',
  },
  {
    id: 'cron_staleness_sweep',
    cronSchedule: '0 0 * * * (Daily)',
    taskName: 'Linear Staleness Sweep',
    dailyRunCount: 1,
    averageDurationSec: 55,
    emptyStatusRuns: 1,
    overheadMinutesPerDay: 0.9,
    recommendation: 'Batch with PR sync trigger instead of daily ungrounded sweep.',
  },
];

export const INITIAL_SURFACE_ACKS: SurfaceAck[] = [
  {
    surfaceId: 'argon_genesis_cluster',
    label: 'Argon Genesis (Dagster Cluster Control Plane)',
    token: 'tok_arg_99824e81ad07c',
    state: 'agreed',
    deadlineMs: Date.now() + 86400000,
    lastSeenMs: Date.now() - 45000,
    authSource: 'Argon Genesis (Cluster)',
  },
  {
    surfaceId: 'mac_session_460567726510256',
    label: 'Mac Session CLI Helper (genesis-control-plane)',
    token: 'tok_mac_8f73b190a42e',
    state: 'agreed',
    deadlineMs: Date.now() + 86400000,
    lastSeenMs: Date.now() - 120000,
    authSource: 'Cryptographic One-Time Token',
  },
  {
    surfaceId: 'mobile_node_ios_client',
    label: 'Mobile Client Node (Offline-Capable Agent)',
    token: undefined,
    state: 'deferred',
    deadlineMs: Date.now() + 7200000, // 2 hours remaining
    lastSeenMs: Date.now() - 900000,
    authSource: 'Cryptographic One-Time Token',
  },
  {
    surfaceId: 'ci_worker_runner_01',
    label: 'CI Worker Runner (MUM-298 Estate Gate)',
    token: 'tok_ci_11b899ea217c',
    state: 'agreed',
    deadlineMs: Date.now() + 86400000,
    lastSeenMs: Date.now() - 60000,
    authSource: 'Argon Genesis (Cluster)',
  },
  {
    surfaceId: 'legacy_board_sync',
    label: 'Broadcast Board Listener (Unregistered Surface)',
    token: undefined,
    state: 'blind',
    deadlineMs: Date.now() - 3600000, // Expired 1 hour ago
    lastSeenMs: Date.now() - 7200000,
    authSource: 'Local Self-Report (Deprecated)',
  },
];

export const INITIAL_LEDGER_ENTRIES: TelemetryMetric[] = [
  {
    id: 'act_101',
    timestamp: Date.now() - 300000,
    surfaceId: 'argon_genesis_cluster',
    callId: 'call_gcp_001',
    action: 'git.pr_sync',
    status: 'admitted',
    durationMs: 42,
    receiptId: 'rcpt_1730974550_99a',
  },
  {
    id: 'act_102',
    timestamp: Date.now() - 240000,
    surfaceId: 'mobile_node_ios_client',
    callId: 'call_mob_002',
    action: 'mobile.sync_draft',
    status: 'queued',
    durationMs: 8,
    reason: 'Safe offline mutation queued without lease',
  },
  {
    id: 'act_103',
    timestamp: Date.now() - 180000,
    surfaceId: 'mobile_node_ios_client',
    callId: 'call_mob_003',
    action: 'cluster.deploy',
    status: 'refused',
    durationMs: 5,
    reason: 'Unsafe offline mutation refused while disconnected',
  },
  {
    id: 'act_104',
    timestamp: Date.now() - 120000,
    surfaceId: 'mac_session_460567726510256',
    callId: 'call_mac_004',
    action: 'unknown_capability_delete',
    status: 'refused',
    durationMs: 4,
    reason: 'Unknown capability downgraded to read-only; mutation refused',
  },
  {
    id: 'act_105',
    timestamp: Date.now() - 60000,
    surfaceId: 'ci_worker_runner_01',
    callId: 'call_ci_005',
    action: 'contract.verify',
    status: 'admitted',
    durationMs: 14,
    receiptId: 'rcpt_1730974800_21f',
  },
];
