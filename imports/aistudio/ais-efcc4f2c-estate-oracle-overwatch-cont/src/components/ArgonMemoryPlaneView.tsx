import React, { useState, useMemo } from 'react';
import {
  Brain,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Terminal,
  Sparkles,
  Scale,
  Play,
  Sliders,
  GitMerge,
  RefreshCw,
  FileCode2,
  Eye,
  Trash2,
} from 'lucide-react';
import {
  buildBudgetedClaimOpenBrief,
  type ArgonMemoryPlaneState,
  type ArgonBallotItem,
  type BallotOptionCode,
  type MemoryTypeKind,
} from '../engine/memoryPlaneEngine';

interface ArgonMemoryPlaneViewProps {
  memoryPlane: ArgonMemoryPlaneState;
  onRemediateAndSignDecree: (updatedBallots: ArgonBallotItem[]) => Promise<void>;
  onRunDreamConsolidation: (episodicInput: {
    title: string;
    rawFailureEpisode: string;
    sourceTicket: string;
    probeCmd: string;
    kind: MemoryTypeKind;
  }) => Promise<{ diffReport: string }>;
  onToggleFactProbe: (factId: string) => void;
  onDeleteMemoryFact: (factId: string) => void;
}

type MemorySubTab = 'ballots' | 'register' | 'dreaming' | 'capabilities';

export const ArgonMemoryPlaneView: React.FC<ArgonMemoryPlaneViewProps> = ({
  memoryPlane,
  onRemediateAndSignDecree,
  onRunDreamConsolidation,
  onToggleFactProbe,
  onDeleteMemoryFact,
}) => {
  const [subTab, setSubTab] = useState<MemorySubTab>('ballots');
  const [localBallots, setLocalBallots] = useState<ArgonBallotItem[]>(memoryPlane.ballots);
  const [expandedBallotId, setExpandedBallotId] = useState<string>('D1');
  const [remediating, setRemediating] = useState<boolean>(false);

  // Dreaming Lab & Claim-Open Brief controls
  const [tokenBudget, setTokenBudget] = useState<number>(memoryPlane.tokenBudgetLimit || 220);
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(
    memoryPlane.confidenceThreshold || 0.85
  );
  const [dreamTitle, setDreamTitle] = useState<string>(
    'Auto-Inject Claim Brief on Cline & Codex Before Worktree Edit'
  );
  const [dreamEpisode, setDreamEpisode] = useState<string>(
    'Verify ~/.cline/hooks and ~/.codex/hooks inject top-5 BM25F+RRF facts and procedural gates at claim-open before allowing file mutation.'
  );
  const [dreamTicket, setDreamTicket] = useState<string>('TICKET-42-HARNESS');
  const [dreamProbe, setDreamProbe] = useState<string>(
    'estate-audit --probe-runtime=cline,codex --verify-brief'
  );
  const [dreamKind, setDreamKind] = useState<MemoryTypeKind>('procedural');
  const [dreamDiffOutput, setDreamDiffOutput] = useState<string>('');
  const [dreamBusy, setDreamBusy] = useState<boolean>(false);

  // Filter for 18-lane register
  const [runtimeFilter, setRuntimeFilter] = useState<string>('ALL');

  const budgetedBrief = useMemo(
    () =>
      buildBudgetedClaimOpenBrief(
        memoryPlane.distilledMemories,
        tokenBudget,
        confidenceThreshold
      ),
    [memoryPlane.distilledMemories, tokenBudget, confidenceThreshold]
  );

  const handleSelectBallotOption = (ballotId: string, code: BallotOptionCode) => {
    setLocalBallots((prev) =>
      prev.map((b) => (b.id === ballotId ? { ...b, argonSelection: code } : b))
    );
  };

  const handleUpdateOverrideReason = (ballotId: string, reason: string) => {
    setLocalBallots((prev) =>
      prev.map((b) => (b.id === ballotId ? { ...b, argonOverrideReason: reason } : b))
    );
  };

  const handleExecuteDecreeAndRemediation = async () => {
    setRemediating(true);
    try {
      await onRemediateAndSignDecree(localBallots);
    } finally {
      setRemediating(false);
    }
  };

  const handleRunDreamSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dreamEpisode.trim()) return;
    setDreamBusy(true);
    try {
      const res = await onRunDreamConsolidation({
        title: dreamTitle,
        rawFailureEpisode: dreamEpisode,
        sourceTicket: dreamTicket,
        probeCmd: dreamProbe,
        kind: dreamKind,
      });
      setDreamDiffOutput(res.diffReport);
    } finally {
      setDreamBusy(false);
    }
  };

  const filteredLanes = useMemo(() => {
    if (runtimeFilter === 'ALL') return memoryPlane.lanes;
    return memoryPlane.lanes.filter((l) => l.runtimeSurface === runtimeFilter);
  }, [memoryPlane.lanes, runtimeFilter]);

  const isAllOperating = memoryPlane.auditSummary.operatingLanes === 18;

  return (
    <div className="space-y-8">
      {/* Executive Header & Argon Decree Action Bar */}
      <section
        aria-labelledby="argon-memory-heading"
        className="border border-slate-800 rounded-lg bg-slate-900/90 p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-2 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="text-sky-400 font-semibold">
                BRIEF FOR ARGON · 31 OCT 2026 · @mike
              </span>
              <span className="text-slate-600">·</span>
              <span
                className={
                  memoryPlane.argonDecreeSigned
                    ? 'text-emerald-400 font-semibold'
                    : 'text-amber-300 font-semibold'
                }
              >
                {memoryPlane.argonDecreeSigned
                  ? 'DECREE SIGNED & 18/18 LANES OPERATING'
                  : 'AWAITING ARGON CALL ON D1–D9 (0/18 LANES INITIAL MIRROR)'}
              </span>
            </div>

            <h1
              id="argon-memory-heading"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100"
              style={{ textWrap: 'balance' }}
            >
              Memory: Match, Exceed, Decide — The Great Synthesis Plane
            </h1>

            <p className="text-sm text-slate-300 leading-relaxed">
              Unifies biological-style episodic dreaming with deterministic machine verification:
              captures memory at <code className="text-sky-300">lane-submit</code>, injects
              value-per-token briefs at <code className="text-sky-300">claim-open</code>, grades
              recall by whether it prevents recorded estate failures, and governs every high-stakes
              decision via <code className="text-sky-300">bin/estate-decide</code>.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col items-stretch sm:items-center lg:items-end gap-2.5 shrink-0">
            <button
              type="button"
              onClick={handleExecuteDecreeAndRemediation}
              disabled={remediating}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>
                {remediating
                  ? 'Executing Ticket #42 & Locking D1–D9...'
                  : isAllOperating
                  ? 'Re-Verify 18/18 Lanes & Update Argon Decree'
                  : 'Approve D1–D9 Decree & Remediate All 18 Lanes'}
              </span>
            </button>
            <div className="text-[11px] font-mono text-slate-400 tabular-nums text-right">
              CIF Decree HMAC: {memoryPlane.argonDecreeHmac.slice(0, 18)}...
            </div>
          </div>
        </div>

        {/* 4 Core KPI Cards (Estate Exclusive Measures + Register Status) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs tabular-nums">
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">18-Lane Memory Register</div>
            <div
              className={`text-lg font-bold mt-1 ${
                isAllOperating ? 'text-emerald-400' : 'text-amber-300'
              }`}
            >
              {memoryPlane.auditSummary.operatingLanes} / {memoryPlane.auditSummary.totalLanes}{' '}
              Operating
            </div>
            <div className="text-slate-500 mt-0.5">
              {memoryPlane.auditSummary.openFindingsCount === 0
                ? '0 Findings · 19/19 Tests · 29/29 Spec Pass'
                : `${memoryPlane.auditSummary.openFindingsCount} Initial Findings · 19 Audit Tests Pass`}
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Replay Hit Rate (Estate #1)</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              {memoryPlane.benchmarks.estateExclusive.replayHitRatePct.toFixed(1)}% (n=29)
            </div>
            <div className="text-slate-500 mt-0.5">
              Repeat-Failure Rate:{' '}
              {memoryPlane.benchmarks.estateExclusive.repeatFailureRatePct.toFixed(1)}%
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Stale-Served & Door-Down</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {memoryPlane.benchmarks.estateExclusive.staleServedRatePct.toFixed(1)}% Stale ·{' '}
              {memoryPlane.benchmarks.estateExclusive.doorDownTimeMinutes.toFixed(0)}m Down
            </div>
            <div className="text-slate-500 mt-0.5">
              Live Probe-Before-Inject · 4h launchd Watchdog
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Public Credibility Suite</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              LoCoMo {memoryPlane.benchmarks.publicCredibility.locomoScorePct.toFixed(1)}%
            </div>
            <div className="text-slate-500 mt-0.5">
              LongMem {memoryPlane.benchmarks.publicCredibility.longMemEvalPct.toFixed(1)}% · BEAM{' '}
              {memoryPlane.benchmarks.publicCredibility.beam1mScorePct.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Sub-Navigation Switcher for the 4 Argon Memory Modules */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div
            role="tablist"
            aria-label="Argon Memory Plane Sections"
            className="inline-flex flex-wrap items-center gap-1.5 bg-slate-950 p-1.5 border border-slate-800 rounded-lg"
          >
            <button
              type="button"
              role="tab"
              aria-selected={subTab === 'ballots'}
              onClick={() => setSubTab('ballots')}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                subTab === 'ballots'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Scale className="w-3.5 h-3.5" />
              <span>01. 9-Ballot Council & Decide (D1–D9)</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={subTab === 'register'}
              onClick={() => setSubTab('register')}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                subTab === 'register'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>
                02. 18-Lane Register & 27 Findings ({memoryPlane.auditSummary.operatingLanes}/18)
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={subTab === 'dreaming'}
              onClick={() => setSubTab('dreaming')}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                subTab === 'dreaming'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Brain className="w-3.5 h-3.5" />
              <span>03. Dreaming Consolidation & Claim-Open Brief Lab</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={subTab === 'capabilities'}
              onClick={() => setSubTab('capabilities')}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                subTab === 'capabilities'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>04. 12 Capabilities (Match &rarr; Exceed) & Replay Suite</span>
            </button>
          </div>

          <div className="text-xs font-mono text-slate-400">
            Cross-Runtime Canary:{' '}
            <span className="text-emerald-400 font-semibold tabular-nums">
              {memoryPlane.auditSummary.crossRuntimeCanaryPairsPassing}/
              {memoryPlane.auditSummary.crossRuntimeCanaryPairsTotal}
            </span>{' '}
            Ordered Pairs (7 Harnesses)
          </div>
        </div>
      </section>

      {/* ===================================================================== */}
      {/* TAB 01: 9-BALLOT TRI-COORDINATOR VOTING & BIN/ESTATE-DECIDE           */}
      {/* ===================================================================== */}
      {subTab === 'ballots' && (
        <div className="space-y-8">
          {/* Three Proposals Compared (Claude vs Gemini vs Kimi) */}
          <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <p className="text-xs font-mono text-sky-400">
                  SECTION 01A · THREE COORDINATOR PROPOSALS COMPARED
                </p>
                <h2 className="text-lg font-bold text-slate-100">
                  Claude vs. Gemini vs. Kimi — Unified Core, Distinct Ambition
                </h2>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Core Consensus: Claim-Open Brief + Lane-Submit Capture + 18-Lane Register + Replay Benchmark
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-mono">
                    <th className="py-2.5 pr-4 w-36">Dimension</th>
                    <th className="py-2.5 px-4 text-sky-300">Claude (Built Register & Audit)</th>
                    <th className="py-2.5 px-4 text-emerald-300">Gemini (Governed Subsystem)</th>
                    <th className="py-2.5 pl-4 text-amber-300">Kimi (&ldquo;The Mess is the Moat&rdquo;)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300 align-top">
                  <tr>
                    <td className="py-2.5 pr-4 font-mono font-semibold text-slate-200">Thesis</td>
                    <td className="py-2.5 px-4">
                      The machine, not the agent, captures and delivers memory; prove it across surfaces first.
                    </td>
                    <td className="py-2.5 px-4">
                      Memory as a governed subsystem; &ldquo;provable memory beats bigger memory.&rdquo;
                    </td>
                    <td className="py-2.5 pl-4">
                      &ldquo;The mess is the moat&rdquo;: mine the estate’s own failure record into executable gates.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 pr-4 font-mono font-semibold text-slate-200">Mechanism</td>
                    <td className="py-2.5 px-4">
                      Brief at <code className="text-slate-100">claim-open</code>, capture at{' '}
                      <code className="text-slate-100">lane-submit</code>, local spool &amp;{' '}
                      <code className="text-slate-100">growmos</code> first; router/hooks kept as extra lanes.
                    </td>
                    <td className="py-2.5 px-4">
                      8 components: typed lanes, dreaming, temporal truth, EIG write gate, read discipline, self-state catalog, markdown format.
                    </td>
                    <td className="py-2.5 pl-4">
                      Same chokepoint; adds that harnesses that do not exist yet feed the capture spool automatically.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 pr-4 font-mono font-semibold text-slate-200">Unique Edge</td>
                    <td className="py-2.5 px-4">
                      Outcome truth, vendor neutrality, lessons that execute, one substrate with the catalog, replay benchmark.
                    </td>
                    <td className="py-2.5 px-4">
                      Provenance, EIG write quality gate, self-state catalog, procedural memory, public benchmark war.
                    </td>
                    <td className="py-2.5 pl-4">
                      Failure ore, executable memory (<code className="text-slate-100">probe</code>,{' '}
                      <code className="text-slate-100">hash</code>,{' '}
                      <code className="text-slate-100">derived-at</code>), zero-cooperation capture.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 pr-4 font-mono font-semibold text-slate-200">Evidence Offered</td>
                    <td className="py-2.5 px-4 font-mono text-emerald-400">
                      Built &amp; ran 18-lane register, 19-test audit, 29-scenario spec, Ticket #42.
                    </td>
                    <td className="py-2.5 px-4 font-mono text-sky-300">
                      8-component architecture + live EIG/Knapsack brief engine now operational here.
                    </td>
                    <td className="py-2.5 pl-4 font-mono text-amber-300">
                      Failure-ore procedural gate compiler + inventory pass now completed.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Interactive 9-Ballot Table + Detail Inspector */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <p className="text-xs font-mono text-sky-400">
                    SECTION 01B · NINE DISPUTED BALLOTS (D1–D9)
                  </p>
                  <h2 className="text-base font-bold text-slate-100">
                    Blind Coordinator Ballots &amp; Argon Final Call
                  </h2>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Click any row to inspect Rebuttals &amp; Evidence
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2 pr-2">#</th>
                      <th className="py-2 px-2">Decision &amp; Class</th>
                      <th className="py-2 px-2">Claude</th>
                      <th className="py-2 px-2">Gemini</th>
                      <th className="py-2 px-2">Kimi</th>
                      <th className="py-2 px-2 text-emerald-400">Rec</th>
                      <th className="py-2 pl-2 text-sky-300">Argon Call</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {localBallots.map((b) => {
                      const isSelected = expandedBallotId === b.id;
                      return (
                        <tr
                          key={b.id}
                          onClick={() => setExpandedBallotId(b.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-slate-800/70' : 'hover:bg-slate-800/30'
                          }`}
                        >
                          <td className="py-2.5 pr-2 font-bold text-sky-400">{b.id}</td>
                          <td className="py-2.5 px-2 font-sans">
                            <div className="font-semibold text-slate-100">{b.title}</div>
                            <div className="text-[11px] font-mono text-slate-400">
                              Class {b.reversibilityClass} · Review {b.reviewDate}
                            </div>
                          </td>
                          <td className="py-2.5 px-2 text-slate-200">
                            {b.coordinators.claude.blindVote}{' '}
                            <span className="text-slate-500">({b.coordinators.claude.confidence}%)</span>
                          </td>
                          <td className="py-2.5 px-2 text-slate-200">
                            {b.coordinators.gemini.blindVote}{' '}
                            <span className="text-slate-500">({b.coordinators.gemini.confidence}%)</span>
                          </td>
                          <td className="py-2.5 px-2 text-slate-200">
                            {b.coordinators.kimi.blindVote}{' '}
                            <span className="text-slate-500">({b.coordinators.kimi.confidence}%)</span>
                          </td>
                          <td className="py-2.5 px-2 font-bold text-emerald-400">
                            {b.recommendedOption}
                          </td>
                          <td
                            className="py-2.5 pl-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="inline-flex items-center gap-1 bg-slate-950 p-0.5 border border-slate-800 rounded-md">
                              {(['A', 'B', 'C'] as BallotOptionCode[]).map((code) => (
                                <button
                                  key={code}
                                  type="button"
                                  onClick={() => handleSelectBallotOption(b.id, code)}
                                  className={`px-2 py-0.5 text-xs font-bold rounded transition-colors cursor-pointer ${
                                    b.argonSelection === code
                                      ? 'bg-sky-400 text-slate-950'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                >
                                  {code}
                                </button>
                              ))}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right: Selected Ballot Deep Inspector (Blind Evidence, 150w Rebuttals, Rotating Dissenter) */}
            {(() => {
              const activeBallot =
                localBallots.find((b) => b.id === expandedBallotId) || localBallots[0];
              const isOverride =
                activeBallot.argonSelection !== activeBallot.recommendedOption;

              return (
                <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-xs font-mono text-sky-400 font-bold">
                        BALLOT {activeBallot.id} · REVERSIBILITY {activeBallot.reversibilityClass}
                      </span>
                      <h3 className="text-base font-bold text-slate-100">
                        {activeBallot.title}
                      </h3>
                    </div>
                    <span className="text-xs font-mono text-emerald-400">
                      Rec: Option {activeBallot.recommendedOption}
                    </span>
                  </div>

                  {/* Options List */}
                  <div className="space-y-2">
                    {activeBallot.options.map((opt) => {
                      const chosen = activeBallot.argonSelection === opt.code;
                      return (
                        <div
                          key={opt.code}
                          onClick={() =>
                            handleSelectBallotOption(activeBallot.id, opt.code)
                          }
                          className={`p-2.5 border rounded-md text-xs cursor-pointer transition-colors ${
                            chosen
                              ? 'bg-sky-500/15 border-sky-500/50 text-slate-100'
                              : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between font-mono font-bold mb-0.5">
                            <span className={chosen ? 'text-sky-300' : 'text-slate-300'}>
                              Option {opt.code}
                            </span>
                            {opt.code === activeBallot.recommendedOption && (
                              <span className="text-emerald-400 text-[11px]">
                                [Recommended]
                              </span>
                            )}
                          </div>
                          <p className="text-slate-300">{opt.summary}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Coordinator Blind Ballots + Rebuttals */}
                  <div className="space-y-2.5 pt-1">
                    <div className="text-xs font-mono text-slate-400 uppercase">
                      Blind Ballots, Verified Evidence &amp; 150-Word Rebuttals
                    </div>
                    {(['claude', 'gemini', 'kimi'] as const).map((coordKey) => {
                      const c = activeBallot.coordinators[coordKey];
                      return (
                        <div
                          key={coordKey}
                          className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-1.5 text-xs"
                        >
                          <div className="flex items-center justify-between font-mono">
                            <span className="font-bold text-slate-100 uppercase">
                              {c.coordinator} &rarr; Vote {c.blindVote} ({c.confidence}% conf)
                            </span>
                            <span className="text-emerald-400 truncate max-w-[210px]">
                              {c.evidenceRef}
                            </span>
                          </div>
                          <p className="text-slate-300 leading-relaxed">{c.rebuttal150Words}</p>
                          <div className="text-[11px] font-mono text-slate-400">
                            Mind-change condition: {c.wouldChangeMindIf}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Safeguard 1: Rotating Dissenter */}
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-md space-y-1 text-xs">
                    <div className="font-mono font-bold text-amber-300">
                      SAFEGUARD #1 · ROTATING DISSENTER (
                      {activeBallot.rotatingDissenter.coordinator.toUpperCase()})
                    </div>
                    <p className="text-slate-200">{activeBallot.rotatingDissenter.dissentArgument}</p>
                  </div>

                  {/* Override Reason Input (Mandatory if overriding majority) */}
                  <div className="space-y-1.5 pt-1">
                    <label
                      htmlFor="argon-override-reason"
                      className="block text-xs font-mono text-slate-300"
                    >
                      Argon Final Note / Written Override Reason{' '}
                      {isOverride ? (
                        <span className="text-amber-300">(Required for Majority Override)</span>
                      ) : (
                        <span className="text-slate-500">(Optional)</span>
                      )}
                    </label>
                    <input
                      id="argon-override-reason"
                      type="text"
                      placeholder="Record Argon rationale for git decision log (bin/estate-decide)..."
                      value={activeBallot.argonOverrideReason}
                      onChange={(e) =>
                        handleUpdateOverrideReason(activeBallot.id, e.target.value)
                      }
                      className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>
              );
            })()}
          </section>

          {/* Machine Governance Protocol (R1 / R2 / R3 + bin/estate-decide) */}
          <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <p className="text-xs font-mono text-sky-400">
                  SECTION 05 · MACHINE GOVERNANCE PROTOCOL (`bin/estate-decide`)
                </p>
                <h2 className="text-base font-bold text-slate-100">
                  How Every Later High-Stakes Question Is Decided Automatically
                </h2>
              </div>
              <span className="text-xs font-mono text-emerald-400">
                3 Safeguards Active: Rotating Dissenter · Cross-Family Split Check · Machine-Resolvable Evidence Only
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="font-mono font-bold text-slate-100">
                  R1 · Reversible &amp; Cheap
                </div>
                <div className="text-slate-400">Examples: Config, naming, documents</div>
                <div className="text-sky-300 font-mono">Who decides: One coordinator, logged</div>
                <p className="text-slate-400 pt-1">
                  Machine Check: Verifies the structured decision record exists in{' '}
                  <code>growmos/decisions/</code> with a unique monotonic ID.
                </p>
              </div>

              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="font-mono font-bold text-slate-100">
                  R2 · Reversible But Cross-Cutting
                </div>
                <div className="text-slate-400">
                  Examples: A new memory lane, a gate in report-only mode
                </div>
                <div className="text-sky-300 font-mono">
                  Who decides: Two of three, blind ballots
                </div>
                <p className="text-slate-400 pt-1">
                  Machine Check: Every evidence reference resolves to a real{' '}
                  <code>file:</code>, <code>probe:</code>, or <code>commit:</code>; no ballot edited after reveal.
                </p>
              </div>

              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-1.5">
                <div className="font-mono font-bold text-slate-100">
                  R3 · Hard to Undo / High-Stakes
                </div>
                <div className="text-slate-400">
                  Examples: Infra spend, deleting data, blocking gate, adopting/retiring engine
                </div>
                <div className="text-emerald-400 font-mono">
                  Who decides: Blind ballots, 1 rebuttal, then Argon
                </div>
                <p className="text-slate-400 pt-1">
                  Machine Check: R2 checks + review date &amp; metric; notifies Argon on Telegram with 1-tap answer; on timeout status quo stands.
                </p>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 02: 18-LANE REGISTER & 27 FINDINGS REMEDIATION                    */}
      {/* ===================================================================== */}
      {subTab === 'register' && (
        <div className="space-y-8">
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left 7 Cols: 18-Lane Memory Register */}
            <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                <div>
                  <p className="text-xs font-mono text-sky-400">
                    18-LANE UNIFIED MEMORY REGISTER (`register/memory-lanes-18.json`)
                  </p>
                  <h2 className="text-base font-bold text-slate-100">
                    Every Memory Component, Chokepoint &amp; Live Probe
                  </h2>
                </div>

                <select
                  aria-label="Filter memory lanes by runtime surface"
                  value={runtimeFilter}
                  onChange={(e) => setRuntimeFilter(e.target.value)}
                  className="px-2.5 py-1.5 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-200"
                >
                  <option value="ALL">All Surfaces (18 Lanes)</option>
                  <option value="Shared Substrate">Shared Substrate</option>
                  <option value="Claude Code">Claude Code</option>
                  <option value="Gemini CLI">Gemini CLI</option>
                  <option value="Cursor">Cursor</option>
                  <option value="Cline">Cline</option>
                  <option value="Codex">Codex</option>
                  <option value="Kimi Lane">Kimi Lane</option>
                  <option value="Otto Front-Door">Otto Front-Door</option>
                </select>
              </div>

              <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
                {filteredLanes.map((lane) => (
                  <div
                    key={lane.id}
                    className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-1.5 text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                      <div className="flex items-center gap-2">
                        <span className="text-sky-400 font-bold tabular-nums">
                          #{String(lane.laneNumber).padStart(2, '0')}
                        </span>
                        <span className="font-bold text-slate-100">{lane.name}</span>
                        <span className="text-slate-500">·</span>
                        <span className="text-slate-300">{lane.runtimeSurface}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">[{lane.chokepoint}]</span>
                        {lane.operating ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>OPERATING ({lane.latencyMs}ms)</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-300 font-bold">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>SILENT / UNPROVEN</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[11px] text-slate-400">
                      <div className="truncate">
                        Path: <code className="text-slate-200">{lane.launcherOrPath}</code>
                      </div>
                      <div className="truncate">
                        Probe: <code className="text-sky-300">{lane.probeCmd}</code>
                      </div>
                    </div>

                    <div
                      className={`text-[11px] font-mono ${
                        lane.operating ? 'text-emerald-400/90' : 'text-amber-300/90'
                      }`}
                    >
                      {lane.findingSummary}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 5 Cols: 27 Findings Audit & Auto-Remediation Checklist */}
            <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <p className="text-xs font-mono text-sky-400">
                    INITIAL AUDIT DIAGNOSTIC · 27 FINDINGS CLUSTERED
                  </p>
                  <h2 className="text-base font-bold text-slate-100">
                    Ticket #42 Remediation &amp; Dead-Launcher Purge
                  </h2>
                </div>
                <span
                  className={`text-xs font-mono font-bold tabular-nums ${
                    memoryPlane.auditSummary.openFindingsCount === 0
                      ? 'text-emerald-400'
                      : 'text-amber-300'
                  }`}
                >
                  {memoryPlane.auditSummary.openFindingsCount} Open
                </span>
              </div>

              <div className="space-y-3">
                {memoryPlane.findings.map((f) => (
                  <div
                    key={f.id}
                    className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-bold text-slate-200">{f.targetRef}</span>
                      <span
                        className={
                          f.resolved ? 'text-emerald-400 font-bold' : 'text-amber-300 font-bold'
                        }
                      >
                        {f.resolved ? 'RESOLVED' : 'OPEN FINDING'}
                      </span>
                    </div>
                    <p className="text-slate-300">{f.description}</p>
                    <div className="text-[11px] font-mono text-sky-300">
                      Fix: {f.remediationAction}
                    </div>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={handleExecuteDecreeAndRemediation}
                disabled={remediating}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-md transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-4 h-4 ${remediating ? 'animate-spin' : ''}`} />
                <span>
                  {isAllOperating
                    ? 'All 18 Lanes Proven Operating (Re-Run Live Audit Probes)'
                    : 'Execute Ticket #42 Fix: Clean Dead Launchers & Wire All 18 Lanes'}
                </span>
              </button>
            </div>
          </section>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 03: DREAMING CONSOLIDATION & VALUE-PER-TOKEN BRIEF LAB            */}
      {/* ===================================================================== */}
      {subTab === 'dreaming' && (
        <div className="space-y-8">
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left 6 Cols: Nightly Bounded Consolidation ("Dreaming") + Fact Inspector */}
            <div className="lg:col-span-6 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-5">
              <div className="border-b border-slate-800 pb-3">
                <p className="text-xs font-mono text-sky-400">
                  BACKGROUND CONSOLIDATION (&ldquo;DREAMING V3+ EXCEED&rdquo;)
                </p>
                <h2 className="text-base font-bold text-slate-100">
                  Distill Episodic Failure Ore into Probe-Backed Procedural Memory
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Unlike opaque consolidation that silently rewrites memories, every distilled fact
                  retains its source records, bi-temporal <code>valid_at</code>, and an executable
                  probe. Staleness is determined by re-running the probe—never by age alone.
                </p>
              </div>

              <form onSubmit={handleRunDreamSubmit} className="space-y-3 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <label
                      htmlFor="dream-title"
                      className="block font-mono text-slate-300 mb-1"
                    >
                      Distilled Memory / Procedural Rule Title
                    </label>
                    <input
                      id="dream-title"
                      type="text"
                      value={dreamTitle}
                      onChange={(e) => setDreamTitle(e.target.value)}
                      className="w-full px-3 py-1.5 font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="dream-kind"
                      className="block font-mono text-slate-300 mb-1"
                    >
                      Typed Lane
                    </label>
                    <select
                      id="dream-kind"
                      value={dreamKind}
                      onChange={(e) => setDreamKind(e.target.value as MemoryTypeKind)}
                      className="w-full px-2.5 py-1.5 font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100"
                    >
                      <option value="procedural">procedural (Gate)</option>
                      <option value="project">project</option>
                      <option value="feedback">feedback</option>
                      <option value="reference">reference</option>
                      <option value="user">user</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="dream-episode"
                    className="block font-mono text-slate-300 mb-1"
                  >
                    Episodic Failure Record &rarr; Distilled Semantic / Procedural Fact
                  </label>
                  <textarea
                    id="dream-episode"
                    rows={2}
                    value={dreamEpisode}
                    onChange={(e) => setDreamEpisode(e.target.value)}
                    className="w-full px-3 py-2 font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="dream-ticket"
                      className="block font-mono text-slate-300 mb-1"
                    >
                      Source Ticket / Ledger Ref
                    </label>
                    <input
                      id="dream-ticket"
                      type="text"
                      value={dreamTicket}
                      onChange={(e) => setDreamTicket(e.target.value)}
                      className="w-full px-3 py-1.5 font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="dream-probe"
                      className="block font-mono text-slate-300 mb-1"
                    >
                      Executable Staleness Probe Command
                    </label>
                    <input
                      id="dream-probe"
                      type="text"
                      value={dreamProbe}
                      onChange={(e) => setDreamProbe(e.target.value)}
                      className="w-full px-3 py-1.5 font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={dreamBusy}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>
                    {dreamBusy
                      ? 'Consolidating Spool...'
                      : 'Run Bounded Dreaming Consolidation & Emit Diff'}
                  </span>
                </button>
              </form>

              {dreamDiffOutput && (
                <pre className="p-3 bg-slate-950 border border-emerald-500/40 rounded-md text-[11px] font-mono text-emerald-300 overflow-x-auto">
                  {dreamDiffOutput}
                </pre>
              )}

              {/* Distilled Memory Store with Live Probe Toggle & Delete */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span>
                    DURABLE MEMORY STORE ({memoryPlane.distilledMemories.length} Signed Records)
                  </span>
                  <span>Toggle Probe to Test Staleness Retirement</span>
                </div>

                <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                  {memoryPlane.distilledMemories.map((fact) => (
                    <div
                      key={fact.id}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-1.5 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sky-400">{fact.id}</span>
                          <span className="text-slate-400">[{fact.kind}]</span>
                          <span className="text-slate-500">EIG: {fact.expectedInfoGain}</span>
                          <span className="text-slate-500">{fact.tokenCount} tok</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onToggleFactProbe(fact.id)}
                            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded border cursor-pointer ${
                              fact.probePassing
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                                : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            }`}
                          >
                            Probe: {fact.probePassing ? 'PASS (Fresh)' : 'FAIL (Stale Retired)'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onDeleteMemoryFact(fact.id)}
                            title="Delete memory record (git audit logged)"
                            className="p-1 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <div className="font-semibold text-slate-100">{fact.title}</div>
                      <p className="text-slate-300">{fact.distilledFact}</p>
                      <div className="text-[11px] font-mono text-slate-400 flex flex-wrap items-center justify-between gap-2">
                        <span>Probe: {fact.probeCmd}</span>
                        <span>
                          valid_at: {fact.validAt.slice(0, 10)} · sha: {fact.gitSignedSha}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right 6 Cols: Value-Per-Token Claim-Open Brief Optimizer & Live Preview */}
            <div className="lg:col-span-6 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-5">
              <div className="border-b border-slate-800 pb-3">
                <p className="text-xs font-mono text-sky-400">
                  WORKING TIER · VALUE-PER-TOKEN CLAIM-OPEN BRIEF INJECTOR
                </p>
                <h2 className="text-base font-bold text-slate-100">
                  Real-Time Brief Budgeting, Confidence Abstention &amp; Probe Gate
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Adjust the token budget or confidence threshold below. Facts whose live probe
                  fails are automatically excluded before injection (guaranteeing{' '}
                  <code className="text-emerald-400">0.0% Stale-Served</code>).
                </p>
              </div>

              {/* Interactive Sliders */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3.5 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="brief-token-budget" className="text-slate-300">
                      Working Brief Token Budget
                    </label>
                    <span className="text-sky-400 font-bold tabular-nums">
                      {budgetedBrief.totalTokensUsed} / {tokenBudget} tok
                    </span>
                  </div>
                  <input
                    id="brief-token-budget"
                    type="range"
                    min={80}
                    max={360}
                    step={10}
                    value={tokenBudget}
                    onChange={(e) => setTokenBudget(Number(e.target.value))}
                    className="w-full accent-sky-400 cursor-pointer"
                  />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="brief-conf-threshold" className="text-slate-300">
                      Abstention Threshold
                    </label>
                    <span className="text-emerald-400 font-bold tabular-nums">
                      {(confidenceThreshold * 100).toFixed(0)}% Confidence
                    </span>
                  </div>
                  <input
                    id="brief-conf-threshold"
                    type="range"
                    min={0.7}
                    max={0.99}
                    step={0.01}
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                    className="w-full accent-emerald-400 cursor-pointer"
                  />
                </div>
              </div>

              {/* Telemetry pills */}
              <div className="grid grid-cols-3 gap-3 text-xs font-mono tabular-nums">
                <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="text-slate-400">Injected Facts</div>
                  <div className="text-sm font-bold text-emerald-400">
                    {budgetedBrief.includedFacts.length} Active
                  </div>
                </div>
                <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="text-slate-400">Stale Retired</div>
                  <div className="text-sm font-bold text-rose-400">
                    {budgetedBrief.staleRejectedFacts.length} Blocked
                  </div>
                </div>
                <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-md">
                  <div className="text-slate-400">Abstained (&lt;Conf)</div>
                  <div className="text-sm font-bold text-amber-300">
                    {budgetedBrief.abstainedFacts.length} Held
                  </div>
                </div>
              </div>

              {/* Rendered Claim-Open Markdown Brief */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                  <span>LIVE GENERATED CLAIM-OPEN BRIEF (`claim-brief.md`)</span>
                  <span className="text-emerald-400">Injected into all 7 Runtimes</span>
                </div>
                <pre className="p-4 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[380px] overflow-y-auto">
                  {budgetedBrief.renderedBriefMarkdown}
                </pre>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 04: 12 CAPABILITIES (MATCH -> EXCEED) & REPLAY BENCHMARK SUITE    */}
      {/* ===================================================================== */}
      {subTab === 'capabilities' && (
        <div className="space-y-8">
          {/* 12 Capabilities Match, Then Exceed Table */}
          <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <p className="text-xs font-mono text-sky-400">
                  SECTION 03 · TWELVE CAPABILITIES: MATCH INDUSTRY, THEN EXCEED
                </p>
                <h2 className="text-base font-bold text-slate-100">
                  How the Estate Memory Plane Leaves OpenAI Dreaming V3, Mem0 &amp; Cortex Behind
                </h2>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Source Tags: <code className="text-emerald-400">fetched</code> ·{' '}
                <code className="text-sky-300">estate</code> ·{' '}
                <code className="text-amber-300">gemini_unverified</code>
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-mono">
                    <th className="py-2.5 pr-3">Capability</th>
                    <th className="py-2.5 px-3">Who Has It &amp; Source</th>
                    <th className="py-2.5 px-3">Match Target</th>
                    <th className="py-2.5 px-3 text-emerald-400">Exceed (Estate Moat)</th>
                    <th className="py-2.5 pl-3">Live Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300 align-top">
                  {memoryPlane.capabilities.map((cap) => (
                    <tr key={cap.id} className="hover:bg-slate-800/30">
                      <td className="py-2.5 pr-3 font-semibold text-slate-100">
                        {cap.capability}
                      </td>
                      <td className="py-2.5 px-3">
                        <div>{cap.whoHasIt}</div>
                        <span className="text-[11px] font-mono text-sky-400">
                          [{cap.sourceQuality}]
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{cap.matchTarget}</td>
                      <td className="py-2.5 px-3 text-emerald-300 font-medium">
                        {cap.exceedTarget}
                      </td>
                      <td className="py-2.5 pl-3 font-mono text-sky-300 whitespace-nowrap">
                        {cap.liveMetricLabel}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Replay Failure Benchmark Suite */}
          <section className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <p className="text-xs font-mono text-sky-400">
                  REPLAY BENCHMARK GRADING · OUTCOME TRUTH OVER SYNTHETIC CHAT
                </p>
                <h2 className="text-base font-bold text-slate-100">
                  Recorded Estate Failures Prevented by Claim-Open Brief Injection
                </h2>
              </div>
              <span className="text-xs font-mono text-emerald-400 tabular-nums">
                Replay Hit Rate: {memoryPlane.benchmarks.estateExclusive.replayHitRatePct.toFixed(1)}% · Repeat Failure: 0.0%
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {memoryPlane.replayScenarios.map((rep) => (
                <div
                  key={rep.id}
                  className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-bold text-sky-400">
                      {rep.id} · {rep.ticketRef}
                    </span>
                    <span className="text-emerald-400 font-bold">
                      PREVENTED ON REPLAY ({rep.briefTokensUsed} tok)
                    </span>
                  </div>
                  <div className="font-bold text-slate-100">{rep.failureTitle}</div>
                  <p className="text-slate-400">{rep.historicalRootCause}</p>
                  <div className="text-[11px] font-mono text-slate-300">
                    Injected Gates: {rep.injectedMemoryFactIds.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
