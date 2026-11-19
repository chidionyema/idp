import React, { useState, useMemo } from 'react';
import { Calendar, ExternalLink, ArrowUpRight, Search } from 'lucide-react';
import type { ChronosCadenceSlot, VentureSurfaceStatus } from '../types/estate';

interface ChronosVenturesViewProps {
  cadence: ChronosCadenceSlot[];
  ventures: VentureSurfaceStatus[];
  onDispatchVentureAudit: (instructionId: string, title: string, body: string, repo: string) => void;
}

export const ChronosVenturesView: React.FC<ChronosVenturesViewProps> = ({
  cadence,
  ventures,
  onDispatchVentureAudit,
}) => {
  const [ventureQuery, setVentureQuery] = useState('');

  const filteredVentures = useMemo(() => {
    if (!ventureQuery.trim()) return ventures;
    const q = ventureQuery.toLowerCase();
    return ventures.filter(
      (v) =>
        v.name.toLowerCase().includes(q) ||
        v.role.toLowerCase().includes(q) ||
        v.revenueMechanism.toLowerCase().includes(q) ||
        v.primaryRepo.toLowerCase().includes(q)
    );
  }, [ventures, ventureQuery]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-5 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 text-balance">
            Chronos Operating Cadence &amp; Venture Monetization Spine
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Provider-independent operating schedule replacing brittle single-provider reminders, paired with commercial conversion gates.
          </p>
        </div>

        <div className="relative shrink-0">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <input
            type="search"
            aria-label="Filter commercial ventures"
            value={ventureQuery}
            onChange={(e) => setVentureQuery(e.target.value)}
            placeholder="Filter venture or repo…"
            className="pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-[#0B101D] border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
          />
        </div>
      </div>

      {/* Chronos Bounded Weekly Operating Cadence */}
      <section
        aria-labelledby="chronos-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
      >
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <div>
            <h2 id="chronos-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
              01. Chronos / Tempo Durable Operating Cadence (Mon · Tue · Wed · Continuous)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Bounded autonomous routines owned by Estate formations and indexed by machine-readable deliverables.
            </p>
          </div>
          <Calendar className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0" aria-hidden="true" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">
                <th className="py-3 px-5">Cadence Window</th>
                <th className="py-3 px-4">Work Lane &amp; Formation</th>
                <th className="py-3 px-4">Bounded Objective</th>
                <th className="py-3 px-5">Deliverable Contract</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {cadence.map((slot) => (
                <tr key={slot.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-5 align-top whitespace-nowrap">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{slot.day}</div>
                    <div className="font-mono tabular-nums text-slate-500 dark:text-slate-400 mt-0.5">
                      {slot.windowUtc}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 align-top">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">{slot.lane}</div>
                    <div className="font-mono text-cyan-700 dark:text-cyan-400 mt-0.5">
                      Owner: {slot.ownerFormation.toUpperCase()} · {slot.status}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 align-top text-slate-700 dark:text-slate-300 leading-relaxed max-w-sm">
                    {slot.objective}
                  </td>
                  <td className="py-3.5 px-5 align-top text-slate-600 dark:text-slate-400 leading-relaxed max-w-xs">
                    {slot.deliverableContract}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Commercial Ventures & Revenue Pipeline */}
      <section aria-labelledby="ventures-heading" className="space-y-4">
        <div>
          <h2 id="ventures-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
            02. Authoritative Group Portfolio &amp; Commercial Release Gates
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Separates active commercial ventures (Meridian Intelligence, MumChimp, Fieldbooks, Prospector) from historical archives without inventing unverified traction.
          </p>
        </div>

        {filteredVentures.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl">
            No ventures match &ldquo;{ventureQuery}&rdquo;.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {filteredVentures.map((v) => (
              <div
                key={v.id}
                className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col justify-between gap-4"
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                        <span>{v.name}</span>
                        {v.liveUrl && (
                          <a
                            href={v.liveUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Visit ${v.name}`}
                            className="text-slate-400 hover:text-amber-500 dark:hover:text-amber-400"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </h3>
                      <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400">
                        {v.role} · Authority {v.authority} · {v.readinessState}
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-xs space-y-1.5">
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">Revenue Mechanism: </span>
                      <span className="text-slate-600 dark:text-slate-400">{v.revenueMechanism}</span>
                    </div>
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">Current Release Gate: </span>
                      <span className="text-slate-600 dark:text-slate-400">{v.currentBlocker}</span>
                    </div>
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">Next Execution Step: </span>
                      <span className="text-slate-600 dark:text-slate-400">{v.nextAction}</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate">
                    {v.primaryRepo}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      onDispatchVentureAudit(
                        `INS-${v.id.toUpperCase()}`,
                        `Commercial Release Gate: ${v.name}`,
                        `${v.nextAction} Enforce WCAG AA contrast, responsive mobile geometry, and visitor-side conversion verification.`,
                        'chidionyema/idp'
                      )
                    }
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    Run Release Audit
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
