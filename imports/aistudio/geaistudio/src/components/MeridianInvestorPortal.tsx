import React, { useEffect, useState } from 'react';
import {
  ArrowUpRight,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Lock,
  ShieldCheck,
} from 'lucide-react';
import meridianHeroImg from '../assets/images/meridian_investor_hero_1794814569927.jpg';
import type {
  CommercialGapClosureItem,
  InvestorUnitEconomicsOutput,
  MathematicalSynchronicityStamp,
} from '../engine/founderRegoChronosPlane';
import type { NavTabId } from '../types/api';

interface CommercialOverviewPayload {
  economics: InvestorUnitEconomicsOutput;
  gapMatrix: CommercialGapClosureItem[];
  synchronicity: MathematicalSynchronicityStamp;
  guaranteesVerified: number;
  guaranteesTotal: number;
  ensemblePassPct: number;
  frontierPassPct: number;
  ensembleCostReductionPct: number;
  prospectorSavingsPct: number;
  mumchimpPublishedCount: number;
  walReceipts: number;
  diligenceRequests: Array<{
    id: string;
    submittedAtUtc: string;
    investorName: string;
    firm: string;
    email: string;
    focusTrack: string;
    receiptSha256: string;
  }>;
}

interface MeridianInvestorPortalProps {
  onNavigateTab: (tab: NavTabId) => void;
}

export function MeridianInvestorPortal({ onNavigateTab }: MeridianInvestorPortalProps) {
  const [data, setData] = useState<CommercialOverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [heroImgFailed, setHeroImgFailed] = useState(false);

  // Interactive unit economics sliders
  const [enterpriseCustomers, setEnterpriseCustomers] = useState(45);
  const [avgMonthlyPlatformFeeUsd, setAvgMonthlyPlatformFeeUsd] = useState(4200);
  const [monthlyBillionsTokens, setMonthlyBillionsTokens] = useState(32);
  const [sovereignSharePct, setSovereignSharePct] = useState(88);
  const [recalculating, setRecalculating] = useState(false);

  // Validated Investor / Commercial Diligence Request Form
  const [investorName, setInvestorName] = useState('');
  const [firm, setFirm] = useState('');
  const [email, setEmail] = useState('');
  const [focusTrack, setFocusTrack] = useState('Institutional Lead / Series Diligence');
  const [formError, setFormError] = useState<string | null>(null);
  const [formReceipt, setFormReceipt] = useState<string | null>(null);
  const [submittingForm, setSubmittingForm] = useState(false);

  async function fetchCommercialOverview() {
    try {
      const res = await fetch('/api/commercial/overview');
      if (res.ok) {
        const json = (await res.json()) as CommercialOverviewPayload;
        setData(json);
        setEnterpriseCustomers(json.economics.input.enterpriseCustomers);
        setAvgMonthlyPlatformFeeUsd(json.economics.input.avgMonthlyPlatformFeeUsd);
        setMonthlyBillionsTokens(json.economics.input.monthlyBillionsTokensAcrossFleet);
        setSovereignSharePct(json.economics.input.sovereignAndSpotSharePct);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchCommercialOverview();

    // SSE real-time synchronization (I-8090 zero client polling)
    const source = new EventSource('/api/union/stream');
    source.addEventListener('union_snapshot', () => {
      void fetch('/api/commercial/overview')
        .then((r) => (r.ok ? r.json() : null))
        .then((next: CommercialOverviewPayload | null) => {
          if (next) {
            setData((prev) =>
              prev
                ? {
                    ...next,
                    economics: prev.economics,
                  }
                : next
            );
          }
        })
        .catch(() => {});
    });
    return () => {
      source.close();
    };
  }, []);

  async function handleModelChange(next: {
    enterpriseCustomers: number;
    avgMonthlyPlatformFeeUsd: number;
    monthlyBillionsTokensAcrossFleet: number;
    sovereignAndSpotSharePct: number;
  }) {
    setRecalculating(true);
    try {
      const res = await fetch('/api/commercial/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(next),
      });
      if (res.ok) {
        const updated = (await res.json()) as { economics: InvestorUnitEconomicsOutput };
        setData((prev) => (prev ? { ...prev, economics: updated.economics } : prev));
      }
    } finally {
      setRecalculating(false);
    }
  }

  async function handleDiligenceSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormReceipt(null);

    const trimmedName = investorName.trim();
    const trimmedFirm = firm.trim();
    const trimmedEmail = email.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (trimmedName.length < 2) {
      setFormError('Please enter your full name.');
      return;
    }
    if (trimmedFirm.length < 2) {
      setFormError('Please enter your fund or enterprise organization.');
      return;
    }
    if (!emailRegex.test(trimmedEmail)) {
      setFormError('Please enter a valid institutional email address.');
      return;
    }

    setSubmittingForm(true);
    try {
      const res = await fetch('/api/commercial/diligence-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          investorName: trimmedName,
          firm: trimmedFirm,
          email: trimmedEmail,
          focusTrack,
        }),
      });
      const out = (await res.json()) as {
        ok?: boolean;
        error?: string;
        entry?: { receiptSha256: string };
        overview?: CommercialOverviewPayload;
      };
      if (!res.ok || !out.ok) {
        setFormError(out.error ?? 'Unable to record diligence request.');
        return;
      }
      if (out.overview) {
        setData((prev) =>
          prev ? { ...out.overview!, economics: prev.economics } : out.overview!
        );
      }
      setFormReceipt(
        `Diligence access registered for ${trimmedName} (${trimmedFirm}) · Receipt SHA-256 ${out.entry?.receiptSha256.slice(0, 16) ?? ''}`
      );
      setInvestorName('');
      setFirm('');
      setEmail('');
    } finally {
      setSubmittingForm(false);
    }
  }

  if (loading || !data) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading Meridian Investor Portal">
        <div className="h-72 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-24 bg-white border border-slate-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const { economics } = data;

  return (
    <div className="space-y-8">
      {/* 0. Guided 5-Step Investor Meeting Walkthrough Bar */}
      <section
        aria-label="Investor meeting guided walkthrough"
        className="bg-slate-900 text-white rounded-lg px-5 py-3.5 flex flex-wrap items-center justify-between gap-3"
      >
        <div className="text-xs">
          <span className="font-semibold text-emerald-300">Sovereign Investor Pitch Sequence</span>
          <span className="text-slate-400 mx-2" aria-hidden="true">
            ·
          </span>
          <span className="text-slate-300">
            Jump directly across verified live commercial, governance, research, and Academy proof:
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(
            [
              { step: '01', label: 'Unit Economics (Here)', tab: 'investor_meridian' as NavTabId },
              { step: '02', label: 'Rego & OTTO SLA', tab: 'founder_plane' as NavTabId },
              { step: '03', label: '2100 Research -> Mumchimp', tab: 'mumchimp_research' as NavTabId },
              { step: '04', label: 'Standout Academy', tab: 'academy' as NavTabId },
              { step: '05', label: 'VIP CEO Telegram', tab: 'telegram_vip' as NavTabId },
            ] as const
          ).map((item) => (
            <button
              key={item.step}
              type="button"
              onClick={() => onNavigateTab(item.tab)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                item.tab === 'investor_meridian'
                  ? 'bg-white text-slate-900'
                  : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
              }`}
            >
              <span className="font-mono text-[11px] mr-1 opacity-75">{item.step}.</span>
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {/* 1. Flagship Meridian Hero Split (2-column items-stretch per frontend-design §5.13) */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch">
          <div className="lg:col-span-7 p-6 sm:p-8 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>Meridian Sovereign Systems</span>
                <span aria-hidden="true">·</span>
                <span>Genesis Operating Plane</span>
                <span aria-hidden="true">·</span>
                <span>London &amp; European Cloud Sovereignty</span>
              </div>

              <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-900 max-w-2xl [text-wrap:balance]">
                Frontier-Surpassing Intelligence at Sovereign Open-Weights Economics.
              </h2>

              <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">
                Meridian unifies verified small-model ensembles, multi-cloud spot arbitrage, FOCUS
                1.0 micro-dollar billing, autonomous causal research, and Rego policy-as-code into
                one mathematically synchronized commercial plane.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <a
                href={`/api/commercial/investor-memo?enterpriseCustomers=${enterpriseCustomers}&avgMonthlyPlatformFeeUsd=${avgMonthlyPlatformFeeUsd}&monthlyBillionsTokensAcrossFleet=${monthlyBillionsTokens}&sovereignAndSpotSharePct=${sovereignSharePct}`}
                download="meridian-genesis-investor-diligence-memo.md"
                className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2.5 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
              >
                <Download className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                Download Signed Investor Memo
              </a>
              <button
                type="button"
                onClick={() => onNavigateTab('founder_plane')}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
              >
                Inspect Rego &amp; Chronos Proof
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => onNavigateTab('mumchimp_research')}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0"
              >
                Open Mumchimp &amp; Prospector-2100
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="lg:col-span-5 relative min-h-[240px] bg-slate-900">
            {!heroImgFailed ? (
              <img
                src={meridianHeroImg}
                alt="Meridian sovereign technology architectural headquarters at golden hour"
                referrerPolicy="no-referrer"
                onError={() => setHeroImgFailed(true)}
                className="w-full h-full lg:h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-slate-900 text-slate-200">
                <ShieldCheck className="h-8 w-8 text-blue-400 mb-2" aria-hidden="true" />
                <span className="text-sm font-semibold">Meridian Sovereign Infrastructure</span>
                <span className="text-xs text-slate-400 mt-1">
                  Zero-Retention · FOCUS 1.0 · RS(3,8) Continuity
                </span>
              </div>
            )}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-4 text-white">
              <div className="text-xs font-mono tabular-nums text-slate-200">
                Merkle Root {data.synchronicity.merkleRootSha256.slice(0, 16)}… · Beat #
                {data.synchronicity.chronosBeat}
              </div>
              <div className="text-xs text-slate-300 mt-0.5">
                {data.guaranteesVerified}/{data.guaranteesTotal} Production Guarantees Verified Live
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Full-Width 4-Column Audited Proof Strip below Hero */}
      <section aria-label="Audited Commercial & Technical Proof">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <div className="text-xs text-slate-500">Ensemble Quality vs Single Frontier</div>
            <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
              {data.ensemblePassPct}% vs {data.frontierPassPct}%
            </div>
            <div className="mt-1 text-xs text-emerald-700">
              +{(data.ensemblePassPct - data.frontierPassPct).toFixed(1)}pp verified lift (500-ep
              Condorcet proof)
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <div className="text-xs text-slate-500">Inference &amp; Research Cost Advantage</div>
            <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
              {economics.cogsReductionPct}% Lower COGS
            </div>
            <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
              ${economics.blendedCogsPer1MTokensUsd.toFixed(3)}/1M vs $
              {economics.legacyFrontierCogsPer1MTokensUsd.toFixed(2)} Frontier
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <div className="text-xs text-slate-500">Modeled Consolidated Gross Margin</div>
            <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
              {economics.grossMarginPct}%
            </div>
            <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
              ARR ${(economics.annualizedRunRateArrUsd / 1_000_000).toFixed(2)}M · LTV:CAC{' '}
              {economics.ltvToCacRatio}x
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <div className="text-xs text-slate-500">Durable WAL &amp; Mumchimp Yield</div>
            <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
              {data.walReceipts.toLocaleString()} Receipts
            </div>
            <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
              0 dropped · {data.mumchimpPublishedCount} verified briefs live in Mumchimp
            </div>
          </div>
        </div>
      </section>

      {/* 2. Asymmetric Commercial Capabilities Architecture (Proposition -> Mechanism -> Proof) */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              Core Commercial Architecture &amp; Defensible Moat
            </h3>
            <p className="text-sm text-slate-600">
              Every product line shares one deterministic kernel, one billing ledger, and one
              constitutional Rego boundary.
            </p>
          </div>
          <span className="text-xs text-slate-500 font-mono tabular-nums">
            PR #7999 Radical Candor Compliant
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="text-xs text-slate-500">
                01. Sovereign Compute &amp; FOCUS 1.0 FinOps Gateway
              </div>
              <h4 className="text-base font-semibold text-slate-900">
                PennyD Multi-Lane Router, InterCloud Arbitrage &amp; Meridian Battalion Metering
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Routes enterprise workloads across zero-retention sovereign open-weights specialists
                (Nemotron, DeepSeek, Qwen3, MagenticBrain, Fara1.5) and elastic InterCloud spot
                GPUs. Sub-50ms spot reclamation failover and atomic CAS budget locks guarantee zero
                dropped receipts and micro-dollar CFO auditability.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
              <span className="text-slate-600 font-mono tabular-nums">
                Verified by INT-01..06, F1..F9 &amp; F19 · 0% double-billing
              </span>
              <button
                type="button"
                onClick={() => onNavigateTab('meridian')}
                className="font-medium text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 whitespace-nowrap"
              >
                Inspect 4-Domain Metering
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="text-xs text-slate-500">02. Autonomous Commercial Flywheel</div>
              <h4 className="text-base font-semibold text-slate-900">
                Prospector-2100 Causal Engine Feeding Mumchimp
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Replaces naive Frontier scrapers ($0.048/brief) with Bayesian EVSI triage and
                adversarial confounder falsification ($0.00018/cycle), publishing verified briefs
                straight into Mumchimp.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 text-xs">
              <span className="text-emerald-700 font-mono tabular-nums">
                {data.prospectorSavingsPct}% cost cut · 266x efficiency
              </span>
              <button
                type="button"
                onClick={() => onNavigateTab('mumchimp_research')}
                className="font-medium text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 whitespace-nowrap"
              >
                Open Mumchimp
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="text-xs text-slate-500">03. Extinction-Proof Resilience</div>
              <h4 className="text-base font-semibold text-slate-900">
                Cephalopod I-8088 RS(3,8) Multi-Cloud Continuity
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                4KB Ed25519-signed Galois Field Vandermonde spores survive simultaneous destruction
                of 5 out of 8 cloud providers with bit-exact WAL fence reconstruction.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 text-xs">
              <span className="text-slate-600 font-mono tabular-nums">All C(8,3)=56 subsets</span>
              <button
                type="button"
                onClick={() => onNavigateTab('genesis_ttt')}
                className="font-medium text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 whitespace-nowrap"
              >
                Verify RS(3,8)
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="text-xs text-slate-500">
                04. Constitutional Governance, Executive Concierge &amp; Academy
              </div>
              <h4 className="text-base font-semibold text-slate-900">
                Rego Policy-as-Code, Hermes · OTTO_NUMEN VIP Telegram &amp; 4-Tier Genesis Academy
              </h4>
              <p className="text-sm text-slate-600 leading-relaxed">
                Founder configuration acts as first-class state guarded pre-commit by{' '}
                <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">
                  package genesis.constitutional.v1
                </code>
                . Executive escalations shard cleanly across 5 Telegram Forum Topics with 98% alert
                reduction, while Genesis Academy trains novices through founders on live simulations.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
              <span className="text-slate-600 font-mono tabular-nums">
                10/10 Rego Constitutional Rules Active · 5 Harmonic Chronos Rings Locked
              </span>
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={() => onNavigateTab('telegram_vip')}
                  className="font-medium text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 whitespace-nowrap"
                >
                  VIP CEO Telegram
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateTab('academy')}
                  className="font-medium text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 whitespace-nowrap"
                >
                  Genesis Academy
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Permanent Commercial IP Distinction (16 Nov 2026 Deep Audit) */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1 max-w-3xl">
            <div className="text-xs font-mono text-slate-500">
              05. Defensible Methodological IP · Workforce Training &amp; Enterprise Advisory (GAP-09)
            </div>
            <h4 className="text-sm sm:text-base font-semibold text-slate-900">
              Reproducible Machine-Agent Discipline: Intent &rarr; Independently Measurable Effect
            </h4>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Our intellectual property is not an ad-hoc gate checklist: deterministic mechanics are
              assigned to fail-closed machines, uncertain judgement is reserved for bounded agents,
              and Rego Rule <code className="font-mono">R-010</code> enforces that every externally
              marketed capability independently earns its operational-yield proof (keeping candidate{' '}
              <code className="font-mono">ff8543bd</code>, 21/21 adversarial tests vs IDP{' '}
              <code className="font-mono">d03f5d59</code>, explicitly disclosed while{' '}
              <code className="font-mono">LIVE_CEREMONY_EFFECT = UNKNOWN</code>).
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onNavigateTab('union')}
              className="rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-800 hover:bg-slate-100 transition-colors whitespace-nowrap"
            >
              Inspect 13-Pin Audit
            </button>
            <button
              type="button"
              onClick={() => onNavigateTab('academy')}
              className="rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap"
            >
              Experience Unseen Transfer Lab
            </button>
          </div>
        </div>
      </section>

      {/* 3. Interactive Institutional Unit Economics & Gross Margin Sensitivity Modeler */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-blue-700" aria-hidden="true" />
              Interactive Institutional Unit Economics &amp; Margin Sensitivity Modeler
            </h3>
            <p className="text-sm text-slate-600">
              Stress-test Meridian ARR, blended COGS per 1M tokens, gross margin, and CAC payback
              across enterprise scale assumptions.
            </p>
          </div>
          <span className="text-xs font-mono tabular-nums text-slate-500">
            {recalculating ? 'Updating model…' : 'Live Deterministic Cohort Math'}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Sliders */}
          <div className="lg:col-span-5 space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="inv-customers">Enterprise Customers</label>
                <span className="font-mono tabular-nums">{enterpriseCustomers} logos</span>
              </div>
              <input
                id="inv-customers"
                type="range"
                min={10}
                max={250}
                step={5}
                value={enterpriseCustomers}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setEnterpriseCustomers(val);
                  void handleModelChange({
                    enterpriseCustomers: val,
                    avgMonthlyPlatformFeeUsd,
                    monthlyBillionsTokensAcrossFleet: monthlyBillionsTokens,
                    sovereignAndSpotSharePct: sovereignSharePct,
                  });
                }}
                className="w-full accent-slate-900"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="inv-fee">Monthly Platform Subscription / Logo</label>
                <span className="font-mono tabular-nums">
                  ${avgMonthlyPlatformFeeUsd.toLocaleString()}/mo
                </span>
              </div>
              <input
                id="inv-fee"
                type="range"
                min={1500}
                max={15000}
                step={300}
                value={avgMonthlyPlatformFeeUsd}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setAvgMonthlyPlatformFeeUsd(val);
                  void handleModelChange({
                    enterpriseCustomers,
                    avgMonthlyPlatformFeeUsd: val,
                    monthlyBillionsTokensAcrossFleet: monthlyBillionsTokens,
                    sovereignAndSpotSharePct: sovereignSharePct,
                  });
                }}
                className="w-full accent-slate-900"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="inv-tokens">Monthly Fleet Token Volume</label>
                <span className="font-mono tabular-nums">{monthlyBillionsTokens}B tokens/mo</span>
              </div>
              <input
                id="inv-tokens"
                type="range"
                min={5}
                max={150}
                step={5}
                value={monthlyBillionsTokens}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setMonthlyBillionsTokens(val);
                  void handleModelChange({
                    enterpriseCustomers,
                    avgMonthlyPlatformFeeUsd,
                    monthlyBillionsTokensAcrossFleet: val,
                    sovereignAndSpotSharePct: sovereignSharePct,
                  });
                }}
                className="w-full accent-slate-900"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="inv-sov">Sovereign Open-Weights + InterCloud Spot Share</label>
                <span className="font-mono tabular-nums">{sovereignSharePct}%</span>
              </div>
              <input
                id="inv-sov"
                type="range"
                min={55}
                max={98}
                step={1}
                value={sovereignSharePct}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setSovereignSharePct(val);
                  void handleModelChange({
                    enterpriseCustomers,
                    avgMonthlyPlatformFeeUsd,
                    monthlyBillionsTokensAcrossFleet: monthlyBillionsTokens,
                    sovereignAndSpotSharePct: val,
                  });
                }}
                className="w-full accent-slate-900"
              />
            </div>
          </div>

          {/* Financial Ledger Table */}
          <div className="lg:col-span-7 overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                  <th className="py-2 pr-4 font-medium">Institutional Metric</th>
                  <th className="py-2 px-4 font-medium text-right">Modeled Output</th>
                  <th className="py-2 pl-4 font-medium">Driver / Benchmark Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="py-2.5 pr-4 font-medium text-slate-900">
                    Annualized Run-Rate (ARR)
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums font-semibold text-slate-900">
                    ${economics.annualizedRunRateArrUsd.toLocaleString()}
                  </td>
                  <td className="py-2.5 pl-4 text-xs text-slate-600">
                    Platform SaaS + metered FOCUS 1.0 usage
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4 font-medium text-slate-900">
                    Consolidated Gross Margin
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums font-semibold text-emerald-700">
                    {economics.grossMarginPct}%
                  </td>
                  <td className="py-2.5 pl-4 text-xs text-slate-600">
                    Top-decile SaaS profile (vs ~40% AI wrapper peers)
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4 font-medium text-slate-900">
                    Blended Inference COGS / 1M
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-900">
                    ${economics.blendedCogsPer1MTokensUsd.toFixed(4)}
                  </td>
                  <td className="py-2.5 pl-4 text-xs text-slate-600">
                    {economics.cogsReductionPct}% below $11.25 Frontier baseline
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4 font-medium text-slate-900">
                    CAC Payback / LTV:CAC
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-900">
                    {economics.cacPaybackMonths} mos · {economics.ltvToCacRatio}x
                  </td>
                  <td className="py-2.5 pl-4 text-xs text-slate-600">
                    48-month enterprise cohort · {economics.netDollarRetentionPct}% NDR
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 pr-4 font-medium text-slate-900">Rule of 40 Composite</td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums font-semibold text-slate-900">
                    {economics.ruleOf40Score}
                  </td>
                  <td className="py-2.5 pl-4 text-xs text-slate-600">
                    85% YoY growth baseline + operating margin
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 4. 8-Pillar Commercial Gap-Closure Matrix */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Institutional Diligence &amp; Enterprise Procurement Gap-Closure Matrix
          </h3>
          <p className="text-sm text-slate-600">
            Every enterprise security, billing, continuity, IP provenance, and R&amp;D staging
            question answered with live executable proof.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="py-2.5 pr-4 font-medium">Pillar</th>
                <th className="py-2.5 px-4 font-medium">Mechanism &amp; Proof</th>
                <th className="py-2.5 pl-4 font-medium text-right">Stage Disposition</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.gapMatrix.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/70">
                  <td className="py-3 pr-4 align-top">
                    <div className="font-medium text-slate-900">
                      {item.id} · {item.pillar}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {item.investorOrEnterpriseQuestion}
                    </div>
                  </td>
                  <td className="py-3 px-4 align-top">
                    <div className="text-xs sm:text-sm text-slate-700">{item.estateMechanism}</div>
                    <div className="text-xs font-mono tabular-nums text-slate-500 mt-1">
                      {item.verificationProof}
                    </div>
                  </td>
                  <td className="py-3 pl-4 align-top text-right whitespace-nowrap">
                    {item.readinessStatus === 'VERIFIED_PRODUCTION' ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        Verified Live
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                        <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                        Spec-Gated (#8185)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. Validated Investor / Enterprise Partner Diligence Registration */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Register Partner Diligence Session or Request Signed Data Room Bundle
          </h3>
          <p className="text-sm text-slate-600">
            Generates a SHA-256 stamped diligence receipt and routes a quiet executive card to Topic
            #116 on Hermes · OTTO_NUMEN.
          </p>
        </div>

        <form
          onSubmit={handleDiligenceSubmit}
          noValidate
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end"
        >
          <div>
            <label htmlFor="dil-name" className="block text-xs font-medium text-slate-700 mb-1">
              Partner / Executive Name
            </label>
            <input
              id="dil-name"
              type="text"
              value={investorName}
              onChange={(e) => setInvestorName(e.target.value)}
              placeholder="e.g. Elena Rostova"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-slate-900 focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="dil-firm" className="block text-xs font-medium text-slate-700 mb-1">
              Fund or Enterprise Organization
            </label>
            <input
              id="dil-firm"
              type="text"
              value={firm}
              onChange={(e) => setFirm(e.target.value)}
              placeholder="e.g. Northstar Sovereign Capital"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-slate-900 focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="dil-email" className="block text-xs font-medium text-slate-700 mb-1">
              Institutional Email
            </label>
            <input
              id="dil-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="partner@fund.com"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-slate-900 focus:outline-none"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="dil-track" className="block text-xs font-medium text-slate-700">
              Diligence Track
            </label>
            <div className="flex gap-2">
              <select
                id="dil-track"
                value={focusTrack}
                onChange={(e) => setFocusTrack(e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
              >
                <option value="Institutional Lead / Series Diligence">Series Diligence</option>
                <option value="Enterprise Sovereign Pilot & DPA">Enterprise Pilot</option>
                <option value="InterCloud Strategic Compute Partner">Compute Partner</option>
              </select>
              <button
                type="submit"
                disabled={submittingForm}
                className="rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                {submittingForm ? 'Recording…' : 'Register Access'}
              </button>
            </div>
          </div>
        </form>

        {formError && (
          <p role="alert" className="text-xs font-medium text-red-700">
            {formError}
          </p>
        )}
        {formReceipt && (
          <p role="status" className="text-xs font-mono tabular-nums text-emerald-700">
            {formReceipt}
          </p>
        )}

        {data.diligenceRequests.length > 0 && (
          <div className="pt-3 border-t border-slate-100 space-y-1.5">
            <div className="text-xs font-medium text-slate-500">
              Recent Stamped Diligence Access Log
            </div>
            {data.diligenceRequests.slice(0, 3).map((req) => (
              <div
                key={req.id}
                className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600 font-mono tabular-nums"
              >
                <span>
                  {req.investorName} · {req.firm} ({req.focusTrack})
                </span>
                <span>Receipt {req.receiptSha256.slice(0, 12)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
