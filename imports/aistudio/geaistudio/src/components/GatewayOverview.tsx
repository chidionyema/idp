import { useState } from 'react';
import { ArrowRight, CheckCircle2, AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';
import { LaneFaultMode, RouteResult, RoutingStrategy } from '../engine/types';
import { GatewayStateSnapshot, CapSaveApiResponse, RouteApiResponse } from '../types/api';

interface GatewayOverviewProps {
  state: GatewayStateSnapshot;
  onStateChange: (next: GatewayStateSnapshot) => void;
}

const FAULT_OPTIONS: Array<{ value: LaneFaultMode; label: string }> = [
  { value: 'healthy', label: 'Healthy' },
  { value: '402_credit_exhausted', label: '402 Credit Exhausted' },
  { value: '401_upstream_key', label: '401 Invalid Upstream Key' },
  { value: '429_rate_limit', label: '429 Rate Limit' },
  { value: '503_unavailable', label: '503 Unavailable' },
  { value: 'latency_spike', label: '+850ms Latency Spike' },
];

const STRATEGY_LABELS: Array<{ value: RoutingStrategy; label: string }> = [
  { value: 'priority_failover', label: 'Priority Failover' },
  { value: 'lowest_latency', label: 'Lowest Latency' },
  { value: 'weighted_cost', label: 'Lowest Cost' },
  { value: 'least_busy', label: 'Least Busy' },
];

export function GatewayOverview({ state, onStateChange }: GatewayOverviewProps) {
  const [selectedKeyId, setSelectedKeyId] = useState(
    state.clientKeys[0]?.id ?? 'opencode_primary'
  );
  const [budgetInput, setBudgetInput] = useState(
    String(state.clientKeys[0]?.dailyBudgetUsd ?? 250)
  );
  const [testClobberGuard, setTestClobberGuard] = useState(false);
  const [capSaveFeedback, setCapSaveFeedback] = useState<CapSaveApiResponse['saveResult'] | null>(null);
  const [capSaving, setCapSaving] = useState(false);

  const [sandboxKey, setSandboxKey] = useState(
    state.clientKeys[0]?.rawKey ?? 'pk_live_opencode_primary_94a2'
  );
  const [sandboxModel, setSandboxModel] = useState('deepseek-chat');
  const [sandboxTokens, setSandboxTokens] = useState('1024');
  const [sandboxResult, setSandboxResult] = useState<RouteResult | null>(null);
  const [routingBusy, setRoutingBusy] = useState(false);
  const [laneActionBusy, setLaneActionBusy] = useState<string | null>(null);

  const healthyLanes = state.lanes.filter((l) => l.circuitState === 'CLOSED' && l.faultMode === 'healthy').length;
  const verifiedKeysCount = state.clientKeys.filter((k) => k.lastProbeStatus === 'pass').length;

  async function handleStrategyChange(nextStrategy: RoutingStrategy) {
    const res = await fetch('/api/strategy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy: nextStrategy }),
    });
    if (res.ok) {
      const data = (await res.json()) as GatewayStateSnapshot;
      onStateChange(data);
    }
  }

  async function handleCapSave(e: React.FormEvent) {
    e.preventDefault();
    setCapSaving(true);
    try {
      const res = await fetch('/api/cap-save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyId: selectedKeyId,
          dailyBudgetUsd: Number(budgetInput),
          simulateLegacyClobberBug: testClobberGuard,
        }),
      });
      const data = (await res.json()) as CapSaveApiResponse;
      setCapSaveFeedback(data.saveResult);
      if (data.state) {
        onStateChange(data.state);
      }
    } finally {
      setCapSaving(false);
    }
  }

  async function handleLaneFaultChange(laneId: string, faultMode: LaneFaultMode) {
    setLaneActionBusy(laneId);
    try {
      const res = await fetch(`/api/lanes/${laneId}/fault`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faultMode }),
      });
      if (res.ok) {
        const data = await res.json();
        onStateChange(data.state);
      }
    } finally {
      setLaneActionBusy(null);
    }
  }

  async function handleLaneTopUp(laneId: string) {
    setLaneActionBusy(laneId);
    try {
      const res = await fetch(`/api/lanes/${laneId}/topup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amountUsd: 50 }),
      });
      if (res.ok) {
        const data = await res.json();
        onStateChange(data.state);
      }
    } finally {
      setLaneActionBusy(null);
    }
  }

  async function handleDispatchRequest(e: React.FormEvent) {
    e.preventDefault();
    setRoutingBusy(true);
    try {
      const res = await fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientKey: sandboxKey,
          modelSlug: sandboxModel,
          estimatedTokens: Number(sandboxTokens) || 1024,
          strategy: state.strategy,
        }),
      });
      const data = (await res.json()) as RouteApiResponse;
      setSandboxResult(data.result);
      if (data.state) {
        onStateChange(data.state);
      }
    } finally {
      setRoutingBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* 4-Column KPI Strip */}
      <section aria-label="Gateway summary metrics" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs font-medium text-slate-500">Healthy Upstream Lanes</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-semibold text-slate-900 font-mono tabular-nums">
              {healthyLanes} / {state.lanes.length}
            </span>
            <span className="text-xs text-slate-500">Auto-failover pool</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs font-medium text-slate-500">WAL Preserved Receipts</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-semibold text-slate-900 font-mono tabular-nums">
              {state.walStats.totalReceipts.toLocaleString()}
            </span>
            <span className="text-xs text-emerald-700 font-medium">
              {state.walStats.uncommittedCount} uncommitted
            </span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs font-medium text-slate-500">Verified Client Keys</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-semibold text-slate-900 font-mono tabular-nums">
              {verifiedKeysCount} / {state.clientKeys.length}
            </span>
            <span className="text-xs text-slate-500">All-key canary pass</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <label htmlFor="strategy-select" className="block text-xs font-medium text-slate-500">
            Active Routing Policy
          </label>
          <select
            id="strategy-select"
            value={state.strategy}
            onChange={(e) => handleStrategyChange(e.target.value as RoutingStrategy)}
            className="mt-2 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-900 focus:border-blue-600 focus:outline-none"
          >
            {STRATEGY_LABELS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Upstream Lane Pool */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Upstream Lane Routing Pool</h2>
            <p className="mt-0.5 text-sm text-slate-500">
              Simulate 402 credit exhaustion or 401/503 faults and verify instant failover plus credit top-up recovery.
            </p>
          </div>
          <div className="text-xs text-slate-500 font-mono tabular-nums">
            Port 4200 Ingress · Port 3082 Atomic Cap-Save
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-500">
                <th className="py-3 px-6">Lane &amp; Model</th>
                <th className="py-3 px-4">Circuit</th>
                <th className="py-3 px-4 text-right">Credit Balance</th>
                <th className="py-3 px-4 text-right">Base Latency</th>
                <th className="py-3 px-4 text-right">Succeeded / Failed</th>
                <th className="py-3 px-4">Fault Injection</th>
                <th className="py-3 px-6 text-right">Credit Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {state.lanes.map((lane) => {
                const isHealthy = lane.circuitState === 'CLOSED' && lane.faultMode === 'healthy';
                return (
                  <tr key={lane.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-6">
                      <div className="font-medium text-slate-900">{lane.provider} · {lane.model}</div>
                      <div className="text-xs text-slate-500 font-mono">{lane.id} · priority {lane.priority}</div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                          lane.circuitState === 'CLOSED' && isHealthy
                            ? 'text-emerald-700'
                            : lane.circuitState === 'OPEN'
                            ? 'text-red-700'
                            : 'text-amber-700'
                        }`}
                      >
                        {lane.circuitState === 'CLOSED' && isHealthy ? (
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        ) : (
                          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        {lane.circuitState}
                      </span>
                      {lane.lastFailureReason && (
                        <div className="text-xs text-slate-500 mt-0.5 max-w-[190px] truncate" title={lane.lastFailureReason}>
                          {lane.lastFailureReason}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-900">
                      ${lane.creditBalanceUsd.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                      {lane.baseLatencyMs} ms
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                      {lane.successCount} / {lane.failureCount}
                    </td>
                    <td className="py-3 px-4">
                      <select
                        aria-label={`Fault mode for ${lane.id}`}
                        disabled={laneActionBusy === lane.id}
                        value={lane.faultMode}
                        onChange={(e) => handleLaneFaultChange(lane.id, e.target.value as LaneFaultMode)}
                        className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-800 focus:border-blue-600 focus:outline-none"
                      >
                        {FAULT_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-6 text-right whitespace-nowrap">
                      <button
                        type="button"
                        disabled={laneActionBusy === lane.id}
                        onClick={() => handleLaneTopUp(lane.id)}
                        className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors whitespace-nowrap"
                      >
                        <RefreshCw className="h-3 w-3" aria-hidden="true" />
                        Top Up +$50
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Two-column Split: Atomic Cap-Save Ledger + Live Request Sandbox */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Atomic Cap-Save & Client Key Ledger */}
        <section className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Atomic Client Key Ledger &amp; Cap-Save
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Updates a single key&apos;s daily budget ceiling in place and verifies 100% of active keys before committing.
            </p>

            <div className="mt-4 divide-y divide-slate-200 border border-slate-200 rounded-md">
              {state.clientKeys.map((k) => (
                <div key={k.id} className="p-3.5 flex items-center justify-between gap-4 text-sm">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900">{k.label}</div>
                    <div className="text-xs text-slate-500 font-mono truncate">
                      {k.maskedKey} · {k.boundClient}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-mono tabular-nums font-medium text-slate-900">
                      ${k.spentTodayUsd.toFixed(2)} / ${k.dailyBudgetUsd.toFixed(0)}
                    </div>
                    <div className={`text-xs font-medium ${k.lastProbeStatus === 'pass' ? 'text-emerald-700' : 'text-red-700'}`}>
                      Probe {k.lastProbeStatus === 'pass' ? 'Verified' : 'Failed'}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <form onSubmit={handleCapSave} className="mt-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="cap-key-select" className="block text-xs font-medium text-slate-700">
                    Target Client Key
                  </label>
                  <select
                    id="cap-key-select"
                    value={selectedKeyId}
                    onChange={(e) => {
                      const nextId = e.target.value;
                      setSelectedKeyId(nextId);
                      const found = state.clientKeys.find((k) => k.id === nextId);
                      if (found) setBudgetInput(String(found.dailyBudgetUsd));
                    }}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none"
                  >
                    {state.clientKeys.map((k) => (
                      <option key={k.id} value={k.id}>
                        {k.label} ({k.id})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="cap-budget-input" className="block text-xs font-medium text-slate-700">
                    Daily Budget Ceiling (USD)
                  </label>
                  <input
                    id="cap-budget-input"
                    type="number"
                    min="1"
                    max="100000"
                    step="1"
                    value={budgetInput}
                    onChange={(e) => setBudgetInput(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono tabular-nums text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="inline-flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={testClobberGuard}
                    onChange={(e) => setTestClobberGuard(e.target.checked)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                  />
                  <span>Simulate legacy single-key clobber bug (tests atomic rollback)</span>
                </label>

                <button
                  type="submit"
                  disabled={capSaving}
                  className="rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap disabled:opacity-50"
                >
                  {capSaving ? 'Saving & Probing...' : 'Save Budget Atomically'}
                </button>
              </div>
            </form>
          </div>

          {capSaveFeedback && (
            <div
              role="status"
              className={`mt-4 rounded-md border p-3.5 text-xs ${
                capSaveFeedback.ok
                  ? 'border-emerald-200 bg-emerald-50/70 text-emerald-900'
                  : 'border-amber-200 bg-amber-50/70 text-amber-900'
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                {capSaveFeedback.ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" />
                ) : (
                  <ShieldAlert className="h-4 w-4 text-amber-700 shrink-0" />
                )}
                {capSaveFeedback.ok
                  ? `Committed $${capSaveFeedback.newBudgetUsd} ceiling — ${capSaveFeedback.preservedKeyCount} keys preserved & verified`
                  : capSaveFeedback.error}
              </div>
              {capSaveFeedback.verifiedKeys.length > 0 && (
                <div className="mt-1.5 font-mono text-slate-700">
                  {capSaveFeedback.verifiedKeys
                    .map((v) => `${v.id}: ${v.valid ? 'PASS' : 'FAIL'}`)
                    .join(' · ')}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Live Request Dispatch Sandbox */}
        <section className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Live Router Dispatch &amp; Error Attribution Sandbox
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Send a live request through the gateway to inspect failover hops, 401 vs 402 vs 502 error attribution, and WAL receipts.
            </p>

            <form onSubmit={handleDispatchRequest} className="mt-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label htmlFor="sandbox-client-key" className="block text-xs font-medium text-slate-700">
                    Inbound Bearer Key
                  </label>
                  <select
                    id="sandbox-client-key"
                    value={sandboxKey}
                    onChange={(e) => setSandboxKey(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none"
                  >
                    {state.clientKeys.map((k) => (
                      <option key={k.id} value={k.rawKey}>
                        {k.label} ({k.maskedKey})
                      </option>
                    ))}
                    <option value="pk_invalid_dropped_key">Unknown / Clobbered Key (Tests 401)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="sandbox-tokens" className="block text-xs font-medium text-slate-700">
                    Est. Tokens
                  </label>
                  <input
                    id="sandbox-tokens"
                    type="number"
                    min="64"
                    max="64000"
                    value={sandboxTokens}
                    onChange={(e) => setSandboxTokens(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono tabular-nums text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex-1 min-w-[180px]">
                  <label htmlFor="sandbox-model" className="block text-xs font-medium text-slate-700">
                    Requested Model Slug
                  </label>
                  <input
                    id="sandbox-model"
                    type="text"
                    value={sandboxModel}
                    onChange={(e) => setSandboxModel(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={routingBusy}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
                >
                  <span>{routingBusy ? 'Routing...' : 'Dispatch Request'}</span>
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </form>
          </div>

          <div className="mt-5 border border-slate-200 rounded-md bg-slate-50 p-4">
            {!sandboxResult ? (
              <div className="text-xs text-slate-500">
                No request dispatched in this session yet. Try injecting a 402 fault on DeepSeek Flash above and dispatching a request to observe automatic failover.
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span
                    className={`font-semibold ${
                      sandboxResult.ok ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    HTTP {sandboxResult.httpStatus} ·{' '}
                    {sandboxResult.ok
                      ? `Routed via ${sandboxResult.selectedProvider} (${sandboxResult.selectedLaneId})`
                      : sandboxResult.errorPayload?.error.type}
                  </span>
                  <span className="font-mono tabular-nums text-slate-600">
                    Overhead {sandboxResult.gatewayOverheadUs} µs · Total {sandboxResult.totalLatencyMs} ms
                    {sandboxResult.receiptSequence ? ` · WAL #${sandboxResult.receiptSequence}` : ''}
                  </span>
                </div>

                {sandboxResult.errorPayload && (
                  <div className="rounded bg-red-50 border border-red-200 px-3 py-2 text-xs font-mono text-red-800 break-words">
                    {JSON.stringify(sandboxResult.errorPayload.error)}
                  </div>
                )}

                {sandboxResult.attempts.length > 0 && (
                  <div className="space-y-1">
                    {sandboxResult.attempts.map((a, idx) => (
                      <div
                        key={`${a.laneId}-${idx}`}
                        className="flex items-center justify-between gap-3 text-xs border-t border-slate-200 pt-1.5"
                      >
                        <span className="font-mono text-slate-700">
                          {idx + 1}. {a.laneId} ({a.httpStatus})
                        </span>
                        <span className="text-slate-600 truncate">{a.detail}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Recent Durable WAL Receipts */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Durable WAL Receipt Ledger</h2>
            <p className="mt-0.5 text-sm text-slate-500">
              Append-only sequence log persisted before response acknowledgement to prevent restart loss.
            </p>
          </div>
          <span className="text-xs font-mono tabular-nums text-slate-500">
            Latest Sequence #{state.walStats.latestSequence}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-500">
                <th className="py-2.5 px-6">Sequence</th>
                <th className="py-2.5 px-4">Client Key</th>
                <th className="py-2.5 px-4">Upstream Lane</th>
                <th className="py-2.5 px-4 text-right">Tokens</th>
                <th className="py-2.5 px-4 text-right">Cost</th>
                <th className="py-2.5 px-6 text-right">Durability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {state.recentReceipts.slice(0, 8).map((r) => (
                <tr key={r.sequence} className="hover:bg-slate-50/80">
                  <td className="py-2.5 px-6 font-mono tabular-nums font-medium text-slate-900">
                    #{r.sequence}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-slate-700">{r.clientKeyId}</td>
                  <td className="py-2.5 px-4 text-slate-700">
                    {r.provider} · {r.model}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                    {r.tokens.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                    ${r.costUsd.toFixed(5)}
                  </td>
                  <td className="py-2.5 px-6 text-right font-medium text-emerald-700">
                    {r.persistedToWal ? 'WAL Synced' : 'Buffered'}
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
