import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
  Cpu,
  Database,
  ArrowRight,
  Zap,
  Send,
} from 'lucide-react';
import type {
  OttoInstanceState,
  EstateEntity,
  CifStepReceipt,
} from '../engine/oracleEngine';

interface OttoForensicsViewProps {
  ottoInstances: OttoInstanceState[];
  entities: EstateEntity[];
  onReconcileSplitBrain: () => void;
  onExecuteOttoDirect: (
    prompt: string,
    forceConsolidate?: boolean
  ) => Promise<{
    reply: string;
    routeUsed: string;
    elapsedMs: number;
    receipt: CifStepReceipt;
  }>;
  onOpenTelegramFrontDoor: () => void;
}

export const OttoForensicsView: React.FC<OttoForensicsViewProps> = ({
  ottoInstances,
  entities,
  onReconcileSplitBrain,
  onExecuteOttoDirect,
  onOpenTelegramFrontDoor,
}) => {
  const [directInput, setDirectInput] = useState<string>('');
  const [executing, setExecuting] = useState<boolean>(false);
  const [lastExecution, setLastExecution] = useState<{
    reply: string;
    routeUsed: string;
    elapsedMs: number;
    receipt: CifStepReceipt;
  } | null>(null);

  const isSplitBrainActive = ottoInstances.some((o) => o.status === 'active_conflict');

  const handleDirectExecute = async (e: React.FormEvent, preset?: string) => {
    e.preventDefault();
    const q = (preset ?? directInput).trim();
    if (!q) return;
    setExecuting(true);
    try {
      const res = await onExecuteOttoDirect(q, false);
      setLastExecution(res);
      if (!preset) setDirectInput('');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-10">
      {/* Header + Primary Cutover Action */}
      <section aria-labelledby="otto-audit-heading" className="space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="space-y-2 max-w-3xl">
            <p className="text-xs font-mono text-sky-400">
              01. Operational Day-0 Otto · Router Hard-Bypass & Split-Brain Cutover
            </p>
            <h1
              id="otto-audit-heading"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100"
              style={{ textWrap: 'balance' }}
            >
              Day-0 Personal Agent Consolidation & Direct Router Bypass
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Eliminates both the competing 2-Ottos split-brain and the broken model router gateway.
              Canonical Otto executes directly over the upstream socket grounded in{' '}
              <code className="text-slate-200">estate-graph</code> Pass-1 retrieval and signs every
              action with a CIF HMAC-SHA256 receipt.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {isSplitBrainActive ? (
              <button
                type="button"
                onClick={onReconcileSplitBrain}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Consolidate & Purge Split-Brain</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onOpenTelegramFrontDoor}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-100 bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Canonical Day-0 Active · Open Front-Door</span>
              </button>
            )}
          </div>
        </div>

        {/* Router-Bypass Direct Execution Terminal */}
        <div className="border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3 text-xs font-mono">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span className="font-bold text-slate-100">
                ROUTER BYPASS CIRCUIT BREAKER: LOCKED ON DIRECT UPSTREAM SOCKET
              </span>
            </div>
            <span className="text-emerald-400">
              Flaky Gateway: QUARANTINED · Zero-Excuse Failover: ARMED
            </span>
          </div>

          <form
            onSubmit={(e) => handleDirectExecute(e)}
            className="flex flex-col sm:flex-row gap-2.5"
          >
            <label htmlFor="otto-forensics-cmd" className="sr-only">
              Execute command on Canonical Day-0 Otto via Direct Router Bypass
            </label>
            <input
              id="otto-forensics-cmd"
              type="text"
              value={directInput}
              onChange={(e) => setDirectInput(e.target.value)}
              placeholder="Dispatch direct instruction to Day-0 Otto (bypasses router -> queries estate-graph -> signs CIF receipt)..."
              className="flex-1 px-3.5 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
            />
            <button
              type="submit"
              disabled={executing}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold bg-sky-400 hover:bg-sky-300 text-slate-950 rounded-md transition-colors whitespace-nowrap shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{executing ? 'Running Direct...' : 'Run Direct (Bypass Router)'}</span>
            </button>
          </form>

          {lastExecution && (
            <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-md space-y-2 text-xs font-mono">
              <div className="flex flex-wrap items-center justify-between gap-2 text-emerald-400 border-b border-slate-800 pb-2">
                <span>
                  {lastExecution.routeUsed} · {lastExecution.elapsedMs}ms
                </span>
                <span>
                  CIF-HMAC: {lastExecution.receipt.hmacSignature.slice(0, 14)}... (Exit: 0)
                </span>
              </div>
              <pre className="text-slate-200 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {lastExecution.reply}
              </pre>
            </div>
          )}
        </div>

        {/* Status Banner */}
        <div className="p-4 rounded-lg border border-slate-800 bg-slate-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono">
              {isSplitBrainActive ? (
                <span className="text-rose-400 font-semibold inline-flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" />
                  ASYMMETRIC CAPTURE DETECTED (2 COMPETING OTTO PROCESSES)
                </span>
              ) : (
                <span className="text-emerald-400 font-semibold inline-flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  SPLIT-BRAIN RESOLVED · SINGLE CANONICAL DAY-0 OTTO ENFORCED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {isSplitBrainActive
                ? 'PID 41892 (~/Desktop/otto-old-worktree) is intercepting 44% of prompts into unverified markdown while PID 88410 (~/estate/otto-core) writes to estate.db.'
                : 'Legacy PID 41892 terminated & archived. All 42 asymmetric context frames migrated into ~/.estate/estate.db with verified CIF HMAC receipt.'}
            </p>
          </div>
          <div className="text-xs font-mono text-slate-300 tabular-nums shrink-0">
            Context Unity: {isSplitBrainActive ? '56% / 44% Split' : '100% Canonical WAL'}
          </div>
        </div>

        {/* Side-by-Side Comparison of the 2 Ottos */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
          {ottoInstances.map((inst) => {
            const isLegacy = inst.role === 'legacy_split_brain';
            return (
              <div
                key={inst.instanceId}
                className="border border-slate-800 rounded-lg bg-slate-900/70 p-5 flex flex-col justify-between space-y-5"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-2 text-xs font-mono tabular-nums border-b border-slate-800 pb-3">
                    <span className={isLegacy ? 'text-amber-400' : 'text-sky-400'}>
                      {inst.instanceId}
                    </span>
                    <span>
                      PID: {inst.pid === 0 ? 'TERMINATED (0)' : inst.pid} · Context Share:{' '}
                      {inst.capturedContextPct}%
                    </span>
                  </div>

                  <div>
                    <h2 className="text-base font-bold text-slate-100">{inst.label}</h2>
                    <p className="text-xs font-mono text-slate-400 mt-1 break-all">
                      $ {inst.entrypoint}
                    </p>
                  </div>

                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-950 p-3.5 rounded-md border border-slate-800">
                    <div>
                      <dt className="text-slate-500 flex items-center gap-1">
                        <Cpu className="w-3 h-3" />
                        Git Worktree Path
                      </dt>
                      <dd className="font-mono text-slate-200 mt-0.5">{inst.worktreePath}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500 flex items-center gap-1">
                        <GitBranch className="w-3 h-3" />
                        Active Branch
                      </dt>
                      <dd className="font-mono text-slate-200 mt-0.5">{inst.branch}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="text-slate-500 flex items-center gap-1">
                        <Database className="w-3 h-3" />
                        Memory & Provenance Backend
                      </dt>
                      <dd className="font-mono text-slate-200 mt-0.5">{inst.memoryBackend}</dd>
                    </div>
                  </dl>

                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-slate-300">
                      Forensic Findings & State Behavior
                    </h3>
                    <ul className="space-y-1.5 text-xs text-slate-400">
                      {inst.driftSymptoms.map((symptom, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <ArrowRight className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                          <span>{symptom}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono">
                  <span>
                    CIF HMAC Gate:{' '}
                    <strong className={inst.cifEnforced ? 'text-emerald-400' : 'text-rose-400'}>
                      {inst.cifEnforced ? 'ENFORCED (SHA256)' : 'MISSING / UNVERIFIED'}
                    </strong>
                  </span>
                  <span className="text-slate-400">Status: {inst.status}</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 02: Branch, PR & Claim Archaeology Matrix */}
      <section aria-labelledby="archaeology-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <p className="text-xs font-mono text-sky-400">
              02. Indexed Git Worktree, PR & Claim Archaeology
            </p>
            <h2 id="archaeology-heading" className="text-xl font-bold text-slate-100">
              OIA GTM Claims, Otto Worktrees & Infra Falsification Lineage
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400 tabular-nums">
            Retrieved deterministically via estate-graph (0 shell loops)
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-800 rounded-lg bg-slate-900/50">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 bg-slate-900">
                <th className="py-3 px-4">Entity / Ticket ID</th>
                <th className="py-3 px-4">Worktree / Repo & Branch</th>
                <th className="py-3 px-4">Forensic Findings & Lineage</th>
                <th className="py-3 px-4 text-right">CIF Provenance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {entities.map((ent) => (
                <tr key={ent.id} className="hover:bg-slate-900/90 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-sky-400 whitespace-nowrap">
                    {ent.id}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    <div>{ent.repoOrPath}</div>
                    <div className="text-slate-500">{ent.branchOrRef}</div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 max-w-xl">
                    <div className="font-semibold text-slate-100 mb-0.5">{ent.title}</div>
                    <div className="text-slate-400 leading-relaxed">{ent.summary}</div>
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono tabular-nums whitespace-nowrap">
                    {ent.cifVerified ? (
                      <span className="text-emerald-400 inline-flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        HMAC {ent.hmacSignature.slice(0, 8)}...
                      </span>
                    ) : (
                      <span className="text-rose-400 inline-flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Unverified Log
                      </span>
                    )}
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
