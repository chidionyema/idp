import { useEffect, useState } from 'react';
import { CheckCircle2, Cpu, RefreshCw, ShieldAlert, Sparkles } from 'lucide-react';
import {
  DiscoveredModelEntry,
  LegionTaskClass,
  SmallVsFrontierBenchmark,
  TaskAdmissionDecision,
} from '../engine/modelSupply';
import type { WorkstreamStatus } from '../engine/estateWorkstreams';
import { SupplyApiResponse } from '../types/api';

const TASK_CLASSES: Array<{ id: LegionTaskClass; label: string }> = [
  { id: 'orchestration', label: 'Orchestration (MagenticBrain)' },
  { id: 'computer_use', label: 'Computer-Use Browser (Fara1.5)' },
  { id: 'routine_coding', label: 'Routine Coding (OpenCode Free)' },
  { id: 'independent_review', label: 'Independent Review (Escalation)' },
  { id: 'frontier_reasoning', label: 'Frontier Reasoning (Opus 4.1)' },
];

function formatAvailability(avail: DiscoveredModelEntry['availability']) {
  if (avail === 'ACTIVE') return { label: 'ACTIVE', cls: 'text-emerald-700' };
  if (avail === 'PRE_EXHAUSTION_DRAIN') return { label: 'PRE-EXHAUSTION', cls: 'text-amber-700' };
  if (avail === 'GEO_RESTRICTED') return { label: 'GEO-RESTRICTED', cls: 'text-red-700' };
  return { label: 'EXHAUSTED', cls: 'text-red-700' };
}

function formatRetention(policy: DiscoveredModelEntry['retentionPolicy']) {
  if (policy === 'zero_retention') return 'Zero Retention';
  if (policy === 'local_only') return 'Local / Private';
  return 'Provider Logged';
}

export function ModelSupplyIntelligence() {
  const [data, setData] = useState<SupplyApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sweeping, setSweeping] = useState(false);
  const [certifying, setCertifying] = useState(false);
  const [admitting, setAdmitting] = useState(false);
  const [benchmarking, setBenchmarking] = useState(false);
  const [updatingModelId, setUpdatingModelId] = useState<string | null>(null);
  const [certResultSummary, setCertResultSummary] = useState<string | null>(null);
  const [workstreamFilter, setWorkstreamFilter] = useState<'ALL' | WorkstreamStatus>('ALL');

  const [taskClass, setTaskClass] = useState<LegionTaskClass>('routine_coding');
  const [requiresZeroRetention, setRequiresZeroRetention] = useState(false);
  const [estimatedTokens, setEstimatedTokens] = useState(2400);
  const [regionCode, setRegionCode] = useState('us-west');

  const [decision, setDecision] = useState<TaskAdmissionDecision | null>(null);
  const [benchmark, setBenchmark] = useState<SmallVsFrontierBenchmark | null>(null);

  async function fetchSupply() {
    setLoading(true);
    try {
      const res = await fetch('/api/supply');
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleRunBenchmark(workloadTasks = 200) {
    setBenchmarking(true);
    try {
      const res = await fetch('/api/supply/benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workloadTasks }),
      });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
        if (json.benchmark) setBenchmark(json.benchmark);
      }
    } finally {
      setBenchmarking(false);
    }
  }

  useEffect(() => {
    void fetchSupply();
    void handleRunBenchmark(200);
  }, []);

  async function handleDiscoverSweep() {
    setSweeping(true);
    try {
      const res = await fetch('/api/supply/discover', { method: 'POST' });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
      }
    } finally {
      setSweeping(false);
    }
  }

  async function handleRunCertification() {
    setCertifying(true);
    try {
      const res = await fetch('/api/supply/certify', { method: 'POST' });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
        if (json.certificationProbe) {
          setCertResultSummary(
            `Certified ${json.certificationProbe.certifiedCount}/${json.certificationProbe.testedModels} lanes (quarantined: ${json.certificationProbe.quarantinedCount})`
          );
        }
      }
    } finally {
      setCertifying(false);
    }
  }

  async function handleOptimusOutcome(modelId: string, verified: boolean) {
    setUpdatingModelId(modelId);
    try {
      const res = await fetch('/api/supply/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelId, verified, latencyMs: verified ? 95 : 420 }),
      });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
      }
    } finally {
      setUpdatingModelId(null);
    }
  }

  async function handleQuotaUpdate(
    modelId: string,
    updates: { quotaRemainingPct?: number; geoAllowed?: boolean }
  ) {
    setUpdatingModelId(modelId);
    try {
      const res = await fetch('/api/supply/quota', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelId, ...updates }),
      });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
      }
    } finally {
      setUpdatingModelId(null);
    }
  }

  async function handleAdmitTask() {
    setAdmitting(true);
    try {
      const res = await fetch('/api/supply/admit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskClass,
          requiresZeroRetention,
          estimatedTokens,
          regionCode,
        }),
      });
      if (res.ok) {
        const json = (await res.json()) as SupplyApiResponse;
        setData(json);
        if (json.decision) setDecision(json.decision);
      }
    } finally {
      setAdmitting(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="h-32 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-80 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  const models = data?.models ?? [];
  const activeCount = models.filter((m) => m.availability === 'ACTIVE').length;
  const preExhaustionCount = models.filter(
    (m) => m.availability === 'PRE_EXHAUSTION_DRAIN' || m.availability === 'EXHAUSTED'
  ).length;
  const zeroRetentionCount = models.filter(
    (m) => m.retentionPolicy === 'zero_retention' || m.retentionPolicy === 'local_only'
  ).length;

  return (
    <div className="space-y-6">
      {/* Header & KPI Summary */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="max-w-2xl">
            <h2 className="text-base font-semibold text-slate-900">
              Model Supply &amp; Execution Intelligence (Battalion + Legion)
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Continuously discovers OpenCode free models, Microsoft Research small specialist models (MagenticBrain &amp; Fara1.5), Gemini quota, and frontier escalation pools with strict geo, retention, and pre-exhaustion drain guardrails.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              disabled={certifying}
              onClick={handleRunCertification}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
              {certifying ? 'Certifying...' : 'Run Capability Certification'}
            </button>
            <button
              type="button"
              disabled={sweeping}
              onClick={handleDiscoverSweep}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${sweeping ? 'animate-spin' : ''}`} aria-hidden="true" />
              {sweeping ? 'Discovering Supply...' : 'Run Supply Discovery Sweep'}
            </button>
          </div>
        </div>

        {certResultSummary && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs text-emerald-800">
            Independent Capability Probe: {certResultSummary}
          </div>
        )}

        <div className="mt-6 pt-5 border-t border-slate-200 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-slate-500">Discovery Cycle</div>
            <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-slate-900">
              #{data?.discoveryCycle ?? 1}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Certified Active Supply</div>
            <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-emerald-700">
              {activeCount} / {models.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Pre-Exhaustion / Drained</div>
            <div
              className={`mt-1 text-xl font-mono tabular-nums font-semibold ${
                preExhaustionCount > 0 ? 'text-amber-700' : 'text-slate-900'
              }`}
            >
              {preExhaustionCount}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Zero-Retention / Local Lanes</div>
            <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-slate-900">
              {zeroRetentionCount}
            </div>
          </div>
        </div>
      </section>

      {/* Discovered Model Supply Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Continuously Discovered Model Supply Matrix
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              15% pre-exhaustion drain threshold prevents mid-mission 429 drops. Provider terms and geo compliance are strictly enforced.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">
            Pre-exhaustion cutoff: &le;15% quota
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-4 font-medium">Model &amp; Source</th>
                <th className="py-2.5 px-4 font-medium">Specialist Role</th>
                <th className="py-2.5 px-4 font-medium">Availability</th>
                <th className="py-2.5 px-4 font-medium text-right">Quota %</th>
                <th className="py-2.5 px-4 font-medium">Retention Policy</th>
                <th className="py-2.5 px-4 font-medium text-right">Pass / Optimus</th>
                <th className="py-2.5 px-4 font-medium text-right">Cost / Outcome</th>
                <th className="py-2.5 px-4 font-medium text-right">Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {models.map((m) => {
                const avail = formatAvailability(m.availability);
                const busy = updatingModelId === m.id;
                return (
                  <tr key={m.id} className="hover:bg-slate-50/70">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">{m.name}</div>
                      <div className="text-[11px] text-slate-500">
                        {m.providerSource} &middot; <span className="font-mono">{m.id}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">{m.specializedRole}</td>
                    <td className={`py-3 px-4 font-semibold whitespace-nowrap ${avail.cls}`}>
                      {m.certification === 'UNVERIFIED' ? 'UNVERIFIED' : avail.label}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums font-medium text-slate-900">
                      {m.quotaRemainingPct}%
                    </td>
                    <td className="py-3 px-4 text-slate-700 whitespace-nowrap">
                      {formatRetention(m.retentionPolicy)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-900 whitespace-nowrap">
                      {m.capabilityPassRatePct.toFixed(1)}% &middot;{' '}
                      <span className="text-slate-500">{m.optimusPriorityScore.toFixed(1)}</span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-900">
                      ${m.costPerVerifiedOutcomeUsd.toFixed(6)}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5">
                        {m.quotaRemainingPct > 15 ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleQuotaUpdate(m.id, { quotaRemainingPct: 10 })}
                            className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                          >
                            Drain to 10%
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleQuotaUpdate(m.id, { quotaRemainingPct: 85 })}
                            className="rounded border border-emerald-300 bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
                          >
                            Restore 85%
                          </button>
                        )}
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleQuotaUpdate(m.id, { geoAllowed: !m.geoAllowed })}
                          className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          {m.geoAllowed ? 'Restrict Geo' : 'Allow Geo'}
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleOptimusOutcome(m.id, true)}
                          title="Record verified outcome to Optimus feedback loop"
                          className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-mono text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                        >
                          +Pass
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

      {/* Two-Column Split: Admission Simulator + Optimus Small vs Frontier Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Quota-Aware Task Admission Simulator */}
        <section className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-blue-600" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-slate-900">
                Quota-Aware Task Admission Simulator
              </h3>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Test Legion routing across task classes, zero-retention requirements, and pre-exhaustion drain states.
            </p>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <label className="block">
                <span className="font-medium text-slate-700">Task Class</span>
                <select
                  value={taskClass}
                  onChange={(e) => setTaskClass(e.target.value as LegionTaskClass)}
                  className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
                >
                  {TASK_CLASSES.map((tc) => (
                    <option key={tc.id} value={tc.id}>
                      {tc.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="font-medium text-slate-700">Estimated Tokens</span>
                <input
                  type="number"
                  min={200}
                  max={64000}
                  step={200}
                  value={estimatedTokens}
                  onChange={(e) => setEstimatedTokens(Number(e.target.value) || 2000)}
                  className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-blue-600 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="font-medium text-slate-700">Execution Region</span>
                <input
                  type="text"
                  value={regionCode}
                  onChange={(e) => setRegionCode(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-blue-600 focus:outline-none"
                />
              </label>

              <label className="flex items-center gap-2 pt-5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={requiresZeroRetention}
                  onChange={(e) => setRequiresZeroRetention(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                />
                <span className="font-medium text-slate-800">Require Zero-Retention</span>
              </label>
            </div>

            <div className="mt-4">
              <button
                type="button"
                disabled={admitting}
                onClick={handleAdmitTask}
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5 text-blue-400" aria-hidden="true" />
                {admitting ? 'Evaluating Policy...' : 'Admit Task'}
              </button>
            </div>
          </div>

          {decision && (
            <div className="mt-5 pt-4 border-t border-slate-200 space-y-3 text-xs">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-slate-500">Selected Execution Lane</div>
                  <div className="mt-0.5 text-sm font-semibold text-slate-900">
                    {decision.admitted ? decision.selectedModelName : 'Admission Blocked'}
                  </div>
                  <div className="mt-0.5 text-slate-600">{decision.decisionReason}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-slate-500">Savings vs Frontier</div>
                  <div className="mt-0.5 text-sm font-mono tabular-nums font-semibold text-emerald-700">
                    ${decision.savingsVsFrontierUsd.toFixed(6)}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 border border-slate-200 rounded-md p-3 bg-slate-50">
                <div>
                  <div className="text-[11px] text-slate-500">Pre-Exhaustion Fallback</div>
                  <div
                    className={`mt-0.5 font-mono font-semibold ${
                      decision.preExhaustionFallbackTriggered ? 'text-amber-700' : 'text-slate-900'
                    }`}
                  >
                    {decision.preExhaustionFallbackTriggered ? 'TRIGGERED' : 'NOMINAL'}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Estimated Cost</div>
                  <div className="mt-0.5 font-mono tabular-nums font-semibold text-slate-900">
                    ${decision.estimatedCostUsd.toFixed(6)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Frontier Escalation</div>
                  <div className="mt-0.5 font-mono font-semibold text-slate-900">
                    {decision.escalatedToFrontier ? 'SELECTIVE' : 'AVOIDED'}
                  </div>
                </div>
              </div>

              {decision.rejectedCandidates.length > 0 && (
                <div>
                  <div className="text-[11px] font-medium text-slate-600 mb-1.5">
                    Policy-Rejected Candidates ({decision.rejectedCandidates.length})
                  </div>
                  <ul className="space-y-1">
                    {decision.rejectedCandidates.map((rej) => (
                      <li
                        key={rej.modelId}
                        className="flex items-start justify-between gap-3 rounded border border-slate-200 px-2.5 py-1.5 bg-white"
                      >
                        <span className="font-mono text-slate-800">{rej.modelId}</span>
                        <span className="text-slate-600 text-right">{rej.reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Right: Optimus Benchmark: Small-Model Legion vs. Frontier-Everywhere */}
        <section className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Optimus Benchmark: Small-Model Legion vs. Frontier-Everywhere
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Compares MagenticBrain orchestration + Fara1.5 browser execution + OpenCode free coding + 10% selective review against unrouted frontier models.
                </p>
              </div>
              <button
                type="button"
                disabled={benchmarking}
                onClick={() => handleRunBenchmark(200)}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                {benchmarking ? 'Running...' : 'Re-Run 200-Task Benchmark'}
              </button>
            </div>

            {benchmark && (
              <div className="mt-5 space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 border border-slate-200 rounded-md p-4 bg-slate-50">
                  <div>
                    <div className="text-[11px] text-slate-500">Cost Reduction</div>
                    <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-emerald-700">
                      {benchmark.costReductionPct.toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500">Small-Model Share</div>
                    <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-slate-900">
                      {benchmark.smallOrchestration.smallModelSharePct.toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500">Net Savings ({benchmark.workloadTasks} tasks)</div>
                    <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-emerald-700">
                      ${benchmark.netSavingsUsd.toFixed(4)}
                    </div>
                  </div>
                </div>

                <div className="border border-slate-200 rounded-md overflow-hidden">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                        <th className="py-2 px-3 font-medium">Execution Strategy</th>
                        <th className="py-2 px-3 font-medium text-right">Total Cost</th>
                        <th className="py-2 px-3 font-medium text-right">Cost / Outcome</th>
                        <th className="py-2 px-3 font-medium text-right">p95 Latency</th>
                        <th className="py-2 px-3 font-medium text-right">Pass Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      <tr>
                        <td className="py-2.5 px-3 font-medium text-slate-900">
                          Legion Small + Selective Escalation
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-emerald-700 font-semibold">
                          ${benchmark.smallOrchestration.totalCostUsd.toFixed(4)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          ${benchmark.smallOrchestration.costPerVerifiedOutcomeUsd.toFixed(6)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          {benchmark.smallOrchestration.p95LatencyMs} ms
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          {benchmark.smallOrchestration.verifiedPassRatePct.toFixed(1)}%
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 text-slate-700">
                          Frontier Everywhere (Unrouted)
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          ${benchmark.frontierEverywhere.totalCostUsd.toFixed(4)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          ${benchmark.frontierEverywhere.costPerVerifiedOutcomeUsd.toFixed(6)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          {benchmark.frontierEverywhere.p95LatencyMs} ms
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900">
                          {benchmark.frontierEverywhere.verifiedPassRatePct.toFixed(1)}%
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Battalion Routing Matrix Mapping */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">
            Battalion Routing Matrix Mapping (Small Specialist + Selective Frontier Escalation)
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Maps Microsoft Research (MagenticBrain, Fara1.5, MagenticLite) and OpenCode free supply directly onto Battalion execution lanes with deterministic verification gates.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-4 font-medium">Task Class</th>
                <th className="py-2.5 px-4 font-medium">Battalion Lane</th>
                <th className="py-2.5 px-4 font-medium">Primary Specialist</th>
                <th className="py-2.5 px-4 font-medium">Pre-Exhaustion Fallback</th>
                <th className="py-2.5 px-4 font-medium">Escalation Trigger &amp; Target</th>
                <th className="py-2.5 px-4 font-medium">Independent Verifier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {(data?.routingMatrix ?? []).map((row) => (
                <tr key={row.taskClass}>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900 whitespace-nowrap">
                    {row.taskClass}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-700 whitespace-nowrap">
                    {row.battalionLane}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900">{row.primarySpecialist}</td>
                  <td className="py-3 px-4 text-slate-700">{row.preExhaustionFallback}</td>
                  <td className="py-3 px-4 text-slate-600">
                    <div>{row.escalationTrigger}</div>
                    <div className="text-[11px] font-medium text-slate-800">
                      Target: {row.frontierEscalationTarget}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-emerald-700 font-medium">
                    {row.independentVerifier}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* GEMINI-FREE-MODEL-RECOVERY Work Package */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">
            GEMINI-FREE-MODEL-RECOVERY Work Package &amp; Epistemic Provenance
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Meridian invariant: uninspected external recovery artifacts (chidionyema/gemini-sync and Argon) remain visibly PENDING_INSPECTION until directly audited — never fabricated or overwritten.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-4 font-medium">ID</th>
                <th className="py-2.5 px-4 font-medium">Source</th>
                <th className="py-2.5 px-4 font-medium">Artifact Scope</th>
                <th className="py-2.5 px-4 font-medium">Verification Status</th>
                <th className="py-2.5 px-4 font-medium">Audit Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {(data?.recoveryPackage ?? []).map((item) => (
                <tr key={item.id}>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900 whitespace-nowrap">
                    {item.id}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900 whitespace-nowrap">
                    {item.source}
                  </td>
                  <td className="py-3 px-4 text-slate-700">{item.artifact}</td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    {item.status === 'VERIFIED' ? (
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        VERIFIED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 font-semibold text-amber-700">
                        <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                        PENDING_INSPECTION
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-600">{item.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Estate 7-Workstream Forensic Inventory */}
      {data?.workstreams && (
        <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="max-w-2xl">
              <div className="text-[11px] font-mono font-semibold text-amber-700">
                DEVELOPMENT_STAGE_CONCEPT &mdash; SANDBOX CONTROL PLANE (NOT PRODUCTION CERTIFIED)
              </div>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">
                Estate 7-Workstream Forensic Inventory (Epistemic Status &amp; Known Defects)
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Preserves exact SOURCE-LOCATED (2), PARTIAL (4), and UNKNOWN (1) provenance across all 7 estate workstreams without inventing Drive paths or missing bodies.
              </p>
            </div>

            <div
              role="group"
              aria-label="Filter workstreams by status"
              className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0"
            >
              {(['ALL', 'SOURCE-LOCATED', 'PARTIAL', 'UNKNOWN'] as const).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setWorkstreamFilter(status)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md whitespace-nowrap ${
                    workstreamFilter === status
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Workstream</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">Entry Point &amp; Drive</th>
                  <th className="py-2.5 px-4 font-medium">Known Defect(s)</th>
                  <th className="py-2.5 px-4 font-medium">Missing Artifacts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {data.workstreams
                  .filter((w) =>
                    workstreamFilter === 'ALL' ? true : w.status === workstreamFilter
                  )
                  .map((ws) => (
                    <tr key={ws.id} className="align-top">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="font-semibold text-slate-900">
                          {ws.id}. {ws.name}
                        </div>
                        <div className="mt-0.5 text-[11px] text-slate-500 max-w-[220px] truncate" title={ws.locations}>
                          {ws.locations}
                        </div>
                      </td>
                      <td
                        className={`py-3 px-4 font-mono font-semibold whitespace-nowrap ${
                          ws.status === 'SOURCE-LOCATED'
                            ? 'text-emerald-700'
                            : ws.status === 'PARTIAL'
                            ? 'text-amber-700'
                            : 'text-red-700'
                        }`}
                      >
                        {ws.status}
                      </td>
                      <td className="py-3 px-4 text-slate-700 max-w-[220px]">
                        <div className="font-mono text-[11px] text-slate-800 break-words">
                          {ws.entryPoint}
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500">
                          Drive: <span className="font-mono">{ws.drivePath}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 max-w-[300px]">{ws.knownDefect}</td>
                      <td className="py-3 px-4 text-slate-600 max-w-[260px]">{ws.missing}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
