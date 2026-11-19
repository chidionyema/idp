import { useEffect, useState } from 'react';
import { Download, GitBranch, Menu, Search, ShieldCheck, Zap } from 'lucide-react';
import { ApplianceSetupDrConsole } from './components/ApplianceSetupDrConsole';
import { AuraObsidianDeck } from './components/AuraObsidianDeck';
import { ChaosStressLab } from './components/ChaosStressLab';
import { CompetitorBenchmarks } from './components/CompetitorBenchmarks';
import { DagsterOrchestration } from './components/DagsterOrchestration';
import { EstateGrandUnion } from './components/EstateGrandUnion';
import { FalsifiersSuite } from './components/FalsifiersSuite';
import { FounderAutonomousReactivity } from './components/FounderAutonomousReactivity';
import { FounderRegoChronosPlane } from './components/FounderRegoChronosPlane';
import { GatewayOverview } from './components/GatewayOverview';
import { GenesisAcademy } from './components/GenesisAcademy';
import { GenesisSurvivalTtt } from './components/GenesisSurvivalTtt';
import { GlobalGetWorkModal } from './components/GlobalGetWorkModal';
import { HermesLivingTree } from './components/HermesLivingTree';
import { MeridianBattalion } from './components/MeridianBattalion';
import { MeridianInvestorPortal } from './components/MeridianInvestorPortal';
import { MeridianSymphony } from './components/MeridianSymphony';
import { ModelSupplyIntelligence } from './components/ModelSupplyIntelligence';
import { MumConciergeHub } from './components/MumConciergeHub';
import { MumchimpProspectorHub } from './components/MumchimpProspectorHub';
import { OttoNumenVipTelegram } from './components/OttoNumenVipTelegram';
import { PacketForensics } from './components/PacketForensics';
import { PhoenixRoundTablePanel } from './components/PhoenixRoundTablePanel';
import { SidebarNav } from './components/SidebarNav';
import { SovereignConciergePalette } from './components/SovereignConciergePalette';
import {
  isDeclaredGetWorkRoute,
  resolveDeclaredAppRoute,
} from './engine/crescendoThreeWayUnion';
import { VerificationSuiteReport } from './engine/types';
import {
  EstateGrandUnionSnapshot,
  GatewayStateSnapshot,
  GrandUnionApiResponse,
  NavTabId,
  ProductionGuaranteesReport,
} from './types/api';

const TAB_TITLES: Record<NavTabId, string> = {
  appliance_setup: 'Turnkey Appliance Setup & Zero-Device Phone Disaster Recovery',
  phoenix_round_table: 'Operation Phoenix · Daily Cold-Boot & Union Round Table',
  union: 'Estate Grand Union · Chronos, InterCloud & First-Use Audit',
  founder_reactivity: 'Real-Time Founder’s View · Autonomous Reactivity & Custody (#8184)',
  investor_meridian: 'Meridian Sovereign Systems · Company & Investor Data Room',
  founder_plane: 'Founder Control Plane · Chronos Harmonics & Rego Constitution',
  mum_concierge: 'Mum’s Sovereign Concierge · Auntie Ezinne (WhatsApp & EON-001)',
  mumchimp_research: 'Mumchimp Commercial Hub · Prospector-2100 Autonomous Research',
  academy: 'Genesis Academy · Novice to Founder Live Simulations',
  telegram_vip: 'VIP CEO Telegram · Hermes · OTTO_NUMEN Concierge',
  hermes: 'Hermes · The Living Tree',
  symphony: 'Meridian Symphony · Estate Constellation',
  genesis_ttt: 'Genesis Survival & TTT · I-8088 + GEN-TTT-001',
  aura: 'AURA-2100 Obsidian Glass · Binary Manifold',
  overview: 'Gateway Overview',
  packets: 'Packet Forensics & Token Savings',
  meridian: 'Meridian Battalion Metering',
  supply: 'Model Supply & Legion',
  dagster: 'Dagster Orchestration',
  competitors: 'Competitor Benchmarks',
  falsifiers: 'Falsifiers & Integration Tests',
  chaos: 'Chaos & Stress Lab',
};

function resolveInitialTab(): NavTabId {
  if (typeof window !== 'undefined') {
    return resolveDeclaredAppRoute(window.location.pathname, window.location.search);
  }
  return 'union';
}

function resolveInitialGetWorkOpen(): boolean {
  if (typeof window !== 'undefined') {
    return isDeclaredGetWorkRoute(window.location.pathname, window.location.search);
  }
  return false;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTabId>(resolveInitialTab);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [conciergeOpen, setConciergeOpen] = useState(false);
  const [getWorkOpen, setGetWorkOpen] = useState<boolean>(resolveInitialGetWorkOpen);
  const [autoStartGitHubDevice, setAutoStartGitHubDevice] = useState(false);
  const [handoffTriggerSeq, setHandoffTriggerSeq] = useState(0);
  const [state, setState] = useState<GatewayStateSnapshot | null>(null);
  const [unionSnapshot, setUnionSnapshot] = useState<EstateGrandUnionSnapshot | null>(null);
  const [guarantees, setGuarantees] = useState<ProductionGuaranteesReport | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifyingAll, setVerifyingAll] = useState(false);
  const [verificationReport, setVerificationReport] = useState<VerificationSuiteReport | null>(
    null
  );

  async function loadInitialUnionAndState() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/union');
      if (!res.ok) {
        throw new Error(`Control plane returned HTTP ${res.status}`);
      }
      const data = (await res.json()) as GrandUnionApiResponse;
      setUnionSnapshot(data.union);
      setState(data.state);
      if (data.guarantees) {
        setGuarantees(data.guarantees);
      } else {
        void fetch('/api/union/guarantees')
          .then((r) => (r.ok ? r.json() : null))
          .then((g: ProductionGuaranteesReport | null) => {
            if (g) setGuarantees(g);
          })
          .catch(() => {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load router control plane');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInitialUnionAndState();

    // Server-authoritative SSE stream (/api/union/stream) — zero client polling (I-8090)
    const source = new EventSource('/api/union/stream');
    source.onopen = () => {
      setSseConnected(true);
    };
    source.addEventListener('union_snapshot', (evt) => {
      try {
        const parsed = JSON.parse((evt as MessageEvent).data) as {
          union: EstateGrandUnionSnapshot;
          state: GatewayStateSnapshot;
        };
        setUnionSnapshot(parsed.union);
        setState(parsed.state);
        setSseConnected(true);
        setLoading(false);
      } catch {
        // Ignore malformed frame cleanly
      }
    });
    source.onerror = () => {
      setSseConnected(false);
    };

    const onKeyDown = (evt: KeyboardEvent) => {
      if ((evt.metaKey || evt.ctrlKey) && evt.key.toLowerCase() === 'k') {
        evt.preventDefault();
        setConciergeOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', onKeyDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      source.close();
    };
  }, []);

  async function handleTopBarVerify() {
    setVerifyingAll(true);
    try {
      const res = await fetch('/api/tests/run', { method: 'POST' });
      if (res.ok) {
        const report = (await res.json()) as VerificationSuiteReport;
        setVerificationReport(report);
        setActiveTab('falsifiers');
      }
    } finally {
      setVerifyingAll(false);
    }
  }

  async function handleQuickPulseBeat() {
    const res = await fetch('/api/union/beat', { method: 'POST' });
    if (res.ok) {
      const data = (await res.json()) as {
        union: EstateGrandUnionSnapshot;
        state: GatewayStateSnapshot;
      };
      setUnionSnapshot(data.union);
      setState(data.state);
    }
  }

  function handleUnionUpdated(nextUnion: EstateGrandUnionSnapshot, nextState?: GatewayStateSnapshot) {
    setUnionSnapshot(nextUnion);
    if (nextState) {
      setState(nextState);
    }
  }

  const openCircuitCount =
    state?.lanes.filter((l) => l.circuitState !== 'CLOSED').length ?? 0;

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900">
      <SidebarNav
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        vaultHydrated={state?.vaultHydrated ?? true}
        openCircuitCount={openCircuitCount}
        onOpenConcierge={() => setConciergeOpen(true)}
      />

      <SovereignConciergePalette
        open={conciergeOpen}
        onClose={() => setConciergeOpen(false)}
        onSelectTab={setActiveTab}
        onRunVerificationSuite={() => void handleTopBarVerify()}
        onPulseBeat={() => void handleQuickPulseBeat()}
      />

      <GlobalGetWorkModal
        open={getWorkOpen}
        autoStartGitHubDevice={autoStartGitHubDevice}
        onClearAutoStart={() => setAutoStartGitHubDevice(false)}
        onClose={() => {
          setGetWorkOpen(false);
          setAutoStartGitHubDevice(false);
        }}
        onOpenFullHandoffTab={() => {
          setActiveTab('founder_reactivity');
          setHandoffTriggerSeq((n) => n + 1);
        }}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top Bar Contract: Breadcrumb on left, Push to GitHub / Get Work + Verify actions on right */}
        <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-4 sm:px-6 py-3.5 flex items-center justify-between gap-3 sm:gap-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              className="lg:hidden rounded-md p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900 shrink-0"
            >
              <Menu className="h-5 w-5" />
            </button>
            <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm min-w-0">
              <span className="hidden sm:inline font-semibold text-slate-900 whitespace-nowrap shrink-0">
                Meridian · Genesis
              </span>
              <span aria-hidden="true" className="hidden sm:inline text-slate-400">
                /
              </span>
              <h1 className="font-semibold sm:font-medium text-slate-900 sm:text-slate-600 truncate">
                {TAB_TITLES[activeTab]}
              </h1>
            </nav>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => {
                setAutoStartGitHubDevice(false);
                setGetWorkOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 sm:px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
            >
              <GitBranch className="h-3.5 w-3.5 text-emerald-300" aria-hidden="true" />
              <span>Push to GitHub · Get Work</span>
            </button>

            <button
              type="button"
              disabled={verifyingAll}
              onClick={handleTopBarVerify}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 sm:px-3.5 py-2 text-xs font-medium text-slate-800 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
              <span className="sm:hidden">{verifyingAll ? 'Verifying...' : 'Verify'}</span>
              <span className="hidden sm:inline">
                {verifyingAll ? 'Verifying...' : 'Run Verification Suite'}
              </span>
            </button>
          </div>
        </header>

        <main className="flex-1 min-w-0 p-4 sm:p-6 max-w-[1280px] w-full mx-auto space-y-6">
          {/* Direct Zero-Block 3-Day GitHub Sync & Terminal Capsule Action Bar */}
          <section
            aria-label="Direct 3-Day GitHub Sync"
            className="bg-white border border-slate-200 rounded-lg px-4 py-3.5 flex flex-wrap items-center justify-between gap-3"
          >
            <div className="min-w-0 space-y-0.5">
              <p className="text-sm font-semibold text-slate-900">
                Complete 3-Day Sync (15–17 Nov) · Direct Server-to-GitHub Push & Sandbox-Proof Capsule
              </p>
              <p className="text-xs text-slate-600 font-mono tabular-nums">
                18/18 workstreams sealed · chidionyema/gemini-sync &amp; argon-sync · #7760 ref
                aistudio/meridian-hermes-carbon-20261117
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => {
                  setAutoStartGitHubDevice(true);
                  setGetWorkOpen(true);
                }}
                className="inline-flex items-center gap-1.5 rounded-md bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-800 transition-colors whitespace-nowrap shrink-0"
              >
                <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Push All 3 Days Directly to GitHub (1-Click Device Code)</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setAutoStartGitHubDevice(false);
                  setGetWorkOpen(true);
                }}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
              >
                <Download className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
                <span>1-Command Capsule &amp; Downloads</span>
              </button>
            </div>
          </section>
          {/* Global Non-Sticky UHNW Concierge, Chronos & Tempo Nerve Strip */}
          {!loading && !error && unionSnapshot && (
            <div className="bg-white border border-slate-200 rounded-lg px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2 text-slate-600 font-mono tabular-nums">
                <span className="font-semibold text-slate-900">
                  Chronos Beat #{unionSnapshot.chronos.beatNumber}
                </span>
                <span aria-hidden="true">·</span>
                <span>WAL {unionSnapshot.battalionRollup.walReceipts.toLocaleString()}</span>
                <span aria-hidden="true">·</span>
                <span>
                  InterCloud {unionSnapshot.interCloudSummary.onlineLanes}/
                  {unionSnapshot.interCloudSummary.totalLanes} Pools
                </span>
                <span aria-hidden="true">·</span>
                <span>
                  13-Pin Audit {unionSnapshot.firstUseAudit.adversarialTestsPassed}/
                  {unionSnapshot.firstUseAudit.adversarialTestsTotal} (Live Effect:{' '}
                  {unionSnapshot.firstUseAudit.liveCeremonyEffect})
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-3 min-w-0 max-w-full">
                <button
                  type="button"
                  onClick={() => setConciergeOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-900 hover:bg-slate-100 whitespace-nowrap"
                >
                  <Search className="h-3 w-3 text-slate-500" aria-hidden="true" />
                  OTTO Concierge (⌘K)
                </button>
                <button
                  type="button"
                  onClick={handleQuickPulseBeat}
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-900 whitespace-nowrap"
                >
                  <Zap className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
                  Pulse Beat
                </button>
                {activeTab !== 'appliance_setup' && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('appliance_setup')}
                    className="text-xs font-semibold text-emerald-800 hover:text-emerald-950 whitespace-nowrap"
                  >
                    Turnkey Setup & Phone DR
                  </button>
                )}
                {activeTab !== 'phoenix_round_table' && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('phoenix_round_table')}
                    className="text-xs font-semibold text-slate-900 hover:text-slate-700 whitespace-nowrap"
                  >
                    Phoenix Round Table
                  </button>
                )}
                {activeTab !== 'founder_reactivity' && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('founder_reactivity')}
                    className="text-xs font-semibold text-cyan-800 hover:text-cyan-950 whitespace-nowrap"
                  >
                    Real-Time Founder View
                  </button>
                )}
                {activeTab !== 'investor_meridian' && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('investor_meridian')}
                    className="text-xs font-medium text-blue-700 hover:text-blue-900 whitespace-nowrap"
                  >
                    Investor Room
                  </button>
                )}
              </div>
            </div>
          )}

          {loading && (
            <div className="space-y-6" aria-busy="true" aria-label="Loading control plane">
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="h-24 bg-white border border-slate-200 rounded-lg animate-pulse"
                  />
                ))}
              </div>
              <div className="h-64 bg-white border border-slate-200 rounded-lg animate-pulse" />
            </div>
          )}

          {!loading && error && (
            <div className="bg-white border border-red-200 rounded-lg p-6">
              <h2 className="text-base font-semibold text-red-800">
                Unable to reach router control plane
              </h2>
              <p className="mt-1 text-sm text-slate-600">{error}</p>
              <button
                type="button"
                onClick={loadInitialUnionAndState}
                className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800"
              >
                Retry Connection
              </button>
            </div>
          )}

          {!loading && !error && state && (
            <>
              {activeTab === 'appliance_setup' && <ApplianceSetupDrConsole />}
              {activeTab === 'phoenix_round_table' && <PhoenixRoundTablePanel />}
              {activeTab === 'union' && unionSnapshot && (
                <EstateGrandUnion
                  union={unionSnapshot}
                  guarantees={guarantees}
                  sseConnected={sseConnected}
                  onUnionUpdated={handleUnionUpdated}
                  onNavigateTab={setActiveTab}
                />
              )}
              {activeTab === 'founder_reactivity' && (
                <FounderAutonomousReactivity handoffTriggerSeq={handoffTriggerSeq} />
              )}
              {activeTab === 'investor_meridian' && (
                <MeridianInvestorPortal onNavigateTab={setActiveTab} />
              )}
              {activeTab === 'founder_plane' && <FounderRegoChronosPlane />}
              {activeTab === 'mum_concierge' && <MumConciergeHub />}
              {activeTab === 'mumchimp_research' && <MumchimpProspectorHub />}
              {activeTab === 'academy' && (
                <GenesisAcademy onNavigateTab={setActiveTab} />
              )}
              {activeTab === 'telegram_vip' && <OttoNumenVipTelegram />}
              {activeTab === 'hermes' && <HermesLivingTree />}
              {activeTab === 'symphony' && (
                <MeridianSymphony onStateChange={setState} />
              )}
              {activeTab === 'genesis_ttt' && <GenesisSurvivalTtt />}
              {activeTab === 'aura' && <AuraObsidianDeck />}
              {activeTab === 'overview' && (
                <GatewayOverview state={state} onStateChange={setState} />
              )}
              {activeTab === 'packets' && (
                <PacketForensics onStateChange={setState} />
              )}
              {activeTab === 'meridian' && <MeridianBattalion />}
              {activeTab === 'supply' && <ModelSupplyIntelligence />}
              {activeTab === 'dagster' && (
                <DagsterOrchestration state={state} onStateChange={setState} />
              )}
              {activeTab === 'competitors' && <CompetitorBenchmarks />}
              {activeTab === 'falsifiers' && (
                <FalsifiersSuite
                  externalReport={verificationReport}
                  onReportUpdated={setVerificationReport}
                />
              )}
              {activeTab === 'chaos' && <ChaosStressLab />}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
