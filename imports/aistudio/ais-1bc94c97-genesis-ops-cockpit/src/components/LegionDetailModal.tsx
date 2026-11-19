import React, { useState } from 'react';
import {
  X,
  Play,
  Volume2,
  CheckCircle2,
  AlertTriangle,
  Lock,
  GitPullRequest,
  ShieldCheck,
  Send,
  Sparkles,
  Mic,
  Copy,
  Check,
} from 'lucide-react';
import { SpokenBrief } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface LegionDetailModalProps {
  brief: SpokenBrief;
  onClose: () => void;
  onApproveFounderAction: (briefId: string, actionId: string) => void;
  onSendToTelegram: (brief: SpokenBrief) => void;
  geminiEnrichmentEnabled: boolean;
}

export const LegionDetailModal: React.FC<LegionDetailModalProps> = ({
  brief,
  onClose,
  onApproveFounderAction,
  onSendToTelegram,
  geminiEnrichmentEnabled,
}) => {
  const [founderVoiceMemo, setFounderVoiceMemo] = useState('');
  const [memoSent, setMemoSent] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  const handleCopyHash = () => {
    navigator.clipboard.writeText(brief.sha256Receipt);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleSendDirective = (e: React.FormEvent) => {
    e.preventDefault();
    if (!founderVoiceMemo.trim()) return;
    audioEngine.playTacticalCue('action');
    setMemoSent(true);
    setTimeout(() => {
      setFounderVoiceMemo('');
      setMemoSent(false);
    }, 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800/80 text-sky-400 font-mono text-xs">
                {brief.legionName}
              </span>
              <h2 className="text-base font-bold text-zinc-100">{brief.title}</h2>
            </div>
            <div className="text-xs text-zinc-400 font-mono mt-1 flex items-center gap-3">
              <span>Duration: {brief.recordedDurationSec}s</span>
              <span>•</span>
              <span>Raw JSONL: {brief.rawLogLineCount} entries ({brief.rawLogDurationMinutes} min window)</span>
              <span>•</span>
              <span className="text-emerald-400">$0 Estate Compute</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Spoken Brief Script Card */}
          <div className="p-4 rounded-xl bg-zinc-900/70 border border-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-zinc-300 font-mono flex items-center gap-1.5">
                <Volume2 className="w-4 h-4 text-sky-400" />
                Spoken Brief Transcript ({brief.recordedDurationSec}s)
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => audioEngine.playBrief(brief.spokenScript, brief.recordedDurationSec, brief.karaokeLines)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-sky-500 hover:bg-sky-400 text-zinc-950 text-xs font-semibold shadow transition-colors"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Play in Voice Bar</span>
                </button>
                <button
                  onClick={() => onSendToTelegram(brief)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition-colors"
                  title="Push audio note to genesis-host-spooler Telegram lane"
                >
                  <Send className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Spool to Telegram</span>
                </button>
              </div>
            </div>

            <p className="text-sm text-zinc-200 leading-relaxed font-sans bg-zinc-950/60 p-3 rounded-lg border border-zinc-850">
              "{brief.spokenScript}"
            </p>

            {/* Cryptographic Hash Citation */}
            <div className="mt-3 flex items-center justify-between text-xs font-mono bg-zinc-950 p-2.5 rounded-lg border border-zinc-800 text-zinc-400">
              <div className="flex items-center gap-2 truncate mr-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-zinc-500 shrink-0">RECEIPT HASH:</span>
                <span className="text-zinc-200 truncate">{brief.sha256Receipt}</span>
              </div>
              <button
                onClick={handleCopyHash}
                className="flex items-center gap-1 text-zinc-400 hover:text-white px-2 py-0.5 rounded hover:bg-zinc-850 shrink-0 text-[11px]"
              >
                {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedHash ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Three Pillars: What Shipped, What's Blocked, Needs Founder */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 1. What Shipped */}
            <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 mb-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>WHAT SHIPPED</span>
              </div>
              <div className="space-y-2">
                {brief.sections.whatShipped.map((item) => (
                  <div key={item.id} className="text-xs text-zinc-300 bg-zinc-950/50 p-2 rounded border border-zinc-850">
                    <div className="font-medium">{item.text}</div>
                    <div className="flex items-center justify-between mt-1 text-[10px] text-zinc-500 font-mono">
                      <span>{item.impact}</span>
                      {item.commitHash && <span className="text-sky-400">commit {item.commitHash}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. What's Blocked */}
            <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-400 mb-2">
                <Lock className="w-4 h-4" />
                <span>WHAT'S BLOCKED</span>
              </div>
              <div className="space-y-2">
                {brief.sections.whatIsBlocked.map((item) => (
                  <div key={item.id} className="text-xs text-zinc-300 bg-zinc-950/50 p-2 rounded border border-zinc-850">
                    <div className="font-medium text-rose-200">{item.text}</div>
                    <div className="mt-1 text-[11px] text-zinc-400 leading-normal">{item.detail}</div>
                    <span className="inline-block mt-1 text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-950 border border-rose-800 text-rose-300">
                      {item.blockerType.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. Needs Founder */}
            <div className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span>NEEDS FOUNDER</span>
              </div>
              <div className="space-y-2">
                {brief.sections.needsFounder.map((action) => (
                  <div
                    key={action.id}
                    className={`text-xs p-2.5 rounded-lg border transition-all ${
                      action.status === 'approved'
                        ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-300'
                        : 'bg-zinc-950 border-amber-500/40 text-zinc-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-zinc-100">{action.title}</span>
                      <span
                        className={`text-[9px] font-mono px-1 rounded uppercase ${
                          action.status === 'approved'
                            ? 'bg-emerald-900 text-emerald-200'
                            : 'bg-amber-900 text-amber-200'
                        }`}
                      >
                        {action.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 mb-2 leading-relaxed">{action.description}</p>

                    {action.status === 'pending' ? (
                      <button
                        onClick={() => onApproveFounderAction(brief.id, action.id)}
                        className="w-full py-1.5 px-2 rounded bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold text-xs flex items-center justify-center gap-1 shadow transition-colors"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>1-Click Approve Action</span>
                      </button>
                    ) : (
                      <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" />
                        <span>Action Approved & Dispatched</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Founder Spoken Voice Directive / Memo Input */}
          <div className="p-4 rounded-xl bg-zinc-900/70 border border-zinc-800">
            <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-2 mb-2">
              <Mic className="w-4 h-4 text-sky-400" />
              <span>Dispatch Founder Voice Directive to {brief.legionName}</span>
            </h4>
            <p className="text-xs text-zinc-400 mb-3">
              Type or speak a voice memo back to the legion. In the WeChat/Telegram model, this memo is synthesized and placed into the agent spooler immediately.
            </p>

            <form onSubmit={handleSendDirective} className="flex gap-2">
              <input
                type="text"
                value={founderVoiceMemo}
                onChange={(e) => setFounderVoiceMemo(e.target.value)}
                placeholder="e.g. 'PR 412 is approved. Proceed with Piper ARM VM lane promotion immediately.'"
                className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-sky-500 font-sans"
              />
              <button
                type="submit"
                disabled={!founderVoiceMemo.trim()}
                className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-zinc-950 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Dispatch</span>
              </button>
            </form>

            {memoSent && (
              <div className="mt-2 text-xs text-emerald-400 font-mono flex items-center gap-1 animate-fade-in">
                <Check className="w-3.5 h-3.5" />
                <span>Directive spooled to {brief.legionName} ring buffer via genesis-host-spooler!</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
