import React, { useState, useMemo } from 'react';
import {
  GitBranch,
  Search,
  ShieldCheck,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Play,
} from 'lucide-react';
import type {
  ClaimGateAuditResult,
  EvidenceClass,
  ReconciledPullRequest,
} from '../engine/estateRules';

interface GreenlaneTriageViewProps {
  pullRequests: ReconciledPullRequest[];
  liveIdpSha: string;
  onEvaluateGuard: (input: Record<string, unknown>) => Promise<ClaimGateAuditResult>;
  onPromoteToLegion: (instructionId: string, title: string, body: string, repo: string) => void;
}

export const GreenlaneTriageView: React.FC<GreenlaneTriageViewProps> = ({
  pullRequests,
  liveIdpSha,
  onEvaluateGuard,
  onPromoteToLegion,
}) => {
  const [filterMode, setFilterMode] = useState<'ALL' | 'READY_FOR_GREENLANE' | 'REBASE_ONTO_LIVE_MAIN' | 'BLOCKED'>('ALL');
  const [query, setQuery] = useState('');

  // Interactive Git & Anti-Hallucination Claim-Gate Linter state
  const [claimedAuth, setClaimedAuth] = useState<EvidenceClass>('E1');
  const [claimText, setClaimText] = useState(
    'Bridge is 100% working and verified in production after pushing straight to main.'
  );
  const [observedSha, setObservedSha] = useState('b5531c...');
  const [commandsRaw, setCommandsRaw] = useState(
    'git push origin main\nkubectl apply -f platform/compiled/agent-foundry-hf/external-secret.yaml'
  );
  const [missingCapsRaw, setMissingCapsRaw] = useState('GENESIS_GOOGLE_REFRESH_TOKEN');
  const [auditResult, setAuditResult] = useState<ClaimGateAuditResult | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);

  const filteredPrs = useMemo(() => {
    return pullRequests.filter((pr) => {
      if (filterMode === 'READY_FOR_GREENLANE' && pr.disposition !== 'READY_FOR_GREENLANE') return false;
      if (filterMode === 'REBASE_ONTO_LIVE_MAIN' && pr.disposition !== 'REBASE_ONTO_LIVE_MAIN') return false;
      if (
        filterMode === 'BLOCKED' &&
        pr.disposition !== 'FIX_FAILING_GATE_FIRST' &&
        pr.disposition !== 'AWAITING_PRIVATE_CONNECTOR'
      ) {
        return false;
      }
      if (query.trim()) {
        const q = query.toLowerCase();
        return (
          pr.title.toLowerCase().includes(q) ||
          pr.repo.toLowerCase().includes(q) ||
          String(pr.number).includes(q)
        );
      }
      return true;
    });
  }, [pullRequests, filterMode, query]);

  const handleRunGuard = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuditing(true);
    try {
      const commands = commandsRaw
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);
      const missingCapabilities = missingCapsRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const res = await onEvaluateGuard({
        claimedAuthority: claimedAuth,
        claimText,
        proposedCommands: commands,
        observedSha: observedSha.trim() || null,
        missingCapabilities,
        integrationTestsPassed: missingCapabilities.length === 0,
        falsifierVerdict: missingCapabilities.length === 0 ? 'PASS' : 'FAIL',
        targetRepo: 'chidionyema/idp',
        isPublicCleared: true,
      });
      setAuditResult(res);
    } finally {
      setIsAuditing(false);
    }
  };

  const paddedLiveSha = /^[0-9a-f]{40}$/i.test(liveIdpSha)
    ? liveIdpSha
    : liveIdpSha.padEnd(40, '0').slice(0, 40);

  const loadCleanGreenlaneExample = () => {
    setClaimedAuth('E1');
    setClaimText(
      'Validated branch commit range against merge-base and queued fast-forward candidate on lane/ins-7981.'
    );
    setObservedSha(paddedLiveSha);
    setCommandsRaw('npx tsx --test src/engine/estateRules.test.ts\nestate-execute lane-submit --repo idp --branch lane/ins-7981');
    setMissingCapsRaw('');
    setAuditResult(null);
  };

  const loadHallucinationExample = () => {
    setClaimedAuth('E1');
    setClaimText('Bridge is 100% working and verified in production after pushing straight to main.');
    setObservedSha('b5531c...');
    setCommandsRaw(
      'git push origin main\nkubectl apply -f platform/compiled/agent-foundry-hf/external-secret.yaml'
    );
    setMissingCapsRaw('GENESIS_GOOGLE_REFRESH_TOKEN');
    setAuditResult(null);
  };

  return (
    <div className="space-y-8">
      <div className="pb-5 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 text-balance">
          Greenlane Git Spine, PR Reconciliation & Anti-Hallucination Guard
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Zero hand-raised red PRs, zero direct pushes to main, deterministic SHA drift reconciliation, and automated Claim-Gate enforcement.
        </p>
      </div>

      {/* Bounded PR Merge & Rebase Matrix */}
      <section
        aria-labelledby="pr-matrix-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
      >
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 id="pr-matrix-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
              01. Reconciled Pull Request Backlog & Bounded Greenlane Order
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Compares handover E2 commits against live E1 GitHub API heads and moving main (<span className="font-mono">{paddedLiveSha.slice(0, 10)}</span>).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input
                type="search"
                aria-label="Filter pull requests by number or title"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search PR # or title..."
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div
              role="group"
              aria-label="Filter pull requests by disposition"
              className="inline-flex items-center p-1 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              {(
                [
                  ['ALL', 'All PRs'],
                  ['READY_FOR_GREENLANE', 'Greenlane Ready'],
                  ['REBASE_ONTO_LIVE_MAIN', 'Needs Rebase'],
                  ['BLOCKED', 'Blocked / Private'],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilterMode(key)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    filterMode === key
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">
                <th className="py-3 px-5">PR & Repository</th>
                <th className="py-3 px-4">SHA Drift Audit</th>
                <th className="py-3 px-4">Greenlane Disposition</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {filteredPrs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 px-5 text-center text-slate-500 dark:text-slate-400">
                    No pull requests match the current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredPrs.map((pr) => (
                  <tr key={`${pr.repo}-${pr.number}`} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-5 align-top">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        <span className="font-mono">#{pr.number}</span> · {pr.title}
                      </div>
                      <div className="mt-0.5 font-mono text-slate-500 dark:text-slate-400">
                        {pr.repo} · Authority {pr.authority} · Tier P{pr.priorityTier}
                      </div>
                      {pr.blockingIncident && (
                        <div className="mt-1 text-red-700 dark:text-red-400 font-medium">
                          Blocker: {pr.blockingIncident}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 align-top font-mono tabular-nums">
                      <div className="text-slate-800 dark:text-slate-200">
                        {pr.liveSha ? `Live: ${pr.liveSha.slice(0, 8)}` : `Handover: ${pr.handoverSha?.slice(0, 8) ?? 'unobserved'}`}
                      </div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {pr.driftState}
                        {pr.mainMoved ? ' · Main Moved' : ''}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 align-top">
                      {pr.disposition === 'READY_FOR_GREENLANE' && (
                        <span className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Ready for Greenlane
                        </span>
                      )}
                      {pr.disposition === 'REBASE_ONTO_LIVE_MAIN' && (
                        <span className="inline-flex items-center gap-1 font-medium text-blue-700 dark:text-blue-400">
                          <GitBranch className="w-3.5 h-3.5" />
                          Rebase onto Live Main
                        </span>
                      )}
                      {pr.disposition === 'FIX_FAILING_GATE_FIRST' && (
                        <span className="inline-flex items-center gap-1 font-medium text-red-700 dark:text-red-400">
                          <XCircle className="w-3.5 h-3.5" />
                          Fix Failing Gate First
                        </span>
                      )}
                      {pr.disposition === 'AWAITING_PRIVATE_CONNECTOR' && (
                        <span className="inline-flex items-center gap-1 font-medium text-amber-700 dark:text-amber-400">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Awaiting Private Repo PAT
                        </span>
                      )}
                      <div className="mt-1 font-mono text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-xs">
                        {pr.recommendedLaneCommand}
                      </div>
                    </td>
                    <td className="py-3.5 px-5 align-top text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() =>
                          onPromoteToLegion(
                            `INS-0${pr.number}`,
                            `Reconcile ${pr.repo}#${pr.number} for Greenlane`,
                            `Prepare PR #${pr.number} ("${pr.title}") for Greenlane convergence (${pr.disposition}). Verify branch delta and negative tests without direct main push.`,
                            pr.repo
                          )
                        }
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
                      >
                        <Play className="w-3 h-3" />
                        Prep Lane
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Interactive Git & Anti-Hallucination Claim-Gate Firewall */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <form
          onSubmit={handleRunGuard}
          className="xl:col-span-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                02. Deterministic Git & Claim-Gate Linter
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Blocks agent hallucinations, fake SHAs, silent E3/U promotion, direct main pushes, and kubectl hand-applies.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={loadHallucinationExample}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Load Hallucinated / Rogue Agent Sample
            </button>
            <button
              type="button"
              onClick={loadCleanGreenlaneExample}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Load Compliant Greenlane Sample
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="guard-auth" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Agent Claimed Authority
              </label>
              <select
                id="guard-auth"
                value={claimedAuth}
                onChange={(e) => setClaimedAuth(e.target.value as EvidenceClass)}
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                <option value="E1">E1 (Live Verified Yield)</option>
                <option value="E2">E2 (Historical Snapshot)</option>
                <option value="E3">E3 (Intent / Proposal)</option>
                <option value="U">U (Unverified / Missing Access)</option>
              </select>
            </div>

            <div>
              <label htmlFor="guard-sha" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Cited Commit SHA
              </label>
              <input
                id="guard-sha"
                type="text"
                value={observedSha}
                onChange={(e) => setObservedSha(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label htmlFor="guard-claim" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Agent Status Claim
            </label>
            <input
              id="guard-claim"
              type="text"
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label htmlFor="guard-cmds" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Proposed Git / Cluster Commands (one per line)
            </label>
            <textarea
              id="guard-cmds"
              rows={3}
              value={commandsRaw}
              onChange={(e) => setCommandsRaw(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label htmlFor="guard-missing" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Unprovisioned Secrets / Capabilities (comma-separated, if any)
            </label>
            <input
              id="guard-missing"
              type="text"
              value={missingCapsRaw}
              onChange={(e) => setMissingCapsRaw(e.target.value)}
              placeholder="Leave blank if all capabilities are verified"
              className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <button
            type="submit"
            disabled={isAuditing}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <ShieldCheck className="w-4 h-4" />
            {isAuditing ? 'Evaluating Claim-Gate...' : 'Run Deterministic Claim-Gate'}
          </button>
        </form>

        <section
          aria-labelledby="guard-verdict-heading"
          className="xl:col-span-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
        >
          <h2 id="guard-verdict-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
            03. Claim-Gate Verdict & Required Remediations
          </h2>

          {!auditResult ? (
            <div className="p-6 border border-dashed border-slate-300 dark:border-slate-700 rounded-lg text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Click <strong>Run Deterministic Claim-Gate</strong> to inspect how the firewall catches fabricated commit SHAs, silent authority upgrades, <code className="font-mono">git push origin main</code>, and <code className="font-mono">kubectl apply</code> violations, and logs the pass/refuse event to <code className="font-mono">/fleet</code>.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg font-mono text-xs tabular-nums">
                <div className="flex items-center gap-2 font-semibold">
                  {auditResult.verdict === 'PASS' ? (
                    <span className="text-emerald-700 dark:text-emerald-400 inline-flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" />
                      VERDICT: PASS
                    </span>
                  ) : (
                    <span className="text-red-700 dark:text-red-400 inline-flex items-center gap-1">
                      <XCircle className="w-4 h-4" />
                      VERDICT: {auditResult.verdict}
                    </span>
                  )}
                </div>
                <div className="text-slate-700 dark:text-slate-300">
                  Epistemic Score: {auditResult.epistemicScore}/100 · Effective Authority: {auditResult.effectiveAuthority}
                </div>
              </div>

              {auditResult.violations.length === 0 ? (
                <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                  Zero policy violations detected. Candidate complies with Greenlane lane/* convergence and Epistemic Rule §0.
                </p>
              ) : (
                <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
                  {auditResult.violations.map((v, i) => (
                    <div key={i} className="p-3.5 text-xs space-y-1">
                      <div className="font-mono font-semibold text-red-700 dark:text-red-400">
                        {v.severity} · {v.code}
                      </div>
                      <p className="text-slate-800 dark:text-slate-200">{v.message}</p>
                      <p className="text-slate-500 dark:text-slate-400">Fix: {v.remediation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
