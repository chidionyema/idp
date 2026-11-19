import React, { useState } from 'react';
import {
  Clock,
  ShieldCheck,
  Send,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
} from 'lucide-react';
import type { EstateStateSnapshot } from '../types/estate';
import type { ReconciledPullRequest } from '../engine/estateRules';
import { ArgonSyncPanel, type ArgonSyncActionResult } from './ArgonSyncPanel';

interface FlowAndBridgeViewProps {
  argonSync: EstateStateSnapshot['argonSync'];
  flowInstructions: EstateStateSnapshot['flowInstructions'];
  liveIdpSha: string;
  idp7981Pr?: ReconciledPullRequest;
  onSyncArgon: (branch?: string) => Promise<ArgonSyncActionResult>;
  onRefreshState: () => Promise<void>;
  onRunWatchdog: (simulateStallInstructionId?: string) => Promise<{ recoveredIds: string[] }>;
  onDispatchInbound: (payload: Record<string, unknown>) => Promise<{
    ok: boolean;
    message: string;
  }>;
  onExecuteInstructionInLegion: (instructionId: string, title: string, body: string, repo: string) => void;
}

export const FlowAndBridgeView: React.FC<FlowAndBridgeViewProps> = ({
  argonSync,
  flowInstructions,
  liveIdpSha,
  idp7981Pr,
  onSyncArgon,
  onRefreshState,
  onRunWatchdog,
  onDispatchInbound,
  onExecuteInstructionInLegion,
}) => {
  const [watchdogNotice, setWatchdogNotice] = useState<string | null>(null);
  const [isSweeping, setIsSweeping] = useState(false);

  const [repo, setRepo] = useState('chidionyema/idp');
  const [instructionId, setInstructionId] = useState('INS-08001');
  const [title, setTitle] = useState('Add signed provenance pre-flight test to Greenlane runner');
  const [body, setBody] = useState(
    'Validate commit signature lineage before opening Greenlane fast-forward candidate on chidionyema/idp.'
  );
  const [publicFlag, setPublicFlag] = useState(true);
  const [bridgeResult, setBridgeResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [isSubmittingBridge, setIsSubmittingBridge] = useState(false);

  const nowMs = Date.now();

  const handleSweep = async (simulateId?: string) => {
    setIsSweeping(true);
    setWatchdogNotice(null);
    try {
      const res = await onRunWatchdog(simulateId);
      if (res.recoveredIds.length > 0) {
        setWatchdogNotice(
          `600s Watchdog fenced stale worker epoch and triggered autonomous recovery on: ${res.recoveredIds.join(', ')}`
        );
      } else {
        setWatchdogNotice('Watchdog sweep complete: all active worker heartbeats are within the 600-second window.');
      }
    } finally {
      setIsSweeping(false);
    }
  };

  const handleInboundSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingBridge(true);
    setBridgeResult(null);
    try {
      const payload: Record<string, unknown> = {
        v: 1,
        repo,
        instruction_id: instructionId,
        title,
        body,
      };
      if (publicFlag) {
        payload.public = true;
      }
      const outcome = await onDispatchInbound(payload);
      setBridgeResult(outcome);
    } finally {
      setIsSubmittingBridge(false);
    }
  };

  const loadNegativePreset = (preset: 'public-leak' | 'private-mismatch' | 'duplicate' | 'valid') => {
    setBridgeResult(null);
    if (preset === 'public-leak') {
      setRepo('chidionyema/idp');
      setInstructionId('INS-NEG-LEAK');
      setTitle('Attempt unredacted dispatch to public IDP without public:true');
      setBody('Confidential outbox payload lacking explicit public clearance flag.');
      setPublicFlag(false);
    } else if (preset === 'private-mismatch') {
      setRepo('chidionyema/argon');
      setInstructionId('INS-NEG-PRIV');
      setTitle('Private Argon dispatch erroneously marked public:true');
      setBody('Testing private repository boundary guard against public flag mismatch.');
      setPublicFlag(true);
    } else if (preset === 'duplicate') {
      const existing = flowInstructions[0]?.instructionId ?? 'INS-00011';
      setRepo('chidionyema/idp');
      setInstructionId(existing);
      setTitle('Replay existing instruction ID to verify idempotency');
      setBody('Duplicate network delivery must return idempotent receipt without spawning zombie worker.');
      setPublicFlag(true);
    } else {
      setRepo('chidionyema/idp');
      setInstructionId(`INS-${Math.floor(10000 + Math.random() * 89999)}`);
      setTitle('Verify Temporal instruction-ID binding on Greenlane runner');
      setBody('Bind canonical Argon instruction IDs to durable execution checkpoints with negative test.');
      setPublicFlag(true);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 text-balance">
            FLOW Durable State Machine & [GENESIS-OUTBOX] Inbound Bridge
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Causal instruction-to-yield tracking, 600-second stagnation watchdog, argon-sync lease fencing, and JSON v1 intake firewall.
          </p>
        </div>

        <button
          type="button"
          onClick={() => handleSweep()}
          disabled={isSweeping}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
        >
          <Clock className="w-3.5 h-3.5" aria-hidden="true" />
          {isSweeping ? 'Sweeping Heartbeats...' : 'Run 600s Stagnation Watchdog'}
        </button>
      </div>

      {watchdogNotice && (
        <div
          role="status"
          className="p-4 text-xs font-medium text-slate-800 dark:text-slate-200 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl flex items-center gap-2"
        >
          <ShieldCheck className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <span>{watchdogNotice}</span>
        </div>
      )}

      {/* 00. Argon Continuity & Governed lane/* Sync Engine */}
      <ArgonSyncPanel
        argonSync={argonSync}
        onTriggerSync={onSyncArgon}
        onRefreshState={onRefreshState}
        variant="full"
      />

      {/* Durable FLOW Ledger */}
      <section
        aria-labelledby="flow-ledger-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
      >
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 id="flow-ledger-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
            01. Durable FLOW Instruction Ledger & Lease Epochs
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Heartbeats exceeding 600s trigger autonomous recovery and increment the argon-sync lease epoch so stale workers fail closed.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">
                <th className="py-3 px-5">Instruction / Repo</th>
                <th className="py-3 px-4">Phase & Formation</th>
                <th className="py-3 px-4 text-right">Lease Epoch</th>
                <th className="py-3 px-4 text-right">Heartbeat Age</th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {flowInstructions.map((inst) => {
                const ageSec = Math.max(0, Math.floor((nowMs - inst.lastHeartbeatMs) / 1000));
                const isOverdue = ageSec >= 600 && inst.phase !== 'YIELD_CONFIRMED';
                return (
                  <tr key={inst.instructionId} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-5 align-top">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        <span className="font-mono">{inst.instructionId}</span> · {inst.title}
                      </div>
                      <div className="mt-0.5 text-slate-500 dark:text-slate-400 font-mono">
                        {inst.repo} · {inst.laneBranch ?? 'pending-lane'}
                        {inst.receiptHash ? ` · Receipt ${inst.receiptHash.slice(0, 10)}` : ''}
                      </div>
                      {inst.stagnationReason && (
                        <div className="mt-1 text-amber-700 dark:text-amber-400">
                          {inst.stagnationReason}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 align-top font-mono">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{inst.phase}</div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {inst.formation.toUpperCase()} · HELM {inst.helmShots}s
                      </div>
                    </td>
                    <td className="py-3.5 px-4 align-top text-right font-mono tabular-nums">
                      <div className="text-slate-900 dark:text-slate-100">Epoch {inst.leaseEpoch}</div>
                      <div className="text-slate-500 dark:text-slate-400 mt-0.5">
                        {inst.assignedWorkerId ?? 'unassigned'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 align-top text-right font-mono tabular-nums">
                      <span
                        className={
                          isOverdue
                            ? 'text-red-700 dark:text-red-400 font-semibold'
                            : 'text-slate-700 dark:text-slate-300'
                        }
                      >
                        {ageSec}s {isOverdue ? '(>600s STALE)' : ''}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 align-top text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleSweep(inst.instructionId)}
                          aria-label={`Simulate 600s stall and recover ${inst.instructionId}`}
                          className="px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
                        >
                          Test 600s Fence
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            onExecuteInstructionInLegion(
                              inst.instructionId,
                              inst.title,
                              inst.body,
                              inst.repo
                            )
                          }
                          aria-label={`Run Legion worker on ${inst.instructionId}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-md transition-colors whitespace-nowrap shrink-0"
                        >
                          <Play className="w-3 h-3" />
                          Run Worker
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* [GENESIS-OUTBOX] JSON v1 Inbound Bridge & Negative Firewall Harness */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <form
          onSubmit={handleInboundSubmit}
          className="xl:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
        >
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              02. [GENESIS-OUTBOX] JSON v1 Authenticated Intake & Privacy Firewall
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Validates JSON v1 schema, enforces explicit <code className="font-mono">public: true</code> on public repos, deduplicates replays, and creates fenced FLOW workers (never stopping at bare RECEIVED_UNVERIFIED issues).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400 mr-1">
              Test Presets:
            </span>
            <button
              type="button"
              onClick={() => loadNegativePreset('valid')}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Valid v1 Dispatch
            </button>
            <button
              type="button"
              onClick={() => loadNegativePreset('public-leak')}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Negative: Public Repo Leak
            </button>
            <button
              type="button"
              onClick={() => loadNegativePreset('private-mismatch')}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Negative: Private Flag Mismatch
            </button>
            <button
              type="button"
              onClick={() => loadNegativePreset('duplicate')}
              className="px-2.5 py-1 text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md whitespace-nowrap shrink-0"
            >
              Idempotent Duplicate Replay
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="bridge-repo" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Target Estate Repository
              </label>
              <select
                id="bridge-repo"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                <option value="chidionyema/idp">chidionyema/idp (public)</option>
                <option value="chidionyema/hermes-v2">chidionyema/hermes-v2 (public)</option>
                <option value="chidionyema/argon">chidionyema/argon (private)</option>
                <option value="chidionyema/estate-graph">chidionyema/estate-graph (private)</option>
              </select>
            </div>

            <div>
              <label htmlFor="bridge-inst-id" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Instruction ID (Idempotency Key)
              </label>
              <input
                id="bridge-inst-id"
                type="text"
                value={instructionId}
                onChange={(e) => setInstructionId(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label htmlFor="bridge-title" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Dispatch Title
            </label>
            <input
              id="bridge-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label htmlFor="bridge-body" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Instruction Specification Body
            </label>
            <textarea
              id="bridge-body"
              rows={3}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="flex items-center justify-between gap-4 pt-1">
            <label className="inline-flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={publicFlag}
                onChange={(e) => setPublicFlag(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Explicit <code className="font-mono">public: true</code> clearance</span>
            </label>

            <button
              type="submit"
              disabled={isSubmittingBridge}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Send className="w-3.5 h-3.5" aria-hidden="true" />
              {isSubmittingBridge ? 'Validating Contract...' : 'Submit v1 Dispatch'}
            </button>
          </div>

          {bridgeResult && (
            <div
              role="alert"
              className={`p-3.5 rounded-lg border text-xs flex items-start gap-2 ${
                bridgeResult.ok
                  ? 'bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                  : 'bg-red-50/70 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
              }`}
            >
              {bridgeResult.ok ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
              )}
              <span>{bridgeResult.message}</span>
            </div>
          )}
        </form>

        {/* Transport Reconciliation & Credential Truth Panel */}
        <section
          aria-labelledby="transport-truth-heading"
          className="xl:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
        >
          <h2 id="transport-truth-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
            03. Inbound Transport Reconciliation (Single Canonical Path)
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Per Priority B, competing half-built relays (<code className="font-mono">genesis_drop.ingest</code>, <code className="font-mono">omega-codex-live.py</code>, Apps Script) are consolidated in favor of the single <code className="font-mono">[GENESIS-OUTBOX]</code> JSON v1 contract wired directly to durable FLOW worker leases.
          </p>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 border-t border-b border-slate-200 dark:border-slate-800 text-xs">
            <div className="py-3 flex items-start justify-between gap-3">
              <div>
                <div className="font-medium text-slate-900 dark:text-slate-100">JSON v1 Intake & Privacy Firewall</div>
                <div className="text-slate-500 dark:text-slate-400">Schema + public/private repo guard + idempotency ledger</div>
              </div>
              <span className="font-mono text-emerald-700 dark:text-emerald-400 font-medium shrink-0">E1 Operating</span>
            </div>
            <div className="py-3 flex items-start justify-between gap-3">
              <div>
                <div className="font-medium text-slate-900 dark:text-slate-100">IDP PR #7981 Workflow Checks</div>
                <div className="text-slate-500 dark:text-slate-400 font-mono">
                  Head {(idp7981Pr?.liveSha || idp7981Pr?.handoverSha || '15b03200').slice(0, 8)} · target main {liveIdpSha.slice(0, 10)} ({idp7981Pr?.disposition ?? 'REBASE_ONTO_LIVE_MAIN'})
                </div>
              </div>
              <span className="font-mono text-cyan-700 dark:text-cyan-400 font-medium shrink-0">
                {idp7981Pr?.authority ?? 'E1'} Observed
              </span>
            </div>
            <div className="py-3 flex items-start justify-between gap-3">
              <div>
                <div className="font-medium text-slate-900 dark:text-slate-100">Gmail / Drive Polling Secrets</div>
                <div className="text-slate-500 dark:text-slate-400">GENESIS_GOOGLE_REFRESH_TOKEN in GitHub Actions</div>
              </div>
              <span className="font-mono text-amber-700 dark:text-amber-400 font-medium inline-flex items-center gap-1 shrink-0">
                <AlertTriangle className="w-3.5 h-3.5" />
                U Unprovisioned
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
