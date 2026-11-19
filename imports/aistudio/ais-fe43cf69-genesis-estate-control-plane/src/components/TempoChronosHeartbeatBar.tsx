import React, { useEffect, useRef } from 'react';
import { Volume2, VolumeX, ArrowUpRight, Radio } from 'lucide-react';
import type {
  BeastSynchronyCatalogState,
  HorizonId,
  PersonaTier,
} from '../engine/beastGovernor';
import {
  playSovereignHeartbeatPulse,
  speakLiveEstateHeadline,
} from '../utils/sovereignAudio';

interface TempoChronosHeartbeatBarProps {
  synchrony: BeastSynchronyCatalogState;
  activePersona: PersonaTier;
  onSelectPersona: (persona: PersonaTier) => void;
  activeHorizon: HorizonId;
  onSelectHorizon: (horizon: HorizonId) => void;
  heartbeatAudioEnabled: boolean;
  onToggleHeartbeatAudio: () => void;
  onDeepLinkNavigate: (deepLinkHash: string) => void;
}

const HORIZON_SHORT_LABELS: Record<HorizonId, string> = {
  '1S_TEMPO': '1s Tempo',
  '1M_PULSE': '1m Pulse',
  '1D_TACTICAL': '1d Tactical',
  '1W_CHRONOS': '1w Chronos',
};

export const TempoChronosHeartbeatBar: React.FC<TempoChronosHeartbeatBarProps> = ({
  synchrony,
  activePersona,
  onSelectPersona,
  activeHorizon,
  onSelectHorizon,
  heartbeatAudioEnabled,
  onToggleHeartbeatAudio,
  onDeepLinkNavigate,
}) => {
  const lastSpokenHeadlineIdRef = useRef<string | null>(null);
  const lastPulseSeqRef = useRef<number>(synchrony.heartbeatSequence);

  const selectedHorizonBucket =
    synchrony.horizons.find((h) => h.horizonId === activeHorizon) ?? synchrony.horizons[0];
  const topHeadline =
    synchrony.rankedHeadlines.find((h) => h.horizonId === activeHorizon) ??
    synchrony.rankedHeadlines[0];

  // Play acoustic heartbeat on authoritative server SSE heartbeat ticks when Founder enables audio
  useEffect(() => {
    if (!heartbeatAudioEnabled) return;
    if (synchrony.heartbeatSequence !== lastPulseSeqRef.current) {
      lastPulseSeqRef.current = synchrony.heartbeatSequence;
      playSovereignHeartbeatPulse(synchrony.heartbeatPosture, true);
    }
  }, [
    heartbeatAudioEnabled,
    synchrony.heartbeatSequence,
    synchrony.heartbeatPosture,
  ]);

  // Speak high-priority headline shifts when audio is enabled
  useEffect(() => {
    if (!heartbeatAudioEnabled || !topHeadline) return;
    if (lastSpokenHeadlineIdRef.current !== topHeadline.headlineId) {
      lastSpokenHeadlineIdRef.current = topHeadline.headlineId;
      speakLiveEstateHeadline(topHeadline.spokenScript, true);
    }
  }, [heartbeatAudioEnabled, topHeadline]);

  const handleHearNow = () => {
    playSovereignHeartbeatPulse(synchrony.heartbeatPosture, true);
    if (topHeadline) {
      window.setTimeout(() => {
        speakLiveEstateHeadline(topHeadline.spokenScript, true);
      }, 280);
    }
  };

  return (
    <section
      aria-label="Tempo and Chronos Multi-Horizon Synchrony Bar"
      className="mb-6 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 space-y-2.5"
    >
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
        {/* Left: Heartbeat Telemetry + Horizon Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono tabular-nums text-slate-700 dark:text-slate-200">
            <Radio
              className={`w-3.5 h-3.5 shrink-0 ${
                synchrony.mathematicallySynchronized
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
              aria-hidden="true"
            />
            <span className="font-semibold">{synchrony.heartbeatBpm} BPM</span>
            <span aria-hidden="true" className="text-slate-400">
              ·
            </span>
            <span className="text-slate-500 dark:text-slate-400">
              Drift {synchrony.founderSystemPhaseDriftMs.toFixed(1)} ms
            </span>
          </div>

          <div
            role="group"
            aria-label="Synchrony Horizon Selector"
            className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg"
          >
            {synchrony.horizons.map((h) => {
              const active = h.horizonId === activeHorizon;
              return (
                <button
                  key={h.horizonId}
                  type="button"
                  onClick={() => onSelectHorizon(h.horizonId)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    active
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-amber-300 shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {HORIZON_SHORT_LABELS[h.horizonId]}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onToggleHeartbeatAudio}
              aria-pressed={heartbeatAudioEnabled}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-colors whitespace-nowrap shrink-0 ${
                heartbeatAudioEnabled
                  ? 'bg-amber-400/15 border-amber-500/40 text-amber-800 dark:text-amber-300'
                  : 'bg-slate-100 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {heartbeatAudioEnabled ? (
                <Volume2 className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />
              )}
              <span>{heartbeatAudioEnabled ? 'Heartbeat Audio On' : 'Heartbeat Audio Muted'}</span>
            </button>

            <button
              type="button"
              onClick={handleHearNow}
              className="px-2.5 py-1 text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Speak Headline
            </button>
          </div>
        </div>

        {/* Right: Progressive 4-Persona Product Lens Switcher */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">
            Menu Persona:
          </span>
          <div
            role="group"
            aria-label="Product Menu Persona Scope"
            className="flex flex-wrap items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg"
          >
            {synchrony.personas.map((p) => {
              const active = p.id === activePersona;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onSelectPersona(p.id)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    active
                      ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {p.shortBadge}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Row: Live Synchronized Horizon Headline + Deep Link */}
      <div className="pt-2 border-t border-slate-200/80 dark:border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div className="min-w-0 flex flex-wrap items-center gap-2 text-slate-700 dark:text-slate-300">
          <span className="font-mono tabular-nums text-[11px] font-semibold text-amber-700 dark:text-amber-400 whitespace-nowrap">
            {selectedHorizonBucket.label}:
          </span>
          <span className="font-mono tabular-nums text-[11px] text-slate-600 dark:text-slate-400 whitespace-nowrap">
            {selectedHorizonBucket.primaryMetric}
          </span>
          <span aria-hidden="true" className="text-slate-400">
            ·
          </span>
          <span className="truncate">{topHeadline?.headline || selectedHorizonBucket.summaryHeadline}</span>
        </div>

        <button
          type="button"
          onClick={() =>
            onDeepLinkNavigate(topHeadline?.deepLinkHash || selectedHorizonBucket.deepLinkHash)
          }
          className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-400 hover:underline whitespace-nowrap shrink-0 self-start sm:self-auto"
        >
          <span>Open Synchrony Deep Link</span>
          <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
};
