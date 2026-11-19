import React from 'react';
import {
  TrendingDown,
  Clock,
  Repeat,
  HardDrive,
  AlertOctagon,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
} from 'lucide-react';
import { INITIAL_RECURRING_METRICS } from '../protocol/telemetry';

export const DeliveryFrictionAnalytics: React.FC = () => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <TrendingDown className="h-5 w-5 text-rose-400" />
            <h2 className="text-base font-semibold text-white">
              Delivery Friction & Scheduled Overhead Telemetry (MUM-300 / MUM-301)
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Empirical baseline: 33 fresh agent sessions/day overhead, ungrounded cron runs, and repeat loop vulnerabilities.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 font-bold">
            ~19.1 Min/Day Overhead
          </span>
          <span className="px-3 py-1 rounded-lg bg-amber-950/80 border border-amber-800 text-amber-300 font-bold">
            33 Agent Sessions/Day
          </span>
        </div>
      </div>

      {/* Top Level Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1 */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Scheduled Waste</span>
            <Repeat className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">33 runs/day</div>
          <p className="text-[11px] text-slate-400">
            Agents spun up hourly to report <span className="text-amber-400 font-mono">"nothing changed"</span> despite tool returning <span className="text-slate-300 font-mono">posted: false</span>.
          </p>
        </div>

        {/* Card 2 */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Announcement Duplication</span>
            <FileSpreadsheet className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">15 Events / Cycle</div>
          <p className="text-[11px] text-slate-400">
            5 events with unparseable surface ID, 2 duplicate acks under variant spellings; resolved by token registry.
          </p>
        </div>

        {/* Card 3 */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Pre-empted Blockers</span>
            <HardDrive className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">~1.0 GB Disk-Full</div>
          <p className="text-[11px] text-slate-400">
            Duplicate byte-identical installers avoided; shared Git metadata isolated from writable workspace.
          </p>
        </div>
      </div>

      {/* Breakdown Table: Recurring Agent Sessions */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Recurring Scheduled Sessions Breakdown (MUM-300 Missing Cost Class)
        </h3>
        <div className="border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
              <tr>
                <th className="py-2.5 px-4 font-medium">Scheduled Task</th>
                <th className="py-2.5 px-4 font-medium">Frequency</th>
                <th className="py-2.5 px-4 font-medium">Daily Runs</th>
                <th className="py-2.5 px-4 font-medium text-rose-300">Empty ("No Change")</th>
                <th className="py-2.5 px-4 font-medium">Overhead</th>
                <th className="py-2.5 px-4 font-medium">Estate Resolution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70 bg-slate-950/40">
              {INITIAL_RECURRING_METRICS.map((metric) => (
                <tr key={metric.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-white">{metric.taskName}</div>
                    <div className="text-[11px] text-slate-400 font-mono">{metric.id}</div>
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">{metric.cronSchedule}</td>
                  <td className="py-3 px-4 font-mono text-slate-300">{metric.dailyRunCount} runs</td>
                  <td className="py-3 px-4 font-mono text-rose-400 font-medium">
                    {metric.emptyStatusRuns} runs ({Math.round((metric.emptyStatusRuns / metric.dailyRunCount) * 100)}%)
                  </td>
                  <td className="py-3 px-4 font-mono text-amber-300">{metric.overheadMinutesPerDay} min/day</td>
                  <td className="py-3 px-4 text-slate-400 text-[11px]">
                    {metric.recommendation}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Comparison: Legacy Loop Detector vs Hardened Short-Loop (Clause 4) */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Clause 4 Loop Detector Hardening (Empirical Bug Fixes)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Legacy flawed implementation */}
          <div className="p-4 rounded-xl bg-slate-950 border border-rose-900/50 space-y-2">
            <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs">
              <XCircle className="h-4 w-4" />
              <span>Legacy short-loop.sh (Failed Open)</span>
            </div>
            <ul className="text-[11px] text-slate-400 space-y-1.5 list-disc pl-4 font-mono">
              <li>Matched ONLY byte-identical raw terminal output (minor error rewording bypassed it).</li>
              <li>Working directory included in hash (changing directory reset the loop counter).</li>
              <li>Unreadable/corrupt state file disabled loop detection silently without warning.</li>
            </ul>
          </div>

          {/* New Hardened implementation */}
          <div className="p-4 rounded-xl bg-slate-950 border border-emerald-900/50 space-y-2">
            <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-xs">
              <CheckCircle2 className="h-4 w-4" />
              <span>Canonical Protocol ShortLoopDetector</span>
            </div>
            <ul className="text-[11px] text-slate-300 space-y-1.5 list-disc pl-4 font-mono">
              <li>Semantic payload + target capability + evidence digest fingerprinting.</li>
              <li>Folder-agnostic path normalization (directory switching cannot evade check).</li>
              <li>Fails loud with fatal exception on corrupted state store per governance rules.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
