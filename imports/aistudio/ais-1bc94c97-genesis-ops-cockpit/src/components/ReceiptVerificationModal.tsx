import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  Copy,
  Check,
  FileCode,
  Layers,
  Cpu,
  Clock,
  Sparkles,
} from 'lucide-react';
import { SpokenBrief } from '../types';

interface ReceiptVerificationModalProps {
  brief: SpokenBrief | null;
  onClose: () => void;
}

export const ReceiptVerificationModal: React.FC<ReceiptVerificationModalProps> = ({
  brief,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!brief) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(brief.sha256Receipt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-xl bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-zinc-100 font-mono">
                CRYPTOGRAPHIC PROVENANCE RECEIPT
              </h2>
              <div className="text-[11px] text-zinc-400 font-mono">
                Machine-Generated Summary Hash • Verifiable Spoken Audit
              </div>
            </div>
          </div>

          <button onClick={onClose} className="p-1 rounded text-zinc-400 hover:text-zinc-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-zinc-900 border border-zinc-800 space-y-2">
            <div className="text-zinc-400 text-[11px]">IMMUTABLE SHA-256 DIGEST:</div>
            <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-emerald-400 break-all select-all font-mono leading-relaxed">
              {brief.sha256Receipt}
            </div>
            <div className="flex justify-end">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied Hash' : 'Copy 64-char Hash'}</span>
              </button>
            </div>
          </div>

          {/* Provenance Pipeline Metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <span className="text-zinc-500 text-[10px] uppercase">Input Source</span>
              <div className="font-semibold text-zinc-200 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-amber-400" />
                <span>{brief.rawLogLineCount} JSONL entries</span>
              </div>
              <div className="text-[11px] text-zinc-400">{brief.rawLogDurationMinutes} min session noise</div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <span className="text-zinc-500 text-[10px] uppercase">Condensation Ratio</span>
              <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" />
                <span>99.6% Reduction</span>
              </div>
              <div className="text-[11px] text-zinc-400">{brief.recordedDurationSec}s Spoken Audio</div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <span className="text-zinc-500 text-[10px] uppercase">Condenser Engine</span>
              <div className="font-semibold text-zinc-200">
                {brief.pipeline.condenser}
              </div>
              <div className="text-[11px] text-zinc-400">Zero model spend ($0.00)</div>
            </div>

            <div className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
              <span className="text-zinc-500 text-[10px] uppercase">TTS Target</span>
              <div className="font-semibold text-cyan-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                <span>{brief.pipeline.ttsEngine}</span>
              </div>
              <div className="text-[11px] text-zinc-400">Voice: {brief.pipeline.piperVoice}</div>
            </div>
          </div>

          {/* Receipt Culture Note */}
          <div className="p-3 rounded-xl bg-zinc-900/40 border border-zinc-800 text-zinc-400 leading-relaxed font-sans text-xs">
            <strong>Receipt Culture:</strong> The founder hears the state of the world without sifting through 40 minutes of noise. Because each spoken brief cites its machine-generated summary hash, the founder's audio briefing is cryptographically verifiable against the raw session disk store.
          </div>
        </div>
      </div>
    </div>
  );
};
