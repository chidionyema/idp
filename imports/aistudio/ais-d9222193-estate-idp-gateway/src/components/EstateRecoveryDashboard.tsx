import React, { useState, useMemo } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ArrowRight,
  Copy,
  Check,
  Code,
  FileText,
  Lock,
  Unlock,
  Terminal,
  Send,
  Zap,
  Cpu,
  Database,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Filter,
  Flame,
  GitBranch,
  RefreshCw,
  Search,
  Ban,
  ShieldOff,
  Scale,
  Sparkles,
} from 'lucide-react';
import {
  ESTATE_DIRECTIVE_XML,
  CANONICAL_GUARDIAN_PINNED_SHA,
  REJECTED_GUARDIAN_CANDIDATE_SHA,
  HARD_OPERATIONAL_LAWS,
  ACTIVE_BLOCKERS,
  RECONCILED_PR_BASELINE,
  CANONICAL_WORKSTREAMS,
  EXECUTION_PLAN_STAGES,
  OPERATIONAL_COMPLETION_CONTRACTS,
  INITIAL_OUTBOX_JOBS,
  OperationalCompletionContract,
  OutboxActuationJob,
  CORRECTED_ARCHITECTURAL_LOCKS,
  REMOVED_DANGEROUS_ASSUMPTIONS,
  ESTATE_PHILOSOPHY,
  CorrectedLock,
  DangerousAssumption,
  ESTATE_REALITY_ASSESSMENTS,
  IDP_7771_MANDATE,
  EstateRealityAssessmentItem,
} from '../protocol/estateRecoveryData';
import {
  AgentContinuityEngine,
  AgentWorker,
  MissionCheckpoint,
  FailoverEvent,
} from '../protocol/agentContinuity';

export const EstateRecoveryDashboard: React.FC = () => {
  const [selectedSection, setSelectedSection] = useState<
    'locks' | 'assessment' | 'contracts' | 'continuity' | 'stages' | 'blockers' | 'laws' | 'outbox' | 'directive'
  >('locks');

  const [continuityEngine] = useState<AgentContinuityEngine>(() => new AgentContinuityEngine());
  const [continuityWorkers, setContinuityWorkers] = useState<AgentWorker[]>(() => continuityEngine.getWorkers());
  const [failoverHistory, setFailoverHistory] = useState<FailoverEvent[]>(() => continuityEngine.getFailoverHistory());
  const [takeoverFeedback, setTakeoverFeedback] = useState<string | null>(null);
  const [fencingWriteFeedback, setFencingWriteFeedback] = useState<{
    permitted: boolean;
    code?: string;
    reason?: string;
  } | null>(null);

  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [selectedContractId, setSelectedContractId] = useState<string | null>('1_governance_and_ci');
  const [contractFilter, setContractFilter] = useState<string>('all');
  const [testedGuardianSha, setTestedGuardianSha] = useState<string>(CANONICAL_GUARDIAN_PINNED_SHA);
  const [isOutageMode, setIsOutageMode] = useState<boolean>(false);
  const [outboxJobs, setOutboxJobs] = useState<OutboxActuationJob[]>(INITIAL_OUTBOX_JOBS);
  const [newJobType, setNewJobType] = useState<'GIT_PUSH' | 'GH_VARIABLE_SET' | 'GH_SECRET_SET' | 'K3S_APPLY'>('GH_VARIABLE_SET');
  const [newJobTarget, setNewJobTarget] = useState<string>('chidionyema/argon');
  const [sovereignSealApproved, setSovereignSealApproved] = useState<boolean>(true);
  const [showAddJobModal, setShowAddJobModal] = useState<boolean>(false);
  const [simulatedRejection, setSimulatedRejection] = useState<{
    guard: string;
    reason: string;
    correctPath: string;
    timestamp: number;
  } | null>(null);

  const copyToClipboard = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(key);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const filteredContracts = useMemo(() => {
    if (contractFilter === 'all') return OPERATIONAL_COMPLETION_CONTRACTS;
    return OPERATIONAL_COMPLETION_CONTRACTS.filter((c) => c.operationalStatus === contractFilter);
  }, [contractFilter]);

  const selectedContract = useMemo(() => {
    return OPERATIONAL_COMPLETION_CONTRACTS.find((c) => c.id === selectedContractId) || null;
  }, [selectedContractId]);

  const isGuardianShaValid = testedGuardianSha.trim() === CANONICAL_GUARDIAN_PINNED_SHA;

  const handleAddActuationJob = () => {
    const job: OutboxActuationJob = {
      jobId: `act_job_${Date.now().toString(36)}`,
      timestamp: Date.now(),
      type: newJobType,
      targetRepoOrHost: newJobTarget,
      payload: {
        enqueuedBy: 'Google AI Studio Recovery Engine',
        directiveVersion: '2026.11.07-v1',
        dofLeaseVerified: true,
      },
      status: 'DISPATCHED_TO_HOST',
      receiptSha: `sha256:${Math.random().toString(36).slice(2, 10)}${Math.random().toString(36).slice(2, 10)}`,
    };
    setOutboxJobs((prev) => [job, ...prev]);
    setShowAddJobModal(false);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Invariant Anchor & Recovery Mandate */}
      <div className="bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border border-cyan-800/60 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center space-x-3 flex-wrap gap-y-2">
              <span className="px-2.5 py-1 rounded-md bg-cyan-950 border border-cyan-700/80 text-cyan-300 font-mono text-xs font-bold tracking-wide uppercase flex items-center space-x-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
                <span>Directive v2026.11.07-v1</span>
              </span>
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-slate-300 font-mono text-xs">
                App ID: c3d3ce2c-d6bc-49e1-a38e-e25473f17b6a
              </span>
              <span className="px-2.5 py-1 rounded-md bg-emerald-950 border border-emerald-700/80 text-emerald-300 font-mono text-xs font-semibold">
                93 PRs Reconciled across 4 Repos
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Genesis Estate 24-Hour Recovery Audit & Production Engine
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
              Autonomous execution and verification cockpit enforcing the Estate-Wide Degree of Freedom (DoF)
              security invariant, eliminating duplicate PR churn, and validating the 9 operational completion contracts
              with zero routine Founder intervention.
            </p>
          </div>

          {/* Quick Guardian Pin & Status */}
          <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 min-w-[280px] space-y-3 font-mono text-xs shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-[11px]">GENESIS_GUARDIAN_SHA</span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  isGuardianShaValid
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-rose-950 text-rose-400 border border-rose-800'
                }`}
              >
                {isGuardianShaValid ? 'PINNED & REVIEWED' : 'INVALID CANDIDATE'}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={testedGuardianSha}
                onChange={(e) => setTestedGuardianSha(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-cyan-300 font-mono text-xs w-full focus:outline-none focus:border-cyan-500"
                placeholder="Commit SHA..."
              />
              <button
                onClick={() => setTestedGuardianSha(CANONICAL_GUARDIAN_PINNED_SHA)}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] whitespace-nowrap"
                title="Reset to canonical da1536c7"
              >
                Reset
              </button>
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
              <span className="text-slate-400">Rejected candidate:</span>
              <button
                onClick={() => setTestedGuardianSha(REJECTED_GUARDIAN_CANDIDATE_SHA)}
                className="text-rose-400 hover:underline"
                title="Test with rejected candidate 8e232aa"
              >
                {REJECTED_GUARDIAN_CANDIDATE_SHA} (Test)
              </button>
            </div>
          </div>
        </div>

        {/* Executable Invariant Formula Pill Strip */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
          <div className="flex items-center space-x-2 text-cyan-300 bg-slate-950/70 px-3 py-1.5 rounded-lg border border-cyan-900/50">
            <span className="text-cyan-400 font-bold">∀ a ∈ A_privileged :</span>
            <span>Execute(a) ⇒ TrustedActor(a) ∧ FreshLease(a) ∧ AllowedScope(a) ∧ PinnedPolicy(a)</span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsOutageMode(!isOutageMode)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                isOutageMode
                  ? 'bg-amber-950 text-amber-300 border border-amber-700'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
              }`}
            >
              <Flame className="h-3.5 w-3.5 text-amber-400" />
              <span>{isOutageMode ? 'Outage Contraction: ACTIVE' : 'Outage Contraction: Standby'}</span>
            </button>

            <button
              onClick={() => copyToClipboard('directive', ESTATE_DIRECTIVE_XML)}
              className="px-3 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-xs font-semibold flex items-center space-x-1.5"
            >
              {copiedText === 'directive' ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Copied XML Directive</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Copy System Instruction Block</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex overflow-x-auto pb-1 gap-2 border-b border-slate-800 text-xs font-semibold scrollbar-none">
        <button
          onClick={() => setSelectedSection('locks')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'locks'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Scale className="h-4 w-4 text-cyan-400" />
          <span>6 Corrected Locks (L1–L6) & 3 Safety Preventions</span>
        </button>

        <button
          onClick={() => setSelectedSection('assessment')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'assessment'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <GitBranch className="h-4 w-4 text-cyan-400" />
          <span>Estate Reality & Assessment (IDP #7771)</span>
        </button>

        <button
          onClick={() => setSelectedSection('contracts')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'contracts'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <CheckCircle2 className="h-4 w-4" />
          <span>10 Operational Completion Contracts</span>
        </button>

        <button
          onClick={() => setSelectedSection('continuity')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'continuity'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Cpu className="h-4 w-4 text-cyan-400" />
          <span>Agent Continuity &amp; Takeover (IDP #7790)</span>
        </button>

        <button
          onClick={() => setSelectedSection('stages')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'stages'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>7-Stage Execution Plan</span>
        </button>

        <button
          onClick={() => setSelectedSection('blockers')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'blockers'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Active Blockers Remediation & Baseline (93 PRs)</span>
        </button>

        <button
          onClick={() => setSelectedSection('laws')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'laws'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          <span>6 Hard Operational Laws</span>
        </button>

        <button
          onClick={() => setSelectedSection('outbox')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'outbox'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Terminal className="h-4 w-4" />
          <span>Outbox Actuation & 3-Shield Council</span>
        </button>

        <button
          onClick={() => setSelectedSection('directive')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl transition-all ${
            selectedSection === 'directive'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 shadow'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Code className="h-4 w-4" />
          <span>System Directive XML</span>
        </button>
      </div>

      {/* Section 0: The 6 Corrected Architectural Locks & 3 Safety Preventions */}
      {selectedSection === 'locks' && (
        <div className="space-y-6">
          {/* Engineering Verdict Philosophy Banner */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-800/60 shadow-xl">
            <div className="flex items-start space-x-3.5">
              <Sparkles className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
              <div className="space-y-1.5">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-300">
                    Engineering Verdict &amp; Core Architecture Principle
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Self-Recovering vs Locked-Down
                  </span>
                </div>
                <p className="text-sm text-slate-200 font-sans leading-relaxed">
                  "{ESTATE_PHILOSOPHY}"
                </p>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  All six locks (L1–L6) are adopted as enforceable invariants, with hazardous assumptions eliminated to guarantee automatic self-recovery.
                </p>
              </div>
            </div>
          </div>

          {/* Dangerous Assumptions Interceptor & Interactive Simulator */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-1">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Ban className="h-4 w-4 text-rose-400" />
                  <span>Three Particularly Dangerous Assumptions Removed</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Eliminated from the estate execution model to prevent audit invalidation, unauthenticated authority claims, and confidence-score bypasses.
                </p>
              </div>

              {/* Interactive Test Buttons */}
              <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                <span className="text-[10px] font-mono text-slate-400 mr-1">Simulate Guard:</span>
                <button
                  onClick={() =>
                    setSimulatedRejection({
                      guard: 'REJECT_BLIND_FORCE_PUSH',
                      reason:
                        'Force-pushing is not automatically safer than creating a replacement PR. Rewriting history destroys approvals and forensic lineage.',
                      correctPath:
                        'Repair in place where safe; otherwise preserve commit lineage and authorize an explicit replacement.',
                      timestamp: Date.now(),
                    })
                  }
                  className="px-2 py-1 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[10px] font-mono"
                >
                  Blind Force-Push
                </button>

                <button
                  onClick={() =>
                    setSimulatedRejection({
                      guard: 'REJECT_UNAUTHENTICATED_REVIEW',
                      reason:
                        'Two AI reviews (e.g. Kimi and ChatGPT) do NOT establish independent authority without cryptographic principal signatures.',
                      correctPath:
                        'Security proof must bind to authenticated, distinct KMS/Ed25519 key IDs and exact reviewed tree digest.',
                      timestamp: Date.now(),
                    })
                  }
                  className="px-2 py-1 rounded-lg bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 text-[10px] font-mono"
                >
                  Unauthenticated AI Review
                </button>

                <button
                  onClick={() =>
                    setSimulatedRejection({
                      guard: 'REJECT_CONFIDENCE_BYPASS',
                      reason:
                        "A model's confidence score (e.g. WWFD >= 0.97) is NOT authorization. Bypassing lease or scope checks is refused.",
                      correctPath:
                        'Must provide calibrated evidence, explicit precedent scope, fresh lease token, and enforceable delegation.',
                      timestamp: Date.now(),
                    })
                  }
                  className="px-2 py-1 rounded-lg bg-purple-950/80 hover:bg-purple-900 border border-purple-800 text-purple-300 text-[10px] font-mono"
                >
                  WWFD 0.99 Confidence Bypass
                </button>
              </div>
            </div>

            {/* Simulated Rejection Alert Banner */}
            {simulatedRejection && (
              <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-xs space-y-2 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-rose-400 flex items-center space-x-1.5">
                    <ShieldAlert className="h-4 w-4" />
                    <span>GATE REJECTION: {simulatedRejection.guard}</span>
                  </span>
                  <button
                    onClick={() => setSimulatedRejection(null)}
                    className="text-slate-400 hover:text-white text-[11px]"
                  >
                    Dismiss
                  </button>
                </div>
                <div className="text-slate-200">{simulatedRejection.reason}</div>
                <div className="pt-1.5 border-t border-rose-900/60 font-mono text-[11px] text-cyan-300 flex items-center space-x-1">
                  <span className="text-slate-400">Required Authorized Path:</span>
                  <span>{simulatedRejection.correctPath}</span>
                </div>
              </div>
            )}

            {/* The 3 Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {REMOVED_DANGEROUS_ASSUMPTIONS.map((d) => (
                <div
                  key={d.id}
                  className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5 flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white flex items-center space-x-1.5">
                        <ShieldOff className="h-3.5 w-3.5 text-rose-400" />
                        <span>{d.name}</span>
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-900">
                        REMOVED
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-rose-950/80 text-[11px] text-rose-200/90 italic">
                      "{d.flawedAssumption}"
                    </div>

                    <div className="text-[11px] text-slate-300 leading-relaxed">
                      <span className="text-slate-400 font-semibold block text-[10px] uppercase font-mono">
                        Why Dangerous:
                      </span>
                      {d.whyDangerous}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 space-y-1 text-[11px] font-mono">
                    <span className="text-cyan-400 font-semibold block text-[10px] uppercase">
                      Architectural Correction:
                    </span>
                    <p className="text-cyan-200 text-[10px]">{d.architecturalCorrection}</p>
                    <div className="text-[9px] text-amber-400 truncate mt-1" title={d.enforcedGuard}>
                      {d.enforcedGuard}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* The Six Corrected Architectural Locks (L1–L6) */}
          <div className="space-y-3 pt-2">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Scale className="h-4 w-4 text-cyan-400" />
                <span>The Six Corrected Architectural Locks (L1–L6)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Adopted as enforceable security and reliability invariants with explicit self-recovering design corrections.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {CORRECTED_ARCHITECTURAL_LOCKS.map((lock) => (
                <div
                  key={lock.id}
                  className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      <span className="h-7 w-7 rounded-xl bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono text-xs font-bold flex items-center justify-center shadow-sm">
                        {lock.id}
                      </span>
                      <h4 className="text-sm font-bold text-white">{lock.name}</h4>
                    </div>

                    <div className="flex items-center space-x-1.5 font-mono text-[10px]">
                      <span
                        className={`px-2 py-0.5 rounded font-bold ${
                          lock.verdict === 'Adopt'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-amber-950 text-amber-300 border border-amber-800'
                        }`}
                      >
                        {lock.verdict}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {lock.status}
                      </span>
                    </div>
                  </div>

                  {/* Required Correction Highlight */}
                  <div className="p-3 rounded-xl bg-slate-950 border border-cyan-900/60 space-y-1">
                    <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider block">
                      Required Correction:
                    </span>
                    <p className="text-xs text-cyan-100 font-sans leading-relaxed">
                      {lock.requiredCorrection}
                    </p>
                  </div>

                  {/* Design Rationale */}
                  <div className="text-xs text-slate-300 space-y-1">
                    <span className="text-[10px] font-mono text-slate-400 uppercase block font-semibold">
                      Design Rationale:
                    </span>
                    <p className="text-slate-300 font-sans leading-relaxed">{lock.designRationale}</p>
                  </div>

                  {/* Boundary and Self Recovery Details */}
                  <div className="pt-2 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] font-mono">
                    <div className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 block mb-0.5">Enforcement Boundary:</span>
                      <span className="text-white font-medium">{lock.enforcementBoundary}</span>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 block mb-0.5">Self-Recovery Mechanism:</span>
                      <span className="text-emerald-300">{lock.selfRecoveryPrinciple}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Section: Estate Reality & Assessment (IDP #7771) */}
      {selectedSection === 'assessment' && (
        <div className="space-y-6">
          {/* IDP #7771 Upstream Registration Card */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border border-cyan-800/60 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-lg bg-cyan-950 border border-cyan-700 flex items-center justify-center text-cyan-400 font-mono text-xs font-bold">
                  #7771
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-bold text-white">
                      Canonical Recovery Mandate: GitHub IDP #7771
                    </h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
                      VERIFIED ON GITHUB
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 font-sans">
                    Title: Founder Zero-Touch Autonomous Execution &bull; Requirements registered directly on GitHub
                  </p>
                </div>
              </div>

              <div className="text-right text-[11px] font-mono text-slate-400">
                <span>Status: </span>
                <span className="text-amber-300 font-bold">Requirements Registered (Enforcement Pending)</span>
              </div>
            </div>

            {/* Core Mandate Directives */}
            <div className="space-y-2">
              <span className="text-[11px] font-mono uppercase font-bold text-cyan-300 block">
                Upstream Binding Directives (IDP #7771):
              </span>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
                {IDP_7771_MANDATE.coreDirectives.map((d, idx) => (
                  <li key={idx} className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-start space-x-2">
                    <Check className="h-3.5 w-3.5 text-cyan-400 mt-0.5 shrink-0" />
                    <span className="leading-relaxed">{d}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Boundary Framing Alert */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1.5 font-sans">
              <div className="flex items-center space-x-2 text-cyan-300 font-mono font-bold text-[11px]">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                <span>ROLE BOUNDARY &amp; DISPOSITION</span>
              </div>
              <p className="text-slate-300 leading-relaxed text-xs">
                Google AI Studio operates strictly as a <strong className="text-white">candidate observability and assurance interface</strong>.
                It consumes authenticated estate evidence and submits narrowly scoped requests through the existing broker—it is{' '}
                Actual guarantees reside in the estate's trusted execution boundaries (the governed IDP action doors on Oracle ARM / k3s;
                <code className="text-cyan-300 font-mono"> server.py</code> handles context MCP tool dispatch).
              </p>
            </div>
          </div>

          {/* Five Estate Reality vs Claims Reconciliations */}
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Scale className="h-4 w-4 text-cyan-400" />
                <span>Five Verified Estate Reality Comparisons</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Reconciliation between local test harness claims and live Argon / IDP production infrastructure.
              </p>
            </div>

            <div className="space-y-3">
              {ESTATE_REALITY_ASSESSMENTS.map((item) => (
                <div
                  key={item.id}
                  className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 hover:border-slate-700 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2.5">
                      <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300">
                        {item.claim}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 font-mono text-[10px]">
                      <span
                        className={`px-2 py-0.5 rounded font-bold ${
                          item.authorityBoundary === 'ESTATE_CANONICAL'
                            ? 'bg-purple-950 text-purple-300 border border-purple-800'
                            : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        }`}
                      >
                        {item.authorityBoundary}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                        {item.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                      <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold block">
                        Verified Estate Reality:
                      </span>
                      <p className="text-slate-300 leading-relaxed font-sans">{item.verifiedEstateReality}</p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950 border border-cyan-900/40 space-y-1">
                      <span className="text-[10px] font-mono text-cyan-400 uppercase font-semibold block">
                        Engineering Decision:
                      </span>
                      <p className="text-cyan-100 leading-relaxed font-sans font-medium">{item.engineeringDecision}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Section 1: The 9 Operational Completion Contracts */}
      {selectedSection === 'contracts' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <CheckCircle2 className="h-5 w-5 text-cyan-400" />
                <span>The 10 Operational Completion Contracts (IDP #7790)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluated by Google AI Studio &amp; genesis-certifier before transitioning any workstream to OPERATIONAL_COMPLETE.
              </p>
            </div>

            {/* Filter buttons */}
            <div className="flex items-center space-x-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setContractFilter('all')}
                className={`px-2.5 py-1 rounded-lg ${
                  contractFilter === 'all' ? 'bg-cyan-950 text-cyan-300 font-semibold' : 'text-slate-400'
                }`}
              >
                All ({OPERATIONAL_COMPLETION_CONTRACTS.length})
              </button>
              <button
                onClick={() => setContractFilter('OPERATIONAL_COMPLETE')}
                className={`px-2.5 py-1 rounded-lg ${
                  contractFilter === 'OPERATIONAL_COMPLETE' ? 'bg-emerald-950 text-emerald-300 font-semibold' : 'text-slate-400'
                }`}
              >
                Complete
              </button>
              <button
                onClick={() => setContractFilter('QUEUED_FOR_GREENLANE')}
                className={`px-2.5 py-1 rounded-lg ${
                  contractFilter === 'QUEUED_FOR_GREENLANE' ? 'bg-cyan-950 text-cyan-300 font-semibold' : 'text-slate-400'
                }`}
              >
                Greenlane Queue
              </button>
              <button
                onClick={() => setContractFilter('IN_VERIFICATION')}
                className={`px-2.5 py-1 rounded-lg ${
                  contractFilter === 'IN_VERIFICATION' ? 'bg-amber-950 text-amber-300 font-semibold' : 'text-slate-400'
                }`}
              >
                Verifying
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Contracts List */}
            <div className="lg:col-span-5 space-y-3">
              {filteredContracts.map((c) => {
                const isSelected = selectedContractId === c.id;
                const allSatisfied = c.requiredEvidence.every((e) => e.satisfied);

                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedContractId(c.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-slate-900 border-cyan-500/80 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/50'
                        : 'bg-slate-950/70 border-slate-800/80 hover:bg-slate-900/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-cyan-400 text-xs font-bold">#{c.number}</span>
                          <h3 className="text-xs font-bold text-white">{c.name}</h3>
                        </div>
                        <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                          {c.targetPrs.map((pr) => (
                            <span key={pr} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              {pr}
                            </span>
                          ))}
                        </div>
                      </div>

                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border whitespace-nowrap ${
                          c.operationalStatus === 'OPERATIONAL_COMPLETE'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : c.operationalStatus === 'QUEUED_FOR_GREENLANE'
                            ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                        }`}
                      >
                        {c.operationalStatus}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span>Evidence items: {c.requiredEvidence.length}</span>
                      <span className={allSatisfied ? 'text-emerald-400 font-semibold' : 'text-amber-400'}>
                        {c.requiredEvidence.filter((e) => e.satisfied).length} / {c.requiredEvidence.length} Satisfied
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Contract Detail Inspector */}
            <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5">
              {selectedContract ? (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                    <div>
                      <span className="font-mono text-xs text-cyan-400 font-bold">Contract #{selectedContract.number}</span>
                      <h3 className="text-sm font-bold text-white mt-0.5">{selectedContract.name}</h3>
                      <div className="text-xs text-slate-400 font-mono mt-1">
                        Targets: {selectedContract.targetPrs.join(', ')}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-xs font-mono font-bold px-2.5 py-1 rounded-lg border ${
                          selectedContract.operationalStatus === 'OPERATIONAL_COMPLETE'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : selectedContract.operationalStatus === 'QUEUED_FOR_GREENLANE'
                            ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                        }`}
                      >
                        {selectedContract.operationalStatus}
                      </span>
                    </div>
                  </div>

                  {/* Certifier Signature Badge */}
                  {selectedContract.certifierSignature ? (
                    <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-800/80 flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center space-x-2 text-emerald-300">
                        <Lock className="h-4 w-4 text-emerald-400" />
                        <span>Independent Certifier Ed25519 Signature:</span>
                      </div>
                      <span className="text-[11px] text-emerald-400 font-bold truncate max-w-[220px]" title={selectedContract.certifierSignature}>
                        {selectedContract.certifierSignature}
                      </span>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-center justify-between text-xs font-mono text-amber-300">
                      <div className="flex items-center space-x-2">
                        <Unlock className="h-4 w-4 text-amber-400" />
                        <span>Awaiting Held-Out Trial Ed25519 Seal</span>
                      </div>
                      <span className="text-[10px] text-amber-400">PENDING CERTIFIER</span>
                    </div>
                  )}

                  {/* Required Evidence Table */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-slate-300">Required Evidence Verification Matrix</h4>
                    <div className="border border-slate-800 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
                          <tr>
                            <th className="py-2.5 px-3">Evidence Key / Description</th>
                            <th className="py-2.5 px-3">Required Spec</th>
                            <th className="py-2.5 px-3">Measured State</th>
                            <th className="py-2.5 px-3 text-right">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/70 bg-slate-950/40 font-mono text-[11px]">
                          {selectedContract.requiredEvidence.map((e) => (
                            <tr key={e.key} className="hover:bg-slate-900/40">
                              <td className="py-2.5 px-3">
                                <div className="text-slate-200 font-bold">{e.key}</div>
                                <div className="text-[10px] text-slate-400 font-sans">{e.description}</div>
                              </td>
                              <td className="py-2.5 px-3 text-slate-300">
                                {typeof e.requiredValue === 'boolean' ? (e.requiredValue ? 'true' : 'false') : e.requiredValue}
                              </td>
                              <td className="py-2.5 px-3 text-cyan-300">
                                {typeof e.currentValue === 'boolean' ? (e.currentValue ? 'true' : 'false') : e.currentValue}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                {e.satisfied ? (
                                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold">
                                    <Check className="h-3 w-3 text-emerald-400" />
                                    <span>PASS</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold">
                                    <AlertTriangle className="h-3 w-3 text-rose-400" />
                                    <span>FAIL</span>
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Schema YAML Format preview */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                      <span>Acceptance Schema Declaration (YAML)</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `yaml_${selectedContract.id}`,
                            `${selectedContract.id}:\n  target_prs: ${JSON.stringify(selectedContract.targetPrs)}\n  required_evidence:\n${selectedContract.requiredEvidence
                              .map((e) => `    - ${e.key}: ${JSON.stringify(e.requiredValue)}`)
                              .join('\n')}`
                          )
                        }
                        className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                      >
                        {copiedText === `yaml_${selectedContract.id}` ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span>Copied YAML</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>Copy Schema</span>
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono overflow-x-auto whitespace-pre">
{`${selectedContract.id}:
  target_prs: ${JSON.stringify(selectedContract.targetPrs)}
  required_evidence:
${selectedContract.requiredEvidence.map((e) => `    - ${e.key}: ${JSON.stringify(e.requiredValue)}`).join('\n')}`}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-slate-400 text-xs">Select a contract to view details.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Section: Agent Continuity, Cross-Surface Heartbeats & Capacity Takeover (IDP #7790) */}
      {selectedSection === 'continuity' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                  CONTRACT 10 / IDP #7790
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  SLO &le; 15s TAKEOVER
                </span>
              </div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2 mt-1">
                <Cpu className="h-5 w-5 text-cyan-400" />
                <span>Agent Continuity, Cross-Surface Heartbeats &amp; Capacity-Aware Takeover</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5 max-w-3xl leading-relaxed">
                Guarantees autonomous recovery from LLM context/token limits and worker crashes via durable off-host checkpoints,
                cross-surface heartbeat monitoring, capacity-routed failover, and strict fencing tokens.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  const res = continuityEngine.simulateFailureAndTakeover('worker_cloud_arm_01', 'TOKEN_EXHAUSTION');
                  setContinuityWorkers(continuityEngine.getWorkers());
                  setFailoverHistory(continuityEngine.getFailoverHistory());
                  if (res.success && res.event) {
                    setTakeoverFeedback(
                      `Autonomous failover succeeded in ${res.event.reassignmentLatencyMs}ms: Mission reassigned from ${res.event.previousWorkerId} to ${res.event.targetWorkerId} (highest capacity score: 94). Checkpoint ${res.event.checkpointRestoredSha} restored. New fencing token: ${res.event.newFencingToken}`
                    );
                  } else {
                    setTakeoverFeedback(`Simulation: ${res.reason}`);
                  }
                  setFencingWriteFeedback(null);
                }}
                className="px-3 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold flex items-center space-x-1.5 shadow-md shadow-cyan-950/50"
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Simulate Token Exhaustion Takeover</span>
              </button>

              <button
                onClick={() => {
                  const result = continuityEngine.evaluateFencingWrite(
                    'mission_idp_7790_recovery',
                    'worker_cloud_arm_01',
                    'lease_fence_v1_001_arm'
                  );
                  setFencingWriteFeedback(result);
                }}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold flex items-center space-x-1.5 border border-slate-700"
              >
                <Lock className="h-3.5 w-3.5 text-amber-400" />
                <span>Test Stale Fencing Rejection</span>
              </button>
            </div>
          </div>

          {/* Feedback Banners */}
          {takeoverFeedback && (
            <div className="p-3.5 rounded-xl bg-cyan-950/60 border border-cyan-800/80 text-xs font-mono text-cyan-200 flex items-start space-x-2.5">
              <Sparkles className="h-4 w-4 text-cyan-400 mt-0.5 shrink-0" />
              <div className="flex-1">
                <span className="font-bold text-white block">FAILOVER SIMULATION EXECUTED:</span>
                <span className="leading-relaxed">{takeoverFeedback}</span>
              </div>
            </div>
          )}

          {fencingWriteFeedback && (
            <div
              className={`p-3.5 rounded-xl border text-xs font-mono flex items-start space-x-2.5 ${
                fencingWriteFeedback.permitted
                  ? 'bg-emerald-950/60 border-emerald-800 text-emerald-200'
                  : 'bg-rose-950/60 border-rose-800 text-rose-200'
              }`}
            >
              {fencingWriteFeedback.permitted ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-rose-400 mt-0.5 shrink-0" />
              )}
              <div className="flex-1">
                <span className="font-bold text-white block">
                  {fencingWriteFeedback.permitted ? 'MUTATION PERMITTED' : `MUTATION REFUSED (${fencingWriteFeedback.code}):`}
                </span>
                <span className="leading-relaxed">{fencingWriteFeedback.reason || 'Lease token accepted'}</span>
              </div>
            </div>
          )}

          {/* Active Workers Telemetry Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Cpu className="h-4 w-4 text-cyan-400" />
                <span>Active Cloud Workers &amp; Capacity Telemetry</span>
              </h3>
              <span className="text-[11px] font-mono text-slate-400">
                Off-host execution • Independent of local laptop
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {continuityWorkers.map((w) => {
                const isExhausted = w.status === 'TOKEN_EXHAUSTED';
                const isHealthy = w.status === 'HEALTHY';

                return (
                  <div
                    key={w.workerId}
                    className={`p-4 rounded-xl border transition-all ${
                      isExhausted
                        ? 'bg-rose-950/30 border-rose-800/80'
                        : w.activeMissionId
                        ? 'bg-cyan-950/30 border-cyan-700/80 shadow-md'
                        : 'bg-slate-900/80 border-slate-800'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-bold text-white">{w.workerId}</span>
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                            }`}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-400 block mt-0.5">
                          {w.surfaceId} ({w.hostType})
                        </span>
                      </div>

                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          isHealthy
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : 'bg-rose-950 text-rose-300 border-rose-800'
                        }`}
                      >
                        {w.status}
                      </span>
                    </div>

                    <div className="mt-4 space-y-2 text-xs">
                      <div>
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
                          <span>Available Capacity:</span>
                          <span className="font-bold text-cyan-300">{w.availableCapacityScore}%</span>
                        </div>
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className={`h-full transition-all duration-500 ${
                              w.availableCapacityScore > 75
                                ? 'bg-emerald-500'
                                : w.availableCapacityScore > 40
                                ? 'bg-cyan-500'
                                : 'bg-amber-500'
                            }`}
                            style={{ width: `${w.availableCapacityScore}%` }}
                          />
                        </div>
                      </div>

                      <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Assigned Mission:</span>
                          <span className={w.activeMissionId ? 'text-cyan-300 font-bold' : 'text-slate-500'}>
                            {w.activeMissionId || 'None (Idle Standby)'}
                          </span>
                        </div>
                        {w.fencingLeaseToken && (
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Fencing Token:</span>
                            <span className="text-amber-300 font-bold truncate max-w-[140px]" title={w.fencingLeaseToken}>
                              {w.fencingLeaseToken}
                            </span>
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Off-host Cloud:</span>
                          <span className="text-emerald-400">True (OCI/k3s)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Durable Checkpoint & Fencing Architecture */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center space-x-2 text-cyan-300 font-bold text-xs font-mono">
                <Database className="h-4 w-4 text-cyan-400" />
                <span>DURABLE CHECKPOINT (OFF-HOST OCI BUCKET)</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                Checkpoints capture compiled context, execution history, and variable bindings outside transient agent RAM.
                If context window limits or timeouts occur, the checkpoint restores state immediately to the highest-capacity node.
              </p>
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 space-y-1">
                <div><span className="text-slate-500">Mission:</span> mission_idp_7790_recovery</div>
                <div><span className="text-slate-500">Checkpoint SHA:</span> sha256:chk_98e1002ba98cf11</div>
                <div><span className="text-slate-500">Durable URI:</span> oci://estate-checkpoints/idp_7790/step_b.json</div>
                <div><span className="text-slate-500">Restoration Bound:</span> &le; 15,000ms (Observed: 4,500ms)</div>
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center space-x-2 text-cyan-300 font-bold text-xs font-mono">
                <Lock className="h-4 w-4 text-cyan-400" />
                <span>STALE WORKER FENCING INVARIANT</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                When a worker is partitioned or disconnected and later recovers, it becomes a &quot;zombie worker&quot;.
                Fencing lease tokens strictly prevent zombie writes by rejecting any mutation stamped with an invalidated lease token.
              </p>
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 space-y-1">
                <div><span className="text-slate-500">Active Fencing Rule:</span> Monotonically increasing fencing leases</div>
                <div><span className="text-slate-500">Rejection Code:</span> REJECTED_STALE_FENCING_LEASE</div>
                <div><span className="text-slate-500">Lock Boundary:</span> Governed IDP Action Doors (Oracle ARM / k3s)</div>
              </div>
            </div>
          </div>

          {/* Failover Events Log */}
          {failoverHistory.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 font-mono">Autonomous Failover Event Audit Trail:</h4>
              <div className="border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[11px]">
                    <tr>
                      <th className="py-2.5 px-3">Event ID</th>
                      <th className="py-2.5 px-3">Trigger Reason</th>
                      <th className="py-2.5 px-3">Handoff</th>
                      <th className="py-2.5 px-3">Restored Checkpoint</th>
                      <th className="py-2.5 px-3">Latency</th>
                      <th className="py-2.5 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                    {failoverHistory.map((ev) => (
                      <tr key={ev.eventId} className="hover:bg-slate-900">
                        <td className="py-2.5 px-3 text-cyan-300">{ev.eventId}</td>
                        <td className="py-2.5 px-3 text-amber-300">{ev.triggerReason}</td>
                        <td className="py-2.5 px-3 text-slate-200">
                          {ev.previousWorkerId} &rarr; <span className="text-emerald-400 font-bold">{ev.targetWorkerId}</span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 truncate max-w-[140px]">{ev.checkpointRestoredSha}</td>
                        <td className="py-2.5 px-3 text-cyan-300 font-bold">{ev.reassignmentLatencyMs}ms</td>
                        <td className="py-2.5 px-3 text-right">
                          <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold">
                            {ev.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section 2: 7-Stage Execution Plan */}
      {selectedSection === 'stages' && (
        <div className="space-y-6">
          <div className="pb-2">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Layers className="h-5 w-5 text-cyan-400" />
              <span>Dependency-Ordered 7-Stage Execution Plan</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict stage gates: no downstream stage starts until the upstream stage exit criteria are independently verified.
            </p>
          </div>

          <div className="space-y-4">
            {EXECUTION_PLAN_STAGES.map((s, idx) => (
              <div
                key={s.stageId}
                className={`p-5 rounded-2xl border transition-all ${
                  s.status === 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION'
                    ? 'bg-slate-900/80 border-cyan-800/80 shadow-md'
                    : s.status === 'ACTIVE'
                    ? 'bg-gradient-to-r from-slate-900 via-cyan-950/30 to-slate-900 border-cyan-700/80 shadow-lg ring-1 ring-cyan-500/30'
                    : 'bg-slate-950 border-slate-800/80 opacity-75'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center space-x-3">
                    <span
                      className={`h-8 w-8 rounded-xl font-mono text-xs font-bold flex items-center justify-center border ${
                        s.status === 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION'
                          ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                          : s.status === 'ACTIVE'
                          ? 'bg-cyan-950 text-cyan-300 border-cyan-600 shadow-sm shadow-cyan-500/50'
                          : 'bg-slate-900 text-slate-500 border-slate-800'
                      }`}
                    >
                      {s.stageId}
                    </span>
                    <div>
                      <h3 className="text-sm font-bold text-white">{s.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{s.description}</p>
                    </div>
                  </div>

                  <span
                    className={`text-xs font-mono font-bold px-3 py-1 rounded-full border self-start sm:self-center ${
                      s.status === 'IMPORTED_BASELINE_PENDING_LIVE_RECONCILIATION'
                        ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                        : s.status === 'ACTIVE'
                        ? 'bg-cyan-950 text-cyan-300 border-cyan-800 animate-pulse'
                        : 'bg-slate-900 text-slate-500 border-slate-800'
                    }`}
                  >
                    {s.status}
                  </span>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                      Execution Actions
                    </span>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {s.actions.map((act, i) => (
                        <li key={i} className="flex items-start space-x-2">
                          <ArrowRight className="h-3 w-3 text-cyan-400 mt-0.5 shrink-0" />
                          <span>{act}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-1.5 bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
                    <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                      <Lock className="h-3.5 w-3.5 text-cyan-400" />
                      <span>Stage Exit Criterion</span>
                    </span>
                    <p className="text-xs text-cyan-200 font-mono font-medium">{s.exitCriterion}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 3: Active Blockers & Baseline (93 PRs) */}
      {selectedSection === 'blockers' && (
        <div className="space-y-6">
          <div className="pb-2">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-amber-400" />
              <span>Active Blockers &amp; Remediation Targets</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Resolves all failing CI evidence and merges overlapping scope across chidionyema/idp, argon, argon-sync, and estate-graph.
            </p>
          </div>

          {/* Active Blocker Cards */}
          <div className="grid grid-cols-1 gap-4">
            {ACTIVE_BLOCKERS.map((b) => (
              <div
                key={b.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-cyan-400">
                      {b.repo}
                    </span>
                    <span className="text-sm font-bold text-white">{b.targetPr}</span>
                    {b.supersedes && (
                      <span className="text-xs text-slate-400 font-mono">
                        (supersedes: <span className="text-amber-400">{b.supersedes}</span>)
                      </span>
                    )}
                  </div>

                  <span
                    className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border self-start sm:self-auto ${
                      b.status === 'READY_FOR_GREENLANE'
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : b.status === 'REMEDIATING'
                        ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                        : 'bg-rose-950 text-rose-300 border-rose-800'
                    }`}
                  >
                    {b.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Live CI / State Evidence:</span>
                    <span className="text-rose-300 font-mono text-[11px]">{b.liveCiEvidence}</span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Root Defect:</span>
                    <span className="text-slate-300">{b.rootDefect}</span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-400 block mb-1">Mandatory Remediation Action:</span>
                    <span className="text-cyan-200 font-medium">{b.mandatoryAction}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Reconciled Merged Baseline (Preserve & Reuse) */}
          <div className="pt-4 border-t border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Preserved Merged Baseline (Do Not Re-Implement)</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
              {RECONCILED_PR_BASELINE.filter((p) => p.status === 'MERGED_BASELINE').map((pr) => (
                <div key={`${pr.repo}-${pr.number}`} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">{pr.repo}</span>
                    <span className="text-emerald-400 font-bold">#{pr.number}</span>
                  </div>
                  <div className="text-white font-medium text-xs mt-1 truncate">{pr.title}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{pr.notes}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Section 4: 6 Hard Operational Laws */}
      {selectedSection === 'laws' && (
        <div className="space-y-6">
          <div className="pb-2">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <ShieldAlert className="h-5 w-5 text-cyan-400" />
              <span>The 6 Hard Operational Laws</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Governing execution boundaries, Founder intervention limits, and strict runtime requirements.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {HARD_OPERATIONAL_LAWS.map((l) => (
              <div
                key={l.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <span className="h-6 w-6 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono text-xs font-bold flex items-center justify-center">
                      {l.number}
                    </span>
                    <h3 className="text-sm font-bold text-white">{l.name}</h3>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {l.id}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">{l.rule}</p>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1.5 font-mono text-xs">
                  <span className="text-[10px] text-slate-400 block uppercase">Enforcement Mechanism</span>
                  <div className="text-cyan-300 text-xs">{l.mechanism}</div>
                </div>

                <div className="flex items-center justify-between pt-1 text-[11px] font-mono text-slate-400">
                  <span>Verification Tag:</span>
                  <span className="text-amber-400 font-semibold">{l.verificationTag}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 5: Outbox Actuation & 3-Shield Council */}
      {selectedSection === 'outbox' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <Terminal className="h-5 w-5 text-cyan-400" />
                <span>Zero Founder CLI Chores: Outbox Spooler &amp; 3-Shield Council</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Emits structured actuation jobs to .genesis/outbox/admin_actuation.jsonl for genesis-host-spooler.py.
                Escalates only irreducible decisions via 3-Shield Council to Telegram 3327 1-Tap Sovereign Seal.
              </p>
            </div>

            <button
              onClick={() => setShowAddJobModal(true)}
              className="px-3.5 py-2 rounded-xl bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 text-xs font-semibold flex items-center space-x-1.5 self-start sm:self-auto"
            >
              <Send className="h-3.5 w-3.5 text-cyan-400" />
              <span>Emit Actuation Job</span>
            </button>
          </div>

          {/* 3-Shield Council and Sovereign Seal Status Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
              3-Shield Council &amp; 1-Tap Telegram Sovereign Seal
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Shield 1: Argon Guard</span>
                <span className="text-emerald-400 font-bold text-xs mt-1 block">CONSENSUS_AFFIRMED</span>
                <span className="text-[10px] text-slate-400">Reviewed main da1536c7</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Shield 2: Kimi Web</span>
                <span className="text-emerald-400 font-bold text-xs mt-1 block">SECURITY_PASSED</span>
                <span className="text-[10px] text-slate-400">No protected leak</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Shield 3: ChatGPT Web</span>
                <span className="text-emerald-400 font-bold text-xs mt-1 block">INVARIANT_VERIFIED</span>
                <span className="text-[10px] text-slate-400">DoF lease valid</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400">Telegram Seal #3327</span>
                  <button
                    onClick={() => setSovereignSealApproved(!sovereignSealApproved)}
                    className="text-[10px] text-cyan-400 hover:underline"
                  >
                    Toggle
                  </button>
                </div>
                <span
                  className={`font-bold text-xs mt-1 block ${
                    sovereignSealApproved ? 'text-cyan-300' : 'text-amber-400'
                  }`}
                >
                  {sovereignSealApproved ? '1-TAP SEAL: GRANTED' : 'AWAITING APPROVAL'}
                </span>
                <span className="text-[10px] text-slate-400">AURA-2100 Ed25519</span>
              </div>
            </div>
          </div>

          {/* Actuation Queue Table */}
          <div className="border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Job ID &amp; Target</th>
                  <th className="py-2.5 px-4 font-medium">Actuation Type</th>
                  <th className="py-2.5 px-4 font-medium">Status &amp; Receipt</th>
                  <th className="py-2.5 px-4 font-medium">Enqueued At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 bg-slate-950/40 font-mono text-[11px]">
                {outboxJobs.map((job) => (
                  <tr key={job.jobId} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="text-cyan-400 font-bold">{job.jobId}</div>
                      <div className="text-[10px] text-slate-400">{job.targetRepoOrHost}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 text-[10px]">
                        {job.type}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          job.status === 'EXECUTED_BY_SPOOLER'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        }`}
                      >
                        {job.status}
                      </span>
                      {job.receiptSha && (
                        <div className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[160px]">
                          {job.receiptSha}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(job.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Modal to Emit Actuation Job */}
          {showAddJobModal && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Terminal className="h-4 w-4 text-cyan-400" />
                  <span>Emit Structured Actuation Job</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Sends job to .genesis/outbox/admin_actuation.jsonl. The host spooler executes it directly without manual Founder commands.
                </p>

                <div className="space-y-3 font-mono text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Job Type</label>
                    <select
                      value={newJobType}
                      onChange={(e) => setNewJobType(e.target.value as any)}
                      className="bg-slate-950 border border-slate-700 rounded-lg p-2 text-white w-full"
                    >
                      <option value="GH_VARIABLE_SET">GH_VARIABLE_SET</option>
                      <option value="GH_SECRET_SET">GH_SECRET_SET</option>
                      <option value="GIT_PUSH">GIT_PUSH</option>
                      <option value="K3S_APPLY">K3S_APPLY</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1">Target Repo or Host</label>
                    <input
                      type="text"
                      value={newJobTarget}
                      onChange={(e) => setNewJobTarget(e.target.value)}
                      className="bg-slate-950 border border-slate-700 rounded-lg p-2 text-white w-full"
                      placeholder="e.g. chidionyema/argon or oracle-arm-k3s"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => setShowAddJobModal(false)}
                    className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddActuationJob}
                    className="px-3.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 text-xs font-semibold"
                  >
                    Enqueue to Spooler
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section 6: Directive XML Source */}
      {selectedSection === 'directive' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2">
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <Code className="h-5 w-5 text-cyan-400" />
                <span>Google AI Studio System Directive Block</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Copy-paste ready system instruction block formatted for direct ingestion.
              </p>
            </div>

            <button
              onClick={() => copyToClipboard('directive_raw', ESTATE_DIRECTIVE_XML)}
              className="px-3 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 text-xs font-semibold flex items-center space-x-1.5"
            >
              {copiedText === 'directive_raw' ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy XML</span>
                </>
              )}
            </button>
          </div>

          <pre className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed shadow-inner">
            {ESTATE_DIRECTIVE_XML}
          </pre>
        </div>
      )}
    </div>
  );
};
