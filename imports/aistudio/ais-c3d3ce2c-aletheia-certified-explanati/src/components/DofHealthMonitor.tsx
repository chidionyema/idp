/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Area, AreaChart, Tooltip, YAxis } from 'recharts';
import {
  buildSystemProbeHealthMatrix,
  simulateComponentProbeTick,
  type ComponentProbeOverride,
  type CriticalComponentId,
  type DofEpisodeState,
  type DofLevel,
  type ProbeStatus,
} from '../core/dofGovernance';

interface DofHealthMonitorProps {
  episode: DofEpisodeState;
  onMemoryProbePass: () => void;
  onMemoryTriggerFailure: () => void;
  onComponentBannerUpdate: (message: string) => void;
}

function getProbeStatusStyle(status: ProbeStatus): {
  prefix: string;
  textClass: string;
  borderClass: string;
  bgClass: string;
} {
  switch (status) {
    case 'PASS':
      return {
        prefix: '● PASS',
        textClass: 'text-emerald-400',
        borderClass: 'border-emerald-500/40',
        bgClass: 'bg-emerald-950/25',
      };
    case 'FAIL':
      return {
        prefix: '✖ FAIL',
        textClass: 'text-rose-400',
        borderClass: 'border-rose-500/50',
        bgClass: 'bg-rose-950/35',
      };
    case 'CANNOT_RUN':
      return {
        prefix: '▲ NO-RUN',
        textClass: 'text-amber-300',
        borderClass: 'border-amber-500/50',
        bgClass: 'bg-amber-950/30',
      };
  }
}

function getLeaseBadgeStyle(level: DofLevel): {
  label: string;
  textClass: string;
  borderClass: string;
  bgClass: string;
  sparklineStroke: string;
  sparklineFill: string;
} {
  switch (level) {
    case 'L0':
      return {
        label: 'L0 · FULL LEASE',
        textClass: 'text-emerald-300',
        borderClass: 'border-emerald-500/50',
        bgClass: 'bg-emerald-950/30',
        sparklineStroke: '#10b981',
        sparklineFill: 'rgba(16, 185, 129, 0.22)',
      };
    case 'L1':
      return {
        label: 'L1 · DIAGNOSE ONLY',
        textClass: 'text-cyan-300',
        borderClass: 'border-cyan-500/50',
        bgClass: 'bg-cyan-950/30',
        sparklineStroke: '#22d3ee',
        sparklineFill: 'rgba(34, 211, 238, 0.22)',
      };
    case 'L2':
      return {
        label: 'L2 · REPAIR ONLY',
        textClass: 'text-amber-300',
        borderClass: 'border-amber-500/60',
        bgClass: 'bg-amber-950/35',
        sparklineStroke: '#f59e0b',
        sparklineFill: 'rgba(245, 158, 11, 0.24)',
      };
    case 'L3':
      return {
        label: 'L3 · FROZEN 🔴',
        textClass: 'text-rose-300',
        borderClass: 'border-rose-500/70',
        bgClass: 'bg-rose-950/45',
        sparklineStroke: '#f43f5e',
        sparklineFill: 'rgba(244, 63, 94, 0.28)',
      };
  }
}

export const DofHealthMonitor: React.FC<DofHealthMonitorProps> = ({
  episode,
  onMemoryProbePass,
  onMemoryTriggerFailure,
  onComponentBannerUpdate,
}) => {
  const [overrides, setOverrides] = useState<
    Partial<Record<CriticalComponentId, ComponentProbeOverride>>
  >({});
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);
  const [streamTickCount, setStreamTickCount] = useState<number>(1);
  const [lastHeartbeatIso, setLastHeartbeatIso] = useState<string>(
    '2026-11-04T17:30:46Z'
  );

  // Sync MEMORY-01 override whenever the parent episode resets or advances
  useEffect(() => {
    setOverrides((prev) => {
      if (!prev['MEMORY-01']) return prev;
      const next = { ...prev };
      delete next['MEMORY-01'];
      return next;
    });
  }, [
    episode.activeLevel,
    episode.consecutiveProbePasses,
    episode.completedRepairSteps.length,
    episode.founderOttOverrideActive,
  ]);

  // Real-time probe telemetry heartbeat (updates latency jitter & heartbeat clock)
  useEffect(() => {
    if (!isLiveStreaming) return;
    const timer = window.setInterval(() => {
      const nowIso = new Date().toISOString();
      setStreamTickCount((c) => c + 1);
      setLastHeartbeatIso(nowIso);
      setOverrides((prev) => {
        const updated: Partial<
          Record<CriticalComponentId, ComponentProbeOverride>
        > = { ...prev };
        (['DISK-01', 'XREC-GATE-01', 'ROUTER-01'] as CriticalComponentId[]).forEach(
          (cid, idx) => {
            const existing = updated[cid];
            if (existing) {
              updated[cid] = {
                ...existing,
                lastProbeLatencyMs: Math.max(
                  7,
                  ((existing.lastProbeLatencyMs + idx * 3 + 5) % 34) + 8
                ),
                lastProbeTimestamp: nowIso,
              };
            }
          }
        );
        return updated;
      });
    }, 2500);
    return () => window.clearInterval(timer);
  }, [isLiveStreaming]);

  const rows = buildSystemProbeHealthMatrix(episode, overrides);

  const totalVerifiedL0 = rows.filter((r) => r.activeLeaseLevel === 'L0').length;
  const totalFailures = rows.reduce((acc, r) => acc + r.failureCount, 0);
  const totalRestorePasses = rows.reduce(
    (acc, r) => acc + r.consecutiveRestorePasses,
    0
  );

  const handleRowProbeAction = (
    componentId: CriticalComponentId,
    mode: 'PASS_BOTH' | 'FAIL_BOTH' | 'FALSE_POSITIVE_A'
  ) => {
    const nowIso = new Date().toISOString();
    setLastHeartbeatIso(nowIso);

    if (componentId === 'MEMORY-01') {
      if (mode === 'PASS_BOTH') {
        onMemoryProbePass();
        return;
      }
      if (mode === 'FAIL_BOTH') {
        onMemoryTriggerFailure();
        return;
      }
    }

    const currentRow = rows.find((r) => r.componentId === componentId);
    const baseOverride: ComponentProbeOverride | undefined =
      overrides[componentId] ||
      (currentRow
        ? {
            methodAStatus: currentRow.methodAStatus,
            methodBStatus: currentRow.methodBStatus,
            failureCount: currentRow.failureCount,
            consecutiveRestorePasses: currentRow.consecutiveRestorePasses,
            lastProbeLatencyMs: currentRow.lastProbeLatencyMs,
            lastProbeTimestamp: currentRow.lastProbeTimestamp,
            auditTrendHistory: currentRow.auditTrendHistory,
          }
        : undefined);

    const nextOverride = simulateComponentProbeTick(
      baseOverride,
      mode,
      nowIso,
      currentRow?.auditTrendHistory
    );
    setOverrides((prev) => ({
      ...prev,
      [componentId]: nextOverride,
    }));

    if (mode === 'FAIL_BOTH') {
      onComponentBannerUpdate(
        `DOF HEALTH MONITOR: ${componentId} dual-method probe failed (1-Down) -> Component lease narrowed to L2 (repair.${componentId} only; hysteresis reset to 0/3).`
      );
    } else if (mode === 'FALSE_POSITIVE_A') {
      onComponentBannerUpdate(
        `DOF HEALTH MONITOR (Edge Case 1): ${componentId} Method A failed while Method B passed -> Disagreement holds component at L1 Diagnose-Only.`
      );
    } else {
      onComponentBannerUpdate(
        `DOF HEALTH MONITOR: ${componentId} dual probe PASS (${nextOverride.consecutiveRestorePasses}/3 consecutive passes verified).`
      );
    }
  };

  const handleResetAllComponentProbes = () => {
    setOverrides({});
    onComponentBannerUpdate(
      'DOF HEALTH MONITOR: Cleared manual component probe overrides; synchronized with active episode state.'
    );
  };

  return (
    <section
      aria-label="DoF Health Monitor Real-Time Probe Dashboard"
      className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-5"
    >
      {/* Top Header & Real-Time Stream Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
            <span className="text-cyan-300 font-semibold">
              REAL-TIME DOF HEALTH MONITOR
            </span>
            <span aria-hidden="true" className="text-slate-600">
              ·
            </span>
            <span
              className={
                isLiveStreaming ? 'text-emerald-400 font-semibold' : 'text-amber-300'
              }
            >
              {isLiveStreaming
                ? `● LIVE PROBE TELEMETRY (TICK #${streamTickCount})`
                : '▲ STREAM PAUSED'}
            </span>
            <span aria-hidden="true" className="text-slate-600">
              ·
            </span>
            <span className="text-slate-400 tabular-nums">
              Last Sweep: {lastHeartbeatIso.slice(11, 19)} UTC
            </span>
          </div>
          <h2 className="text-lg lg:text-xl font-bold text-slate-100 font-display">
            Priority-Ordered System Probe Matrix, 10-Cycle Epistemic Sparklines &amp; Lease Table
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsLiveStreaming((s) => !s)}
            className={`px-3 py-1.5 text-xs font-mono font-semibold rounded border transition-colors cursor-pointer ${
              isLiveStreaming
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/50 hover:border-emerald-400'
                : 'bg-[#111827] text-slate-300 border-slate-700 hover:border-cyan-400'
            }`}
          >
            {isLiveStreaming ? 'Pause Telemetry Stream' : 'Resume Telemetry Stream'}
          </button>
          <button
            type="button"
            onClick={handleResetAllComponentProbes}
            className="px-3 py-1.5 text-xs font-mono text-slate-300 bg-[#090D16] border border-slate-700 rounded hover:border-slate-500 transition-colors cursor-pointer"
          >
            Sync All Probes
          </button>
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-3.5 rounded bg-[#080B12] border border-slate-800/90 space-y-1">
          <div className="text-slate-400">Estate Effective Lease</div>
          <div className="text-base font-bold text-slate-100 tabular-nums">
            {episode.activeLevel} ·{' '}
            {episode.founderOttOverrideActive
              ? 'OTT OVERRIDE'
              : episode.activeLevel === 'L0'
                ? 'FULL RENT'
                : `RESTRICTED (${episode.failingComponent || 'HOLD'})`}
          </div>
        </div>

        <div className="p-3.5 rounded bg-[#080B12] border border-slate-800/90 space-y-1">
          <div className="text-slate-400">Verified L0 Subsystems</div>
          <div className="text-base font-bold text-emerald-400 tabular-nums">
            {totalVerifiedL0} / {rows.length} Components Verified
          </div>
        </div>

        <div className="p-3.5 rounded bg-[#080B12] border border-slate-800/90 space-y-1">
          <div className="text-slate-400">1-Down Failure Drops</div>
          <div className="text-base font-bold text-amber-300 tabular-nums">
            {totalFailures} Recorded Drop(s)
          </div>
        </div>

        <div className="p-3.5 rounded bg-[#080B12] border border-slate-800/90 space-y-1">
          <div className="text-slate-400">3-Up Hysteresis Passes</div>
          <div className="text-base font-bold text-cyan-300 tabular-nums">
            {totalRestorePasses} / {rows.length * 3} Aggregate Passes
          </div>
        </div>
      </div>

      {/* Dynamic System Probe, Sparkline & Capability Lease Table */}
      <div className="overflow-x-auto border border-slate-800/90 rounded-lg bg-[#080B12]">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-[#0A0F1A] font-mono text-[11px] uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4">Priority &amp; Component</th>
              <th className="py-3 px-4">Method A &amp; B Probes</th>
              <th className="py-3 px-4">Active Capability Lease</th>
              <th className="py-3 px-4">1-Down / 3-Up Counters</th>
              <th className="py-3 px-4">10-Cycle Epistemic Trend</th>
              <th className="py-3 px-4 text-right">Live Probe Simulation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80">
            {rows.map((row) => {
              const methodAStyle = getProbeStatusStyle(row.methodAStatus);
              const methodBStyle = getProbeStatusStyle(row.methodBStatus);
              const leaseStyle = getLeaseBadgeStyle(row.activeLeaseLevel);
              const latestCycle =
                row.auditTrendHistory[row.auditTrendHistory.length - 1];
              const minCycleScore = Math.min(
                ...row.auditTrendHistory.map((d) => d.healthScore)
              );

              return (
                <tr
                  key={row.componentId}
                  className="hover:bg-[#0C1220] transition-colors align-top"
                >
                  {/* Column 1: Priority & Component */}
                  <td className="py-3.5 px-4 space-y-1">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="px-1.5 py-0.5 rounded-sm bg-slate-800 text-cyan-300 font-bold text-[11px]">
                        {row.priorityTier}
                      </span>
                      <span className="font-bold text-slate-100 text-sm">
                        {row.componentId}
                      </span>
                    </div>
                    <div className="text-slate-300">{row.subsystemName}</div>
                    <div className="font-mono text-[11px] text-slate-400 tabular-nums">
                      Digest {row.probeDigest} · {row.lastProbeLatencyMs}ms
                    </div>
                  </td>

                  {/* Column 2: Dual Probe Methods (A & B) */}
                  <td className="py-3.5 px-4 space-y-1.5 font-mono">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded-sm border text-[10px] font-semibold ${methodAStyle.textClass} ${methodAStyle.borderClass} ${methodAStyle.bgClass}`}
                      >
                        A: {methodAStyle.prefix}
                      </span>
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded-sm border text-[10px] font-semibold ${methodBStyle.textClass} ${methodBStyle.borderClass} ${methodBStyle.bgClass}`}
                      >
                        B: {methodBStyle.prefix}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-sans">
                      {row.methodAName} / {row.methodBName}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {row.agreementState === 'AGREED_PASS'
                        ? 'Dual Consensus: 2/2 PASS'
                        : row.agreementState === 'AGREED_FAIL'
                          ? 'Dual Consensus: 2/2 FAIL (1-Down)'
                          : 'Single-Method Disagreement -> L1 Hold'}
                    </div>
                  </td>

                  {/* Column 3: Active Capability Lease */}
                  <td className="py-3.5 px-4 space-y-1.5">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-sm border font-mono text-[11px] font-bold ${leaseStyle.textClass} ${leaseStyle.borderClass} ${leaseStyle.bgClass}`}
                    >
                      {leaseStyle.label}
                    </span>
                    <div className="font-mono text-[11px] text-slate-300 leading-relaxed max-w-[230px]">
                      {row.rentedActionSpace}
                    </div>
                  </td>

                  {/* Column 4: Failure & Restoration Counters (1-Down / 3-Up) */}
                  <td className="py-3.5 px-4 space-y-2 font-mono tabular-nums">
                    <div className="flex items-center justify-between gap-3 text-[11px]">
                      <span className="text-slate-400">
                        Drops:{' '}
                        <strong
                          className={
                            row.failureCount > 0 ? 'text-rose-400' : 'text-slate-200'
                          }
                        >
                          {row.failureCount}
                        </strong>
                      </span>
                      <span className="text-slate-300">
                        Restore:{' '}
                        <strong
                          className={
                            row.consecutiveRestorePasses === 3
                              ? 'text-emerald-400'
                              : 'text-amber-300'
                          }
                        >
                          {row.consecutiveRestorePasses}/{row.requiredRestorePasses}
                        </strong>
                      </span>
                    </div>

                    {/* 3-Segment Hysteresis Progress Bar */}
                    <div
                      className="grid grid-cols-3 gap-1"
                      aria-label={`${row.componentId} restoration hysteresis ${row.consecutiveRestorePasses} of 3 passes`}
                    >
                      {[1, 2, 3].map((step) => {
                        const passed = row.consecutiveRestorePasses >= step;
                        return (
                          <div
                            key={step}
                            className={`h-2 rounded-sm ${
                              passed
                                ? 'bg-emerald-400'
                                : row.activeLeaseLevel === 'L3'
                                  ? 'bg-rose-900/70'
                                  : 'bg-slate-800'
                            }`}
                          />
                        );
                      })}
                    </div>
                  </td>

                  {/* Column 5: 10-Cycle Recharts Epistemic Trend Sparkline */}
                  <td className="py-3.5 px-4">
                    <div
                      className="w-[148px] space-y-1"
                      aria-label={`${row.componentId} 10-cycle failure and restoration sparkline trend`}
                    >
                      <div className="flex items-center justify-between font-mono text-[10px] tabular-nums">
                        <span className="text-slate-400">
                          C-9→C0 (Min {minCycleScore}%)
                        </span>
                        <span className={`font-bold ${leaseStyle.textClass}`}>
                          {latestCycle?.healthScore ?? 100}%
                        </span>
                      </div>
                      <div className="bg-[#05080F] border border-slate-800/90 rounded px-1 py-1">
                        <AreaChart
                          width={138}
                          height={38}
                          data={row.auditTrendHistory}
                          margin={{ top: 3, right: 3, left: 3, bottom: 2 }}
                        >
                          <YAxis domain={[0, 105]} hide />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#090D16',
                              border: '1px solid #334155',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontFamily: 'JetBrains Mono, monospace',
                              padding: '4px 6px',
                              color: '#f1f5f9',
                            }}
                            formatter={(value) => [`${value}% Health`, 'Lease Score']}
                            labelFormatter={(label) => `Cycle ${label}`}
                          />
                          <Area
                            type="monotone"
                            dataKey="healthScore"
                            stroke={leaseStyle.sparklineStroke}
                            strokeWidth={1.75}
                            fill={leaseStyle.sparklineFill}
                            isAnimationActive={false}
                          />
                        </AreaChart>
                      </div>
                    </div>
                  </td>

                  {/* Column 6: Interactive Row Controls */}
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex flex-wrap items-center justify-end gap-1.5 font-mono">
                      <button
                        type="button"
                        onClick={() => handleRowProbeAction(row.componentId, 'PASS_BOTH')}
                        className="px-2 py-1 text-[11px] text-emerald-300 bg-emerald-950/40 border border-emerald-500/40 rounded hover:border-emerald-400 transition-colors cursor-pointer"
                      >
                        +1 Pass
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          handleRowProbeAction(row.componentId, 'FALSE_POSITIVE_A')
                        }
                        className="px-2 py-1 text-[11px] text-cyan-300 bg-[#0F172A] border border-cyan-500/40 rounded hover:border-cyan-400 transition-colors cursor-pointer"
                      >
                        1/2 Anomaly (L1)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRowProbeAction(row.componentId, 'FAIL_BOTH')}
                        className="px-2 py-1 text-[11px] text-rose-300 bg-rose-950/35 border border-rose-500/40 rounded hover:border-rose-400 transition-colors cursor-pointer"
                      >
                        Dual Fail (L2)
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};
