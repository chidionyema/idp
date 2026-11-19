/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Zap,
  Lock,
  GitCommit,
  Terminal,
} from 'lucide-react';
import {
  MetricPayload,
  SurfaceType,
  GateVerificationOutcome,
  InvariantRule,
} from '../types/optimus';
import { evaluateGate, DEFAULT_INVARIANT_RULES } from '../utils/optimus-engine';

interface PushGateSimulatorProps {
  initialSurface?: SurfaceType;
  rules?: InvariantRule[];
  onAppendToLedger: (outcome: GateVerificationOutcome, payload: MetricPayload) => void;
}

interface PresetScenario {
  id: string;
  title: string;
  description: string;
  surface: SurfaceType;
  entityId: string;
  actor: string;
  bypassFlags: string[];
  metrics: Record<string, number | string | boolean>;
  expectedOutcome: 'RATIFIED' | 'BLOCKED';
}

const PRESET_SCENARIOS: PresetScenario[] = [
  {
    id: 'founder_unmetered',
    title: 'Founder Direct Edit (Missing Metrics)',
    description: 'A direct file edit pushed without running the AST metric profiler or OTel collector.',
    surface: 'git_commit_push',
    entityId: 'commit a78f102 (quick-founder-patch)',
    actor: 'founder@foundry.io',
    bypassFlags: [],
    metrics: {
      critical_cve_count: 0,
      metric_signature_valid: false,
      // Intentionally omitting coverage_percent and cyclomatic_complexity
    },
    expectedOutcome: 'BLOCKED',
  },
  {
    id: 'developer_no_verify',
    title: 'Developer Sneaky Bypass (--no-verify)',
    description: 'An engineer attempts to bypass pre-commit hooks using git push --no-verify.',
    surface: 'git_commit_push',
    entityId: 'commit 3f99a1c (emergency-fix)',
    actor: 'dev-alex@foundry.io',
    bypassFlags: ['--no-verify'],
    metrics: {
      coverage_percent: 78.4,
      cyclomatic_complexity_max: 18,
      critical_cve_count: 0,
      metric_signature_valid: false,
    },
    expectedOutcome: 'BLOCKED',
  },
  {
    id: 'compliant_release',
    title: 'Compliant Feature Commit (All Invariants Passed)',
    description: 'Standard production-ready PR with complete AST profiling, 95.2% coverage, 0 CVEs, and valid ECDSA signature.',
    surface: 'git_commit_push',
    entityId: 'commit 6e2098b (feat/audit-ledger-v2)',
    actor: 'elena.rostova@foundry.io',
    bypassFlags: [],
    metrics: {
      coverage_percent: 95.2,
      cyclomatic_complexity_max: 8,
      critical_cve_count: 0,
      metric_signature_valid: true,
      circumvention_flags_detected: 0,
    },
    expectedOutcome: 'RATIFIED',
  },
  {
    id: 'iac_unmetered_egress',
    title: 'Terraform IaC with Unmetered Egress',
    description: 'Cloud YAML adding 2 AWS egress routes with no registered OpenTelemetry exporter.',
    surface: 'infra_as_code',
    entityId: 'pr #402 (terraform/egress-nat.tf)',
    actor: 'cloud-infra@foundry.io',
    bypassFlags: [],
    metrics: {
      unmetered_endpoints_count: 2,
      critical_cve_count: 0,
      drift_index: 0.045,
      metric_signature_valid: false,
    },
    expectedOutcome: 'BLOCKED',
  },
  {
    id: 'agent_runaway_tokens',
    title: 'Autonomous AI Agent Token Loop',
    description: 'Autonomous reasoning agent entering an unbounded recursive tool-call storm.',
    surface: 'autonomous_agent',
    entityId: 'agent deep-research-bot (task-812)',
    actor: 'agent-scheduler',
    bypassFlags: [],
    metrics: {
      agent_token_velocity: 5200,
      drift_index: 0.05,
      metric_signature_valid: true,
    },
    expectedOutcome: 'BLOCKED',
  },
  {
    id: 'script_unmetered_bash',
    title: 'Unstamped DB Migration Shell Script',
    description: 'A developer executes an untracked raw shell script inside production devcontainer.',
    surface: 'runnable_script',
    entityId: 'script db-migrate-hotfix.sh',
    actor: 'backend-dev@foundry.io',
    bypassFlags: [],
    metrics: {
      memory_resident_mb: 320,
      cyclomatic_complexity_max: 16,
      metric_signature_valid: false,
    },
    expectedOutcome: 'BLOCKED',
  },
];

export const PushGateSimulator: React.FC<PushGateSimulatorProps> = ({
  initialSurface = 'git_commit_push',
  rules = DEFAULT_INVARIANT_RULES,
  onAppendToLedger,
}) => {
  const [selectedSurface, setSelectedSurface] = useState<SurfaceType>(initialSurface);
  const [entityId, setEntityId] = useState('commit 9a88c21 (feat/optimus-gate)');
  const [actor, setActor] = useState('founder@foundry.io');
  const [coverage, setCoverage] = useState(94.5);
  const [complexity, setComplexity] = useState(8);
  const [latency, setLatency] = useState(65);
  const [cves, setCves] = useState(0);
  const [memoryMb, setMemoryMb] = useState(140);
  const [unmeteredCount, setUnmeteredCount] = useState(0);
  const [tokenVelocity, setTokenVelocity] = useState(1200);
  const [driftIndex, setDriftIndex] = useState(0.005);
  const [hasNoVerifyFlag, setHasNoVerifyFlag] = useState(false);
  const [hasSkipMetricsFlag, setHasSkipMetricsFlag] = useState(false);
  const [signatureValid, setSignatureValid] = useState(true);

  const [outcome, setOutcome] = useState<GateVerificationOutcome | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);
  const [appendedSuccess, setAppendedSuccess] = useState(false);

  const handleApplyPreset = (preset: PresetScenario) => {
    setSelectedSurface(preset.surface);
    setEntityId(preset.entityId);
    setActor(preset.actor);
    setHasNoVerifyFlag(preset.bypassFlags.includes('--no-verify'));
    setHasSkipMetricsFlag(preset.bypassFlags.includes('--skip-metrics'));

    setCoverage(preset.metrics.coverage_percent !== undefined ? Number(preset.metrics.coverage_percent) : 0);
    setComplexity(preset.metrics.cyclomatic_complexity_max !== undefined ? Number(preset.metrics.cyclomatic_complexity_max) : 10);
    setLatency(preset.metrics.p99_latency_ms !== undefined ? Number(preset.metrics.p99_latency_ms) : 50);
    setCves(preset.metrics.critical_cve_count !== undefined ? Number(preset.metrics.critical_cve_count) : 0);
    setMemoryMb(preset.metrics.memory_resident_mb !== undefined ? Number(preset.metrics.memory_resident_mb) : 128);
    setUnmeteredCount(preset.metrics.unmetered_endpoints_count !== undefined ? Number(preset.metrics.unmetered_endpoints_count) : 0);
    setTokenVelocity(preset.metrics.agent_token_velocity !== undefined ? Number(preset.metrics.agent_token_velocity) : 1200);
    setDriftIndex(preset.metrics.drift_index !== undefined ? Number(preset.metrics.drift_index) : 0.01);
    setSignatureValid(preset.metrics.metric_signature_valid !== undefined ? Boolean(preset.metrics.metric_signature_valid) : true);

    // Auto-run evaluation for instant feedback
    const bypassFlagsDetected: string[] = [];
    if (preset.bypassFlags.includes('--no-verify')) bypassFlagsDetected.push('--no-verify');
    if (preset.bypassFlags.includes('--skip-metrics')) bypassFlagsDetected.push('--skip-metrics');

    const payload: MetricPayload = {
      surface: preset.surface,
      entityId: preset.entityId,
      actor: preset.actor,
      bypassFlagsDetected,
      metrics: {
        ...preset.metrics,
      },
    };

    const res = evaluateGate(payload, rules);
    setOutcome(res);
    setAppendedSuccess(false);
  };

  const handleExecuteEvaluation = () => {
    const bypassFlagsDetected: string[] = [];
    if (hasNoVerifyFlag) bypassFlagsDetected.push('--no-verify');
    if (hasSkipMetricsFlag) bypassFlagsDetected.push('--skip-metrics');

    const metrics: Record<string, number | string | boolean> = {
      metric_signature_valid: signatureValid,
      critical_cve_count: cves,
    };

    if (selectedSurface === 'git_commit_push' || selectedSurface === 'ci_cd_pipeline') {
      metrics.coverage_percent = coverage;
      metrics.cyclomatic_complexity_max = complexity;
      metrics.slsa_provenance_level = 3;
    }

    if (selectedSurface === 'microservice_engine' || selectedSurface === 'network_ingress_egress') {
      metrics.p99_latency_ms = latency;
      metrics.error_budget_burn_rate = 0.01;
      metrics.unmetered_endpoints_count = unmeteredCount;
      metrics.memory_resident_mb = memoryMb;
    }

    if (selectedSurface === 'infra_as_code') {
      metrics.unmetered_endpoints_count = unmeteredCount;
      metrics.drift_index = driftIndex;
    }

    if (selectedSurface === 'autonomous_agent') {
      metrics.agent_token_velocity = tokenVelocity;
      metrics.drift_index = driftIndex;
    }

    if (selectedSurface === 'scheduled_job' || selectedSurface === 'runnable_script') {
      metrics.memory_resident_mb = memoryMb;
      metrics.cyclomatic_complexity_max = complexity;
    }

    const payload: MetricPayload = {
      surface: selectedSurface,
      entityId,
      actor,
      bypassFlagsDetected,
      metrics,
    };

    const res = evaluateGate(payload, rules);
    setOutcome(res);
    setAppendedSuccess(false);
  };

  const handleCopyToken = () => {
    if (outcome?.signedPushToken) {
      navigator.clipboard.writeText(outcome.signedPushToken);
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    }
  };

  const handleAppend = () => {
    if (outcome) {
      const payload: MetricPayload = {
        surface: selectedSurface,
        entityId,
        actor,
        bypassFlagsDetected: outcome.isCircumventionAttempt ? ['--no-verify'] : [],
        metrics: {
          coverage_percent: coverage,
          cyclomatic_complexity_max: complexity,
          p99_latency_ms: latency,
          critical_cve_count: cves,
          metric_signature_valid: signatureValid,
          unmetered_endpoints_count: unmeteredCount,
          agent_token_velocity: tokenVelocity,
        },
      };
      onAppendToLedger(outcome, payload);
      setAppendedSuccess(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div>
        <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
          <Terminal className="w-5 h-5 text-indigo-400" />
          <span>Push Gate Interceptor & Invariant Simulator</span>
        </h2>
        <p className="text-xs text-slate-400">
          Simulate any push, commit, agent execution, or infra plan against Project Optimus hard mathematical gates.
        </p>
      </div>

      {/* Preset Scenarios Strip */}
      <div className="space-y-2">
        <div className="text-xs font-mono text-slate-400">REAL-WORLD TESTING SCENARIOS (CLICK TO TEST)</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {PRESET_SCENARIOS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handleApplyPreset(preset)}
              className="p-3 text-left rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 transition-all space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white leading-tight">{preset.title}</span>
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    preset.expectedOutcome === 'RATIFIED'
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                      : 'bg-red-950/80 text-red-400 border border-red-800/60'
                  }`}
                >
                  {preset.expectedOutcome}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">{preset.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Two Column Layout: Controls on Left, Invariant Proof & Cryptographic Gate on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Input Form (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Push Configuration</span>
            <span className="text-xs font-mono text-indigo-400">Target: {selectedSurface}</span>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Estate Surface Layer</label>
              <select
                value={selectedSurface}
                onChange={(e) => setSelectedSurface(e.target.value as SurfaceType)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
              >
                <option value="git_commit_push">Git Commits & Ref Pushes</option>
                <option value="ci_cd_pipeline">CI/CD Pipelines & Runners</option>
                <option value="microservice_engine">Microservices & Core Engines</option>
                <option value="infra_as_code">Infra as Code & Cloud YAML</option>
                <option value="scheduled_job">Scheduled Jobs & Workers</option>
                <option value="autonomous_agent">Autonomous AI Agents</option>
                <option value="network_ingress_egress">Network, HTTPS & Mesh Egress</option>
                <option value="runnable_script">Ad-Hoc Scripts & CLI Tools</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Entity ID / Ref</label>
                <input
                  type="text"
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Committer / Actor</label>
                <input
                  type="text"
                  value={actor}
                  onChange={(e) => setActor(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Metric Inputs */}
            <div className="pt-2 border-t border-slate-800/80 space-y-2.5">
              <span className="text-[11px] font-mono text-slate-400 block uppercase">Telemetry Metrics to Submit</span>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Coverage (%)</span>
                    <span className="font-mono text-indigo-400">{coverage}%</span>
                  </div>
                  <input
                    type="range"
                    min="40"
                    max="100"
                    step="0.5"
                    value={coverage}
                    onChange={(e) => setCoverage(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Cyclomatic Complexity</span>
                    <span className="font-mono text-indigo-400">{complexity}</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="30"
                    value={complexity}
                    onChange={(e) => setComplexity(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>P99 Latency (ms)</span>
                    <span className="font-mono text-indigo-400">{latency}ms</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="400"
                    value={latency}
                    onChange={(e) => setLatency(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Critical CVEs</span>
                    <span className="font-mono text-indigo-400">{cves}</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={cves}
                    onChange={(e) => setCves(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Unmetered Routes</span>
                    <span className="font-mono text-indigo-400">{unmeteredCount}</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    max="5"
                    value={unmeteredCount}
                    onChange={(e) => setUnmeteredCount(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white font-mono"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Agent Token Velocity</span>
                    <span className="font-mono text-indigo-400">{tokenVelocity} t/s</span>
                  </div>
                  <input
                    type="range"
                    min="500"
                    max="6000"
                    step="100"
                    value={tokenVelocity}
                    onChange={(e) => setTokenVelocity(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Circumvention Flags (Testing Anti-Bypass) */}
            <div className="pt-2 border-t border-slate-800/80 space-y-2">
              <span className="text-[11px] font-mono text-slate-400 block uppercase">Circumvention Flags (Testing Bypasses)</span>
              <div className="space-y-1.5">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasNoVerifyFlag}
                    onChange={(e) => setHasNoVerifyFlag(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-red-500 focus:ring-0"
                  />
                  <span>Inject <code className="font-mono text-red-400">--no-verify</code> into git push args</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasSkipMetricsFlag}
                    onChange={(e) => setHasSkipMetricsFlag(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-red-500 focus:ring-0"
                  />
                  <span>Inject <code className="font-mono text-red-400">--skip-metrics</code> in CI job args</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={signatureValid}
                    onChange={(e) => setSignatureValid(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-indigo-500 focus:ring-0"
                  />
                  <span>Cryptographic Key Signature Valid</span>
                </label>
              </div>
            </div>

            <button
              onClick={handleExecuteEvaluation}
              className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm shadow-indigo-900/40"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Evaluate Gate Invariants</span>
            </button>
          </div>
        </div>

        {/* Right Column: Gate Verdict & Invariant Proof (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Mathematical Gate Verdict
            </span>
            {outcome && (
              <span
                className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded flex items-center gap-1.5 ${
                  outcome.allowed
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                    : 'bg-red-950/80 text-red-400 border border-red-800'
                }`}
              >
                {outcome.allowed ? <ShieldCheck className="w-3.5 h-3.5" /> : <ShieldAlert className="w-3.5 h-3.5" />}
                <span>{outcome.status}</span>
              </span>
            )}
          </div>

          {!outcome ? (
            <div className="py-16 text-center text-slate-500 space-y-2">
              <Lock className="w-8 h-8 mx-auto text-slate-600" />
              <div className="text-xs">No evaluation in progress</div>
              <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                Select a preset scenario above or click &ldquo;Evaluate Gate Invariants&rdquo; to test Project Optimus zero-circumvention engine.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Verdict Announcement */}
              <div
                className={`p-4 rounded-lg border ${
                  outcome.allowed
                    ? 'bg-emerald-950/30 border-emerald-900/60 text-emerald-200'
                    : 'bg-red-950/30 border-red-900/60 text-red-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  {outcome.allowed ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1">
                    <div className="text-sm font-bold text-white">
                      {outcome.allowed
                        ? 'PUSH RATIFIED: Cryptographic Token Issued'
                        : 'PUSH INTERCEPTED & BLOCKED: Invariants Violated'}
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed">
                      {outcome.allowed
                        ? 'All mathematical constraints satisfied. The server-side git update-ref hook accepted the push ticket.'
                        : 'Server-side ref gate rejected ref update. Zero circumvention tolerance enforced. Code cannot enter repo.'}
                    </div>
                  </div>
                </div>

                {outcome.rejectionReasons.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-red-900/40 space-y-1">
                    <div className="text-[11px] font-mono text-red-400 uppercase font-bold">
                      Rejection Causes ({outcome.rejectionReasons.length}):
                    </div>
                    <ul className="text-xs text-red-300 space-y-1 list-disc list-inside">
                      {outcome.rejectionReasons.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Cryptographic Artifacts (if allowed) */}
              {outcome.allowed && (
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 space-y-2 font-mono text-xs">
                  <div className="flex items-center justify-between text-slate-400 text-[11px]">
                    <span>SIGNED PUSH TICKET</span>
                    <button
                      onClick={handleCopyToken}
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                    >
                      {copiedToken ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedToken ? 'Copied' : 'Copy Token'}</span>
                    </button>
                  </div>
                  <div className="p-2 bg-slate-900 rounded text-emerald-400 text-[11px] break-all border border-slate-800">
                    {outcome.signedPushToken}
                  </div>
                  <div className="text-[10px] text-slate-500 break-all">
                    Signature: {outcome.cryptographicSignature}
                  </div>
                </div>
              )}

              {/* Invariant Rules Checklist */}
              <div className="space-y-2">
                <div className="text-xs font-mono text-slate-400 uppercase flex items-center justify-between">
                  <span>Evaluated Mathematical Invariants</span>
                  <span>{outcome.evaluationResults.filter((r) => r.passed).length}/{outcome.evaluationResults.length} Passed</span>
                </div>

                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                  {outcome.evaluationResults.map((evalItem) => (
                    <div
                      key={evalItem.ruleId}
                      className="flex items-center justify-between p-2.5 rounded bg-slate-950 border border-slate-800/80 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        {evalItem.passed ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                        )}
                        <span className="font-medium text-slate-200">{evalItem.ruleName}</span>
                      </div>

                      <div className="flex items-center gap-3 font-mono text-[11px]">
                        <span className="text-slate-400">Actual: {String(evalItem.actualValue)}</span>
                        <span aria-hidden="true" className="text-slate-600">·</span>
                        <span className={evalItem.passed ? 'text-emerald-400' : 'text-red-400 font-bold'}>
                          {evalItem.deviation}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Append to Ledger Action */}
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <div className="text-xs text-slate-400 font-mono">
                  Merkle Leaf: <span className="text-slate-300">{outcome.merkleLeaf.substring(0, 16)}...</span>
                </div>
                <button
                  onClick={handleAppend}
                  disabled={appendedSuccess}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors flex items-center gap-1.5"
                >
                  <GitCommit className="w-3 h-3 text-indigo-400" />
                  <span>{appendedSuccess ? 'Recorded in Ledger' : 'Append to Merkle Ledger'}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
