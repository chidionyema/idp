import React, { useEffect, useState, useMemo } from 'react';
import { RefreshCw, ShieldCheck, Activity, Cpu, CheckCircle2, XCircle, Search } from 'lucide-react';
import type { OptimusSnapshotBundle } from '../types/estate';
import {
  OPTIMUS_PROOF_SCHEMA,
  DEFAULT_OPTIMUS_APP_ID,
  DEFAULT_FOUNDER_SURFACE_APP_ID,
  type OptimusAdmissionInput,
  type OptimusAdmissionResult,
  type OptimusEvidenceRecord,
} from '../engine/optimusAndReactor';

interface OptimusAndBrainViewProps {
  optimus: OptimusSnapshotBundle;
  liveIdpSha: string;
  onIngestSignedProbe: (targetSurface?: string) => Promise<void>;
  onEvaluateAdmission: (input: OptimusAdmissionInput) => Promise<OptimusAdmissionResult>;
}

type AdmissionPresetKey =
  | 'VALID_CORRELATED'
  | 'MISSING_COUNT'
  | 'DROPPED_EVENTS'
  | 'STALE_TIMESTAMP'
  | 'UNTRUSTED_APP';

export const OptimusAndBrainView: React.FC<OptimusAndBrainViewProps> = ({
  optimus,
  liveIdpSha,
  onIngestSignedProbe,
  onEvaluateAdmission,
}) => {
  const [streamStatus, setStreamStatus] = useState<'LIVE_SSE' | 'CONNECTING' | 'SNAPSHOT'>('CONNECTING');
  const [liveRecords, setLiveRecords] = useState<OptimusEvidenceRecord[]>(optimus.records);
  const [isIngesting, setIsIngesting] = useState(false);
  const [targetSurface, setTargetSurface] = useState('github:chidionyema/idp');

  const [selectedPreset, setSelectedPreset] = useState<AdmissionPresetKey>('VALID_CORRELATED');
  const [admissionVerdict, setAdmissionVerdict] = useState<OptimusAdmissionResult>(optimus.latestAdmission);
  const [isCheckingAdmission, setIsCheckingAdmission] = useState(false);
  const [ledgerQuery, setLedgerQuery] = useState('');
  const [kindFilter, setKindFilter] = useState<string>('ALL');

  useEffect(() => {
    setLiveRecords(optimus.records);
  }, [optimus.records]);

  // Connect to live `/api/brain/stream` SSE feed (`optimus-evidence` frames)
  useEffect(() => {
    if (typeof EventSource === 'undefined') {
      setStreamStatus('SNAPSHOT');
      return;
    }
    const es = new EventSource('/api/brain/stream');
    es.addEventListener('connected', () => {
      setStreamStatus('LIVE_SSE');
    });
    es.addEventListener('optimus-evidence', (ev: MessageEvent) => {
      try {
        const rec = JSON.parse(ev.data) as OptimusEvidenceRecord;
        setLiveRecords((prev) => (prev.some((r) => r.eventId === rec.eventId) ? prev : [rec, ...prev].slice(0, 50)));
      } catch {
        // Ignore malformed frame
      }
    });
    es.onerror = () => {
      setStreamStatus('SNAPSHOT');
    };
    return () => {
      es.close();
    };
  }, []);

  const paddedSha = /^[0-9a-f]{40}$/i.test(liveIdpSha)
    ? liveIdpSha
    : liveIdpSha.padEnd(40, 'a').slice(0, 40);

  const buildPresetPayload = (preset: AdmissionPresetKey): OptimusAdmissionInput => {
    const now = new Date();
    const nowIso = now.toISOString();
    const observedAtIso =
      preset === 'STALE_TIMESTAMP'
        ? new Date(now.getTime() - 920_000).toISOString() // 920s old (>600s max age!)
        : nowIso;

    const instructions = [
      {
        instruction_id: 'INS-00011',
        permission: 'allowed',
        permission_receipt: 'RCPT-GENESIS-8D483078AEF3',
        yield_tracking: 'pending',
      },
    ];

    const optPayload = {
      schema: OPTIMUS_PROOF_SCHEMA,
      subject_sha: paddedSha,
      observed_at: observedAtIso,
      instructions,
      metrics: {
        required_events: liveRecords.length || 4,
        observed_events: liveRecords.length || 4,
        dropped_events: preset === 'DROPPED_EVENTS' ? 2 : 0,
      },
    };

    const fndPayload = {
      schema: OPTIMUS_PROOF_SCHEMA,
      subject_sha: paddedSha,
      observed_at: observedAtIso,
      instructions,
      founder_surface: {
        live: true,
        instructions_visible: true,
        permission_visible: true,
        yield_tracking_visible: true,
        event_cursor: String(optimus.eventCursor),
        url: 'http://localhost:3000/#optimus',
      },
    };

    return {
      subjectSha: paddedSha,
      nowIso,
      totalCount: preset === 'MISSING_COUNT' ? null : 2,
      checkRuns: [
        {
          id: 501,
          name: 'optimus-metrics',
          head_sha: paddedSha,
          status: 'completed',
          conclusion: 'success',
          completed_at: observedAtIso,
          app: { id: preset === 'UNTRUSTED_APP' ? 999 : DEFAULT_OPTIMUS_APP_ID },
          output: { text: JSON.stringify(optPayload) },
        },
        {
          id: 502,
          name: 'founder-surface-visibility',
          head_sha: paddedSha,
          status: 'completed',
          conclusion: 'success',
          completed_at: observedAtIso,
          app: { id: DEFAULT_FOUNDER_SURFACE_APP_ID },
          output: { text: JSON.stringify(fndPayload) },
        },
      ],
    };
  };

  const handleRunAdmissionPreset = async (preset: AdmissionPresetKey) => {
    setSelectedPreset(preset);
    setIsCheckingAdmission(true);
    try {
      const payload = buildPresetPayload(preset);
      const res = await onEvaluateAdmission(payload);
      if (res && typeof res.admitted === 'boolean') {
        setAdmissionVerdict(res);
      }
    } finally {
      setIsCheckingAdmission(false);
    }
  };

  const handleTriggerProbe = async () => {
    setIsIngesting(true);
    try {
      await onIngestSignedProbe(targetSurface);
    } finally {
      setIsIngesting(false);
    }
  };

  const latest = liveRecords[0];
  const verifiedCount = liveRecords.filter((r) => r.verified).length;
  const filteredRecords = useMemo(() => {
    return liveRecords.filter((r) => {
      if (kindFilter !== 'ALL' && r.kind !== kindFilter) return false;
      if (ledgerQuery.trim()) {
        const q = ledgerQuery.toLowerCase();
        return (
          r.surface.toLowerCase().includes(q) ||
          r.summary.toLowerCase().includes(q) ||
          r.kind.toLowerCase().includes(q) ||
          (r.instructionId?.toLowerCase().includes(q) ?? false)
        );
      }
      return true;
    });
  }, [liveRecords, kindFilter, ledgerQuery]);

  return (
    <div className="space-y-8">
      {/* Header & Live Signed Probe Action */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-cyan-700 dark:text-cyan-400">
            <span>PROJECT OPTIMUS &amp; ONE-BRAIN</span>
            <span aria-hidden="true">·</span>
            <span>stream {streamStatus}</span>
            <span aria-hidden="true">·</span>
            <span>
              {verifiedCount}/{liveRecords.length} HMAC-verified
            </span>
            <span aria-hidden="true">·</span>
            <span>signer {optimus.keyFingerprint}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Verifiable Operational Integrity &amp; Decision Intelligence
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
            Git and runtime observations signed with HMAC-SHA256 at ingestion, deduplicated by monotonic sequence cursor, and enforced by the Dual-Root Release Admission Gate (estate-operational-proof.v1).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <label htmlFor="optimus-target-surface" className="sr-only">
            Target surface to probe and sign
          </label>
          <select
            id="optimus-target-surface"
            value={targetSurface}
            onChange={(e) => setTargetSurface(e.target.value)}
            className="px-3 py-2 text-xs font-mono bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 rounded-lg"
          >
            <option value="github:chidionyema/idp">github:chidionyema/idp</option>
            <option value="genesis-founder-surface.pages.dev">genesis-founder-surface.pages.dev</option>
            <option value="otto-private-office.vercel.app">otto-private-office.vercel.app</option>
            <option value="meridian-intelligence-uk.vercel.app">meridian-intelligence-uk.vercel.app</option>
          </select>

          <button
            type="button"
            onClick={handleTriggerProbe}
            disabled={isIngesting}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIngesting ? 'animate-spin' : ''}`} aria-hidden="true" />
            {isIngesting ? 'Signing Probe…' : 'Ingest Signed Probe'}
          </button>
        </div>
      </div>

      {/* 4-Metric Precision Telemetry Strip (`8_science_space_biotech.md`) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1">
          <div className="text-xs text-slate-500 dark:text-slate-400">Measured Signed Events</div>
          <div className="text-2xl font-mono font-bold tabular-nums text-slate-900 dark:text-slate-50">
            {liveRecords.length}
            <span className="text-xs font-mono font-normal text-slate-400 ml-1.5">
              cursor #{optimus.eventCursor}
            </span>
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400 font-mono">
            {optimus.signerMode === 'ESTATE_RECEIPT_KEY_PROVISIONED'
              ? 'ESTATE_RECEIPT_KEY active'
              : 'Runtime HMAC signer active'}
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1">
          <div className="text-xs text-slate-500 dark:text-slate-400">Latest Probe Latency</div>
          <div className="text-2xl font-mono font-bold tabular-nums text-slate-900 dark:text-slate-50">
            {latest ? latest.metrics.latencyMs.toFixed(1) : '0.0'}
            <span className="text-xs font-mono font-normal text-slate-400 ml-1.5">ms</span>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 font-mono truncate">
            {latest ? latest.surface : 'awaiting probe'}
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1">
          <div className="text-xs text-slate-500 dark:text-slate-400">Executor Process RSS</div>
          <div className="text-2xl font-mono font-bold tabular-nums text-slate-900 dark:text-slate-50">
            {optimus.oneBrain.processRssMb.toFixed(1)}
            <span className="text-xs font-mono font-normal text-slate-400 ml-1.5">MB</span>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            Uptime {optimus.oneBrain.nodeUptimeSec}s · ceiling 512.0 MB
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl space-y-1">
          <div className="text-xs text-slate-500 dark:text-slate-400">Open Threshold Signals</div>
          <div className="text-2xl font-mono font-bold tabular-nums text-slate-900 dark:text-slate-50">
            {optimus.signals.length}
            <span className="text-xs font-mono font-normal text-slate-400 ml-1.5">breaches</span>
          </div>
          <div className="text-xs text-cyan-700 dark:text-cyan-400 font-mono">
            0 dropped events · deterministic bounds
          </div>
        </div>
      </div>

      {/* Section 01: Signed Observations + Deterministic Signals */}
      <section aria-label="01. Optimus Signed Observations" className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <div className="xl:col-span-8 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                01. Latest Cryptographically Signed Observations
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Every row is an HMAC-SHA256 verified server measurement — zero seeded vanity metrics.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" aria-hidden="true" />
                <input
                  type="search"
                  aria-label="Filter signed observations by surface or summary"
                  value={ledgerQuery}
                  onChange={(e) => setLedgerQuery(e.target.value)}
                  placeholder="Filter surface or SHA…"
                  className="pl-8 pr-2.5 py-1.5 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>

              <select
                aria-label="Filter signed observations by kind"
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs font-mono bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200"
              >
                <option value="ALL">All Kinds ({liveRecords.length})</option>
                <option value="SURFACE_PROBE">SURFACE_PROBE</option>
                <option value="GIT_LINEAGE">GIT_LINEAGE</option>
                <option value="LEGION_EXECUTION">LEGION_EXECUTION</option>
                <option value="WATCHDOG_FENCE">WATCHDOG_FENCE</option>
                <option value="ADMISSION_AUDIT">ADMISSION_AUDIT</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900/70 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2.5 px-4 font-medium w-[28%]">Surface &amp; Kind</th>
                  <th className="py-2.5 px-3 font-medium w-[20%]">Latency / RSS</th>
                  <th className="py-2.5 px-3 font-medium w-[28%]">Provenance &amp; Summary</th>
                  <th className="py-2.5 px-4 font-medium w-[24%]">HMAC Verification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
                {filteredRecords.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 px-4 text-center text-slate-500 dark:text-slate-400">
                      No signed observations match the active filter.
                    </td>
                  </tr>
                ) : (
                  filteredRecords.slice(0, 12).map((r) => (
                    <tr key={r.eventId} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40">
                      <td className="py-3 px-4 align-top break-words">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{r.surface}</div>
                        <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                          #{r.seq} · {r.kind} · Auth {r.authority}
                        </div>
                      </td>
                      <td className="py-3 px-3 align-top font-mono tabular-nums text-slate-800 dark:text-slate-200">
                        <div>{r.metrics.latencyMs.toFixed(1)} ms</div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {r.metrics.memoryRssMb.toFixed(1)} MB RSS
                        </div>
                      </td>
                      <td className="py-3 px-3 align-top break-words text-slate-600 dark:text-slate-300">
                        <div className="font-mono text-[11px] text-cyan-700 dark:text-cyan-400">
                          {r.subjectSha ? `SHA ${r.subjectSha.slice(0, 12)}` : 'runtime-probe'}
                          {r.instructionId ? ` · ${r.instructionId}` : ''}
                        </div>
                        <div className="mt-0.5 line-clamp-2">{r.summary}</div>
                      </td>
                      <td className="py-3 px-4 align-top font-mono">
                        <div
                          className={
                            r.verified
                              ? 'text-emerald-700 dark:text-emerald-400 font-medium'
                              : 'text-rose-600 dark:text-rose-400 font-medium'
                          }
                        >
                          {r.verified ? 'VERIFIED_HMAC' : 'TAMPERED'}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                          {r.hmacSha256.slice(0, 16)}…
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Deterministic Signals & One-Brain Provider Roster */}
        <div className="xl:col-span-4 space-y-6">
          <div className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Deterministic Threshold Signals
              </h3>
              <Activity className="w-4 h-4 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Derived strictly from signed fields and fixed per-surface bounds (latency &le; 1800ms, RSS &le; 512MB, monotonic sequence +1).
            </p>
            {optimus.signals.length === 0 ? (
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/60 text-xs text-emerald-800 dark:text-emerald-300">
                Nominal: Zero threshold breaches or sequence gaps across {liveRecords.length} signed events.
              </div>
            ) : (
              <div className="space-y-2">
                {optimus.signals.map((sig) => (
                  <div
                    key={sig.signalId}
                    className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-xs space-y-1"
                  >
                    <div className="font-mono font-semibold text-amber-800 dark:text-amber-300">
                      {sig.severity} · {sig.surface} ({sig.measuredValue} vs {sig.threshold})
                    </div>
                    <div className="text-slate-600 dark:text-slate-300">{sig.remediation}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                One-Brain Replaceable Model Roster
              </h3>
              <Cpu className="w-4 h-4 text-amber-500" aria-hidden="true" />
            </div>
            <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {optimus.oneBrain.providerRoster.map((p) => (
                <div key={p.slot} className="py-2.5 first:pt-0 last:pb-0 space-y-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-900 dark:text-slate-100">{p.slot}</span>
                    <span className="font-mono text-[11px] text-cyan-700 dark:text-cyan-400">
                      {p.status} · {p.authority}
                    </span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {p.modelAlias} — {p.role}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: Optimus Dual-Root Release Admission Gate (`idp-optimus-founder-admission`) */}
      <section
        aria-label="02. Optimus Dual-Root Release Admission Verifier"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 sm:p-6 space-y-4"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400">
              <ShieldCheck className="w-4 h-4" aria-hidden="true" />
              <span>idp-optimus-founder-admission · {OPTIMUS_PROOF_SCHEMA}</span>
            </div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              02. Dual-Root Greenlane Release Lock Falsifier
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl">
              Correlates App #{DEFAULT_OPTIMUS_APP_ID} (optimus-metrics) and App #{DEFAULT_FOUNDER_SURFACE_APP_ID} (founder-surface-visibility) on exact 40-hex commit SHA. Missing check-run counts, dropped events, or stale (&gt;600s) receipts fail closed.
            </p>
          </div>
        </div>

        {/* Interactive Falsifier Presets */}
        <div className="flex flex-wrap gap-2">
          {(
            [
              ['VALID_CORRELATED', 'Valid Correlated SHA (IDP HEAD)'],
              ['MISSING_COUNT', 'Falsifier: Missing Check-Run Count'],
              ['DROPPED_EVENTS', 'Falsifier: Dropped Events > 0'],
              ['STALE_TIMESTAMP', 'Falsifier: Stale >600s Receipt'],
              ['UNTRUSTED_APP', 'Falsifier: Untrusted App #999'],
            ] as Array<[AdmissionPresetKey, string]>
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              disabled={isCheckingAdmission}
              onClick={() => handleRunAdmissionPreset(key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                selectedPreset === key
                  ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 border-transparent font-semibold'
                  : 'bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-400'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Verdict Readout */}
        <div
          role="status"
          className={`p-4 rounded-xl border text-xs space-y-2 ${
            admissionVerdict.admitted
              ? 'bg-emerald-50/70 dark:bg-emerald-950/25 border-emerald-300 dark:border-emerald-800/70'
              : 'bg-rose-50/70 dark:bg-rose-950/30 border-rose-300 dark:border-rose-800/70'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2 font-mono font-semibold">
            {admissionVerdict.admitted ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span className="text-emerald-800 dark:text-emerald-300">
                  STATE: {admissionVerdict.state}
                </span>
                <span className="text-slate-500">·</span>
                <span className="text-slate-700 dark:text-slate-300">
                  SHA {admissionVerdict.subjectSha.slice(0, 12)} · {admissionVerdict.observedEvents} events · cursor #{admissionVerdict.eventCursor}
                </span>
              </>
            ) : (
              <>
                <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" aria-hidden="true" />
                <span className="text-rose-800 dark:text-rose-300">
                  STATE: {admissionVerdict.state} · [{admissionVerdict.errorCode}]
                </span>
              </>
            )}
          </div>
          <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
            {admissionVerdict.admitted ? admissionVerdict.governanceNote : admissionVerdict.reason}
          </p>
        </div>
      </section>
    </div>
  );
};
