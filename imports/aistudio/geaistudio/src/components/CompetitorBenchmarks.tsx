import { useState } from 'react';
import { COMPETITOR_BENCHMARKS, CompetitorProfile } from '../data/competitors';

type CategoryFilter = 'all' | 'latency' | 'enterprise' | 'observability';

export function CompetitorBenchmarks() {
  const [filter, setFilter] = useState<CategoryFilter>('all');

  const filtered = COMPETITOR_BENCHMARKS.filter((c) => {
    if (filter === 'all') return true;
    if (c.category === 'ours') return true;
    if (filter === 'observability') {
      return c.category === 'observability' || c.category === 'marketplace';
    }
    return c.category === filter;
  });

  const maxScore = 100;

  return (
    <div className="space-y-6">
      {/* Header & Category Filter */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Commercial AI Gateway Competitive Research &amp; Feature Parity
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Benchmarked against leading production AI routers (Bifrost, LiteLLM, Portkey, OpenRouter, and Helicone) across latency overhead, atomicity, and failover orchestration.
            </p>
          </div>

          <div role="group" aria-label="Filter competitor categories" className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
            {(
              [
                { id: 'all', label: 'All Gateways' },
                { id: 'latency', label: 'Low-Latency Core' },
                { id: 'enterprise', label: 'Enterprise Control' },
                { id: 'observability', label: 'Observability & Market' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilter(tab.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  filter === tab.id
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Visual Capability Comparison Bars */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6 pt-6 border-t border-slate-200">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 mb-3">
              Composite Resilience &amp; Control Score by Dimension
            </h3>
            <div className="space-y-3.5">
              {filtered.map((item: CompetitorProfile) => {
                const avg = Math.round(
                  (item.scores.routingSpeed +
                    item.scores.failoverRecovery +
                    item.scores.configAtomicity +
                    item.scores.observability +
                    item.scores.orchestration) /
                    5
                );
                const isOurs = item.id === 'pennyd-dagster';
                return (
                  <div key={item.id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className={isOurs ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'}>
                        {item.name}
                      </span>
                      <span className="font-mono tabular-nums text-slate-600">
                        {item.coreOverheadLabel} · {avg}/100
                      </span>
                    </div>
                    <div className="h-2.5 w-full rounded bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded transition-all ${
                          isOurs ? 'bg-blue-600' : 'bg-slate-400'
                        }`}
                        style={{ width: `${(avg / maxScore) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4 bg-slate-50/60">
            <h3 className="text-sm font-semibold text-slate-900">
              Architectural Takeaways from Competitor Research
            </h3>
            <dl className="mt-3 space-y-2.5 text-xs">
              <div>
                <dt className="font-semibold text-slate-900">Bifrost (Maxim AI) — Speed Benchmark</dt>
                <dd className="text-slate-600 mt-0.5">
                  Proves Go/in-process gateways achieve ~11 µs core overhead vs Python FastAPI&apos;s 10–30 ms hop, with circuit breaking and tier escalation.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-900">Portkey — Enterprise Governance</dt>
                <dd className="text-slate-600 mt-0.5">
                  Sets the bar for conditional metadata routing, virtual key guardrails, and explicit policy compliance.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-900">LiteLLM &amp; OpenRouter — Failover Breadth</dt>
                <dd className="text-slate-600 mt-0.5">
                  Demonstrate multi-provider slug redundancy and least-busy / cost-weighted routing across 100–400+ models.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-900">PennyD Dagster Advantage</dt>
                <dd className="text-slate-700 mt-0.5">
                  Combines microsecond routing overhead and multi-lane circuit breaking with Dagster asset self-healing, atomic multi-key cap-save invariants, and zero-loss WAL receipts.
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      {/* Detailed Feature Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">Full Technical Feature Matrix</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-500">
                <th className="py-3 px-6">Gateway</th>
                <th className="py-3 px-4">Overhead</th>
                <th className="py-3 px-4">Failover &amp; Circuit Breaker</th>
                <th className="py-3 px-4">Error Attribution</th>
                <th className="py-3 px-4">Config &amp; Key Safety</th>
                <th className="py-3 px-4">Orchestration &amp; WAL</th>
                <th className="py-3 px-6">Gap Closed by PennyD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {filtered.map((c) => {
                const isOurs = c.id === 'pennyd-dagster';
                return (
                  <tr
                    key={c.id}
                    className={`align-top ${isOurs ? 'bg-blue-50/40' : 'hover:bg-slate-50/80'}`}
                  >
                    <td className="py-3.5 px-6">
                      <div className="font-semibold text-slate-900 whitespace-nowrap">{c.name}</div>
                      <div className="text-slate-500 mt-0.5">{c.hostingModel}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono tabular-nums text-slate-800 whitespace-nowrap">
                      {c.coreOverheadLabel}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">{c.failoverDepth}</td>
                    <td className="py-3.5 px-4 text-slate-700">{c.errorAttribution}</td>
                    <td className="py-3.5 px-4 text-slate-700">{c.keyCapSafety}</td>
                    <td className="py-3.5 px-4 text-slate-700">
                      <div>{c.orchestrationModel}</div>
                      <div className="text-slate-500 mt-0.5">{c.receiptDurability}</div>
                    </td>
                    <td className="py-3.5 px-6 text-slate-700">{c.gapEliminatedByPennyD}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
