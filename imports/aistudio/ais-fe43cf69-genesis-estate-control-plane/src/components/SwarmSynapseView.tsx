import React, { useState, useEffect } from 'react';
import {
  Download,
  RefreshCw,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Dna,
  GitCommit,
  Laptop,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import type { SwarmSynapseState, SwarmHydrateOutcome } from '../engine/swarmSynapse';

interface SwarmSynapseViewProps {
  initialSynapse: SwarmSynapseState;
  onRefreshState: () => Promise<void>;
}

export const SwarmSynapseView: React.FC<SwarmSynapseViewProps> = ({
  initialSynapse,
  onRefreshState,
}) => {
  const [synapse, setSynapse] = useState<SwarmSynapseState>(initialSynapse);
  const [selectedNewOwner, setSelectedNewOwner] = useState<string>(
    initialSynapse.offlineContinuity.availableCloudWorkers[0]?.workerId ?? 'gemini-4-centurion-01'
  );
  const [continuityBusy, setContinuityBusy] = useState(false);
  const [continuityBanner, setContinuityBanner] = useState<{
    tone: 'emerald' | 'amber' | 'rose';
    text: string;
  } | null>(null);

  // Interactive Stigmergic Hydrate / Dual-Yield Lab State
  const [agentIdInput, setAgentIdInput] = useState('codex-session-04');
  const [layerInput, setLayerInput] = useState('idp/platform/estate/estate-proof');
  const [failureSigInput, setFailureSigInput] = useState('');
  const [activeFencingToken, setActiveFencingToken] = useState<number>(
    initialSynapse.authoritativeToken
  );
  const [commitShaInput, setCommitShaInput] = useState('d4b1349cec6c8a049f12b7183c948102a74590ef');
  const [learnedFactInput, setLearnedFactInput] = useState(
    'Moved estate-proof, gate, and swarm-synapse into idp/platform/estate/ so host verification survives a dead laptop.'
  );
  const [antibodySigInput, setAntibodySigInput] = useState('HOST_TOOLING_LOCAL_ONLY_DRIFT');
  const [antibodyCmdInput, setAntibodyCmdInput] = useState(
    'python3 idp/platform/estate/estate-swarm-synapse.py hydrate --agent host --layer proof'
  );
  const [synapseBusy, setSynapseBusy] = useState(false);
  const [synapseOutcomeBanner, setSynapseOutcomeBanner] = useState<{
    tone: 'emerald' | 'amber' | 'rose';
    text: string;
  } | null>(null);
  const [showSporeInspector, setShowSporeInspector] = useState(false);

  useEffect(() => {
    setSynapse(initialSynapse);
  }, [initialSynapse]);

  // Subscribe to real-time SSE `synapse-delta` (<15ms broadcast across Genesis & Otto views)
  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    const onDelta = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as { swarmSynapse?: SwarmSynapseState };
        if (parsed.swarmSynapse) {
          setSynapse(parsed.swarmSynapse);
        }
      } catch {
        // Ignore malformed frame
      }
    };
    es.addEventListener('synapse-delta', onDelta);
    return () => {
      es.removeEventListener('synapse-delta', onDelta);
      es.close();
    };
  }, []);

  const runContinuityStep = async (
    action:
      | 'FAIL_TAKEOVER'
      | 'INITIATE_REASSIGN'
      | 'TEST_STALE_WORKER_WRITE'
      | 'ACK_NEW_WORKER'
      | 'COMPLETE_VERIFIED_YIELD'
      | 'RESET_PROOF'
  ) => {
    setContinuityBusy(true);
    setContinuityBanner(null);
    try {
      const res = await fetch('/api/continuity/reassign-flow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, newOwnerId: selectedNewOwner }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setContinuityBanner({
          tone: 'rose',
          text: data.error || 'Continuity transition refused by lease authority.',
        });
        return;
      }
      if (data.swarmSynapse) {
        setSynapse(data.swarmSynapse as SwarmSynapseState);
      }
      setContinuityBanner({
        tone: data.rejectedHttpStatus === 409 ? 'amber' : 'emerald',
        text: data.message,
      });
      await onRefreshState();
    } catch (err) {
      setContinuityBanner({
        tone: 'rose',
        text: err instanceof Error ? err.message : 'Continuity request failed',
      });
    } finally {
      setContinuityBusy(false);
    }
  };

  const handleHydrate = async (override?: {
    agentId?: string;
    layer?: string;
    failureSig?: string | null;
  }) => {
    setSynapseBusy(true);
    setSynapseOutcomeBanner(null);
    try {
      const payload = {
        agentId: override?.agentId ?? agentIdInput,
        layer: override?.layer ?? layerInput,
        failureSig: override?.failureSig !== undefined ? override.failureSig : failureSigInput || null,
      };
      const res = await fetch('/api/synapse/hydrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.swarmSynapse) {
        setSynapse(data.swarmSynapse as SwarmSynapseState);
      }
      const outcome = data.outcome as SwarmHydrateOutcome;
      if (outcome.status === 'LEASE_GRANTED') {
        setActiveFencingToken(outcome.fencingToken);
        setSynapseOutcomeBanner({
          tone: 'emerald',
          text: `LEASE_GRANTED (#${outcome.fencingToken}) on ${outcome.layer} for ${outcome.agentId} · GENESIS_SPORE.dna ${outcome.sporeBytes}B / 4096B.`,
        });
      } else if (outcome.status === 'PASS_0_ANTIBODY_HIT') {
        setSynapseOutcomeBanner({
          tone: 'emerald',
          text: `PASS_0_ANTIBODY_HIT (${outcome.antibodyId} · 0 LLM diagnostic passes): Run "${outcome.remediationCmd}"`,
        });
      } else if (outcome.status === 'LOCKED_BY_ACTIVE_PEER') {
        setSynapseOutcomeBanner({
          tone: 'amber',
          text: `LOCKED_BY_ACTIVE_PEER: ${outcome.leasedBy} holds fenced lease #${outcome.fencingToken} (${outcome.leaseExpiresInSec}s remaining) — duplicate stampede blocked in 0ms.`,
        });
      } else if (outcome.status === 'ALREADY_LANDED_BY_PEER') {
        setSynapseOutcomeBanner({
          tone: 'amber',
          text: `ALREADY_LANDED_BY_PEER (${outcome.leasedBy}): ${outcome.instruction}`,
        });
      } else {
        setSynapseOutcomeBanner({
          tone: 'rose',
          text: `${outcome.status}: ${outcome.instruction}`,
        });
      }
      await onRefreshState();
    } finally {
      setSynapseBusy(false);
    }
  };

  const handleDualYield = async (overrideFact?: string) => {
    setSynapseBusy(true);
    setSynapseOutcomeBanner(null);
    try {
      const factToSend = overrideFact !== undefined ? overrideFact : learnedFactInput;
      const res = await fetch('/api/synapse/yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: agentIdInput,
          layer: layerInput,
          fencingToken: activeFencingToken,
          commitSha: commitShaInput,
          learnedFact: factToSend,
          antibodySig: antibodySigInput || null,
          antibodyCmd: antibodyCmdInput || null,
        }),
      });
      const data = await res.json();
      if (data.swarmSynapse) {
        setSynapse(data.swarmSynapse as SwarmSynapseState);
      }
      if (!res.ok || !data.ok) {
        setSynapseOutcomeBanner({
          tone: 'rose',
          text: `[${data.outcome?.errorCode || 'REFUSED'}] ${data.outcome?.reason || 'Dual-Yield refused'}`,
        });
        return;
      }
      setSynapseOutcomeBanner({
        tone: 'emerald',
        text: `DUAL_YIELD_COMMITTED: Ring seq #${data.outcome.ringEvent.seqId} · Merkle ${String(data.outcome.ringEvent.merkleRoot).slice(0, 14)}… · Spore ${data.outcome.sporeBytes}B${data.outcome.antibodyRegistered ? ` · Registered ${data.outcome.antibodyRegistered}` : ''}.`,
      });
      await onRefreshState();
    } finally {
      setSynapseBusy(false);
    }
  };

  const handleLifoRollback = async () => {
    setSynapseBusy(true);
    setSynapseOutcomeBanner(null);
    try {
      const res = await fetch('/api/synapse/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: 1 }),
      });
      const data = await res.json();
      if (data.swarmSynapse) {
        setSynapse(data.swarmSynapse as SwarmSynapseState);
        setActiveFencingToken((data.swarmSynapse as SwarmSynapseState).authoritativeToken);
      }
      setSynapseOutcomeBanner({
        tone: 'amber',
        text: `LIFO_ROLLBACK_COMPLETE: Reverted ${data.rolled?.rolledBackEntries?.length ?? 0} journal entry & bumped authoritative fencing token to #${data.rolled?.newAuthoritativeToken}.`,
      });
      await onRefreshState();
    } finally {
      setSynapseBusy(false);
    }
  };

  const mission = synapse.offlineContinuity;
  const spore = synapse.sporeDna;
  const latestRing = synapse.realtimeEventRing[0];

  return (
    <div className="space-y-6">
      {/* Top Executive Header & 1-Click Complete Download Bar */}
      <section
        aria-labelledby="swarm-synapse-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400 tabular-nums">
              <span>GENESIS v0.7.0-RT · STIGMERGIC SWARM SYNAPSE</span>
              <span aria-hidden="true">·</span>
              <span>O(1) LEDGER COORDINATION</span>
              <span aria-hidden="true">·</span>
              <span>MAC-OFFLINE CONTINUITY</span>
            </div>
            <h1
              id="swarm-synapse-heading"
              className="text-xl font-semibold text-slate-900 dark:text-slate-50"
            >
              Self-Healing Swarm Synapse, Pass-0 Antibodies &amp; Mac-Offline Reassignment Proof
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-4xl leading-relaxed">
              Eliminates <code className="font-mono">O(M^2)</code> multi-session stampedes across Pi,
              Codex, OpenCode, AI Studio, Gemini, and MiniMax. Every work unit acquires a Kleppmann
              DDIA monotonic fencing lease, checks Pass-0 Antibodies in 0 LLM passes, commits a
              Dual-Yield epistemic delta into <code className="font-mono">GENESIS_SPORE.dna</code> (
              <code className="font-mono">&lt;= 4096B</code>), and proves end-to-end Genesis ↔ Otto
              reassignment with the Mac offline.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/argon/export.tar.gz"
              download="genesis-2100-complete-export.tar.gz"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Download Everything (.tar.gz)
            </a>

            <a
              href="/api/synapse/spore.dna"
              download="GENESIS_SPORE.dna"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Dna className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              GENESIS_SPORE.dna ({spore.byteLength}B)
            </a>

            <a
              href="/api/synapse/estate-swarm-synapse.py"
              download="estate-swarm-synapse.py"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
              estate-swarm-synapse.py
            </a>
          </div>
        </div>

        {/* 4 Calibrated Tabular Telemetry KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5 font-mono tabular-nums">
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              MONOTONIC FENCING TOKEN
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              #{synapse.authoritativeToken} · Ring Seq #{latestRing?.seqId ?? 0}
            </div>
            <div className="text-[11px] text-cyan-700 dark:text-cyan-400 truncate">
              Merkle {(latestRing?.merkleRoot ?? spore.merkleRoot).slice(0, 18)}…
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              PASS-0 ANTIBODY IMMUNITY
            </div>
            <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
              {synapse.catechismAntibodies.length} Active Reflexes (0-Pass)
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              {synapse.catechismAntibodies.reduce((s, a) => s + a.hitCount, 0)} cumulative 0-token saves
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              4KB EXECUTABLE SPORE BUDGET
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {spore.byteLength} / {spore.maxBytes} B ({((spore.byteLength / spore.maxBytes) * 100).toFixed(1)}%)
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              SHA {spore.sha256Prefix.slice(0, 10)} · {synapse.diskFreeMb} MB free
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              GENESIS ↔ OTTO OFFLINE PARITY
            </div>
            <div
              className={`text-sm font-semibold ${
                mission.parityVerified
                  ? 'text-emerald-700 dark:text-emerald-400'
                  : 'text-rose-700 dark:text-rose-400'
              }`}
            >
              {mission.parityVerified ? '100% SYNCHRONIZED' : 'DRIFT DETECTED'}
            </div>
            <div className="text-[11px] text-amber-700 dark:text-amber-400 truncate">
              Owner: {mission.genesisSurface.displayedOwner}
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 01: MAC-OFFLINE END-TO-END INSTRUCTION CONTINUITY & FOUNDER REASSIGNMENT PROOF */}
      <section
        aria-labelledby="offline-reassign-proof-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
              <span>01. TARGET COMMERCIAL PROOF · MAC-OFFLINE END-TO-END CONTINUITY</span>
              <span aria-hidden="true">·</span>
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                <Laptop className="w-3.5 h-3.5" aria-hidden="true" />
                Mac Host: {mission.macHostStatus} (0 local dependencies)
              </span>
            </div>
            <h2
              id="offline-reassign-proof-heading"
              className="text-base font-semibold text-slate-900 dark:text-slate-50"
            >
              {mission.instructionId}: {mission.title}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
              Proves one instruction tracked end-to-end with the Mac offline: Genesis and Otto read
              identical owner, checkpoint, and verified progress; failed auto-takeover surfaces{' '}
              <strong className="font-semibold text-slate-900 dark:text-slate-100">
                Needs reassignment
              </strong>
              ; choosing a new owner immediately fences out the old worker and switches both
              surfaces <strong className="font-semibold text-slate-900 dark:text-slate-100">only after</strong>{' '}
              the new worker acknowledges the handoff.
            </p>
          </div>

          <button
            type="button"
            onClick={() => runContinuityStep('RESET_PROOF')}
            disabled={continuityBusy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
            Reset Proof Cycle
          </button>
        </div>

        {/* Interactive 5-Step Deterministic Proof Controls */}
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3">
          <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-3">
            <div className="space-y-1 min-w-[310px]">
              <label
                htmlFor="reassign-worker-select"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300"
              >
                Choose Replacement Cloud Worker Owner
              </label>
              <select
                id="reassign-worker-select"
                value={selectedNewOwner}
                onChange={(e) => setSelectedNewOwner(e.target.value)}
                className="w-full pl-3 pr-8 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                {mission.availableCloudWorkers.map((w) => (
                  <option key={w.workerId} value={w.workerId}>
                    {w.workerId} ({w.formation} · {w.region})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={continuityBusy}
                onClick={() => runContinuityStep('FAIL_TAKEOVER')}
                className="px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200 bg-amber-100 dark:bg-amber-950/50 hover:bg-amber-200 dark:hover:bg-amber-900/60 border border-amber-300 dark:border-amber-700/70 rounded-lg transition-colors whitespace-nowrap"
              >
                1. Trigger Auto-Takeover Failure
              </button>

              <button
                type="button"
                disabled={continuityBusy}
                onClick={() => runContinuityStep('INITIATE_REASSIGN')}
                className="px-3 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap"
              >
                2. Reassign Owner (Bump Fence)
              </button>

              <button
                type="button"
                disabled={continuityBusy}
                onClick={() => runContinuityStep('TEST_STALE_WORKER_WRITE')}
                className="px-3 py-2 text-xs font-semibold text-rose-800 dark:text-rose-200 bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-300 dark:border-rose-800 rounded-lg transition-colors whitespace-nowrap"
              >
                3. Test Old Worker Write (Must Reject)
              </button>

              <button
                type="button"
                disabled={continuityBusy || !mission.pendingNewOwner}
                onClick={() => runContinuityStep('ACK_NEW_WORKER')}
                className="px-3 py-2 text-xs font-semibold text-cyan-900 dark:text-cyan-200 bg-cyan-100 dark:bg-cyan-950/60 hover:bg-cyan-200 dark:hover:bg-cyan-900/70 border border-cyan-300 dark:border-cyan-700 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap"
              >
                4. Acknowledge Handoff ({mission.pendingNewOwner ?? 'New Worker'})
              </button>

              <button
                type="button"
                disabled={continuityBusy}
                onClick={() => runContinuityStep('COMPLETE_VERIFIED_YIELD')}
                className="px-3 py-2 text-xs font-semibold text-emerald-900 dark:text-emerald-200 bg-emerald-100 dark:bg-emerald-950/60 hover:bg-emerald-200 dark:hover:bg-emerald-900/70 border border-emerald-300 dark:border-emerald-700 rounded-lg transition-colors whitespace-nowrap"
              >
                5. Seal Verified Yield
              </button>
            </div>
          </div>

          {continuityBanner && (
            <div
              role="status"
              className={`px-3.5 py-2.5 rounded-lg border text-xs font-mono ${
                continuityBanner.tone === 'emerald'
                  ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                  : continuityBanner.tone === 'amber'
                    ? 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
                    : 'bg-rose-50/80 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
              }`}
            >
              {continuityBanner.text}
            </div>
          )}
        </div>

        {/* Side-by-Side Live Surface Parity: Genesis Control Plane vs Otto Private Office */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 font-mono tabular-nums">
          {[mission.genesisSurface, mission.ottoSurface].map((surf) => {
            const isNeedsReassign = surf.displayedStatusLabel.startsWith('Needs reassignment');
            return (
              <div
                key={surf.surfaceName}
                className="p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3"
              >
                <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-slate-200 dark:border-slate-800">
                  <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                    {surf.surfaceName}
                  </span>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">
                    Fence #{surf.fencingToken} · Epoch e{mission.leaseEpoch}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-slate-500 dark:text-slate-400">Status</span>
                    <span
                      className={`font-semibold text-right ${
                        isNeedsReassign
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-emerald-600 dark:text-emerald-400'
                      }`}
                    >
                      {surf.displayedStatusLabel}
                    </span>
                  </div>

                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-slate-500 dark:text-slate-400">Displayed Active Owner</span>
                    <span className="font-semibold text-cyan-700 dark:text-cyan-300">
                      {surf.displayedOwner}
                    </span>
                  </div>

                  {surf.pendingAckTarget && (
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-slate-500 dark:text-slate-400">Pending Handoff ACK</span>
                      <span className="text-amber-600 dark:text-amber-300">
                        {surf.pendingAckTarget} (unconfirmed)
                      </span>
                    </div>
                  )}

                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-slate-500 dark:text-slate-400">Checkpoint SHA</span>
                    <span className="text-slate-800 dark:text-slate-200">
                      {surf.checkpointSha.slice(0, 16)}…
                    </span>
                  </div>

                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 text-[11px] text-slate-600 dark:text-slate-300 font-sans leading-relaxed">
                    <span className="font-mono text-slate-500 dark:text-slate-400 mr-1.5">
                      VERIFIED PROGRESS:
                    </span>
                    {surf.lastVerifiedProgress}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Rejected Stale Worker Attempts + Transition Ledger */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
          <div className="xl:col-span-5 p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-2">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-500" aria-hidden="true" />
              <span>Lease Authority Fencing Rejections ({mission.rejectedWriteLog.length})</span>
            </div>
            {mission.rejectedWriteLog.length === 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                No stale worker write attempts recorded yet. After clicking &ldquo;2. Reassign Owner&rdquo;,
                click &ldquo;3. Test Old Worker Write&rdquo; to verify HTTP 409 epoch fencing.
              </p>
            ) : (
              <div className="space-y-2 max-h-40 overflow-y-auto font-mono text-[11px] tabular-nums">
                {mission.rejectedWriteLog.map((rej, idx) => (
                  <div
                    key={`${rej.rejectedAtIso}-${idx}`}
                    className="p-2.5 rounded bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/70 text-rose-800 dark:text-rose-300 space-y-0.5"
                  >
                    <div className="font-semibold">
                      HTTP {rej.httpStatus} · {rej.errorCode}
                    </div>
                    <div>{rej.detail}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="xl:col-span-7 p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-2">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              End-to-End Continuity Audit Trail
            </div>
            <div className="max-h-40 overflow-y-auto divide-y divide-slate-200 dark:divide-slate-800 text-xs font-mono tabular-nums">
              {mission.transitionHistory.map((item) => (
                <div key={item.step} className="py-1.5 flex items-start justify-between gap-3">
                  <span className="text-slate-700 dark:text-slate-300">
                    #{item.step} · {item.event}
                  </span>
                  <span className="text-slate-500 shrink-0">fence #{item.fencingToken}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 02: INTERACTIVE STIGMERGIC SWARM COORDINATOR (HYDRATE / ANTIBODIES / DUAL-YIELD / ROLLBACK) */}
      <section
        aria-labelledby="stigmergic-coordinator-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1">
            <div className="text-xs font-mono text-amber-600 dark:text-amber-400">
              02. STIGMERGIC KERNEL · MYCELIUM TASK QUEUE, PASS-0 ANTIBODIES &amp; DUAL-YIELD ENFORCER
            </div>
            <h2
              id="stigmergic-coordinator-heading"
              className="text-base font-semibold text-slate-900 dark:text-slate-50"
            >
              Turn-0 Layer Hydration, 0-Pass Antibody Hit &amp; Turn-N Epistemic Dual-Yield
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={synapseBusy}
              onClick={() =>
                handleHydrate({
                  agentId: 'gemini-probe-02',
                  layer: 'idp/sqlite/step_runs',
                  failureSig: 'SQLITE_STEP_RUNS_NOT_NULL_DRIFT',
                })
              }
              className="px-3 py-1.5 text-xs font-mono font-medium text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 border border-emerald-300 dark:border-emerald-800 rounded-lg transition-colors whitespace-nowrap"
            >
              Test Pass-0 Antibody (0 LLM Passes)
            </button>

            <button
              type="button"
              disabled={synapseBusy}
              onClick={() =>
                handleHydrate({
                  agentId: 'competing-minimax-09',
                  layer: 'idp/platform/estate/memory/door.py',
                  failureSig: null,
                })
              }
              className="px-3 py-1.5 text-xs font-mono font-medium text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 hover:bg-amber-100 dark:hover:bg-amber-900/50 border border-amber-300 dark:border-amber-800 rounded-lg transition-colors whitespace-nowrap"
            >
              Test Peer Lease Collision
            </button>

            <button
              type="button"
              disabled={synapseBusy}
              onClick={() => handleDualYield('short')}
              className="px-3 py-1.5 text-xs font-mono font-medium text-rose-800 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/50 border border-rose-300 dark:border-rose-800 rounded-lg transition-colors whitespace-nowrap"
            >
              Test Missing Fact Refusal
            </button>

            <button
              type="button"
              disabled={synapseBusy}
              onClick={handleLifoRollback}
              className="px-3 py-1.5 text-xs font-mono font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap"
            >
              LIFO Saga Rollback (1 Step)
            </button>
          </div>
        </div>

        {/* Hydrate + Dual-Yield Form */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              Step A — Acquire Fenced Layer Lease (<code className="font-mono">synapse hydrate</code>)
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label
                  htmlFor="synapse-agent-id"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Session / Agent ID
                </label>
                <input
                  id="synapse-agent-id"
                  type="text"
                  value={agentIdInput}
                  onChange={(e) => setAgentIdInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
                />
              </div>
              <div>
                <label
                  htmlFor="synapse-layer-target"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Target Layer / Path
                </label>
                <input
                  id="synapse-layer-target"
                  type="text"
                  value={layerInput}
                  onChange={(e) => setLayerInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="synapse-failure-sig"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
              >
                Optional Failure Class Signature (Checks Pass-0 Antibodies First)
              </label>
              <input
                id="synapse-failure-sig"
                type="text"
                value={failureSigInput}
                onChange={(e) => setFailureSigInput(e.target.value)}
                placeholder="e.g. SQLITE_STEP_RUNS_NOT_NULL_DRIFT"
                className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
              />
            </div>

            <button
              type="button"
              disabled={synapseBusy}
              onClick={() => handleHydrate()}
              className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${synapseBusy ? 'animate-spin' : ''}`} aria-hidden="true" />
              Hydrate &amp; Lease Target Layer
            </button>
          </div>

          <div className="lg:col-span-7 p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                Step B — Commit Dual-Yield + Synthesize Antibody (<code className="font-mono">synapse yield</code>)
              </span>
              <span className="text-[11px] font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
                Active Token #{activeFencingToken}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label
                  htmlFor="synapse-commit-sha"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Commit SHA
                </label>
                <input
                  id="synapse-commit-sha"
                  type="text"
                  value={commitShaInput}
                  onChange={(e) => setCommitShaInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
                />
              </div>
              <div>
                <label
                  htmlFor="synapse-ab-sig"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  New Antibody Signature
                </label>
                <input
                  id="synapse-ab-sig"
                  type="text"
                  value={antibodySigInput}
                  onChange={(e) => setAntibodySigInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
                />
              </div>
              <div>
                <label
                  htmlFor="synapse-ab-cmd"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Pass-0 Remediation Cmd
                </label>
                <input
                  id="synapse-ab-cmd"
                  type="text"
                  value={antibodyCmdInput}
                  onChange={(e) => setAntibodyCmdInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="synapse-fact-input"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1"
              >
                Mandatory Epistemic Delta (<code className="font-mono">--fact</code> &gt;= 15 chars)
              </label>
              <textarea
                id="synapse-fact-input"
                rows={2}
                value={learnedFactInput}
                onChange={(e) => setLearnedFactInput(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setShowSporeInspector((v) => !v)}
                className="text-xs font-mono text-cyan-700 dark:text-cyan-400 hover:underline"
              >
                {showSporeInspector
                  ? 'Hide Live GENESIS_SPORE.dna Payload'
                  : `Inspect Live GENESIS_SPORE.dna (${spore.byteLength} B)`}
              </button>

              <button
                type="button"
                disabled={synapseBusy}
                onClick={() => handleDualYield()}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap"
              >
                <span>Commit Dual-Yield &amp; Repack 4KB Spore</span>
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>

        {synapseOutcomeBanner && (
          <div
            role="status"
            className={`px-3.5 py-2.5 rounded-lg border text-xs font-mono flex items-center gap-2 ${
              synapseOutcomeBanner.tone === 'emerald'
                ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : synapseOutcomeBanner.tone === 'amber'
                  ? 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
                  : 'bg-rose-50/80 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}
          >
            {synapseOutcomeBanner.tone === 'rose' ? (
              <XCircle className="w-4 h-4 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            )}
            <span>{synapseOutcomeBanner.text}</span>
          </div>
        )}

        {showSporeInspector && (
          <div className="p-3.5 rounded-lg bg-slate-950 text-slate-200 border border-slate-800 font-mono text-[11px] space-y-2 overflow-x-auto">
            <div className="text-amber-400">
              .genesis/GENESIS_SPORE.dna ({spore.byteLength} bytes &lt;= 4096B cap · executable via python3)
            </div>
            <pre className="whitespace-pre-wrap break-all text-cyan-300">{spore.executableScript}</pre>
          </div>
        )}

        {/* Mycelium Task Queue & Catechism Antibodies Tables */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
          <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
            <div className="px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/70 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-900 dark:text-slate-100">
              mycelium_task_queue (Active Peer Leases &amp; Landed Layers)
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    <th className="py-2 px-3">Layer</th>
                    <th className="py-2 px-3">State</th>
                    <th className="py-2 px-3">Session</th>
                    <th className="py-2 px-3 text-right">Fence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {synapse.myceliumTaskQueue.map((row) => (
                    <tr key={row.taskId} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30">
                      <td className="py-2 px-3 text-slate-900 dark:text-slate-100">{row.taskId}</td>
                      <td
                        className={`py-2 px-3 font-semibold ${
                          row.status === 'COMPLETED'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {row.status}
                      </td>
                      <td className="py-2 px-3 text-slate-600 dark:text-slate-300">{row.leasedBy}</td>
                      <td className="py-2 px-3 text-right text-cyan-700 dark:text-cyan-400">
                        #{row.fencingToken}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
            <div className="px-3.5 py-2.5 bg-slate-50 dark:bg-slate-900/70 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-900 dark:text-slate-100">
              catechism_antibodies (Pass-0 Reflexes)
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    <th className="py-2 px-3">ID</th>
                    <th className="py-2 px-3">Signature</th>
                    <th className="py-2 px-3 text-right">0-Pass Hits</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {synapse.catechismAntibodies.map((ab) => (
                    <tr key={ab.antibodyId} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30">
                      <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400 font-semibold">
                        {ab.antibodyId}
                      </td>
                      <td className="py-2 px-3 text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
                        {ab.failureClassSignature}
                      </td>
                      <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-300">
                        {ab.hitCount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 03: HANDOVER 2026-11-12 CLAIM AUDIT & S1-S5 FAILURE PREVENTION MATRIX */}
      <section
        aria-labelledby="handover-claim-audit-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
      >
        <div className="space-y-1 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-amber-600 dark:text-amber-400">
            03. HANDOVER_2026-11-12.MD · REMOTE BACKUP LINEAGE &amp; ZERO-ROUNDING CLAIM AUDIT
          </div>
          <h2
            id="handover-claim-audit-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Off-Machine Backup Commits, S1–S5 Concurrent Failure Prevention &amp; Open Commercial Boundaries
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Verified Remote Backups */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-2.5">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <GitCommit className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
              <span>Verified GitHub Backup Refs (Survives Dead Laptop)</span>
            </div>
            <div className="space-y-2 font-mono text-xs tabular-nums">
              {synapse.handoverAudit.remoteBackups.map((bk) => (
                <div
                  key={bk.repo}
                  className="p-2.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {bk.repo} · <span className="text-cyan-700 dark:text-cyan-400">{bk.branch}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      Commit {bk.commitSha} · {bk.verifiedBy}
                    </div>
                  </div>
                  <a
                    href={bk.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400 hover:underline shrink-0"
                  >
                    <span>GitHub</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              ))}
            </div>
          </div>

          {/* Open Commercial Boundaries (Zero Rounding Up) */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-2.5">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              Remaining Honest Commercial &amp; Governance Boundaries
            </div>
            <div className="space-y-2 text-xs">
              {synapse.handoverAudit.commercialGapsOpen.map((gap) => (
                <div
                  key={gap.id}
                  className="p-2.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-0.5"
                >
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {gap.item}
                    </span>
                    <span
                      className={`text-[11px] ${
                        gap.status === 'RESOLVED_IN_BUNDLE'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {gap.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    {gap.honestDetail}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* S1-S5 Concurrent Failure Surface Matrix */}
        <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/70 border-b border-slate-200 dark:border-slate-800 font-mono text-slate-500 dark:text-slate-400">
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Estate Surface</th>
                  <th className="py-2.5 px-3">Concurrent M-Session Failure Mode</th>
                  <th className="py-2.5 px-3">Deterministic Kernel Prevention (v0.7.0-RT)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {synapse.failureMatrix.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 font-mono font-semibold text-amber-600 dark:text-amber-400">
                      {row.id}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-slate-100">
                      {row.surface}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                      {row.failureMode}
                    </td>
                    <td className="py-2.5 px-3 text-emerald-700 dark:text-emerald-300 font-mono text-[11px]">
                      {row.deterministicPrevention}
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
};
