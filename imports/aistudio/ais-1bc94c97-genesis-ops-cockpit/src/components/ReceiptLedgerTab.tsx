import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  FileText,
  Search,
  ExternalLink,
  Play,
} from 'lucide-react';
import { SpokenBrief } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface ReceiptLedgerTabProps {
  briefs: SpokenBrief[];
  onPlayBrief: (brief: SpokenBrief) => void;
}

export const ReceiptLedgerTab: React.FC<ReceiptLedgerTabProps> = ({ briefs, onPlayBrief }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filtered = briefs.filter(
    (b) =>
      b.legionName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.sha256Receipt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-zinc-900/60 border border-zinc-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Cryptographic Receipt & Machine Hash Ledger</span>
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Every 60–90s spoken brief carries an immutable SHA-256 hash calculated over the raw session transcript and executive summary. Hearing it is verifiable.
          </p>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by Legion, title, or hash..."
            className="bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700 w-64"
          />
        </div>
      </div>

      {/* Ledger Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900/90 text-zinc-400 font-mono text-[11px] border-b border-zinc-800">
              <tr>
                <th className="py-3 px-4">Legion & Brief</th>
                <th className="py-3 px-4">SHA-256 Machine Receipt</th>
                <th className="py-3 px-4">Raw Window</th>
                <th className="py-3 px-4">Spoken Length</th>
                <th className="py-3 px-4">Engine & Cost</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-850">
              {filtered.map((brief) => (
                <tr key={brief.id} className="hover:bg-zinc-900/40 transition-colors">
                  {/* Title */}
                  <td className="py-3 px-4">
                    <div className="font-semibold text-zinc-200">{brief.legionName}</div>
                    <div className="text-[11px] text-zinc-400">{brief.title}</div>
                  </td>

                  {/* Hash */}
                  <td className="py-3 px-4 font-mono">
                    <div className="flex items-center gap-1.5 text-zinc-300">
                      <span className="text-emerald-400">sha256:</span>
                      <span className="truncate max-w-[180px]">{brief.sha256Receipt.slice(0, 16)}...</span>
                      <button
                        onClick={() => handleCopy(brief.id, brief.sha256Receipt)}
                        className="text-zinc-500 hover:text-zinc-300 p-1 rounded"
                        title="Copy full 64-char hex hash"
                      >
                        {copiedId === brief.id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </td>

                  {/* Raw Window */}
                  <td className="py-3 px-4 text-zinc-400 font-mono text-[11px]">
                    <div>{brief.rawLogLineCount} JSONL entries</div>
                    <div className="text-zinc-500">{brief.rawLogDurationMinutes} min duration</div>
                  </td>

                  {/* Spoken Duration */}
                  <td className="py-3 px-4 font-mono text-zinc-300">
                    <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[11px]">
                      {brief.recordedDurationSec}s audio
                    </span>
                  </td>

                  {/* Engine & Cost */}
                  <td className="py-3 px-4">
                    <div className="text-zinc-300 font-mono text-[11px]">
                      {brief.pipeline.ttsEngine}
                    </div>
                    <div className="text-[10px] text-emerald-400 font-mono">
                      ${brief.pipeline.estateCostUsd.toFixed(5)} estate spend
                    </div>
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => {
                        onPlayBrief(brief);
                        audioEngine.playBrief(brief.spokenScript, brief.recordedDurationSec, brief.karaokeLines);
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs font-semibold transition-colors"
                    >
                      <Play className="w-3.5 h-3.5 fill-current text-sky-400" />
                      <span>Hear Brief</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
