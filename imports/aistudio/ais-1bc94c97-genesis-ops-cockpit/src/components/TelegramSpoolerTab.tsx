import React, { useState } from 'react';
import {
  Send,
  Play,
  Pause,
  RotateCcw,
  ShieldCheck,
  Radio,
  Clock,
  Mic,
  CheckCheck,
  Download,
  Check,
} from 'lucide-react';
import { TelegramVoiceNote } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface TelegramSpoolerTabProps {
  voiceNotes: TelegramVoiceNote[];
  onPlayVoiceNote: (note: TelegramVoiceNote) => void;
  onSendFounderVoiceMemo: (text: string) => void;
}

export const TelegramSpoolerTab: React.FC<TelegramSpoolerTabProps> = ({
  voiceNotes,
  onPlayVoiceNote,
  onSendFounderVoiceMemo,
}) => {
  const [playingNoteId, setPlayingNoteId] = useState<string | null>(null);
  const [founderInput, setFounderInput] = useState('');
  const [dispatchedToast, setDispatchedToast] = useState(false);

  const handlePlayToggle = (note: TelegramVoiceNote) => {
    if (playingNoteId === note.id) {
      audioEngine.stop();
      setPlayingNoteId(null);
    } else {
      audioEngine.playBrief(note.spokenScript, note.durationSec);
      setPlayingNoteId(note.id);
      onPlayVoiceNote(note);
    }
  };

  const handleSendMemo = (e: React.FormEvent) => {
    e.preventDefault();
    if (!founderInput.trim()) return;
    onSendFounderVoiceMemo(founderInput.trim());
    audioEngine.playTacticalCue('action');
    setFounderInput('');
    setDispatchedToast(true);
    setTimeout(() => setDispatchedToast(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Surface Header Banner */}
      <div className="bg-zinc-900/60 border border-zinc-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Send className="w-4 h-4 text-emerald-400" />
            <span>Surface Two: Telegram Voice Notes (`genesis-host-spooler`)</span>
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            WeChat / Telegram async voice delivery. Survives killed or disconnected agent sessions because each audio file persists on disk with its SHA-256 hash.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono text-zinc-400">
          <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>SPOOLER: 140ms LATENCY</span>
          </span>
          <span className="text-zinc-500">•</span>
          <span>ESTATE DISK: PERSISTED</span>
        </div>
      </div>

      {/* Telegram Chat Simulation Interface */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 shadow-2xl overflow-hidden flex flex-col h-[520px]">
        {/* Telegram Chat Header */}
        <div className="px-4 py-3 bg-zinc-900/90 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-xs text-zinc-950 shadow">
              GH
            </div>
            <div>
              <div className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                <span>Genesis Host Spooler</span>
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
              </div>
              <div className="text-[11px] text-zinc-400 font-mono">
                5 legions online • Automated Spool Active
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-zinc-500">
            @genesis_ops_bot
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <div className="text-center">
            <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded-full bg-zinc-900 text-zinc-500 border border-zinc-800">
              Today — Spoken Session Ledger
            </span>
          </div>

          {voiceNotes.map((note) => {
            const isPlaying = playingNoteId === note.id;

            return (
              <div key={note.id} className="flex flex-col items-start max-w-lg">
                {/* Author Pill */}
                <div className="flex items-center gap-2 mb-1 px-1 text-[11px] font-mono text-zinc-400">
                  <span className="text-emerald-400 font-semibold">{note.legionName}</span>
                  <span>•</span>
                  <span>{note.timestamp}</span>
                </div>

                {/* Telegram Audio Bubble */}
                <div className="w-full bg-zinc-900 border border-zinc-800/80 rounded-2xl rounded-tl-sm p-3.5 space-y-2.5 shadow-md">
                  {/* Play & Waveform Row */}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handlePlayToggle(note)}
                      className={`h-11 w-11 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-95 shadow ${
                        isPlaying
                          ? 'bg-emerald-500 text-zinc-950'
                          : 'bg-emerald-950/70 border border-emerald-600/50 text-emerald-300 hover:bg-emerald-900'
                      }`}
                    >
                      {isPlaying ? (
                        <Pause className="w-5 h-5 fill-current" />
                      ) : (
                        <Play className="w-5 h-5 fill-current ml-0.5" />
                      )}
                    </button>

                    {/* Waveform Bars */}
                    <div className="flex-1 flex items-center gap-1 h-8">
                      {Array.from({ length: 32 }).map((_, idx) => {
                        const heights = [8, 14, 20, 24, 16, 28, 22, 12, 18, 26, 14, 10, 22, 18, 24, 16];
                        const barH = heights[idx % heights.length];
                        return (
                          <div
                            key={idx}
                            className={`w-1 rounded-full transition-all duration-200 ${
                              isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-700'
                            }`}
                            style={{ height: `${barH}px` }}
                          />
                        );
                      })}
                    </div>

                    <div className="text-xs font-mono text-zinc-400 shrink-0">
                      {note.durationSec}s
                    </div>
                  </div>

                  {/* Summary Snippet */}
                  <div className="text-xs text-zinc-300 leading-normal bg-zinc-950/60 p-2 rounded-lg border border-zinc-850">
                    "{note.summarySnippet}"
                  </div>

                  {/* Receipt Hash & Delivery Status */}
                  <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-1 border-t border-zinc-850">
                    <div className="flex items-center gap-1 text-zinc-400">
                      <ShieldCheck className="w-3 h-3 text-emerald-400" />
                      <span>sha256:{note.voiceFileSha256.slice(0, 8)}...</span>
                    </div>

                    <div className="flex items-center gap-1 text-emerald-400">
                      <span>Delivered</span>
                      <CheckCheck className="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Telegram Input Bar (Founder Voice Memo & Directives) */}
        <div className="p-3 bg-zinc-900 border-t border-zinc-800">
          <form onSubmit={handleSendMemo} className="flex items-center gap-2">
            <input
              type="text"
              value={founderInput}
              onChange={(e) => setFounderInput(e.target.value)}
              placeholder="Send founder voice directive back to legions..."
              className="flex-1 bg-zinc-950 border border-zinc-700 rounded-full px-4 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 font-sans"
            />
            <button
              type="submit"
              disabled={!founderInput.trim()}
              className="h-9 w-9 rounded-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-zinc-950 flex items-center justify-center transition-colors shrink-0 shadow"
              title="Dispatch to Legion Spooler"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </form>

          {dispatchedToast && (
            <div className="mt-2 text-xs text-emerald-400 font-mono text-center flex items-center justify-center gap-1">
              <Check className="w-3.5 h-3.5" />
              <span>Voice note delivered to genesis-host-spooler!</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
