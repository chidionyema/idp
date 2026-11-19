import React, { useState } from 'react';
import {
  EstateState,
  DefectStatus,
  DefectRegistryMode,
  evaluateArgonPrePushGate,
  validateGenesisCommitTrailers,
  ALLOWED_GENESIS_CHANGE_CLASSES,
} from '../engine/ottoEngine';
import { ShieldCheck, AlertCircle, Check, FileCode, Terminal } from 'lucide-react';

interface ArgonGateViewProps {
  state: EstateState;
  onResolveDefect: (defectId: string, status: DefectStatus) => void;
  onUnblockAllGates: (mode: DefectRegistryMode) => void;
  onUpdateTrailers: (trailers: EstateState['argonGate']['commitTrailers']) => void;
}

export const ArgonGateView: React.FC<ArgonGateViewProps> = ({
  state,
  onResolveDefect,
  onUnblockAllGates,
  onUpdateTrailers,
}) => {
  const gateEval = evaluateArgonPrePushGate(state.argonGate);
  const trailerValidation = validateGenesisCommitTrailers(state.argonGate.commitTrailers);

  const [draftTrailers, setDraftTrailers] = useState(state.argonGate.commitTrailers);

  const handleTrailerSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateTrailers(draftTrailers);
  };

  return (
    <div className="space-y-8">
      {/* Header & Diagnosis */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
              ARGON GOVERNANCE DIAGNOSTIC · BRANCH wip/otto-background-sweep (5de5998)
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
              Why 5de5998 Was Refused by Origin & Repo-Wide Deadlock Resolution
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              Argon&apos;s pre-push hook reads <code className="font-mono text-xs">genesis-defect-controls.json</code> (32 KB),
              which existed untracked on disk (causing <code className="font-mono text-xs">ENOENT</code> in clean worktrees),
              and once supplied, three open defects in <code className="font-mono text-xs">CONTROL_PROPOSED</code> blocked
              every push across the repository. Commit the registry and verify the three controls below to unblock all pushes.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => onUnblockAllGates('TRACKED_COMMITTED')}
              className="px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              Commit Registry & Verify All 3 Controls
            </button>
            <button
              type="button"
              onClick={() => onUnblockAllGates('BLIND_WORKTREE_FALLBACK')}
              className="px-4 py-2.5 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              Set verify_defect_controls.mjs to BLIND Mode
            </button>
          </div>
        </div>
      </section>

      {/* The 4 Sequential Pre-Push Refusals */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            01. The 4 Pre-Push Refusal Chain (Measured on /tmp/wt-otto)
          </h2>
          <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
            Overall Pre-Push Verdict:{' '}
            <strong className={gateEval.verdict === 'PASS' ? 'text-emerald-500' : 'text-amber-500'}>
              {gateEval.verdict}
            </strong>
          </span>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-500 dark:text-slate-400">
                <th className="py-2.5 pr-4 font-medium">Refusal #</th>
                <th className="py-2.5 px-3 font-medium">Gate Rule Identifier</th>
                <th className="py-2.5 px-3 font-medium">Diagnostic & Remediation Trace</th>
                <th className="py-2.5 pl-3 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/70 text-xs font-mono tabular-nums">
              {gateEval.refusals.map((refusal) => (
                <tr key={refusal.step} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 pr-4 font-semibold text-slate-900 dark:text-slate-100">
                    Refusal #{refusal.step}
                  </td>
                  <td className="py-3.5 px-3 text-slate-700 dark:text-slate-300">
                    {refusal.code}
                  </td>
                  <td className="py-3.5 px-3 font-sans text-slate-600 dark:text-slate-300">
                    {refusal.detail}
                  </td>
                  <td className="py-3.5 pl-3 text-right">
                    <span
                      className={
                        refusal.status === 'FIXED'
                          ? 'text-emerald-500 font-semibold'
                          : 'text-rose-500 font-semibold'
                      }
                    >
                      {refusal.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Defect Control Registry (genesis-defect-controls.json) */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              02. Defect Control Registry Inspector (genesis-defect-controls.json · 32.0 KB)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Transitioning these three controls from <code className="font-mono">CONTROL_PROPOSED</code> to{' '}
              <code className="font-mono">CONTROL_VERIFIED</code> unblocks releases across <code className="font-mono">argon</code>,{' '}
              <code className="font-mono">idp</code>, and <code className="font-mono">argon-sync</code>.
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
            Registry State: <strong className="text-slate-200">{state.argonGate.registryMode}</strong>
          </div>
        </div>

        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {state.argonGate.defects.map((defect) => (
            <div key={defect.id} className="py-5 first:pt-0 last:pb-0 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="space-y-1.5 max-w-3xl">
                <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">{defect.id}</span>
                  <span aria-hidden="true">·</span>
                  <span>repo={defect.repo}</span>
                  <span aria-hidden="true">·</span>
                  <span>severity={defect.severity}</span>
                  <span aria-hidden="true">·</span>
                  <span>{defect.verificationHash}</span>
                </div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {defect.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  <strong>Mitigation Rule:</strong> {defect.remediationRule}
                </p>
                <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  Check: <code>{defect.verificationCommand}</code>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span
                  className={`text-xs font-mono font-semibold ${
                    defect.status === 'CONTROL_VERIFIED'
                      ? 'text-emerald-500'
                      : 'text-amber-500'
                  }`}
                >
                  {defect.status}
                </span>
                <button
                  type="button"
                  onClick={() =>
                    onResolveDefect(
                      defect.id,
                      defect.status === 'CONTROL_VERIFIED' ? 'CONTROL_PROPOSED' : 'CONTROL_VERIFIED'
                    )
                  }
                  className="px-3.5 py-2 text-xs font-medium text-slate-900 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                >
                  {defect.status === 'CONTROL_VERIFIED' ? 'Re-Open Control' : `Verify ${defect.id}`}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Commit Trailer Validator (Refusal #1 & #2) */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
        <div className="pb-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            03. Genesis Pre-Push Trailer Synthesizer (Refusals #1 & #2)
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Validates commit message trailers before <code className="font-mono">git push origin propose/*</code> so{' '}
            <code className="font-mono">Genesis-Change-Class</code> never uses rejected values like <code className="font-mono">tooling</code>.
          </p>
        </div>

        <form onSubmit={handleTrailerSubmit} className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="trailer-instruction-id"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Genesis-Instruction-Id
            </label>
            <input
              id="trailer-instruction-id"
              type="text"
              value={draftTrailers.instructionId}
              onChange={(e) => setDraftTrailers({ ...draftTrailers, instructionId: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="trailer-change-class"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Genesis-Change-Class (Allowed Enum)
            </label>
            <select
              id="trailer-change-class"
              value={draftTrailers.changeClass}
              onChange={(e) => setDraftTrailers({ ...draftTrailers, changeClass: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            >
              {ALLOWED_GENESIS_CHANGE_CLASSES.map((cls) => (
                <option key={cls} value={cls}>
                  {cls}
                </option>
              ))}
              <option value="tooling">tooling (invalid — triggers Refusal #2)</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="trailer-verification"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Genesis-Verification
            </label>
            <input
              id="trailer-verification"
              type="text"
              value={draftTrailers.verification}
              onChange={(e) => setDraftTrailers({ ...draftTrailers, verification: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="trailer-artifacts"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Genesis-Artifacts
            </label>
            <input
              id="trailer-artifacts"
              type="text"
              value={draftTrailers.artifacts}
              onChange={(e) => setDraftTrailers({ ...draftTrailers, artifacts: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="md:col-span-2 flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="text-xs font-mono">
              {trailerValidation.valid ? (
                <span className="text-emerald-500">Trailers valid for Argon pre-push hook</span>
              ) : (
                <span className="text-rose-500">{trailerValidation.errors.join(' ')}</span>
              )}
            </div>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              Apply Commit Trailers
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};
