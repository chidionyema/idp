import React, { useState, useEffect } from 'react';
import {
  Download,
  Copy,
  Check,
  ShieldAlert,
  RotateCcw,
  Terminal,
  Play,
  Database,
  UserCheck,
} from 'lucide-react';
import type {
  IoCanonicalWorkGraphState,
  Oracle00AdjudicationResult,
  Synapse00OperationalizationResult,
  MandatoryEvalReceipt,
  MandatoryTrainingTuple,
} from '../engine/ioCanonicalEngine';

interface IoWorkGraphAndIdentityViewProps {
  initialWorkGraph: IoCanonicalWorkGraphState;
  canonicalSporeBytes: number;
  onRefreshState: () => Promise<void>;
}

type GraphTabFilter = 'WORK_GRAPH' | 'UNOWNED_ONLY' | 'CANONICAL_PACKS' | 'IO_GENEALOGY';

export const IoWorkGraphAndIdentityView: React.FC<IoWorkGraphAndIdentityViewProps> = ({
  initialWorkGraph,
  canonicalSporeBytes,
  onRefreshState,
}) => {
  const [graphState, setGraphState] = useState<IoCanonicalWorkGraphState>(initialWorkGraph);
  const [activeFilter, setActiveFilter] = useState<GraphTabFilter>('WORK_GRAPH');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedMacCmd, setCopiedMacCmd] = useState(false);

  const [busyAction, setBusyAction] = useState(false);
  const [statusBanner, setStatusBanner] = useState<{
    tone: 'emerald' | 'amber' | 'rose';
    text: string;
  } | null>(null);

  const [selectedStewardDid, setSelectedStewardDid] = useState<string>(
    initialWorkGraph.identities[1]?.actorDid ?? 'did:estate:principal:aurelius-marcus'
  );
  const [selectedDomainId, setSelectedDomainId] = useState<string>('DOM-IO-ENGINE');
  const [oracleLayerInput, setOracleLayerInput] = useState<string>('packages/io-engine/index.ts');
  const [oracleResult, setOracleResult] = useState<Oracle00AdjudicationResult | null>(null);
  const [synapseResult, setSynapseResult] = useState<Synapse00OperationalizationResult | null>(null);

  useEffect(() => {
    setGraphState(initialWorkGraph);
  }, [initialWorkGraph]);

  // Real-time SSE listener: Founder sees every eval & training tuple across ALL activities in <15ms
  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    const onPulse = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as {
          ioWorkGraph?: IoCanonicalWorkGraphState;
          evalReceipt?: MandatoryEvalReceipt;
          trainingTuple?: MandatoryTrainingTuple;
        };
        if (parsed.ioWorkGraph) {
          setGraphState(parsed.ioWorkGraph);
        }
      } catch {
        // Ignore malformed SSE payload
      }
    };
    es.addEventListener('io-activity-pulse', onPulse);
    return () => {
      es.removeEventListener('io-activity-pulse', onPulse);
      es.close();
    };
  }, []);

  const unownedNodes = graphState.workGraphNodes.filter((n) => n.disposition === 'UNOWNED_DRIFT');
  const unownedArtifactCount = unownedNodes.reduce((s, n) => s + n.artifactCount, 0);
  const totalIndexedArtifacts = graphState.workGraphNodes.reduce((s, n) => s + n.artifactCount, 0);
  const passEvalCount = graphState.evalReceipts.filter(
    (r) => r.verdict === 'PASS_PRODUCTION_GRADE'
  ).length;
  const blockedEvalCount = graphState.evalReceipts.length - passEvalCount;
  const activeSessionId =
    graphState.activeSessions.find((s) => s.status === 'ACTIVE_FENCED')?.sessionId ??
    'ses-aurelius-io-01';

  const copyMacSyncCommand = async () => {
    const origin =
      typeof window !== 'undefined'
        ? window.location.origin
        : 'https://ais-dev-pzsvwui4y7si7n5xkqupny-534240513427.europe-west3.run.app';
    const cmd = `curl -fsSL ${origin}/api/io/sync-to-mac.sh | bash`;
    try {
      await navigator.clipboard.writeText(cmd);
      setCopiedMacCmd(true);
      window.setTimeout(() => setCopiedMacCmd(false), 2400);
    } catch {
      setStatusBanner({
        tone: 'amber',
        text: `Run in local argon/idp checkout: ${cmd}`,
      });
    }
  };

  const handleTriageAllUnowned = async () => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const res = await fetch('/api/io/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'TRIAGE_ALL', sessionId: activeSessionId }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      setStatusBanner({
        tone: 'emerald',
        text: `Triaged ${data.triagedCount ?? 0} unowned clusters with forced write-back receipts -> Remaining unowned artifacts: ${data.remainingUnownedArtifacts ?? 0}.`,
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleTriageSingleNode = async (nodeId: string) => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const res = await fetch('/api/io/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'SINGLE',
          nodeId,
          sessionId: activeSessionId,
          ownerDid: selectedStewardDid,
          boundPackId: 'PACK-15',
          disposition: 'CANONICAL_PACK',
        }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      setStatusBanner({
        tone: data.ok ? 'emerald' : 'rose',
        text: data.ok
          ? `Bound ${nodeId} to PACK-15 with persistent real-name owner & write-back receipt (Unowned remaining: ${data.remainingUnownedArtifacts}).`
          : data.error || 'Triage blocked by mandatory eval gate.',
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleTestUnownedCommitBlock = async () => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const res = await fetch('/api/io/activity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          simulateViolation: 'UNOWNED_SESSIONLESS_STASH',
        }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      setStatusBanner({
        tone: 'amber',
        text: `[HTTP ${data.rejectedHttpStatus ?? 428} BLOCKED] Invisible/sessionless work refused by AGENTS.md Line-1 & Real-Name Gate -> Crystallized ${data.trainingTuple?.tupleId} (DPO_REJECTION_PAIR + ${data.trainingTuple?.synthesizedAntibodyId}).`,
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleResetWorkGraphDemo = async () => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const res = await fetch('/api/io/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'RESET_DEMO' }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      setStatusBanner({
        tone: 'amber',
        text: 'Reset Single Work Graph to pre-triage baseline (32 stashes, 3 dist bundles, 19 previews flagged UNOWNED_DRIFT).',
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleStartSession = async () => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const domain = graphState.domains.find((d) => d.domainId === selectedDomainId);
      const res = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actorDid: selectedStewardDid,
          domainId: selectedDomainId,
          packId: domain?.primaryPackId ?? 'PACK-15',
        }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      setStatusBanner({
        tone: data.ok ? 'emerald' : 'rose',
        text: data.ok
          ? `Started fenced estate-session ${data.session.sessionId} for ${data.session.actorRealName} (Eval 100/100 · SFT tuple ${data.trainingTuple?.tupleId} written).`
          : data.error || 'Failed to start estate-session.',
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleRunOracle00 = async (simulateDuplicateRebuild = false) => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const targetLayer = simulateDuplicateRebuild
        ? 'src/scratch/rebuild-mega-oracle-again.ts'
        : oracleLayerInput;
      const res = await fetch('/api/io/oracle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: activeSessionId,
          actorDid: selectedStewardDid,
          targetLayer,
          proposedSymbolOrFile: simulateDuplicateRebuild ? 'mega-oracle' : undefined,
        }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      if (data.oracle) setOracleResult(data.oracle as Oracle00AdjudicationResult);
      setStatusBanner({
        tone: data.oracle?.verdict === 'ADJUDICATED_CANONICAL_PROCEED' ? 'emerald' : 'amber',
        text: `ORACLE-00 (${data.oracle?.verdict}): ${data.oracle?.mandatoryWriteBackDirective}`,
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const handleRunSynapse00 = async (simulateLegacy55KbSpore = false) => {
    setBusyAction(true);
    setStatusBanner(null);
    try {
      const res = await fetch('/api/io/synapse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: activeSessionId,
          actorDid: selectedStewardDid,
          localHostSporeBytes: simulateLegacy55KbSpore ? 5632 : canonicalSporeBytes,
        }),
      });
      const data = await res.json();
      if (data.ioWorkGraph) setGraphState(data.ioWorkGraph);
      if (data.synapse) setSynapseResult(data.synapse as Synapse00OperationalizationResult);
      setStatusBanner({
        tone: data.synapse?.syncVerdict === 'ZERO_TOUCH_SYNC_READY' ? 'emerald' : 'amber',
        text: `SYNAPSE-00 (${data.synapse?.syncVerdict}): ${data.synapse?.hostSporeRemediation}`,
      });
      await onRefreshState();
    } finally {
      setBusyAction(false);
    }
  };

  const q = searchQuery.trim().toLowerCase();
  const filteredGraphNodes = graphState.workGraphNodes.filter((n) => {
    if (activeFilter === 'UNOWNED_ONLY' && n.disposition !== 'UNOWNED_DRIFT') return false;
    if (!q) return true;
    return (
      n.label.toLowerCase().includes(q) ||
      n.physicalLocation.toLowerCase().includes(q) ||
      (n.ownerRealName || '').toLowerCase().includes(q) ||
      (n.boundPackId || '').toLowerCase().includes(q)
    );
  });

  const filteredPacks = graphState.packs.filter((p) => {
    if (!q) return true;
    return (
      p.packId.toLowerCase().includes(q) ||
      p.slug.toLowerCase().includes(q) ||
      p.title.toLowerCase().includes(q) ||
      p.ownerRealName.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Executive Header: Canonical PACK-15 IO Engine, Surface Provenance & 1-Click Sync/Export */}
      <section
        aria-labelledby="io-work-graph-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400 tabular-nums">
              <span>PACK-15 @meridian-estate/io-engine</span>
              <span aria-hidden="true">·</span>
              <span>CLOUD SURFACE: fe43cf69</span>
              <span aria-hidden="true">·</span>
              <span>BUS: /packs · /session · /capabilities</span>
            </div>
            <h1
              id="io-work-graph-heading"
              className="text-xl font-semibold text-slate-900 dark:text-slate-50"
            >
              Single Work Graph, Persistent Real-Name Ownership &amp; Forced Real-Time Eval + Training
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-4xl leading-relaxed">
              Extracts <code className="font-mono">ORACLE-00</code> (<code className="font-mono">protocolEngine.ts:17129</code> at{' '}
              <code className="font-mono">255295f</code>) and <code className="font-mono">SYNAPSE-00</code> (
              <code className="font-mono">protocolEngine.ts:18925</code> at <code className="font-mono">a127ac2</code>) into
              canonical <code className="font-mono">packages/io-engine</code> + standalone <code className="font-mono">bin/io</code>.
              Indexes all 15 packs, 32 stashes, 92 branches, 3 dist bundles, and 19 previews under named stewards, and enforces
              mandatory real-time evaluation and SFT/DPO dataset crystallization across every activity.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/argon/export.tar.gz"
              download="genesis-2100-complete-export.tar.gz"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Download Complete Package (.tar.gz)
            </a>

            <a
              href="/api/io/bin-io"
              download="io"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              Download bin/io CLI
            </a>

            <a
              href="/api/io/training-dataset.jsonl"
              download="realtime-training-dataset.jsonl"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Database className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
              Training JSONL ({graphState.trainingTuples.length})
            </a>

            <button
              type="button"
              onClick={copyMacSyncCommand}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              {copiedMacCmd ? (
                <Check className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
              )}
              {copiedMacCmd ? 'Copied Mac Sync Command' : 'Copy 1-Line Mac Sync'}
            </button>
          </div>
        </div>

        {/* 4 Calibrated Tabular KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5 font-mono tabular-nums">
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              SINGLE WORK GRAPH COVERAGE
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {graphState.packs.length} Packs · {totalIndexedArtifacts} Artifacts
            </div>
            <div
              className={`text-[11px] ${
                unownedArtifactCount === 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              {unownedArtifactCount === 0
                ? '0 Unowned (100% Triaged)'
                : `${unownedArtifactCount} Unowned (${unownedNodes.length} Drift Clusters)`}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              PERSISTENT REAL-NAME OWNERSHIP
            </div>
            <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
              {graphState.domains.length} / {graphState.domains.length} Domains Owned
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              Principal: {graphState.accountableFounder.realName}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              FORCED REAL-TIME EVAL HARNESS
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {graphState.evalReceipts.length} Scored (100% Enforced)
            </div>
            <div className="text-[11px] text-cyan-700 dark:text-cyan-400 truncate">
              {passEvalCount} Passed · {blockedEvalCount} Blocked at Gate
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              MANDATORY TRAINING DATASET
            </div>
            <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
              {graphState.trainingTuples.length} Live SFT / DPO Tuples
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              Spore {canonicalSporeBytes} B / 4096 B · SSE Live
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 01: SINGLE WORK GRAPH & INVISIBLE-WORK EXTINGUISHER */}
      <section
        aria-labelledby="invisible-work-extinguisher-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1">
            <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
              01. SINGLE QUERYABLE WORK GRAPH · ZERO INVISIBLE WORK LAW
            </div>
            <h2
              id="invisible-work-extinguisher-heading"
              className="text-base font-semibold text-slate-900 dark:text-slate-50"
            >
              32 Git Stashes, 92 Branches, 3 Dist Bundles, 19 Previews &amp; 15-Pack Registry
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
              Eliminates filename luck and parked invisible work. Every stash, branch cohort, binary bundle,
              and preview sandbox must bind to a canonical pack with a real-name steward and SHA-256 write-back receipt.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={busyAction || unownedArtifactCount === 0}
              onClick={handleTriageAllUnowned}
              className="px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Triage All Unowned Into Canonical Packs ({unownedArtifactCount})
            </button>

            <button
              type="button"
              disabled={busyAction}
              onClick={handleTestUnownedCommitBlock}
              className="px-3 py-2 text-xs font-semibold text-rose-800 dark:text-rose-200 bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-300 dark:border-rose-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Test Unowned Commit (Must Block)
            </button>

            <button
              type="button"
              disabled={busyAction}
              onClick={handleResetWorkGraphDemo}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
              Reset Triage Baseline
            </button>
          </div>
        </div>

        {statusBanner && (
          <div
            role="status"
            className={`px-3.5 py-2.5 rounded-lg border text-xs font-mono ${
              statusBanner.tone === 'emerald'
                ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : statusBanner.tone === 'amber'
                  ? 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
                  : 'bg-rose-50/80 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}
          >
            {statusBanner.text}
          </div>
        )}

        {/* Filter Bar + Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div
            role="tablist"
            aria-label="Work Graph View Filter"
            className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 rounded-lg"
          >
            {(
              [
                { id: 'WORK_GRAPH', label: `All Graph Nodes (${graphState.workGraphNodes.length})` },
                { id: 'UNOWNED_ONLY', label: `Unowned Drift (${unownedNodes.length})` },
                { id: 'CANONICAL_PACKS', label: `15-Pack Registry (${graphState.packs.length})` },
                { id: 'IO_GENEALOGY', label: `IO Build Genealogy (${graphState.ioBuildGenealogy.length})` },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeFilter === tab.id}
                onClick={() => setActiveFilter(tab.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  activeFilter === tab.id
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-amber-300 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="w-full md:w-80">
            <label htmlFor="work-graph-search" className="sr-only">
              Search packs, branches, stashes, or stewards
            </label>
            <input
              id="work-graph-search"
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search pack, SHA, stash, or steward…"
              className="w-full px-3 py-1.5 text-xs font-mono bg-slate-50 dark:bg-[#070B14] border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>

        {/* Dynamic Table View Based on Active Tab */}
        {(activeFilter === 'WORK_GRAPH' || activeFilter === 'UNOWNED_ONLY') && (
          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            {filteredGraphNodes.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400">
                Zero unowned work artifacts remain — every stash, branch cohort, bundle, and preview is bound to a canonical pack with a real-name owner.
              </div>
            ) : (
              <table className="w-full text-left border-collapse text-xs tabular-nums">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                    <th className="py-2.5 px-3 font-medium">Artifact Cluster &amp; Physical Residence</th>
                    <th className="py-2.5 px-3 font-medium text-right">Count</th>
                    <th className="py-2.5 px-3 font-medium">Bound Pack</th>
                    <th className="py-2.5 px-3 font-medium">Persistent Real-Name Owner</th>
                    <th className="py-2.5 px-3 font-medium">Disposition &amp; Receipt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {filteredGraphNodes.map((node) => {
                    const isUnowned = node.disposition === 'UNOWNED_DRIFT';
                    return (
                      <tr
                        key={node.nodeId}
                        className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors"
                      >
                        <td className="py-2.5 px-3 space-y-0.5 max-w-md">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {node.label}
                          </div>
                          <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                            {node.physicalLocation}
                          </div>
                          <div className="text-[11px] text-slate-600 dark:text-slate-400">
                            {node.invisibleRiskSummary}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-900 dark:text-slate-100">
                          {node.artifactCount}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-cyan-700 dark:text-cyan-400 whitespace-nowrap">
                          {node.boundPackId ?? 'UNBOUND'}
                        </td>
                        <td className="py-2.5 px-3">
                          {node.ownerRealName ? (
                            <div className="space-y-0.5">
                              <div className="font-medium text-slate-900 dark:text-slate-100">
                                {node.ownerRealName}
                              </div>
                              <div className="font-mono text-[11px] text-slate-500">
                                Principal: {node.accountableHuman.split(' ')[0]} Onyema
                              </div>
                            </div>
                          ) : (
                            <span className="font-mono text-rose-600 dark:text-rose-400 font-semibold">
                              UNOWNED (Blocks Close)
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono whitespace-nowrap">
                          {isUnowned ? (
                            <button
                              type="button"
                              disabled={busyAction}
                              onClick={() => handleTriageSingleNode(node.nodeId)}
                              className="px-2.5 py-1 text-[11px] font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded transition-colors"
                            >
                              Assign &amp; Land Receipt
                            </button>
                          ) : (
                            <div className="space-y-0.5">
                              <div className="text-emerald-700 dark:text-emerald-400 font-semibold">
                                {node.disposition}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                SHA {node.writeBackReceiptHash?.slice(0, 12)}
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeFilter === 'CANONICAL_PACKS' && (
          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                  <th className="py-2.5 px-3 font-medium">Pack ID</th>
                  <th className="py-2.5 px-3 font-medium">Slug &amp; Canonical Module Path</th>
                  <th className="py-2.5 px-3 font-medium">Named Domain Steward</th>
                  <th className="py-2.5 px-3 font-medium text-right">Tests</th>
                  <th className="py-2.5 px-3 font-medium">Registry SHA-256</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {filteredPacks.map((pack) => (
                  <tr
                    key={pack.packId}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <td className="py-2.5 px-3 font-mono font-semibold text-amber-600 dark:text-amber-400 whitespace-nowrap">
                      {pack.packId}
                    </td>
                    <td className="py-2.5 px-3 space-y-0.5">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {pack.title}
                      </div>
                      <div className="font-mono text-[11px] text-cyan-700 dark:text-cyan-400">
                        {pack.canonicalPath} · {pack.sourceCommitRef}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-800 dark:text-slate-200">
                      {pack.ownerRealName}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                      {pack.verifiedTestsCount}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {pack.sha256Hash.slice(0, 18)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeFilter === 'IO_GENEALOGY' && (
          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                  <th className="py-2.5 px-3 font-medium">#</th>
                  <th className="py-2.5 px-3 font-medium">Historical IO Build &amp; Residence</th>
                  <th className="py-2.5 px-3 font-medium">Root Cause of Rebuild Confusion</th>
                  <th className="py-2.5 px-3 font-medium">Permanent Cleanup in PACK-15</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {graphState.ioBuildGenealogy.map((item) => (
                  <tr key={item.buildNumber} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40">
                    <td className="py-2.5 px-3 font-mono font-semibold text-amber-600 dark:text-amber-400">
                      #{item.buildNumber}
                    </td>
                    <td className="py-2.5 px-3 space-y-0.5 max-w-xs">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {item.codename}
                      </div>
                      <div className="font-mono text-[11px] text-cyan-700 dark:text-cyan-400">
                        {item.commitOrPath}
                      </div>
                      <div className="text-[11px] text-slate-500">{item.testEvidence}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300 max-w-sm leading-relaxed">
                      {item.historicalDefect}
                    </td>
                    <td className="py-2.5 px-3 space-y-0.5 max-w-sm leading-relaxed">
                      <div className="font-mono text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                        {item.status}
                      </div>
                      <div className="text-slate-700 dark:text-slate-300 [overflow-wrap:anywhere]">{item.canonicalResolution}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* SECTION 02: CANONICAL PACK-15 IO ENGINE (ORACLE-00 + SYNAPSE-00) & REAL-NAME DOMAIN STEWARDS */}
      <section
        aria-labelledby="canonical-io-engine-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
      >
        <div className="space-y-1 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
            02. CANONICAL PACK-15 EXECUTION · ORACLE-00 + SYNAPSE-00 + PERSISTENT DOMAIN STEWARDSHIP
          </div>
          <h2
            id="canonical-io-engine-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Extracted IO Engine Contract &amp; Real-Name Domain Ownership Matrix
          </h2>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Left 5 Cols: Interactive ORACLE-00 + SYNAPSE-00 + estate-session Executor */}
          <div className="xl:col-span-5 p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                <span>AGENTS.md Line-1: Bind Persistent Real-Name Steward &amp; Session</span>
              </div>

              <div className="grid grid-cols-1 gap-2.5">
                <div className="space-y-1">
                  <label
                    htmlFor="io-steward-select"
                    className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                  >
                    Real-Name Steward Identity
                  </label>
                  <select
                    id="io-steward-select"
                    value={selectedStewardDid}
                    onChange={(e) => setSelectedStewardDid(e.target.value)}
                    className="w-full pl-2.5 pr-7 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  >
                    {graphState.identities.map((id) => (
                      <option key={id.actorDid} value={id.actorDid}>
                        {id.realName}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label
                    htmlFor="io-domain-select"
                    className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                  >
                    Owned Estate Domain
                  </label>
                  <select
                    id="io-domain-select"
                    value={selectedDomainId}
                    onChange={(e) => setSelectedDomainId(e.target.value)}
                    className="w-full pl-2.5 pr-7 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                  >
                    {graphState.domains.map((d) => (
                      <option key={d.domainId} value={d.domainId}>
                        {d.domainId} ({d.primaryPackId})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="button"
                disabled={busyAction}
                onClick={handleStartSession}
                className="w-full py-2 px-3 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap"
              >
                Start Fenced estate-session (Active: {activeSessionId})
              </button>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-2.5">
              <div className="space-y-1">
                <label
                  htmlFor="oracle-layer-input"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                >
                  Target Layer for ORACLE-00 Causal Adjudicator (<code className="font-mono">protocolEngine.ts:17129</code>)
                </label>
                <input
                  id="oracle-layer-input"
                  type="text"
                  value={oracleLayerInput}
                  onChange={(e) => setOracleLayerInput(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busyAction}
                  onClick={() => handleRunOracle00(false)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap"
                >
                  <Play className="w-3.5 h-3.5" aria-hidden="true" />
                  Run ORACLE-00 Adjudicator
                </button>

                <button
                  type="button"
                  disabled={busyAction}
                  onClick={() => handleRunOracle00(true)}
                  className="px-3 py-2 text-xs font-semibold text-rose-800 dark:text-rose-200 bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-300 dark:border-rose-800 rounded-lg transition-colors whitespace-nowrap"
                >
                  Test Duplicate IO Rebuild (Blocks)
                </button>
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  disabled={busyAction}
                  onClick={() => handleRunSynapse00(false)}
                  className="px-3 py-2 text-xs font-semibold text-cyan-900 dark:text-cyan-200 bg-cyan-100 dark:bg-cyan-950/60 hover:bg-cyan-200 dark:hover:bg-cyan-900/70 border border-cyan-300 dark:border-cyan-700 rounded-lg transition-colors whitespace-nowrap"
                >
                  Run SYNAPSE-00 Zero-Touch Sync
                </button>

                <button
                  type="button"
                  disabled={busyAction}
                  onClick={() => handleRunSynapse00(true)}
                  className="px-3 py-2 text-xs font-medium text-amber-900 dark:text-amber-200 bg-amber-100 dark:bg-amber-950/50 hover:bg-amber-200 dark:hover:bg-amber-900/60 border border-amber-300 dark:border-amber-700/70 rounded-lg transition-colors whitespace-nowrap"
                >
                  Audit Legacy 5.5KB Spore Drift
                </button>
              </div>

              {oracleResult && (
                <div className="p-3 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 font-mono text-[11px] space-y-1">
                  <div className="font-semibold text-cyan-700 dark:text-cyan-400">
                    {oracleResult.engineVersion} → {oracleResult.verdict}
                  </div>
                  <div className="text-slate-600 dark:text-slate-300">
                    Deduplicated {oracleResult.deduplicatedBranchClones}/92 branches · Chain{' '}
                    {oracleResult.causalChainHash.slice(0, 14)}…
                  </div>
                </div>
              )}

              {synapseResult && (
                <div className="p-3 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 font-mono text-[11px] space-y-1">
                  <div className="font-semibold text-emerald-700 dark:text-emerald-400">
                    {synapseResult.engineVersion} → {synapseResult.syncVerdict}
                  </div>
                  <div className="text-slate-600 dark:text-slate-300">
                    {synapseResult.hostSporeRemediation}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right 7 Cols: 8-Domain Persistent Real-Name Stewardship Matrix */}
          <div className="xl:col-span-7 overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-xl">
            <table className="w-full text-left border-collapse text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                  <th className="py-2.5 px-3 font-medium">Domain &amp; Canonical Paths</th>
                  <th className="py-2.5 px-3 font-medium">Pack</th>
                  <th className="py-2.5 px-3 font-medium">Real-Name Steward &amp; Sovereign Principal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {graphState.domains.map((dom) => (
                  <tr key={dom.domainId} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40">
                    <td className="py-2.5 px-3 space-y-0.5">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {dom.domainName}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500">
                        {dom.canonicalPaths.join(' · ')}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-amber-600 dark:text-amber-400 whitespace-nowrap">
                      {dom.primaryPackId}
                    </td>
                    <td className="py-2.5 px-3 space-y-0.5">
                      <div className="font-medium text-cyan-700 dark:text-cyan-300">
                        {dom.stewardRealName}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500">{dom.stewardDid}</div>
                      <div className="font-mono text-[11px] text-slate-600 dark:text-slate-400">
                        Principal: {dom.accountableHuman}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* SECTION 03: FOUNDER REAL-TIME MANDATORY EVAL & SFT/DPO TRAINING STREAM */}
      <section
        aria-labelledby="realtime-eval-training-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="space-y-1 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-amber-600 dark:text-amber-400 tabular-nums">
            03. FOUNDER REAL-TIME VISIBILITY · MANDATORY 5-GATE EVAL &amp; LIVE SFT/DPO TRAINING LEDGER
          </div>
          <h2
            id="realtime-eval-training-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Every Activity Scored &amp; Crystallized Into Training Data in Real Time (Zero Bypass)
          </h2>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Mandatory 5-Gate Real-Time Evaluation Stream */}
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
            <div className="px-3.5 py-2.5 bg-slate-50 dark:bg-[#070B14] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2 text-xs font-semibold text-slate-900 dark:text-slate-100">
              <span className="whitespace-nowrap">Live 5-Gate Evaluations ({graphState.evalReceipts.length})</span>
              <span className="font-mono text-[11px] text-slate-500 whitespace-nowrap shrink-0">ID · Session · Pack · E1 · Receipt</span>
            </div>
            <div className="max-h-72 overflow-y-auto divide-y divide-slate-200 dark:divide-slate-800 text-xs tabular-nums">
              {graphState.evalReceipts.slice(0, 12).map((ev) => {
                const passed = ev.verdict === 'PASS_PRODUCTION_GRADE';
                return (
                  <div key={ev.evalId} className="p-3 space-y-1">
                    <div className="flex items-center justify-between gap-2 font-mono">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {ev.actorRealName} · {ev.actionType}
                      </span>
                      <span
                        className={`font-semibold ${
                          passed
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-rose-600 dark:text-rose-400'
                        }`}
                      >
                        {ev.overallScore}/100 ({ev.passedGateCount}/5 gates)
                      </span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-300 leading-relaxed">
                      {ev.summary}
                    </div>
                    {!passed && ev.blockingReasons.length > 0 && (
                      <div className="font-mono text-[11px] text-rose-600 dark:text-rose-400 flex items-start gap-1">
                        <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" aria-hidden="true" />
                        <span>{ev.blockingReasons.join(' ')}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Mandatory Real-Time SFT / DPO Training Dataset Stream */}
          <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
            <div className="px-3.5 py-2.5 bg-slate-50 dark:bg-[#070B14] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-900 dark:text-slate-100">
              <span>Live SFT / DPO Training Tuples ({graphState.trainingTuples.length})</span>
              <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                .ops/realtime-training-dataset.jsonl
              </span>
            </div>
            <div className="max-h-72 overflow-y-auto divide-y divide-slate-200 dark:divide-slate-800 text-xs font-mono tabular-nums">
              {graphState.trainingTuples.slice(0, 12).map((tup) => {
                const isGold = tup.datasetKind === 'SFT_GOLD_TRAJECTORY';
                return (
                  <div key={tup.tupleId} className="p-3 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-cyan-700 dark:text-cyan-300">
                        {tup.tupleId} · {tup.datasetKind} ({tup.packId})
                      </span>
                      <span
                        className={
                          isGold
                            ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                            : 'text-amber-600 dark:text-amber-400 font-semibold'
                        }
                      >
                        reward {tup.rewardScalar > 0 ? '+1.0' : '-1.0'}
                        {tup.synthesizedAntibodyId ? ` · ${tup.synthesizedAntibodyId}` : ''}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-300 font-sans leading-relaxed">
                      {tup.chosenTrajectory}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
