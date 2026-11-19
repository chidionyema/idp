import { Fragment, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Download,
  Flame,
  Lock,
  Play,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  XCircle,
} from 'lucide-react';
import type {
  BootStageId,
  PhoenixControlSnapshot,
} from '../types/api';
import { SystemFirstIocExplorer } from './SystemFirstIocExplorer';

type SubViewId = 'pipeline_forces' | 'estate_fsm' | 'ioc_anti_confusion' | 'unblock_immunity';

const STAGE_FAULT_OPTIONS: Array<{ id: BootStageId; label: string }> = [
  { id: 'STAGE_1_UNPACK', label: 'Stage 1 · Bundle Unpack Fault' },
  { id: 'STAGE_2_CLEAN_BUILD', label: 'Stage 2 · Clean Build Fault' },
  { id: 'STAGE_3_PROOFS_FSM', label: 'Stage 3 · FSM Dead-End Fault' },
  { id: 'STAGE_4_EXTERNAL_PROBES', label: 'Stage 4 · OKE Ghost IP 193.x Fault' },
  { id: 'STAGE_5_ROUND_TABLE', label: 'Stage 5 · Quorum Drop Fault' },
];

export function PhoenixRoundTablePanel() {
  const [snapshot, setSnapshot] = useState<PhoenixControlSnapshot | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [runningDrill, setRunningDrill] = useState(false);
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [decisionBanner, setDecisionBanner] = useState<{
    kind: 'error' | 'success';
    text: string;
  } | null>(null);
  const [subView, setSubView] = useState<SubViewId>('pipeline_forces');
  const [expandedForceId, setExpandedForceId] = useState<string | null>(null);
  const [selectedFaultStage, setSelectedFaultStage] = useState<BootStageId>(
    'STAGE_4_EXTERNAL_PROBES'
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetch('/api/phoenix/state')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: PhoenixControlSnapshot | null) => {
        if (active && data) {
          setSnapshot(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });

    // Authoritative SSE stream (/api/phoenix/stream) — zero client polling (I-8090)
    const es = new EventSource('/api/phoenix/stream');
    es.onopen = () => {
      if (active) setSseConnected(true);
    };
    es.addEventListener('phoenix_snapshot', (evt) => {
      try {
        const parsed = JSON.parse((evt as MessageEvent).data) as PhoenixControlSnapshot;
        if (active) {
          setSnapshot(parsed);
          setSseConnected(true);
          setLoading(false);
        }
      } catch {
        // Ignore malformed SSE frames cleanly
      }
    });
    es.onerror = () => {
      if (active) setSseConnected(false);
    };

    return () => {
      active = false;
      es.close();
    };
  }, []);

  async function triggerDrill(opts: {
    probeMode: 'LIVE_ESTATE' | 'CLEANROOM_REHEARSAL';
    simulateP0FaultStage?: BootStageId | null;
    triggerSource: 'FOUNDER_MANUAL' | 'SANDBOX_REHEARSAL' | 'FAULT_INJECTION_TEST';
  }) {
    setRunningDrill(true);
    setDecisionBanner(null);
    try {
      const res = await fetch('/api/phoenix/drill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          probeMode: opts.probeMode,
          triggerSource: opts.triggerSource,
          simulateP0FaultStage: opts.simulateP0FaultStage ?? null,
          runCleanRoomTsc: true,
        }),
      });
      const json = (await res.json()) as {
        snapshot?: PhoenixControlSnapshot;
        error?: string;
      };
      if (json.snapshot) {
        setSnapshot(json.snapshot);
      } else if (json.error) {
        setDecisionBanner({ kind: 'error', text: json.error });
      }
    } catch (err) {
      setDecisionBanner({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Unable to execute cold-boot drill',
      });
    } finally {
      setRunningDrill(false);
    }
  }

  async function submitFounderDecision(decision: 'GO' | 'ABORT') {
    setSubmittingDecision(true);
    setDecisionBanner(null);
    try {
      const res = await fetch('/api/phoenix/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reason:
            decision === 'GO'
              ? 'Founder Sovereign Seat authorized Go from Round Table cockpit.'
              : 'Founder invoked Emergency Quarantine Abort from Round Table cockpit.',
        }),
      });
      const json = (await res.json()) as {
        ok: boolean;
        error?: string;
        snapshot?: PhoenixControlSnapshot;
      };
      if (json.snapshot) {
        setSnapshot(json.snapshot);
      }
      if (!res.ok || !json.ok) {
        setDecisionBanner({
          kind: 'error',
          text: json.error || `HTTP ${res.status} — Action rejected fail-closed.`,
        });
      } else {
        setDecisionBanner({
          kind: 'success',
          text:
            decision === 'GO'
              ? '24-Hour Operational Seal minted and broadcast onto OMNIFLOW bus.'
              : 'Emergency Freeze active — autonomous dispatch locked and broadcast onto OMNIFLOW bus.',
        });
      }
    } catch (err) {
      setDecisionBanner({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Decision request failed',
      });
    } finally {
      setSubmittingDecision(false);
    }
  }

  function handleCopy(id: string, text: string) {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(text);
    }
    setCopiedId(id);
    setTimeout(() => {
      setCopiedId((cur) => (cur === id ? null : cur));
    }, 1800);
  }

  if (loading || !snapshot) {
    return (
      <div className="space-y-4" aria-busy="true">
        <div className="h-32 rounded-lg bg-white border border-slate-200 animate-pulse" />
        <div className="h-64 rounded-lg bg-white border border-slate-200 animate-pulse" />
      </div>
    );
  }

  const run = snapshot.currentRun;
  const forcesReady = run.forces.filter((f) => f.quorumState === 'SEATED_READY').length;
  const passedStages = run.stages.filter((s) => s.status === 'PASSED').length;
  const constitution = snapshot.constitutionReport;
  const seal = snapshot.activeSeal;

  const verdictLabel =
    run.overallVerdict === 'OPERATIONAL_100_PCT_SEALED'
      ? 'OPERATIONAL · 100% SEALED'
      : run.overallVerdict === 'QUORUM_READY_AWAITING_GO'
        ? 'QUORUM READY · AWAITING GO'
        : run.overallVerdict === 'FOUNDER_ABORTED_FREEZE'
          ? 'FOUNDER ABORT · FROZEN'
          : run.overallVerdict === 'RUNNING'
            ? 'DRILL EXECUTING LIVE'
            : run.overallVerdict === 'IDLE_UNINITIALIZED'
              ? 'STANDBY · RUN INITIAL DRILL'
              : 'CRITICAL P0 · QUARANTINED';

  const verdictColorClass =
    run.overallVerdict === 'OPERATIONAL_100_PCT_SEALED' ||
    run.overallVerdict === 'QUORUM_READY_AWAITING_GO'
      ? 'text-emerald-700'
      : run.overallVerdict === 'RUNNING' || run.overallVerdict === 'IDLE_UNINITIALIZED'
        ? 'text-amber-700'
        : 'text-red-700';

  return (
    <div className="space-y-6">
      {/* 1. Founder Driving Seat Command Header */}
      <section className="bg-white border border-slate-200 rounded-lg p-5 sm:p-6 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500">
              <span className="inline-flex items-center gap-1.5 font-semibold text-slate-900">
                <Flame className="h-3.5 w-3.5 text-slate-900" aria-hidden="true" />
                OPERATION PHOENIX v2
              </span>
              <span aria-hidden="true">·</span>
              <span>SCHEDULE {snapshot.dailyScheduleCronUtc}</span>
              <span aria-hidden="true">·</span>
              <span className={sseConnected ? 'text-emerald-700 font-medium' : 'text-amber-700'}>
                SSE {sseConnected ? 'LIVE' : 'CONNECTING'}
              </span>
              <span aria-hidden="true">·</span>
              <span className={`font-semibold ${verdictColorClass}`}>{verdictLabel}</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              Daily Cold-Boot &amp; Union Round Table Driving Seat
            </h2>
            <p className="text-sm text-slate-600 max-w-3xl">
              {run.founderReason || snapshot.zeroToleranceDoctrine}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={runningDrill}
              onClick={() =>
                void triggerDrill({
                  probeMode: 'LIVE_ESTATE',
                  triggerSource: 'FOUNDER_MANUAL',
                })
              }
              className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-4 min-h-[40px] text-xs font-semibold text-white hover:bg-slate-800 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              {runningDrill ? 'Executing Clean-Room Boot...' : 'Run Live Cold-Boot Drill'}
            </button>

            <button
              type="button"
              disabled={runningDrill}
              onClick={() =>
                void triggerDrill({
                  probeMode: 'CLEANROOM_REHEARSAL',
                  triggerSource: 'SANDBOX_REHEARSAL',
                })
              }
              className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3.5 min-h-[40px] text-xs font-medium text-slate-800 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
              Clean-Room Quorum Rehearsal
            </button>

            <a
              href="/api/phoenix/cli-script"
              className="inline-flex items-center justify-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 min-h-[40px] text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
              CLI Boot Script
            </a>
          </div>
        </div>

        {/* Single-Row Flat Hairline-Divided Sovereign Telemetry & Veto Strip */}
        <div className="border-t border-slate-200 pt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 bg-slate-50/60 rounded-md">
          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">24h Operations Seal</div>
            <div className="mt-1 flex items-center gap-1.5 text-sm font-semibold font-mono tabular-nums text-slate-900">
              {snapshot.autonomousDispatchAllowed ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" aria-hidden="true" />
                  <span className="truncate">{seal?.sealId}</span>
                </>
              ) : (
                <>
                  <Lock className="h-4 w-4 text-red-600 shrink-0" aria-hidden="true" />
                  <span>LOCKED · FAIL-CLOSED</span>
                </>
              )}
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500 truncate">
              {snapshot.autonomousDispatchAllowed
                ? seal?.sealKind ?? 'Active 24h Operations Seal'
                : seal?.revokedReason ?? 'No active seal minted'}
            </div>
          </div>

          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">Cold-Boot Stages &amp; Quorum</div>
            <div className="mt-1 text-sm font-semibold font-mono tabular-nums text-slate-900">
              {passedStages}/6 Stages · {forcesReady}/{run.forces.length} Forces
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500 font-mono truncate">
              HEAD {run.sourceHeadSha.slice(0, 10)} · {(run.bundleBytes / (1024 * 1024)).toFixed(2)} MiB
            </div>
          </div>

          <div className="px-3.5 py-2.5">
            <div className="text-[11px] font-medium text-slate-500">Closed-Loop FSM Constitution</div>
            <div className="mt-1 text-sm font-semibold font-mono tabular-nums text-slate-900">
              {constitution.provenClosedLoopCount}/{constitution.totalRegisteredFsms} FSMs Proven
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500">
              {constitution.totalEstateLayers}/6 Layers · Zero Dead-Ends
            </div>
          </div>

          <div className="px-3.5 py-2.5 flex flex-col justify-between gap-2">
            <div className="text-[11px] font-medium text-slate-500">Founder Sovereign Veto</div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={
                  submittingDecision ||
                  runningDrill ||
                  run.overallVerdict !== 'QUORUM_READY_AWAITING_GO'
                }
                onClick={() => void submitFounderDecision('GO')}
                className="flex-1 inline-flex items-center justify-center gap-1 rounded bg-emerald-700 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800 transition-colors whitespace-nowrap disabled:bg-slate-200 disabled:text-slate-500 disabled:cursor-not-allowed"
              >
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                Authorize Go
              </button>
              <button
                type="button"
                disabled={submittingDecision || runningDrill}
                onClick={() => void submitFounderDecision('ABORT')}
                className="flex-1 inline-flex items-center justify-center gap-1 rounded border border-red-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 transition-colors whitespace-nowrap disabled:opacity-50"
              >
                <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                Abort Freeze
              </button>
            </div>
          </div>
        </div>

        {/* Fault-Injection Control & Sub-View Underline Tabs */}
        <div className="border-t border-slate-200 pt-3 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-4 border-b xl:border-b-0 border-slate-200">
            <button
              type="button"
              onClick={() => setSubView('pipeline_forces')}
              className={`pb-2 xl:pb-0 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                subView === 'pipeline_forces'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              6-Stage Boot &amp; Round Table
            </button>
            <button
              type="button"
              onClick={() => setSubView('estate_fsm')}
              className={`pb-2 xl:pb-0 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                subView === 'estate_fsm'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              6-Layer Map &amp; 10 FSMs
            </button>
            <button
              type="button"
              onClick={() => setSubView('ioc_anti_confusion')}
              className={`pb-2 xl:pb-0 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                subView === 'ioc_anti_confusion'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              System-First IoC &amp; Anti-Confusion Gate
            </button>
            <button
              type="button"
              onClick={() => setSubView('unblock_immunity')}
              className={`pb-2 xl:pb-0 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                subView === 'unblock_immunity'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Unblock ({run.unblockPack.length}) &amp; Immunity ({snapshot.immunityLedger.length})
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <label htmlFor="phoenix-fault-stage" className="text-xs text-slate-500 whitespace-nowrap">
              Chaos Fault:
            </label>
            <select
              id="phoenix-fault-stage"
              value={selectedFaultStage}
              onChange={(e) => setSelectedFaultStage(e.target.value as BootStageId)}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              {STAGE_FAULT_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={runningDrill}
              onClick={() =>
                void triggerDrill({
                  probeMode: 'CLEANROOM_REHEARSAL',
                  simulateP0FaultStage: selectedFaultStage,
                  triggerSource: 'FAULT_INJECTION_TEST',
                })
              }
              className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
              Simulate P0 Fault
            </button>
          </div>
        </div>

        {decisionBanner && (
          <div
            role="status"
            className={`rounded-md border px-4 py-2.5 text-xs font-medium ${
              decisionBanner.kind === 'error'
                ? 'border-red-200 bg-red-50 text-red-800'
                : 'border-emerald-200 bg-emerald-50 text-emerald-800'
            }`}
          >
            {decisionBanner.text}
          </div>
        )}
      </section>

      {/* 2. Sub-View 1: 6-Stage Pipeline & 8-Force Round Table */}
      {subView === 'pipeline_forces' && (
        <div className="space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Stage 1–6 Clean-Room Cold-Boot Pipeline
                </h3>
                <p className="text-xs text-slate-500">
                  Drill {run.drillId} · Mode {run.probeMode} · Zero-tolerance binary gate
                </p>
              </div>
              <div className="text-xs font-mono tabular-nums text-slate-500">
                Bundle {run.bundleSha256.slice(0, 14)}…
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                    <th className="py-2.5 px-4">Stage</th>
                    <th className="py-2.5 px-4">Gate Verdict</th>
                    <th className="py-2.5 px-4">Latency</th>
                    <th className="py-2.5 px-4">Safe-Heal &amp; Verification Evidence</th>
                    <th className="py-2.5 px-4">Proof Digest</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {run.stages.map((st) => (
                    <tr key={st.stageId} className="hover:bg-slate-50/70">
                      <td className="py-3 px-4 font-medium text-slate-900 whitespace-nowrap">
                        <div>{st.order}. {st.title}</div>
                        <div className="font-mono text-[11px] text-slate-400">{st.stageId}</div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono font-semibold">
                        <span
                          className={
                            st.status === 'PASSED'
                              ? 'text-emerald-700'
                              : st.status === 'CRITICAL_FAILURE'
                                ? 'text-red-700'
                                : st.status === 'RUNNING'
                                  ? 'text-blue-700'
                                  : 'text-slate-500'
                          }
                        >
                          {st.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono tabular-nums text-slate-700">
                        {st.durationMs} ms
                      </td>
                      <td className="py-3 px-4 text-slate-700 max-w-lg">
                        <div>{st.summary}</div>
                        {st.failureClassCode && (
                          <div className="mt-1 font-mono text-[11px] text-red-700">
                            Class: {st.failureClassCode}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono tabular-nums text-slate-500">
                        {st.proofSha256.slice(0, 12)}…
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Union Round Table · All 8 Estate Forces Convened
                </h3>
                <p className="text-xs text-slate-500">
                  Click any force row to inspect external gaps and copy surgical unblock commands
                </p>
              </div>
              <div className="text-xs font-mono tabular-nums text-slate-700 font-semibold">
                {forcesReady}/{run.forces.length} SEATED_READY
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                    <th className="py-2.5 px-4">Force / Division</th>
                    <th className="py-2.5 px-4">Quorum Seat</th>
                    <th className="py-2.5 px-4">Clean-Room</th>
                    <th className="py-2.5 px-4">External Live</th>
                    <th className="py-2.5 px-4">Diagnostic Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {run.forces.map((force) => {
                    const isOpen = expandedForceId === force.forceId;
                    const seatColor =
                      force.quorumState === 'SEATED_READY'
                        ? 'text-emerald-700'
                        : force.quorumState === 'AWAITING_EXTERNAL_AUTH'
                          ? 'text-amber-700'
                          : 'text-red-700';
                    return (
                      <Fragment key={force.forceId}>
                        <tr
                          onClick={() =>
                            setExpandedForceId(isOpen ? null : force.forceId)
                          }
                          className="cursor-pointer hover:bg-slate-50"
                        >
                          <td className="py-3 px-4 font-medium text-slate-900">
                            <div>{force.forceName}</div>
                            <div className="text-[11px] font-mono text-slate-400">
                              {force.forceId} · {force.layer}
                            </div>
                          </td>
                          <td className={`py-3 px-4 whitespace-nowrap font-mono font-semibold ${seatColor}`}>
                            {force.quorumState}
                          </td>
                          <td className="py-3 px-4 whitespace-nowrap font-mono">
                            {force.cleanRoomVerified ? 'VERIFIED' : 'FAIL'}
                          </td>
                          <td className="py-3 px-4 whitespace-nowrap font-mono">
                            {force.externalLiveVerified ? 'LIVE_OK' : 'UNVERIFIED'}
                          </td>
                          <td className="py-3 px-4 text-slate-600 max-w-md">
                            {force.detail}
                          </td>
                        </tr>
                        {isOpen && (
                          <tr key={`${force.forceId}-detail`} className="bg-slate-50">
                            <td colSpan={5} className="px-5 py-3 text-xs text-slate-700 space-y-2">
                              <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-slate-500">
                                <span>Authority: {force.authorityScope}</span>
                                <span aria-hidden="true">·</span>
                                <span>Attestation: {force.attestationSha256.slice(0, 16)}…</span>
                              </div>
                              {force.remediationCommands.length > 0 ? (
                                <div className="space-y-1">
                                  <div className="font-semibold text-slate-900">
                                    Surgical Unblock Commands ({force.blockerCategory}):
                                  </div>
                                  <pre className="rounded border border-slate-200 bg-white p-2.5 font-mono text-[11px] text-slate-800 overflow-x-auto">
                                    {force.remediationCommands.join('\n')}
                                  </pre>
                                </div>
                              ) : (
                                <div className="text-emerald-700 font-medium">
                                  Zero pending remediation — force satisfies both clean-room and live checks.
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {run.externalHostProbes.length > 0 && (
            <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-900">
                  Outside-In Host &amp; Retired OKE Ghost-IP Probe Results
                </h3>
                <span className="text-xs font-mono text-slate-500">
                  {run.externalHostProbes.filter((h) => h.liveOk).length}/
                  {run.externalHostProbes.length} Live Healthy
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                      <th className="py-2.5 px-4">Target Host</th>
                      <th className="py-2.5 px-4">Verdict</th>
                      <th className="py-2.5 px-4">HTTP</th>
                      <th className="py-2.5 px-4">Resolved IPs</th>
                      <th className="py-2.5 px-4">Measured Detail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {run.externalHostProbes.map((hp) => (
                      <tr key={hp.host}>
                        <td className="py-2.5 px-4 font-mono text-slate-900">{hp.host}</td>
                        <td
                          className={`py-2.5 px-4 font-mono font-semibold whitespace-nowrap ${
                            hp.liveOk ? 'text-emerald-700' : 'text-red-700'
                          }`}
                        >
                          {hp.retiredOkeIpDetected
                            ? 'GHOST_IP_193_BLOCKED'
                            : hp.liveOk
                              ? 'MEASURED_OK'
                              : 'QUARANTINED_FAIL'}
                        </td>
                        <td className="py-2.5 px-4 font-mono tabular-nums text-slate-700">
                          {hp.httpStatus ?? '—'}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-slate-600">
                          {hp.resolvedIps.length > 0 ? hp.resolvedIps.join(', ') : 'NXDOMAIN / None'}
                        </td>
                        <td className="py-2.5 px-4 text-slate-600">{hp.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}

      {/* 3. Sub-View 2: Complete 6-Layer Estate Map & 10 Closed-Loop FSM Proofs */}
      {subView === 'estate_fsm' && (
        <div className="space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Five Mathematical Closed-Loop Laws (Enforced on Every Build)
                </h3>
                <p className="text-xs text-slate-500">
                  Constitution {constitution.constitutionSha256.slice(0, 16)}… · Zero open-loop or unregistered workflows permitted
                </p>
              </div>
              <span className="font-mono text-xs font-semibold text-emerald-700">
                {constitution.provenClosedLoopCount}/{constitution.totalRegisteredFsms} FSMs PROVEN
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {constitution.lawChecklist.map((law) => (
                <div key={law.lawId} className="border border-slate-200 rounded-md p-3.5 space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-semibold text-slate-900">{law.lawId}</span>
                    <span className={law.satisfied ? 'text-emerald-700 font-semibold' : 'text-red-700 font-semibold'}>
                      {law.satisfied ? 'SATISFIED' : 'VIOLATED'}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-slate-900">{law.title}</div>
                  <p className="text-xs text-slate-600">{law.guarantee}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h3 className="text-base font-semibold text-slate-900">
                10 Registered Estate Closed-Loop Finite State Machines
              </h3>
              <p className="text-xs text-slate-500">
                Every workflow satisfies forward reachability, reverse terminal closure, safe quarantine exit, and timeout boundedness
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                    <th className="py-2.5 px-4">FSM</th>
                    <th className="py-2.5 px-4">States / Edges</th>
                    <th className="py-2.5 px-4">Reachable</th>
                    <th className="py-2.5 px-4">Zero Dead-Ends</th>
                    <th className="py-2.5 px-4">Quarantine Exit</th>
                    <th className="py-2.5 px-4">Timeout Edge</th>
                    <th className="py-2.5 px-4">Theorem Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {constitution.fsmProofs.map((proof) => (
                    <tr key={proof.fsmId}>
                      <td className="py-3 px-4 font-medium text-slate-900">
                        <div>{proof.fsmId} · {proof.name}</div>
                        <div className="font-mono text-[11px] text-slate-400">
                          {proof.layer} · {proof.ownerForce}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono tabular-nums text-slate-700">
                        {proof.stateCount} / {proof.transitionCount}
                      </td>
                      <td className="py-3 px-4 font-mono text-emerald-700">
                        {proof.allStatesReachableFromInitial ? 'TRUE' : 'FALSE'}
                      </td>
                      <td className="py-3 px-4 font-mono text-emerald-700">
                        {proof.zeroDeadEndStates ? 'TRUE' : 'FALSE'}
                      </td>
                      <td className="py-3 px-4 font-mono text-emerald-700">
                        {proof.allActiveStatesHaveQuarantineExit ? 'TRUE' : 'FALSE'}
                      </td>
                      <td className="py-3 px-4 font-mono text-emerald-700">
                        {proof.allWaitingStatesHaveTimeoutEdge ? 'TRUE' : 'FALSE'}
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-emerald-700 whitespace-nowrap">
                        {proof.closedLoopProven ? 'PROVEN_CLOSED' : 'VIOLATION'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h3 className="text-base font-semibold text-slate-900">
                Complete 6-Layer Estate Architecture Map
              </h3>
            </div>
            <div className="divide-y divide-slate-200">
              {constitution.estateMap.map((layer) => (
                <div key={layer.layerId} className="p-5 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-slate-900">
                      Layer {layer.order} · {layer.title}
                    </div>
                    <div className="font-mono text-xs text-slate-500">
                      Bound FSMs: {layer.boundFsmIds.join(', ')}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 text-xs">
                    <div>
                      <div className="font-semibold text-slate-700 mb-1">Core Systems</div>
                      <ul className="space-y-1 text-slate-600 list-disc pl-4">
                        {layer.coreSystems.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="font-semibold text-emerald-800 mb-1">Verified Locally</div>
                      <ul className="space-y-1 text-slate-600 list-disc pl-4">
                        {layer.verifiedLocalCapabilities.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="font-semibold text-amber-800 mb-1">External Gates / Candid Gaps</div>
                      <ul className="space-y-1 text-slate-600 list-disc pl-4">
                        {layer.externalGapsOrGates.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* 3.5. Sub-View: System-First IoC, 4KB DNA & Anti-Confusion Gate Explorer */}
      {subView === 'ioc_anti_confusion' && <SystemFirstIocExplorer />}

      {/* 4. Sub-View 3: Surgical Unblock Pack & Inherited Immunity Ledger */}
      {subView === 'unblock_immunity' && (
        <div className="space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Surgical Unblock Pack (Split by Root-Cause Authority)
                </h3>
                <p className="text-xs text-slate-500">
                  Separates deterministic code/build issues from external credential, token &amp; DNS cutover commands
                </p>
              </div>
              <span className="font-mono text-xs font-semibold text-slate-700">
                {run.unblockPack.length} Open P0 Item(s)
              </span>
            </div>

            {run.unblockPack.length === 0 ? (
              <div className="border border-emerald-200 bg-emerald-50 rounded-md p-4 text-xs text-emerald-800 font-medium">
                Zero P0 blockers in current run — Ready for Founder Go Seal.
              </div>
            ) : (
              <div className="space-y-3">
                {run.unblockPack.map((item) => {
                  const cmdBlock = item.commands.join('\n');
                  return (
                    <div key={item.id} className="border border-slate-200 rounded-md p-4 space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2 text-xs font-mono">
                          <ShieldAlert className="h-4 w-4 text-red-600 shrink-0" aria-hidden="true" />
                          <span className="font-semibold text-slate-900">{item.title}</span>
                          <span className="text-slate-400">·</span>
                          <span className="text-red-700 font-semibold">{item.category}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleCopy(item.id, cmdBlock)}
                          className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                        >
                          {copiedId === item.id ? (
                            <>
                              <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                              Copy Commands
                            </>
                          )}
                        </button>
                      </div>
                      <p className="text-xs text-slate-600">{item.rootCause}</p>
                      <pre className="rounded border border-slate-200 bg-slate-50 p-2.5 font-mono text-[11px] text-slate-800 overflow-x-auto">
                        {cmdBlock}
                      </pre>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Inherited Immunity Ratchet (Chesed → Geburah Permanent Locks)
                </h3>
                <p className="text-xs text-slate-500">
                  Every failure class discovered during drills permanently locks an assertion into Stage 3/4 checks
                </p>
              </div>
              <Terminal className="h-4 w-4 text-slate-400" aria-hidden="true" />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                    <th className="py-2.5 px-4">Rule ID</th>
                    <th className="py-2.5 px-4">Failure Class Locked</th>
                    <th className="py-2.5 px-4">Stage</th>
                    <th className="py-2.5 px-4">Permanent Guard Assertion</th>
                    <th className="py-2.5 px-4">Hits</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {snapshot.immunityLedger.map((rule) => (
                    <tr key={rule.ruleId}>
                      <td className="py-2.5 px-4 font-mono font-semibold text-slate-900">
                        {rule.ruleId}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-red-700">
                        {rule.failureClassCode}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-slate-500">
                        {rule.originStageId}
                      </td>
                      <td className="py-2.5 px-4 text-slate-700">{rule.guardAssertion}</td>
                      <td className="py-2.5 px-4 font-mono tabular-nums text-slate-700">
                        {rule.triggeredCount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
