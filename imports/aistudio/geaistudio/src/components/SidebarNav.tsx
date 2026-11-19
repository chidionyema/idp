import {
  Activity,
  BarChart3,
  Binary,
  BookOpen,
  Briefcase,
  Compass,
  Cpu,
  Flame,
  GitBranch,
  Globe,
  HeartHandshake,
  Layers,
  MessageSquare,
  Microscope,
  Network,
  Radar,
  Search,
  ShieldCheck,
  Sliders,
  Smartphone,
  Sparkles,
  X,
} from 'lucide-react';
import { NavTabId } from '../types/api';

interface SidebarNavProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  vaultHydrated: boolean;
  openCircuitCount: number;
  onOpenConcierge?: () => void;
}

interface NavGroup {
  suiteLabel: string;
  items: Array<{
    id: NavTabId;
    label: string;
    description: string;
    icon: typeof Activity;
  }>;
}

const NAV_SUITES: NavGroup[] = [
  {
    suiteLabel: '01. Founder & Investor Suite',
    items: [
      {
        id: 'appliance_setup',
        label: 'Turnkey Setup & Phone DR',
        description: '0-CLI · 0-Sudo · Foreign Phone Boot',
        icon: Smartphone,
      },
      {
        id: 'phoenix_round_table',
        label: 'Phoenix Cold-Boot & Table',
        description: '06:00 UTC Drill · 10/10 FSMs · Seal',
        icon: Flame,
      },
      {
        id: 'investor_meridian',
        label: 'Meridian & Investor Room',
        description: 'Company site, ARR model & diligence',
        icon: Briefcase,
      },
      {
        id: 'founder_reactivity',
        label: 'Real-Time Founder View',
        description: 'MCC-001 · Web/App/Console · #8184',
        icon: Radar,
      },
      {
        id: 'union',
        label: 'Estate Grand Union',
        description: 'Chronos, InterCloud & 13-Pin Audit',
        icon: Globe,
      },
      {
        id: 'founder_plane',
        label: 'Founder & Rego Plane',
        description: 'UHNW OTTO Charter & Rego v1',
        icon: Sliders,
      },
      {
        id: 'telegram_vip',
        label: 'VIP CEO Telegram',
        description: 'Hermes · OTTO_NUMEN Concierge',
        icon: MessageSquare,
      },
      {
        id: 'mum_concierge',
        label: 'Mum’s Concierge',
        description: 'Auntie Ezinne · WhatsApp & EON-001',
        icon: HeartHandshake,
      },
    ],
  },
  {
    suiteLabel: '02. Commercial & Standout Academy',
    items: [
      {
        id: 'academy',
        label: 'Genesis Academy',
        description: '3-Rep theory & unseen transfer pilot',
        icon: BookOpen,
      },
      {
        id: 'mumchimp_research',
        label: 'Mumchimp & Research',
        description: 'Prospector-2100 autonomous yield',
        icon: Microscope,
      },
      {
        id: 'competitors',
        label: 'Competitor Benchmarks',
        description: 'Bifrost, LiteLLM, Portkey',
        icon: BarChart3,
      },
    ],
  },
  {
    suiteLabel: '03. Genesis Intelligence & Continuity',
    items: [
      {
        id: 'genesis_ttt',
        label: 'Genesis Survival & TTT',
        description: 'I-8088 RS(3,8) & GEN-TTT-001',
        icon: Network,
      },
      {
        id: 'symphony',
        label: 'Meridian Symphony',
        description: 'Estate living causal graph',
        icon: Compass,
      },
      {
        id: 'hermes',
        label: 'Hermes · Living Tree',
        description: 'Isopsephy, Qabalah & World Sky',
        icon: Sparkles,
      },
      {
        id: 'aura',
        label: 'AURA-2100 Obsidian',
        description: '64B binary manifold & forks',
        icon: Binary,
      },
    ],
  },
  {
    suiteLabel: '04. Infrastructure, Metering & Proofs',
    items: [
      {
        id: 'overview',
        label: 'Gateway Overview',
        description: 'Lanes, keys & WAL ledger',
        icon: Activity,
      },
      {
        id: 'packets',
        label: 'Packet Forensics',
        description: 'Live tokens & exact savings',
        icon: Radar,
      },
      {
        id: 'meridian',
        label: 'Meridian Battalion',
        description: '4-domain metering & coverage',
        icon: Cpu,
      },
      {
        id: 'supply',
        label: 'Model Supply & Legion',
        description: 'Free tiers & MSR small models',
        icon: Layers,
      },
      {
        id: 'dagster',
        label: 'Dagster Orchestration',
        description: 'Assets, sensors & migration',
        icon: GitBranch,
      },
      {
        id: 'falsifiers',
        label: 'Falsifiers & Tests',
        description: '41-case proof & 20/20 guarantees',
        icon: ShieldCheck,
      },
      {
        id: 'chaos',
        label: 'Chaos & Stress Lab',
        description: 'Fault injection & p99 SLA',
        icon: Flame,
      },
    ],
  },
];

export function SidebarNav({
  activeTab,
  onSelectTab,
  mobileOpen,
  onCloseMobile,
  vaultHydrated,
  openCircuitCount,
  onOpenConcierge,
}: SidebarNavProps) {
  const navContent = (
    <div className="flex h-full flex-col justify-between bg-white border-r border-slate-200 px-4 py-5 overflow-y-auto">
      <div>
        <div className="px-2 pb-4 border-b border-slate-200 space-y-3">
          <div>
            <div className="text-base font-bold tracking-tight text-slate-900">
              Meridian · Genesis
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              Sovereign Private-Office Plane
            </div>
          </div>

          {onOpenConcierge && (
            <button
              type="button"
              onClick={() => {
                onCloseMobile();
                onOpenConcierge();
              }}
              className="w-full flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
            >
              <span className="inline-flex items-center gap-1.5 font-medium truncate">
                <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" aria-hidden="true" />
                OTTO Concierge
              </span>
              <kbd className="font-mono text-[11px] text-slate-500 shrink-0">⌘K</kbd>
            </button>
          )}
        </div>

        <nav aria-label="Primary sections" className="mt-4 space-y-5">
          {NAV_SUITES.map((suite) => (
            <div key={suite.suiteLabel} className="space-y-1">
              <div className="px-2.5 text-[11px] font-semibold text-slate-400">
                {suite.suiteLabel}
              </div>
              {suite.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      onSelectTab(item.id);
                      onCloseMobile();
                    }}
                    aria-current={isActive ? 'page' : undefined}
                    className={`w-full flex items-start gap-2.5 rounded-lg px-2.5 py-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
                      isActive
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    <Icon
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        isActive ? 'text-blue-400' : 'text-slate-400'
                      }`}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <div className="text-sm font-medium leading-tight whitespace-nowrap truncate">
                        {item.label}
                      </div>
                      <div
                        className={`mt-0.5 text-xs truncate ${
                          isActive ? 'text-slate-300' : 'text-slate-500'
                        }`}
                      >
                        {item.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      <div className="border-t border-slate-200 mt-5 pt-4 px-2 space-y-2 text-xs text-slate-600">
        <div className="flex items-center justify-between">
          <span>Vault State</span>
          <span
            className={`font-medium ${
              vaultHydrated ? 'text-emerald-700' : 'text-red-700'
            }`}
          >
            {vaultHydrated ? 'Hydrated' : 'Needs Heal'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Open Circuits</span>
          <span
            className={`font-mono tabular-nums font-medium ${
              openCircuitCount === 0 ? 'text-slate-900' : 'text-amber-700'
            }`}
          >
            {openCircuitCount}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden lg:block w-64 shrink-0">{navContent}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-900/40"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 w-64 max-w-[80vw] h-full">
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close navigation menu"
              className="absolute right-3 top-4 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            >
              <X className="h-4 w-4" />
            </button>
            {navContent}
          </div>
        </div>
      )}
    </>
  );
}
