import React from 'react';
import {
  Play,
  Volume2,
  Lock,
  GitPullRequest,
  AlertTriangle,
  CheckCircle,
  ShieldCheck,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
} from 'lucide-react';
import { Legion, SpokenBrief } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface LegionGridProps {
  legions: Legion[];
  briefs: Record<string, SpokenBrief>;
  activeBriefId: string | null;
  onSelectLegionBrief: (brief: SpokenBrief) => void;
  onOpenTriage: (brief: SpokenBrief) => void;
  onOpenReceipt: (brief: SpokenBrief) => void;
  geminiEnrichmentEnabled: boolean;
}

export const LegionGrid: React.FC<LegionGridProps> = ({
  legions,
  briefs,
  activeBriefId,
  onSelectLegionBrief,
  onOpenTriage,
  onOpenReceipt,
  geminiEnrichmentEnabled,
}) => {
  return (
    <div className="space-y-4">
      {/* Overview Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-900/60 border border-zinc-800/80 p-4 rounded-xl">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <span>Autonomous Agent Legions</span>
            <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono">
              5 Active Units
            </span>
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Press any legion to hear its condensed 60–90s spoken session brief. All briefs cite verifiable machine hashes.
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-zinc-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>2 Merge-Ready / Active</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-400">
            <span className="h-2 w-2 rounded-full bg-rose-400" />
            <span>2 DOF-Gate Queued</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-400">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            <span>1 Spooling</span>
          </div>
        </div>
      </div>

      {/* Grid of Legions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {legions.map((legion) => {
          const brief = briefs[legion.currentBriefId];
          const isPlayingThis = activeBriefId === brief?.id;
          const pendingFounderCount = brief?.sections.needsFounder.filter((f) => f.status === 'pending').length || 0;

          return (
            <div
              key={legion.id}
              className={`group relative rounded-xl border p-4 transition-all duration-200 flex flex-col justify-between ${
                isPlayingThis
                  ? 'bg-zinc-900/90 border-sky-500/60 shadow-lg shadow-sky-500/10'
                  : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70'
              }`}
            >
              {/* Header */}
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-7 w-7 rounded-lg flex items-center justify-center font-bold text-xs"
                      style={{
                        backgroundColor: legion.colorTheme.primary + '20',
                        color: legion.colorTheme.primary,
                        border: `1px solid ${legion.colorTheme.primary}40`,
                      }}
                    >
                      {legion.symbol}
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100 group-hover:text-sky-300 transition-colors">
                        {legion.name}
                      </h3>
                      <div className="text-[11px] font-mono text-zinc-500">
                        {legion.code} • {legion.role}
                      </div>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${
                      legion.status === 'gated'
                        ? 'bg-rose-950/50 border-rose-800/60 text-rose-300'
                        : legion.status === 'merge_ready'
                        ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300'
                        : legion.status === 'blocked'
                        ? 'bg-amber-950/50 border-amber-800/60 text-amber-300'
                        : 'bg-sky-950/50 border-sky-800/60 text-sky-300'
                    }`}
                  >
                    {legion.statusLabel}
                  </span>
                </div>

                {/* Brief Title */}
                {brief && (
                  <div className="my-2.5">
                    <div className="text-xs font-medium text-zinc-300 line-clamp-1">
                      {brief.title}
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
                      {brief.spokenScript}
                    </p>
                  </div>
                )}

                {/* Triage summary stats */}
                {brief && (
                  <div className="my-3 space-y-1.5 text-[11px]">
                    {/* Shipped */}
                    {brief.sections.whatShipped[0] && (
                      <div className="flex items-start gap-1.5 text-zinc-300">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-1">
                          <strong className="text-zinc-200">Shipped:</strong> {brief.sections.whatShipped[0].text}
                        </span>
                      </div>
                    )}

                    {/* Blocked */}
                    {brief.sections.whatIsBlocked[0] && brief.sections.whatIsBlocked[0].blockerType !== 'dependency' && (
                      <div className="flex items-start gap-1.5 text-rose-300">
                        <Lock className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-1">
                          <strong>Blocked:</strong> {brief.sections.whatIsBlocked[0].text}
                        </span>
                      </div>
                    )}

                    {/* Needs Founder */}
                    {pendingFounderCount > 0 && (
                      <div className="flex items-start gap-1.5 text-amber-300 font-medium">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-1">
                          <strong>Needs Founder:</strong> {brief.sections.needsFounder[0].title}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom Actions Bar */}
              <div className="pt-3 border-t border-zinc-800/80 mt-2 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                  <button
                    onClick={() => brief && onOpenReceipt(brief)}
                    className="flex items-center gap-1 hover:text-zinc-200 transition-colors"
                  >
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    <span>sha256:{brief?.sha256Receipt.slice(0, 8)}...</span>
                  </button>

                  <span>{brief?.recordedDurationSec || 60}s Audio Brief</span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Primary: Hear Brief Button */}
                  <button
                    onClick={() => {
                      if (brief) {
                        onSelectLegionBrief(brief);
                        audioEngine.playBrief(brief.spokenScript, brief.recordedDurationSec, brief.karaokeLines);
                      }
                    }}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                      isPlayingThis
                        ? 'bg-sky-500 hover:bg-sky-400 text-zinc-950 shadow-md shadow-sky-500/20'
                        : 'bg-zinc-800 hover:bg-zinc-700 text-white'
                    }`}
                  >
                    {isPlayingThis ? (
                      <>
                        <Volume2 className="w-4 h-4 animate-pulse" />
                        <span>Playing ({brief?.recordedDurationSec}s)</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-current" />
                        <span>Hear Brief ({brief?.recordedDurationSec}s)</span>
                      </>
                    )}
                  </button>

                  {/* Secondary: Inspect Triage & Approvals */}
                  <button
                    onClick={() => brief && onOpenTriage(brief)}
                    className="p-2 rounded-lg bg-zinc-900 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white transition-colors"
                    title="View Shipped / Blocked / Needs Founder & Approve Actions"
                  >
                    <ArrowUpRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
