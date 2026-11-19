import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Sliders, Volume2 } from 'lucide-react';
import type { ActiveDisruptiveIncident } from '../engine/beastGovernor';
import { playSovereignChime } from '../utils/sovereignAudio';

interface AllSurfaceIncidentBannerProps {
  incident: ActiveDisruptiveIncident | null;
  audioEnabled: boolean;
  onResolveAuto: () => Promise<void>;
  onLoosenDialOverride: () => Promise<void>;
  onOpenBeastTab: () => void;
}

export const AllSurfaceIncidentBanner: React.FC<AllSurfaceIncidentBannerProps> = ({
  incident,
  audioEnabled,
  onResolveAuto,
  onLoosenDialOverride,
  onOpenBeastTab,
}) => {
  const [resolving, setResolving] = useState(false);
  const [expandedTrace, setExpandedTrace] = useState(true);
  const lastSoundedIncidentId = useRef<string | null>(null);

  useEffect(() => {
    if (incident && incident.incidentId !== lastSoundedIncidentId.current) {
      lastSoundedIncidentId.current = incident.incidentId;
      playSovereignChime('incident_klaxon', audioEnabled);
    }
    if (!incident) {
      lastSoundedIncidentId.current = null;
    }
  }, [incident, audioEnabled]);

  if (!incident) return null;

  const diag = incident.diagnosisPack;

  const handleAutoFix = async () => {
    setResolving(true);
    try {
      await onResolveAuto();
      playSovereignChime('execute', audioEnabled);
    } finally {
      setResolving(false);
    }
  };

  const handleLoosenOverride = async () => {
    setResolving(true);
    try {
      await onLoosenDialOverride();
      playSovereignChime('clarify', audioEnabled);
    } finally {
      setResolving(false);
    }
  };

  return (
    <section
      role="alert"
      aria-live="assertive"
      aria-label="All-Surface Sovereign Incident Interrupt"
      className="w-full bg-red-50 dark:bg-[#22080D] border-b border-red-300 dark:border-red-800 text-slate-900 dark:text-slate-100 px-4 sm:px-6 lg:px-8 py-4"
    >
      <div className="max-w-[1380px] mx-auto space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono tabular-nums text-red-700 dark:text-red-300">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600 dark:text-red-400" aria-hidden="true" />
              <span className="font-semibold">ALL-SURFACE ACTION REQUIRED</span>
              <span aria-hidden="true">·</span>
              <span>{incident.incidentId}</span>
              <span aria-hidden="true">·</span>
              <span>Intercepted in {incident.detectionLeadTimeMs.toFixed(2)} ms</span>
              <span aria-hidden="true">·</span>
              <span>{incident.allSurfacesInterrupted}/{incident.allSurfacesInterrupted} Surfaces Halted</span>
              <span aria-hidden="true">·</span>
              <span>Woke {diag.selectedWakeupSurface} ({diag.wakeupElapsedMs.toFixed(1)} ms)</span>
            </div>

            <h2 className="text-sm sm:text-base font-bold text-red-900 dark:text-red-100">
              {incident.headline}
            </h2>
            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed max-w-4xl">
              {incident.detail}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={resolving}
              onClick={handleAutoFix}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-500 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
              {resolving ? 'Coordinating Fix...' : 'Execute Auto-Remediation & Seal Proof'}
            </button>

            {incident.faultKind === 'UNEVALUATED_SESSION' && (
              <button
                type="button"
                disabled={resolving}
                onClick={handleLoosenOverride}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-red-900 dark:text-red-200 bg-white dark:bg-red-950/80 border border-red-300 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900/60 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                <Sliders className="w-3.5 h-3.5" aria-hidden="true" />
                Loosen Eval Dial Override
              </button>
            )}

            <button
              type="button"
              onClick={() => playSovereignChime('incident_klaxon', true)}
              aria-label="Replay audible incident alert tone"
              className="inline-flex items-center gap-1.5 px-2.5 py-2 text-xs font-medium text-red-800 dark:text-red-200 bg-white/80 dark:bg-red-950/60 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5" aria-hidden="true" />
              Test Tone
            </button>

            <button
              type="button"
              onClick={onOpenBeastTab}
              className="px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Open Beast Console
            </button>

            <button
              type="button"
              onClick={() => setExpandedTrace((v) => !v)}
              aria-expanded={expandedTrace}
              aria-label={expandedTrace ? 'Collapse diagnosis pack trace' : 'Expand diagnosis pack trace'}
              className="p-2 text-red-800 dark:text-red-200 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-lg transition-colors shrink-0"
            >
              {expandedTrace ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {expandedTrace && (
          <div className="pt-2.5 border-t border-red-200 dark:border-red-900/80 grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1">
              <div className="font-mono tabular-nums text-[11px] text-red-800 dark:text-red-300">
                Diagnosis Pack: {diag.diagPackId} · Layer: {diag.failingLayer} · Rule: {diag.violatedRegoRule}
              </div>
              <div className="text-slate-700 dark:text-slate-300">
                <span className="font-semibold">Scoped Task:</span> {diag.scopedTaskObjective}
              </div>
              <div className="font-mono text-[11px] text-slate-600 dark:text-slate-400">
                Repro: {diag.reproductionCommand}
              </div>
            </div>

            <div className="space-y-1">
              <div className="font-semibold text-red-900 dark:text-red-200">
                Millisecond Wake-Up Cascade ({diag.selectedWakeupSurface}):
              </div>
              <ul className="space-y-0.5 font-mono tabular-nums text-[11px] text-slate-700 dark:text-slate-300">
                {diag.wakeupCascadeTrace.map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
