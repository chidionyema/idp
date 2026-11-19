import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  PackageCheck,
  Radio,
  RefreshCw,
  Send,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import type {
  ProductionGuaranteesReport,
  SyncTelemetrySnapshot,
} from '../engine/debugPackBuilder';

import type {
  EstateSessionRecord,
  WakeEventRecord,
} from '../engine/ingestReceiver';

interface FleetReceiverSummary {
  acceptedCount: number;
  rejectedCount: number;
  idleCount: number;
  runningCount: number;
  sessions: EstateSessionRecord[];
  wakeEvents: WakeEventRecord[];
}

interface SyncTelemetryPayload {
  sync: SyncTelemetrySnapshot;
  guarantees: ProductionGuaranteesReport;
  fleetReceiver?: FleetReceiverSummary;
}

export function EstateSyncMonitor() {
  const [data, setData] = useState<SyncTelemetryPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [pushing, setPushing] = useState<boolean>(false);
  const [sseConnected, setSseConnected] = useState<boolean>(false);

  const loadSnapshot = useCallback(async () => {
    try {
      const res = await fetch('/api/sync/telemetry');
      if (res.ok) {
        const json = (await res.json()) as SyncTelemetryPayload;
        setData(json);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
    const es = new EventSource('/api/sync/stream');
    es.addEventListener('open', () => setSseConnected(true));
    es.addEventListener('error', () => setSseConnected(false));
    es.addEventListener('snapshot', (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent<string>).data) as SyncTelemetryPayload;
        setData(parsed);
        setLoading(false);
        setSseConnected(true);
      } catch {
        // Ignore malformed SSE frame cleanly
      }
    });
    es.addEventListener('sync_event', (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent<string>).data) as {
          sync: SyncTelemetrySnapshot;
          fleetReceiver?: FleetReceiverSummary;
        };
        setData((prev) =>
          prev
            ? {
                ...prev,
                sync: parsed.sync,
                fleetReceiver: parsed.fleetReceiver ?? prev.fleetReceiver,
              }
            : prev
        );
      } catch {
        // Ignore malformed SSE frame cleanly
      }
    });
    return () => {
      es.close();
    };
  }, [loadSnapshot]);

  async function handleTriggerSync() {
    setPushing(true);
    try {
      await fetch('/api/export/push-bundle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      await loadSnapshot();
    } finally {
      setPushing(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 text-xs text-slate-500">
        Loading real-time estate sync telemetry &amp; readiness guarantees...
      </div>
    );
  }

  if (!data) return null;
  const { sync, guarantees } = data;
  const lastEvent = sync.lastEvent;

  return (
    <div className="space-y-6">
      {/* Top Real-Time Sync & Wake Identity Panel */}
      <section className="rounded-lg bg-slate-950 text-slate-100 border border-slate-800 p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 font-semibold text-sky-400">
                <Radio
                  className={`h-3.5 w-3.5 ${sseConnected ? 'text-emerald-400' : 'text-amber-400'}`}
                  aria-hidden="true"
                />
                {sseConnected ? 'SSE Live Stream Connected' : 'HTTP Polling Fallback'}
              </span>
              <span className="text-slate-600" aria-hidden="true">&middot;</span>
              <span className="font-mono text-slate-400">Session {sync.sessionId}</span>
              <span className="text-slate-600" aria-hidden="true">&middot;</span>
              <span className="font-mono text-amber-300">{sync.wakePolicy}</span>
            </div>
            <h3 className="mt-1 text-base font-semibold text-white">
              Real-Time Reset-Proof Bundle Sync &amp; Session Wake Monitor
            </h3>
            <p className="mt-0.5 text-xs text-slate-400">
              Triggered mechanically by Vite container boot, workspace file watch, npm postbuild, and manual probe. Zero custom env vars required.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <button
              type="button"
              disabled={pushing}
              onClick={handleTriggerSync}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3.5 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
            >
              <Send className="h-3.5 w-3.5" aria-hidden="true" />
              {pushing ? 'Dispatching...' : 'Trigger Live Sync & Wake'}
            </button>
            <button
              type="button"
              onClick={loadSnapshot}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 whitespace-nowrap"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh
            </button>
            <a
              href="/api/export/bundle"
              download="meridian-hermes-today.bundle"
              className="inline-flex items-center gap-1.5 rounded-md border border-amber-400/50 bg-amber-500/15 px-3 py-2 text-xs font-medium text-amber-200 hover:bg-amber-500/25 whitespace-nowrap"
            >
              <PackageCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Git Bundle (.bundle)
            </a>
            <a
              href="/api/debug-pack"
              download="meridian-hermes-debug-pack.json"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Debug Pack JSON
            </a>
            <a
              href="/api/debug-pack?format=markdown"
              download="meridian-hermes-debug-pack.md"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              Debug Pack MD
            </a>
          </div>
        </div>

        {/* Key Telemetry Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 pt-4 border-t border-slate-800 text-xs">
          <div className="min-w-0">
            <div className="text-slate-400">Git HEAD &amp; Clean</div>
            <div className="mt-1 font-mono font-semibold text-white break-words">
              {sync.headSha.slice(0, 8)} · {sync.workingTreeClean ? 'CLEAN' : 'DIRTY'}
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-slate-400">Verified Bundle Size</div>
            <div className="mt-1 font-mono tabular-nums font-semibold text-white">
              {sync.bundleBytes.toLocaleString()} B
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-slate-400">Bundle SHA-256</div>
            <div className="mt-1 font-mono font-semibold text-sky-300 break-all">
              {sync.bundleSha256 ? sync.bundleSha256.slice(0, 16) + '...' : 'PENDING'}
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-slate-400">Outbound Pushes</div>
            <div className="mt-1 font-mono tabular-nums font-semibold text-white">
              {sync.successfulPushes} ok / {sync.failedPushes} unaccepted
            </div>
          </div>
          <div className="min-w-0 col-span-2 lg:col-span-1">
            <div className="text-slate-400">Last Wake Disposition</div>
            <div
              className={`mt-1 font-mono font-semibold break-all ${
                lastEvent?.pushed ? 'text-emerald-400' : 'text-amber-300'
              }`}
            >
              {lastEvent?.wakeDisposition ?? 'AWAITING_FIRST_SYNC'}
            </div>
          </div>
        </div>
      </section>

      {/* Two-Column View: Canonical Endpoint Truth + Production Guarantees */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left 6 Cols: Canonical Ingest Endpoints & Recent Wake/Sync Events */}
        <div className="xl:col-span-6 space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">
                  Canonical Ingest Targets &amp; Failover Order
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Truthful live HTTPS status per endpoint; never simulates green delivery when offline.
                </p>
              </div>
              <Activity className="h-4 w-4 text-slate-500 shrink-0" aria-hidden="true" />
            </div>

            <div className="divide-y divide-slate-200">
              {sync.canonicalEndpoints.map((endpoint, idx) => {
                const attempt = lastEvent?.attempts.find((a) => a.url === endpoint);
                const accepted = Boolean(attempt?.accepted);
                return (
                  <div key={endpoint} className="p-4 flex items-start justify-between gap-3 text-xs">
                    <div className="min-w-0">
                      <div className="font-mono font-semibold text-slate-900 break-all">
                        #{idx + 1} · {endpoint}
                      </div>
                      <div className="mt-1 text-slate-600">
                        {attempt
                          ? `HTTP ${attempt.httpStatus ?? 'ERR'} · ${attempt.latencyMs} ms · ${attempt.error ?? 'Accepted for idle-or-spawn wake'}`
                          : 'No live outbound attempt recorded in current log yet — click Trigger Live Sync & Wake.'}
                      </div>
                    </div>
                    <span
                      className={`inline-flex items-center gap-1 font-mono font-semibold shrink-0 ${
                        accepted ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {accepted ? (
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                      {accepted ? 'ACCEPTED' : attempt ? 'UNAVAILABLE' : 'IDLE'}
                    </span>
                  </div>
                );
              })}
            </div>

            {data.fleetReceiver && (
              <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-700">
                <span>
                  Local Receiver &amp; Fleet Pull Manifest: {data.fleetReceiver.acceptedCount} accepted · {data.fleetReceiver.runningCount} running · {data.fleetReceiver.idleCount} idle workers
                </span>
                <a
                  href="/api/export/manifest"
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-700 hover:underline font-semibold"
                >
                  /api/export/manifest
                </a>
              </div>
            )}
          </section>

          <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">
                  Real-Time Sync &amp; Wake Event Stream ({sync.events.length})
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Every boot, file-watch, postbuild, and manual sync attempt with exact latency.
                </p>
              </div>
              <Terminal className="h-4 w-4 text-slate-500 shrink-0" aria-hidden="true" />
            </div>

            {sync.events.length === 0 ? (
              <div className="p-5 text-xs text-slate-500">
                No sync events persisted yet. Click Trigger Live Sync &amp; Wake or run build.
              </div>
            ) : (
              <div className="divide-y divide-slate-200 max-h-96 overflow-y-auto">
                {sync.events.slice(0, 20).map((ev) => (
                  <div key={ev.eventId} className="px-5 py-3 text-xs space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono font-semibold text-slate-900">
                        {ev.trigger} · {ev.wakeDisposition}
                      </span>
                      <span className="font-mono text-slate-500">
                        {new Date(ev.timestampUtc).toLocaleTimeString()} ({ev.durationMs} ms)
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-600 break-words">
                      SHA {ev.bundleSha256?.slice(0, 12) ?? 'none'} · {ev.bundleBytes.toLocaleString()} B · {ev.reason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Right 6 Cols: Commercial-Grade Production Guarantees G-01..G-07 */}
        <section className="xl:col-span-6 bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-semibold text-slate-900">
                Production Readiness Guarantees ({guarantees.verifiedCount}/{guarantees.totalCount} Verified)
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Live computed audit over all control planes, chaos tests, security guards &amp; ingest receiver.
              </p>
            </div>
            <ShieldCheck
              className={`h-4 w-4 shrink-0 ${
                guarantees.allVerified ? 'text-emerald-700' : 'text-amber-700'
              }`}
              aria-hidden="true"
            />
          </div>

          <div className="divide-y divide-slate-200">
            {guarantees.guarantees.map((g) => (
              <div key={g.id} className="p-4 flex items-start justify-between gap-3 text-xs">
                <div className="min-w-0">
                  <div className="font-semibold text-slate-900">
                    <span className="font-mono text-blue-700">{g.id}</span> · {g.subsystem}
                  </div>
                  <div className="mt-0.5 text-slate-600">{g.guarantee}</div>
                  <div className="mt-1 font-mono text-[11px] text-slate-500 break-words">
                    {g.evidence}
                  </div>
                </div>
                <span
                  className={`font-mono text-[11px] font-semibold shrink-0 ${
                    g.status === 'VERIFIED' ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  {g.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
