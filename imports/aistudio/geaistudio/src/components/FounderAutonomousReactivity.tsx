import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Play,
  RefreshCw,
  Send,
  WifiOff,
  Zap,
} from 'lucide-react';
import type {
  AutonomousReactivitySnapshot,
  CapabilityAuditStatus,
  DurableObligationRecord,
  ExperimentId,
  ObligationLifecycleStage,
} from '../engine/autonomousReactivity';
import { FounderMccConvergencePanel } from './FounderMccConvergencePanel';
import { OmniflowLiveRoomPanel } from './OmniflowLiveRoomPanel';
import { TeamHandoffExportPanel } from './TeamHandoffExportPanel';

type ReactivityViewTab =
  | 'live_comms_bus'
  | 'unified_mcc_bus'
  | 'live_command'
  | 'experiments_sla'
  | 'estate_audit'
  | 'team_handoff';

const CANONICAL_STAGES: ObligationLifecycleStage[] = [
  'DETECTED',
  'ROUTED',
  'DELIVERED',
  'ACCEPTED',
  'LEASED',
  'EXECUTING',
  'VERIFIED',
];

const EXPERIMENT_BUTTONS: Array<{
  id: ExperimentId;
  shortLabel: string;
  subtitle: string;
}> = [
  {
    id: 'EXP_A',
    shortLabel: 'Exp A · Passkey Lost Escalation (P0)',
    subtitle: '20:00 bin/idp-passkey-verify correlation, QUAD lease & KARMA proof',
  },
  {
    id: 'EXP_B',
    shortLabel: 'Exp B · Idle Workforce Activation',
    subtitle: 'Idle != Available & Connected != Capable runtime filter',
  },
  {
    id: 'EXP_C',
    shortLabel: 'Exp C · Worker Crash & Fence 409',
    subtitle: '2-heartbeat loss, f_2 takeover & zombie f_1 write rejection',
  },
  {
    id: 'EXP_D',
    shortLabel: 'Exp D · 4-Surface Lineage',
    subtitle: 'Mobile -> Browser -> Cloud -> KARMA single missionId',
  },
  {
    id: 'EXP_E',
    shortLabel: 'Exp E · NATS Outage & Replay',
    subtitle: 'Durable offline outbox, convergence & 0-duplicate replay',
  },
  {
    id: 'EXP_F',
    shortLabel: 'Exp F · Chesed -> Geburah Immunity',
    subtitle: '0ms producer prevention on replayed failure class',
  },
];

interface TopologyGraphNode {
  id: string;
  planeLabel: string;
  title: string;
  subtitle: string;
  x: number;
  y: number;
  tone: 'cyan' | 'emerald' | 'amber' | 'slate';
  detail: string;
}

export function FounderAutonomousReactivity({
  handoffTriggerSeq = 0,
}: {
  handoffTriggerSeq?: number;
} = {}) {
  const [snap, setSnap] = useState<AutonomousReactivitySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);
  const [view, setView] = useState<ReactivityViewTab>(() => {
    if (handoffTriggerSeq > 0) return 'team_handoff';
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const pathNorm = window.location.pathname.replace(/\/+$/, '').toLowerCase();
      if (
        params.get('handoff') === '1' ||
        params.get('getwork') === '1' ||
        pathNorm === '/handoff' ||
        pathNorm === '/get-work' ||
        pathNorm === '/export' ||
        pathNorm === '/download'
      ) {
        return 'team_handoff';
      }
      if (
        params.get('comms') === '1' ||
        pathNorm === '/comms' ||
        pathNorm === '/bus' ||
        pathNorm === '/omniflow'
      ) {
        return 'live_comms_bus';
      }
    }
    return 'live_comms_bus';
  });

  useEffect(() => {
    if (handoffTriggerSeq > 0) {
      setView('team_handoff');
    }
  }, [handoffTriggerSeq]);
  const [selectedObligationId, setSelectedObligationId] = useState<string>('OBL-PASSKEY-8175');
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string>('node-beast');
  const [auditFilter, setAuditFilter] = useState<'all' | CapabilityAuditStatus>('all');
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<string | null>(null);
  const [customEscalationTitle, setCustomEscalationTitle] = useState('');

  const loadInitialState = useCallback(async () => {
    try {
      const res = await fetch('/api/reactivity/state');
      if (res.ok) {
        const json = (await res.json()) as AutonomousReactivitySnapshot;
        setSnap(json);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Strict I-8090 compliance: EventSource SSE stream only (zero setInterval HTTP polling)
  useEffect(() => {
    void loadInitialState();
    const es = new EventSource('/api/reactivity/stream');
    es.addEventListener('open', () => setSseConnected(true));
    es.addEventListener('error', () => setSseConnected(false));
    es.addEventListener('reactivity_snapshot', (ev) => {
      try {
        const parsed = JSON.parse(
          (ev as MessageEvent<string>).data
        ) as AutonomousReactivitySnapshot;
        setSnap(parsed);
        setLoading(false);
        setSseConnected(true);
      } catch {
        // Ignore malformed SSE frame cleanly
      }
    });
    return () => {
      es.close();
    };
  }, [loadInitialState]);

  async function invokeReactivityAction(
    payload: Record<string, unknown>,
    busyLabel: string
  ) {
    setBusyKey(busyLabel);
    try {
      const res = await fetch('/api/reactivity/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        message?: string;
        snapshot?: AutonomousReactivitySnapshot;
        obligationId?: string;
      };
      if (json.snapshot) {
        setSnap(json.snapshot);
      }
      if (json.obligationId) {
        setSelectedObligationId(json.obligationId);
      }
      if (json.message) {
        setActionBanner(json.message);
      }
    } finally {
      setBusyKey(null);
    }
  }

  const activeObligation: DurableObligationRecord | undefined = useMemo(() => {
    if (!snap) return undefined;
    return (
      snap.obligations.find((o) => o.obligationId === selectedObligationId) ??
      snap.obligations[0]
    );
  }, [snap, selectedObligationId]);

  const topologyNodes: TopologyGraphNode[] = useMemo(() => {
    const natsUp = snap?.brokerTransportState === 'NATS_JETSTREAM_CONNECTED';
    const passkeyStage =
      snap?.obligations.find((o) => o.obligationId === 'OBL-PASSKEY-8175')?.stage ?? 'DETECTED';
    const immunityCount = snap?.inheritedImmunityRules.length ?? 0;

    return [
      {
        id: 'node-founder-edge',
        planeLabel: 'P1 · Connectivity',
        title: 'Founder & Disconnected Surfaces',
        subtitle: natsUp ? 'NATS JetStream + SSE Live' : 'Degraded Offline Outbox',
        x: 92,
        y: 88,
        tone: natsUp ? 'cyan' : 'amber',
        detail:
          'Ingests Founder Face ID escalations, OMNIFLOW events, WhatsApp bursts, and CLI telemetry. Broker ACK proves transport delivery only (never completion).',
      },
      {
        id: 'node-beast',
        planeLabel: 'P2 · BEAST / SPIDER #8183',
        title: 'Living Intelligence Graph #8184',
        subtitle: '20:00 Passkey Diagnosis Correlated',
        x: 310,
        y: 88,
        tone: 'cyan',
        detail:
          'Correlates the 20:00 bin/idp-passkey-verify report with the Founder Face ID failure and PR #8175 dependency, converging duplicate comments by subjectKey.',
      },
      {
        id: 'node-quad-flow',
        planeLabel: 'P3 · FLOW · Legion · QUAD',
        title: 'QUAD Ed25519 Admission & Lease',
        subtitle: `Fence Epoch f_${snap?.globalFencingEpoch ?? 100}`,
        x: 540,
        y: 88,
        tone: 'emerald',
        detail:
          'Rejects self-declared ESTATE_AGENT env vars (403), incapable nodes (422), and 0%-quota idle workers (429) before issuing a monotonic fencing token.',
      },
      {
        id: 'node-temporal',
        planeLabel: 'P4 · Durable Custody',
        title: 'Temporal Fenced Execution',
        subtitle: `Passkey: ${passkeyStage}`,
        x: 310,
        y: 218,
        tone: passkeyStage === 'VERIFIED' ? 'emerald' : 'cyan',
        detail:
          'Retains durable custody when workers crash or browsers close. 2-heartbeat watchdog revokes expired leases and rejects stale zombie writes (409).',
      },
      {
        id: 'node-karma',
        planeLabel: 'P5 · KARMA / Optimus',
        title: 'Independent Verifier & Immunity',
        subtitle: `${immunityCount} Producer Rule${immunityCount === 1 ? '' : 's'} Active`,
        x: 540,
        y: 218,
        tone: immunityCount > 0 ? 'emerald' : 'slate',
        detail:
          'Blocks executor self-certification (403), independently verifies outcomes, and compiles Chesed -> Geburah producer-level prevention rules.',
      },
      {
        id: 'node-external-gate',
        planeLabel: 'R-010 · Epistemic Boundary',
        title: 'Cross-Host Fleet Rollout',
        subtitle: 'BLOCKED_DISPATCH / NOT VERIFIED',
        x: 92,
        y: 218,
        tone: 'amber',
        detail:
          'Honest boundary: local engine proves all 7 stages & Experiments A–F; live WAN NATS & external PR #8175 deployment remain explicitly uninflated.',
      },
    ];
  }, [snap]);

  const selectedGraphNode =
    topologyNodes.find((n) => n.id === selectedGraphNodeId) ?? topologyNodes[1];

  const filteredAuditRows = useMemo(() => {
    if (!snap) return [];
    if (auditFilter === 'all') return snap.estateAuditMatrix;
    return snap.estateAuditMatrix.filter((r) => r.classification === auditFilter);
  }, [snap, auditFilter]);

  if (loading || !snap) {
    if (view === 'team_handoff') {
      return (
        <div className="space-y-6">
          <TeamHandoffExportPanel />
        </div>
      );
    }
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3">
        <div className="h-4 w-64 bg-slate-100 rounded" />
        <div className="h-24 w-full bg-slate-50 rounded border border-slate-100" />
        <div className="text-xs text-slate-500">
          Hydrating Meridian Real-Time Founder’s View &amp; Living Intelligence Graph (#8184)…
        </div>
      </div>
    );
  }

  const natsConnected = snap.brokerTransportState === 'NATS_JETSTREAM_CONNECTED';

  return (
    <div className="space-y-6">
      {/* Top Executive Header & Honest Cross-Host Epistemic Banner */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-slate-500">
              <span className="font-semibold text-slate-900">{snap.programmeAnchor}</span>
              <span aria-hidden="true">·</span>
              <span>Continuity #7790</span>
              <span aria-hidden="true">·</span>
              <span>Fleet Comms #7481</span>
              <span aria-hidden="true">·</span>
              <span>OMNIFLOW #8133</span>
              <span aria-hidden="true">·</span>
              <span className={sseConnected ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                {sseConnected ? 'SSE Telemetry Live (0 Polling)' : 'SSE Reconnecting'}
              </span>
            </div>
            <span className="font-semibold text-amber-700">
              External Cross-Host Verdict: BLOCKED_DISPATCH / NOT VERIFIED
            </span>
          </div>

          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
            <div className="space-y-1 max-w-3xl">
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight text-balance">
                Meridian Universal Execution Protocol (MCC-001) &amp; Real-Time Founder’s View
              </h2>
              <p className="text-xs sm:text-sm text-slate-600">
                Unified <strong className="font-semibold text-slate-900">Web · App · Console</strong>{' '}
                collaboration enforced through existing IDP, QUAD, FLOW, Legion, and{' '}
                <code className="font-mono">bin/capability-index</code>. Issue comments and broker{' '}
                <code className="font-mono">inbox --ack</code> never settle obligations.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <button
                type="button"
                disabled={busyKey !== null}
                onClick={() =>
                  void invokeReactivityAction(
                    { action: 'run_all_experiments' },
                    'run_all_experiments'
                  )
                }
                className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
              >
                <Play className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                {busyKey === 'run_all_experiments'
                  ? 'Executing Experiments A–F…'
                  : 'Run Ship-and-Prove Suite (Exp A–F)'}
              </button>
            </div>
          </div>

          {/* Segmented View Controls */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <button
              type="button"
              onClick={() => setView('live_comms_bus')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'live_comms_bus'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              00. Live Cross-Agent Comms Bus
            </button>
            <button
              type="button"
              onClick={() => setView('unified_mcc_bus')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'unified_mcc_bus'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              01. Unified Web · App · Console &amp; MCC-001
            </button>
            <button
              type="button"
              onClick={() => setView('live_command')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'live_command'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              02. 5-Plane Custody &amp; Passkey (#8184)
            </button>
            <button
              type="button"
              onClick={() => setView('experiments_sla')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'experiments_sla'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              03. Cert Suite (10/10), LTL &amp; Exp A–F
            </button>
            <button
              type="button"
              onClick={() => setView('estate_audit')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'estate_audit'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              04. IDP + Cross-Repo Reuse &amp; 14-Boundary Audit
            </button>
            <button
              type="button"
              onClick={() => setView('team_handoff')}
              className={`min-h-[40px] max-w-full text-left sm:whitespace-nowrap leading-snug px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors ${
                view === 'team_handoff'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              05. Today’s Changes &amp; Team Handoff
            </button>
          </div>
        </div>

        {/* Truthful Separation Banner */}
        <div className="rounded-lg border border-amber-300 bg-amber-50/70 px-4 py-2.5 text-xs text-amber-950">
          <strong>Epistemic Separation (Rego R-010):</strong> {snap.crossHostHonestVerdict.summaryBanner}
        </div>

        {actionBanner && (
          <div className="rounded-lg border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs font-mono text-slate-900 flex items-center justify-between gap-3">
            <span>{actionBanner}</span>
            <button
              type="button"
              onClick={() => setActionBanner(null)}
              className="text-slate-500 hover:text-slate-900 font-sans font-medium whitespace-nowrap"
            >
              Dismiss
            </button>
          </div>
        )}
      </section>

      {/* 4-Column Precision Telemetry Strip (Tabular Numerals) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs text-slate-500">Unowned Accepted P0 Obligations</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono tabular-nums text-slate-900">
              {snap.unownedAcceptedP0Obligations}
            </span>
            <span className="text-xs font-mono text-emerald-700">Target: 0</span>
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {snap.obligations.length} durable obligations in Temporal/FLOW custody
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs text-slate-500">Monotonic Lease Fence &amp; Split-Brain Guard</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono tabular-nums text-slate-900">
              f_{snap.globalFencingEpoch}
            </span>
            <span className="text-xs font-mono text-cyan-700">
              {snap.staleFenceRejectionsCount} stale 409s
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {snap.duplicateProtectedEffectsCount} duplicate protected side effects
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs text-slate-500">False Settlements Blocked (Comment / ACK / Self)</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono tabular-nums text-slate-900">
              {snap.falseSettlementsBlockedCount}
            </span>
            <span className="text-xs font-mono text-emerald-700">Fail-Closed</span>
          </div>
          <div className="mt-1 text-xs text-slate-600">
            GitHub issues &amp; <code className="font-mono">inbox --ack</code> cannot settle work
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs text-slate-500">Connectivity &amp; Chesed → Geburah Immunity</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className={`text-xl font-bold font-mono tabular-nums ${
                natsConnected ? 'text-emerald-700' : 'text-amber-700'
              }`}
            >
              {natsConnected ? 'NATS ONLINE' : `OUTBOX (${snap.durableOutboxBacklogCount})`}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
            {snap.inheritedImmunityRules.length} immunity rule(s) ·{' '}
            {snap.inheritedImmunityRules.reduce((a, r) => a + r.preventedRecurrences, 0)} regressions prevented
          </div>
        </div>
      </section>

      {/* =================================================================== */}
      {/* VIEW 0: LIVE OMNIFLOW UNIVERSAL REAL-TIME COLLABORATION BUS         */}
      {/* =================================================================== */}
      {view === 'live_comms_bus' && <OmniflowLiveRoomPanel />}

      {/* =================================================================== */}
      {/* VIEW 1: UNIFIED WEB · APP · CONSOLE & MCC-001 EXECUTION PROTOCOL    */}
      {/* =================================================================== */}
      {view === 'unified_mcc_bus' && (
        <FounderMccConvergencePanel
          mcc={snap.mccConvergence}
          mode="unified_bus_mcc"
          busyKey={busyKey}
          onInvokeAction={invokeReactivityAction}
        />
      )}

      {/* =================================================================== */}
      {/* VIEW 2: REAL-TIME CUSTODY, OBSIDIAN LIVING GRAPH & WORKFORCE MATRIX */}
      {/* =================================================================== */}
      {view === 'live_command' && (
        <div className="space-y-6">
          {/* Deep Obsidian 2400-Future 5-Plane & Causal Topology Stage */}
          <section className="rounded-xl bg-[#07090E] text-slate-100 border border-slate-800 p-5 space-y-5">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <div className="text-xs font-mono text-cyan-400">
                  LIVING INTELLIGENCE GRAPH #8184 · FIVE-PLANE REACTIVE OPERATING FABRIC
                </div>
                <h3 className="mt-0.5 text-base font-semibold text-white">
                  Interactive Causal Topology &amp; 7-Stage Obligation Custody Pipeline
                </h3>
              </div>

              {/* Direct Real-Time Fault & Repair Controls */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      { action: 'run_experiment', experimentId: 'EXP_A' },
                      'exp_a_quick'
                    )
                  }
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-md bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50 whitespace-nowrap"
                >
                  <Zap className="h-3.5 w-3.5" aria-hidden="true" />
                  Repair Passkey Incident (Exp A)
                </button>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      {
                        action: 'attempt_github_settlement',
                        obligationId: activeObligation?.obligationId ?? 'OBL-PASSKEY-8175',
                      },
                      'gh_probe'
                    )
                  }
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  Test GitHub Comment != Custody
                </button>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      {
                        action: 'attempt_broker_ack_settlement',
                        obligationId: activeObligation?.obligationId ?? 'OBL-PASSKEY-8175',
                      },
                      'ack_probe'
                    )
                  }
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  Test inbox --ack != Settlement
                </button>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      { action: 'run_experiment', experimentId: 'EXP_C' },
                      'exp_c_quick'
                    )
                  }
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  Simulate Crash &amp; Fence 409 (Exp C)
                </button>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      { action: 'toggle_nats', connected: !natsConnected },
                      'toggle_nats'
                    )
                  }
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  <WifiOff className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                  {natsConnected ? 'Disconnect NATS Broker' : 'Reconnect NATS & Replay'}
                </button>
              </div>
            </div>

            {/* Interactive SVG Topology + Selected Plane Inspector */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
              <div className="lg:col-span-8 rounded-lg border border-slate-800 bg-[#0B0F19] p-3 overflow-x-auto">
                <svg
                  viewBox="0 0 680 300"
                  role="img"
                  aria-label="Meridian Five-Plane Reactive Intelligence Topology"
                  className="w-full min-w-[560px] h-auto cursor-crosshair"
                >
                  {/* Subtle calibration grid */}
                  <g stroke="#1E293B" strokeWidth="1" opacity="0.45">
                    <line x1="0" y1="75" x2="680" y2="75" />
                    <line x1="0" y1="150" x2="680" y2="150" />
                    <line x1="0" y1="225" x2="680" y2="225" />
                    <line x1="170" y1="0" x2="170" y2="300" />
                    <line x1="340" y1="0" x2="340" y2="300" />
                    <line x1="510" y1="0" x2="510" y2="300" />
                  </g>

                  {/* Directed causal edges */}
                  <g stroke="#38BDF8" strokeWidth="1.75" fill="none" opacity="0.75">
                    <path d="M 190 88 L 298 88" />
                    <path d="M 426 88 L 528 88" />
                    <path d="M 595 118 L 385 192" />
                    <path d="M 426 218 L 528 218" />
                    <path d="M 595 248 C 595 282, 145 282, 145 118" strokeDasharray="4 4" stroke="#10B981" />
                    <path d="M 298 218 L 204 218" strokeDasharray="3 3" stroke="#F59E0B" />
                  </g>

                  {/* Interactive Plane Nodes */}
                  {topologyNodes.map((node) => {
                    const isSelected = node.id === selectedGraphNode.id;
                    const strokeColor =
                      node.tone === 'emerald'
                        ? '#10B981'
                        : node.tone === 'amber'
                          ? '#F59E0B'
                          : node.tone === 'cyan'
                            ? '#06B6D4'
                            : '#64748B';
                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x - 82}, ${node.y - 30})`}
                        onClick={() => setSelectedGraphNodeId(node.id)}
                        className="cursor-pointer"
                      >
                        <rect
                          width="196"
                          height="62"
                          rx="8"
                          fill={isSelected ? '#111827' : '#090D16'}
                          stroke={strokeColor}
                          strokeWidth={isSelected ? '2.2' : '1.2'}
                        />
                        <text
                          x="10"
                          y="18"
                          fill={strokeColor}
                          fontSize="9.5"
                          fontFamily="monospace"
                          fontWeight="600"
                        >
                          {node.planeLabel}
                        </text>
                        <text
                          x="10"
                          y="35"
                          fill="#F8FAFC"
                          fontSize="11"
                          fontWeight="600"
                        >
                          {node.title}
                        </text>
                        <text
                          x="10"
                          y="51"
                          fill="#94A3B8"
                          fontSize="9.5"
                          fontFamily="monospace"
                        >
                          {node.subtitle}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Right Column: Selected Node Inspector + BEAST Causal Edges */}
              <div className="lg:col-span-4 rounded-lg border border-slate-800 bg-[#0B0F19] p-4 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="text-xs font-mono text-cyan-400">
                    {selectedGraphNode.planeLabel}
                  </div>
                  <h4 className="text-sm font-semibold text-white">
                    {selectedGraphNode.title}
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {selectedGraphNode.detail}
                  </p>
                </div>

                <div className="border-t border-slate-800 pt-3 space-y-2">
                  <div className="text-xs font-mono text-slate-400">
                    BEAST / SPIDER #8183 Active Ontology Links
                  </div>
                  <ul className="space-y-1.5 text-xs">
                    {snap.beastGraphEdges.map((edge) => (
                      <li
                        key={edge.id}
                        className="font-mono text-[11px] text-slate-300 flex items-start justify-between gap-2"
                      >
                        <span className="truncate" title={`${edge.fromEntity} -> ${edge.toEntity}`}>
                          {edge.relation}: {edge.toEntity}
                        </span>
                        <span
                          className={
                            edge.activeInLoop ? 'text-emerald-400 shrink-0' : 'text-amber-400 shrink-0'
                          }
                        >
                          {edge.activeInLoop ? 'BOUND' : 'PENDING'}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* 7-Stage Independently Observable Custody Pipeline */}
            {activeObligation && (
              <div className="border-t border-slate-800 pt-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="font-mono text-slate-300">
                    Selected Obligation:{' '}
                    <span className="text-white font-semibold">{activeObligation.obligationId}</span> ·{' '}
                    <span>{activeObligation.title}</span>
                  </div>
                  <div className="font-mono text-slate-400 tabular-nums">
                    Custodian: {activeObligation.currentCustodianWorkflow} · Fence:{' '}
                    {activeObligation.currentFencingToken > 0
                      ? `f_${activeObligation.currentFencingToken}`
                      : 'unleased'}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                  {CANONICAL_STAGES.map((st, idx) => {
                    const reached = activeObligation.transitions.some((t) => t.toStage === st);
                    const isCurrent = activeObligation.stage === st;
                    return (
                      <div
                        key={st}
                        className={`rounded-lg border px-3 py-2.5 font-mono text-xs ${
                          isCurrent
                            ? 'border-cyan-400 bg-cyan-950/50 text-white'
                            : reached
                              ? 'border-emerald-700/70 bg-emerald-950/25 text-emerald-300'
                              : 'border-slate-800 bg-slate-900/60 text-slate-500'
                        }`}
                      >
                        <div className="text-[10px] text-slate-400">0{idx + 1}</div>
                        <div className="font-semibold mt-0.5">{st}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          {/* Five Composed Planes Summary Strip */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                Five Composed Reactive Planes (Existing Meridian Systems Joined, Zero Parallel Bloat)
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                Graph informs · Gateway controls effects · Workflow retains custody
              </span>
            </div>
            <div className="divide-y divide-slate-200 border-t border-slate-200">
              {snap.fivePlanes.map((plane) => (
                <div
                  key={plane.id}
                  className="py-3.5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2 text-xs"
                >
                  <div className="space-y-0.5 max-w-2xl">
                    <div className="font-semibold text-slate-900">{plane.title}</div>
                    <div className="text-slate-600">{plane.governingRule}</div>
                    <div className="text-slate-500 font-mono text-[11px]">
                      {plane.constituents.join(' · ')}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 font-mono tabular-nums shrink-0">
                    <span className="text-slate-700">{plane.liveMetricLabel}</span>
                    <span
                      className={
                        plane.sandboxStatus === 'OPERATIONAL_VERIFIED'
                          ? 'text-emerald-700 font-semibold'
                          : 'text-amber-700 font-semibold'
                      }
                    >
                      Engine: {plane.sandboxStatus}
                    </span>
                    <span className="text-amber-700">
                      WAN: {plane.crossHostProductionStatus}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Split Grid: Workforce Discovery Table + Durable Obligations & Transition Receipts */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Workforce Discovery & QUAD Admission */}
            <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">
                    Living Workforce Discovery &amp; QUAD Admission Matrix
                  </h3>
                  <p className="text-xs text-slate-600">
                    Enforces <code className="font-mono">Idle != Available</code>,{' '}
                    <code className="font-mono">Connected != Capable</code>, and Ed25519 attestation.
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void invokeReactivityAction(
                      { action: 'restore_workers' },
                      'restore_workers'
                    )
                  }
                  className="min-h-[36px] inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  Restore Crashed Workers
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-2 pr-3 font-medium">Participant / Runtime</th>
                      <th className="py-2 px-3 font-medium">QUAD Identity</th>
                      <th className="py-2 px-3 font-medium text-right">Quota</th>
                      <th className="py-2 px-3 font-medium">Lease / Diagnosis</th>
                      <th className="py-2 pl-3 font-medium text-right">Fault Probe</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {snap.participants.map((p) => (
                      <tr key={p.agentId} className="hover:bg-slate-50/80">
                        <td className="py-2.5 pr-3 align-top">
                          <div className="font-semibold text-slate-900">{p.displayName}</div>
                          <div className="font-mono text-[11px] text-slate-500">
                            {p.connectivity} · {p.workloadState} · HB {p.lastHeartbeatAgeMs}ms
                          </div>
                        </td>
                        <td className="py-2.5 px-3 align-top font-mono text-[11px]">
                          <span
                            className={
                              p.quadIdentityMode === 'ED25519_ATTESTED'
                                ? 'text-emerald-700 font-semibold'
                                : 'text-red-700 font-semibold'
                            }
                          >
                            {p.quadIdentityMode}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 align-top text-right font-mono tabular-nums">
                          {p.remainingQuotaPct}%
                        </td>
                        <td className="py-2.5 px-3 align-top max-w-[230px]">
                          <div className="text-slate-700">{p.availabilityDiagnosis}</div>
                        </td>
                        <td className="py-2.5 pl-3 align-top text-right">
                          {p.surfaceClass === 'CLOUD_EXECUTOR' || p.surfaceClass === 'CLI_WORKER' ? (
                            <button
                              type="button"
                              disabled={busyKey !== null || p.connectivity === 'CRASHED'}
                              onClick={() =>
                                void invokeReactivityAction(
                                  { action: 'crash_worker', workerId: p.agentId },
                                  `crash_${p.agentId}`
                                )
                              }
                              className="rounded border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 whitespace-nowrap"
                            >
                              Simulate Crash
                            </button>
                          ) : (
                            <span className="font-mono text-[11px] text-slate-400">Protected</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Durable Obligations + Live Causal Transition Feed */}
            <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
              <div className="space-y-2">
                <h3 className="text-base font-semibold text-slate-900">
                  Durable Obligations &amp; Causal Receipts
                </h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!customEscalationTitle.trim()) return;
                    void invokeReactivityAction(
                      {
                        action: 'observe_custom_escalation',
                        title: customEscalationTitle.trim(),
                      },
                      'custom_obs'
                    );
                    setCustomEscalationTitle('');
                  }}
                  className="flex gap-2"
                >
                  <label htmlFor="founder-custom-escalation" className="sr-only">
                    Inject Founder escalation into BEAST/SPIDER
                  </label>
                  <input
                    id="founder-custom-escalation"
                    type="text"
                    value={customEscalationTitle}
                    onChange={(e) => setCustomEscalationTitle(e.target.value)}
                    placeholder="Inject live P0/P1 escalation (auto-dispatches & verifies)…"
                    className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={busyKey !== null || !customEscalationTitle.trim()}
                    className="min-h-[36px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                  >
                    <Send className="h-3.5 w-3.5" aria-hidden="true" />
                    Inject
                  </button>
                </form>
              </div>

              {/* Obligation Selector List */}
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {snap.obligations.map((obl) => {
                  const selected = obl.obligationId === activeObligation?.obligationId;
                  return (
                    <button
                      key={obl.obligationId}
                      type="button"
                      onClick={() => setSelectedObligationId(obl.obligationId)}
                      className={`w-full text-left rounded-lg border p-2.5 text-xs transition-colors ${
                        selected
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : 'border-slate-200 bg-slate-50 text-slate-900 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 font-mono">
                        <span className="font-semibold">
                          {obl.priority} · {obl.obligationId}
                        </span>
                        <span
                          className={
                            selected
                              ? 'text-cyan-300'
                              : obl.stage === 'VERIFIED'
                                ? 'text-emerald-700 font-semibold'
                                : 'text-amber-700 font-semibold'
                          }
                        >
                          {obl.stage}
                        </span>
                      </div>
                      <div className={`mt-0.5 truncate ${selected ? 'text-slate-200' : 'text-slate-600'}`}>
                        {obl.title}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Transitions for Selected Obligation */}
              {activeObligation && (
                <div className="border-t border-slate-200 pt-3 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                    <span>Merkle Lineage: {activeObligation.merkleLineageSha256.slice(0, 16)}…</span>
                    <span>Converged: {activeObligation.convergedDuplicateCount}x</span>
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {activeObligation.transitions
                      .slice()
                      .reverse()
                      .map((tr) => (
                        <div
                          key={`${tr.stepIndex}-${tr.receiptSha256}`}
                          className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs space-y-1"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-1 font-mono text-[11px] text-slate-600">
                            <span className="font-semibold text-slate-900">
                              #{tr.stepIndex} {tr.fromStage} → {tr.toStage} [{tr.omniflowVerb}]
                            </span>
                            <span>
                              {tr.fencingToken ? `f_${tr.fencingToken} · ` : ''}
                              {tr.observedLatencyMs}ms
                            </span>
                          </div>
                          <div className="text-slate-700 leading-snug">{tr.summary}</div>
                          <div className="font-mono text-[10px] text-slate-400">
                            Actor: {tr.actorId} · SHA {tr.receiptSha256.slice(0, 12)}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* VIEW 3: 10/10 CERT SUITE, LTL MODEL CHECK & EXPERIMENTS (A-F)       */}
      {/* =================================================================== */}
      {view === 'experiments_sla' && (
        <div className="space-y-6">
          <FounderMccConvergencePanel
            mcc={snap.mccConvergence}
            mode="cert_suite_ltl"
            busyKey={busyKey}
            onInvokeAction={invokeReactivityAction}
          />
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Executable Ship-and-Prove Acceptance Contracts (Experiments A–F)
                </h3>
                <p className="text-xs text-slate-600 font-mono">
                  DESIGN → IMPLEMENT → INTEGRATE → DEPLOY → OBSERVE → FALSIFY → CORRECT → CONTINUE
                </p>
              </div>
              <button
                type="button"
                disabled={busyKey !== null}
                onClick={() =>
                  void invokeReactivityAction(
                    { action: 'run_all_experiments' },
                    'run_all_experiments'
                  )
                }
                className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
              >
                <Play className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                Execute All 6 Experiments Now
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {EXPERIMENT_BUTTONS.map((btn) => {
                const executed = snap.experiments.find((e) => e.experimentId === btn.id);
                return (
                  <div
                    key={btn.id}
                    className="rounded-xl border border-slate-200 p-4 flex flex-col justify-between gap-3"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-2 text-xs font-mono">
                        <span className="font-semibold text-slate-900">{btn.id}</span>
                        <span
                          className={
                            executed?.passedInEngine
                              ? 'text-emerald-700 font-semibold'
                              : 'text-slate-500'
                          }
                        >
                          {executed
                            ? executed.passedInEngine
                              ? `PASS (${executed.durationMs}ms)`
                              : 'FAIL'
                            : 'READY'}
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-slate-900">{btn.shortLabel}</div>
                      <p className="text-xs text-slate-600">{btn.subtitle}</p>

                      {executed && (
                        <ul className="pt-2 border-t border-slate-100 space-y-1 text-xs">
                          {executed.keyAssertions.map((a) => (
                            <li key={a.check} className="text-slate-700">
                              <span className="font-mono font-semibold text-emerald-700">
                                {a.passed ? 'OK' : 'ERR'}
                              </span>{' '}
                              · {a.check}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <button
                      type="button"
                      disabled={busyKey !== null}
                      onClick={() =>
                        void invokeReactivityAction(
                          { action: 'run_experiment', experimentId: btn.id },
                          `exp_${btn.id}`
                        )
                      }
                      className="min-h-[38px] w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-900 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
                    >
                      {busyKey === `exp_${btn.id}` ? 'Running…' : `Run ${btn.id}`}
                    </button>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Quantitative SLA Benchmark Table */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="text-base font-semibold text-slate-900">
              Quantitative Autonomy &amp; Recovery Benchmarks (Calibrated vs Cross-Host Baseline)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-medium">ID</th>
                    <th className="py-2 px-3 font-medium">Metric</th>
                    <th className="py-2 px-3 font-medium font-mono">Target</th>
                    <th className="py-2 px-3 font-medium font-mono">Measured Engine</th>
                    <th className="py-2 pl-3 font-medium">Observed Estate Cross-Host Baseline</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {snap.quantitativeBenchmarks.map((row) => (
                    <tr key={row.metricId}>
                      <td className="py-2.5 pr-3 font-mono text-slate-500">{row.metricId}</td>
                      <td className="py-2.5 px-3 font-medium text-slate-900">{row.metric}</td>
                      <td className="py-2.5 px-3 font-mono tabular-nums text-slate-700">
                        {row.engineeringTarget}
                      </td>
                      <td className="py-2.5 px-3 font-mono tabular-nums font-semibold text-emerald-700">
                        {row.measuredSandboxValue}
                      </td>
                      <td className="py-2.5 pl-3 text-slate-600">{row.estateCrossHostBaseline}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* =================================================================== */}
      {/* VIEW 4: IDP/CROSS-REPO RECONCILIATION & 14-BOUNDARY REALITY AUDIT   */}
      {/* =================================================================== */}
      {view === 'estate_audit' && (
        <div className="space-y-6">
          <FounderMccConvergencePanel
            mcc={snap.mccConvergence}
            mode="reconciliation_mandate"
            busyKey={busyKey}
            onInvokeAction={invokeReactivityAction}
          />
          {/* 4 Source Investigation Findings */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Source-Level Investigation Findings (`bin/estate-fleet` · OMNIFLOW · Passkey Worker)
              </h3>
              <p className="text-xs text-slate-600">
                All four root defects discovered in existing estate coordination code are now guarded fail-closed in the reactivity engine.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {snap.sourceDefectFindings.map((f) => (
                <div key={f.id} className="rounded-xl border border-slate-200 p-4 space-y-1.5 text-xs">
                  <div className="flex items-center justify-between font-mono text-slate-500">
                    <span className="font-semibold text-slate-900">
                      {f.id} · {f.component}
                    </span>
                    <span className="text-emerald-700 font-semibold">{f.falsifierGuardStatus}</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-900">{f.defectTitle}</div>
                  <p className="text-slate-600">
                    <strong>Observed:</strong> {f.observedReality}
                  </p>
                  <p className="text-slate-800">
                    <strong>Correction:</strong> {f.architecturalCorrection}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* 14-Boundary Estate-Wide Investigation Matrix */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  14-Boundary Estate-Wide Execution &amp; Communication Reality Matrix
                </h3>
                <p className="text-xs text-slate-600">
                  Classified strictly across <code className="font-mono">operating</code>,{' '}
                  <code className="font-mono">partial</code>, <code className="font-mono">dormant</code>, and{' '}
                  <code className="font-mono">unknown</code> — never conflating branch code with live cross-host deployment.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-1 bg-slate-100 p-1 rounded-lg">
                {(['all', 'operating', 'partial', 'dormant', 'unknown'] as const).map((statusKey) => (
                  <button
                    key={statusKey}
                    type="button"
                    onClick={() => setAuditFilter(statusKey)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                      auditFilter === statusKey
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {statusKey === 'all' ? 'All (14)' : statusKey}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-medium">Surface / Workforce</th>
                    <th className="py-2 px-3 font-medium">Classification</th>
                    <th className="py-2 px-3 font-medium">Runtime Owner &amp; Deployment</th>
                    <th className="py-2 px-3 font-medium">Primary Failure Mode</th>
                    <th className="py-2 pl-3 font-medium">Reproducible Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredAuditRows.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50/80">
                      <td className="py-3 pr-3 align-top">
                        <div className="font-semibold text-slate-900">{row.boundary}</div>
                        <div className="text-slate-500 mt-0.5">{row.mustEstablish}</div>
                      </td>
                      <td className="py-3 px-3 align-top font-mono font-semibold">
                        <span
                          className={
                            row.classification === 'operating'
                              ? 'text-emerald-700'
                              : row.classification === 'partial'
                                ? 'text-blue-700'
                                : 'text-amber-700'
                          }
                        >
                          {row.classification.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-3 align-top">
                        <div className="font-mono text-[11px] text-slate-900">{row.runtimeOwner}</div>
                        <div className="text-slate-600 mt-0.5">{row.currentDeployment}</div>
                      </td>
                      <td className="py-3 px-3 align-top text-slate-600">{row.primaryFailureModes}</td>
                      <td className="py-3 pl-3 align-top text-slate-700">{row.reproducibleEvidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {view === 'team_handoff' && <TeamHandoffExportPanel />}
    </div>
  );
}
