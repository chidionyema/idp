import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowUpRight, CheckCircle2, Download, Search, ShieldCheck, X, Zap } from 'lucide-react';
import type { VipConciergeReceipt } from '../engine/uhnwSovereignCharter';
import type { NavTabId } from '../types/api';

interface SovereignConciergePaletteProps {
  open: boolean;
  onClose: () => void;
  onSelectTab: (tab: NavTabId) => void;
  onRunVerificationSuite: () => void;
  onPulseBeat: () => void;
}

interface QuickDestination {
  id: string;
  step?: string;
  label: string;
  subtitle: string;
  tab: NavTabId;
  category: 'Investor Pitch Sequence' | 'All Estate Surfaces';
}

const PITCH_AND_SURFACES: QuickDestination[] = [
  {
    id: 'pitch-1',
    step: 'Step 01',
    label: 'Meridian & Institutional Investor Room',
    subtitle: 'Thesis, live ARR/gross-margin sensitivity modeler, 9-pillar gap matrix & signed memo',
    tab: 'investor_meridian',
    category: 'Investor Pitch Sequence',
  },
  {
    id: 'pitch-2',
    step: 'Step 02',
    label: 'Mumchimp & Prospector-2100 Autonomous Research',
    subtitle: '266x cheaper causal research ($0.00018/cycle) feeding verified briefs into Mumchimp',
    tab: 'mumchimp_research',
    category: 'Investor Pitch Sequence',
  },
  {
    id: 'pitch-3',
    step: 'Step 03',
    label: 'Genesis Standout Academy (Unseen Transfer Pilot)',
    subtitle: 'Tri-representational convergence, boundary counterexamples & 3-item transfer scoring',
    tab: 'academy',
    category: 'Investor Pitch Sequence',
  },
  {
    id: 'pitch-4',
    step: 'Step 04',
    label: 'Founder Plane, Rego v1 & OTTO UHNW Covenant',
    subtitle: '10/10 Rego rules, 8-leaf Chronos Merkle stamp & 7-agent <=150ms service covenant',
    tab: 'founder_plane',
    category: 'Investor Pitch Sequence',
  },
  {
    id: 'pitch-5',
    step: 'Step 05',
    label: 'Estate Grand Union & 13-Pin Machine-Agent Audit',
    subtitle: 'IDP main d03f5d59 comparison, 21/21 observer+ratchet suite & VIP CEO Telegram',
    tab: 'union',
    category: 'Investor Pitch Sequence',
  },
  {
    id: 'surf-appliance-setup',
    label: 'Turnkey Appliance Setup & Foreign Phone DR',
    subtitle: 'Pure-UI 1-click 5-pillar setup, Tokyo/foreign zero-device phone bootstrap, 12/12 red-team & perpetual ratchet',
    tab: 'appliance_setup',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-phoenix',
    label: 'Operation Phoenix · Daily Cold-Boot & Round Table',
    subtitle: 'Clean-room temp clone, 10/10 Closed-Loop FSM proofs, 8-force quorum & 24h Go/Abort Seal',
    tab: 'phoenix_round_table',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-founder-reactivity',
    label: 'Real-Time Founder’s View (#8184 · BEAST Reactivity)',
    subtitle: '7-stage obligation custody, QUAD Ed25519 admission, monotonic fencing & Experiments A–F',
    tab: 'founder_reactivity',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-tg',
    label: 'VIP CEO Telegram (@otto_numen_bot)',
    subtitle: '5 Supergroup Forum Topics, zero-send heartbeat sink & 98% storm reduction',
    tab: 'telegram_vip',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-mum-concierge',
    label: 'Mum’s Sovereign Concierge (Auntie Ezinne)',
    subtitle: 'WhatsApp audio/large-print UX, EON-001 £95.11 credit, 9 Nov-16 falsifiers & G0–G5 gates',
    tab: 'mum_concierge',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-ttt',
    label: 'Genesis Survival RS(3,8) & GEN-TTT-001',
    subtitle: '5-cloud extinction recovery across all C(8,3)=56 subsets + stage-gated R&D',
    tab: 'genesis_ttt',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-supply',
    label: 'Model Supply & Legion Best-of-3',
    subtitle: 'Zero-retention sovereign specialists surpassing single Frontier quality',
    tab: 'supply',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-meridian',
    label: 'Meridian Battalion 4-Domain Metering',
    subtitle: 'FOCUS 1.0 micro-dollar billing & BLIND != 0 provenance',
    tab: 'meridian',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-falsifiers',
    label: '41-Case Integration, Falsifiers & Live Assurance',
    subtitle: 'INT-01..10 + F1..F31 executable proof suite & live HTTP/SSE endpoint matrix',
    tab: 'falsifiers',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-hermes',
    label: 'Hermes · The Living Tree',
    subtitle: 'Greek isopsephy, Hebrew gematria, 37-word canon & world resonance',
    tab: 'hermes',
    category: 'All Estate Surfaces',
  },
  {
    id: 'surf-symphony',
    label: 'Meridian Symphony & AURA-2100',
    subtitle: 'Estate causal constellation & 64-byte binary manifold',
    tab: 'symphony',
    category: 'All Estate Surfaces',
  },
];

export function SovereignConciergePalette({
  open,
  onClose,
  onSelectTab,
  onRunVerificationSuite,
  onPulseBeat,
}: SovereignConciergePaletteProps) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [customDirective, setCustomDirective] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [latestReceipt, setLatestReceipt] = useState<VipConciergeReceipt | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      const timer = setTimeout(() => inputRef.current?.focus(), 20);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return PITCH_AND_SURFACES;
    return PITCH_AND_SURFACES.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        (item.step && item.step.toLowerCase().includes(q))
    );
  }, [query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
      return;
    }
    if (e.key === 'ArrowDown' && filtered.length > 0) {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp' && filtered.length > 0) {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter' && filtered[activeIndex] && document.activeElement === inputRef.current) {
      e.preventDefault();
      onSelectTab(filtered[activeIndex].tab);
      onClose();
    }
  }

  async function handleDispatchDirective(
    presetKey:
      | 'investor_series_brief'
      | 'lock_sovereign_margins'
      | 'audit_13pin_doctrine'
      | 'sync_mumchimp_academy'
      | 'custom',
    instructionText: string
  ) {
    setDispatching(true);
    try {
      const res = await fetch('/api/founder/concierge-dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          presetKey,
          founderInstruction: instructionText,
        }),
      });
      if (res.ok) {
        const json = (await res.json()) as { receipt: VipConciergeReceipt };
        setLatestReceipt(json.receipt);
        setCustomDirective('');
      }
    } finally {
      setDispatching(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/50 p-4 sm:pt-14 overflow-y-auto"
      onKeyDown={handleKeyDown}
    >
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="OTTO Sovereign Private-Office Concierge"
        className="relative z-10 w-full max-w-3xl rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden"
      >
        {/* Search & Instant Command Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200">
          <Search className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
          <label htmlFor="concierge-search-input" className="sr-only">
            Search surfaces, investor pitch steps, or concierge actions
          </label>
          <input
            ref={inputRef}
            id="concierge-search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Jump to Investor Room, Academy, Rego, Mumchimp, Telegram… (↑↓ Enter)"
            className="w-full text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close concierge palette"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* One-Tap Executive & Investor Meeting Actions */}
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs text-slate-600 font-medium">
            UHNW Sovereign Concierge · Rego R-009 &le;150ms SLA Bound
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              href="/api/commercial/investor-memo"
              download="meridian-genesis-investor-diligence-memo.md"
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 whitespace-nowrap shrink-0"
            >
              <Download className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              Signed Investor Memo
            </a>
            <button
              type="button"
              onClick={() => {
                onRunVerificationSuite();
                onClose();
              }}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap shrink-0"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
              Verify All 32 Cases
            </button>
            <button
              type="button"
              onClick={() => {
                onPulseBeat();
              }}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap shrink-0"
            >
              <Zap className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
              Pulse Chronos Beat
            </button>
          </div>
        </div>

        {/* Live OTTO & Fleet Direct Dispatch Strip */}
        <div className="p-4 border-b border-slate-200 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-900">
              Direct OTTO &amp; Fleet VIP Concierge Dispatch (Machine Producer + Agent Judgement)
            </span>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                disabled={dispatching}
                onClick={() =>
                  void handleDispatchDirective(
                    'investor_series_brief',
                    'Prepare Investor Meeting diligence brief and verify unit economics.'
                  )
                }
                className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap"
              >
                Investor Readiness Sweep
              </button>
              <button
                type="button"
                disabled={dispatching}
                onClick={() =>
                  void handleDispatchDirective(
                    'audit_13pin_doctrine',
                    'Verify 13-Pin Machine-Agent boundary and AGENTS.md no-growth ratchet.'
                  )
                }
                className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap"
              >
                13-Pin Audit Check
              </button>
              <button
                type="button"
                disabled={dispatching}
                onClick={() =>
                  void handleDispatchDirective(
                    'sync_mumchimp_academy',
                    'Synchronize Prospector-2100 Mumchimp briefs and Academy transfer pilot.'
                  )
                }
                className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap"
              >
                Sync Mumchimp &amp; Academy
              </button>
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!customDirective.trim()) return;
              void handleDispatchDirective('custom', customDirective);
            }}
            className="flex gap-2"
          >
            <label htmlFor="otto-custom-directive" className="sr-only">
              Issue custom Founder directive to OTTO
            </label>
            <input
              id="otto-custom-directive"
              type="text"
              value={customDirective}
              onChange={(e) => setCustomDirective(e.target.value)}
              placeholder="Or issue a custom Founder directive to OTTO & Fleet…"
              className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
            />
            <button
              type="submit"
              disabled={dispatching || !customDirective.trim()}
              className="rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap shrink-0"
            >
              {dispatching ? 'Executing…' : 'Dispatch'}
            </button>
          </form>

          {latestReceipt && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3 text-xs space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono tabular-nums">
                <span className="font-semibold text-emerald-900 inline-flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                  {latestReceipt.assignedLeadAgent} · {latestReceipt.executionLatencyMs}ms (&le;150ms SLA)
                </span>
                <span className="text-slate-600">
                  Tier: {latestReceipt.epistemicTierEarned} · SHA {latestReceipt.receiptSha256.slice(0, 12)}
                </span>
              </div>
              <p className="text-slate-700">{latestReceipt.agentJudgementBrief}</p>
              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-slate-500">
                  Machine steps: {latestReceipt.machineProducerSteps.join(' · ')}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    onSelectTab(latestReceipt.recommendedTab);
                    onClose();
                  }}
                  className="inline-flex items-center gap-1 font-medium text-blue-700 hover:text-blue-900 whitespace-nowrap shrink-0 ml-2"
                >
                  Open Surface
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Guided Investor Pitch Sequence & Filtered Surface List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No matching surface found for &ldquo;{query}&rdquo;.
            </div>
          ) : (
            filtered.map((item, idx) => {
              const selected = idx === activeIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    onSelectTab(item.tab);
                    onClose();
                  }}
                  className={`w-full px-4 py-3 text-left flex items-center justify-between gap-4 transition-colors ${
                    selected ? 'bg-slate-100' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      {item.step && (
                        <>
                          <span className="font-mono font-semibold text-blue-700">{item.step}</span>
                          <span aria-hidden="true">·</span>
                        </>
                      )}
                      <span>{item.category}</span>
                    </div>
                    <div className="text-sm font-semibold text-slate-900 truncate mt-0.5">
                      {item.label}
                    </div>
                    <div className="text-xs text-slate-600 truncate">{item.subtitle}</div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-slate-400 shrink-0" aria-hidden="true" />
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
