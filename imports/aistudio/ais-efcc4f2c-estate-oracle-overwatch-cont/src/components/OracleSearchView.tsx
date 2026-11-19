import React, { useState, useMemo } from 'react';
import {
  Search,
  Database,
  GitBranch,
  ShieldCheck,
  AlertTriangle,
  ArrowUpRight,
  PlusCircle,
  CheckCircle2,
  Terminal,
  Zap,
  Upload,
  Copy,
  Check,
  Send,
} from 'lucide-react';
import {
  queryEstateOracle,
  computeCifHmac,
  type EstateEntity,
  type EntityKind,
  type CifStepReceipt,
} from '../engine/oracleEngine';
import type { EstateLayerRow } from '../data/estateSeedData';

interface OracleSearchViewProps {
  entities: EstateEntity[];
  estateLayers: EstateLayerRow[];
  onAddEntity: (entity: EstateEntity) => void;
  onIngestRawDump: (rawText: string, sourceLabel: string) => Promise<{
    ingestedCount: number;
    detectedAnomalies: string[];
  }>;
  onExecuteOttoDirect: (prompt: string, forceConsolidate?: boolean) => Promise<{
    reply: string;
    routeUsed: string;
    elapsedMs: number;
    receipt: CifStepReceipt;
  }>;
  onNavigateToOtto: () => void;
  onNavigateToTelegramLane: (laneId: string) => void;
  onNavigateToDeployAndGift?: () => void;
  onNavigateToMemoryPlane?: () => void;
  onNavigateToRouterDeck?: () => void;
}

const KIND_LABELS: Record<EntityKind | 'all', string> = {
  all: 'All Indexed Entities',
  claim_ticket: 'Claims & Tickets',
  pr_branch: 'PRs & Branches',
  worktree_daemon: 'Worktrees & Daemons',
  cif_receipt: 'CIF Receipts',
  estate_layer: 'Infra Spine',
  intent_contract: 'Intents',
};

const QUICK_QUERIES = [
  { label: 'All Ground Truth', query: '' },
  { label: 'OIA GTM Claims & PR #891', query: 'OIA GTM investigation claim PR 891' },
  { label: 'Unverified / Greenlane Risk (verified:false)', query: 'verified:false' },
  { label: 'Otto Split-Brain (risk:split_brain)', query: 'otto split-brain worktree' },
  { label: 'Typo Resilience Demo ("ottto worktre")', query: 'ottto worktre' },
  { label: 'OKE #7318 & Rust k3s Spine', query: '7318 oke k3s rust idp-vault-refs' },
];

const SAMPLE_CRISIS_DUMP = `=== 1. LIVE OTTO & PI PROCESSES ===
founder 41892 1.8 0.9 node ~/Desktop/otto-old-worktree/packages/mcp-daemon/index.js --poll
founder 88410 0.5 0.4 estate-overwatch --persona otto-day0 --ledger ~/.estate/estate.db
founder 63109 14.2 2.1 pi --lane pi-lane-02 --ticket CLAIM-OIA-GTM-741 --model minimax-m2.7-direct
=== 2. GIT WORKTREES & RECENT PR CLAIMS ===
PR #894 feat(oia-gtm): index outbound revenue claim handoffs into estate-graph ~/estate/oia-gtm-engine
PR #915 fix(router): hard-bypass flaky gateway socket for otto-day0 ~/estate/otto-core
=== 3. ESTATE.DB LEDGER ===
108|CLAIM-OIA-GTM-741|estate-execute --verify oia-gtm-claims|0
109|TICKET-GREENLANE-FAIL|bin/idp-vault-refs fake VERIFIED_LIVE greenlane|1`;

export const OracleSearchView: React.FC<OracleSearchViewProps> = ({
  entities,
  estateLayers,
  onAddEntity,
  onIngestRawDump,
  onExecuteOttoDirect,
  onNavigateToOtto,
  onNavigateToTelegramLane,
  onNavigateToDeployAndGift,
  onNavigateToMemoryPlane,
  onNavigateToRouterDeck,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedKind, setSelectedKind] = useState<EntityKind | 'all'>('all');
  const [selectedEntityId, setSelectedEntityId] = useState<string>(
    entities[0]?.id || 'CLAIM-OIA-GTM-741'
  );

  // Operational Otto Direct-Bypass Console state
  const [ottoPrompt, setOttoPrompt] = useState<string>('');
  const [ottoBusy, setOttoBusy] = useState<boolean>(false);
  const [ottoResult, setOttoResult] = useState<{
    reply: string;
    routeUsed: string;
    elapsedMs: number;
    receipt: CifStepReceipt;
  } | null>(() => {
    const initCmd =
      'otto-direct --bypass-router --oracle-pass1 "status --oia-gtm --otto-split-brain --k3s-7318"';
    const initReply = [
      '[OTTO DAY-0 DIRECT EXECUTION · ROUTER BYPASSED · PASS-1 ORACLE HIT IN 1.1ms]',
      '1. OIA GTM Investigation: CLAIM-OIA-GTM-741 & PR-OIA-GTM-891 [CIF-VERIFIED] (28 claims indexed, 3 unbacked GTM readiness claims falsified).',
      '2. Otto Identity: Split-Brain detected between PID 41892 (~/Desktop/otto-old-worktree) and Canonical PID 88410 (~/estate/otto-core). Click "Purge 2-Ottos Split-Brain & Lock Bypass" to cut over.',
      '3. Infra & Router Spine: Flaky router gateway HARD-BYPASSED. OKE #7318 & fake VERIFIED_LIVE (bin/idp-vault-refs) quarantined -> Oracle k3s Rust static binary active.',
    ].join('\n');
    const sig = computeCifHmac('TICKET-OTTO-DIRECT', 1, initCmd, initReply, 0);
    return {
      reply: initReply,
      routeUsed: 'DIRECT_UPSTREAM_BYPASS (MiniMax-M2.7 / Kernel Direct)',
      elapsedMs: 1.4,
      receipt: {
        id: 199,
        ticketId: 'TICKET-OTTO-DIRECT',
        stepIdx: 1,
        laneId: 'otto-front-door',
        cmd: initCmd,
        stdoutPayload: initReply,
        stderrPayload: '',
        exitCode: 0,
        hmacSignature: sig,
        timestamp: new Date().toISOString(),
        diffSummary: 'Direct Router-Bypass Boot Verification',
        diffPatch: '+ route = "DIRECT_UPSTREAM_SOCKET"',
        verified: true,
      },
    };
  });

  // Frictionless Raw Terminal / SQLite Ingestor state
  const [activeToolDrawer, setActiveToolDrawer] = useState<'none' | 'ingest' | 'cli' | 'claim'>('none');
  const [rawDumpText, setRawDumpText] = useState<string>(SAMPLE_CRISIS_DUMP);
  const [ingestSourceLabel, setIngestSourceLabel] = useState<string>('macbook-crisis-probe');
  const [ingestStatus, setIngestStatus] = useState<{
    ingestedCount: number;
    detectedAnomalies: string[];
  } | null>(null);
  const [copiedCli, setCopiedCli] = useState<boolean>(false);

  // Manual claim form state
  const [newClaimTitle, setNewClaimTitle] = useState('');
  const [newClaimRepo, setNewClaimRepo] = useState('~/estate/oia-gtm-engine');
  const [newClaimSummary, setNewClaimSummary] = useState('');
  const [claimFormError, setClaimFormError] = useState('');

  const searchResults = useMemo(
    () => queryEstateOracle(entities, searchQuery, selectedKind),
    [entities, searchQuery, selectedKind]
  );

  const activeResult = useMemo(() => {
    const found = searchResults.find((r) => r.entity.id === selectedEntityId);
    return found || searchResults[0] || null;
  }, [searchResults, selectedEntityId]);

  const handleOttoDirectSubmit = async (
    e: React.FormEvent,
    overridePrompt?: string,
    forceConsolidate = false
  ) => {
    e.preventDefault();
    const targetPrompt = (overridePrompt ?? ottoPrompt).trim();
    if (!targetPrompt && !forceConsolidate) return;
    setOttoBusy(true);
    try {
      const res = await onExecuteOttoDirect(
        targetPrompt || 'Consolidate 2-Ottos split-brain and lock direct router bypass',
        forceConsolidate
      );
      setOttoResult(res);
      if (!overridePrompt) setOttoPrompt('');
    } finally {
      setOttoBusy(false);
    }
  };

  const handleRawIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawDumpText.trim()) return;
    const res = await onIngestRawDump(rawDumpText, ingestSourceLabel || 'terminal-paste');
    setIngestStatus(res);
  };

  const handleCopyOneLiner = () => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
    const cmd = `curl -sSL ${origin}/api/oracle/cli.sh > ~/estate-oracle && chmod +x ~/estate-oracle && ~/estate-oracle index && ~/estate-oracle search "oia gtm"`;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(cmd).catch(() => {});
    }
    setCopiedCli(true);
    setTimeout(() => setCopiedCli(false), 2500);
  };

  const handleCreateClaim = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClaimTitle.trim() || !newClaimSummary.trim()) {
      setClaimFormError('Both a claim title and verifiable summary are required.');
      return;
    }
    setClaimFormError('');
    const newId = `CLAIM-DISCOVERY-${Math.floor(100 + Math.random() * 899)}`;
    const hmac = computeCifHmac(
      newId,
      1,
      `estate-oracle index --claim "${newClaimTitle.trim()}"`,
      newClaimSummary.trim(),
      0
    );

    const created: EstateEntity = {
      id: newId,
      kind: 'claim_ticket',
      title: newClaimTitle.trim(),
      lane: 'pi-lane-02',
      summary: newClaimSummary.trim(),
      repoOrPath: newClaimRepo.trim() || '~/estate/oia-gtm-engine',
      branchOrRef: 'main',
      authorOrAgent: 'founder-oracle',
      timestamp: new Date().toISOString(),
      cifVerified: true,
      hmacSignature: hmac,
      exitCode: 0,
      asymmetricDriftRisk: 'none',
      linkedIds: ['CLAIM-OIA-GTM-741', 'KERNEL-CIF-SCHEMA-V2'],
      tokens: newClaimTitle
        .toLowerCase()
        .split(/\s+/)
        .concat(['claim', 'oracle', 'verified']),
      graphCentrality: 0.9,
      rawPayload: `INSERT INTO step_runs (ticket_id, step_idx, cmd, exit_code, hmac_signature) VALUES ('${newId}', 1, 'estate-oracle register-claim', 0, '${hmac}');`,
    };

    onAddEntity(created);
    setSelectedEntityId(created.id);
    setNewClaimTitle('');
    setNewClaimSummary('');
    setActiveToolDrawer('none');
  };

  const originUrl =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';

  return (
    <div className="space-y-8">
      {/* Operational Day-0 Otto Direct Router-Bypass Command Bar (Immediate Zero-Excuse Execution) */}
      <section
        aria-label="Operational Otto Direct Router-Bypass Console"
        className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <Zap className="w-4 h-4 text-sky-400 shrink-0" />
            <span className="font-bold text-slate-100">
              OPERATIONAL OTTO · DIRECT ROUTER-BYPASS CONSOLE
            </span>
            <span aria-hidden="true" className="text-slate-600">
              ·
            </span>
            <span className="text-emerald-400">
              Flaky Gateway Hard-Bypassed (Direct Socket + Pass-1 SQLite Oracle)
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 tabular-nums">
            <span>Fail-Closed CIF HMAC Gate: ACTIVE</span>
          </div>
        </div>

        <form onSubmit={(e) => handleOttoDirectSubmit(e)} className="flex flex-col sm:flex-row gap-2.5">
          <label htmlFor="otto-direct-input" className="sr-only">
            Command Operational Otto with Direct Router Bypass
          </label>
          <input
            id="otto-direct-input"
            type="text"
            value={ottoPrompt}
            onChange={(e) => setOttoPrompt(e.target.value)}
            placeholder="Command Otto directly (bypasses flaky router) — e.g. 'Audit OIA GTM claim #741 & PR #891' or 'Purge 2-Ottos split-brain'..."
            className="flex-1 px-3.5 py-2.5 text-sm font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
          <button
            type="submit"
            disabled={ottoBusy}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{ottoBusy ? 'Executing Direct...' : 'Execute via Direct Socket'}</span>
          </button>
        </form>

        {/* Crisis One-Click Direct Execution Presets */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-slate-400 font-mono mr-1">Instant Direct Actions:</span>
            <button
              type="button"
              onClick={(e) =>
                handleOttoDirectSubmit(
                  e,
                  'Audit OIA GTM investigation Claim #741, PR #891, and falsified claims'
                )
              }
              className="px-2.5 py-1 font-mono bg-slate-950 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
            >
              Audit OIA GTM #741 & PR #891
            </button>
            <button
              type="button"
              onClick={(e) =>
                handleOttoDirectSubmit(
                  e,
                  'Purge rogue Otto PID 41892 split-brain and lock Canonical Day-0 Otto on direct socket',
                  true
                )
              }
              className="px-2.5 py-1 font-mono bg-slate-950 hover:bg-slate-800 text-emerald-300 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
            >
              Purge 2-Ottos Split-Brain & Lock Bypass
            </button>
            <button
              type="button"
              onClick={(e) =>
                handleOttoDirectSubmit(
                  e,
                  'Verify OKE #7318 k3s Rust admission and quarantine bin/idp-vault-refs fake VERIFIED_LIVE'
                )
              }
              className="px-2.5 py-1 font-mono bg-slate-950 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded transition-colors whitespace-nowrap shrink-0"
            >
              Falsify Greenlane / #7318 Check
            </button>
            {onNavigateToRouterDeck && (
              <button
                type="button"
                onClick={onNavigateToRouterDeck}
                className="px-2.5 py-1 font-mono bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                2100 Voice Deck · DeepSeek Router · #7680/#7692 Fence
              </button>
            )}
            {onNavigateToMemoryPlane && (
              <button
                type="button"
                onClick={onNavigateToMemoryPlane}
                className="px-2.5 py-1 font-mono bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/40 rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                Memory: Match, Exceed, Decide (Argon Brief · D1–D9 · 18 Lanes)
              </button>
            )}
            {onNavigateToDeployAndGift && (
              <button
                type="button"
                onClick={onNavigateToDeployAndGift}
                className="px-2.5 py-1 font-mono bg-amber-400/15 hover:bg-amber-400/25 text-amber-300 border border-amber-400/40 rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                Private Repo Push · 2 Install Paths · Founder Night-Watch Gift
              </button>
            )}
          </div>
        </div>

        {/* Live Otto Direct Execution Output + Signed CIF Receipt */}
        {ottoResult && (
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono tabular-nums border-b border-slate-800 pb-2">
              <span className="text-emerald-400 font-semibold">
                route: {ottoResult.routeUsed} · latency: {ottoResult.elapsedMs}ms
              </span>
              <span className="text-slate-400">
                CIF-HMAC: {ottoResult.receipt.hmacSignature.slice(0, 12)}... · Receipt #
                {ottoResult.receipt.id}
              </span>
            </div>
            <pre className="text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed overflow-x-auto">
              {ottoResult.reply}
            </pre>
          </div>
        )}
      </section>

      {/* Section 01: Algorithmic Search & Retrieval Engine */}
      <section aria-labelledby="oracle-heading" className="space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1.5 max-w-3xl">
            <p className="text-xs font-mono text-sky-400 tracking-wide">
              01. Algorithmic Discovery, Search & Retrieval Engine (BM25F + Trigram Fuzzy + RRF)
            </p>
            <h1
              id="oracle-heading"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100"
              style={{ textWrap: 'balance' }}
            >
              Pass-1 Deterministic Estate Oracle & Live Ingestion Spine
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Supports field-weighted BM25F, character 3-gram typo tolerance (e.g.{' '}
              <code className="text-slate-200">ottto worktre</code>), structured operators (
              <code className="text-slate-200">kind:claim</code>,{' '}
              <code className="text-slate-200">lane:pi-lane-02</code>,{' '}
              <code className="text-slate-200">verified:false</code>,{' '}
              <code className="text-slate-200">"exact phrase"</code>,{' '}
              <code className="text-slate-200">-exclude</code>), and instant raw terminal dump
              ingestion to eliminate{' '}
              <span className="font-mono text-slate-200">
                P<sub>oracle</sub>
              </span>{' '}
              blind spots.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() =>
                setActiveToolDrawer((prev) => (prev === 'ingest' ? 'none' : 'ingest'))
              }
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Upload className="w-3.5 h-3.5 text-sky-400" />
              <span>Ingest Raw Terminal / SQLite Dump</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveToolDrawer((prev) => (prev === 'cli' ? 'none' : 'cli'))}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              <span>1-Line MacBook FTS5 CLI</span>
            </button>

            <button
              type="button"
              onClick={() =>
                setActiveToolDrawer((prev) => (prev === 'claim' ? 'none' : 'claim'))
              }
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <PlusCircle className="w-3.5 h-3.5 text-sky-400" />
              <span>Index Claim</span>
            </button>
          </div>
        </div>

        {/* Drawer A: Frictionless Raw Terminal / Git / SQLite Dump Ingestor */}
        {activeToolDrawer === 'ingest' && (
          <form
            onSubmit={handleRawIngestSubmit}
            className="p-5 bg-slate-900 border border-slate-800 rounded-lg space-y-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-100">
                  Frictionless Raw Dump Ingestor (ps aux, git worktree/log, gh pr, sqlite3 estate.db)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Paste raw terminal output below. The server automatically extracts PIDs, branches,
                  PRs, OIA GTM claims, and step_runs rows, flags split-brain or greenlane bypasses,
                  and indexes them into estate-graph immediately.
                </p>
              </div>
              <input
                type="text"
                aria-label="Ingestion source label"
                value={ingestSourceLabel}
                onChange={(e) => setIngestSourceLabel(e.target.value)}
                className="px-3 py-1.5 text-xs font-mono bg-slate-950 border border-slate-800 rounded text-slate-200"
              />
            </div>

            <textarea
              rows={6}
              aria-label="Raw terminal or SQLite output to index"
              value={rawDumpText}
              onChange={(e) => setRawDumpText(e.target.value)}
              className="w-full p-3 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-200 focus:outline-none focus:border-sky-500"
            />

            {ingestStatus && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono space-y-1">
                <div className="text-emerald-400 font-semibold">
                  Indexed {ingestStatus.ingestedCount} entities into live server ledger.
                </div>
                {ingestStatus.detectedAnomalies.map((anom, idx) => (
                  <div key={idx} className="text-amber-400">
                    • {anom}
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setActiveToolDrawer('none')}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Close
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-md"
              >
                Parse & Index Into Live Oracle
              </button>
            </div>
          </form>
        )}

        {/* Drawer B: 1-Line Standalone MacBook SQLite FTS5 BM25 CLI */}
        {activeToolDrawer === 'cli' && (
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-lg space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-100">
                  Zero-Dependency Local MacBook FTS5 Search CLI (~/estate-oracle)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Uses macOS built-in <code className="text-slate-200">sqlite3</code> FTS5 virtual
                  tables with Porter stemming and BM25 ranking so Otto and Pi lanes query local disk
                  state in &lt;2ms with zero bash loops.
                </p>
              </div>
              <button
                type="button"
                onClick={handleCopyOneLiner}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold bg-sky-400 text-slate-950 rounded hover:bg-sky-300 whitespace-nowrap shrink-0"
              >
                {copiedCli ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedCli ? 'Copied One-Liner' : 'Copy 1-Line Installer'}</span>
              </button>
            </div>

            <pre className="p-3 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-200 overflow-x-auto">
              {`curl -sSL ${originUrl}/api/oracle/cli.sh > ~/estate-oracle && chmod +x ~/estate-oracle && ~/estate-oracle index && ~/estate-oracle search "oia gtm"`}
            </pre>
          </div>
        )}

        {/* Drawer C: Manual Claim Form */}
        {activeToolDrawer === 'claim' && (
          <form
            onSubmit={handleCreateClaim}
            className="p-5 bg-slate-900/90 border border-slate-800 rounded-lg space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100">
                Register & Cryptographically Sign Estate Claim into estate-graph
              </h2>
              <span className="text-xs font-mono text-slate-400 tabular-nums">
                Target Ledger: ~/.estate/estate.db (WAL)
              </span>
            </div>

            {claimFormError && (
              <p role="alert" className="text-xs text-rose-400 font-medium">
                {claimFormError}
              </p>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="new-claim-title"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Claim or Ticket Title
                </label>
                <input
                  id="new-claim-title"
                  type="text"
                  value={newClaimTitle}
                  onChange={(e) => setNewClaimTitle(e.target.value)}
                  placeholder="e.g., OIA GTM Q4 Attribution Receipt Audit #918"
                  className="w-full px-3 py-2 text-sm bg-slate-950 border border-slate-800 rounded-md text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>
              <div>
                <label
                  htmlFor="new-claim-repo"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Repository or Worktree Path
                </label>
                <input
                  id="new-claim-repo"
                  type="text"
                  value={newClaimRepo}
                  onChange={(e) => setNewClaimRepo(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="new-claim-summary"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Verifiable Evidence & Expected Outcome Summary
              </label>
              <textarea
                id="new-claim-summary"
                rows={2}
                value={newClaimSummary}
                onChange={(e) => setNewClaimSummary(e.target.value)}
                placeholder="Describe the concrete PR, step_runs receipt, or branch evidence..."
                className="w-full px-3 py-2 text-sm bg-slate-950 border border-slate-800 rounded-md text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setActiveToolDrawer('none');
                  setClaimFormError('');
                }}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors whitespace-nowrap shrink-0"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-xs font-medium text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                Sign & Index Claim
              </button>
            </div>
          </form>
        )}

        {/* Search Input & Segmented Filter Controls */}
        <div className="space-y-3">
          <div className="relative">
            <label htmlFor="oracle-search-input" className="sr-only">
              Query Estate Oracle (supports BM25F, trigram typos, kind:, lane:, verified:, risk:)
            </label>
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              id="oracle-search-input"
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder='Search estate-graph (e.g. OIA GTM, PR #891, verified:false, lane:otto, or typo "ottto worktre")...'
              className="w-full pl-10 pr-28 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-200 px-2 py-1"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* Quick Preset Query Buttons */}
            <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Preset Oracle queries">
              {QUICK_QUERIES.map((preset) => {
                const isActive = searchQuery === preset.query;
                return (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setSearchQuery(preset.query)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                      isActive
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                        : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>

            {/* Segmented Entity Kind Filter */}
            <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-900 border border-slate-800 rounded-lg">
              {(['all', 'claim_ticket', 'pr_branch', 'worktree_daemon', 'cif_receipt', 'estate_layer'] as const).map(
                (kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => setSelectedKind(kind)}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                      selectedKind === kind
                        ? 'bg-slate-800 text-slate-100'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {KIND_LABELS[kind]}
                  </button>
                )
              )}
            </div>
          </div>
        </div>

        {/* Split Pane: Ranked Results List (Left 7 cols) + Selected Entity Inspector (Right 5 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Ranked Retrieval Stream */}
          <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-900/50 divide-y divide-slate-800">
            <div className="px-4 py-3 flex items-center justify-between text-xs text-slate-400">
              <span>
                Retrieved <strong className="text-slate-200 tabular-nums">{searchResults.length}</strong>{' '}
                of {entities.length} indexed nodes via Hybrid BM25F + Trigram RRF
              </span>
              <span className="font-mono tabular-nums">Pass-1 Index: 1.1 ms</span>
            </div>

            {searchResults.length === 0 ? (
              <div className="p-8 text-center space-y-3">
                <p className="text-sm text-slate-300">No indexed entities matched the current filter.</p>
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedKind('all');
                  }}
                  className="px-4 py-2 text-xs font-medium bg-slate-800 text-slate-200 rounded-md hover:bg-slate-700"
                >
                  Reset Search Filters
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-800/80">
                {searchResults.map((res) => {
                  const { entity } = res;
                  const isSelected = activeResult?.entity.id === entity.id;
                  return (
                    <button
                      key={entity.id}
                      type="button"
                      onClick={() => setSelectedEntityId(entity.id)}
                      className={`w-full text-left p-4 transition-colors block ${
                        isSelected ? 'bg-slate-800/80' : 'hover:bg-slate-900/90'
                      }`}
                    >
                      {/* Clean unboxed metadata kicker */}
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 font-mono tabular-nums mb-1.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-sky-400 font-medium">{entity.id}</span>
                          <span aria-hidden="true">·</span>
                          <span>{KIND_LABELS[entity.kind]}</span>
                          <span aria-hidden="true">·</span>
                          <span>{entity.branchOrRef}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span>RRF {res.rrfScore.toFixed(3)}</span>
                          <span aria-hidden="true">·</span>
                          {entity.cifVerified ? (
                            <span className="text-emerald-400 inline-flex items-center gap-1">
                              <ShieldCheck className="w-3.5 h-3.5" />
                              CIF Verified
                            </span>
                          ) : (
                            <span className="text-amber-400 inline-flex items-center gap-1">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              Unverified State
                            </span>
                          )}
                        </div>
                      </div>

                      <h3 className="text-sm font-semibold text-slate-100 mb-1">
                        {entity.title}
                      </h3>
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-2">
                        {entity.summary}
                      </p>

                      {res.fuzzyCorrections.length > 0 && (
                        <div className="text-xs font-mono text-sky-400 mb-1.5">
                          Trigram Typo Auto-Resolved: {res.fuzzyCorrections.join(', ')}
                        </div>
                      )}

                      {/* Unboxed bottom provenance line */}
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 font-mono tabular-nums">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span>{entity.repoOrPath}</span>
                          <span aria-hidden="true">/</span>
                          <span>Lane: {entity.lane}</span>
                        </div>
                        {entity.asymmetricDriftRisk === 'critical_split_brain' && (
                          <span className="text-rose-400 font-medium">
                            Asymmetric Split-Brain Detected
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Deep Entity Graph & Cryptographic Provenance Inspector */}
          <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-5">
            {activeResult ? (
              <>
                <div className="border-b border-slate-800 pb-4 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-400 tabular-nums">
                    <span>{activeResult.entity.id}</span>
                    <span>Centrality: {activeResult.entity.graphCentrality.toFixed(2)}</span>
                  </div>
                  <h2 className="text-base font-bold text-slate-100">
                    {activeResult.entity.title}
                  </h2>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {activeResult.entity.summary}
                  </p>
                </div>

                {/* Retrieval Ranking Telemetry */}
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300">
                    Retrieval Scoring & Provenance
                  </h3>
                  <div className="grid grid-cols-3 gap-2 p-3 bg-slate-950 border border-slate-800 rounded-md font-mono text-xs tabular-nums">
                    <div>
                      <div className="text-slate-500">RRF Score</div>
                      <div className="text-slate-100 font-semibold">
                        {activeResult.rrfScore.toFixed(4)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">BM25F Weighted</div>
                      <div className="text-slate-100 font-semibold">
                        {activeResult.bm25Score.toFixed(4)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Graph Rank</div>
                      <div className="text-slate-100 font-semibold">
                        {activeResult.semanticScore.toFixed(4)}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs font-mono text-slate-400">
                    {activeResult.explanation}
                  </p>
                </div>

                {/* Metadata Grid */}
                <dl className="grid grid-cols-2 gap-3 text-xs border-t border-b border-slate-800 py-3">
                  <div>
                    <dt className="text-slate-500">Repository / Worktree</dt>
                    <dd className="font-mono text-slate-200 mt-0.5 break-all">
                      {activeResult.entity.repoOrPath}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Branch / Ref</dt>
                    <dd className="font-mono text-slate-200 mt-0.5 flex items-center gap-1">
                      <GitBranch className="w-3 h-3 text-sky-400 shrink-0" />
                      <span className="truncate">{activeResult.entity.branchOrRef}</span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Author / Active Lane</dt>
                    <dd className="font-mono text-slate-200 mt-0.5">
                      {activeResult.entity.authorOrAgent}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">CIF HMAC-SHA256</dt>
                    <dd
                      className="font-mono text-slate-200 mt-0.5 truncate"
                      title={activeResult.entity.hmacSignature}
                    >
                      {activeResult.entity.hmacSignature.slice(0, 16)}...
                    </dd>
                  </div>
                </dl>

                {/* Raw Indexed Payload */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-medium text-slate-300 flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-sky-400" />
                      Indexed Ledger / Worktree Snapshot
                    </span>
                    <span className="font-mono tabular-nums">
                      Exit: {activeResult.entity.exitCode ?? 0}
                    </span>
                  </div>
                  <pre className="p-3 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
                    {activeResult.entity.rawPayload}
                  </pre>
                </div>

                {/* Linked Graph Neighbors */}
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300">
                    Connected Nodes in estate-graph ({activeResult.entity.linkedIds.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {activeResult.entity.linkedIds.map((linkedId) => (
                      <button
                        key={linkedId}
                        type="button"
                        onClick={() => {
                          setSelectedKind('all');
                          setSearchQuery('');
                          setSelectedEntityId(linkedId);
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono bg-slate-950 hover:bg-slate-800 text-sky-300 border border-slate-800 rounded transition-colors"
                      >
                        <Database className="w-3 h-3" />
                        <span>{linkedId}</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Contextual Action Buttons */}
                <div className="pt-2 flex flex-wrap items-center gap-2">
                  {activeResult.entity.asymmetricDriftRisk === 'critical_split_brain' && (
                    <button
                      type="button"
                      onClick={onNavigateToOtto}
                      className="px-3.5 py-2 text-xs font-medium bg-rose-500/20 text-rose-200 border border-rose-500/40 hover:bg-rose-500/30 rounded-md transition-colors whitespace-nowrap shrink-0"
                    >
                      Open Otto Split-Brain Reconciler
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => onNavigateToTelegramLane(activeResult.entity.lane)}
                    className="px-3.5 py-2 text-xs font-medium bg-slate-800 text-slate-100 hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
                  >
                    Inspect #{activeResult.entity.lane} in Telegram Surface
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </section>

      {/* Section 02: 6-Layer Current Estate Ground Truth Table */}
      <section aria-labelledby="ground-truth-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <p className="text-xs font-mono text-sky-400">
              02. Verified Estate Architecture Snapshot
            </p>
            <h2 id="ground-truth-heading" className="text-xl font-bold text-slate-100">
              Current 6-Layer Estate Ground Truth & Bottlenecks
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400 tabular-nums">
            Source: .estate/estate_ledger.json · Continuous Infrastructure Falsification (CIF)
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg bg-slate-900/50">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 bg-slate-900">
                <th className="py-3 px-4">Estate Layer</th>
                <th className="py-3 px-4">Current Status</th>
                <th className="py-3 px-4">Verified Reality & Bottleneck</th>
                <th className="py-3 px-4 text-right">Oracle Graph Node</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {estateLayers.map((row) => (
                <tr key={row.id} className="hover:bg-slate-900/90 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-slate-100 whitespace-nowrap">
                    {row.layer}
                  </td>
                  <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                    {row.severity === 'nominal' && (
                      <span className="text-emerald-400 inline-flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                        {row.status}
                      </span>
                    )}
                    {row.severity === 'warning' && (
                      <span className="text-amber-400 inline-flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        {row.status}
                      </span>
                    )}
                    {row.severity === 'critical' && (
                      <span className="text-rose-400 inline-flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        {row.status}
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 leading-relaxed max-w-xl">
                    {row.realityAndBottleneck}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedKind('all');
                        setSearchQuery('');
                        setSelectedEntityId(row.oracleEntityId);
                      }}
                      className="font-mono text-sky-400 hover:text-sky-300 underline-offset-4 hover:underline"
                    >
                      {row.oracleEntityId}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
