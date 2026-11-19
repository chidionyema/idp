import React, { useEffect, useState, useCallback } from 'react';
import {
  Film,
  Orbit,
  Activity,
  Eye,
  Cpu,
  GitMerge,
  Workflow,
  CalendarClock,
  Mic,
  Sun,
  Moon,
  Menu,
  X,
  Dna,
  Network,
  Layers,
  ShieldCheck,
  BookOpen,
  Scale,
  GraduationCap,
} from 'lucide-react';
import type { EstateStateSnapshot, LegionExecutionRun } from './types/estate';
import type { ClaimGateAuditResult, FormationId } from './engine/estateRules';
import type { OptimusAdmissionInput, OptimusAdmissionResult } from './engine/optimusAndReactor';
import {
  getPersonaDefinition,
  type BeastGovernorState,
  type BeastSynchronyCatalogState,
  type SovereignStandardsGovernanceState,
  type GenesisAcademyState,
  type HorizonId,
  type PersonaTier,
} from './engine/beastGovernor';
import { BeastConvergenceView } from './components/BeastConvergenceView';
import { GenesisAcademyView } from './components/GenesisAcademyView';
import { SovereignStandardsMemoryBddView } from './components/SovereignStandardsMemoryBddView';
import { SovereignCatalogAndBrochureView } from './components/SovereignCatalogAndBrochureView';
import { TempoChronosHeartbeatBar } from './components/TempoChronosHeartbeatBar';
import { AllSurfaceIncidentBanner } from './components/AllSurfaceIncidentBanner';
import { OmegaUniversalCoreView } from './components/OmegaUniversalCoreView';
import { RegisterProjectorView } from './components/RegisterProjectorView';
import { IoWorkGraphAndIdentityView } from './components/IoWorkGraphAndIdentityView';
import { SwarmSynapseView } from './components/SwarmSynapseView';
import { SpatialReactor2100 } from './components/SpatialReactor2100';
import { OptimusAndBrainView } from './components/OptimusAndBrainView';
import { FleetOverviewView } from './components/FleetOverviewView';
import { LegionWorkforceView } from './components/LegionWorkforceView';
import { FlowAndBridgeView } from './components/FlowAndBridgeView';
import { GreenlaneTriageView } from './components/GreenlaneTriageView';
import { ChronosVenturesView } from './components/ChronosVenturesView';
import { VoiceCommandDrawer, type VoiceStageActionPayload } from './components/VoiceCommandDrawer';
import type { ArgonSyncActionResult } from './components/ArgonSyncPanel';
import { playExecutiveSpeech, stopAllSovereignSpeech } from './utils/sovereignAudio';

export type NavTab =
  | 'beast'
  | 'academy'
  | 'standards'
  | 'catalog'
  | 'omega'
  | 'io'
  | 'projector'
  | 'synapse'
  | 'reactor'
  | 'optimus'
  | 'fleet'
  | 'legion'
  | 'flow'
  | 'greenlane'
  | 'chronos';

const NAV_ITEMS: Array<{
  id: NavTab;
  label: string;
  shortLabel: string;
  inHeader: boolean;
  icon: React.FC<{ className?: string }>;
}> = [
  { id: 'beast', label: 'The Beast · Continuous Proof', shortLabel: 'The Beast', inHeader: true, icon: ShieldCheck },
  { id: 'academy', label: 'Genesis Asymmetric Academy', shortLabel: 'Academy', inHeader: true, icon: GraduationCap },
  { id: 'standards', label: 'Standards, Memory & BDD', shortLabel: 'Standards & BDD', inHeader: true, icon: Scale },
  { id: 'catalog', label: 'Product Menu & Living Brochure', shortLabel: 'Catalog & Sync', inHeader: true, icon: BookOpen },
  { id: 'omega', label: 'Omega Universal Core', shortLabel: 'Omega Core', inHeader: true, icon: Layers },
  { id: 'io', label: 'IO Engine & Work Graph', shortLabel: 'IO & Graph', inHeader: false, icon: Network },
  { id: 'projector', label: 'Face & Fleet Projector', shortLabel: 'Projector', inHeader: false, icon: Film },
  { id: 'reactor', label: 'Reactor 2100 (3D Field)', shortLabel: 'Reactor', inHeader: false, icon: Orbit },
  { id: 'synapse', label: 'Swarm Synapse (v0.7-RT)', shortLabel: 'Synapse', inHeader: false, icon: Dna },
  { id: 'optimus', label: 'Project Optimus & Brain', shortLabel: 'Optimus', inHeader: false, icon: Activity },
  { id: 'fleet', label: 'All-Seeing Eye (/fleet)', shortLabel: 'Fleet', inHeader: false, icon: Eye },
  { id: 'legion', label: 'Legion Workforce (8)', shortLabel: 'Legion', inHeader: false, icon: Cpu },
  { id: 'greenlane', label: 'Greenlane & Claim-Gate', shortLabel: 'Greenlane', inHeader: false, icon: GitMerge },
  { id: 'flow', label: 'FLOW & Argon Sync', shortLabel: 'Argon / FLOW', inHeader: false, icon: Workflow },
  { id: 'chronos', label: 'Chronos & Ventures', shortLabel: 'Chronos', inHeader: false, icon: CalendarClock },
];

const VALID_TABS = new Set<NavTab>([
  'beast',
  'academy',
  'standards',
  'catalog',
  'omega',
  'io',
  'projector',
  'synapse',
  'reactor',
  'optimus',
  'fleet',
  'legion',
  'flow',
  'greenlane',
  'chronos',
]);

const VALID_PERSONAS = new Set<PersonaTier>([
  'FOUNDER_SOVEREIGN',
  'INSTITUTIONAL_INVESTOR',
  'ENTERPRISE_OPERATOR',
  'PUBLIC_VISITOR',
]);

const VALID_HORIZONS = new Set<HorizonId>([
  '1S_TEMPO',
  '1M_PULSE',
  '1D_TACTICAL',
  '1W_CHRONOS',
]);

function parseHashDeepLink(hashInput?: string): {
  tab: NavTab;
  persona?: PersonaTier;
  horizon?: HorizonId;
  section?: string;
} {
  const rawHash =
    hashInput !== undefined
      ? hashInput
      : typeof window !== 'undefined'
      ? window.location.hash
      : '#beast';
  const cleaned = rawHash.replace(/^#\/?/, '').trim();
  const [tabPart, queryPart] = cleaned.split('?');
  const tabCandidate = (tabPart || '').trim().toLowerCase() as NavTab;
  const tab: NavTab = VALID_TABS.has(tabCandidate) ? tabCandidate : 'beast';

  let persona: PersonaTier | undefined;
  let horizon: HorizonId | undefined;
  let section: string | undefined;

  if (queryPart) {
    const params = new URLSearchParams(queryPart);
    const p = params.get('persona') as PersonaTier | null;
    if (p && VALID_PERSONAS.has(p)) persona = p;
    const h = params.get('horizon') as HorizonId | null;
    if (h && VALID_HORIZONS.has(h)) horizon = h;
    const s = params.get('section');
    if (s) section = s;
  }

  return { tab, persona, horizon, section };
}

export default function App() {
  const initialDeepLink = parseHashDeepLink();
  const [activeTab, setActiveTabState] = useState<NavTab>(initialDeepLink.tab);
  const [activePersona, setActivePersona] = useState<PersonaTier>(
    initialDeepLink.persona ?? 'FOUNDER_SOVEREIGN'
  );
  const [activeHorizon, setActiveHorizon] = useState<HorizonId>(
    initialDeepLink.horizon ?? '1S_TEMPO'
  );
  const [heartbeatAudioEnabled, setHeartbeatAudioEnabled] = useState<boolean>(false);
  const [snapshot, setSnapshot] = useState<EstateStateSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isReprobing, setIsReprobing] = useState(false);

  // Default to Genesis 2100 Nocturnal Sovereign workspace (#050811)
  const [isDark, setIsDark] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);

  const [prefilledMission, setPrefilledMission] = useState<{
    instructionId?: string;
    title?: string;
    objective: string;
    repo: string;
  } | null>(null);

  const [isPlayingBriefing, setIsPlayingBriefing] = useState(false);
  const [briefingScript, setBriefingScript] = useState<string | null>(null);
  const [briefingAudioMode, setBriefingAudioMode] = useState<string | null>(null);

  const setActiveTab = useCallback((next: NavTab) => {
    setActiveTabState(next);
    setVoiceModalOpen(false);
    if (typeof window !== 'undefined') {
      const nextHash = `#${next}`;
      if (window.location.hash !== nextHash) {
        window.history.replaceState(null, '', nextHash);
      }
    }
  }, []);

  const handleDeepLinkNavigate = useCallback((deepLinkHash: string) => {
    const parsed = parseHashDeepLink(deepLinkHash);
    setActiveTabState(parsed.tab);
    if (parsed.persona) setActivePersona(parsed.persona);
    if (parsed.horizon) setActiveHorizon(parsed.horizon);
    setVoiceModalOpen(false);
    if (typeof window !== 'undefined') {
      const normalized = deepLinkHash.startsWith('#') ? deepLinkHash : `#${deepLinkHash}`;
      if (window.location.hash !== normalized) {
        window.history.replaceState(null, '', normalized);
      }
      if (parsed.section) {
        window.setTimeout(() => {
          const el = document.getElementById(parsed.section!);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 60);
      }
    }
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const parsed = parseHashDeepLink();
      setActiveTabState(parsed.tab);
      if (parsed.persona) setActivePersona(parsed.persona);
      if (parsed.horizon) setActiveHorizon(parsed.horizon);
      setVoiceModalOpen(false);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDark]);

  const fetchEstateState = useCallback(async () => {
    setLoadError(null);
    try {
      const res = await fetch('/api/estate/state');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as EstateStateSnapshot;
      setSnapshot(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unable to load Estate state');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEstateState();
  }, [fetchEstateState]);

  // Global All-Surface SSE subscription so any millisecond incident or synchrony tick updates every view immediately
  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    const onBeastPulse = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as {
          beastGovernor?: BeastGovernorState;
          beastSynchrony?: BeastSynchronyCatalogState;
          sovereignStandards?: SovereignStandardsGovernanceState;
          genesisAcademy?: GenesisAcademyState;
        };
        if (
          parsed.beastGovernor ||
          parsed.beastSynchrony ||
          parsed.sovereignStandards ||
          parsed.genesisAcademy
        ) {
          setSnapshot((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              beastGovernor: parsed.beastGovernor ?? prev.beastGovernor,
              beastSynchrony: parsed.beastSynchrony ?? prev.beastSynchrony,
              sovereignStandards: parsed.sovereignStandards ?? prev.sovereignStandards,
              genesisAcademy: parsed.genesisAcademy ?? prev.genesisAcademy,
            };
          });
        }
      } catch {
        // Ignore malformed SSE frame
      }
    };
    es.addEventListener('beast-pulse', onBeastPulse);
    es.addEventListener('synchrony-pulse', onBeastPulse);
    es.addEventListener('standards-pulse', onBeastPulse);
    es.addEventListener('academy-pulse', onBeastPulse);
    return () => {
      es.removeEventListener('beast-pulse', onBeastPulse);
      es.removeEventListener('synchrony-pulse', onBeastPulse);
      es.removeEventListener('standards-pulse', onBeastPulse);
      es.removeEventListener('academy-pulse', onBeastPulse);
      es.close();
    };
  }, []);

  const handleResolveGlobalIncident = useCallback(
    async (mode: 'AUTO_COORDINATE_FIX' | 'LOOSEN_DIAL_OVERRIDE') => {
      const res = await fetch('/api/beast/resolve-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.beastGovernor) {
        setSnapshot((prev) =>
          prev ? { ...prev, beastGovernor: data.beastGovernor as BeastGovernorState } : prev
        );
      } else {
        await fetchEstateState();
      }
    },
    [fetchEstateState]
  );

  const handleReprobe = async () => {
    setIsReprobing(true);
    try {
      const res = await fetch('/api/estate/reprobe', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as EstateStateSnapshot;
        setSnapshot(data);
      }
    } finally {
      setIsReprobing(false);
    }
  };

  const handleExecuteFormation = async (payload: {
    formationId: FormationId;
    repo: string;
    instructionId?: string;
    title?: string;
    objective: string;
    helmShots: number;
  }): Promise<LegionExecutionRun | null> => {
    const res = await fetch('/api/legion/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Cloud formation execution failed');
    }
    await fetchEstateState();
    return data.execution as LegionExecutionRun;
  };

  const handleIngestOptimus = async (targetSurface?: string) => {
    const res = await fetch('/api/brain/optimus/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targetSurface }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || 'Optimus signed ingestion failed');
    }
    await fetchEstateState();
  };

  const handleEvaluateOptimusAdmission = async (
    input: OptimusAdmissionInput
  ): Promise<OptimusAdmissionResult> => {
    const res = await fetch('/api/brain/optimus/admission', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    const data = await res.json();
    await fetchEstateState();
    return (data.verdict ?? data.admission) as OptimusAdmissionResult;
  };

  const handleRunWatchdog = async (simulateStallInstructionId?: string) => {
    const res = await fetch('/api/flow/watchdog', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulateStallInstructionId }),
    });
    const data = await res.json();
    await fetchEstateState();
    return { recoveredIds: (data.recoveredIds as string[]) || [] };
  };

  const handleDispatchInbound = async (payload: Record<string, unknown>) => {
    const res = await fetch('/api/inbound/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    await fetchEstateState();
    if (!res.ok) {
      return {
        ok: false,
        message: `[${data.errorCode || 'REJECTED'}] ${data.reason || 'Dispatch blocked by Inbound Firewall'}`,
      };
    }
    return {
      ok: true,
      message: `${data.validation?.status}: ${data.validation?.authorityNote} (Branch: ${data.validation?.laneBranch})`,
    };
  };

  const handleEvaluateGuard = async (input: Record<string, unknown>): Promise<ClaimGateAuditResult> => {
    const res = await fetch('/api/guard/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    const data = await res.json();
    await fetchEstateState();
    return data.result as ClaimGateAuditResult;
  };

  const handleSyncArgon = useCallback(
    async (branch = 'lane/aistudio-genesis-2100-sync'): Promise<ArgonSyncActionResult> => {
      const res = await fetch('/api/argon/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: 'chidionyema/argon', branch }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.snapshot) {
        setSnapshot(data.snapshot as EstateStateSnapshot);
      } else {
        await fetchEstateState();
      }
      if (!res.ok || !data.ok) {
        return {
          ok: false,
          errorCode: data.errorCode,
          reason: data.reason,
          message: `[${data.errorCode || 'SYNC_REFUSED'}] ${data.reason || data.error || 'Argon sync refused by Greenlane guard.'}`,
        };
      }
      if (data.syncedRemote && data.receipt) {
        return {
          ok: true,
          syncedRemote: true,
          authority: 'E1',
          commitSha: data.receipt.commitSha,
          pullRequestUrl: data.receipt.pullRequestUrl,
          message: `VERIFIED E1 PUSH: Commit ${String(data.receipt.commitSha).slice(0, 12)} synced to chidionyema/argon@${data.receipt.branch}${data.receipt.pullRequestNumber ? ` · PR #${data.receipt.pullRequestNumber}` : ''}.`,
        };
      }
      const merkleShort = String(data.argonSync?.manifest?.merkleRootSha256 || '').slice(0, 12);
      const fileCount = data.argonSync?.manifest?.fileCount ?? 0;
      return {
        ok: true,
        syncedRemote: false,
        authority: 'U',
        message: `STAGED FOR ARGON (${fileCount} SHA-256 verified files · Merkle ${merkleShort}): .ops/register.jsonl & .genesis/outbox/argon-sync-bundle-20261111.json updated. Remote push held at Authority U until GitHub OAuth / GITHUB_TOKEN is attached, or run Greenlane Apply (.sh).`,
      };
    },
    [fetchEstateState]
  );

  const handleSelectMissionForLegion = (
    instructionId: string,
    title: string,
    objective: string,
    repo: string
  ) => {
    setPrefilledMission({ instructionId, title, objective, repo });
    setActiveTab('legion');
  };

  const handleStopBriefing = useCallback(() => {
    stopAllSovereignSpeech();
    setIsPlayingBriefing(false);
  }, []);

  const handlePlayBriefing = async () => {
    setIsPlayingBriefing(true);
    try {
      const res = await fetch('/api/voice/briefing', { method: 'POST' });
      const data = await res.json();
      if (data.script) {
        setBriefingScript(data.script);
      }
      const handle = await playExecutiveSpeech(
        data.script || 'Genesis Estate operational sitrep ready.',
        data.wavBase64,
        () => {
          setIsPlayingBriefing(false);
        }
      );
      setBriefingAudioMode(handle.mode);
      if (handle.mode === 'TRANSCRIPT_ONLY') {
        setIsPlayingBriefing(false);
      }
    } catch {
      setIsPlayingBriefing(false);
    }
  };

  const handleExecuteVoiceAction = async (payload: VoiceStageActionPayload): Promise<string> => {
    if (payload.actionKind === 'INGEST_OPTIMUS') {
      await handleIngestOptimus('voice-stage:optimus-probe');
      return 'Signed HMAC Optimus observation ingested & broadcast over SSE.';
    }
    if (payload.actionKind === 'SWEEP_WATCHDOG') {
      const out = await handleRunWatchdog();
      return out.recoveredIds.length > 0
        ? `FLOW 600s Watchdog fenced & recovered: ${out.recoveredIds.join(', ')}`
        : 'FLOW 600s Watchdog sweep complete — all worker heartbeats < 600s.';
    }
    if (payload.actionKind === 'REPROBE_ESTATE') {
      await handleReprobe();
      return 'Live GitHub E1 commits and production edge surfaces re-probed.';
    }
    if (payload.actionKind === 'PLAY_BRIEFING') {
      await handlePlayBriefing();
      return 'Synthesizing & playing Captain audio sitrep.';
    }
    if (payload.actionKind === 'SYNC_ARGON') {
      const syncOut = await handleSyncArgon();
      setActiveTab('flow');
      return syncOut.message;
    }
    if (payload.actionKind === 'NAVIGATE_TAB' && payload.targetTab) {
      setActiveTab(payload.targetTab);
      return `Navigated to ${payload.targetTab.toUpperCase()}.`;
    }
    if (payload.actionKind === 'TRIGGER_BLAST') {
      setActiveTab('reactor');
      return `Switched to Reactor 2100 targeting ${payload.targetNodeId}.`;
    }
    const formation = payload.formation ?? 'centurion';
    const repo = payload.repo ?? 'chidionyema/idp';
    const generatedId = `INS-V${Math.floor(1000 + Math.random() * 8999)}`;
    await handleExecuteFormation({
      formationId: formation,
      repo,
      instructionId: generatedId,
      title: payload.summaryText.slice(0, 68),
      objective: payload.summaryText,
      helmShots: 2,
    });
    setActiveTab('legion');
    return `Dispatched Legion ${formation.toUpperCase()} on ${repo} (${generatedId}).`;
  };

  const activePersonaDef = getPersonaDefinition(activePersona);
  const visibleSidebarItems = NAV_ITEMS.filter((n) =>
    activePersonaDef.visibleNavIds.includes(n.id)
  );
  const activeNavMeta = NAV_ITEMS.find((n) => n.id === activeTab) ?? NAV_ITEMS[0];
  const headerLinks = NAV_ITEMS.filter((n) => n.inHeader);

  const handleSelectPersona = useCallback(
    (nextPersona: PersonaTier) => {
      setActivePersona(nextPersona);
      const nextDef = getPersonaDefinition(nextPersona);
      if (!nextDef.visibleNavIds.includes(activeTab)) {
        setActiveTab('catalog');
      }
    },
    [activeTab, setActiveTab]
  );

  const idpRepo = snapshot?.repos.find((r) => r.repo === 'chidionyema/idp');
  const liveIdpSha =
    idpRepo?.liveMainSha ||
    idpRepo?.handoverMainSha ||
    'e23325ffaa000000000000000000000000000000';
  const idp7981Pr = snapshot?.reconciledPullRequests.find(
    (p) => p.repo === 'chidionyema/idp' && p.number === 7981
  );
  const greenlaneReadyCount =
    snapshot?.reconciledPullRequests.filter((p) => p.disposition === 'READY_FOR_GREENLANE').length ?? 0;

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#050811] text-slate-900 dark:text-slate-100">
      {/* Desktop Sovereign Sidebar (248px) */}
      <aside
        aria-label="Primary Estate Navigation"
        className="hidden lg:flex lg:flex-col lg:w-64 lg:shrink-0 border-r border-slate-200 dark:border-slate-800/80 bg-white dark:bg-[#080D1A]"
      >
        <div className="h-14 px-5 flex items-center justify-between border-b border-slate-200 dark:border-slate-800/80">
          <div className="flex items-baseline gap-1.5 whitespace-nowrap">
            <span className="font-sans text-sm font-bold tracking-wider uppercase text-slate-900 dark:text-slate-50">
              Genesis
            </span>
            <span className="font-display italic text-base font-medium text-amber-600 dark:text-amber-400">
              2100
            </span>
          </div>
          <span className="font-mono text-[10px] tracking-widest uppercase text-slate-400 dark:text-slate-500">
            OS v2
          </span>
        </div>

        <div className="px-5 py-3 border-b border-slate-200/70 dark:border-slate-800/60 flex items-center justify-between gap-2">
          <p className="font-display italic text-xs text-slate-600 dark:text-slate-400 truncate">
            See the whole. Move the real.
          </p>
          <span className="font-mono tabular-nums text-[10px] text-amber-600 dark:text-amber-400 shrink-0">
            {activePersonaDef.shortBadge}
          </span>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {visibleSidebarItems.map((item) => {
            const Icon = item.icon;
            const active = item.id === activeTab;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveTab(item.id)}
                aria-current={active ? 'page' : undefined}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                  active
                    ? 'bg-slate-900 text-white dark:bg-amber-500/15 dark:text-amber-300 dark:border dark:border-amber-500/30 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    active ? 'text-amber-400' : 'text-slate-400 dark:text-slate-500'
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800/80 space-y-3">
          <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
            Chesed first, Geburah second. Dual-root Optimus proof before yield.
          </div>
          <button
            type="button"
            onClick={() => setIsDark((d) => !d)}
            aria-label={isDark ? 'Switch to daylight workspace' : 'Switch to nocturnal 2100 workspace'}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap"
          >
            <span>{isDark ? 'Daylight Surface' : 'Nocturnal 2100'}</span>
            {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
          </button>
        </div>
      </aside>

      {/* Mobile Navigation Drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/70"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <div className="relative z-10 w-64 max-w-[82vw] bg-white dark:bg-[#080D1A] border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between p-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-baseline gap-1.5">
                  <span className="font-sans text-sm font-bold tracking-wider uppercase text-slate-900 dark:text-slate-50">
                    Genesis
                  </span>
                  <span className="font-display italic text-base text-amber-500 dark:text-amber-400">
                    2100
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileNavOpen(false)}
                  aria-label="Close navigation menu"
                  className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <nav className="space-y-1">
                {visibleSidebarItems.map((item) => {
                  const Icon = item.icon;
                  const active = item.id === activeTab;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setActiveTab(item.id);
                        setMobileNavOpen(false);
                      }}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium rounded-lg whitespace-nowrap ${
                        active
                          ? 'bg-slate-900 text-white dark:bg-amber-500/15 dark:text-amber-300 font-semibold'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      <Icon className="w-4 h-4 shrink-0" />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>

            <button
              type="button"
              onClick={() => setIsDark((d) => !d)}
              className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              <span>{isDark ? 'Daylight Surface' : 'Nocturnal 2100'}</span>
              {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Strict 3-Zone Top Bar Contract */}
        <header className="h-14 px-4 sm:px-6 lg:px-8 bg-white dark:bg-[#080D1A] border-b border-slate-200 dark:border-slate-800/80 flex items-center justify-between gap-8 shrink-0">
          {/* Zone 1: Brand Context / Mobile Menu Trigger */}
          <div className="flex items-center gap-2.5 min-w-0 shrink-0">
            <button
              type="button"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation menu"
              className="lg:hidden p-1.5 -ml-1 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 rounded-lg"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap truncate">
              Meridian Estate / <span className="text-amber-600 dark:text-amber-400">{activeNavMeta.shortLabel}</span>
            </span>
          </div>

          {/* Zone 2: 5 Clean Single-Line Section Links */}
          <nav
            aria-label="Quick section jump"
            className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-600 dark:text-slate-400"
          >
            {headerLinks.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveTab(item.id)}
                className={`py-1 transition-colors whitespace-nowrap shrink-0 ${
                  activeTab === item.id
                    ? 'text-slate-900 dark:text-amber-300 underline underline-offset-4 decoration-2 decoration-amber-500'
                    : 'hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {item.shortLabel}
              </button>
            ))}
          </nav>

          {/* Zone 3: Single Primary Action */}
          <div className="shrink-0">
            <button
              type="button"
              onClick={() => setVoiceModalOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Mic className="w-3.5 h-3.5" aria-hidden="true" />
              Voice Stage
            </button>
          </div>
        </header>

        {/* Global Loud Disruptive All-Surface Incident Interrupt (Visible Across All 12 Views) */}
        {snapshot?.beastGovernor?.activeIncident && (
          <AllSurfaceIncidentBanner
            incident={snapshot.beastGovernor.activeIncident}
            audioEnabled={snapshot.beastGovernor.dials.disruptiveAllSurfaceAlertAudio}
            onResolveAuto={() => handleResolveGlobalIncident('AUTO_COORDINATE_FIX')}
            onLoosenDialOverride={() => handleResolveGlobalIncident('LOOSEN_DIAL_OVERRIDE')}
            onOpenBeastTab={() => setActiveTab('beast')}
          />
        )}

        {/* Viewport Workspace */}
        <main
          className={`flex-1 w-full mx-auto ${
            activeTab === 'reactor'
              ? 'p-3 sm:p-5 lg:p-6 max-w-[1440px]'
              : 'p-4 sm:p-6 lg:p-8 max-w-[1380px]'
          }`}
        >
          {loading ? (
            <div className="space-y-6" aria-busy="true" aria-label="Loading live estate state">
              <div className="h-12 bg-slate-200/70 dark:bg-slate-800/50 rounded-xl animate-pulse" />
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="h-24 bg-slate-200/70 dark:bg-slate-800/50 rounded-xl animate-pulse" />
                <div className="h-24 bg-slate-200/70 dark:bg-slate-800/50 rounded-xl animate-pulse" />
                <div className="h-24 bg-slate-200/70 dark:bg-slate-800/50 rounded-xl animate-pulse" />
                <div className="h-24 bg-slate-200/70 dark:bg-slate-800/50 rounded-xl animate-pulse" />
              </div>
              <div className="h-[460px] bg-slate-200/70 dark:bg-slate-800/50 rounded-2xl animate-pulse" />
            </div>
          ) : loadError || !snapshot ? (
            <div
              role="alert"
              className="p-6 bg-white dark:bg-[#0B101D] border border-red-200 dark:border-red-900/70 rounded-xl space-y-3"
            >
              <h2 className="text-base font-semibold text-red-700 dark:text-red-400">
                Estate Control Plane State Load Failure
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {loadError || 'Backend snapshot unavailable.'}
              </p>
              <button
                type="button"
                onClick={fetchEstateState}
                className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg"
              >
                Retry State Sync
              </button>
            </div>
          ) : (
            <>
              <TempoChronosHeartbeatBar
                synchrony={snapshot.beastSynchrony}
                activePersona={activePersona}
                onSelectPersona={handleSelectPersona}
                activeHorizon={activeHorizon}
                onSelectHorizon={setActiveHorizon}
                heartbeatAudioEnabled={heartbeatAudioEnabled}
                onToggleHeartbeatAudio={() => setHeartbeatAudioEnabled((v) => !v)}
                onDeepLinkNavigate={handleDeepLinkNavigate}
              />

              {activeTab === 'beast' && (
                <BeastConvergenceView
                  initialBeast={snapshot.beastGovernor}
                  onRefreshState={fetchEstateState}
                  onNavigateTab={setActiveTab}
                />
              )}

              {activeTab === 'academy' && (
                <GenesisAcademyView
                  initialAcademy={snapshot.genesisAcademy}
                  onRefreshState={fetchEstateState}
                  onDeepLinkNavigate={handleDeepLinkNavigate}
                />
              )}

              {activeTab === 'standards' && (
                <SovereignStandardsMemoryBddView
                  initialStandards={snapshot.sovereignStandards}
                  onRefreshState={fetchEstateState}
                  onDeepLinkNavigate={handleDeepLinkNavigate}
                />
              )}

              {activeTab === 'catalog' && (
                <SovereignCatalogAndBrochureView
                  beast={snapshot.beastGovernor}
                  synchrony={snapshot.beastSynchrony}
                  activePersona={activePersona}
                  onSelectPersona={handleSelectPersona}
                  activeHorizon={activeHorizon}
                  onSelectHorizon={setActiveHorizon}
                  onDeepLinkNavigate={handleDeepLinkNavigate}
                  onRefreshState={fetchEstateState}
                />
              )}

              {activeTab === 'omega' && (
                <OmegaUniversalCoreView
                  initialOmega={snapshot.omegaCore}
                  onRefreshState={fetchEstateState}
                  onOpenIoGraph={() => setActiveTab('io')}
                />
              )}

              {activeTab === 'io' && (
                <IoWorkGraphAndIdentityView
                  initialWorkGraph={snapshot.ioWorkGraph}
                  canonicalSporeBytes={snapshot.swarmSynapse.sporeDna.byteLength}
                  onRefreshState={fetchEstateState}
                />
              )}

              {activeTab === 'projector' && (
                <RegisterProjectorView
                  initialProjector={snapshot.projector}
                  argonSync={snapshot.argonSync}
                  onSyncArgon={handleSyncArgon}
                  onRefreshState={fetchEstateState}
                  onOpenArgonConsole={() => setActiveTab('flow')}
                  onPromotePacketToLegion={handleSelectMissionForLegion}
                />
              )}

              {activeTab === 'synapse' && (
                <SwarmSynapseView
                  initialSynapse={snapshot.swarmSynapse}
                  onRefreshState={fetchEstateState}
                />
              )}

              {activeTab === 'reactor' && (
                <SpatialReactor2100
                  nodes={snapshot.reactorNodes}
                  optimusEventCount={snapshot.optimus.records.length}
                  greenlaneReadyCount={greenlaneReadyCount}
                  idpHeadSha={liveIdpSha}
                  onSwitchToMatrix={() => setActiveTab('fleet')}
                  onNavigateTab={setActiveTab}
                  onExecuteFormation={handleExecuteFormation}
                  onIngestOptimus={handleIngestOptimus}
                  onRunWatchdog={() => handleRunWatchdog()}
                  onReprobe={handleReprobe}
                  onOpenVoiceDrawer={() => setVoiceModalOpen(true)}
                  onPlayBriefing={handlePlayBriefing}
                  onStopBriefing={handleStopBriefing}
                  isPlayingBriefing={isPlayingBriefing}
                  briefingScript={briefingScript}
                  onSyncArgon={handleSyncArgon}
                />
              )}

              {activeTab === 'optimus' && (
                <OptimusAndBrainView
                  optimus={snapshot.optimus}
                  liveIdpSha={liveIdpSha}
                  onIngestSignedProbe={handleIngestOptimus}
                  onEvaluateAdmission={handleEvaluateOptimusAdmission}
                />
              )}

              {activeTab === 'fleet' && (
                <FleetOverviewView
                  snapshot={snapshot}
                  isReprobing={isReprobing}
                  onReprobe={handleReprobe}
                  onNavigateTab={setActiveTab}
                  onSelectMissionForLegion={handleSelectMissionForLegion}
                  onPlayBriefing={handlePlayBriefing}
                  onStopBriefing={handleStopBriefing}
                  isPlayingBriefing={isPlayingBriefing}
                  briefingScript={briefingScript}
                />
              )}

              {activeTab === 'legion' && (
                <LegionWorkforceView
                  executions={snapshot.executions}
                  prefilledMission={prefilledMission}
                  onExecuteFormation={handleExecuteFormation}
                />
              )}

              {activeTab === 'flow' && (
                <FlowAndBridgeView
                  argonSync={snapshot.argonSync}
                  flowInstructions={snapshot.flowInstructions}
                  liveIdpSha={liveIdpSha}
                  idp7981Pr={idp7981Pr}
                  onSyncArgon={handleSyncArgon}
                  onRefreshState={fetchEstateState}
                  onRunWatchdog={handleRunWatchdog}
                  onDispatchInbound={handleDispatchInbound}
                  onExecuteInstructionInLegion={handleSelectMissionForLegion}
                />
              )}

              {activeTab === 'greenlane' && (
                <GreenlaneTriageView
                  pullRequests={snapshot.reconciledPullRequests}
                  liveIdpSha={liveIdpSha}
                  onEvaluateGuard={handleEvaluateGuard}
                  onPromoteToLegion={handleSelectMissionForLegion}
                />
              )}

              {activeTab === 'chronos' && (
                <ChronosVenturesView
                  cadence={snapshot.cadence}
                  ventures={snapshot.ventures}
                  onDispatchVentureAudit={handleSelectMissionForLegion}
                />
              )}
            </>
          )}
        </main>
      </div>

      <VoiceCommandDrawer
        isOpen={voiceModalOpen}
        onClose={() => setVoiceModalOpen(false)}
        onExecuteVoiceAction={handleExecuteVoiceAction}
        onPlayBriefing={handlePlayBriefing}
        onStopBriefing={handleStopBriefing}
        isPlayingBriefing={isPlayingBriefing}
        briefingScript={briefingScript}
        briefingAudioMode={briefingAudioMode}
      />
    </div>
  );
}
