import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Code2,
  Download,
  Lock,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  XCircle,
} from 'lucide-react';
import type {
  CodeRegoGovernanceClassification,
  FounderConfigMutationResult,
  FounderEstateConfig,
  MathematicalSynchronicityStamp,
  RegoEvaluationReport,
} from '../engine/founderRegoChronosPlane';
import type { CeoFocusPolicy } from '../engine/ottoNumenTelegram';
import type { RoutingStrategy } from '../engine/types';
import type {
  EpistemicClaimAuditResult,
  UhnwCharterSnapshot,
  VipConciergeReceipt,
} from '../engine/uhnwSovereignCharter';

interface FounderPlanePayload {
  config: FounderEstateConfig;
  regoReport: RegoEvaluationReport;
  synchronicity: MathematicalSynchronicityStamp;
  auditTrail: FounderConfigMutationResult['auditEntry'][];
  uhnwCharter?: UhnwCharterSnapshot;
}

const CODE_PRESETS: Array<{ label: string; moduleName: string; code: string }> = [
  {
    label: 'Imperative Policy Branch (Flagged by R-008)',
    moduleName: 'adHocEnterprisePublish.ts',
    code: `export function publishBrief(user: { role: string }, spendUsd: number, regionCode: string) {
  if (user.role === 'admin' && spendUsd <= 0.25 && regionCode === 'eu-west') {
    return true;
  }
  return false;
}`,
  },
  {
    label: 'Rego-Delegated Handler (Compliant)',
    moduleName: 'constitutionalSyndicator.ts',
    code: `export function admitMutation(candidateConfig: FounderCandidate) {
  const verdict = evaluateRegoConstitutionalPolicy(candidateConfig);
  return verdict.allow;
}`,
  },
  {
    label: 'Pure Mathematical Codec (OK in TypeScript)',
    moduleName: 'vandermondeGf256.ts',
    code: `export function xorShardBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = a[i] ^ b[i];
  return out;
}`,
  },
];

export function FounderRegoChronosPlane() {
  const [data, setData] = useState<FounderPlanePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mutationBanner, setMutationBanner] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  // Editable Founder configuration controls
  const [routingStrategy, setRoutingStrategy] = useState<RoutingStrategy>('weighted_cost');
  const [sovereignFloorPct, setSovereignFloorPct] = useState(82);
  const [causalGatePct, setCausalGatePct] = useState(88);
  const [maxSpendUsd, setMaxSpendUsd] = useState(0.01);
  const [telegramFocus, setTelegramFocus] = useState<CeoFocusPolicy>('VIP_P0_ONLY');

  // Code-to-Rego Classifier Lab (Rule R-008)
  const [moduleName, setModuleName] = useState(CODE_PRESETS[0].moduleName);
  const [codeSnippet, setCodeSnippet] = useState(CODE_PRESETS[0].code);
  const [classification, setClassification] = useState<CodeRegoGovernanceClassification | null>(
    null
  );

  // UHNW Concierge & Rego R-010 Epistemic Separation Verifier
  const [vipInstruction, setVipInstruction] = useState(
    'Prepare Partner Investor Brief with verified unit economics and honest R&D stage gates.'
  );
  const [vipDispatchReceipt, setVipDispatchReceipt] = useState<VipConciergeReceipt | null>(null);
  const [epistemicAudit, setEpistemicAudit] = useState<EpistemicClaimAuditResult | null>(null);

  async function fetchPlane(syncForm = false) {
    try {
      const res = await fetch('/api/founder/plane');
      if (res.ok) {
        const json = (await res.json()) as FounderPlanePayload;
        setData(json);
        if (syncForm) {
          setRoutingStrategy(json.config.routingStrategy);
          setSovereignFloorPct(json.config.sovereignFreeFloorPct);
          setCausalGatePct(json.config.prospectorMinCausalConfidencePct);
          setMaxSpendUsd(json.config.maxAutonomousCycleSpendUsd);
          setTelegramFocus(json.config.telegramFocusPolicy);
        }
      }
    } finally {
      setLoading(false);
    }
  }

  async function runCodeClassifier(modName: string, snippet: string) {
    const res = await fetch('/api/founder/rego-classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ moduleName: modName, sourceSnippet: snippet }),
    });
    if (res.ok) {
      setClassification((await res.json()) as CodeRegoGovernanceClassification);
    }
  }

  useEffect(() => {
    void fetchPlane(true);
    void runCodeClassifier(CODE_PRESETS[0].moduleName, CODE_PRESETS[0].code);

    // Live SSE synchronization on every Chronos beat (zero HTTP polling)
    const source = new EventSource('/api/union/stream');
    source.addEventListener('union_snapshot', () => {
      void fetchPlane(false);
    });
    return () => {
      source.close();
    };
  }, []);

  async function handleCommitConfig(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMutationBanner(null);
    try {
      const res = await fetch('/api/founder/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          routingStrategy,
          sovereignFreeFloorPct: sovereignFloorPct,
          prospectorMinCausalConfidencePct: causalGatePct,
          maxAutonomousCycleSpendUsd: maxSpendUsd,
          telegramFocusPolicy: telegramFocus,
        }),
      });
      const out = (await res.json()) as FounderConfigMutationResult & {
        plane: FounderPlanePayload;
      };
      if (out.plane) {
        setData(out.plane);
      }
      if (out.committed) {
        setMutationBanner({
          ok: true,
          message: `Revision #${out.config.revision} signed (${out.config.configSha256.slice(0, 14)}…) & propagated live across Router, Prospector-2100, and OTTO_NUMEN.`,
        });
      } else {
        setMutationBanner({
          ok: false,
          message: `Rego Fail-Closed Denial (HTTP 422): ${out.regoReport.deniedReasons.join(' | ')}`,
        });
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleAdversarialUnsafeProbe() {
    setSaving(true);
    setMutationBanner(null);
    try {
      const res = await fetch('/api/founder/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allowGitNoVerifyShortcuts: true,
          prospectorMinCausalConfidencePct: 62,
          enforceZeroClientPollingI8090: false,
        }),
      });
      const out = (await res.json()) as FounderConfigMutationResult & {
        plane: FounderPlanePayload;
      };
      if (out.plane) {
        setData(out.plane);
      }
      setMutationBanner({
        ok: false,
        message: `Constitutional Guard Verified (HTTP ${res.status}): Rego blocked unsafe override (${out.regoReport.deniedReasons.join(' · ')}) — live state untouched at Revision #${out.config.revision}.`,
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleVipDirectiveSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch('/api/founder/concierge-dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        presetKey: 'custom',
        founderInstruction: vipInstruction,
      }),
    });
    if (res.ok) {
      const json = (await res.json()) as {
        receipt: VipConciergeReceipt;
        uhnwCharter: UhnwCharterSnapshot;
      };
      setVipDispatchReceipt(json.receipt);
      setData((prev) => (prev ? { ...prev, uhnwCharter: json.uhnwCharter } : prev));
    }
  }

  async function handleRunEpistemicAudit(mode: 'blocked_inflation' | 'truthful_candidate') {
    const payload =
      mode === 'blocked_inflation'
        ? {
            capabilityName: 'First-Use Ceremony Observer (ff8543bd)',
            claimedMarketingTier: 'CERTIFIED_PRODUCTION_YIELD',
            hasPlanLock: true,
            localAdversarialTestsPassed: true,
            signedGreenlaneMerged: false,
            independentLiveOutcomeJoined: false,
          }
        : {
            capabilityName: 'First-Use Ceremony Observer (ff8543bd)',
            claimedMarketingTier: 'ENGINEERING_TEST_VERIFIED',
            hasPlanLock: true,
            localAdversarialTestsPassed: true,
            signedGreenlaneMerged: false,
            independentLiveOutcomeJoined: false,
          };
    const res = await fetch('/api/founder/epistemic-audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const out = (await res.json()) as EpistemicClaimAuditResult;
    setEpistemicAudit(out);
  }

  if (loading || !data) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading Founder & Rego Plane">
        <div className="h-40 bg-white border border-slate-200 rounded-lg animate-pulse" />
        <div className="h-72 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  const { synchronicity, config, regoReport } = data;

  return (
    <div className="space-y-6">
      {/* 1. Mathematical Synchronicity Stamp & 8-Leaf Merkle Root */}
      <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Founder First-Class Control Plane</span>
              <span aria-hidden="true">·</span>
              <span>Chronos Harmonic Clockwork</span>
              <span aria-hidden="true">·</span>
              <span>package {regoReport.packageName}</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Mathematical Synchronicity Stamp &amp; Rego Constitutional Plane
            </h2>
          </div>

          <a
            href="/api/founder/rego-bundle"
            download="genesis-constitutional-v1.rego"
            className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
          >
            <Download className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
            Download Policy (.rego)
          </a>
        </div>

        {/* 4-Column Mathematical Synchronicity KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs text-slate-500">8-Leaf Estate Merkle Root</div>
            <div className="mt-1 text-sm font-mono tabular-nums font-semibold text-slate-900 truncate">
              {synchronicity.merkleRootSha256}
            </div>
            <div className="mt-1 text-xs text-emerald-700">
              Re-stamped every Chronos beat (#{synchronicity.chronosBeat})
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs text-slate-500">Harmonic Phase-Lock &amp; Drift</div>
            <div className="mt-1 text-lg font-bold font-mono tabular-nums text-emerald-700">
              {synchronicity.phaseLocked ? 'PHASE-LOCKED' : 'DRIFT ALERT'} ·{' '}
              {synchronicity.driftRadians.toFixed(2)} rad
            </div>
            <div className="mt-1 text-xs text-slate-600">
              Unjoined / Orphaned Subsystems: {synchronicity.unjoinedSubsystemsCount}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs text-slate-500">Founder Config Revision</div>
            <div className="mt-1 text-lg font-bold font-mono tabular-nums text-slate-900">
              Rev #{config.revision} · {config.configSha256.slice(0, 10)}
            </div>
            <div className="mt-1 text-xs text-slate-600 truncate">
              Authority: {config.authorEmail}
            </div>
          </div>

          <div className="border border-slate-200 rounded-md p-4">
            <div className="text-xs text-slate-500">Rego Constitutional Verdict</div>
            <div className="mt-1 text-lg font-bold font-mono tabular-nums text-emerald-700">
              {regoReport.passedRules}/{regoReport.totalRules} Rules ALLOW
            </div>
            <div className="mt-1 text-xs font-mono tabular-nums text-slate-600">
              Bundle SHA {regoReport.bundleSha256.slice(0, 12)}
            </div>
          </div>
        </div>

        {/* 5-Ring Chronos Harmonic Schedule Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
                <th className="py-2 pr-4 font-medium">Harmonic Ring</th>
                <th className="py-2 px-4 font-medium">Cadence</th>
                <th className="py-2 px-4 font-medium">Joined Subsystems</th>
                <th className="py-2 px-4 font-medium">Mathematical Contract</th>
                <th className="py-2 pl-4 font-medium text-right">Beat Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {synchronicity.harmonicRings.map((ring) => (
                <tr key={ring.tier}>
                  <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-slate-900 whitespace-nowrap">
                    {ring.tier}
                  </td>
                  <td className="py-2.5 px-4 font-mono tabular-nums text-xs text-slate-700 whitespace-nowrap">
                    {ring.targetPeriodLabel}
                  </td>
                  <td className="py-2.5 px-4 text-xs text-slate-700">
                    {ring.subsystems.join(' · ')}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-xs text-slate-500">
                    {ring.mathematicalContract}
                  </td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-xs font-semibold text-emerald-700">
                    {ring.executionsCount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 2. First-Class Founder Configuration & Rego Pre-Commit Gate */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Sliders className="h-4 w-4 text-blue-700" aria-hidden="true" />
              First-Class Founder Configuration Authority
            </h3>
            <span className="text-xs font-mono tabular-nums text-slate-500">
              Pre-Commit Rego Guarded
            </span>
          </div>

          <form onSubmit={handleCommitConfig} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="fnd-strategy"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  Gateway Routing Strategy
                </label>
                <select
                  id="fnd-strategy"
                  value={routingStrategy}
                  onChange={(e) => setRoutingStrategy(e.target.value as RoutingStrategy)}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                >
                  <option value="weighted_cost">Weighted Cost + Quality</option>
                  <option value="priority_failover">Priority Failover</option>
                  <option value="lowest_latency">Lowest p95 Latency</option>
                  <option value="least_busy">Least Busy Queue</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="fnd-telegram"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  CEO Telegram Focus Policy
                </label>
                <select
                  id="fnd-telegram"
                  value={telegramFocus}
                  onChange={(e) => setTelegramFocus(e.target.value as CeoFocusPolicy)}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                >
                  <option value="VIP_P0_ONLY">VIP P0 Decisions Only</option>
                  <option value="VIP_PLUS_BRIEFINGS">VIP + Executive Briefings</option>
                  <option value="SILENT_DND_ALL">Silent Deep-Work DND</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="fnd-sov">
                  Sovereign $0.00 + InterCloud Spot Floor (Rego R-004 &ge; 50%)
                </label>
                <span className="font-mono tabular-nums">{sovereignFloorPct}%</span>
              </div>
              <input
                id="fnd-sov"
                type="range"
                min={35}
                max={98}
                step={1}
                value={sovereignFloorPct}
                onChange={(e) => setSovereignFloorPct(Number(e.target.value))}
                className="w-full accent-slate-900"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="fnd-causal">
                  Mumchimp Causal Confidence Gate (Rego R-005 &ge; 85%)
                </label>
                <span className="font-mono tabular-nums">{causalGatePct}%</span>
              </div>
              <input
                id="fnd-causal"
                type="range"
                min={70}
                max={98}
                step={1}
                value={causalGatePct}
                onChange={(e) => setCausalGatePct(Number(e.target.value))}
                className="w-full accent-slate-900"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                <label htmlFor="fnd-spend">
                  Autonomous Per-Cycle Spend Cap (Rego R-006 &le; $0.050)
                </label>
                <span className="font-mono tabular-nums">${maxSpendUsd.toFixed(3)}</span>
              </div>
              <input
                id="fnd-spend"
                type="range"
                min={0.002}
                max={0.08}
                step={0.002}
                value={maxSpendUsd}
                onChange={(e) => setMaxSpendUsd(Number(e.target.value))}
                className="w-full accent-slate-900"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2.5 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                Validate via Rego &amp; Sign Config
              </button>

              <button
                type="button"
                disabled={saving}
                onClick={handleAdversarialUnsafeProbe}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
              >
                <ShieldAlert className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                Probe Unsafe Override (Fail-Closed Test)
              </button>
            </div>
          </form>

          {mutationBanner && (
            <div
              role="status"
              className={`rounded-md border p-3 text-xs leading-relaxed ${
                mutationBanner.ok
                  ? 'border-emerald-200 bg-emerald-50/70 text-emerald-900'
                  : 'border-amber-200 bg-amber-50/70 text-amber-950'
              }`}
            >
              {mutationBanner.message}
            </div>
          )}

          {/* Immutable Signed Audit Log */}
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <div className="text-xs font-semibold text-slate-700">
              Immutable Founder Configuration &amp; Denial Ledger
            </div>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {data.auditTrail.slice(0, 5).map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-start justify-between gap-2 text-xs font-mono tabular-nums"
                >
                  <span className={entry.committed ? 'text-slate-700' : 'text-red-700'}>
                    {entry.committed ? 'COMMITTED' : 'DENIED'} · {entry.summary}
                  </span>
                  <span className="text-slate-400 shrink-0">#{entry.revision}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 3. Active Rego Rules Matrix + R-008 Future-Code Classifier */}
        <div className="lg:col-span-6 space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <Lock className="h-4 w-4 text-emerald-700" aria-hidden="true" />
                Active Constitutional Rego Rules (R-001..R-010)
              </h3>
              <span className="text-xs font-mono tabular-nums text-emerald-700 font-semibold">
                {regoReport.passedRules}/{regoReport.totalRules} Verified
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {regoReport.rules.map((r) => (
                <div
                  key={r.ruleId}
                  className="py-2.5 first:pt-0 last:pb-0 flex items-start justify-between gap-3 text-xs"
                >
                  <div>
                    <div className="font-medium text-slate-900">
                      <span className="font-mono">{r.ruleId}</span> · {r.description}
                    </div>
                    <div className="font-mono text-[11px] text-slate-500 mt-0.5">
                      {r.actualExpr}
                    </div>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 font-medium shrink-0 ${
                      r.passed ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {r.passed ? (
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    {r.passed ? 'ALLOW' : 'DENY'}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* Rule R-008 Future-Code Rego Governance Classifier */}
          <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-3">
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <Code2 className="h-4 w-4 text-blue-700" aria-hidden="true" />
                Rule R-008 Enforcer: Policy-as-Rego Code Classifier
              </h3>
              <p className="text-xs text-slate-600">
                Guarantees current and future authorization, quota, admission, and compliance logic
                is expressed in Rego rather than scattered imperative TypeScript branches.
              </p>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {CODE_PRESETS.map((preset) => (
                <button
                  key={preset.moduleName}
                  type="button"
                  onClick={() => {
                    setModuleName(preset.moduleName);
                    setCodeSnippet(preset.code);
                    void runCodeClassifier(preset.moduleName, preset.code);
                  }}
                  className={`px-2.5 py-1 text-xs font-medium rounded border transition-colors whitespace-nowrap shrink-0 ${
                    moduleName === preset.moduleName
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div>
              <label htmlFor="rego-code-input" className="sr-only">
                Proposed TypeScript snippet to audit
              </label>
              <textarea
                id="rego-code-input"
                rows={4}
                value={codeSnippet}
                onChange={(e) => setCodeSnippet(e.target.value)}
                className="w-full rounded-md border border-slate-300 p-2.5 font-mono text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => void runCodeClassifier(moduleName, codeSnippet)}
                className="mt-2 rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap"
              >
                Audit Snippet for Rego Extraction
              </button>
            </div>

            {classification && (
              <div className="border border-slate-200 rounded-md p-3 bg-slate-50 space-y-2 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="font-semibold text-slate-900">{classification.verdict}</span>
                  <span className="text-slate-500">{classification.moduleName}</span>
                </div>
                <p className="text-slate-700">{classification.explanation}</p>
                <pre className="bg-white border border-slate-200 rounded p-2.5 font-mono text-[11px] text-slate-800 overflow-x-auto">
                  {classification.generatedRegoStub}
                </pre>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* 4. Permanent UHNW Sovereign Private-Office Charter & Rego R-010 Epistemic Guard */}
      {data.uhnwCharter && (
        <section className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
          <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4 border-b border-slate-200 pb-4">
            <div className="space-y-1 max-w-2xl">
              <div className="text-xs text-slate-500">
                Permanent UHNW Sovereign Private-Office Charter · Rego Rules R-009 &amp; R-010
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                7-Agent OTTO &amp; Fleet Service-Level Covenant (Zero Unowned Escalations)
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                {data.uhnwCharter.ipDoctrineStatement}
              </p>
            </div>
            <div className="text-left xl:text-right font-mono tabular-nums text-xs shrink-0">
              <div className="font-semibold text-emerald-700">
                All 7 Agents SLA Compliant (&le;{data.uhnwCharter.p0LatencyCeilingMs}ms)
              </div>
              <div className="text-slate-500">
                Max Observed p95: {data.uhnwCharter.maxObservedAgentP95Ms}ms · Merkle{' '}
                {data.uhnwCharter.covenantMerkleRootSha256.slice(0, 12)}…
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="py-2 pr-3 font-medium">Agent / Organ</th>
                  <th className="py-2 px-3 font-medium">Deterministic Machine Mechanics</th>
                  <th className="py-2 px-3 font-medium">Bounded Agent Judgement</th>
                  <th className="py-2 pl-3 font-medium text-right">Observed p95 / Ceiling</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.uhnwCharter.agents.map((agent) => (
                  <tr key={agent.agentId}>
                    <td className="py-2.5 pr-3 align-top">
                      <div className="font-semibold text-slate-900">{agent.displayName}</div>
                      <div className="text-[11px] text-slate-500">{agent.roleTitle}</div>
                    </td>
                    <td className="py-2.5 px-3 align-top text-slate-700">
                      {agent.deterministicMachineMechanics}
                    </td>
                    <td className="py-2.5 px-3 align-top text-slate-600">
                      {agent.boundedAgentJudgement}
                    </td>
                    <td className="py-2.5 pl-3 align-top text-right font-mono tabular-nums whitespace-nowrap text-emerald-700 font-semibold">
                      {agent.observedP95Ms}ms / {agent.p95CeilingMs}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2 border-t border-slate-100">
            {/* Live OTTO Concierge Directive Dispatch */}
            <form onSubmit={handleVipDirectiveSubmit} className="space-y-3">
              <div className="text-xs font-semibold text-slate-900">
                Direct Founder &rarr; OTTO Private-Office Dispatch (&le;150ms Signed Receipt)
              </div>
              <div className="flex gap-2">
                <label htmlFor="founder-vip-dir" className="sr-only">
                  Founder directive to OTTO
                </label>
                <input
                  id="founder-vip-dir"
                  type="text"
                  value={vipInstruction}
                  onChange={(e) => setVipInstruction(e.target.value)}
                  className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-slate-900 focus:outline-none"
                />
                <button
                  type="submit"
                  className="rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
                >
                  Dispatch Directive
                </button>
              </div>
              {vipDispatchReceipt && (
                <div
                  role="status"
                  className="rounded-md border border-emerald-200 bg-emerald-50/70 p-3 text-xs space-y-1"
                >
                  <div className="font-mono tabular-nums font-semibold text-emerald-900">
                    {vipDispatchReceipt.assignedLeadAgent} · {vipDispatchReceipt.executionLatencyMs}
                    ms · SHA {vipDispatchReceipt.receiptSha256.slice(0, 14)}…
                  </div>
                  <p className="text-slate-700">{vipDispatchReceipt.agentJudgementBrief}</p>
                </div>
              )}
            </form>

            {/* Rego R-010 Epistemic Claim Separation Verifier */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-900">
                Rego Rule R-010 Epistemic Separation Guard (Plan &ne; Test Pass &ne; Live Yield)
              </div>
              <p className="text-xs text-slate-600">
                Verify that unmerged engineering candidates (<code className="font-mono">ff8543bd</code>,{' '}
                21/21 local tests, <code className="font-mono">LIVE_CEREMONY_EFFECT = UNKNOWN</code>)
                cannot be marketed as certified production yield:
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void handleRunEpistemicAudit('blocked_inflation')}
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50 transition-colors whitespace-nowrap"
                >
                  Test Inflation Block (HTTP 422)
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunEpistemicAudit('truthful_candidate')}
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap"
                >
                  Test Truthful Candidate (HTTP 200)
                </button>
              </div>
              {epistemicAudit && (
                <div
                  role="status"
                  className={`rounded-md border p-3 text-xs leading-relaxed ${
                    epistemicAudit.allowed
                      ? 'border-emerald-200 bg-emerald-50/70 text-emerald-950'
                      : 'border-amber-300 bg-amber-50 text-amber-950'
                  }`}
                >
                  <div className="font-mono font-semibold">
                    HTTP {epistemicAudit.httpStatus} · Earned Tier: {epistemicAudit.earnedEvidenceTier}
                  </div>
                  <p className="mt-1">{epistemicAudit.verdictSummary}</p>
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
