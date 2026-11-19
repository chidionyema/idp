import React, { useState } from 'react';
import {
  X,
  Lock,
  Unlock,
  CheckCircle2,
  Clock,
  GitPullRequest,
  Cpu,
  ShieldAlert,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { EstateTelemetry } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface DofGateModalProps {
  telemetry: EstateTelemetry;
  isOpen: boolean;
  onClose: () => void;
  onUnblockGate: () => void;
}

export const DofGateModal: React.FC<DofGateModalProps> = ({
  telemetry,
  isOpen,
  onClose,
  onUnblockGate,
}) => {
  const [unblocking, setUnblocking] = useState(false);
  const [unblockedSuccess, setUnblockedSuccess] = useState(telemetry.dofGate.status !== 'LOCKED_AWAITING_CREDENTIAL');

  if (!isOpen) return null;

  const handleSimulateCredential = () => {
    setUnblocking(true);
    audioEngine.playTacticalCue('gate');

    setTimeout(() => {
      onUnblockGate();
      setUnblocking(false);
      setUnblockedSuccess(true);
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-xl bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg border ${unblockedSuccess ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400' : 'bg-rose-950/60 border-rose-800 text-rose-400'}`}>
              {unblockedSuccess ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
            </div>
            <div>
              <h2 className="text-sm font-bold text-zinc-100 font-mono">
                DOF-GATE STATUS & PR PIPELINE
              </h2>
              <div className="text-[11px] text-zinc-400 font-mono">
                Estate Pipeline Gatekeeper • Enclave Protected
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-zinc-400 hover:text-zinc-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Status Banner */}
          <div className={`p-4 rounded-xl border ${unblockedSuccess ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200' : 'bg-rose-950/30 border-rose-800/60 text-rose-200'}`}>
            <div className="flex items-center justify-between font-mono text-xs font-semibold mb-1">
              <span>GATE POSTURE:</span>
              <span>{unblockedSuccess ? 'UNBLOCKED & MERGING' : 'LOCKED — AWAITING CREDENTIAL'}</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed font-sans">
              {unblockedSuccess
                ? 'Credential verified! The gate is open. All pending lanes (Piper ARM VM and Voice Bar) are landing directly into main.'
                : 'As described in the architecture plan: "this queues behind the same gate as everything else — the credential unblocks the lanes, and the voice work lands as PRs right after."'}
            </p>
          </div>

          {/* Queued PRs waiting on Gate */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-zinc-300 font-mono flex items-center justify-between">
              <span>Lanes Queued Behind DOF-Gate</span>
              <span className="text-[11px] text-zinc-500 font-normal">
                {unblockedSuccess ? 'All Lanes Cleared' : '3 PRs Blocked'}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              {/* PR 1 */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-900 border border-zinc-800 font-mono">
                <div className="flex items-center gap-2">
                  <GitPullRequest className="w-4 h-4 text-sky-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-zinc-200">PR #412: Piper ARM VM Neural TTS Lane</div>
                    <div className="text-[11px] text-zinc-500">Fast 4-core neural voices, $0 estate compute</div>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${unblockedSuccess ? 'bg-emerald-950 border border-emerald-800 text-emerald-300' : 'bg-rose-950 border border-rose-800 text-rose-300'}`}>
                  {unblockedSuccess ? 'Merged' : 'Blocked'}
                </span>
              </div>

              {/* PR 2 */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-900 border border-zinc-800 font-mono">
                <div className="flex items-center gap-2">
                  <GitPullRequest className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-zinc-200">PR #415: Genesis Surface Voice Bar</div>
                    <div className="text-[11px] text-zinc-500">Ops cockpit audio bar with zero-infra SpeechSynthesis</div>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${unblockedSuccess ? 'bg-emerald-950 border border-emerald-800 text-emerald-300' : 'bg-rose-950 border border-rose-800 text-rose-300'}`}>
                  {unblockedSuccess ? 'Merged' : 'Blocked'}
                </span>
              </div>

              {/* PR 3 */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-900 border border-zinc-800 font-mono">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-amber-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-zinc-200">Hook: genesis-host-spooler Telegram Lane</div>
                    <div className="text-[11px] text-zinc-500">Persistent voice notes surviving dead agent sessions</div>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded uppercase ${unblockedSuccess ? 'bg-emerald-950 border border-emerald-800 text-emerald-300' : 'bg-rose-950 border border-rose-800 text-rose-300'}`}>
                  {unblockedSuccess ? 'Active' : 'Blocked'}
                </span>
              </div>
            </div>
          </div>

          {/* Action Button */}
          {!unblockedSuccess && (
            <div className="pt-2">
              <button
                onClick={handleSimulateCredential}
                disabled={unblocking}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-zinc-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
              >
                {unblocking ? (
                  <>
                    <Zap className="w-4 h-4 animate-spin" />
                    <span>Unblocking Credential Enclave...</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-4 h-4" />
                    <span>Authorize Credential & Reopen DOF-Gate Now</span>
                  </>
                )}
              </button>
            </div>
          )}

          {unblockedSuccess && (
            <div className="p-3 bg-zinc-900 rounded-lg text-xs font-mono text-emerald-400 flex items-center justify-between">
              <span>All 3 PR lanes successfully promoted to main.</span>
              <button
                onClick={onClose}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition-colors"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
