import { useEffect, useState } from 'react';
import { Pause, Play, Search, Zap, Eye } from 'lucide-react';
import { PacketTraceRecord } from '../engine/meridianTelemetry';
import { GatewayStateSnapshot, PacketsApiResponse } from '../types/api';

interface PacketForensicsProps {
  onStateChange?: (next: GatewayStateSnapshot) => void;
}

export function PacketForensics({ onStateChange }: PacketForensicsProps) {
  const [data, setData] = useState<PacketsApiResponse | null>(null);
  const [selectedPacketId, setSelectedPacketId] = useState<string | null>(null);
  const [liveStreaming, setLiveStreaming] = useState(true);
  const [busy, setBusy] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'DIRECT' | 'ESTIMATED' | 'BLIND'>('ALL');

  async function fetchPackets() {
    const res = await fetch('/api/packets?limit=60');
    if (res.ok) {
      const json = (await res.json()) as PacketsApiResponse;
      setData(json);
      if (!selectedPacketId && json.packets.length > 0) {
        setSelectedPacketId(json.packets[0].packetId);
      }
    }
  }

  useEffect(() => {
    void fetchPackets();
  }, []);

  useEffect(() => {
    if (!liveStreaming || typeof EventSource === 'undefined') return;
    const es = new EventSource('/api/union/stream');
    const onSnapshot = () => {
      void fetchPackets();
    };
    es.addEventListener('union_snapshot', onSnapshot);
    return () => {
      es.removeEventListener('union_snapshot', onSnapshot);
      es.close();
    };
  }, [liveStreaming]);

  async function handleBurst() {
    setBusy(true);
    try {
      const res = await fetch('/api/packets/burst', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 8 }),
      });
      if (res.ok) {
        const json = (await res.json()) as PacketsApiResponse;
        setData(json);
        if (json.packets.length > 0) {
          setSelectedPacketId(json.packets[0].packetId);
        }
        if (json.state && onStateChange) {
          onStateChange(json.state);
        }
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleBaselineChange(baselineModelSlug: string) {
    setBusy(true);
    try {
      const res = await fetch('/api/meridian/baseline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baselineModelSlug }),
      });
      if (res.ok) {
        const json = (await res.json()) as PacketsApiResponse;
        setData(json);
        if (json.state && onStateChange) {
          onStateChange(json.state);
        }
      }
    } finally {
      setBusy(false);
    }
  }

  if (!data) {
    return (
      <div className="space-y-4">
        <div className="h-28 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-96 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  const { summary, packets, rateCards } = data;
  const filteredPackets = packets.filter((p) => {
    if (statusFilter !== 'ALL') {
      const matchesStatus =
        p.measurementStatus === statusFilter ||
        p.reasoningMeasurementStatus === statusFilter;
      if (!matchesStatus) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        p.packetId.toLowerCase().includes(q) ||
        p.provider.toLowerCase().includes(q) ||
        p.economics.modelSlug.toLowerCase().includes(q) ||
        p.missionId.toLowerCase().includes(q) ||
        p.otelSpan.traceId.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const inspectedPacket: PacketTraceRecord | undefined =
    packets.find((p) => p.packetId === selectedPacketId) ?? filteredPackets[0];

  return (
    <div className="space-y-6">
      {/* Real-time Telemetry & Counterfactual Savings Header */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-5 border-b border-slate-200">
          <div className="max-w-2xl">
            <h2 className="text-base font-semibold text-slate-900">
              Forensic Packet Stream &amp; Exact Provider Token Economics
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Every admitted packet is metered token-by-token against provider rate cards and compared against an unrouted, uncached baseline without PennyD.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <label htmlFor="baseline-model-select" className="text-xs font-medium text-slate-600 whitespace-nowrap">
                Without PennyD Baseline:
              </label>
              <select
                id="baseline-model-select"
                disabled={busy}
                value={summary.baselineModelSlug}
                onChange={(e) => handleBaselineChange(e.target.value)}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-900 focus:border-blue-600 focus:outline-none"
              >
                <option value="claude-sonnet-4">Claude Sonnet 4 ($3.00 / $15.00)</option>
                <option value="claude-opus-4-1">Claude Opus 4.1 ($15.00 / $75.00)</option>
                <option value="gpt-4o">GPT-4o Direct ($2.50 / $10.00)</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => setLiveStreaming((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
            >
              {liveStreaming ? (
                <>
                  <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                  Pause Stream
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" aria-hidden="true" />
                  Resume Stream
                </>
              )}
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={handleBurst}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5" aria-hidden="true" />
              {busy ? 'Dispatching...' : 'Dispatch 8-Packet Burst'}
            </button>
          </div>
        </div>

        {/* 4-Column Exact Token & Counterfactual Savings KPIs */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs font-medium text-slate-500">Executed Tokens Metered</div>
            <div className="mt-1.5 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              {summary.totalExecutedTokens.toLocaleString()}
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              In {summary.uncachedInputTokens.toLocaleString()} · Cache {summary.cachedInputTokens.toLocaleString()} · Out {(summary.outputTokens + summary.reasoningTokens).toLocaleString()}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs font-medium text-slate-500">Tokens Saved (Cache + Trim)</div>
            <div className="mt-1.5 text-2xl font-mono tabular-nums font-semibold text-blue-700">
              {summary.tokensSavedByPennyD.toLocaleString()}
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              Avg throughput {summary.avgThroughputTokPerSec} tok/s
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs font-medium text-slate-500">Actual Spend vs. Without PennyD</div>
            <div className="mt-1.5 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              ${summary.actualSpendUsd.toFixed(4)}
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-500">
              Without PennyD: ${summary.withoutPennydSpendUsd.toFixed(4)}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs font-medium text-slate-500">Verified Net Cost Savings</div>
            <div className="mt-1.5 text-2xl font-mono tabular-nums font-semibold text-emerald-700">
              ${summary.netSavingsUsd.toFixed(4)}
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-emerald-700 font-medium">
              {summary.savingsPct.toFixed(2)}% reduction · {summary.blindCount} blind flags visible
            </div>
          </div>
        </div>
      </section>

      {/* Per-Provider Rate & Exact Spend Reconciliation */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Per-Provider Rate Card &amp; Counterfactual Spend Breakdown
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Exact per-1M input, cache-hit, and output rates applied to captured packets.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">
            Baseline: {summary.baselineModelSlug}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
                <th className="py-2.5 px-6 font-medium">Provider · Model</th>
                <th className="py-2.5 px-4 font-medium text-right">Rate (In / Cache / Out per 1M)</th>
                <th className="py-2.5 px-4 font-medium text-right">Packets</th>
                <th className="py-2.5 px-4 font-medium text-right">Executed Tokens</th>
                <th className="py-2.5 px-4 font-medium text-right">Actual Cost</th>
                <th className="py-2.5 px-4 font-medium text-right">Without PennyD</th>
                <th className="py-2.5 px-6 font-medium text-right">Net Saved</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {summary.byProvider.map((row) => {
                const rc = rateCards.find((r) => r.modelSlug === row.modelSlug);
                return (
                  <tr key={`${row.provider}-${row.modelSlug}`} className="hover:bg-slate-50/80">
                    <td className="py-2.5 px-6 font-medium text-slate-900">
                      {row.provider} · <span className="font-mono text-slate-600">{row.modelSlug}</span>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-600">
                      {rc
                        ? `$${rc.inputPer1MUsd.toFixed(2)} / $${rc.cachedInputPer1MUsd.toFixed(3)} / $${rc.outputPer1MUsd.toFixed(2)}`
                        : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                      {row.packets}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                      {row.executedTokens.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums font-medium text-slate-900">
                      ${row.actualUsd.toFixed(6)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-600">
                      ${row.withoutPennydUsd.toFixed(6)}
                    </td>
                    <td className="py-2.5 px-6 text-right font-mono tabular-nums font-semibold text-emerald-700">
                      ${row.savedUsd.toFixed(6)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Packet Stream + Forensic Zero-Black-Box Inspector */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Live Packet Table */}
        <section className="xl:col-span-7 bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input
                type="search"
                aria-label="Filter packets by ID, provider, mission, or trace"
                placeholder="Filter packet, provider, mission, traceId..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
              />
            </div>

            <div role="group" aria-label="Filter measurement status" className="flex items-center gap-1 p-1 bg-slate-100 rounded-md">
              {(['ALL', 'DIRECT', 'ESTIMATED', 'BLIND'] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 text-xs font-medium rounded whitespace-nowrap ${
                    statusFilter === st
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Packet / Mission</th>
                  <th className="py-2.5 px-3 font-medium">Provider · Model</th>
                  <th className="py-2.5 px-3 font-medium text-right">Tokens</th>
                  <th className="py-2.5 px-3 font-medium text-right">Latency · Rate</th>
                  <th className="py-2.5 px-3 font-medium text-right">Saved</th>
                  <th className="py-2.5 px-4 font-medium text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredPackets.map((pkt) => {
                  const isSelected = inspectedPacket?.packetId === pkt.packetId;
                  return (
                    <tr
                      key={pkt.packetId}
                      className={isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50/80'}
                    >
                      <td className="py-2.5 px-4">
                        <div className="font-mono font-semibold text-slate-900">{pkt.packetId}</div>
                        <div className="text-[11px] font-mono text-slate-500">
                          {pkt.missionId} · {pkt.measurementStatus}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="text-slate-900 font-medium">{pkt.provider}</div>
                        <div className="font-mono text-[11px] text-slate-500">{pkt.economics.modelSlug}</div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-800">
                        <div>{pkt.economics.totalExecutedTokens.toLocaleString()}</div>
                        <div className="text-[11px] text-blue-700">
                          -{pkt.economics.tokensSavedByPennyD.toLocaleString()} saved
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700">
                        <div>{pkt.timings.totalMs} ms</div>
                        <div className="text-[11px] text-slate-500">{pkt.timings.tokensPerSec} tok/s</div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                        <div className="font-semibold text-emerald-700">
                          ${pkt.economics.usdSaved.toFixed(5)}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          actual ${pkt.economics.actualTotalCostUsd.toFixed(5)}
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedPacketId(pkt.packetId)}
                          aria-label={`Inspect packet ${pkt.packetId}`}
                          className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <Eye className="h-3 w-3" aria-hidden="true" />
                          Trace
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Zero-Black-Box Forensic Inspector Panel */}
        <section className="xl:col-span-5 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
          {!inspectedPacket ? (
            <div className="text-xs text-slate-500">Select any packet to inspect wire telemetry and math proof.</div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Forensic Trace · {inspectedPacket.packetId}
                  </h3>
                  <div className="mt-0.5 text-xs font-mono text-slate-500">
                    {inspectedPacket.missionId} · {inspectedPacket.executionId} · {inspectedPacket.ownerId}
                  </div>
                </div>
                <span className="text-xs font-mono font-semibold text-slate-900">
                  HTTP {inspectedPacket.httpStatus}
                </span>
              </div>

              {/* Wire Timing Waterfall */}
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-2">
                  Wire Latency &amp; Throughput Waterfall ({inspectedPacket.timings.totalMs} ms total)
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono tabular-nums">
                  <div className="border border-slate-200 rounded p-2.5">
                    <div className="text-slate-500 text-[11px]">Gateway Auth/Cap</div>
                    <div className="font-semibold text-slate-900">
                      {inspectedPacket.timings.gatewayAuthAndCapUs} µs
                    </div>
                  </div>
                  <div className="border border-slate-200 rounded p-2.5">
                    <div className="text-slate-500 text-[11px]">DNS / TLS + TTFB</div>
                    <div className="font-semibold text-slate-900">
                      {inspectedPacket.timings.dnsTlsMs} + {inspectedPacket.timings.upstreamTtfbMs} ms
                    </div>
                  </div>
                  <div className="border border-slate-200 rounded p-2.5">
                    <div className="text-slate-500 text-[11px]">Token Stream</div>
                    <div className="font-semibold text-slate-900">
                      {inspectedPacket.timings.tokenStreamMs} ms ({inspectedPacket.timings.tokensPerSec} tok/s)
                    </div>
                  </div>
                  <div className="border border-slate-200 rounded p-2.5">
                    <div className="text-slate-500 text-[11px]">Host Energy (Joules)</div>
                    <div
                      className={`font-semibold ${
                        inspectedPacket.computeEnergyJoules === null ? 'text-amber-700' : 'text-slate-900'
                      }`}
                    >
                      {inspectedPacket.computeEnergyJoules === null
                        ? 'BLIND (Unknown)'
                        : `${inspectedPacket.computeEnergyJoules} J`}
                    </div>
                  </div>
                </div>
              </div>

              {/* Exact Token Formula Proof */}
              <div className="border border-slate-200 rounded-md bg-slate-50 p-3 space-y-1.5">
                <div className="text-xs font-semibold text-slate-800">Exact Token &amp; Counterfactual Math</div>
                <div className="text-[11px] font-mono text-slate-700 break-words leading-relaxed">
                  {inspectedPacket.economics.formulaSummary}
                </div>
                <div className="text-xs font-mono font-semibold text-emerald-700 pt-1">
                  Net Saved: ${inspectedPacket.economics.usdSaved.toFixed(6)} ({inspectedPacket.economics.savingsPct}%) ·{' '}
                  {inspectedPacket.economics.tokensSavedByPennyD.toLocaleString()} tokens avoided
                </div>
              </div>

              {/* OTel GenAI + FOCUS Provenance */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-700">
                  OpenTelemetry ({inspectedPacket.otelSpan.schemaVersion}) &amp; FOCUS 1.0 Provenance
                </div>
                <pre className="rounded-md border border-slate-200 bg-slate-900 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto leading-relaxed">
{JSON.stringify(
  {
    otel: inspectedPacket.otelSpan,
    focus: inspectedPacket.focusEntry,
    evidenceRef: inspectedPacket.independentEvidenceRef,
  },
  null,
  2
)}
                </pre>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
