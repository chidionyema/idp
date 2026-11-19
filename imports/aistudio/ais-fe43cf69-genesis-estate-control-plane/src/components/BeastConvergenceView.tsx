import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  AlertOctagon,
  Sliders,
  Download,
  Copy,
  Check,
  Sparkles,
  ArrowUpRight,
} from 'lucide-react';
import type {
  BeastGovernorState,
  BeastDynamicDials,
  BeastPosturePreset,
  BeastFaultKind,
} from '../engine/beastGovernor';
import type { NavTab } from '../App';

interface BeastConvergenceViewProps {
  initialBeast: BeastGovernorState;
  onRefreshState: () => Promise<void>;
  onNavigateTab: (tab: NavTab) => void;
}

export const BeastConvergenceView: React.FC<BeastConvergenceViewProps> = ({
  initialBeast,
  onRefreshState,
  onNavigateTab,
}) => {
  const [beast, setBeast] = useState<BeastGovernorState>(initialBeast);
  const [draftDials, setDraftDials] = useState<BeastDynamicDials>(initialBeast.dials);
  const [uiFilter, setUiFilter] = useState<'ALL' | 'ALERTS'>('ALL');
  const [regoTab, setRegoTab] = useState<'LIVE_REGO' | 'IDP_PI_AUDIT'>('LIVE_REGO');
  const [resourceTab, setResourceTab] = useState<'COMPUTE_HARNESS' | 'MODELS_FREE' | 'BITWARDEN_VAULTS'>('COMPUTE_HARNESS');
  const [dreamScenario, setDreamScenario] = useState(
    'Simultaneous MacBook sleep + Bitwarden lease rotation + 0-test Pytest exit during PR #7981 merge'
  );
  const [copiedRego, setCopiedRego] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{
    tone: 'emerald' | 'amber' | 'rose';
    message: string;
  } | null>(null);

  useEffect(() => {
    setBeast(initialBeast);
    setDraftDials(initialBeast.dials);
  }, [initialBeast]);

  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    const onBeastPulse = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as { beastGovernor?: BeastGovernorState };
        if (parsed.beastGovernor) {
          setBeast(parsed.beastGovernor);
          setDraftDials(parsed.beastGovernor.dials);
        }
      } catch {
        // Ignore malformed frame
      }
    };
    es.addEventListener('beast-pulse', onBeastPulse);
    return () => {
      es.removeEventListener('beast-pulse', onBeastPulse);
      es.close();
    };
  }, []);

  const greenUiCount = beast.uiSurfaceProbes.filter(
    (u) => u.contractStatus === 'PROVEN_GREEN'
  ).length;
  const evaluatedSessionsCount = beast.monitoredSessions.filter(
    (s) => s.realtimeEvalAttached
  ).length;
  const provenLayerCount = beast.fractalLayers.filter(
    (l) => l.verdict === 'PROVEN_CONSISTENT'
  ).length;

  const filteredUiProbes =
    uiFilter === 'ALERTS'
      ? beast.uiSurfaceProbes.filter((u) => u.contractStatus !== 'PROVEN_GREEN')
      : beast.uiSurfaceProbes;

  const handleRunSweep = async () => {
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/beast/sweep', { method: 'POST' });
      const data = await res.json();
      if (data.beastGovernor) {
        const next = data.beastGovernor as BeastGovernorState;
        setBeast(next);
        setFeedback({
          tone: next.allLayersConsistent ? 'emerald' : 'amber',
          message: `Continuous CI Sweep #${next.sweepSequence} completed: ${provenLayerCount}/6 Fractal Layers proven · ${greenUiCount}/${next.uiSurfaceProbes.length} UI Surfaces green · Root ${next.fractalConsistencyRootSha256.slice(0, 14)}.`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleApplyPreset = async (preset: BeastPosturePreset) => {
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/beast/dials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ applyPreset: preset }),
      });
      const data = await res.json();
      if (data.beastGovernor) {
        const next = data.beastGovernor as BeastGovernorState;
        setBeast(next);
        setDraftDials(next.dials);
        setFeedback({
          tone: 'emerald',
          message: `Applied Rego Posture "${preset}" across all 8 Beast Organs and recomputed Fractal Merkle Root (${next.fractalConsistencyRootSha256.slice(0, 12)}).`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleSaveCustomDials = async () => {
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/beast/dials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draftDials),
      });
      const data = await res.json();
      if (data.beastGovernor) {
        const next = data.beastGovernor as BeastGovernorState;
        setBeast(next);
        setDraftDials(next.dials);
        setFeedback({
          tone: 'emerald',
          message: `Dynamic Founder Dials persisted in < 1 ms · Wake-up target set to ${data.evalVerdict?.selectedWakeupTarget || 'LOCAL_MAC_CONSOLE'} · Policy digest ${String(data.evalVerdict?.policyDigestSha256 || '').slice(0, 12)}.`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleInjectFault = async (faultKind: BeastFaultKind) => {
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/beast/inject-fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faultKind }),
      });
      const data = await res.json();
      if (data.beastGovernor) {
        setBeast(data.beastGovernor as BeastGovernorState);
        setDraftDials((data.beastGovernor as BeastGovernorState).dials);
      }
      if (data.incident) {
        setFeedback({
          tone: 'rose',
          message: `Disruptive Incident ${data.incident.incidentId} raised across all 12 UI surfaces · Diagnosis Pack ${data.incident.diagnosisPack.diagPackId} dispatched to ${data.incident.diagnosisPack.selectedWakeupSurface}.`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleRunDreams = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dreamScenario.trim()) {
      setFeedback({
        tone: 'amber',
        message: 'Enter a failure scenario for Dreams counterfactual rehearsal.',
      });
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/beast/dreams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: dreamScenario.trim() }),
      });
      const data = await res.json();
      if (data.beastGovernor) {
        setBeast(data.beastGovernor as BeastGovernorState);
      }
      if (data.dream) {
        setFeedback({
          tone: 'emerald',
          message: `Dreams Cycle ${data.dream.dreamId} simulated ${data.dream.counterfactualBranchesSimulated} branches on Free Lane ($0.00) and crystallized ${data.dream.synthesizedAntibodyId}.`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleCopyRego = async () => {
    try {
      await navigator.clipboard.writeText(beast.activeRegoSource);
      setCopiedRego(true);
      window.setTimeout(() => setCopiedRego(false), 2000);
    } catch {
      setFeedback({
        tone: 'amber',
        message: 'Compiled estate.rego ready for download via button above.',
      });
    }
  };

  return (
    <div className="space-y-8">
      {/* Executive Hero & Fault Drill Bar */}
      <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
              <span>@meridian-estate/beast-governor</span>
              <span aria-hidden="true">·</span>
              <span>Sweep #{beast.sweepSequence}</span>
              <span aria-hidden="true">·</span>
              <span>Posture: {beast.dials.preset}</span>
              <span aria-hidden="true">·</span>
              <span>
                Status: {beast.allLayersConsistent ? '6/6 Layers Proven Consistent' : 'Incident Hold Active'}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50 [text-wrap:balance]">
              The Beast · Fractal Continuous Proof &amp; Declarative Rego Governor
            </h1>

            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              Unifies Chronos, Tempo, Otto, IO, Legion, Memory, Dreams, and Mandatory Real-Time Evaluation into one recursive invariant: every session is scored live, every resource and Bitwarden lease is tracked, {beast.regoConsolidationStats.convertiblePercentage}% of imperative harness logic collapses into dynamic Rego dials, and any breach triggers sub-millisecond wake-up across Browser, Console, or Always-On Cloud.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={busy}
              onClick={handleRunSweep}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} aria-hidden="true" />
              Run Continuous CI Sweep
            </button>

            <a
              href="/api/beast/rego"
              download="estate.rego"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              estate.rego
            </a>

            <a
              href="/api/beast/bin-beast"
              download="beast"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              bin/beast
            </a>
          </div>
        </div>

        {/* Full-Width 4-Column Proof KPI Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Fractal Layer Consistency</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {provenLayerCount}/6 Layers
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400 truncate">
              Merkle {beast.fractalConsistencyRootSha256.slice(0, 16)}
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Continuous UI Surface CI</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {greenUiCount}/{beast.uiSurfaceProbes.length} Green
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              DOM vs API parity &le; 16.0 ms
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Mandatory Session Eval</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {evaluatedSessionsCount}/{beast.monitoredSessions.length} Live
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              Zero unevaluated sessions law
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">IDP &amp; Pi Rego Conversion</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {beast.regoConsolidationStats.convertiblePercentage}%
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              {beast.regoConsolidationStats.totalLegacyImperativeLoc.toLocaleString()} LOC &rarr; {beast.regoConsolidationStats.totalDeclarativeRegoLoc} Rego LOC
            </div>
          </div>
        </div>

        {/* Live Pre-Failure Fault Drill Controls */}
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-200 dark:border-slate-800">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            <span className="font-semibold text-slate-900 dark:text-slate-200">
              Live All-Surface Incident Drills:
            </span>{' '}
            Inject a real boundary breach to verify sub-ms quarantine, Diagnosis Pack creation, and Browser / Console / Cloud wake-up.
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => handleInjectFault('UNEVALUATED_SESSION')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/70 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <AlertOctagon className="w-3.5 h-3.5" aria-hidden="true" />
              Inject Unevaluated Session
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => handleInjectFault('UI_SURFACE_DRIFT')}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Inject UI Surface Drift
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => handleInjectFault('BITWARDEN_LEASE_EXPIRED')}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Expire Bitwarden Lease
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => handleInjectFault('LOCAL_MAC_OFFLINE_FAILOVER')}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Simulate Mac Offline
            </button>
          </div>
        </div>

        {feedback && (
          <div
            role="status"
            className={`p-3 rounded-lg border text-xs font-mono ${
              feedback.tone === 'emerald'
                ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/70 text-emerald-800 dark:text-emerald-300'
                : feedback.tone === 'rose'
                  ? 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800/70 text-red-800 dark:text-red-300'
                  : 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/70 text-amber-800 dark:text-amber-300'
            }`}
          >
            {feedback.message}
          </div>
        )}
      </section>

      {/* 01. Fractal Six-Layer Consistency & All-12-UI-Surfaces Continuous CI */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col justify-between space-y-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              01. Recursive Six-Layer Proof Stack
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Solving invariants at Ring 0 aligns policy, resources, agents, WAL, and UI in real time.
            </p>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 border-t border-b border-slate-200 dark:border-slate-800">
            {beast.fractalLayers.map((layer) => {
              const ok = layer.verdict === 'PROVEN_CONSISTENT';
              return (
                <div key={layer.layerId} className="py-3 space-y-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                      {layer.title}
                    </span>
                    <span
                      className={`text-[11px] font-mono tabular-nums whitespace-nowrap shrink-0 ${
                        ok
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400 font-semibold'
                      }`}
                    >
                      {ok ? 'PROVEN' : 'BREACH'} · {layer.assertionsPassed}/{layer.assertionsTotal} ·{' '}
                      {layer.latencyMs.toFixed(2)} ms
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400">{layer.summary}</p>
                  <div className="text-[11px] font-mono tabular-nums text-slate-400 dark:text-slate-500">
                    SHA-256: {layer.layerSha256.slice(0, 24)}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
            Recursive Root SHA-256: {beast.fractalConsistencyRootSha256.slice(0, 32)}...
          </div>
        </div>

        <div className="lg:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                Continuous UI Surface CI (All {beast.uiSurfaceProbes.length} Views)
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Every frontend route is continuously probed against its backend API contract and Merkle state.
              </p>
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg shrink-0">
              <button
                type="button"
                onClick={() => setUiFilter('ALL')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  uiFilter === 'ALL'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                All Surfaces ({beast.uiSurfaceProbes.length})
              </button>
              <button
                type="button"
                onClick={() => setUiFilter('ALERTS')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  uiFilter === 'ALERTS'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Drift Alerts ({beast.uiSurfaceProbes.length - greenUiCount})
              </button>
            </div>
          </div>

          {filteredUiProbes.length === 0 ? (
            <div className="py-12 text-center border border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                Zero UI Surface Drift Alerts
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                All {beast.uiSurfaceProbes.length} founder and investor surfaces are verified green within their frame budgets.
              </p>
              <button
                type="button"
                onClick={() => setUiFilter('ALL')}
                className="px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 rounded-md"
              >
                Show All {beast.uiSurfaceProbes.length} Surfaces
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2 pr-3">Surface &amp; Route</th>
                    <th className="py-2 px-3">Bound Door</th>
                    <th className="py-2 px-3 text-right">Latency / Budget</th>
                    <th className="py-2 pl-3 text-right">CI Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {filteredUiProbes.map((probe) => {
                    const tabSlug = probe.routeHash.replace('#', '') as NavTab;
                    const green = probe.contractStatus === 'PROVEN_GREEN';
                    return (
                      <tr
                        key={probe.surfaceId}
                        className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors"
                      >
                        <td className="py-2.5 pr-3">
                          <button
                            type="button"
                            onClick={() => onNavigateTab(tabSlug)}
                            className="inline-flex items-center gap-1 font-medium text-slate-900 dark:text-slate-100 hover:text-amber-600 dark:hover:text-amber-400 transition-colors text-left"
                          >
                            <span>{probe.title}</span>
                            <ArrowUpRight className="w-3 h-3 shrink-0 opacity-70" aria-hidden="true" />
                          </button>
                          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                            {probe.routeHash} · Eval Hooked
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                          {probe.boundApiEndpoint}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-[11px] text-slate-700 dark:text-slate-300 whitespace-nowrap">
                          {probe.observedLatencyMs.toFixed(1)} ms / {probe.renderBudgetMs} ms
                        </td>
                        <td
                          className={`py-2.5 pl-3 text-right font-mono tabular-nums text-[11px] font-semibold whitespace-nowrap ${
                            green
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {green ? 'PROVEN GREEN' : 'DRIFT ALERT'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* 02. Eight-Organ Beast Convergence, Mandatory Session Eval & Dreams */}
      <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
            02. Eight-Organ Beast Convergence, Mandatory Session Eval &amp; Dreams
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Chronos, Tempo, Otto, IO, Legion, Memory, Dreams, and Realtime Eval operate as one synchronized organism—making un-evaluated research sessions structurally impossible.
          </p>
        </div>

        {/* 8 Beast Organs Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border border-slate-200 dark:border-slate-800 rounded-lg divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800">
          {beast.organs.slice(0, 4).map((organ) => (
            <div key={organ.organId} className="p-4 space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {organ.name}
                </span>
                <span className="text-[11px] font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
                  {organ.latencyMs.toFixed(2)} ms
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400">{organ.role}</p>
              <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                {organ.proofMetric}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 border border-slate-200 dark:border-slate-800 rounded-lg divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800">
          {beast.organs.slice(4, 8).map((organ) => {
            const alert = organ.status === 'ALERT_ACTION_REQUIRED';
            return (
              <div key={organ.organId} className="p-4 space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {organ.name}
                  </span>
                  <span
                    className={`text-[11px] font-mono tabular-nums ${
                      alert
                        ? 'text-red-600 dark:text-red-400 font-semibold'
                        : 'text-emerald-600 dark:text-emerald-400'
                    }`}
                  >
                    {alert ? 'QUARANTINE' : `${organ.latencyMs.toFixed(2)} ms`}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{organ.role}</p>
                <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                  {organ.proofMetric}
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
          {/* Mandatory Session Real-Time Eval Ledger */}
          <div className="lg:col-span-7 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Live Session Real-Time Evaluation Enforcement
              </h3>
              <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
                Rule: ZERO_UNEVALUATED_SESSIONS
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2 px-3">Session &amp; Steward</th>
                    <th className="py-2 px-3">Surface</th>
                    <th className="py-2 px-3 text-right">Gate Score</th>
                    <th className="py-2 px-3 text-right">Enforcement</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {beast.monitoredSessions.map((ses) => {
                    const quarantined = ses.status === 'QUARANTINED_NO_EVAL';
                    return (
                      <tr key={ses.sessionId}>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-slate-900 dark:text-slate-100">
                            {ses.actorRealName}
                          </div>
                          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                            {ses.sessionId}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300">
                          {ses.surface}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-800 dark:text-slate-200">
                          {ses.evalGateScore}/100 ({ses.lastEvalLatencyMs.toFixed(2)} ms)
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono text-[11px] font-semibold whitespace-nowrap ${
                            quarantined
                              ? 'text-red-600 dark:text-red-400'
                              : ses.status === 'SANDBOX_GRIP_LOOSENED'
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-emerald-600 dark:text-emerald-400'
                          }`}
                        >
                          {ses.status}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Dreams Counterfactual Consolidation Lab */}
          <div className="lg:col-span-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Dreams · Counterfactual Failure Rehearsal ($0 Free Lane)
            </h3>
            <form onSubmit={handleRunDreams} className="space-y-2.5">
              <label htmlFor="beast-dream-input" className="block text-xs text-slate-600 dark:text-slate-400">
                Synthetic multi-fault scenario to rehearse before it happens in production:
              </label>
              <div className="flex gap-2">
                <input
                  id="beast-dream-input"
                  type="text"
                  value={dreamScenario}
                  onChange={(e) => setDreamScenario(e.target.value)}
                  className="flex-1 min-w-0 px-3 py-2 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
                >
                  <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
                  Run Dreams Cycle
                </button>
              </div>
            </form>

            <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg max-h-52 overflow-y-auto">
              {beast.dreamCycles.slice(0, 4).map((d) => (
                <div key={d.dreamId} className="p-3 space-y-1 text-xs">
                  <div className="flex items-center justify-between font-mono tabular-nums text-[11px] text-slate-500 dark:text-slate-400">
                    <span>
                      {d.dreamId} · {d.counterfactualBranchesSimulated} branches · Free Lane
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      {d.synthesizedAntibodyId}
                    </span>
                  </div>
                  <div className="text-slate-800 dark:text-slate-200 font-medium">
                    {d.rehearsedFailureScenario}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    {d.regoTighteningSuggestion}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 03. Declarative Rego Policy Engine & Dynamic Founder Dials */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              03. Dynamic Founder Dials (&ldquo;Enforce Everything, Loosen Deliberately&rdquo;)
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Every boundary across IDP, Pi-extensions, Bitwarden, and Legion exposes a real-time dial bound to <code className="font-mono">data.dials</code> in <code className="font-mono">estate.rego</code>.
            </p>
          </div>

          {/* Posture Preset Switcher */}
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
              Constitutional Grip Preset
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {(
                [
                  { id: 'MAXIMUM_LOCKDOWN', label: 'Maximum Lockdown' },
                  { id: 'PRODUCTION_AUTONOMOUS', label: 'Production Auto' },
                  { id: 'RAPID_RND_SANDBOX', label: 'R&D Looser Grip' },
                ] as const
              ).map((p) => {
                const active = draftDials.preset === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    disabled={busy}
                    onClick={() => handleApplyPreset(p.id)}
                    className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                      active
                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-amber-400 dark:text-slate-950 dark:border-amber-400 font-semibold'
                        : 'bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Numeric Sliders */}
          <div className="space-y-4 pt-1">
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <label htmlFor="dial-min-tests" className="font-medium text-slate-700 dark:text-slate-300">
                  Min Test Collection Floor (Pi / CI Gate)
                </label>
                <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-amber-300">
                  {draftDials.minTestCollectionCount} tests
                </span>
              </div>
              <input
                id="dial-min-tests"
                type="range"
                min={0}
                max={30}
                step={1}
                value={draftDials.minTestCollectionCount}
                onChange={(e) =>
                  setDraftDials((d) => ({ ...d, minTestCollectionCount: Number(e.target.value) }))
                }
                className="w-full accent-amber-500"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <label htmlFor="dial-confidence" className="font-medium text-slate-700 dark:text-slate-300">
                  Min Epistemic Confidence Floor
                </label>
                <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-amber-300">
                  {draftDials.minEpistemicConfidencePct}%
                </span>
              </div>
              <input
                id="dial-confidence"
                type="range"
                min={60}
                max={99}
                step={1}
                value={draftDials.minEpistemicConfidencePct}
                onChange={(e) =>
                  setDraftDials((d) => ({ ...d, minEpistemicConfidencePct: Number(e.target.value) }))
                }
                className="w-full accent-amber-500"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <label htmlFor="dial-token-cap" className="font-medium text-slate-700 dark:text-slate-300">
                  Session Token Budget Before Free-Lane Reroute
                </label>
                <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-amber-300">
                  {draftDials.maxSessionTokenBudget.toLocaleString()} tok
                </span>
              </div>
              <input
                id="dial-token-cap"
                type="range"
                min={16000}
                max={200000}
                step={8000}
                value={draftDials.maxSessionTokenBudget}
                onChange={(e) =>
                  setDraftDials((d) => ({ ...d, maxSessionTokenBudget: Number(e.target.value) }))
                }
                className="w-full accent-amber-500"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <label htmlFor="dial-wakeup-sla" className="font-medium text-slate-700 dark:text-slate-300">
                  Incident Wake-Up Guarantee SLA
                </label>
                <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-amber-300">
                  &le; {draftDials.incidentWakeupSlaMs} ms
                </span>
              </div>
              <input
                id="dial-wakeup-sla"
                type="range"
                min={2}
                max={50}
                step={1}
                value={draftDials.incidentWakeupSlaMs}
                onChange={(e) =>
                  setDraftDials((d) => ({ ...d, incidentWakeupSlaMs: Number(e.target.value) }))
                }
                className="w-full accent-amber-500"
              />
            </div>
          </div>

          {/* Hard Boundary Toggles */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draftDials.requireRealtimeEvalOnEverySession}
                onChange={(e) =>
                  setDraftDials((d) => ({
                    ...d,
                    requireRealtimeEvalOnEverySession: e.target.checked,
                  }))
                }
                className="rounded accent-amber-500"
              />
              <span className="text-slate-800 dark:text-slate-200">
                Enforce Real-Time Eval on All Sessions
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draftDials.bitwardenStrictLeaseRequired}
                onChange={(e) =>
                  setDraftDials((d) => ({
                    ...d,
                    bitwardenStrictLeaseRequired: e.target.checked,
                  }))
                }
                className="rounded accent-amber-500"
              />
              <span className="text-slate-800 dark:text-slate-200">
                Strict Bitwarden Scoped Lease
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draftDials.localMacConsoleAvailable}
                onChange={(e) =>
                  setDraftDials((d) => ({
                    ...d,
                    localMacConsoleAvailable: e.target.checked,
                  }))
                }
                className="rounded accent-amber-500"
              />
              <span className="text-slate-800 dark:text-slate-200">
                Local MacBook Console Online
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={draftDials.disruptiveAllSurfaceAlertAudio}
                onChange={(e) =>
                  setDraftDials((d) => ({
                    ...d,
                    disruptiveAllSurfaceAlertAudio: e.target.checked,
                  }))
                }
                className="rounded accent-amber-500"
              />
              <span className="text-slate-800 dark:text-slate-200">
                Loud Disruptive Alert Audio
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer sm:col-span-2">
              <input
                type="checkbox"
                checked={draftDials.allowDirectMainPush}
                onChange={(e) =>
                  setDraftDials((d) => ({
                    ...d,
                    allowDirectMainPush: e.target.checked,
                  }))
                }
                className="rounded accent-amber-500"
              />
              <span className="text-slate-800 dark:text-slate-200">
                Loosen Protected <code className="font-mono">main</code> Branch Lock (Keep Off in Production)
              </span>
            </label>
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={handleSaveCustomDials}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap"
          >
            <Sliders className="w-3.5 h-3.5" aria-hidden="true" />
            Apply Dials &amp; Re-Verify All 6 Layers
          </button>
        </div>

        {/* Right Column: Live Compiled Rego + IDP / Pi-Extension Consolidation Audit */}
        <div className="lg:col-span-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col justify-between space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg">
              <button
                type="button"
                onClick={() => setRegoTab('LIVE_REGO')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  regoTab === 'LIVE_REGO'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Compiled estate.rego
              </button>
              <button
                type="button"
                onClick={() => setRegoTab('IDP_PI_AUDIT')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  regoTab === 'IDP_PI_AUDIT'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                IDP &amp; Pi Rego Audit ({beast.regoConsolidationStats.convertiblePercentage}%)
              </button>
            </div>

            {regoTab === 'LIVE_REGO' && (
              <button
                type="button"
                onClick={handleCopyRego}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg whitespace-nowrap shrink-0"
              >
                {copiedRego ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedRego ? 'Copied Rego' : 'Copy Policy'}
              </button>
            )}
          </div>

          {regoTab === 'LIVE_REGO' ? (
            <pre className="flex-1 p-4 bg-slate-950 text-slate-100 rounded-lg text-[11px] leading-relaxed font-mono overflow-x-auto max-h-[430px] overflow-y-auto border border-slate-800">
              {beast.activeRegoSource}
            </pre>
          ) : (
            <div className="space-y-3 overflow-y-auto max-h-[430px]">
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {beast.regoConsolidationStats.convertiblePercentage}% of scattered imperative checks in IDP, Pi-extensions, and agent harnesses are pure policy decisions—replacing {beast.regoConsolidationStats.totalLegacyImperativeLoc.toLocaleString()} brittle lines with {beast.regoConsolidationStats.totalDeclarativeRegoLoc} declarative Rego lines while keeping only raw crypto, PTY sockets, and 500 Hz motor PWM in native code:
              </p>
              <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
                {beast.regoConsolidationStats.modules.map((m) => (
                  <div key={m.moduleId} className="p-3 space-y-1 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {m.legacySurface}
                      </span>
                      <span className="font-mono tabular-nums text-emerald-600 dark:text-emerald-400 whitespace-nowrap shrink-0">
                        {m.convertiblePct}% Rego ({m.legacyImperativeLoc} &rarr; {m.declarativeRegoLoc} LOC)
                      </span>
                    </div>
                    <div className="font-mono text-[11px] text-amber-700 dark:text-amber-300 [overflow-wrap:anywhere]">
                      Rule: {m.regoPackageRule}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      {m.imperativeRemainderNote}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
            Latest Rego Eval: {beast.recentPolicyReceipts[0]?.evalId || 'REGO-INIT'} ·{' '}
            {beast.recentPolicyReceipts[0]?.durationMs.toFixed(2) || '0.34'} ms · Wake-Up Route:{' '}
            {beast.recentPolicyReceipts[0]?.selectedWakeupTarget || 'LOCAL_MAC_CONSOLE'}
          </div>
        </div>
      </section>

      {/* 04. Estate Resource, Free-Lane, Bitwarden & Wake-Up Ledger */}
      <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              04. Complete Estate Resource, Free-Lane &amp; Bitwarden Inventory
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Authoritative real-time tracking across Compute Machines, Wake-Up Harnesses (WebAgent Browsers, Console, Always-On Cloud), Zero-Cost Free Lanes, and Scoped Bitwarden Vaults.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg shrink-0">
            <button
              type="button"
              onClick={() => setResourceTab('COMPUTE_HARNESS')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                resourceTab === 'COMPUTE_HARNESS'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              Compute &amp; Wake-Up Harnesses
            </button>
            <button
              type="button"
              onClick={() => setResourceTab('MODELS_FREE')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                resourceTab === 'MODELS_FREE'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              Models, Tokens &amp; Free Lanes
            </button>
            <button
              type="button"
              onClick={() => setResourceTab('BITWARDEN_VAULTS')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                resourceTab === 'BITWARDEN_VAULTS'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              Bitwarden &amp; Secret Vaults
            </button>
          </div>
        </div>

        {resourceTab === 'COMPUTE_HARNESS' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2 px-3">Compute Machine</th>
                    <th className="py-2 px-3 text-right">CPU / RAM</th>
                    <th className="py-2 px-3 text-right">Heartbeat</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {beast.resources.computeNodes.map((node) => (
                    <tr key={node.machineId}>
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                          {node.name}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {node.wakeupCapability}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300 whitespace-nowrap">
                        {node.cpuUtilizationPct}% · {node.memoryUsedGb}/{node.memoryTotalGb} GB
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-mono tabular-nums text-[11px] font-semibold whitespace-nowrap ${
                          node.status === 'ONLINE_NOMINAL'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {node.status === 'ONLINE_NOMINAL'
                          ? `ONLINE (${node.heartbeatLatencyMs.toFixed(1)} ms)`
                          : 'SLEEP -> CLOUD'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2 px-3">Incident Wake-Up Harness</th>
                    <th className="py-2 px-3 text-right">Warm Pool</th>
                    <th className="py-2 px-3 text-right">Wake SLA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {beast.resources.executionHarnesses.map((h) => (
                    <tr key={h.harnessId}>
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-slate-900 dark:text-slate-100">{h.name}</div>
                        <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                          {h.scopedCapabilities.join(' · ')}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300 whitespace-nowrap">
                        {h.warmWorkers}/{h.maxWorkers} workers
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-mono tabular-nums text-[11px] font-semibold whitespace-nowrap ${
                          h.status === 'READY_HOT'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {h.status === 'READY_HOT' ? `${h.wakeupLatencyMs.toFixed(1)} ms HOT` : 'STANDBY'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {resourceTab === 'MODELS_FREE' && (
          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                  <th className="py-2 px-3">Legion Model / Free Lane</th>
                  <th className="py-2 px-3">Model Identifier</th>
                  <th className="py-2 px-3 text-right">RPM Headroom</th>
                  <th className="py-2 px-3 text-right">Tokens Today</th>
                  <th className="py-2 px-3 text-right">Cost Today</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                {beast.resources.modelAndFreeLanes.map((lane) => (
                  <tr key={lane.laneId}>
                    <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-slate-100">
                      {lane.name}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                      {lane.modelIdentifier}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                      {lane.rpmAvailable.toLocaleString()} / {lane.rpmLimit.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                      {lane.tokensUsedToday.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">
                      ${lane.costUsdToday.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {resourceTab === 'BITWARDEN_VAULTS' && (
          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                  <th className="py-2 px-3">Vault / Credential Broker</th>
                  <th className="py-2 px-3">Task Scoping &amp; Audit Note</th>
                  <th className="py-2 px-3 text-right">Scoped Items</th>
                  <th className="py-2 px-3 text-right">Lease Status &amp; TTL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                {beast.resources.secretVaults.map((v) => {
                  const expired = v.leaseStatus === 'EXPIRED_LOCKED';
                  return (
                    <tr key={v.vaultId}>
                      <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-slate-100">
                        {v.name}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                        {v.auditNote}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                        {v.scopedItemsCount}
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-mono tabular-nums text-[11px] font-semibold whitespace-nowrap ${
                          expired
                            ? 'text-red-600 dark:text-red-400'
                            : v.leaseStatus === 'BOUNDARY_SCOPED_U'
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-emerald-600 dark:text-emerald-400'
                        }`}
                      >
                        {v.leaseStatus} ({v.leaseRemainingSec}s)
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
