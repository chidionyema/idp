import { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  PackageCheck,
  Play,
  XCircle,
} from 'lucide-react';
import { VerificationSuiteReport } from '../engine/types';

interface FalsifiersSuiteProps {
  externalReport?: VerificationSuiteReport | null;
  onReportUpdated?: (report: VerificationSuiteReport) => void;
}

type FilterMode = 'all' | 'integration' | 'falsifier';

interface LiveEndpointProbe {
  id: string;
  era: string;
  endpoint: string;
  status: number | null;
  ok: boolean;
  latencyMs: number;
  truthMode: string;
}

const ENDPOINT_PROBE_TARGETS = [
  { id: 'ep-state', era: 'Day -3 · Gateway & WAL', endpoint: '/api/state' },
  { id: 'ep-union', era: 'Day -2 · Grand Union & Audit', endpoint: '/api/union' },
  { id: 'ep-omniflow', era: 'Day -1 · OMNIFLOW Bus', endpoint: '/api/omniflow/state' },
  { id: 'ep-karma', era: 'Day -1 · KARMA Settlement', endpoint: '/api/karma/settlement' },
  { id: 'ep-matrix', era: 'Day -1 · 10-Scenario Matrix', endpoint: '/api/resilience/matrix' },
  { id: 'ep-eye', era: 'Day -1 · All-Seeing Eye', endpoint: '/api/audit/all-seeing-eye' },
  { id: 'ep-fsm', era: 'Today · 10/10 FSM Constitution', endpoint: '/api/estate/fsm-constitution' },
  { id: 'ep-phoenix', era: 'Today · Operation Phoenix v2', endpoint: '/api/phoenix/state' },
  { id: 'ep-ioc', era: 'Today · System-First IoC & 4KB DNA', endpoint: '/api/ioc/state' },
];

export function FalsifiersSuite({ externalReport, onReportUpdated }: FalsifiersSuiteProps) {
  const [report, setReport] = useState<VerificationSuiteReport | null>(externalReport ?? null);
  const [running, setRunning] = useState(false);
  const [probingLive, setProbingLive] = useState(false);
  const [liveProbes, setLiveProbes] = useState<LiveEndpointProbe[]>([]);
  const [filter, setFilter] = useState<FilterMode>('all');
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({
    'INT-10': true,
    F30: true,
    F31: true,
  });

  useEffect(() => {
    if (externalReport) {
      setReport(externalReport);
    }
  }, [externalReport]);

  useEffect(() => {
    if (!report) {
      void handleRunSuite();
    }
    void handleRunLiveEndpointProbes();
  }, []);

  async function handleRunSuite() {
    setRunning(true);
    try {
      const res = await fetch('/api/tests/run', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as VerificationSuiteReport;
        setReport(data);
        onReportUpdated?.(data);
      }
    } finally {
      setRunning(false);
    }
  }

  async function handleRunLiveEndpointProbes() {
    setProbingLive(true);
    try {
      const results = await Promise.all(
        ENDPOINT_PROBE_TARGETS.map(async (target): Promise<LiveEndpointProbe> => {
          const t0 = performance.now();
          try {
            const res = await fetch(target.endpoint);
            const latencyMs = Math.max(1, Math.round(performance.now() - t0));
            const json = (await res.json().catch(() => ({}))) as Record<string, unknown>;
            const truthMode =
              typeof json.telemetryFreshness === 'string'
                ? json.telemetryFreshness
                : json.isLiveState === false
                  ? 'HISTORICAL_SNAPSHOT'
                  : 'LIVE_EXPRESS_RUNTIME';
            return {
              id: target.id,
              era: target.era,
              endpoint: target.endpoint,
              status: res.status,
              ok: res.ok,
              latencyMs,
              truthMode,
            };
          } catch {
            return {
              id: target.id,
              era: target.era,
              endpoint: target.endpoint,
              status: null,
              ok: false,
              latencyMs: Math.max(1, Math.round(performance.now() - t0)),
              truthMode: 'UNREACHABLE',
            };
          }
        })
      );
      setLiveProbes(results);
    } finally {
      setProbingLive(false);
    }
  }

  function handleDownloadEvidence() {
    if (!report) return;
    const blob = new Blob([JSON.stringify({ report, liveProbes }, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pennyd-verification-evidence-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function toggleExpanded(id: string) {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  const integrationCount = report
    ? report.cases.filter((c) => c.category === 'integration').length
    : 10;
  const falsifierCount = report
    ? report.cases.filter((c) => c.category === 'falsifier').length
    : 31;
  const totalCaseCount = report?.totalCases ?? 41;
  const visibleCases =
    report?.cases.filter((c) => (filter === 'all' ? true : c.category === filter)) ?? [];

  return (
    <div className="space-y-6">
      {/* Control Header */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="max-w-xl">
            <h2 className="text-base font-semibold text-slate-900">
              End-to-End Integration Suite &amp; Cross-Day Assurance Matrix
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Executes {integrationCount} end-to-end integration suites (INT-01..{integrationCount}) and {falsifierCount} targeted falsifiers (F1..F{falsifierCount}) spanning Gateway/WAL/Dagster, Grand Union, Hermes, I-8095, AURA-2100, MUM-CONCIERGE-001, Autonomous Reactivity (#8184), MCC-001, OMNIFLOW Bus, Sync #7760, KARMA Settlement, 10/10 Closed-Loop FSMs, and Operation Phoenix v2.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={!report}
              onClick={handleDownloadEvidence}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Suite Evidence JSON
            </button>
            <a
              href="/api/debug-pack"
              download="meridian-hermes-debug-pack.json"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Debug Pack JSON
            </a>
            <a
              href="/api/debug-pack?format=markdown"
              download="meridian-hermes-debug-pack.md"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              Debug Pack MD
            </a>
            <a
              href="/api/export/bundle"
              download="meridian-hermes-today.bundle"
              className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-950 hover:bg-amber-100 transition-colors whitespace-nowrap"
            >
              <PackageCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Git Bundle (.bundle)
            </a>
            <button
              type="button"
              disabled={running}
              onClick={handleRunSuite}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              {running ? 'Executing Suite...' : `Run Full ${totalCaseCount}-Case Suite`}
            </button>
          </div>
        </div>

        {/* Summary Metrics */}
        {report && (
          <div className="mt-6 pt-5 border-t border-slate-200 grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-slate-500">Suites &amp; Falsifiers Passed</div>
              <div
                className={`mt-1 text-xl font-mono tabular-nums font-semibold ${
                  report.failedCases === 0 ? 'text-emerald-700' : 'text-red-700'
                }`}
              >
                {report.passedCases} / {report.totalCases}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Assertions Verified</div>
              <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-slate-900">
                {report.passedAssertions} / {report.totalAssertions}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Execution Duration</div>
              <div className="mt-1 text-xl font-mono tabular-nums font-semibold text-slate-900">
                {report.durationMs} ms
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">CLI Full-Stack Test Command</div>
              <div className="mt-1.5 text-[11px] font-mono text-slate-700 break-all">
                npm test
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Live Multi-Day Server HTTP Assurance Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-4 sm:px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Live Backend HTTP Assurance Matrix (Past Days &rarr; Today)
            </h3>
            <p className="text-xs text-slate-500">
              Direct live HTTP verification across core gateway, OMNIFLOW bus, Sync/KARMA, 10/10 FSMs &amp; Phoenix APIs ({liveProbes.filter((p) => p.ok).length}/{ENDPOINT_PROBE_TARGETS.length} responsive).
            </p>
          </div>
          <button
            type="button"
            disabled={probingLive}
            onClick={handleRunLiveEndpointProbes}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
          >
            <Activity className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
            {probingLive ? 'Probing Endpoints...' : 'Probe Live Server Endpoints'}
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-5 font-medium">Workstream Era</th>
                <th className="py-2.5 px-4 font-medium">HTTP Endpoint</th>
                <th className="py-2.5 px-4 font-medium">Runtime Mode</th>
                <th className="py-2.5 px-4 font-medium text-right">Latency</th>
                <th className="py-2.5 px-5 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {liveProbes.map((probe) => (
                <tr key={probe.id}>
                  <td className="py-2.5 px-5 font-medium text-slate-900">{probe.era}</td>
                  <td className="py-2.5 px-4 font-mono text-slate-700">{probe.endpoint}</td>
                  <td className="py-2.5 px-4 font-mono text-slate-600">{probe.truthMode}</td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-500">
                    {probe.latencyMs} ms
                  </td>
                  <td
                    className={`py-2.5 px-5 text-right font-mono font-semibold ${
                      probe.ok ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {probe.status ? `HTTP ${probe.status}` : 'FAILED'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Filter & Cases List */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-4 sm:px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div role="group" aria-label="Filter test category" className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg">
            {(
              [
                { id: 'all', label: `All Cases (${totalCaseCount})` },
                { id: 'falsifier', label: `Adversarial Falsifiers (F1–F${falsifierCount})` },
                { id: 'integration', label: `Integration Tests (INT-01–${integrationCount})` },
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

          {report && (
            <span className="text-xs text-slate-500 font-mono">
              Last verified {new Date(report.runAt).toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="divide-y divide-slate-200">
          {visibleCases.map((testCase) => {
            const isOpen = !!expandedIds[testCase.id];
            return (
              <div key={testCase.id} className="p-5">
                <button
                  type="button"
                  onClick={() => toggleExpanded(testCase.id)}
                  aria-expanded={isOpen}
                  className="w-full flex items-start justify-between gap-4 text-left"
                >
                  <div className="flex items-start gap-3 min-w-0">
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-slate-900">
                          {testCase.title}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {testCase.id} · {testCase.category}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{testCase.hypothesis}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 text-xs">
                    <span className="font-mono tabular-nums text-slate-500">
                      {testCase.durationMs} ms
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 font-semibold ${
                        testCase.passed ? 'text-emerald-700' : 'text-red-700'
                      }`}
                    >
                      {testCase.passed ? (
                        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      ) : (
                        <XCircle className="h-4 w-4" aria-hidden="true" />
                      )}
                      {testCase.passed ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                </button>

                {isOpen && (
                  <div className="mt-4 sm:ml-7 border border-slate-200 rounded-md overflow-x-auto">
                    <table className="w-full min-w-[520px] text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                          <th className="py-2 px-4 font-medium">Assertion</th>
                          <th className="py-2 px-4 font-medium">Expected Invariant</th>
                          <th className="py-2 px-4 font-medium">Measured Actual</th>
                          <th className="py-2 px-4 font-medium text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {testCase.assertions.map((a, idx) => (
                          <tr key={idx}>
                            <td className="py-2 px-4 text-slate-800">{a.name}</td>
                            <td className="py-2 px-4 font-mono text-slate-600">{a.expected}</td>
                            <td className="py-2 px-4 font-mono text-slate-900">{a.actual}</td>
                            <td
                              className={`py-2 px-4 text-right font-semibold ${
                                a.passed ? 'text-emerald-700' : 'text-red-700'
                              }`}
                            >
                              {a.passed ? 'PASS' : 'FAIL'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
