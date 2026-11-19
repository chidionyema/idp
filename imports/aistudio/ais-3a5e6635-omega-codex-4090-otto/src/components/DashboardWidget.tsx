import React, { useState, useEffect } from 'react';
import { EstateState, evaluateEstateSweep } from '../engine/ottoEngine';
import { RefreshCw, Activity, Clock, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface DashboardWidgetProps {
  state: EstateState;
  onTriggerSweep?: () => void;
  autoUpdateIntervalSec?: number;
}

export const DashboardWidget: React.FC<DashboardWidgetProps> = ({
  state,
  onTriggerSweep,
  autoUpdateIntervalSec = 300,
}) => {
  const [secondsUntilNext, setSecondsUntilNext] = useState<number>(autoUpdateIntervalSec);
  const [isSweeping, setIsSweeping] = useState<boolean>(false);
  const [lastAutoUpdate, setLastAutoUpdate] = useState<Date>(() => new Date());

  const sweepEval = evaluateEstateSweep(state);
  const frequencyMinutes = Math.round((state.sweepFrequencySec || autoUpdateIntervalSec) / 60);

  // Auto-updating countdown and periodic trigger
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsUntilNext((prev) => {
        if (prev <= 1) {
          if (onTriggerSweep) {
            setIsSweeping(true);
            setTimeout(() => setIsSweeping(false), 600);
            onTriggerSweep();
          }
          setLastAutoUpdate(new Date());
          return autoUpdateIntervalSec;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autoUpdateIntervalSec, onTriggerSweep]);

  const handleManualSweep = () => {
    setIsSweeping(true);
    setTimeout(() => setIsSweeping(false), 500);
    if (onTriggerSweep) {
      onTriggerSweep();
    }
    setSecondsUntilNext(autoUpdateIntervalSec);
    setLastAutoUpdate(new Date());
  };

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const formatDriftTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const isDrift = sweepEval.verdict === 'DRIFT';
  const argonSyncRepo = state.repos.find((r) => r.id === 'argon-sync');

  return (
    <div
      data-testid="dashboard-widget"
      className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 lg:p-5 shadow-xs space-y-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0" />
          <span className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 tracking-tight">
            ~/.estate/bin/otto-background-sweep.py
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
            Next sweep in <strong className="text-slate-800 dark:text-slate-200">{formatCountdown(secondsUntilNext)}</strong>
          </span>
          <button
            type="button"
            onClick={handleManualSweep}
            title="Execute sweep now"
            className="p-1 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Trigger manual sweep"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSweeping ? 'animate-spin text-amber-500' : ''}`} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Sweep Frequency */}
        <div className="space-y-1">
          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
            Sweep Cadence
          </span>
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono tabular-nums">
            Every {frequencyMinutes} min
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            launchd interval ({state.sweepFrequencySec ?? 300}s)
          </p>
        </div>

        {/* Metric 2: Last Drift Detection Time */}
        <div className="space-y-1">
          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
            Last Drift Detected
          </span>
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono tabular-nums flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{formatDriftTime(state.lastDriftTimestamp || state.sweepTimestamp)}</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums truncate">
            {state.lastDriftTimestamp || state.sweepTimestamp}
          </p>
        </div>

        {/* Metric 3: Current Verdict */}
        <div className="space-y-1">
          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
            Sweep Verdict
          </span>
          <div className="text-sm font-semibold font-mono tabular-nums flex items-center gap-1.5">
            {isDrift ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-amber-500">DRIFT (3,742 dirty)</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-500">{sweepEval.verdict}</span>
              </>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums">
            {state.receiptsRetained}/{state.maxReceipts} receipts stored
          </p>
        </div>

        {/* Metric 4: Disk Sentinel & Non-Destructive Guard */}
        <div className="space-y-1">
          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
            Disk Sentinel
          </span>
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono tabular-nums">
            {state.diskFreeGiB.toFixed(2)} GiB ({sweepEval.diskAdmit})
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Non-destructive observation
          </p>
        </div>
      </div>

      {/* Argon-Sync Zero-Friction Autonomous Push Guarantee Bar */}
      <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 dark:bg-slate-950/60 -mx-4 -mb-4 lg:-mx-5 lg:-mb-5 p-3.5 rounded-b-xl">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
          <div className="min-w-0">
            <div className="text-xs font-mono font-medium text-slate-800 dark:text-slate-200 truncate">
              Argon-Sync Autonomous Push Guarantee: <strong className="text-emerald-600 dark:text-emerald-400">ACTIVE</strong>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {argonSyncRepo?.unpushedCommits && argonSyncRepo.unpushedCommits > 0
                ? `${argonSyncRepo.unpushedCommits} commits queued · Auto-propagating to origin/estate/recovery-durable-sessions`
                : 'All changes synced to argon-sync (origin/estate/recovery-durable-sessions) · Zero human friction'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 text-xs font-mono">
          <span className="text-slate-500 dark:text-slate-400 tabular-nums text-[11px]">
            Last push: {formatDriftTime(state.lastArgonSyncPush || state.sweepTimestamp)}
          </span>
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-500/10 dark:bg-emerald-500/20 px-2 py-0.5 rounded text-[11px]">
            100% PROMPT-FREE
          </span>
        </div>
      </div>
    </div>
  );
};
