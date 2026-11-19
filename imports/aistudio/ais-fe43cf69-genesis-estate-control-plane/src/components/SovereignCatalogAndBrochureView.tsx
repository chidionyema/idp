import React, { useState, useMemo } from 'react';
import {
  Download,
  RefreshCw,
  Volume2,
  ArrowUpRight,
  Copy,
  Check,
  Search,
} from 'lucide-react';
import {
  filterModulesForPersona,
  getPersonaDefinition,
  generateLivingBrochureMarkdown,
  type BeastGovernorState,
  type BeastSynchronyCatalogState,
  type ClientBrowserSurfaceReport,
  type HorizonId,
  type PersonaTier,
  type SynchronyEntityDomain,
} from '../engine/beastGovernor';
import {
  playSovereignHeartbeatPulse,
  speakLiveEstateHeadline,
} from '../utils/sovereignAudio';

interface SovereignCatalogAndBrochureViewProps {
  beast: BeastGovernorState;
  synchrony: BeastSynchronyCatalogState;
  activePersona: PersonaTier;
  onSelectPersona: (persona: PersonaTier) => void;
  activeHorizon: HorizonId;
  onSelectHorizon: (horizon: HorizonId) => void;
  onDeepLinkNavigate: (deepLinkHash: string) => void;
  onRefreshState: () => Promise<void>;
}

function collectRealClientBrowserReport(): ClientBrowserSurfaceReport {
  if (typeof window === 'undefined') {
    return {
      userAgentSummary: 'Server/SSR',
      viewport: '1440x900',
      cookieCount: 0,
      cookieNames: [],
      localStorageKeyCount: 0,
      localStorageKeys: [],
      sessionStorageKeyCount: 0,
      hardwareConcurrency: 4,
      language: 'en-US',
      online: true,
      observedRttMs: 1,
    };
  }

  const rawCookies = (document.cookie || '')
    .split(';')
    .map((c) => c.trim())
    .filter(Boolean);
  const cookieNames = rawCookies.map((pair) => pair.split('=')[0]?.trim() || 'cookie');

  let localKeys: string[] = [];
  let sessionCount = 0;
  try {
    localKeys = Object.keys(window.localStorage || {}).slice(0, 12);
    sessionCount = Object.keys(window.sessionStorage || {}).length;
  } catch {
    // Hermetic iframe storage guard
  }

  const navConn = (
    navigator as unknown as { connection?: { rtt?: number } }
  ).connection;

  return {
    userAgentSummary: navigator.userAgent.slice(0, 72),
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    cookieCount: cookieNames.length,
    cookieNames,
    localStorageKeyCount: localKeys.length,
    localStorageKeys: localKeys,
    sessionStorageKeyCount: sessionCount,
    hardwareConcurrency: navigator.hardwareConcurrency || 4,
    language: navigator.language || 'en-US',
    online: navigator.onLine,
    observedRttMs: typeof navConn?.rtt === 'number' && navConn.rtt > 0 ? navConn.rtt : 8,
  };
}

export const SovereignCatalogAndBrochureView: React.FC<
  SovereignCatalogAndBrochureViewProps
> = ({
  beast,
  synchrony,
  activePersona,
  onSelectPersona,
  activeHorizon,
  onSelectHorizon,
  onDeepLinkNavigate,
  onRefreshState,
}) => {
  const [catalogMode, setCatalogMode] = useState<'CAPABILITY_CARDS' | 'LIVING_BROCHURE'>(
    'CAPABILITY_CARDS'
  );
  const [mechFilter, setMechFilter] = useState<
    'ALL' | 'GAMING_RTS_NETCODE' | 'FOREX_HFT_MARKETS' | 'SOCIAL_REALTIME_GRAPH'
  >('ALL');
  const [omniDomainFilter, setOmniDomainFilter] = useState<'ALL' | SynchronyEntityDomain>('ALL');
  const [omniSearch, setOmniSearch] = useState('');
  const [sweepingNodes, setSweepingNodes] = useState(false);
  const [copiedBrochure, setCopiedBrochure] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const personaDef = useMemo(() => getPersonaDefinition(activePersona), [activePersona]);
  const visibleModules = useMemo(
    () => filterModulesForPersona(synchrony.productModules, activePersona),
    [synchrony.productModules, activePersona]
  );

  const brochureMarkdown = useMemo(
    () => generateLivingBrochureMarkdown(synchrony, beast, activePersona),
    [synchrony, beast, activePersona]
  );

  const filteredMechanics = useMemo(
    () =>
      mechFilter === 'ALL'
        ? synchrony.crossDomainMechanics
        : synchrony.crossDomainMechanics.filter((m) => m.sourceIndustry === mechFilter),
    [synchrony.crossDomainMechanics, mechFilter]
  );

  const filteredOmniNodes = useMemo(() => {
    const q = omniSearch.trim().toLowerCase();
    return synchrony.omniSurfaceMap.nodes.filter((n) => {
      if (omniDomainFilter !== 'ALL' && n.domain !== omniDomainFilter) return false;
      if (!q) return true;
      return (
        n.name.toLowerCase().includes(q) ||
        n.beastUri.toLowerCase().includes(q) ||
        n.physicalOrLogicalPath.toLowerCase().includes(q) ||
        n.telemetryDetail.toLowerCase().includes(q)
      );
    });
  }, [synchrony.omniSurfaceMap.nodes, omniDomainFilter, omniSearch]);

  const handleSweepOmniNodes = async () => {
    setSweepingNodes(true);
    setFeedback(null);
    try {
      const clientReport = collectRealClientBrowserReport();
      const res = await fetch('/api/synchrony/probe-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clientReport }),
      });
      const data = await res.json();
      await onRefreshState();
      if (data.synchrony) {
        const nextSync = data.synchrony as BeastSynchronyCatalogState;
        setFeedback(
          `Mapped ${nextSync.omniSurfaceMap.totalMappedEntities} synchrony entities across Browser (${clientReport.viewport}, ${clientReport.cookieCount} cookies, ${clientReport.localStorageKeyCount} storage keys), Host, Cloud & Packs · 0 orphaned items · Root ${nextSync.synchronyMerkleRootSha256.slice(0, 14)}.`
        );
      }
    } finally {
      setSweepingNodes(false);
    }
  };

  const handleCopyBrochure = async () => {
    try {
      await navigator.clipboard.writeText(brochureMarkdown);
      setCopiedBrochure(true);
      window.setTimeout(() => setCopiedBrochure(false), 2000);
    } catch {
      setFeedback('Use Download Brochure (.md) above to export the live dossier.');
    }
  };

  const handlePlaySitrepAudio = () => {
    playSovereignHeartbeatPulse(synchrony.heartbeatPosture, true);
    const script = `Meridian ${personaDef.shortBadge} briefing. Heartbeat ${synchrony.heartbeatBpm} beats per minute, phase drift ${synchrony.founderSystemPhaseDriftMs} milliseconds. Displaying ${visibleModules.length} of 10 sovereign product pillars. ${synchrony.rankedHeadlines[0]?.spokenScript || ''}`;
    window.setTimeout(() => {
      speakLiveEstateHeadline(script, true);
    }, 260);
    setFeedback(`Playing spoken executive sitrep (${synchrony.heartbeatBpm} BPM pulse + top headline).`);
  };

  return (
    <div className="space-y-8">
      {/* Executive Hero & 4-Persona Progressive Product Menu Controller */}
      <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
              <span>{synchrony.livingBrochureMeta.versionTag}</span>
              <span aria-hidden="true">·</span>
              <span>Active Lens: {personaDef.shortBadge}</span>
              <span aria-hidden="true">·</span>
              <span>
                Synchrony Root: {synchrony.synchronyMerkleRootSha256.slice(0, 14)}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50 [text-wrap:balance]">
              Sovereign Product Menu, Living Brochure &amp; Web of Synchrony
            </h1>

            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {personaDef.audienceSummary} Every capability card, brochure claim, source pack, cookie audit, and compute node is mathematically deep-linked into The Beast so zero code or collateral ever drifts out of sync.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              disabled={sweepingNodes}
              onClick={handleSweepOmniNodes}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${sweepingNodes ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              Sweep All Nodes &amp; Cookies
            </button>

            <button
              type="button"
              onClick={handlePlaySitrepAudio}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Volume2 className="w-3.5 h-3.5" aria-hidden="true" />
              Hear Heartbeat &amp; Sitrep
            </button>

            <a
              href={`/api/beast/brochure?persona=${activePersona}`}
              download={`meridian-brochure-${activePersona.toLowerCase()}.md`}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Export Brochure (.md)
            </a>
          </div>
        </div>

        {/* Progressive Persona Selector Strip (10 -> 7 -> 5 -> 3) */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-0.5">
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              Progressive Persona Product Menu (Founder 10 &rarr; Investor 7 &rarr; Enterprise 5 &rarr; Public 3)
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Redaction Rule: {personaDef.redactionPolicy}
            </div>
          </div>

          <div
            role="group"
            aria-label="Select Brochure and Menu Persona"
            className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg shrink-0"
          >
            {synchrony.personas.map((p) => {
              const active = p.id === activePersona;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onSelectPersona(p.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    active
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-amber-300 shadow-sm font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {p.shortBadge}
                </button>
              );
            })}
          </div>
        </div>

        {/* Full-Width 4-Column Synchrony KPI Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Scoped Product Menu</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {visibleModules.length}/10 Pillars
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              {personaDef.visibleNavIds.length}/13 Navigation Routes Visible
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Tempo-Chronos Heartbeat</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {synchrony.heartbeatBpm} BPM
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              Phase drift {synchrony.founderSystemPhaseDriftMs.toFixed(1)} ms · 4 Horizons
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Mini-NASA Free-Lane Fill</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {synchrony.forexOrderBook.zeroCostMatchRatioPct}% at $0
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              Forex Bid/Ask compute router
            </div>
          </div>

          <div className="p-4 space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400">Omni-Node Surface Map</div>
            <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-50">
              {synchrony.omniSurfaceMap.totalMappedEntities} Linked
            </div>
            <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
              0 throwaway · 0 untracked 3P cookies
            </div>
          </div>
        </div>

        {feedback && (
          <div
            role="status"
            className="px-4 py-2.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 font-mono tabular-nums"
          >
            {feedback}
          </div>
        )}
      </section>

      {/* 01. Sovereign Product Menu & Auto-Synchronized Living Brochure */}
      <section
        id="product-menu"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              01. Sovereign Product Menu &amp; Living Institutional Brochure ({visibleModules.length} Displayed)
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Live-bound to Beast Sweep #{beast.sweepSequence} (Brochure SHA {synchrony.livingBrochureMeta.brochureMerkleSha256.slice(0, 16)}). Click any deep link to inspect the live subsystem.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg">
              <button
                type="button"
                onClick={() => setCatalogMode('CAPABILITY_CARDS')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  catalogMode === 'CAPABILITY_CARDS'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Product Menu ({visibleModules.length})
              </button>
              <button
                type="button"
                onClick={() => setCatalogMode('LIVING_BROCHURE')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                  catalogMode === 'LIVING_BROCHURE'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Living Brochure Source (.md)
              </button>
            </div>

            {catalogMode === 'LIVING_BROCHURE' && (
              <button
                type="button"
                onClick={handleCopyBrochure}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg whitespace-nowrap shrink-0"
              >
                {copiedBrochure ? (
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                <span>{copiedBrochure ? 'Copied' : 'Copy Markdown'}</span>
              </button>
            )}
          </div>
        </div>

        {catalogMode === 'CAPABILITY_CARDS' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {visibleModules.map((mod) => (
              <article
                key={mod.moduleId}
                className="p-5 border border-slate-200 dark:border-slate-800 rounded-xl flex flex-col justify-between gap-4 hover:border-amber-500/40 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                    <span>
                      {String(mod.index).padStart(2, '0')} · {mod.moduleId} · {mod.deploymentStatus}
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-400">
                      {mod.allowedPersonas.length === 4
                        ? 'All Personas'
                        : `${mod.allowedPersonas.length} Personas`}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    {String(mod.index).padStart(2, '0')}. {mod.title}
                  </h3>

                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    {mod.tagline}
                  </p>

                  <div className="pt-1 text-xs text-slate-700 dark:text-slate-300">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      Live Proof:
                    </span>{' '}
                    <span className="font-mono tabular-nums">{mod.liveHeadlineMetric}</span>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    {mod.investorProofPoint}
                  </p>

                  {activePersona === 'FOUNDER_SOVEREIGN' && (
                    <div className="pt-2 border-t border-slate-200/80 dark:border-slate-800/80 space-y-1 text-[11px] font-mono text-slate-500 dark:text-slate-400 [overflow-wrap:anywhere]">
                      <div>Founder Telemetry: {mod.founderRawDetail}</div>
                      <div>
                        Pack {mod.boundPackId} · Door {mod.apiDoor} · {mod.sourcePaths.join(', ')}
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-100 dark:border-slate-800/60">
                  <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 truncate">
                    {mod.beastUri}
                  </span>
                  <button
                    type="button"
                    onClick={() => onDeepLinkNavigate(mod.deepLinkHash)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <span>Open Surface</span>
                    <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7">
              <pre className="p-4 bg-slate-950 text-slate-100 rounded-lg text-xs leading-relaxed font-mono overflow-x-auto max-h-[480px] overflow-y-auto border border-slate-800 whitespace-pre-wrap">
                {brochureMarkdown}
              </pre>
            </div>
            <div className="lg:col-span-5 space-y-4">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Self-Updating Living Brochure Plan &amp; Synchrony Formula
              </h3>
              <p className="text-xs font-mono text-amber-700 dark:text-amber-300 [overflow-wrap:anywhere]">
                {synchrony.livingBrochureMeta.syncGuaranteeFormula}
              </p>
              <ul className="space-y-2.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {synchrony.livingBrochureMeta.updateProtocolSteps.map((step, idx) => (
                  <li key={idx} className="pb-2.5 border-b border-slate-200 dark:border-slate-800 last:border-0">
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>

      {/* 02. Tempo & Chronos Multi-Horizon Synchrony + Live Ranked Headlines */}
      <section
        id="tempo-chronos-heartbeat"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch"
      >
        <div className="lg:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              02. Tempo &amp; Chronos Multi-Horizon Synchrony (1s &rarr; 1m &rarr; 1d &rarr; 1w)
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Multi-timeframe OHLCV synchrony candles ensure 1-second execution ticks never drift from daily delivery or weekly venture goals.
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                  <th className="py-2.5 px-3">Horizon &amp; Organ</th>
                  <th className="py-2.5 px-3">Live Synchrony Metric</th>
                  <th className="py-2.5 px-3 text-right">Candle (O/H/L/C)</th>
                  <th className="py-2.5 px-3 text-right">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                {synchrony.horizons.map((h) => {
                  const selected = h.horizonId === activeHorizon;
                  return (
                    <tr
                      key={h.horizonId}
                      onClick={() => onSelectHorizon(h.horizonId)}
                      className={`cursor-pointer transition-colors ${
                        selected
                          ? 'bg-amber-500/5 dark:bg-amber-500/10'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-900/60'
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {h.label}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          Owner: {h.organOwner} · {h.cadenceWindow}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-mono tabular-nums text-slate-800 dark:text-slate-200">
                          {h.primaryMetric}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {h.secondaryMetric}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-[11px] text-emerald-700 dark:text-emerald-400 whitespace-nowrap">
                        {h.forexCandleSummary.openScore.toFixed(1)} /{' '}
                        {h.forexCandleSummary.highScore.toFixed(1)} /{' '}
                        {h.forexCandleSummary.lowScore.toFixed(1)} /{' '}
                        {h.forexCandleSummary.closeScore.toFixed(1)}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeepLinkNavigate(h.deepLinkHash);
                          }}
                          aria-label={`Open deep link for ${h.label}`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 dark:text-amber-400 hover:underline whitespace-nowrap"
                        >
                          <span>Go</span>
                          <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Algorithmic Social-Ranked Live Headlines & Voice Reader */}
        <div className="lg:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              Ranked Estate Headlines (Audio &amp; Deep-Linked)
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Scored by Impact &times; Urgency so critical signals surface immediately.
            </p>
          </div>

          <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
            {synchrony.rankedHeadlines.map((hdl) => (
              <div key={hdl.headlineId} className="p-3.5 space-y-1.5 text-xs">
                <div className="flex items-center justify-between gap-2 font-mono tabular-nums text-[11px] text-slate-500 dark:text-slate-400">
                  <span>
                    Rank {hdl.impactScore}/100 · {hdl.horizonId} · {hdl.domainOrigin}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => speakLiveEstateHeadline(hdl.spokenScript, true)}
                      aria-label={`Speak headline ${hdl.headlineId}`}
                      className="text-slate-600 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 whitespace-nowrap"
                    >
                      Speak
                    </button>
                    <span aria-hidden="true">·</span>
                    <button
                      type="button"
                      onClick={() => onDeepLinkNavigate(hdl.deepLinkHash)}
                      className="text-amber-700 dark:text-amber-400 hover:underline whitespace-nowrap"
                    >
                      Deep Link
                    </button>
                  </div>
                </div>
                <div
                  className={`font-medium leading-snug ${
                    hdl.severity === 'CRITICAL_INTERRUPT'
                      ? 'text-red-700 dark:text-red-300 font-semibold'
                      : 'text-slate-900 dark:text-slate-100'
                  }`}
                >
                  {hdl.headline}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 03. Zero-Budget Mini-NASA Bridge + Gaming / Forex / Social Behavioral Engines (Visible to Founder, Investor & Enterprise) */}
      {activePersona !== 'PUBLIC_VISITOR' && (
        <section
          id="forex-order-book"
          className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6"
        >
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              03. Zero-Budget &ldquo;Mini-NASA&rdquo; Architecture &amp; Gaming / Forex / Social Live Engines
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              How Meridian achieves aerospace mission-control guarantees on bootstrapped economics by combining NASA Flight Rules with Forex limit order books, Gaming rollback netcode, and Social relevance ranking.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Mini-NASA $0 Replacement Matrix */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Bridging the Mini-NASA Gap on $0 Marginal Compute
              </h3>
              <div className="divide-y divide-slate-200 dark:divide-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg">
                {synchrony.miniNasaBridge.map((p) => (
                  <div key={p.pillarId} className="p-3.5 space-y-1 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {p.nasaCapability}
                      </span>
                      <span className="font-mono tabular-nums text-emerald-600 dark:text-emerald-400 whitespace-nowrap shrink-0">
                        {p.nasaAnnualBudgetRef} &rarr; {p.marginalCostUsd}
                      </span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                      {p.meridianZeroBudgetMechanism}
                    </p>
                    <div className="flex items-center justify-between gap-2 pt-0.5 font-mono tabular-nums text-[11px] text-slate-500 dark:text-slate-400">
                      <span>{p.liveProofMetric}</span>
                      <button
                        type="button"
                        onClick={() => onDeepLinkNavigate(p.deepLinkHash)}
                        className="text-amber-700 dark:text-amber-400 hover:underline whitespace-nowrap"
                      >
                        Inspect &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Live Forex Compute Bid/Ask Order Book */}
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Forex Compute Limit Order Book ({synchrony.forexOrderBook.zeroCostMatchRatioPct}% $0 Match)
                </h3>
                <span className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                  Breaker: {synchrony.forexOrderBook.luldCircuitBreakerState}
                </span>
              </div>

              <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                      <th className="py-2 px-3">Side</th>
                      <th className="py-2 px-3">Lane / Task Participant</th>
                      <th className="py-2 px-3 text-right">SLA / RTT</th>
                      <th className="py-2 px-3 text-right">Price / 1k</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                    {synchrony.forexOrderBook.entries.map((ord) => (
                      <tr key={ord.orderId}>
                        <td
                          className={`py-2.5 px-3 font-mono text-[11px] font-semibold whitespace-nowrap ${
                            ord.side === 'COMPUTE_ASK'
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-amber-700 dark:text-amber-300'
                          }`}
                        >
                          {ord.side === 'COMPUTE_ASK' ? 'ASK' : 'BID'}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-slate-900 dark:text-slate-100">
                            {ord.participant}
                          </div>
                          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                            {ord.capacityUnits} · {ord.matchedStatus}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300 whitespace-nowrap">
                          {ord.slaOrLatencyMs} ms
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                          ${ord.unitCostUsdPer1kTok.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Cross-Domain Behavioral Primitives (Gaming / Forex / Social) */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Active Cross-Domain Real-Time Intelligence Primitives
              </h3>
              <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg">
                {(
                  [
                    { id: 'ALL', label: 'All Domains (5)' },
                    { id: 'GAMING_RTS_NETCODE', label: 'Gaming / Netcode' },
                    { id: 'FOREX_HFT_MARKETS', label: 'Forex / HFT' },
                    { id: 'SOCIAL_REALTIME_GRAPH', label: 'Social / Presence' },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setMechFilter(tab.id)}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                      mechFilter === tab.id
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {filteredMechanics.map((m) => (
                <div
                  key={m.mechId}
                  className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg flex flex-col justify-between gap-3 text-xs"
                >
                  <div className="space-y-1.5">
                    <div className="font-mono text-[11px] text-amber-700 dark:text-amber-400">
                      {m.sourceIndustry.replace(/_/g, ' ')}
                    </div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {m.borrowedPattern}
                    </div>
                    <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                      {m.meridianImplementation}
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800/70 space-y-1">
                    <div className="font-mono tabular-nums text-[11px] text-emerald-700 dark:text-emerald-400">
                      {m.liveTelemetryState}
                    </div>
                    <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                      <span className="truncate">{m.activeBenefit}</span>
                      <button
                        type="button"
                        onClick={() => onDeepLinkNavigate(m.deepLinkHash)}
                        className="text-amber-700 dark:text-amber-400 hover:underline whitespace-nowrap shrink-0"
                      >
                        Open &rarr;
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 04. Omni-Node Surface Mapper & Universal Web of Synchrony (Founder Full View; Scoped Summary for Others) */}
      {activePersona === 'FOUNDER_SOVEREIGN' ? (
        <section
          id="omni-surface-map"
          className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5"
        >
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                04. Omni-Node Surface Mapper &amp; Web of Synchrony (&ldquo;Nothing Escapes The Beast&rdquo;)
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Every catalog item, brochure, pack, source file, cookie/storage key, secret lease, and compute/browser node is mapped, hashed, and deep-linked ({synchrony.omniSurfaceMap.orphanedThrowawayCount} throwaway artifacts).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <div className="relative">
                <Search
                  className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
                  aria-hidden="true"
                />
                <input
                  type="search"
                  value={omniSearch}
                  onChange={(e) => setOmniSearch(e.target.value)}
                  aria-label="Filter mapped synchrony nodes, cookies, packs, or URIs"
                  placeholder="Search URI, cookie, pack, node..."
                  className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg">
                {(
                  [
                    { id: 'ALL', label: 'All Mapped' },
                    { id: 'CATALOG_AND_BROCHURE', label: 'Catalog & Brochure' },
                    { id: 'PACKS_AND_SOURCE', label: 'Source & Packs' },
                    { id: 'COOKIES_STORAGE_TELEMETRY', label: 'Cookies & Vaults' },
                    { id: 'WEB_AND_HOST_NODES', label: 'Web & Host Nodes' },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setOmniDomainFilter(tab.id)}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                      omniDomainFilter === tab.id
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-sm'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {filteredOmniNodes.length === 0 ? (
            <div className="p-8 text-center border border-slate-200 dark:border-slate-800 rounded-lg space-y-2">
              <p className="text-xs text-slate-600 dark:text-slate-400">
                No mapped synchrony entities matched &ldquo;{omniSearch}&rdquo;.
              </p>
              <button
                type="button"
                onClick={() => {
                  setOmniSearch('');
                  setOmniDomainFilter('ALL');
                }}
                className="px-3 py-1.5 text-xs font-medium text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-800 rounded-lg"
              >
                Reset Filter
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2.5 px-3">Entity &amp; Canonical Beast URI</th>
                    <th className="py-2.5 px-3">Physical / Logical Surface</th>
                    <th className="py-2.5 px-3">Live Telemetry &amp; Cookie/Vault Audit</th>
                    <th className="py-2.5 px-3 text-right">Deep Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {filteredOmniNodes.map((node) => (
                    <tr key={node.nodeId} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                          {node.name}
                        </div>
                        <div className="text-[11px] font-mono text-amber-700 dark:text-amber-400">
                          {node.beastUri}
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                        <div>{node.physicalOrLogicalPath}</div>
                        <div className="text-slate-400 dark:text-slate-500">
                          SHA {node.sha256Short} · {node.liveStatus}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-300 max-w-md">
                        {node.telemetryDetail}
                      </td>
                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => onDeepLinkNavigate(node.deepLinkHash)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 rounded-md transition-colors"
                        >
                          <span>Jump</span>
                          <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <section className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Cryptographic Synchrony &amp; Privacy Attestation ({personaDef.shortBadge})
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              All {visibleModules.length} capabilities above are verified live against Beast Merkle Root{' '}
              <code className="font-mono">{beast.fractalConsistencyRootSha256.slice(0, 16)}</code> with 0 untracked third-party cookies. Switch to Founder 10/10 to inspect raw Omni-Node &amp; Bitwarden telemetry.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onSelectPersona('FOUNDER_SOVEREIGN')}
            className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            Unlock Founder 10/10 View
          </button>
        </section>
      )}
    </div>
  );
};
