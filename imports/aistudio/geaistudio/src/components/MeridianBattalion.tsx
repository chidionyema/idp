import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { MeridianApiResponse } from '../types/api';

export function MeridianBattalion() {
  const [data, setData] = useState<MeridianApiResponse | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchMeridian() {
    setLoading(true);
    try {
      const res = await fetch('/api/meridian');
      if (res.ok) {
        const json = (await res.json()) as MeridianApiResponse;
        setData(json);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchMeridian();
  }, []);

  if (loading || !data) {
    return (
      <div className="space-y-4">
        <div className="h-24 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-72 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  const { meridian } = data;
  const {
    activityAccounting,
    physicalResourceAccounting,
    financialAccounting,
    epistemicOutcomeAccounting,
    coverageMatrix,
    missionEndToEndTrace,
    optimusExperimentProof,
  } = meridian;

  return (
    <div className="space-y-6">
      {/* Governing Invariant Header */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="max-w-3xl">
            <h2 className="text-base font-semibold text-slate-900">
              Meridian Battalion — Universal Metering &amp; Resource Intelligence
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Governing Invariant: Every admitted activity carries an identifiable owner, resource-consumption record, provenance, and measurement status (DIRECT, ALLOCATED, ESTIMATED, or visibly BLIND). BLIND is never coerced to zero.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Invariant {meridian.governingInvariantStatus}
            </span>
            <button
              type="button"
              onClick={fetchMeridian}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh Ledger
            </button>
          </div>
        </div>
      </section>

      {/* Four Logically Separate Linked Accounting Domains */}
      <section aria-label="Four linked accounting domains" className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <h3 className="text-sm font-semibold text-slate-900">01. Activity Accounting</h3>
            <span className="text-xs font-mono text-slate-500">FLOW / Legion · OpenCode V2</span>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-xs pt-1">
            <div>
              <dt className="text-slate-500">Active Missions / Sessions</dt>
              <dd className="font-mono tabular-nums font-semibold text-slate-900 mt-0.5">
                {activityAccounting.activeMissions} missions · {activityAccounting.activeSessions} sessions
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Admitted Executions</dt>
              <dd className="font-mono tabular-nums font-semibold text-slate-900 mt-0.5">
                {activityAccounting.admittedExecutions} ({activityAccounting.unownedActivities} unowned)
              </dd>
            </div>
          </dl>
          <div className="text-xs text-slate-600 pt-1">
            Execution Adapter: <span className="font-medium text-slate-900">{activityAccounting.adapterName}</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <h3 className="text-sm font-semibold text-slate-900">02. Physical Resource Accounting</h3>
            <span className="text-xs font-mono text-slate-500">Producers · OpenCost</span>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-xs pt-1">
            <div>
              <dt className="text-slate-500">Tokens Executed / Saved</dt>
              <dd className="font-mono tabular-nums font-semibold text-slate-900 mt-0.5">
                {physicalResourceAccounting.totalExecutedTokens.toLocaleString()} / -{physicalResourceAccounting.tokensSavedByPennyD.toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Host Energy Sensors</dt>
              <dd className="font-mono tabular-nums font-semibold text-amber-700 mt-0.5">
                {physicalResourceAccounting.blindEnergySamplesCount} BLIND (Unknown, ≠ 0)
              </dd>
            </div>
          </dl>
          <div className="text-xs text-slate-600 pt-1 font-mono tabular-nums">
            Reasoning: {physicalResourceAccounting.reasoningTokens.toLocaleString()} tok · Throughput {physicalResourceAccounting.avgThroughputTokPerSec} tok/s
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <h3 className="text-sm font-semibold text-slate-900">03. Financial Accounting (FOCUS 1.0)</h3>
            <span className="text-xs font-mono text-slate-500">QUAD · Reconciliation</span>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-xs pt-1">
            <div>
              <dt className="text-slate-500">Actual vs. Without PennyD</dt>
              <dd className="font-mono tabular-nums font-semibold text-slate-900 mt-0.5">
                ${financialAccounting.actualSpendUsd.toFixed(5)} vs. ${financialAccounting.withoutPennydSpendUsd.toFixed(5)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Net Savings</dt>
              <dd className="font-mono tabular-nums font-semibold text-emerald-700 mt-0.5">
                ${financialAccounting.netSavingsUsd.toFixed(5)} ({financialAccounting.savingsPct.toFixed(2)}%)
              </dd>
            </div>
          </dl>
          <div className="text-xs text-slate-600 pt-1 font-mono tabular-nums">
            Double-counting prevented: {financialAccounting.doubleCountingPreventedCount} · Reconciled: {financialAccounting.reconciledEntriesCount}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <h3 className="text-sm font-semibold text-slate-900">04. Epistemic &amp; Outcome Accounting</h3>
            <span className="text-xs font-mono text-slate-500">Optimus · KARMA</span>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-xs pt-1">
            <div>
              <dt className="text-slate-500">Independently Verified Outcomes</dt>
              <dd className="font-mono tabular-nums font-semibold text-emerald-700 mt-0.5">
                {epistemicOutcomeAccounting.verifiedOutcomesCount} verified · {epistemicOutcomeAccounting.karmaCorrectionsLogged} KARMA logs
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Optimus Cost Lift vs. Baseline</dt>
              <dd className="font-mono tabular-nums font-semibold text-blue-700 mt-0.5">
                +{epistemicOutcomeAccounting.optimusLiftVsBaselinePct.toFixed(2)}%
              </dd>
            </div>
          </dl>
          <div className="text-xs text-slate-600 pt-1">
            Uncertain / Blind Gaps Surfaced: <span className="font-mono font-semibold text-amber-700">{epistemicOutcomeAccounting.blindTelemetryCount}</span>
          </div>
        </div>
      </section>

      {/* Non-Negotiable Acceptance: End-to-End Mission Parity (Genesis / Face / Mini Backstage) + Optimus Lift */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h3 className="text-sm font-semibold text-slate-900">
              End-to-End Estate Mission Provenance ({missionEndToEndTrace.missionId})
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {missionEndToEndTrace.instructionSummary}
            </p>
          </div>

          <dl className="space-y-2 text-xs">
            <div className="flex flex-col sm:flex-row sm:justify-between gap-1">
              <dt className="text-slate-500">Agent &amp; Orchestration Chain</dt>
              <dd className="font-mono text-slate-900">{missionEndToEndTrace.agentChain}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-1">
              <dt className="text-slate-500">Models &amp; Tools</dt>
              <dd className="font-mono text-slate-900">{missionEndToEndTrace.modelAndTools}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-1">
              <dt className="text-slate-500">Compute Allocation</dt>
              <dd className="text-slate-700">{missionEndToEndTrace.computeAllocation}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-1">
              <dt className="text-slate-500">Verified Outcome</dt>
              <dd className="font-medium text-emerald-700">{missionEndToEndTrace.verifiedOutcome}</dd>
            </div>
          </dl>

          <div className="border border-slate-200 rounded-md overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2 px-4 font-medium">Surface Parity</th>
                  <th className="py-2 px-3 font-medium">Mission</th>
                  <th className="py-2 px-3 font-medium text-right">Actual USD</th>
                  <th className="py-2 px-3 font-medium text-right">Saved USD</th>
                  <th className="py-2 px-4 font-medium text-right">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {missionEndToEndTrace.paritySurfaces.map((s) => (
                  <tr key={s.surface}>
                    <td className="py-2 px-4 font-semibold text-slate-900">{s.surface}</td>
                    <td className="py-2 px-3 font-mono text-slate-600">{s.missionId}</td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums text-slate-900">
                      ${s.actualUsd.toFixed(6)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums text-emerald-700 font-semibold">
                      ${s.savingsUsd.toFixed(6)}
                    </td>
                    <td className="py-2 px-4 text-right text-emerald-700">{s.evidenceStatus}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Optimus Controlled Experiment Lift Proof */}
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <h3 className="text-sm font-semibold text-slate-900">
              Optimus Strategy Lift vs. Controlled Baseline
            </h3>
            <div className="mt-0.5 text-xs font-mono text-slate-500">
              {optimusExperimentProof.experimentId} · {optimusExperimentProof.samplePackets} metered packets
            </div>
          </div>

          <div className="space-y-3 text-xs">
            <div className="border border-slate-200 rounded-md p-3">
              <div className="text-slate-500">Control Baseline</div>
              <div className="font-medium text-slate-900 mt-0.5">{optimusExperimentProof.controlBaseline}</div>
              <div className="mt-1.5 font-mono tabular-nums text-slate-700">
                ${optimusExperimentProof.controlCostPer1kTokUsd.toFixed(5)} / 1k tok · p95 {optimusExperimentProof.controlP95LatencyMs} ms
              </div>
            </div>

            <div className="border border-emerald-200 bg-emerald-50/50 rounded-md p-3">
              <div className="text-emerald-800 font-medium">Treatment: {optimusExperimentProof.treatmentStrategy}</div>
              <div className="mt-1.5 font-mono tabular-nums text-slate-900 font-semibold">
                ${optimusExperimentProof.treatmentCostPer1kTokUsd.toFixed(5)} / 1k tok · p95 {optimusExperimentProof.treatmentP95LatencyMs} ms
              </div>
              <div className="mt-1 text-emerald-700 font-mono font-semibold">
                Verified Cost Reduction: {optimusExperimentProof.costReductionPct.toFixed(2)}%
              </div>
            </div>

            <div className="text-xs text-slate-600">
              Independent Verifier: <span className="font-mono text-slate-800">{optimusExperimentProof.independentVerifier}</span>
            </div>
          </div>
        </section>
      </div>

      {/* 11-Activity Universal Coverage Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-base font-semibold text-slate-900">
            Estate-Wide 11-Activity Measurement Coverage Matrix
          </h3>
          <p className="mt-0.5 text-sm text-slate-500">
            Explicit coverage states across every producer. Uninstrumented fields remain visibly BLIND.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
                <th className="py-3 px-6 font-medium">Activity</th>
                <th className="py-3 px-4 font-medium">Accountable System</th>
                <th className="py-3 px-4 font-medium">Standards Mapping</th>
                <th className="py-3 px-4 font-medium">Coverage State</th>
                <th className="py-3 px-6 font-medium">Live Telemetry Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {coverageMatrix.map((row) => (
                <tr key={row.activity} className="hover:bg-slate-50/80">
                  <td className="py-3 px-6 font-semibold text-slate-900 whitespace-nowrap">
                    {row.activity}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-800 whitespace-nowrap">
                    {row.accountableSystem}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-600">{row.standardsMapping}</td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 font-mono font-semibold ${
                        row.status === 'DIRECT'
                          ? 'text-emerald-700'
                          : row.status === 'ALLOCATED' || row.status === 'ESTIMATED'
                          ? 'text-blue-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {row.status === 'BLIND' && (
                        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                      {row.status}
                    </span>
                  </td>
                  <td className="py-3 px-6 text-slate-600">{row.liveCoverageNote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
