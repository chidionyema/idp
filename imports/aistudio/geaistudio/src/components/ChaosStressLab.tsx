import { useEffect, useState } from 'react';
import { CheckCircle2, Flame, AlertTriangle } from 'lucide-react';
import { ChaosConfig, ChaosReport, RoutingStrategy } from '../engine/types';

export function ChaosStressLab() {
  const [config, setConfig] = useState<ChaosConfig>({
    requestCount: 1500,
    concurrency: 50,
    strategy: 'priority_failover',
    injectDeepSeek402: true,
    injectWorkerCrash: true,
    injectCapSaveRace: true,
    injectMultiLane503: true,
    injectLatencySpike: true,
  });

  const [report, setReport] = useState<ChaosReport | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    void handleExecuteChaos();
  }, []);

  async function handleExecuteChaos() {
    setRunning(true);
    try {
      const res = await fetch('/api/chaos/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        const data = (await res.json()) as ChaosReport;
        setReport(data);
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Chaos & Load Parameter Controls */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-5 border-b border-slate-200">
          <div className="max-w-2xl">
            <h2 className="text-base font-semibold text-slate-900">
              Chaos Engineering &amp; Stress Resilience Harness
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Inject simultaneous credit exhaustion, SIGTERM daemon crashes, cap-save concurrency races, and upstream brownouts under high request load.
            </p>
          </div>
          <button
            type="button"
            disabled={running}
            onClick={handleExecuteChaos}
            className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 self-start lg:self-auto disabled:opacity-50"
          >
            <Flame className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
            {running ? 'Running Stress Suite...' : 'Execute Chaos Stress Run'}
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="chaos-volume" className="block text-xs font-medium text-slate-700">
              Request Volume
            </label>
            <select
              id="chaos-volume"
              value={config.requestCount}
              onChange={(e) => setConfig({ ...config, requestCount: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono tabular-nums text-slate-900 focus:border-blue-600 focus:outline-none"
            >
              <option value={500}>500 requests</option>
              <option value={1500}>1,500 requests</option>
              <option value={3000}>3,000 requests</option>
              <option value={5000}>5,000 requests</option>
            </select>
          </div>

          <div>
            <label htmlFor="chaos-concurrency" className="block text-xs font-medium text-slate-700">
              Simulated Concurrency
            </label>
            <select
              id="chaos-concurrency"
              value={config.concurrency}
              onChange={(e) => setConfig({ ...config, concurrency: Number(e.target.value) })}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono tabular-nums text-slate-900 focus:border-blue-600 focus:outline-none"
            >
              <option value={10}>10 concurrent workers</option>
              <option value={50}>50 concurrent workers</option>
              <option value={100}>100 concurrent workers</option>
            </select>
          </div>

          <div>
            <label htmlFor="chaos-strategy" className="block text-xs font-medium text-slate-700">
              Router Policy
            </label>
            <select
              id="chaos-strategy"
              value={config.strategy}
              onChange={(e) => setConfig({ ...config, strategy: e.target.value as RoutingStrategy })}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none"
            >
              <option value="priority_failover">Priority Failover</option>
              <option value="lowest_latency">Lowest Latency</option>
              <option value="weighted_cost">Lowest Cost</option>
              <option value="least_busy">Least Busy</option>
            </select>
          </div>
        </div>

        <div className="mt-5 pt-4 border-t border-slate-200">
          <div className="text-xs font-medium text-slate-700 mb-3">Fault Injectors</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
            {(
              [
                {
                  key: 'injectDeepSeek402',
                  label: 'DeepSeek 402 Credit Drain + Top-Up Sensor Recovery',
                },
                {
                  key: 'injectWorkerCrash',
                  label: 'Mid-Burst SIGTERM Worker Crash (WAL Zero-Loss Test)',
                },
                {
                  key: 'injectCapSaveRace',
                  label: 'Concurrent Cap-Save Race During Live Traffic',
                },
                {
                  key: 'injectMultiLane503',
                  label: 'Dual-Lane 503 Brownout (Deep Fallback Chain)',
                },
                {
                  key: 'injectLatencySpike',
                  label: '+850ms Upstream Tail Latency Spike',
                },
              ] as const
            ).map((fault) => (
              <label
                key={fault.key}
                className="flex items-center gap-2.5 border border-slate-200 rounded-md px-3 py-2.5 cursor-pointer hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={config[fault.key]}
                  onChange={(e) => setConfig({ ...config, [fault.key]: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                />
                <span className="text-slate-800">{fault.label}</span>
              </label>
            ))}
          </div>
        </div>
      </section>

      {/* Chaos Execution Results */}
      {report && (
        <>
          {/* SLA Verdict Banner */}
          <section
            className={`border rounded-lg p-5 flex flex-wrap items-center justify-between gap-4 ${
              report.slaPassed
                ? 'bg-emerald-50/70 border-emerald-200'
                : 'bg-red-50/70 border-red-200'
            }`}
          >
            <div className="flex items-center gap-3">
              {report.slaPassed ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-700 shrink-0" aria-hidden="true" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-700 shrink-0" aria-hidden="true" />
              )}
              <div>
                <div className="text-sm font-semibold text-slate-900">{report.slaVerdict}</div>
                <div className="text-xs text-slate-600 mt-0.5 font-mono">
                  {report.capSaveRacesRun} concurrent cap-save mutations · All client keys intact:{' '}
                  {report.capSaveKeysPreserved ? 'TRUE' : 'FALSE'}
                </div>
              </div>
            </div>
            <div className="text-xs font-mono tabular-nums text-slate-600">
              Executed {new Date(report.runAt).toLocaleTimeString()}
            </div>
          </section>

          {/* 4-Column Chaos Metrics */}
          <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-5">
              <div className="text-xs font-medium text-slate-500">Request Delivery Rate</div>
              <div className="mt-2 text-2xl font-mono tabular-nums font-semibold text-slate-900">
                {report.successRatePct.toFixed(2)}%
              </div>
              <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
                {report.succeededRequests.toLocaleString()} / {report.totalRequests.toLocaleString()} succeeded
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-5">
              <div className="text-xs font-medium text-slate-500">Automatic Failover Routed</div>
              <div className="mt-2 text-2xl font-mono tabular-nums font-semibold text-slate-900">
                {report.failoverRoutedRequests.toLocaleString()}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Requests rescued from 402/503 lanes
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-5">
              <div className="text-xs font-medium text-slate-500">WAL Receipts Preserved</div>
              <div className="mt-2 text-2xl font-mono tabular-nums font-semibold text-emerald-700">
                {report.receiptsPreserved.toLocaleString()}
              </div>
              <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
                {report.receiptsDropped} dropped across SIGTERM crash
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-5">
              <div className="text-xs font-medium text-slate-500">Gateway Overhead (p50 / p99)</div>
              <div className="mt-2 text-2xl font-mono tabular-nums font-semibold text-slate-900">
                {report.p50OverheadUs} / {report.p99OverheadUs} µs
              </div>
              <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
                E2E latency p95: {report.p95TotalLatencyMs} ms
              </div>
            </div>
          </section>

          {/* Latency Percentiles + Incident Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section className="bg-white border border-slate-200 rounded-lg p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Latency Percentile Distribution Under Chaos
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Measured gateway routing overhead (µs) and end-to-end lane dispatch latency (ms).
              </p>

              <div className="mt-5 space-y-4">
                {[
                  {
                    label: 'p50 Median',
                    overhead: report.p50OverheadUs,
                    totalMs: report.p50TotalLatencyMs,
                  },
                  {
                    label: 'p95 Tail',
                    overhead: report.p95OverheadUs,
                    totalMs: report.p95TotalLatencyMs,
                  },
                  {
                    label: 'p99 Extreme Tail',
                    overhead: report.p99OverheadUs,
                    totalMs: report.p99TotalLatencyMs,
                  },
                ].map((row) => (
                  <div key={row.label} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-700">{row.label}</span>
                      <span className="font-mono tabular-nums text-slate-900">
                        Gateway {row.overhead} µs · Upstream E2E {row.totalMs} ms
                      </span>
                    </div>
                    <div className="h-2.5 w-full rounded bg-slate-100 overflow-hidden">
                      <div
                        className="h-full rounded bg-blue-600"
                        style={{
                          width: `${Math.min(100, Math.max(8, (row.totalMs / Math.max(1, report.p99TotalLatencyMs)) * 100))}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="text-sm font-semibold text-slate-900">
                  Chaos Fault Injection &amp; Recovery Timeline
                </h3>
              </div>
              <div className="divide-y divide-slate-200 max-h-[320px] overflow-y-auto">
                {report.timeline.map((item) => (
                  <div key={item.step} className="px-6 py-3 text-xs flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-semibold ${
                            item.severity === 'critical'
                              ? 'text-red-700'
                              : item.severity === 'warning'
                              ? 'text-amber-700'
                              : item.severity === 'resolved'
                              ? 'text-emerald-700'
                              : 'text-slate-700'
                          }`}
                        >
                          {item.event}
                        </span>
                      </div>
                      <p className="mt-0.5 text-slate-600">{item.detail}</p>
                    </div>
                    <span className="font-mono tabular-nums text-slate-500 shrink-0">
                      req #{item.requestIndex}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
