import { useState } from 'react';
import { CheckCircle2, Play, RotateCcw, AlertTriangle } from 'lucide-react';
import { LAUNCHD_TO_DAGSTER_MIGRATION } from '../data/competitors';
import { RestartComparisonReport } from '../engine/types';
import { GatewayStateSnapshot, RestartApiResponse } from '../types/api';

interface DagsterOrchestrationProps {
  state: GatewayStateSnapshot;
  onStateChange: (next: GatewayStateSnapshot) => void;
}

export function DagsterOrchestration({ state, onStateChange }: DagsterOrchestrationProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [restartReport, setRestartReport] = useState<RestartComparisonReport | null>(null);

  async function handleEvaluateSensors() {
    setBusyAction('evaluate');
    try {
      const res = await fetch('/api/dagster/evaluate', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        onStateChange(data.state);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleMaterialize(assetKey: string) {
    setBusyAction(assetKey);
    try {
      const res = await fetch('/api/dagster/materialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assetKey }),
      });
      if (res.ok) {
        const data = await res.json();
        onStateChange(data.state);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSimulateRestart(mode: 'dagster_durable' | 'legacy_launchd') {
    setBusyAction(mode);
    try {
      const res = await fetch('/api/dagster/restart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      if (res.ok) {
        const data = (await res.json()) as RestartApiResponse;
        setRestartReport(data.report);
        onStateChange(data.state);
      }
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Software-Defined Asset Graph */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-slate-200">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Dagster Software-Defined Asset Lineage
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Declarative asset graph replacing imperative launchd plists. Materialize any asset directly or run a sensor tick.
            </p>
          </div>
          <button
            type="button"
            disabled={busyAction !== null}
            onClick={handleEvaluateSensors}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {busyAction === 'evaluate' ? 'Evaluating Sensors...' : 'Evaluate Sensors Now'}
          </button>
        </div>

        {/* 3-tier DAG lineage layout */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          {/* Tier 1: Root Sources */}
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Tier 1 · Root Credentials
            </div>
            {state.dagster.assets
              .filter((a) => a.upstreamDeps.length === 0)
              .map((asset) => (
                <div
                  key={asset.key}
                  className="border border-slate-200 rounded-md p-4 bg-slate-50/50"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{asset.label}</div>
                      <div className="text-xs font-mono text-slate-500 mt-0.5">{asset.key}</div>
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        asset.status === 'materialized' ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {asset.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{asset.summary}</p>
                  <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                    <span className="font-mono tabular-nums text-slate-500">
                      Runs: {asset.materializationCount}
                    </span>
                    <button
                      type="button"
                      disabled={busyAction !== null}
                      onClick={() => handleMaterialize(asset.key)}
                      className="font-medium text-blue-600 hover:text-blue-700 whitespace-nowrap"
                    >
                      {busyAction === asset.key ? 'Running...' : 'Materialize'}
                    </button>
                  </div>
                </div>
              ))}
          </div>

          {/* Tier 2: Derived State */}
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Tier 2 · Derived State &amp; WAL
            </div>
            {state.dagster.assets
              .filter((a) => a.upstreamDeps.length === 1)
              .map((asset) => (
                <div
                  key={asset.key}
                  className="border border-slate-200 rounded-md p-4 bg-slate-50/50"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{asset.label}</div>
                      <div className="text-xs font-mono text-slate-500 mt-0.5">{asset.key}</div>
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        asset.status === 'materialized' ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {asset.status}
                    </span>
                  </div>
                  <div className="mt-1.5 text-xs text-slate-500 font-mono">
                    Deps: {asset.upstreamDeps.join(', ')}
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{asset.summary}</p>
                  <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                    <span className="font-mono tabular-nums text-slate-500">
                      Runs: {asset.materializationCount}
                    </span>
                    <button
                      type="button"
                      disabled={busyAction !== null}
                      onClick={() => handleMaterialize(asset.key)}
                      className="font-medium text-blue-600 hover:text-blue-700 whitespace-nowrap"
                    >
                      {busyAction === asset.key ? 'Running...' : 'Materialize'}
                    </button>
                  </div>
                </div>
              ))}
          </div>

          {/* Tier 3: Unified Control Snapshot */}
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Tier 3 · Router Snapshot
            </div>
            {state.dagster.assets
              .filter((a) => a.upstreamDeps.length > 1)
              .map((asset) => (
                <div
                  key={asset.key}
                  className="border border-slate-200 rounded-md p-4 bg-slate-50/50"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{asset.label}</div>
                      <div className="text-xs font-mono text-slate-500 mt-0.5">{asset.key}</div>
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        asset.status === 'materialized' ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {asset.status}
                    </span>
                  </div>
                  <div className="mt-1.5 text-xs text-slate-500 font-mono">
                    Deps: {asset.upstreamDeps.join(' · ')}
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{asset.summary}</p>
                  <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                    <span className="font-mono tabular-nums text-slate-500">
                      Runs: {asset.materializationCount}
                    </span>
                    <button
                      type="button"
                      disabled={busyAction !== null}
                      onClick={() => handleMaterialize(asset.key)}
                      className="font-medium text-blue-600 hover:text-blue-700 whitespace-nowrap"
                    >
                      {busyAction === asset.key ? 'Running...' : 'Materialize'}
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </section>

      {/* Worker Restart Comparison: Dagster vs Legacy launchd */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-slate-200">
          <div className="max-w-xl">
            <h2 className="text-base font-semibold text-slate-900">
              Worker Restart Verification: Dagster Durable vs. Legacy launchd
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Reproduce the launchctl restart failure mode (dropped RAM receipts + cold vault env) vs. Dagster SIGTERM WAL flush &amp; sensor auto-hydration.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => handleSimulateRestart('legacy_launchd')}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap"
            >
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
              Simulate Legacy launchd Kill
            </button>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => handleSimulateRestart('dagster_durable')}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              Simulate Dagster Durable Restart
            </button>
          </div>
        </div>

        {restartReport ? (
          <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-slate-200 rounded-md p-4">
                <div className="text-xs text-slate-500">Receipts Before / After</div>
                <div className="mt-1.5 text-lg font-mono tabular-nums font-semibold text-slate-900">
                  {restartReport.receiptsBeforeRestart.toLocaleString()} → {restartReport.receiptsAfterRestart.toLocaleString()}
                </div>
              </div>
              <div className="border border-slate-200 rounded-md p-4">
                <div className="text-xs text-slate-500">Dropped Receipts</div>
                <div
                  className={`mt-1.5 text-lg font-mono tabular-nums font-semibold ${
                    restartReport.droppedReceipts === 0 ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  {restartReport.droppedReceipts.toLocaleString()}
                </div>
              </div>
              <div className="border border-slate-200 rounded-md p-4">
                <div className="text-xs text-slate-500">Vault Keys on Boot</div>
                <div
                  className={`mt-1.5 text-sm font-semibold ${
                    restartReport.vaultKeysHydratedOnBoot ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  {restartReport.vaultKeysHydratedOnBoot ? 'Auto-Hydrated' : 'Dropped (Manual Heal Required)'}
                </div>
              </div>
              <div className="border border-slate-200 rounded-md p-4">
                <div className="text-xs text-slate-500">Recovery Latency</div>
                <div className="mt-1.5 text-lg font-mono tabular-nums font-semibold text-slate-900">
                  {restartReport.recoveryTimeMs} ms
                </div>
              </div>
            </div>

            <div className="border border-slate-200 rounded-md bg-slate-50 p-4">
              <div className="text-xs font-semibold text-slate-700 mb-2">
                {restartReport.mode === 'dagster_durable'
                  ? 'Dagster Durable Restart Trace'
                  : 'Legacy launchd Restart Trace'}
              </div>
              <ol className="space-y-1.5 text-xs font-mono text-slate-700">
                {restartReport.events.map((evt, i) => (
                  <li key={i}>{evt}</li>
                ))}
              </ol>
            </div>
          </div>
        ) : (
          <div className="mt-4 text-xs text-slate-500">
            Click either simulation button above to inspect live WAL preservation and vault auto-hydration behavior across restarts.
          </div>
        )}
      </section>

      {/* Active Sensors Table */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">Autonomous Dagster Sensors</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Continuous evaluation daemons replacing manual CLI heal scripts.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-500">
                <th className="py-3 px-6">Sensor</th>
                <th className="py-3 px-4">Target Asset</th>
                <th className="py-3 px-4 text-right">Cadence</th>
                <th className="py-3 px-4 text-right">Triggers Fired</th>
                <th className="py-3 px-6">Last Evaluation Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {state.dagster.sensors.map((sensor) => (
                <tr key={sensor.id} className="hover:bg-slate-50/80">
                  <td className="py-3 px-6 font-mono font-medium text-slate-900">{sensor.name}</td>
                  <td className="py-3 px-4 font-mono text-slate-600">{sensor.targetAsset}</td>
                  <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-600">
                    {sensor.intervalSec}s
                  </td>
                  <td className="py-3 px-4 text-right font-mono tabular-nums font-medium text-slate-900">
                    {sensor.triggersFired}
                  </td>
                  <td className="py-3 px-6 text-slate-700">{sensor.lastVerdict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Launchd -> Dagster Migration Evidence */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">
            Launchd to Dagster Architectural Migration Matrix
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Root-cause elimination map addressing every defect from the prior production incident.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-500">
                <th className="py-3 px-6">Failure Surface</th>
                <th className="py-3 px-4">Legacy launchd Behavior</th>
                <th className="py-3 px-4">Dagster Architecture</th>
                <th className="py-3 px-6">Verified Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {LAUNCHD_TO_DAGSTER_MIGRATION.map((row) => (
                <tr key={row.capability} className="align-top">
                  <td className="py-3.5 px-6 font-semibold text-slate-900 whitespace-nowrap">
                    {row.capability}
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">{row.legacyLaunchd}</td>
                  <td className="py-3.5 px-4 text-slate-800">{row.dagsterReplacement}</td>
                  <td className="py-3.5 px-6 text-emerald-700 font-medium">
                    <span className="inline-flex items-start gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" aria-hidden="true" />
                      <span>{row.verifiedImprovement}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
