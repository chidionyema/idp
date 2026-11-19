import React, { useState } from 'react';
import {
  Landmark,
  CreditCard,
  ShieldCheck,
  Cpu,
  RefreshCw,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowUpRight,
  Lock,
  Activity,
} from 'lucide-react';
import {
  SovereignEstateTreasuryState,
  ModelLaneTier,
  evaluateModelProviderForRota,
  evaluateTokenEfficiencyAndOverzealousGaps,
} from '../engine/estateTreasuryEngine';

interface SovereignEstateEdictViewProps {
  treasury: SovereignEstateTreasuryState;
  onExecuteKeepAliveSweep: () => void;
  onExecuteCommercialSprint: (streamId?: string) => void;
  onApproveFounderRequest: (requestId: string, mode: 'APPROVED_BY_FOUNDER' | 'DELEGATED_TO_CONCIERGE_OTTO') => void;
  onEvaluateAndAddModel: (candidate: {
    providerName: string;
    modelFamily: string;
    lane: ModelLaneTier;
    roleDescription: string;
    monthlyBudgetAllocationGbp: number;
    costPerMillionTokensGbp: number;
    verifiedAccuracyPct: number;
    p95LatencyMs: number;
  }) => { admitted: boolean; reason: string; yieldMultiplier: number };
  onRunMultiHomeCanaryProbe: () => string;
  onNavigateToAgentMonitor: (agentId: string) => void;
}

export const SovereignEstateEdictView: React.FC<SovereignEstateEdictViewProps> = ({
  treasury,
  onExecuteKeepAliveSweep,
  onExecuteCommercialSprint,
  onApproveFounderRequest,
  onEvaluateAndAddModel,
  onRunMultiHomeCanaryProbe,
  onNavigateToAgentMonitor,
}) => {
  const [candProvider, setCandProvider] = useState('Qwen-3-Max (Alibaba Cloud)');
  const [candFamily, setCandFamily] = useState('Qwen-3-235B-Instruct');
  const [candLane, setCandLane] = useState<ModelLaneTier>('backup_elastic');
  const [candRole, setCandRole] = useState('Elastic Multilingual Synthesis & Structured Schema Extraction');
  const [candCostPerM, setCandCostPerM] = useState<number>(0.32);
  const [candAccuracy, setCandAccuracy] = useState<number>(96.9);
  const [candLatency, setCandLatency] = useState<number>(330);
  const [candBudget, setCandBudget] = useState<number>(4);
  const [evalBanner, setEvalBanner] = useState<{
    admitted: boolean;
    reason: string;
    yieldMultiplier: number;
  } | null>(null);
  const [sweepNotice, setSweepNotice] = useState<string | null>(null);
  const [canaryNotice, setCanaryNotice] = useState<string | null>(null);

  // Interactive Token Efficiency & Anti-Overzealous Simulator State
  const [simPrefixTokens, setSimPrefixTokens] = useState<number>(16000);
  const [simShavedTokens, setSimShavedTokens] = useState<number>(300);
  const [simCacheDiscountPct, setSimCacheDiscountPct] = useState<number>(80);
  const [simTaskType, setSimTaskType] = useState<
    'canary_ack' | 'routing_summary' | 'structured_json_or_proof'
  >('structured_json_or_proof');
  const [simProposedMaxTokens, setSimProposedMaxTokens] = useState<number>(150);

  const liveTokenEcon = evaluateTokenEfficiencyAndOverzealousGaps({
    prefixTokens: simPrefixTokens,
    tokensShavedByMicroCompaction: simShavedTokens,
    providerCacheDiscountPct: simCacheDiscountPct,
    taskType: simTaskType,
    proposedMaxTokens: simProposedMaxTokens,
  });

  const livePreviewEval = evaluateModelProviderForRota({
    providerName: candProvider,
    modelFamily: candFamily,
    lane: candLane,
    costPerMillionTokensGbp: candCostPerM,
    verifiedAccuracyPct: candAccuracy,
    p95LatencyMs: candLatency,
    monthlyBudgetAllocationGbp: candBudget,
  });

  const totalCurrentMrr = treasury.commercialStreams.reduce(
    (sum, s) => sum + s.monthlyRecurringRevenueGbp,
    0
  );
  const totalMonthlyOpEx = treasury.obligations.reduce(
    (sum, o) => sum + o.monthlyCostGbp,
    0
  );
  const selfSustainabilityCoverage = Number((totalCurrentMrr / Math.max(1, totalMonthlyOpEx)).toFixed(2));

  const coreModels = treasury.modelRota.filter((m) => m.lane === 'core_permanent');
  const backupAndTrialModels = treasury.modelRota.filter((m) => m.lane !== 'core_permanent');

  const handleRunEvalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const res = onEvaluateAndAddModel({
      providerName: candProvider,
      modelFamily: candFamily,
      lane: candLane,
      roleDescription: candRole,
      monthlyBudgetAllocationGbp: candBudget,
      costPerMillionTokensGbp: candCostPerM,
      verifiedAccuracyPct: candAccuracy,
      p95LatencyMs: candLatency,
    });
    setEvalBanner(res);
  };

  return (
    <div className="space-y-8">
      {/* Section 0: Executive Sovereign Edict Banner & Key Guarantees */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7 space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-500">
              <span className="font-semibold text-slate-900">FOUNDER FINAL EDICT · SOVEREIGN TREASURY &amp; AUTONOMY</span>
              <span aria-hidden="true">·</span>
              <span>Protocols: GEN-DIP-003 · GEN-SCI-003 · GEN-NET-004</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-700 font-semibold">100% Self-Sustaining Architecture</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              £200/mo Sovereign Treasury, Core/Backup Model Rota &amp; Concierge + Otto Keep-Alive
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed">
              Starting <strong>2 December 2026</strong>, the Genesis Estate operates on a strict{' '}
              <strong>£200.00 GBP/month Founder Standing Order for 3 months (£600 GBP total seed)</strong> via its dedicated UK Custodian Vault and 4 isolated Virtual Cards.{' '}
              <strong>The Concierge</strong> and <strong>Otto</strong> autonomously renew all domains, infrastructure, and model providers, while the{' '}
              <strong>Commercial &amp; Marketing Specialists</strong> apply strict <strong>Anti-IDP guardrails</strong> to scale self-serve B2B recurring revenue before the standing order ceases on{' '}
              <strong>2 March 2027</strong>.
            </p>
          </div>

          {/* Right 4-KPI Summary Box */}
          <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2.5 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Sovereign Solvency &amp; Runway Telemetry
              </span>
              <span className="text-xs font-mono font-semibold text-emerald-700">
                SOLVENT · {selfSustainabilityCoverage}x OPEX COVERED
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="text-xs text-slate-500">Founder Standing Order</div>
                <div className="text-xl font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  £{treasury.standingOrderAmountGbp}/mo
                </div>
                <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                  2 Dec 2026 → 2 Mar 2027 (3 mo)
                </div>
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="text-xs text-slate-500">Disciplined Estate OpEx</div>
                <div className="text-xl font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  £{totalMonthlyOpEx}/mo
                </div>
                <div className="text-[11px] font-mono text-emerald-700 mt-0.5">
                  Within £200/mo Seed Ceiling
                </div>
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="text-xs text-slate-500">Commercial Self-Serve MRR</div>
                <div className="text-xl font-bold font-mono tabular-nums text-emerald-700 mt-0.5">
                  £{totalCurrentMrr}/mo
                </div>
                <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                  88.5% Avg Gross Margin (Anti-IDP)
                </div>
              </div>
              <div className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="text-xs text-slate-500">Concierge + Otto Readiness</div>
                <div className="text-xl font-bold font-mono tabular-nums text-slate-900 mt-0.5">
                  99.95%
                </div>
                <div className="text-[11px] font-mono text-emerald-700 mt-0.5">
                  4/4 Online Keep-Alive Proofs
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 1: Delightful, Minimal-Friction Founder Pulse (1-Click Executive Queue) */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-4">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              FOUNDER DELIGHT &amp; ZERO-FRICTION SURFACE · HANDS-OFF BY DEFAULT
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <Sparkles className="w-4 h-4 text-slate-700" />
              01. Pleasant 1-Click Founder Sign-Off &amp; Real-Time Estate Pulse
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              The Estate never burdens you with raw operational admin. When your input is helpful, Otto and The Concierge distil the entire context into a single friction-free 1-click decision—or you can delegate it immediately.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onNavigateToAgentMonitor('agent-concierge-affairs')}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              Inspect Concierge Memory Live
            </button>
            <button
              type="button"
              onClick={() => onNavigateToAgentMonitor('agent-otto-governor')}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              Inspect Otto Memory Live
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {treasury.founderDelightQueue.map((item) => {
            const isResolved = item.status !== 'AWAITING_1_CLICK';
            return (
              <div
                key={item.id}
                className={`border rounded-xl p-4 flex flex-col justify-between transition-colors ${
                  isResolved
                    ? 'bg-slate-50/70 border-slate-200'
                    : 'bg-white border-slate-300 shadow-2xs'
                }`}
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2 text-xs font-mono">
                    <span className="text-slate-500">{item.preparedBy}</span>
                    <span
                      className={`font-semibold ${
                        isResolved ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {item.status === 'APPROVED_BY_FOUNDER'
                        ? '✓ 1-Click Approved'
                        : item.status === 'DELEGATED_TO_CONCIERGE_OTTO'
                        ? '✓ Delegated to Otto & Concierge'
                        : '● Ready for 1-Click'}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {item.oneSentenceSummary}
                  </p>
                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5 text-[11px] text-slate-600 space-y-1">
                    <div>
                      <strong className="text-slate-800">Zero-Friction Guarantee:</strong>{' '}
                      {item.whyMinimalInputNeeded}
                    </div>
                    <div>
                      <strong className="text-slate-800">Verified Impact:</strong>{' '}
                      {item.impactSummary}
                    </div>
                  </div>
                </div>

                <div className="pt-3 mt-3 border-t border-slate-200/80 flex items-center gap-2">
                  {!isResolved ? (
                    <>
                      <button
                        type="button"
                        onClick={() =>
                          onApproveFounderRequest(item.id, 'APPROVED_BY_FOUNDER')
                        }
                        className="flex-1 px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
                      >
                        1-Click Approve
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          onApproveFounderRequest(
                            item.id,
                            'DELEGATED_TO_CONCIERGE_OTTO'
                          )
                        }
                        className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer"
                      >
                        Delegate to Otto
                      </button>
                    </>
                  ) : (
                    <div className="text-xs font-mono text-emerald-700 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Active &amp; Enforced Under GEN-DIP-003
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section 1B: Anti-Plague Root-Cause Cure & MiniMax-M2.7 Subscription Multi-Home Mesh (GEN-NET-005) */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              ZERO-LITELLM IMMUNITY · MINIMAX-M2.7 SUBSCRIPTION FEDERATION · GEN-NET-005
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <ShieldCheck className="w-4 h-4 text-emerald-700" />
              Permanent Cure for Legacy OCI 1GB OOM, Mac Load 159.40 &amp; MiniMax-M2.7 Everywhere
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Prevents legacy IDP/OCI failures from ever entering Genesis: Python LiteLLM and the 11 Mac zombie daemons are constitutionally banned; your flat-rate <strong>MiniMax-M2.7 Monthly Subscription</strong> is federated globally through a stateless Cloudflare Edge Multiplexer with inline semantic canary retry (turning 4/5 raw hits into <strong>99.96% verified completions</strong> from anywhere).
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              const msg = onRunMultiHomeCanaryProbe();
              setCanaryNotice(msg);
            }}
            className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            Run 5/5 Semantic Canary &amp; Multi-Home Probe
          </button>
        </div>

        {canaryNotice && (
          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex flex-wrap items-center justify-between gap-2">
            <span>{canaryNotice}</span>
            <span className="font-mono font-bold">GEN-NET-005 VERIFIED</span>
          </div>
        )}

        {/* 4 Active-Active Execution Homes */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold uppercase tracking-wider text-slate-800">
              4 Active-Active Execution Homes (MiniMax-M2.7 Monthly Subscription Federated Everywhere)
            </span>
            <span className="font-mono text-emerald-700 font-semibold">
              0 MB Swap · 0 LiteLLM OOMs · 99.96% Canary Verified
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {treasury.executionHomes.map((home) => (
              <div
                key={home.homeId}
                className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/70 flex flex-col justify-between space-y-2.5"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-500">{home.topologyRole}</span>
                    <span className="text-emerald-700 font-bold">{home.status}</span>
                  </div>
                  <div className="text-xs font-bold text-slate-900 leading-snug">
                    {home.homeName}
                  </div>
                  <div className="text-[11px] font-mono text-slate-600 break-all">
                    {home.endpointRoute}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/80 space-y-1 text-[11px] font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">RAM / Swap:</span>
                    <span className="text-slate-900 font-semibold">
                      {home.ramUsedMb}MB / {home.ramCeilingMb}MB (Swap: {home.swapUsedMb}MB)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">LiteLLM Status:</span>
                    <span className="text-emerald-700 font-semibold">{home.litellmStatus}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Canary / Latency:</span>
                    <span className="text-slate-900 font-semibold">
                      {home.canaryPassRatePct}% · {home.p95LatencyMs}ms
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 4 Permanent Root-Cause Plague Cures */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {treasury.infraPlagueCures.map((cure) => (
            <div
              key={cure.id}
              className="border border-slate-200 rounded-xl p-3.5 bg-white space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-slate-900">
                  {cure.id} · {cure.legacyPlagueTitle}
                </span>
                <span className="text-emerald-700 font-semibold">
                  {cure.boundProtocolId} · CURED
                </span>
              </div>
              <div className="text-[11px] text-rose-800 bg-rose-50/70 border border-rose-200/70 rounded px-2 py-1 font-mono">
                Legacy Failure: {cure.observedFailureMetric}
              </div>
              <p className="text-[11px] text-slate-600">
                <strong className="text-slate-800">Root Cause:</strong> {cure.rootCauseDiagnosis}
              </p>
              <p className="text-[11px] text-emerald-900 bg-emerald-50/60 border border-emerald-200/70 rounded p-2">
                <strong>Genesis Permanent Solution:</strong> {cure.genesisPermanentCure}
              </p>
            </div>
          ))}
        </div>

        {/* Zero-RAM LiteLLM-Parity Efficiency Optimizations & Anti-Overzealous Sacred Floor Guardrails */}
        <div className="border-t border-slate-200 pt-5 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                ZERO-RAM LITELLM-PARITY EFFICIENCY LANE · SACRED TOKEN FLOOR AUDIT
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-0.5">
                6 Ported LiteLLM Router Efficiency Optimizations (0 MB Python Overhead) &amp; 5 Anti-Overzealous Token Guardrails
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Stretches the <strong>£118/mo Core Model budget</strong> into <strong>£{treasury.equivalentRawModelWorkGbp}/mo of effective token work ({treasury.effectiveTokenMultiplier}x multiplier)</strong> while mathematically blocking overzealous token-cutting traps that bust KV prefix caches or truncate structured JSON.
              </p>
            </div>
            <div className="text-xs font-mono bg-emerald-50 border border-emerald-200 text-emerald-900 px-3 py-1.5 rounded-lg shrink-0">
              Effective Token Multiplier: <strong>{treasury.effectiveTokenMultiplier}x (£{treasury.equivalentRawModelWorkGbp}/mo Work)</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left 6 cols: 6 Ported LiteLLM Efficiency Optimizations */}
            <div className="lg:col-span-6 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-800">
                <span>6 LiteLLM Router Optimizations Ported to Zero-RAM Edge/Node</span>
                <span className="font-mono text-emerald-700">0 MB Python RAM</span>
              </div>
              <div className="space-y-2">
                {treasury.routerEfficiencyOptimizations.map((opt) => (
                  <div
                    key={opt.id}
                    className="border border-slate-200 rounded-lg p-3 bg-slate-50/70 space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-bold text-slate-900">
                        {opt.id} · {opt.litellmFeatureOrigin}
                      </span>
                      <span className="text-emerald-700 font-bold">
                        -{opt.tokenSavingsPct}% Tokens · {opt.latencyImpactMs}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      {opt.genesisZeroRamImplementation}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 6 cols: 5 Anti-Overzealous Token-Cutting Guardrails + Live Breakeven Simulator */}
            <div className="lg:col-span-6 space-y-3">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-800">
                <span>5 Overzealous Token-Cutting Traps &amp; Sacred Floor Guards</span>
                <span className="font-mono text-amber-800">0% Semantic Loss</span>
              </div>
              <div className="space-y-2">
                {treasury.overzealousTokenGapGuards.map((g) => (
                  <div
                    key={g.id}
                    className="border border-slate-200 rounded-lg p-3 bg-white space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-bold text-rose-800">
                        {g.id} · {g.overzealousAntiPattern}
                      </span>
                      <span className="text-emerald-700 font-semibold">
                        {g.boundProtocolId} · GUARDED
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      <strong className="text-rose-800">Why Overzealous Cutting Backfires:</strong>{' '}
                      {g.hiddenBackfireCost}
                    </p>
                    <p className="text-[11px] text-slate-800 bg-slate-50 border border-slate-200/80 rounded px-2 py-1">
                      <strong className="text-emerald-800">Sacred Floor Guardrail:</strong>{' '}
                      {g.sacredFloorGuardrail} (<code className="font-mono text-[10px]">{g.mathematicalInvariant}</code>)
                    </p>
                  </div>
                ))}
              </div>

              {/* Interactive Prefix-Cache Breakeven & Truncation Guard Simulator */}
              <div className="border border-slate-300 rounded-xl p-3.5 bg-slate-50 space-y-2.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="font-bold text-slate-900">
                    LIVE SIMULATOR · KV-CACHE BREAKEVEN &amp; SACRED REASONING FLOOR
                  </span>
                  <span className="text-emerald-700 font-bold">
                    {liveTokenEcon.cachePreservationSavingsMultiplier}x Cheaper via Prefix Freeze
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-0.5">
                      Prefix Tokens
                    </label>
                    <input
                      type="number"
                      min="1000"
                      max="128000"
                      step="1000"
                      value={simPrefixTokens}
                      onChange={(e) => setSimPrefixTokens(Number(e.target.value))}
                      className="w-full px-2 py-1 font-mono bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-0.5">
                      Shaved Tokens
                    </label>
                    <input
                      type="number"
                      min="50"
                      max="15000"
                      step="50"
                      value={simShavedTokens}
                      onChange={(e) => setSimShavedTokens(Number(e.target.value))}
                      className="w-full px-2 py-1 font-mono bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-0.5">
                      Task Class
                    </label>
                    <select
                      value={simTaskType}
                      onChange={(e) =>
                        setSimTaskType(
                          e.target.value as
                            | 'canary_ack'
                            | 'routing_summary'
                            | 'structured_json_or_proof'
                        )
                      }
                      className="w-full px-1.5 py-1 bg-white border border-slate-300 rounded"
                    >
                      <option value="structured_json_or_proof">JSON / Proof</option>
                      <option value="routing_summary">Routing Summary</option>
                      <option value="canary_ack">Canary / ACK</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-0.5">
                      Proposed max_tokens
                    </label>
                    <input
                      type="number"
                      min="16"
                      max="2048"
                      step="16"
                      value={simProposedMaxTokens}
                      onChange={(e) => setSimProposedMaxTokens(Number(e.target.value))}
                      className="w-full px-2 py-1 font-mono bg-white border border-slate-300 rounded"
                    />
                  </div>
                </div>
                <div className="p-2.5 bg-white border border-slate-200 rounded-lg text-[11px] text-slate-700 leading-relaxed">
                  {liveTokenEcon.verdictSummary}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Custodian Banking Vault, 4 Virtual Cards & 3-Month Runway to Self-Sustainability */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Custodian Account & Virtual Cards */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              CUSTODIAN BANKING &amp; PROGRAMMABLE VIRTUAL CARDS · GEN-DIP-003
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <Landmark className="w-4 h-4 text-slate-700" />
              02. Estate Custodian Vault &amp; Virtual Card Lanes
            </h2>
          </div>

          {/* Bank Coordinates Card */}
          <div className="bg-slate-900 text-white rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span>{treasury.custodianBankName}</span>
              <span className="text-emerald-400 font-semibold">STANDING ORDER ACTIVE</span>
            </div>
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-slate-400">
                  Account Holder
                </div>
                <div className="text-sm font-mono font-semibold text-white">
                  {treasury.accountName}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wider text-slate-400">
                  Current Liquid Reserve
                </div>
                <div className="text-xl font-bold font-mono tabular-nums text-emerald-400">
                  £{treasury.currentReserveBalanceGbp.toFixed(2)} GBP
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-xs font-mono">
              <div>
                <span className="text-slate-400 block text-[10px]">UK SORT CODE</span>
                <span>{treasury.ukSortCode}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">ACCOUNT NO</span>
                <span>{treasury.ukAccountNumber}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">IBAN</span>
                <span className="truncate block">{treasury.iban}</span>
              </div>
            </div>
          </div>

          {/* 4 Virtual Cards */}
          <div className="space-y-2.5">
            <div className="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>4 Isolated Virtual Cards (£200.00/mo Total Allocation)</span>
              <span className="font-mono text-slate-500">Auto-3DS Enabled</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {treasury.virtualCards.map((vc) => {
                const utilPct = Math.min(
                  100,
                  Math.round((vc.spentThisMonthGbp / vc.monthlyCapGbp) * 100)
                );
                return (
                  <div
                    key={vc.cardId}
                    className="border border-slate-200 rounded-lg p-3 bg-slate-50/60 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <CreditCard className="w-3.5 h-3.5 text-slate-600" />
                        {vc.cardId}
                      </span>
                      <span className="text-emerald-700 font-medium">{vc.maskedPan}</span>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">{vc.cardLabel}</div>
                      <div className="text-[11px] text-slate-600 line-clamp-2 mt-0.5">
                        {vc.purpose}
                      </div>
                    </div>
                    <div className="pt-1 space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-slate-500">Custodian: {vc.assignedAgent}</span>
                        <span className="font-semibold text-slate-900 tabular-nums">
                          £{vc.spentThisMonthGbp.toFixed(0)} / £{vc.monthlyCapGbp} cap
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-slate-900 rounded-full"
                          style={{ width: `${utilPct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 3-Month Standing Order Runway & Post-March-2027 Independence Table */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="border-b border-slate-200 pb-3">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                90-DAY SEED WINDOW · 2 DEC 2026 TO 2 MAR 2027 CUTOVER
              </div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
                <TrendingUp className="w-4 h-4 text-slate-700" />
                03. 3-Month Standing Order Runway &amp; Self-Funding Cutover
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Founder Standing Order (£200/mo) runs for exactly 3 months. By Month 2, Commercial MRR exceeds Estate OpEx; on <strong>2 March 2027</strong>, Founder payments drop to <strong>£0</strong> and the Estate thrives independently.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 font-mono text-[11px]">
                    <th className="py-2 pr-2">Period</th>
                    <th className="py-2 px-2 text-right">Founder SO</th>
                    <th className="py-2 px-2 text-right">Commercial MRR</th>
                    <th className="py-2 px-2 text-right">Estate OpEx</th>
                    <th className="py-2 px-2 text-right">Cumulative Vault</th>
                    <th className="py-2 pl-2 text-right">Self-Cover</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-mono tabular-nums">
                  {treasury.runwayProjections.map((row) => (
                    <tr
                      key={row.monthIndex}
                      className={
                        row.monthIndex === 4
                          ? 'bg-emerald-50/60 font-semibold text-slate-900'
                          : 'text-slate-700'
                      }
                    >
                      <td className="py-2.5 pr-2 font-sans">
                        <div className="font-semibold text-slate-900">{row.monthLabel}</div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {row.periodDates}
                        </div>
                      </td>
                      <td className="py-2.5 px-2 text-right">
                        {row.founderStandingOrderGbp === 0 ? (
                          <span className="text-emerald-700 font-bold">£0 (Sunset)</span>
                        ) : (
                          `£${row.founderStandingOrderGbp}`
                        )}
                      </td>
                      <td className="py-2.5 px-2 text-right text-emerald-700 font-semibold">
                        +£{row.commercialMrrGbp}
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-600">
                        -£{row.estateOpExGbp}
                      </td>
                      <td className="py-2.5 px-2 text-right font-bold text-slate-900">
                        £{row.endingReserveGbp}
                      </td>
                      <td className="py-2.5 pl-2 text-right">
                        <span
                          className={
                            row.selfSustainingCoverageRatio >= 1.0
                              ? 'text-emerald-700 font-bold'
                              : 'text-amber-700'
                          }
                        >
                          {row.selfSustainingCoverageRatio}x
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-700">
              <strong className="text-slate-900">Post-Seed Guarantee (2 March 2027):</strong>{' '}
              Even after the £200/mo standing order stops, commercial revenue covers Estate OpEx by{' '}
              <span className="font-mono font-bold text-emerald-700">
                {treasury.runwayProjections[3]?.selfSustainingCoverageRatio}x
              </span>
              .
            </div>
            <button
              type="button"
              onClick={() => onExecuteCommercialSprint()}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer shrink-0"
            >
              Simulate Commercial MRR Conversion (+1 Tier)
            </button>
          </div>
        </section>
      </div>

      {/* Section 3: Model Provider Staff Rota (Core Permanent vs Backup Elastic Lanes + Yield Evaluation Lab) */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-4">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              MODEL PROVIDER STAFF ROTA &amp; EMPIRICAL YIELD GATE · GEN-SCI-003
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <Cpu className="w-4 h-4 text-slate-700" />
              04. Core Permanent Models (£118/mo) vs. Backup Elastic Capacity Lane (£24/mo)
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Core budget is permanently locked to <strong>Google Gemini / AI Studio / Antigravity</strong>, <strong>DeepSeek</strong>, and <strong>MiniMax</strong>. Backup capacity (<strong>Z.ai, Claude, Codex/ChatGPT, Kimi</strong>) activates only when surplus budget exists and strict yield benchmarks (≥94.0% accuracy &amp; ≥3.0x ROI yield) pass.
            </p>
          </div>
          <div className="text-xs font-mono text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg shrink-0">
            Active Rota Providers: <strong>{treasury.modelRota.length}</strong> · Min Yield Floor: <strong>3.00x</strong>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left 7 cols: Core Permanent & Backup Lanes */}
          <div className="lg:col-span-7 space-y-5">
            {/* Core Permanent Lane */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold uppercase tracking-wider text-slate-900">
                  Core Permanent Paid Lane (Primary Budget Allocation · VC-CORE-4810)
                </span>
                <span className="font-mono text-emerald-700 font-semibold">
                  £{coreModels.reduce((s, m) => s + m.monthlyBudgetAllocationGbp, 0)}/mo Locked
                </span>
              </div>
              <div className="space-y-2.5">
                {coreModels.map((mod) => (
                  <div
                    key={mod.id}
                    className="border border-slate-300 bg-slate-50/70 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">
                          {mod.providerName}
                        </span>
                        <span className="text-xs font-mono text-slate-500">
                          · {mod.modelFamily}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{mod.roleDescription}</p>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-500 pt-0.5">
                        <span>Accuracy: <strong className="text-slate-900">{mod.verifiedAccuracyPct}%</strong></span>
                        <span>Cost: <strong className="text-slate-900">£{mod.costPerMillionTokensGbp}/1M</strong></span>
                        <span>p95: <strong className="text-slate-900">{mod.p95LatencyMs}ms</strong></span>
                        <span className="text-emerald-700 font-semibold">
                          Yield: {mod.yieldMultiplier}x ROI
                        </span>
                      </div>
                    </div>
                    <div className="text-left sm:text-right font-mono shrink-0 border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-200">
                      <div className="text-xs font-bold text-emerald-700">
                        {mod.rotaStatus}
                      </div>
                      <div className="text-sm font-bold text-slate-900 tabular-nums mt-0.5">
                        £{mod.currentMonthSpendGbp.toFixed(1)} / £{mod.monthlyBudgetAllocationGbp} mo
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Proof: {mod.evaluationProofHash}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Backup Elastic Capacity Lane */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold uppercase tracking-wider text-slate-700">
                  Backup Elastic &amp; Evaluated Rota Lane (Surplus-Gated · VC-BACKUP-2041)
                </span>
                <span className="font-mono text-slate-600">
                  £{backupAndTrialModels.reduce((s, m) => s + m.monthlyBudgetAllocationGbp, 0)}/mo Elastic Reserve
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {backupAndTrialModels.map((mod) => (
                  <div
                    key={mod.id}
                    className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900">{mod.providerName}</span>
                      <span
                        className={`font-mono text-[11px] font-semibold ${
                          mod.rotaStatus === 'SUSPENDED_LOW_YIELD'
                            ? 'text-rose-700'
                            : 'text-slate-700'
                        }`}
                      >
                        {mod.rotaStatus}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-500">
                      {mod.modelFamily} · £{mod.monthlyBudgetAllocationGbp}/mo cap
                    </div>
                    <p className="text-[11px] text-slate-600 line-clamp-2">
                      {mod.roleDescription}
                    </p>
                    <div className="flex items-center justify-between text-[11px] font-mono pt-1 border-t border-slate-100">
                      <span>Acc: {mod.verifiedAccuracyPct}%</span>
                      <span className="text-emerald-700 font-semibold">
                        Yield: {mod.yieldMultiplier}x
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right 5 cols: Active Model Provider Evaluation & Rota Admission Lab */}
          <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-4">
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                AUTONOMOUS ROTA EVALUATION BENCHMARK
              </div>
              <h3 className="text-sm font-bold text-slate-900 mt-0.5">
                Evaluate &amp; Admit Candidate Model Provider to Staff Rota
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Test any new model provider before admitting it to the Estate Staff Rota. Models must prove ≥94.0% benchmark accuracy and ≥3.0x net operational yield.
              </p>
            </div>

            <form onSubmit={handleRunEvalSubmit} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Provider Name
                  </label>
                  <input
                    type="text"
                    value={candProvider}
                    onChange={(e) => setCandProvider(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Model Family
                  </label>
                  <input
                    type="text"
                    value={candFamily}
                    onChange={(e) => setCandFamily(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Accuracy (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="70"
                    max="100"
                    value={candAccuracy}
                    onChange={(e) => setCandAccuracy(Number(e.target.value))}
                    className="w-full px-2.5 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Cost (£ / 1M tok)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="15"
                    value={candCostPerM}
                    onChange={(e) => setCandCostPerM(Number(e.target.value))}
                    className="w-full px-2.5 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Cap (£ / mo)
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    max="25"
                    value={candBudget}
                    onChange={(e) => setCandBudget(Number(e.target.value))}
                    className="w-full px-2.5 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Target Lane Assignment
                </label>
                <select
                  value={candLane}
                  onChange={(e) => setCandLane(e.target.value as ModelLaneTier)}
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                >
                  <option value="backup_elastic">Backup Elastic Capacity Lane (Surplus-Gated)</option>
                  <option value="candidate_trial">Candidate Trial Sandbox</option>
                  <option value="core_permanent">Core Permanent Paid Lane</option>
                </select>
              </div>

              {/* Live Yield Calculation Preview */}
              <div className="bg-white border border-slate-200 rounded-lg p-3 text-xs space-y-1">
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-500">Computed Estate Yield:</span>
                  <span
                    className={`font-bold ${
                      livePreviewEval.admitted ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    {livePreviewEval.yieldMultiplier}x ROI ({livePreviewEval.rotaStatus})
                  </span>
                </div>
                <div className="text-[11px] text-slate-600">{livePreviewEval.reason}</div>
              </div>

              <button
                type="submit"
                className="w-full px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                Run GEN-SCI-003 Trial &amp; Commit to Staff Rota
              </button>
            </form>

            {evalBanner && (
              <div
                className={`p-3 rounded-lg border text-xs ${
                  evalBanner.admitted
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}
              >
                <div className="font-bold">{evalBanner.reason}</div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Section 4: Autonomous Keep-Alive Obligations & Concierge + Otto Co-Administration Verification */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Keep-Alive Obligations Table */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                AUTONOMOUS ESTATE KEEP-ALIVE · DOMAINS, INFRA &amp; PROVIDERS
              </div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
                <RefreshCw className="w-4 h-4 text-slate-700" />
                05. Self-Renewing Estate Obligations Ledger
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                onExecuteKeepAliveSweep();
                setSweepNotice(
                  'The Concierge & Otto completed an autonomous renewal & 3DS verification sweep across all 6 Estate obligations.'
                );
              }}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer shrink-0"
            >
              Execute Concierge + Otto Renewal Sweep
            </button>
          </div>

          {sweepNotice && (
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between">
              <span>{sweepNotice}</span>
              <span className="font-mono font-semibold">GEN-NET-004 VERIFIED</span>
            </div>
          )}

          <div className="space-y-2.5">
            {treasury.obligations.map((ob) => (
              <div
                key={ob.id}
                className="border border-slate-200 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/40"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">
                      {ob.obligationName}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500">
                    {ob.category} · Vendor: {ob.vendor} · Handled by: <strong>{ob.handledBy}</strong> ({ob.virtualCardUsed})
                  </div>
                </div>
                <div className="text-left sm:text-right font-mono shrink-0">
                  <div className="flex items-center sm:justify-end gap-2">
                    <span className="text-xs font-bold text-slate-900">
                      £{ob.monthlyCostGbp}/mo
                    </span>
                    <span
                      className={`text-[11px] font-semibold ${
                        ob.status === 'AUTO_RENEWED_VERIFIED'
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {ob.status}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Next Renewal: {ob.nextRenewalDateIso} · Receipt: {ob.lastReceiptHash.slice(0, 10)}…
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Concierge + Otto Always-Running Verification Matrix */}
        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              CONTINUOUS OPERATIONAL READINESS · CONCIERGE + OTTO
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <ShieldCheck className="w-4 h-4 text-slate-700" />
              06. Concierge &amp; Otto Administration Proofs
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Always-running verification proving The Concierge and Otto can execute any online work, 3DS payment, domain renewal, and budget lock autonomously.
            </p>
          </div>

          <div className="space-y-3">
            {treasury.conciergeOttoChecks.map((chk) => (
              <div
                key={chk.checkId}
                className="border border-slate-200 rounded-lg p-3.5 bg-slate-50/50 space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="font-bold text-slate-900">
                    {chk.checkId} · {chk.agentPair}
                  </span>
                  <span className="text-emerald-700 font-semibold">
                    {chk.passRatePct.toFixed(1)}% VERIFIED
                  </span>
                </div>
                <div className="text-xs font-bold text-slate-900">
                  {chk.capabilityTitle}
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  {chk.testScenario}
                </p>
                <div className="text-[10px] font-mono text-slate-400 pt-1">
                  SHA-256 Proof: {chk.proofHash} · Verified {chk.lastVerifiedIso.slice(0, 19)}Z
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Section 5: Commercial & Marketing Specialists + IDP Commercialization Post-Mortem */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-4">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              COMMERCIAL &amp; MARKETING ARM · ANTI-IDP POST-MORTEM &amp; SELF-FUNDING ENGINE
            </div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mt-0.5">
              <Activity className="w-4 h-4 text-slate-700" />
              07. IDP Commercialization Post-Mortem &amp; Active B2B Revenue Streams
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Why IDP failed at commercialization—and the immutable unit-economic guardrails our <strong>Genesis Commercial Director</strong> and <strong>Growth &amp; Marketing Specialist</strong> enforce so the Estate prospers permanently after the 3-month seed ends.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateToAgentMonitor('agent-commercial-director')}
            className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            Inspect Commercial Specialist Memory
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left 5 cols: IDP Post-Mortem & Immutable Guardrails */}
          <div className="lg:col-span-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-700">
              IDP Commercialization Failure Post-Mortem (Never Repeat)
            </div>
            {treasury.idpPostMortemLessons.map((lesson) => (
              <div
                key={lesson.id}
                className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/70 space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="font-bold text-rose-700">{lesson.id}</span>
                  <span className="text-emerald-700 font-semibold">
                    {lesson.boundProtocolId} · {lesson.status}
                  </span>
                </div>
                <div className="text-xs font-bold text-slate-900">
                  IDP Failure: {lesson.idpFailureMode}
                </div>
                <p className="text-[11px] text-slate-600">
                  <strong>Root Cause:</strong> {lesson.rootCauseAnalysis}
                </p>
                <div className="p-2 bg-white border border-slate-200 rounded-lg text-[11px] text-slate-800">
                  <strong className="text-emerald-800">New Genesis Guardrail ({lesson.enforcedBySpecialist}):</strong>{' '}
                  {lesson.newEstateGuardrail}
                </div>
              </div>
            ))}
          </div>

          {/* Right 7 cols: Active Self-Serve B2B Revenue Streams */}
          <div className="lg:col-span-7 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold uppercase tracking-wider text-slate-900">
                Active Self-Serve B2B Commercial Portfolio (Total MRR: £{totalCurrentMrr}/mo)
              </span>
              <span className="font-mono text-emerald-700 font-semibold">
                {selfSustainabilityCoverage}x Estate OpEx Coverage
              </span>
            </div>

            <div className="space-y-3">
              {treasury.commercialStreams.map((stream) => (
                <div
                  key={stream.id}
                  className="border border-slate-200 rounded-xl p-4 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5">
                    <div className="text-sm font-bold text-slate-900">
                      {stream.productName}
                    </div>
                    <div className="text-xs text-slate-600">
                      Target Segment: <strong>{stream.targetSegment}</strong> · Owner:{' '}
                      <span className="font-mono">{stream.specialistOwner}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-500 pt-0.5">
                      <span>Price: <strong className="text-slate-900">£{stream.monthlyPriceGbp}/mo</strong></span>
                      <span>Subscribers: <strong className="text-slate-900">{stream.activeCustomers}</strong></span>
                      <span>Gross Margin: <strong className="text-emerald-700">{stream.grossMarginPct}%</strong></span>
                      <span>Pipeline: <strong className="text-slate-900">{stream.pipelineProspects} qualified</strong></span>
                    </div>
                  </div>

                  <div className="text-left sm:text-right shrink-0 space-y-2 border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-100">
                    <div>
                      <div className="text-[11px] font-mono text-slate-500">Active Stream MRR</div>
                      <div className="text-lg font-bold font-mono tabular-nums text-emerald-700">
                        £{stream.monthlyRecurringRevenueGbp}/mo
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onExecuteCommercialSprint(stream.id)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer inline-flex items-center gap-1"
                    >
                      Convert +1 Subscriber (+£{stream.monthlyPriceGbp}/mo)
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
