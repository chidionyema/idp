import { useState } from 'react';
import {
  ArrowUpRight,
  CheckCircle2,
  Download,
  Pause,
  Play,
  RotateCcw,
  Search,
  ShieldAlert,
  UploadCloud,
  Zap,
} from 'lucide-react';
import {
  AgentsMdRatchetResult,
  EstateGrandUnionSnapshot,
  GatewayStateSnapshot,
  InstallerShortcutAuditResult,
  NavTabId,
  ProductionGuaranteesReport,
} from '../types/api';

interface EstateGrandUnionProps {
  union: EstateGrandUnionSnapshot;
  guarantees: ProductionGuaranteesReport | null;
  sseConnected: boolean;
  onUnionUpdated: (union: EstateGrandUnionSnapshot, state?: GatewayStateSnapshot) => void;
  onNavigateTab: (tab: NavTabId) => void;
}

type AuditViewTab = 'pins' | 'adversarial' | 'gates';
type ActorFilter = 'ALL' | 'OTTO' | 'FLOW' | 'CREW' | 'INTERCLOUD' | 'BATTALION' | 'KARMA' | 'BEAST';
type GwtStatusFilter =
  | 'ALL'
  | 'LIVE_AUTONOMOUS'
  | 'VERIFIED_CANDIDATE'
  | 'SANDBOX_VERIFIED'
  | 'WIP_GWT_BRANCH'
  | 'BLOCKED_DISPATCH';

export function EstateGrandUnion({
  union,
  guarantees,
  sseConnected,
  onUnionUpdated,
  onNavigateTab,
}: EstateGrandUnionProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // First-Use Governance Audit interactive state
  const [auditTab, setAuditTab] = useState<AuditViewTab>('pins');
  const [ratchetCurrentInput, setRatchetCurrentInput] = useState<string>('348');
  const [ratchetBaselineInput, setRatchetBaselineInput] = useState<string>('348');
  const [installerInput, setInstallerInput] = useState<string>(
    'bin/idp-machine-submit --lane greenlane --verify-provenance'
  );
  const [liveRatchetResult, setLiveRatchetResult] = useState<AgentsMdRatchetResult>(
    union.firstUseAudit.defaultRatchetEvaluation
  );
  const [liveShortcutResult, setLiveShortcutResult] = useState<InstallerShortcutAuditResult>({
    allowed: true,
    blockedShortcuts: [],
    reason: 'Preserves authoritative bin/idp-machine-submit claim, hooks, and multi-agent provenance',
  });

  // Collaboration feed & GWT filters
  const [actorFilter, setActorFilter] = useState<ActorFilter>('ALL');
  const [gwtSearch, setGwtSearch] = useState<string>('');
  const [gwtStatusFilter, setGwtStatusFilter] = useState<GwtStatusFilter>('ALL');

  async function handlePulseBeat() {
    setBusyAction('beat');
    try {
      const res = await fetch('/api/union/beat', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as {
          union: EstateGrandUnionSnapshot;
          state: GatewayStateSnapshot;
        };
        onUnionUpdated(data.union, data.state);
        setActionNotice(
          `Executed Chronos beat #${data.union.chronos.beatNumber} across WAL #${data.union.battalionRollup.walReceipts}.`
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleToggleAutonomous() {
    setBusyAction('auto');
    const nextEnabled = !union.chronos.autonomousEnabled;
    try {
      const res = await fetch('/api/union/autonomous', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextEnabled }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          union: EstateGrandUnionSnapshot;
          state: GatewayStateSnapshot;
        };
        onUnionUpdated(data.union, data.state);
        setActionNotice(
          nextEnabled
            ? `Chronos autonomous heartbeat resumed (${(data.union.chronos.cadenceMs / 1000).toFixed(0)}s SSE push).`
            : 'Chronos autonomous heartbeat paused; manual beat control active.'
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePreemptSpot(laneId?: string) {
    setBusyAction(laneId ? `preempt-${laneId}` : 'preempt');
    try {
      const res = await fetch('/api/union/intercloud/preempt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ laneId }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          reclaimedLaneId: string;
          backupLaneId: string;
          failoverMs: number;
          union: EstateGrandUnionSnapshot;
          state: GatewayStateSnapshot;
        };
        onUnionUpdated(data.union, data.state);
        setActionNotice(
          `Spot reclamation on ${data.reclaimedLaneId} migrated in ${data.failoverMs}ms to ${data.backupLaneId} (0 dropped tasks).`
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleHealSpot() {
    setBusyAction('heal');
    try {
      const res = await fetch('/api/union/intercloud/heal', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as {
          union: EstateGrandUnionSnapshot;
          state: GatewayStateSnapshot;
        };
        onUnionUpdated(data.union, data.state);
        setActionNotice('All reclaimed InterCloud spot pools restored to ONLINE capacity.');
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePushBundleToFleet() {
    setBusyAction('push-bundle');
    try {
      const res = await fetch('/api/export/push-bundle', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as {
          pushed: boolean;
          bundleSha256: string | null;
          bundleBytes: number;
          headSha: string;
          wakeDisposition: string;
          reason: string;
        };
        const shortSha = data.bundleSha256 ? data.bundleSha256.slice(0, 16) : 'pending';
        setActionNotice(
          `Git bundle verified (${data.bundleBytes.toLocaleString()} bytes, SHA-256 ${shortSha}…, HEAD ${data.headSha.slice(0, 8)}) — ${data.wakeDisposition}: ${data.reason}`
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function handleEvaluateEnsemble(episodes: number) {
    setBusyAction(`ens-${episodes}`);
    try {
      const res = await fetch('/api/union/ensemble-proof', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ episodes }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          union: EstateGrandUnionSnapshot;
        };
        onUnionUpdated(data.union);
        setActionNotice(
          `Evaluated ${episodes} episodes: Open Ensemble ${data.union.ensembleProof.ensembleVerifiedPassPct}% vs Frontier ${data.union.ensembleProof.singleFrontierPassPct}% (-${data.union.ensembleProof.costReductionPct}% cost).`
        );
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function runAuditRatchetProbe(override?: {
    currentLinesRaw?: string;
    baselineLinesRaw?: string;
    installerScript?: string;
  }) {
    const currentLinesRaw = override?.currentLinesRaw ?? ratchetCurrentInput;
    const baselineLinesRaw = override?.baselineLinesRaw ?? ratchetBaselineInput;
    const installerScript = override?.installerScript ?? installerInput;

    if (override?.currentLinesRaw !== undefined) setRatchetCurrentInput(override.currentLinesRaw);
    if (override?.baselineLinesRaw !== undefined) setRatchetBaselineInput(override.baselineLinesRaw);
    if (override?.installerScript !== undefined) setInstallerInput(override.installerScript);

    setBusyAction('ratchet');
    try {
      const res = await fetch('/api/union/audit/ratchet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentLinesRaw, baselineLinesRaw, installerScript }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          ratchet: AgentsMdRatchetResult;
          shortcutAudit: InstallerShortcutAuditResult;
        };
        setLiveRatchetResult(data.ratchet);
        setLiveShortcutResult(data.shortcutAudit);
      }
    } finally {
      setBusyAction(null);
    }
  }

  const filteredFeed = union.collaborationFeed.filter((item) =>
    actorFilter === 'ALL' ? true : item.actor === actorFilter
  );

  const filteredGwt = union.gwtAeonRegistry.filter((item) => {
    const matchesStatus = gwtStatusFilter === 'ALL' ? true : item.status === gwtStatusFilter;
    const q = gwtSearch.trim().toLowerCase();
    if (!q) return matchesStatus;
    return (
      matchesStatus &&
      (item.worktree.toLowerCase().includes(q) ||
        item.subsystem.toLowerCase().includes(q) ||
        item.horizonOwner.toLowerCase().includes(q) ||
        item.honestNote.toLowerCase().includes(q))
    );
  });

  const audit = union.firstUseAudit;
  const ens = union.ensembleProof;

  return (
    <div className="space-y-8">
      {/* Section 0: Executive Command Header & 4-Column KPI Strip */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Estate Grand Union</span>
              <span aria-hidden="true">·</span>
              <span>SSE Stream: {sseConnected ? 'Connected (/api/union/stream)' : 'Syncing'}</span>
              <span aria-hidden="true">·</span>
              <span>Zero Client Polling (I-8090)</span>
              {guarantees && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono tabular-nums text-emerald-700 font-medium">
                    {guarantees.verifiedCount}/{guarantees.totalCount} Guarantees Verified
                  </span>
                </>
              )}
            </div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-slate-900">
              Autonomous Chronos, InterCloud Compute &amp; Producer-First Governance
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Joins Chronos &amp; Tempo scheduling, OTTO · FLOW · CREW · KARMA telemetry, sovereign $0.00 + InterCloud spot compute, Founder/Public surfaces, parallel GWT/AEON lanes, and the 16 Nov 2026 First-Use Machine-Agent Governance Audit into one real-time surface.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleToggleAutonomous}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              {union.chronos.autonomousEnabled ? (
                <>
                  <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                  Pause Auto-Beat
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" aria-hidden="true" />
                  Resume Auto-Beat
                </>
              )}
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => handlePreemptSpot()}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
              Preempt Spot Cloud
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleHealSpot}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              Heal Spot Pools
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handlePulseBeat}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5" aria-hidden="true" />
              {busyAction === 'beat' ? 'Pulsing Beat...' : 'Pulse Chronos Beat'}
            </button>
          </div>
        </div>

        {/* Fleet Sync & Team Handoff Strip */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="text-slate-500 font-mono">
            Reset-Proof Git Bundle &amp; Team Sync · Targets: chidionyema/argon-sync &amp; gemini-sync
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handlePushBundleToFleet}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <UploadCloud className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
              {busyAction === 'push-bundle' ? 'Pushing Bundle...' : 'Push Bundle to Fleet'}
            </button>
            <a
              href="/api/export/bundle"
              download="meridian-hermes-today.bundle"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Git Bundle
            </a>
            <a
              href="/api/export/team-handoff"
              download="meridian-estate-team-handoff.md"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Team Handoff MD
            </a>
          </div>
        </div>

        {actionNotice && (
          <div
            role="status"
            className="mt-3 pt-3 border-t border-slate-200 text-xs text-slate-700 font-mono"
          >
            {actionNotice}
          </div>
        )}

        {/* 4-Column KPI Strip */}
        <div className="mt-6 pt-5 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
          <div>
            <div className="text-xs text-slate-500">Chronos &amp; Tempo Heartbeat</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              Beat #{union.chronos.beatNumber}
            </div>
            <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums">
              {union.chronos.autonomousEnabled ? 'Auto Active' : 'Manual Mode'} · Cadence{' '}
              {(union.chronos.cadenceMs / 1000).toFixed(0)}s · Skew {union.chronos.tempoSyncSkewMs}ms
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">Battalion WAL &amp; Verified Savings</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-emerald-700">
              ${union.battalionRollup.netSavingsUsd.toFixed(2)} saved
            </div>
            <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums">
              {union.battalionRollup.walReceipts.toLocaleString()} WAL ·{' '}
              {union.battalionRollup.savingsPct.toFixed(1)}% vs baseline ·{' '}
              {union.battalionRollup.blindGapsVisible} BLIND kept honest
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">InterCloud &amp; Sovereign Capacity</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              {union.interCloudSummary.effectiveCapacityTokPerSec.toLocaleString()} tok/s
            </div>
            <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums">
              {union.interCloudSummary.freeSovereignLanes} Free ($0) ·{' '}
              {union.interCloudSummary.spotArbitrageLanes} Spot · Avg $
              {union.interCloudSummary.weightedAvgPricePer1MUsd.toFixed(3)}/1M
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500">Open Ensemble &amp; First-Use Audit</div>
            <div className="mt-1 text-2xl font-mono tabular-nums font-semibold text-slate-900">
              {ens.ensembleVerifiedPassPct}% vs {ens.singleFrontierPassPct}%
            </div>
            <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums">
              Audit {audit.adversarialTestsPassed}/{audit.adversarialTestsTotal} pass · Live Effect:{' '}
              {audit.liveCeremonyEffect}
            </div>
          </div>
        </div>
      </section>

      {/* Section 1: 16 Nov 2026 First-Use Machine-Agent Governance Audit */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div className="max-w-2xl">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono">
                <span>{audit.auditBranch}</span>
                <span aria-hidden="true">·</span>
                <span>Candidate {audit.candidateHead.slice(0, 12)}</span>
                <span aria-hidden="true">·</span>
                <span>+{audit.commitsAheadOfMain} ahead of IDP main ({audit.comparedMainSha})</span>
              </div>
              <h3 className="mt-1 text-base font-semibold text-slate-900">
                01. First-Use Machine-Agent Governance Deep Audit &amp; AGENTS.md No-Growth Ratchet
              </h3>
              <p className="mt-1 text-xs text-slate-600">{audit.governingPrinciple}</p>
            </div>

            <div
              role="group"
              aria-label="First-Use Audit view selector"
              className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0"
            >
              {(
                [
                  { id: 'pins', label: `13-Pin Matrix (${audit.failureClassesReviewed})` },
                  {
                    id: 'adversarial',
                    label: `Adversarial Tests (${audit.adversarialTestsPassed}/${audit.adversarialTestsTotal})`,
                  },
                  { id: 'gates', label: 'Ratchet Verifier & P0 Watch' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setAuditTab(tab.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    auditTab === tab.id
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Audit Outcome Summary Bar */}
          <div className="mt-5 pt-4 border-t border-slate-200 grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-slate-500">Failure Classes Reviewed</span>
              <div className="mt-0.5 text-base font-mono tabular-nums font-semibold text-slate-900">
                {audit.failureClassesReviewed} Pins
              </div>
            </div>
            <div>
              <span className="text-slate-500">Local Adversarial Suite</span>
              <div className="mt-0.5 text-base font-mono tabular-nums font-semibold text-emerald-700">
                {audit.adversarialTestsPassed}/{audit.adversarialTestsTotal} ({audit.observerTestsPassed} Observer + {audit.ratchetTestsPassed} Ratchet)
              </div>
            </div>
            <div>
              <span className="text-slate-500">Live Ceremony Operational Effect</span>
              <div className="mt-0.5 text-base font-mono tabular-nums font-semibold text-amber-700">
                {audit.liveCeremonyEffect} (Never Faked)
              </div>
            </div>
            <div>
              <span className="text-slate-500">Candidate Enforcement Posture</span>
              <div className="mt-0.5 text-xs font-mono font-semibold text-slate-800">
                VERIFIED CANDIDATE · UNMERGED
              </div>
            </div>
          </div>
        </div>

        {auditTab === 'pins' && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Pin</th>
                  <th className="py-2.5 px-4 font-medium">Control Domain</th>
                  <th className="py-2.5 px-4 font-medium">Current Repository Finding</th>
                  <th className="py-2.5 px-4 font-medium">Producer-First Safeguard</th>
                  <th className="py-2.5 px-4 font-medium">Evidence Tier</th>
                  <th className="py-2.5 px-4 font-medium text-right">Disposition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {audit.pins.map((pin) => (
                  <tr key={pin.pin} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                      #{pin.pin}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-slate-900 whitespace-nowrap">
                      {pin.title}
                    </td>
                    <td className="py-2.5 px-4 text-slate-600">{pin.currentFinding}</td>
                    <td className="py-2.5 px-4 text-slate-600">{pin.producerControl}</td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                      {pin.evidenceTier}
                    </td>
                    <td
                      className={`py-2.5 px-4 text-right font-mono font-semibold whitespace-nowrap ${
                        pin.disposition === 'Do not revive'
                          ? 'text-red-700'
                          : pin.disposition === 'Retain' || pin.disposition === 'Preserve'
                            ? 'text-emerald-700'
                            : 'text-slate-900'
                      }`}
                    >
                      {pin.disposition}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {auditTab === 'adversarial' && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">ID</th>
                  <th className="py-2.5 px-4 font-medium">Suite</th>
                  <th className="py-2.5 px-4 font-medium">Adversarial Invariant</th>
                  <th className="py-2.5 px-4 font-medium">Measured Evidence</th>
                  <th className="py-2.5 px-4 font-medium text-right">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {audit.adversarialChecks.map((chk) => (
                  <tr key={chk.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                      {chk.id}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {chk.suite}
                    </td>
                    <td className="py-2.5 px-4 text-slate-800">{chk.title}</td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600">
                      {chk.detail}
                    </td>
                    <td className="py-2.5 px-4 text-right font-semibold text-emerald-700 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        {chk.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {auditTab === 'gates' && (
          <div className="p-6 space-y-6">
            {/* Interactive AGENTS.md No-Growth Ratchet & Shortcut Blocker */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-3">
                <div className="text-sm font-semibold text-slate-900">
                  Interactive AGENTS.md No-Growth Ratchet &amp; Shortcut Probe
                </div>
                <p className="text-xs text-slate-600">
                  Legacy <code className="font-mono">{audit.legacyEscapedLinesBugReproduced.legacyShellSnippet}</code> failed open (exit 0) on literal <code className="font-mono">$lines</code>. Test the repaired ratchet and installer provenance guard below:
                </p>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      runAuditRatchetProbe({
                        currentLinesRaw: '348',
                        baselineLinesRaw: '348',
                        installerScript: 'bin/idp-machine-submit --lane greenlane --verify-provenance',
                      })
                    }
                    className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                  >
                    348/348 Hold (Pass)
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      runAuditRatchetProbe({
                        currentLinesRaw: '349',
                        baselineLinesRaw: '348',
                      })
                    }
                    className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                  >
                    349/348 Growth (Block)
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      runAuditRatchetProbe({
                        currentLinesRaw: '$lines',
                        baselineLinesRaw: '348',
                      })
                    }
                    className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                  >
                    Literal $lines Escape (Fail-Closed)
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      runAuditRatchetProbe({
                        currentLinesRaw: '332',
                        baselineLinesRaw: '348',
                        installerScript: 'git commit --no-verify && rewrite_multi_agent_history',
                      })
                    }
                    className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
                  >
                    Test --no-verify Shortcut (Reject)
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <label className="block text-xs text-slate-600">
                    Current AGENTS.md Lines
                    <input
                      type="text"
                      value={ratchetCurrentInput}
                      onChange={(e) => setRatchetCurrentInput(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900 focus:border-slate-900 focus:outline-none"
                    />
                  </label>
                  <label className="block text-xs text-slate-600">
                    Baseline Ceiling Lines
                    <input
                      type="text"
                      value={ratchetBaselineInput}
                      onChange={(e) => setRatchetBaselineInput(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900 focus:border-slate-900 focus:outline-none"
                    />
                  </label>
                </div>

                <label className="block text-xs text-slate-600">
                  Submission / Installer Command Under Audit
                  <div className="mt-1 flex gap-2">
                    <input
                      type="text"
                      value={installerInput}
                      onChange={(e) => setInstallerInput(e.target.value)}
                      className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900 focus:border-slate-900 focus:outline-none"
                    />
                    <button
                      type="button"
                      disabled={busyAction === 'ratchet'}
                      onClick={() => runAuditRatchetProbe()}
                      className="rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 whitespace-nowrap shrink-0"
                    >
                      Evaluate Gate
                    </button>
                  </div>
                </label>

                <div className="pt-2 space-y-1.5 text-xs font-mono">
                  <div
                    className={
                      liveRatchetResult.passed ? 'text-emerald-700' : 'text-red-700'
                    }
                  >
                    Ratchet (exit {liveRatchetResult.exitCode}): {liveRatchetResult.summary}
                  </div>
                  <div
                    className={
                      liveShortcutResult.allowed ? 'text-emerald-700' : 'text-red-700'
                    }
                  >
                    Provenance Guard: {liveShortcutResult.reason}
                  </div>
                </div>
              </div>

              {/* Remaining Acceptance Gates & Hourly P0 Watch */}
              <div className="space-y-4 border-t lg:border-t-0 lg:border-l border-slate-200 pt-4 lg:pt-0 lg:pl-6">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    Remaining Acceptance Before Estate-Wide Certification
                  </div>
                  <ul className="mt-2 space-y-1.5 text-xs text-slate-600 list-disc pl-4">
                    {audit.remainingAcceptanceGates.map((gate, i) => (
                      <li key={i}>{gate}</li>
                    ))}
                  </ul>
                </div>

                <div className="pt-3 border-t border-slate-200">
                  <div className="text-sm font-semibold text-slate-900">
                    Hourly P0 Watch &amp; Redacted Ceremony Observer Sample
                  </div>
                  <ul className="mt-2 space-y-1 text-xs text-slate-600 font-mono">
                    {audit.hourlyP0WatchTargets.map((item, i) => (
                      <li key={i}>· {item}</li>
                    ))}
                  </ul>
                  <div className="mt-3 text-[11px] font-mono text-slate-500 space-y-0.5">
                    {audit.defaultObserverReport.redactedPreview.slice(0, 3).map((line, i) => (
                      <div key={i} className="truncate">
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Section 2: Legion Open Ensemble > Frontier & InterCloud Compute Fabric */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div className="max-w-2xl">
              <h3 className="text-base font-semibold text-slate-900">
                02. Legion Open/Small Ensemble Exceeding Frontier &amp; InterCloud Compute Fabric
              </h3>
              <p className="mt-1 text-xs text-slate-600">
                {ens.ensembleArchitecture} — achieves{' '}
                <strong className="font-mono tabular-nums text-slate-900">
                  {ens.ensembleVerifiedPassPct}%
                </strong>{' '}
                verified pass rate vs{' '}
                <strong className="font-mono tabular-nums text-slate-900">
                  {ens.singleFrontierPassPct}%
                </strong>{' '}
                single Frontier (+{ens.qualityAdvantagePts} pts) at{' '}
                <strong className="font-mono tabular-nums text-emerald-700">
                  {ens.costReductionPct}% lower cost
                </strong>{' '}
                (${ens.ensembleCostPerOutcomeUsd.toFixed(5)} vs $
                {ens.singleFrontierCostPerOutcomeUsd.toFixed(5)} per verified outcome).
              </p>
            </div>

            <div
              role="group"
              aria-label="Run Ensemble vs Frontier benchmark episodes"
              className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0"
            >
              {[250, 500, 1500].map((ep) => (
                <button
                  key={ep}
                  type="button"
                  onClick={() => handleEvaluateEnsemble(ep)}
                  className={`px-3 py-1.5 text-xs font-mono tabular-nums font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    ens.episodes === ep
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {ep} Episodes
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                <th className="py-2.5 px-4 font-medium">Compute Pool &amp; Open Model</th>
                <th className="py-2.5 px-4 font-medium">Cost Class</th>
                <th className="py-2.5 px-4 font-medium text-right">Price / 1M</th>
                <th className="py-2.5 px-4 font-medium text-right">Throughput</th>
                <th className="py-2.5 px-4 font-medium text-right">p50 / Failover</th>
                <th className="py-2.5 px-4 font-medium text-right">Routed</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
                <th className="py-2.5 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {union.interCloudLanes.map((lane) => (
                <tr key={lane.id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-4">
                    <div className="font-medium text-slate-900">{lane.name}</div>
                    <div className="text-[11px] text-slate-500">
                      {lane.openWeightsModel} · {lane.regionOrTopology} · {lane.retentionPolicy}
                    </div>
                  </td>
                  <td className="py-2.5 px-4 font-mono text-[11px] text-slate-700 whitespace-nowrap">
                    {lane.costClass}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                    ${lane.pricePer1MTokensUsd.toFixed(3)}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700 whitespace-nowrap">
                    {lane.throughputTokPerSec.toLocaleString()} tok/s
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-600 whitespace-nowrap">
                    {lane.p50LatencyMs}ms / {lane.checkpointFailoverMs}ms
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-900 whitespace-nowrap">
                    {lane.tasksRouted.toLocaleString()}
                  </td>
                  <td
                    className={`py-2.5 px-4 font-mono text-[11px] font-semibold whitespace-nowrap ${
                      lane.status === 'ONLINE'
                        ? 'text-emerald-700'
                        : lane.status === 'SPOT_RECLAIMED_FAILOVER'
                          ? 'text-amber-700'
                          : 'text-slate-500'
                    }`}
                  >
                    {lane.status}
                  </td>
                  <td className="py-2.5 px-4 text-right whitespace-nowrap">
                    {lane.status === 'SPOT_RECLAIMED_FAILOVER' ? (
                      <button
                        type="button"
                        onClick={handleHealSpot}
                        className="text-xs font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap"
                      >
                        Heal Pool
                      </button>
                    ) : lane.costClass === 'INTERCLOUD_SPOT' ? (
                      <button
                        type="button"
                        onClick={() => handlePreemptSpot(lane.id)}
                        className="text-xs font-medium text-slate-600 hover:text-slate-900 whitespace-nowrap"
                      >
                        Simulate Reclaim
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-400 font-mono">Sovereign</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 3: OTTO · FLOW · CREW · KARMA Real-Time Collaboration Bus */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              03. OTTO · FLOW · CREW · KARMA Real-Time Collaboration Bus
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Every Chronos beat routes real packets through Legion admission, PennyD WAL receipts, and producer-first verification.
            </p>
          </div>

          <div
            role="group"
            aria-label="Filter collaboration bus by actor"
            className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg"
          >
            {(['ALL', 'OTTO', 'FLOW', 'CREW', 'INTERCLOUD', 'BATTALION', 'KARMA', 'BEAST'] as const).map(
              (actor) => (
                <button
                  key={actor}
                  type="button"
                  onClick={() => setActorFilter(actor)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    actorFilter === actor
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {actor}
                </button>
              )
            )}
          </div>
        </div>

        {filteredFeed.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-sm font-medium text-slate-900">
              No beats recorded yet for actor {actorFilter}
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Pulse a Chronos beat or reset the actor filter to inspect live bus events.
            </p>
            <div className="mt-3 flex justify-center gap-2">
              <button
                type="button"
                onClick={() => setActorFilter('ALL')}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Show All Actors
              </button>
              <button
                type="button"
                onClick={handlePulseBeat}
                className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
              >
                Pulse Beat Now
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Beat</th>
                  <th className="py-2.5 px-4 font-medium">Actor · Channel</th>
                  <th className="py-2.5 px-4 font-medium">Execution &amp; Worktree</th>
                  <th className="py-2.5 px-4 font-medium">Model</th>
                  <th className="py-2.5 px-4 font-medium text-right">Actual / Saved</th>
                  <th className="py-2.5 px-4 font-medium text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredFeed.slice(0, 12).map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                      #{evt.beatNumber}
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      <span className="font-semibold text-slate-900">{evt.actor}</span>
                      <span className="text-slate-400"> · </span>
                      <span className="text-slate-500 font-mono">{evt.channel}</span>
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="text-slate-800">{evt.summary}</div>
                      <div className="text-[11px] font-mono text-slate-500">
                        {evt.missionId} · {evt.worktreeRef}
                      </div>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                      {evt.modelUsed}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums whitespace-nowrap">
                      <span className="text-slate-900">${evt.costUsd.toFixed(5)}</span>
                      <span className="text-slate-400"> / </span>
                      <span className="text-emerald-700">+${evt.savedUsd.toFixed(4)}</span>
                    </td>
                    <td
                      className={`py-2.5 px-4 text-right font-mono text-[11px] font-semibold whitespace-nowrap ${
                        evt.verdict === 'VERIFIED'
                          ? 'text-emerald-700'
                          : evt.verdict === 'FAILOVER_HEALED'
                            ? 'text-blue-700'
                            : 'text-amber-700'
                      }`}
                    >
                      {evt.verdict}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Section 4: Joined-Up GWT / AEON WIP Matrix & Founder / Public Surfaces */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              04. Joined-Up GWT / AEON Parallel Worktrees &amp; Estate Surfaces
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Zero hidden WIP: every Git worktree, AEON horizon, Founder console, and Public product surface with truthful runtime provenance.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="relative block">
              <span className="sr-only">Search worktrees and subsystems</span>
              <Search
                className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400"
                aria-hidden="true"
              />
              <input
                type="search"
                value={gwtSearch}
                onChange={(e) => setGwtSearch(e.target.value)}
                placeholder="Search GWT, AEON, or audit..."
                className="w-52 rounded-md border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none"
              />
            </label>

            <div
              role="group"
              aria-label="Filter GWT status"
              className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg"
            >
              {(
                [
                  { id: 'ALL', label: `All (${union.gwtAeonRegistry.length})` },
                  { id: 'LIVE_AUTONOMOUS', label: 'LIVE' },
                  { id: 'VERIFIED_CANDIDATE', label: 'CANDIDATE' },
                  { id: 'BLOCKED_DISPATCH', label: 'GATED' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setGwtStatusFilter(tab.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    gwtStatusFilter === tab.id
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredGwt.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-sm font-medium text-slate-900">No matching GWT / AEON lanes</div>
            <button
              type="button"
              onClick={() => {
                setGwtSearch('');
                setGwtStatusFilter('ALL');
              }}
              className="mt-3 rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              Reset GWT Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[840px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Worktree / Branch</th>
                  <th className="py-2.5 px-4 font-medium">Subsystem &amp; Epistemic Note</th>
                  <th className="py-2.5 px-4 font-medium">Owner</th>
                  <th className="py-2.5 px-4 font-medium">Live Telemetry &amp; Tempo</th>
                  <th className="py-2.5 px-4 font-medium">Posture</th>
                  <th className="py-2.5 px-4 font-medium text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredGwt.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono text-[11px] font-semibold text-slate-900 whitespace-nowrap">
                      {item.worktree}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-slate-900">{item.subsystem}</div>
                      <div className="text-[11px] text-slate-500">{item.honestNote}</div>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-700 whitespace-nowrap">
                      {item.horizonOwner}
                    </td>
                    <td className="py-2.5 px-4 font-mono tabular-nums text-[11px] text-slate-700">
                      <div>{item.realtimeMetric}</div>
                      <div className="text-slate-500">{item.tempoCadence}</div>
                    </td>
                    <td
                      className={`py-2.5 px-4 font-mono text-[11px] font-semibold whitespace-nowrap ${
                        item.status === 'LIVE_AUTONOMOUS'
                          ? 'text-emerald-700'
                          : item.status === 'BLOCKED_DISPATCH'
                            ? 'text-red-700'
                            : 'text-amber-700'
                      }`}
                    >
                      {item.status}
                    </td>
                    <td className="py-2.5 px-4 text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => onNavigateTab(item.linkedTab)}
                        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap"
                      >
                        Open Surface
                        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Founder, Public & Investor Surfaces Matrix */}
        <div className="border-t border-slate-200">
          <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-700">
            Founder, Public &amp; Investor Surface Readiness Matrix
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[840px] text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 px-4 font-medium">Surface</th>
                  <th className="py-2 px-4 font-medium">Audience</th>
                  <th className="py-2 px-4 font-medium">Security &amp; Metering Binding</th>
                  <th className="py-2 px-4 font-medium text-right">p95</th>
                  <th className="py-2 px-4 font-medium">Runtime Posture</th>
                  <th className="py-2 px-4 font-medium text-right">Route</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {union.surfaces.map((surf) => (
                  <tr key={surf.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-slate-900">{surf.name}</div>
                      <div className="text-[11px] font-mono text-slate-500">
                        {surf.canonicalEndpoint}
                      </div>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                      {surf.audience}
                    </td>
                    <td className="py-2.5 px-4 text-[11px] text-slate-600">
                      <div>{surf.authPosture}</div>
                      <div className="font-mono text-slate-500">{surf.meteringBinding}</div>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700 whitespace-nowrap">
                      {surf.p95Ms}ms
                    </td>
                    <td
                      className={`py-2.5 px-4 font-mono text-[11px] font-semibold whitespace-nowrap ${
                        surf.runtimeStatus === 'LIVE_IN_CONTAINER'
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {surf.runtimeStatus}
                    </td>
                    <td className="py-2.5 px-4 text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => onNavigateTab(surf.localRouteOrTab)}
                        className="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-900 whitespace-nowrap"
                      >
                        Inspect
                        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
