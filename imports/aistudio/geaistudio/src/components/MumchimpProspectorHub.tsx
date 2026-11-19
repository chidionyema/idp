import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
  Microscope,
  Play,
  ShieldAlert,
} from 'lucide-react';
import prospectorManifoldImg from '../assets/images/mumchimp_research_manifold_1794814571484.jpg';
import type {
  LegacyVs2100Comparison,
  MumchimpChannel,
  ProspectorMumchimpSnapshot,
  ResearchDomain,
} from '../engine/prospectorResearchMumchimp';

const CHANNEL_FILTERS: Array<{ id: 'all' | MumchimpChannel; label: string }> = [
  { id: 'all', label: 'All Channels' },
  { id: 'mumchimp_enterprise_brief', label: 'Enterprise Briefs' },
  { id: 'mumchimp_market_radar', label: 'Market Radar' },
  { id: 'legion_supply_feed', label: 'Legion Supply' },
  { id: 'otto_ceo_digest', label: 'CEO Digest' },
];

export function MumchimpProspectorHub() {
  const [snap, setSnap] = useState<ProspectorMumchimpSnapshot | null>(null);
  const [comparison, setComparison] = useState<LegacyVs2100Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningCycle, setRunningCycle] = useState(false);
  const [channelFilter, setChannelFilter] = useState<'all' | MumchimpChannel>('all');
  const [activeSubView, setActiveSubView] = useState<'live_feed' | 'legacy_postmortem'>(
    'live_feed'
  );
  const [imgFailed, setImgFailed] = useState(false);

  // Custom hypothesis submission state
  const [customTitle, setCustomTitle] = useState('');
  const [customClaim, setCustomClaim] = useState('');
  const [customDomain, setCustomDomain] = useState<ResearchDomain>(
    'COMMERCIAL_ENTERPRISE_SIGNALS'
  );
  const [customError, setCustomError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  async function loadHub() {
    try {
      const res = await fetch('/api/prospector/state');
      if (res.ok) {
        const data = (await res.json()) as {
          snapshot: ProspectorMumchimpSnapshot;
          comparison: LegacyVs2100Comparison;
        };
        setSnap(data.snapshot);
        setComparison(data.comparison);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHub();

    // SSE stream keeps Prospector-2100 & Mumchimp live on Chronos H2 beats (zero HTTP polling)
    const source = new EventSource('/api/union/stream');
    source.addEventListener('union_snapshot', () => {
      void fetch('/api/prospector/state')
        .then((r) => (r.ok ? r.json() : null))
        .then(
          (
            next: {
              snapshot: ProspectorMumchimpSnapshot;
              comparison: LegacyVs2100Comparison;
            } | null
          ) => {
            if (next) {
              setSnap(next.snapshot);
            }
          }
        )
        .catch(() => {});
    });
    return () => {
      source.close();
    };
  }, []);

  async function handleRunCycle(injectTrap = false) {
    setRunningCycle(true);
    setCustomError(null);
    try {
      const body = injectTrap
        ? {
            customHypothesis: {
              title: 'Unverified Rumor: 100% Guaranteed Zero-Shot AGI Leak on Social Feed',
              claim:
                'Anonymous social spike claims 100% guaranteed benchmark saturation with unverified held-out split.',
              domain: 'ML_FRONTIER_ARCHITECTURES' as ResearchDomain,
              isConfounderTrap: true,
            },
          }
        : {};
      const res = await fetch('/api/prospector/cycle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const out = (await res.json()) as {
          finding: {
            id: string;
            adversarialCritiqueVerdict: string;
            cycleCostUsd: number;
            publishedToMumchimp: boolean;
          };
          snapshot: ProspectorMumchimpSnapshot;
        };
        setSnap(out.snapshot);
        setActionNotice(
          out.finding.publishedToMumchimp
            ? `Cycle ${out.finding.id} verified ($${out.finding.cycleCostUsd.toFixed(5)} spend) and syndicated live to Mumchimp.`
            : `Cycle ${out.finding.id} QUARANTINED by MagenticBrain critic — confounder trap blocked before Mumchimp.`
        );
      }
    } finally {
      setRunningCycle(false);
    }
  }

  async function handleCustomSubmit(e: React.FormEvent) {
    e.preventDefault();
    setCustomError(null);
    if (customTitle.trim().length < 5) {
      setCustomError('Enter a hypothesis headline of at least 5 characters.');
      return;
    }
    setRunningCycle(true);
    try {
      const res = await fetch('/api/prospector/cycle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customHypothesis: {
            title: customTitle.trim(),
            claim: customClaim.trim() || customTitle.trim(),
            domain: customDomain,
          },
        }),
      });
      if (res.ok) {
        const out = (await res.json()) as {
          finding: { id: string; publishedToMumchimp: boolean };
          snapshot: ProspectorMumchimpSnapshot;
        };
        setSnap(out.snapshot);
        setCustomTitle('');
        setCustomClaim('');
        setActionNotice(
          out.finding.publishedToMumchimp
            ? `Custom hypothesis ${out.finding.id} passed causal verification and syndicated to Mumchimp.`
            : `Custom hypothesis ${out.finding.id} flagged for confounder risk and quarantined.`
        );
      }
    } finally {
      setRunningCycle(false);
    }
  }

  if (loading || !snap) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading Prospector-2100 & Mumchimp">
        <div className="h-56 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white border border-slate-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const visibleArtifacts =
    channelFilter === 'all'
      ? snap.mumchimpFeed
      : snap.mumchimpFeed.filter((a) => a.channel === channelFilter);

  return (
    <div className="space-y-6">
      {/* Hero Banner Split */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch">
          <div className="lg:col-span-7 p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>Mumchimp Commercial Production Hub</span>
                <span aria-hidden="true">·</span>
                <span>{snap.engineVersion}</span>
                <span aria-hidden="true">·</span>
                <span>Chronos Harmonic H2 (2x Beat)</span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 [text-wrap:balance]">
                2100-Grade Autonomous Causal Research Feeding Mumchimp Live.
              </h2>

              <p className="text-sm text-slate-600 leading-relaxed max-w-2xl">
                Replaces the naive single-pass Frontier scraper ($0.048/brief, 23.8% confounder
                rate) with Bayesian EVSI triage, zero-retention sovereign retrieval, and
                MagenticBrain adversarial falsification at $0.00018 mean cycle cost.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 pt-2">
              <button
                type="button"
                disabled={runningCycle}
                onClick={() => handleRunCycle(false)}
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                {runningCycle ? 'Running Cycle…' : 'Run Autonomous 2100 Cycle'}
              </button>

              <button
                type="button"
                disabled={runningCycle}
                onClick={() => handleRunCycle(true)}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                <ShieldAlert className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                Probe Adversarial Hype Trap
              </button>

              <div className="inline-flex items-center gap-1 p-1 bg-slate-100 rounded-md">
                <button
                  type="button"
                  onClick={() => setActiveSubView('live_feed')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                    activeSubView === 'live_feed'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Live Mumchimp Feed
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSubView('legacy_postmortem')}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                    activeSubView === 'legacy_postmortem'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  vs Legacy Naive Post-Mortem
                </button>
              </div>
            </div>

            {actionNotice && (
              <p role="status" className="text-xs font-mono tabular-nums text-emerald-800">
                {actionNotice}
              </p>
            )}
          </div>

          <div className="lg:col-span-5 relative min-h-[210px] bg-slate-100 border-t lg:border-t-0 lg:border-l border-slate-200">
            {!imgFailed ? (
              <img
                src={prospectorManifoldImg}
                alt="Precision optical glass prisms refracting causal research streams"
                referrerPolicy="no-referrer"
                onError={() => setImgFailed(true)}
                className="w-full h-full lg:h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-6 text-slate-700">
                <Microscope className="h-7 w-7 text-blue-600 mb-2" aria-hidden="true" />
                <span className="text-xs font-semibold">Prospector-2100 Optical Triage</span>
              </div>
            )}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 text-white">
              <div className="text-xs font-mono tabular-nums">
                Feed Digest {snap.latestDigestSha256.slice(0, 16)}… · Rego Gate &ge;{' '}
                {snap.minCausalConfidenceGatePct}%
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4-Column KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Autonomous Cycles Executed</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {snap.cyclesCompleted}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            Joined to Chronos H2 beat (every 2 pulses)
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Research Spend vs Legacy Scraper</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-emerald-700">
            {snap.savingsPct}% Saved
          </div>
          <div className="mt-1 text-xs font-mono tabular-nums text-slate-600">
            ${snap.totalCycleSpendUsd.toFixed(4)} actual vs $
            {snap.legacyCounterfactualSpendUsd.toFixed(3)} legacy
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Mumchimp Syndicated Intelligence</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {snap.mumchimpPublishedCount} Live Briefs
          </div>
          <div className="mt-1 text-xs text-slate-600">
            100% SHA-256 source-pinned &amp; deduplicated
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Confounder &amp; Hype Traps Quarantined</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-amber-700">
            {snap.quarantinedTrapsCount} Blocked
          </div>
          <div className="mt-1 text-xs text-slate-600">
            0 false positives admitted to Mumchimp
          </div>
        </div>
      </section>

      {activeSubView === 'legacy_postmortem' && (
        <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-200 pb-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Legacy Naive Prospector Post-Mortem vs Prospector-2100 Architecture
              </h3>
              <p className="text-sm text-slate-600">
                Diagnosing every failure mode of the legacy scraper and verifying its 2100
                replacement.
              </p>
            </div>
            {comparison && (
              <span className="text-xs font-mono tabular-nums font-semibold text-emerald-700">
                {comparison.costMultiplierImprovement}x Cost Efficiency Gain
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="py-2 pr-4 font-medium">Defect Code</th>
                  <th className="py-2 px-4 font-medium">Legacy Naive Failure</th>
                  <th className="py-2 pl-4 font-medium">Prospector-2100 Resolution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {snap.legacyDefects.map((def) => (
                  <tr key={def.code}>
                    <td className="py-3 pr-4 align-top">
                      <div className="font-mono text-xs font-semibold text-slate-900">
                        {def.code}
                      </div>
                      <div className="text-xs font-medium text-slate-700 mt-0.5">{def.title}</div>
                    </td>
                    <td className="py-3 px-4 align-top">
                      <div className="text-xs text-slate-600">{def.legacyNaiveBehavior}</div>
                      <div className="text-xs font-mono tabular-nums text-red-700 mt-1">
                        {def.observedFailureMetric}
                      </div>
                    </td>
                    <td className="py-3 pl-4 align-top">
                      <div className="text-xs text-slate-800">{def.prospector2100Fix}</div>
                      <div className="text-xs font-mono tabular-nums text-emerald-700 mt-1">
                        {def.verified2100Metric}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeSubView === 'live_feed' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Mumchimp Syndicated Production Catalog */}
          <section className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Mumchimp Live Production Syndication Feed
                </h3>
                <p className="text-xs text-slate-500">
                  Only hypotheses passing MagenticBrain adversarial critique (&ge;
                  {snap.minCausalConfidenceGatePct}%) land here.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-md">
                {CHANNEL_FILTERS.map((cf) => (
                  <button
                    key={cf.id}
                    type="button"
                    onClick={() => setChannelFilter(cf.id)}
                    className={`px-2 py-1 text-[11px] font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                      channelFilter === cf.id
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {cf.label}
                  </button>
                ))}
              </div>
            </div>

            {visibleArtifacts.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">
                No syndicated briefs in this channel yet. Click &ldquo;Run Autonomous 2100
                Cycle&rdquo; above to populate.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {visibleArtifacts.map((art) => (
                  <article key={art.artifactId} className="py-4 first:pt-0 last:pb-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-mono tabular-nums">
                      <span className="text-emerald-700 font-medium inline-flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        Syndicated
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>{art.channel}</span>
                      <span aria-hidden="true">·</span>
                      <span>Causal {art.causalConfidencePct}%</span>
                      <span aria-hidden="true">·</span>
                      <span>SHA {art.contentSha256.slice(0, 10)}</span>
                    </div>
                    <h4 className="text-sm font-semibold text-slate-900">{art.headline}</h4>
                    <p className="text-xs text-slate-600 leading-relaxed">{art.summary}</p>
                    <p className="text-xs text-slate-800 font-medium">
                      Commercial Yield: {art.commercialImpactNote}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* Right Column: Custom Hypothesis Lab + Raw Audit Trail (including quarantined traps) */}
          <div className="lg:col-span-5 space-y-6">
            <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
              <div className="flex items-center gap-2">
                <FlaskConical className="h-4 w-4 text-blue-700" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-slate-900">
                  Dispatch Custom Hypothesis to Prospector-2100
                </h3>
              </div>

              <form onSubmit={handleCustomSubmit} noValidate className="space-y-3">
                <div>
                  <label
                    htmlFor="prop-title"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Hypothesis Title
                  </label>
                  <input
                    id="prop-title"
                    type="text"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                    placeholder="e.g. Sub-4bit KV Quantization Preserves Code Pass@1"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="prop-domain"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Research Domain
                  </label>
                  <select
                    id="prop-domain"
                    value={customDomain}
                    onChange={(e) => setCustomDomain(e.target.value as ResearchDomain)}
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  >
                    <option value="COMMERCIAL_ENTERPRISE_SIGNALS">
                      Commercial &amp; Enterprise Signals
                    </option>
                    <option value="ML_FRONTIER_ARCHITECTURES">
                      Machine Learning &amp; Small Ensembles
                    </option>
                    <option value="INTERCLOUD_SPOT_ECONOMICS">
                      InterCloud &amp; Spot Infrastructure
                    </option>
                    <option value="FORMAL_VERIFICATION_REGO">
                      Formal Verification &amp; Rego Governance
                    </option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="prop-claim"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Primary Evidence / Mechanism Note
                  </label>
                  <input
                    id="prop-claim"
                    type="text"
                    value={customClaim}
                    onChange={(e) => setCustomClaim(e.target.value)}
                    placeholder="Optional empirical claim or trap ('unverified rumor' triggers quarantine)"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                  />
                </div>

                {customError && (
                  <p role="alert" className="text-xs font-medium text-red-700">
                    {customError}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={runningCycle}
                  className="w-full rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap disabled:opacity-50"
                >
                  Evaluate EVSI &amp; Run Adversarial Check
                </button>
              </form>
            </section>

            {/* Adversarial Falsifier Ledger */}
            <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
              <h3 className="text-sm font-semibold text-slate-900">
                Recent Prospector-2100 Critic Verdicts
              </h3>
              <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                {snap.findings.slice(0, 6).map((f) => {
                  const verified = f.adversarialCritiqueVerdict === 'VERIFIED_CAUSAL';
                  return (
                    <div key={f.id} className="py-3 first:pt-0 last:pb-0 space-y-1">
                      <div className="flex items-center justify-between text-xs font-mono tabular-nums">
                        <span
                          className={`inline-flex items-center gap-1 font-medium ${
                            verified ? 'text-emerald-700' : 'text-amber-700'
                          }`}
                        >
                          {verified ? (
                            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                          )}
                          {verified ? 'Verified' : 'Quarantined'} · {f.causalConfidencePct}%
                        </span>
                        <span className="text-slate-500">
                          ${f.cycleCostUsd.toFixed(5)} · EVSI {f.evsiScore}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-900">{f.title}</div>
                      <div className="text-[11px] text-slate-500">{f.adversarialNotes}</div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
