import React from 'react';
import { InstructionExecutionResult } from '../engine/protocolEngine';
import { CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, Terminal, Clock } from 'lucide-react';

interface EphemeralActionCardProps {
  result: InstructionExecutionResult;
  onDismiss?: () => void;
  onExecuteNext?: (text: string) => void;
}

export const EphemeralActionCard: React.FC<EphemeralActionCardProps> = ({
  result,
  onDismiss,
  onExecuteNext,
}) => {
  return (
    <div
      className={`w-full max-w-2xl rounded-2xl p-6 backdrop-blur-2xl transition-all duration-300 border ${
        result.ok
          ? 'bg-slate-900/80 border-emerald-500/30 shadow-[0_8px_32px_rgba(16,185,129,0.12)]'
          : 'bg-rose-950/40 border-rose-500/40 shadow-[0_8px_32px_rgba(244,63,94,0.12)]'
      }`}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          {result.ok ? (
            <div className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-xs uppercase tracking-wider font-semibold">
                Instruction Cryptographically Sealed
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-rose-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-xs uppercase tracking-wider font-semibold">
                Execution Rejected (HTTP {result.httpStatus})
              </span>
            </div>
          )}
        </div>

        {result.instructionId && (
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <Terminal className="w-3.5 h-3.5" />
            <span>{result.instructionId}</span>
          </div>
        )}
      </div>

      {/* Main body content */}
      <div className="space-y-4">
        {result.ok ? (
          <>
            <div>
              <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">
                Proposed Sovereign Action
              </div>
              <p className="text-sm font-medium text-slate-100 leading-relaxed">
                {result.proposedAction}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-1">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-emerald-400" />
                  <span>Execution Lane State</span>
                </div>
                <div className="text-xs font-mono text-emerald-300">
                  {result.executionStatus}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-1">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-cyan-400" />
                  <span>Assurance Door</span>
                </div>
                <div className="text-xs font-mono text-cyan-300 truncate">
                  3-Shield Council / Legion IDP #7664
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/20">
              <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 mb-1">
                Verified Outcome
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {result.verifiedOutcome}
              </p>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="text-xs font-mono text-rose-300 bg-rose-950/40 p-3 rounded-xl border border-rose-500/20">
              <span className="font-semibold">{result.errorCode}</span>: {result.errorMessage}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Instruction execution failed closed. No unverified mutations were written to Cloudflare Pages or downstream GitOps repositories.
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between border-t border-white/10 pt-4 mt-5">
        <div className="text-[11px] font-mono text-slate-400">
          {result.ok ? 'Provable state recorded' : 'Audit error logged'}
        </div>

        <div className="flex items-center gap-2">
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              Clear
            </button>
          )}

          {result.ok && onExecuteNext && (
            <button
              onClick={() => onExecuteNext('Verify Legion job execution status')}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors"
            >
              <span>Follow up</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
