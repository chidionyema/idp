import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Eye,
  Layers,
  ArrowRight,
  Volume2,
  VolumeX,
  Orbit,
} from 'lucide-react';
import type { EstateStateSnapshot } from '../types/estate';

interface FleetOverviewViewProps {
  snapshot: EstateStateSnapshot;
  isReprobing: boolean;
  onReprobe: () => void;
  onNavigateTab: (tab: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos') => void;
  onSelectMissionForLegion: (instructionId: string, title: string, body: string, repo: string) => void;
  onPlayBriefing: () => void;
  onStopBriefing: () => void;
  isPlayingBriefing: boolean;
  briefingScript: string | null;
}

export const FleetOverviewView: React.FC<FleetOverviewViewProps> = ({
  snapshot,
  isReprobing,
  onReprobe,
  onNavigateTab,
  onSelectMissionForLegion,
  onPlayBriefing,
  onStopBriefing,
  isPlayingBriefing,
  briefingScript,
}) => {
  const [eyeMode, setEyeMode] = useState<'all-seeing' | 'one-eye'>('all-seeing');
  const [selectedWorkerInstId, setSelectedWorkerInstId] = useState<string>(
    snapshot.flowInstructions[0]?.instructionId ?? ''
  );

  const activeInst =
    snapshot.flowInstructions.find((f) => f.instructionId === selectedWorkerInstId) ??
    snapshot.flowInstructions[0];
  const linkedExec = activeInst
    ? snapshot.executions.find((e) => e.instructionId === activeInst.instructionId)
    : snapshot.executions[0];

  const liveSurfacesOk = snapshot.surfaces.filter((s) => s.verdict === 'VERIFIED_LIVE').length;
  const readyPrCount = snapshot.reconciledPullRequests.filter(
    (p) => p.disposition === 'READY_FOR_GREENLANE'
  ).length;
  const driftPrCount = snapshot.reconciledPullRequests.filter(
    (p) => p.driftState === 'HEAD_MOVED_LIVE' || p.mainMoved
  ).length;

  return (
    <div className="space-y-8">
      {/* Workspace Toolbar: Spatial/Matrix Morph + Eye Perspective Switch + Re-Probe + Executive Audio Readback */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 text-balance">
            {eyeMode === 'all-seeing'
              ? 'All-Seeing Eye: Reconciled Estate Truth'
              : 'One Eye: Fenced Worker Evidence & 7-Gate Trace'}
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Observed <span className="font-mono tabular-nums">{snapshot.observedAt.replace('T', ' ').slice(0, 19)} UTC</span>
            <span className="mx-2" aria-hidden="true">·</span>
            Receipt <span className="font-mono tabular-nums">{snapshot.receipt.receiptId}</span>
            <span className="mx-2" aria-hidden="true">·</span>
            Zero silent E3/U to E1 authority promotion
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => onNavigateTab('reactor')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-amber-900 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/70 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors whitespace-nowrap shrink-0"
          >
            <Orbit className="w-3.5 h-3.5" aria-hidden="true" />
            3D Reactor 2100
          </button>

          <div
            role="group"
            aria-label="Founder perspective mode"
            className="inline-flex items-center p-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"
          >
            <button
              type="button"
              onClick={() => setEyeMode('all-seeing')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                eyeMode === 'all-seeing'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" aria-hidden="true" />
              All-Seeing Eye
            </button>
            <button
              type="button"
              onClick={() => setEyeMode('one-eye')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                eyeMode === 'one-eye'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Eye className="w-3.5 h-3.5" aria-hidden="true" />
              One Eye
            </button>
          </div>

          {!isPlayingBriefing ? (
            <button
              type="button"
              onClick={onPlayBriefing}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" aria-hidden="true" />
              Play Audio Briefing
            </button>
          ) : (
            <button
              type="button"
              onClick={onStopBriefing}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />
              Stop Audio
            </button>
          )}

          <button
            type="button"
            onClick={onReprobe}
            disabled={isReprobing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isReprobing ? 'animate-spin' : ''}`} aria-hidden="true" />
            {isReprobing ? 'Probing Live Estate...' : 'Re-Probe Live Estate'}
          </button>
        </div>
      </div>

      {briefingScript && (
        <div className="p-4 bg-white dark:bg-[#0B101D] border border-amber-300 dark:border-amber-500/40 rounded-xl">
          <div className="text-xs font-mono text-amber-700 dark:text-amber-400 mb-1">
            CAPTAIN EXECUTIVE SITREP TRANSCRIPT
          </div>
          <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">{briefingScript}</p>
        </div>
      )}

      {/* Quantitative Estate Summary Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800">
        <div className="p-5">
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Handover Cryptographic Receipt
          </div>
          <div className="mt-1.5 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
            {snapshot.receipt.handoverSha256.slice(0, 12)}
          </div>
          <div className="mt-1 text-xs text-emerald-700 dark:text-emerald-400 font-medium">
            E1 Verified · {snapshot.receipt.handoverLines} lines · {(snapshot.receipt.handoverBytes / 1024).toFixed(1)} KB
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Live Surface Probes
          </div>
          <div className="mt-1.5 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
            {liveSurfacesOk} / {snapshot.surfaces.length} Nominal
          </div>
          <div className="mt-1 text-xs text-amber-700 dark:text-amber-400 font-medium">
            {snapshot.surfaces.length - liveSurfacesOk} surfaces with read-only / contract gaps
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Open PR Reconciliation
          </div>
          <div className="mt-1.5 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
            {readyPrCount} Greenlane Ready
          </div>
          <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            {driftPrCount} drifted against moving main · {snapshot.reconciledPullRequests.length} tracked
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Verified Cloud Legion Runs
          </div>
          <div className="mt-1.5 text-xl font-semibold font-mono tabular-nums text-slate-900 dark:text-slate-50">
            {snapshot.executions.length} Executed
          </div>
          <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            {snapshot.flowInstructions.length} durable FLOW instructions active
          </div>
        </div>
      </div>

      {eyeMode === 'all-seeing' ? (
        <>
          {/* Live Production Surfaces & Repository SHA Drift */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <section
              aria-labelledby="surfaces-heading"
              className="xl:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-4">
                <div>
                  <h2 id="surfaces-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    01. Live Production Surface Verification (E1 Direct Probes)
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    HTTP 200 alone never counts as operational yield; payload contract and static-deck regressions are audited live.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full table-fixed text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">
                      <th className="w-[34%] py-3 px-5">Surface</th>
                      <th className="w-[22%] py-3 px-3 text-right">Status / Latency</th>
                      <th className="w-[44%] py-3 px-5">Payload Contract Audit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-sm">
                    {snapshot.surfaces.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-5 align-top break-words">
                          <div className="font-medium text-slate-900 dark:text-slate-100 flex items-start gap-1.5">
                            <span className="leading-snug">{s.name}</span>
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={`Open ${s.name}`}
                              className="text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 shrink-0 mt-0.5"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                            {s.extractedTitle}
                          </div>
                        </td>
                        <td className="py-3.5 px-3 text-right align-top font-mono text-xs tabular-nums">
                          <div className="inline-flex items-center justify-end gap-1 font-medium">
                            {s.verdict === 'VERIFIED_LIVE' && (
                              <>
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                                <span className="text-emerald-700 dark:text-emerald-400">Verified</span>
                              </>
                            )}
                            {s.verdict === 'DEGRADED_CONTRACT' && (
                              <>
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                                <span className="text-amber-700 dark:text-amber-400">Contract Gap</span>
                              </>
                            )}
                            {s.verdict === 'UNREACHABLE' && (
                              <>
                                <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0" />
                                <span className="text-red-700 dark:text-red-400">Unreachable</span>
                              </>
                            )}
                          </div>
                          <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                            HTTP {s.httpStatus ?? 'ERR'} · {s.latencyMs}ms
                          </div>
                        </td>
                        <td className="py-3.5 px-5 align-top text-xs text-slate-600 dark:text-slate-300 leading-relaxed break-words">
                          {s.contractNotes}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Repository Main SHA Drift & OCI Vault P1 Incident */}
            <div className="xl:col-span-5 space-y-6">
              <section
                aria-labelledby="repo-drift-heading"
                className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
              >
                <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                  <h2 id="repo-drift-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    02. Authoritative Branch Lineage & Drift
                  </h2>
                  <button
                    type="button"
                    onClick={() => onNavigateTab('greenlane')}
                    className="inline-flex items-center gap-1 text-xs font-medium text-cyan-700 dark:text-cyan-400 hover:underline whitespace-nowrap shrink-0"
                  >
                    PR Triage
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {snapshot.repos.map((r) => (
                    <div key={r.repo} className="p-4">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono">
                          {r.repo}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
                          {r.authority} · {r.visibility}
                          {r.driftDetected ? ' · Main Moved Live' : ''}
                        </span>
                      </div>
                      <div className="mt-1.5 text-xs font-mono tabular-nums text-slate-700 dark:text-slate-300">
                        {r.liveMainSha ? (
                          <>
                            Live HEAD: <span className="font-semibold">{r.liveMainSha.slice(0, 12)}</span>
                            {r.handoverMainSha && (
                              <span className="text-slate-500 dark:text-slate-400">
                                {' '}· Handover: {r.handoverMainSha.slice(0, 10)}
                              </span>
                            )}
                          </>
                        ) : (
                          <span>
                            Handover HEAD: <span className="font-semibold">{r.handoverMainSha?.slice(0, 12)}</span> · Live token unprovisioned (U)
                          </span>
                        )}
                      </div>
                      {r.liveMessage && (
                        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                          {r.liveMessage}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              {/* Active P1 Incident & Remote Unverified Missions */}
              <section
                aria-labelledby="incident-heading"
                className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 id="incident-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                      03. Active Cluster Incident (#{snapshot.vaultIncident2468.issueNumber})
                    </h2>
                    <p className="mt-1 text-xs text-red-700 dark:text-red-400 font-medium">
                      {snapshot.vaultIncident2468.authority} Confirmed Open · Missing OCI Vault Key: {snapshot.vaultIncident2468.missingKey}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onSelectMissionForLegion(
                        'INS-02468',
                        'Remediate OCI Vault agent-foundry-hf ExternalSecret (#2468)',
                        `Diagnose missing OCI Vault key "${snapshot.vaultIncident2468.missingKey}" referenced in ${snapshot.vaultIncident2468.manifestPath} without muting the monitor.`,
                        'chidionyema/idp'
                      )
                    }
                    className="px-3 py-1.5 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    Dispatch Adversarial Audit
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  Manifest <code className="font-mono text-slate-800 dark:text-slate-200">{snapshot.vaultIncident2468.manifestPath}</code> failed missing-key check at run 43059348616. Per policy, never mute the vault monitor; verify live cluster workload demand before retiring manifest or restoring secret.
                </p>
              </section>
            </div>
          </div>

          {/* Live Safeguard Decision Log (AGENTS.md §3: /fleet must show safeguards deciding PASS/REFUSE) + Handover Receipt Lanes */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <section
              aria-labelledby="safeguards-heading"
              className="xl:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800">
                <h2 id="safeguards-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  04. Live Safeguard & Router Decisions (AGENTS.md §3 Proof Stream)
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Every Claim-Gate refusal, Inbound Firewall check, argon-sync fence recovery, and Legion route logged with its decider.
                </p>
              </div>
              <div className="divide-y divide-slate-200 dark:divide-slate-800 max-h-80 overflow-y-auto">
                {snapshot.safeguardDecisions.map((ev) => (
                  <div key={ev.eventId} className="px-5 py-3.5 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 font-medium">
                        {ev.action === 'PASS' && (
                          <span className="text-emerald-700 dark:text-emerald-400 inline-flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            PASS
                          </span>
                        )}
                        {ev.action === 'REFUSE' && (
                          <span className="text-red-700 dark:text-red-400 inline-flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5" />
                            REFUSE
                          </span>
                        )}
                        {ev.action === 'RECOVER' && (
                          <span className="text-amber-700 dark:text-amber-400 inline-flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            RECOVER
                          </span>
                        )}
                        <span aria-hidden="true" className="text-slate-400">·</span>
                        <span className="font-mono text-slate-800 dark:text-slate-200">{ev.gateName}</span>
                        <span aria-hidden="true" className="text-slate-400">·</span>
                        <span className="text-slate-900 dark:text-slate-100">{ev.subject}</span>
                      </div>
                      <span className="font-mono tabular-nums text-slate-500 dark:text-slate-400">
                        {ev.authority} · {ev.timestamp.slice(11, 19)} UTC
                      </span>
                    </div>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">{ev.detail}</p>
                    <div className="mt-1 text-slate-400 dark:text-slate-500 font-mono">
                      Decider: {ev.decider}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section
              aria-labelledby="lanes-heading"
              className="xl:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800">
                <h2 id="lanes-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  05. Takeover Accountable Lanes & Explicit U Boundaries
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Persisted at <code className="font-mono">.genesis/outbox/takeover-receipt-20261111.json</code>
                </p>
              </div>
              <div className="divide-y divide-slate-200 dark:divide-slate-800">
                {snapshot.receipt.accountableLanes.map((lane) => (
                  <div key={lane.laneId} className="px-5 py-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {lane.laneId} · {lane.title}
                      </span>
                      <span className="font-mono text-emerald-700 dark:text-emerald-400 shrink-0">
                        {lane.priority} · {lane.status}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-slate-500 dark:text-slate-400 truncate">
                      {lane.proofPointer}
                    </div>
                  </div>
                ))}
                {snapshot.receipt.explicitBoundaries.map((b) => (
                  <div key={b.capability} className="px-5 py-3 text-xs bg-slate-50/60 dark:bg-slate-950/40">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-slate-800 dark:text-slate-200">{b.capability}</span>
                      <span className="font-mono text-amber-700 dark:text-amber-400 shrink-0">
                        Authority {b.authority}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">{b.remediation}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      ) : (
        /* One Eye View: Individual Worker Lease, Proof Chain & 7-Gate Evidence */
        <section
          aria-labelledby="one-eye-heading"
          className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6"
        >
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
            <div>
              <h2 id="one-eye-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                One Eye Scoped Worker Telemetry
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Inspect exact fenced worker epoch, 10-link proof chain, and 7-Gate Cognitive Architecture state.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label htmlFor="one-eye-worker-select" className="text-xs font-medium text-slate-600 dark:text-slate-400">
                Instruction Focus:
              </label>
              <select
                id="one-eye-worker-select"
                value={activeInst?.instructionId ?? ''}
                onChange={(e) => setSelectedWorkerInstId(e.target.value)}
                className="px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                {snapshot.flowInstructions.map((inst) => (
                  <option key={inst.instructionId} value={inst.instructionId}>
                    {inst.instructionId} · {inst.formation.toUpperCase()} · Epoch {inst.leaseEpoch}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {activeInst ? (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-5 space-y-4">
                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {activeInst.instructionId}: {activeInst.title}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {activeInst.body}
                </p>
                <dl className="divide-y divide-slate-200 dark:divide-slate-800 border-t border-b border-slate-200 dark:border-slate-800 text-xs">
                  <div className="py-2.5 flex justify-between gap-4">
                    <dt className="text-slate-500 dark:text-slate-400">Assigned Worker</dt>
                    <dd className="font-mono text-slate-900 dark:text-slate-100">{activeInst.assignedWorkerId ?? 'unassigned'}</dd>
                  </div>
                  <div className="py-2.5 flex justify-between gap-4">
                    <dt className="text-slate-500 dark:text-slate-400">argon-sync Lease Epoch</dt>
                    <dd className="font-mono tabular-nums text-slate-900 dark:text-slate-100">Epoch {activeInst.leaseEpoch} (Recoveries: {activeInst.recoveryCount})</dd>
                  </div>
                  <div className="py-2.5 flex justify-between gap-4">
                    <dt className="text-slate-500 dark:text-slate-400">FLOW Lifecycle Phase</dt>
                    <dd className="font-mono text-blue-600 dark:text-blue-400 font-medium">{activeInst.phase}</dd>
                  </div>
                  <div className="py-2.5 flex justify-between gap-4">
                    <dt className="text-slate-500 dark:text-slate-400">Greenlane Target</dt>
                    <dd className="font-mono text-slate-900 dark:text-slate-100">{activeInst.laneBranch ?? 'pending'}</dd>
                  </div>
                  <div className="py-2.5 flex justify-between gap-4">
                    <dt className="text-slate-500 dark:text-slate-400">Artifact Receipt Digest</dt>
                    <dd className="font-mono text-slate-900 dark:text-slate-100">{activeInst.receiptHash ? activeInst.receiptHash.slice(0, 16) : 'Unverified (run Legion)'}</dd>
                  </div>
                </dl>

                <button
                  type="button"
                  onClick={() =>
                    onSelectMissionForLegion(
                      activeInst.instructionId,
                      activeInst.title,
                      activeInst.body,
                      activeInst.repo
                    )
                  }
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
                >
                  <ShieldCheck className="w-4 h-4" />
                  Execute Cloud Formation on {activeInst.instructionId}
                </button>
              </div>

              <div className="lg:col-span-7">
                {linkedExec ? (
                  <div className="space-y-4">
                    <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                      7-Gate Cognitive Architecture Receipt ({linkedExec.executionId} · {linkedExec.modelId})
                    </div>
                    <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
                      {Object.entries(linkedExec.sevenGates).map(([gate, val]) => (
                        <div key={gate} className="p-3 text-xs">
                          <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{gate}: </span>
                          <span className="text-slate-600 dark:text-slate-400">{val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-start justify-center p-6 border border-dashed border-slate-300 dark:border-slate-700 rounded-xl">
                    <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      No Cloud Formation Artifact Recorded Yet for {activeInst.instructionId}
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-md">
                      Per Epistemic Rule §0, this worker displays zero synthetic output until an actual cloud Legion formation and Geburah falsifier run completes.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
};
