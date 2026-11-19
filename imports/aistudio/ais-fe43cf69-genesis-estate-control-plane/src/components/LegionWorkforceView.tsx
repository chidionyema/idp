import React, { useState, useEffect } from 'react';
import {
  Play,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Terminal,
  Sliders,
} from 'lucide-react';
import { LEGION_FORMATIONS, type FormationId } from '../engine/estateRules';
import type { LegionExecutionRun } from '../types/estate';

interface LegionWorkforceViewProps {
  executions: LegionExecutionRun[];
  prefilledMission: {
    instructionId?: string;
    title?: string;
    objective: string;
    repo: string;
  } | null;
  onExecuteFormation: (payload: {
    formationId: FormationId;
    repo: string;
    instructionId?: string;
    title?: string;
    objective: string;
    helmShots: number;
  }) => Promise<LegionExecutionRun | null>;
}

const PRESET_ESTATE_MISSIONS = [
  {
    label: 'IDP #7777: Greenlane missing-ref crash',
    instructionId: 'INS-07777',
    repo: 'chidionyema/idp',
    formation: 'sniper' as FormationId,
    objective:
      'Fix Greenlane engine.py crash when remote lane/<slug> branch ref is deleted mid-flight; add deterministic missing-ref negative regression test.',
  },
  {
    label: 'IDP #2468: OCI Vault agent-foundry-hf audit',
    instructionId: 'INS-02468',
    repo: 'chidionyema/idp',
    formation: 'adversarial' as FormationId,
    objective:
      'Audit platform/compiled/agent-foundry-hf/external-secret.yaml missing OCI Vault key without muting vault incident monitor; produce safe Flux reconciliation patch.',
  },
  {
    label: 'IDP #7981: [GENESIS-OUTBOX] v1 intake hardening',
    instructionId: 'INS-07981',
    repo: 'chidionyema/idp',
    formation: 'phalanx' as FormationId,
    objective:
      'Harden bin/genesis-inbound-bridge.py JSON v1 dispatch intake with fail-closed public:true check, SHA-256 idempotency ledger, and fenced FLOW worker handoff.',
  },
  {
    label: 'Meridian #7971: Mailjet fail-closed enquiry',
    instructionId: 'INS-07971',
    repo: 'chidionyema/idp',
    formation: 'tournament' as FormationId,
    objective:
      'Design fail-closed Mailjet enquiry delivery handler for Meridian Intelligence commercial site with explicit HTTP 503 diagnostic and WCAG validation.',
  },
];

export const LegionWorkforceView: React.FC<LegionWorkforceViewProps> = ({
  executions,
  prefilledMission,
  onExecuteFormation,
}) => {
  const [selectedFormation, setSelectedFormation] = useState<FormationId>('sniper');
  const [repo, setRepo] = useState('chidionyema/idp');
  const [instructionId, setInstructionId] = useState('INS-07777');
  const [objective, setObjective] = useState(PRESET_ESTATE_MISSIONS[0].objective);
  const [helmShots, setHelmShots] = useState(2);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedExecId, setSelectedExecId] = useState<string | null>(executions[0]?.executionId ?? null);

  useEffect(() => {
    if (prefilledMission) {
      setObjective(prefilledMission.objective);
      setRepo(prefilledMission.repo);
      if (prefilledMission.instructionId) {
        setInstructionId(prefilledMission.instructionId);
      }
    }
  }, [prefilledMission]);

  useEffect(() => {
    const spec = LEGION_FORMATIONS.find((f) => f.id === selectedFormation);
    if (spec) {
      setHelmShots(spec.defaultHelmShots);
    }
  }, [selectedFormation]);

  const currentSpec = LEGION_FORMATIONS.find((f) => f.id === selectedFormation) ?? LEGION_FORMATIONS[0];
  const activeRun =
    executions.find((e) => e.executionId === selectedExecId) ?? executions[0] ?? null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    if (objective.trim().length < 8) {
      setErrorMsg('Enter a concrete engineering objective (at least 8 characters) before dispatching Legion.');
      return;
    }
    setIsRunning(true);
    try {
      const run = await onExecuteFormation({
        formationId: selectedFormation,
        repo,
        instructionId: instructionId.trim() || undefined,
        objective: objective.trim(),
        helmShots,
      });
      if (run) {
        setSelectedExecId(run.executionId);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Cloud execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="pb-5 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 text-balance">
          Legion Cloud Workforce & Geburah Epistemic Firewall
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Model-agnostic cloud formations governed by HELM bounded-shot regimes, 7-Gate Cognitive Architecture, and an independent adversarial falsifier.
        </p>
      </div>

      {/* 8 Canonical Legion Formations Selector */}
      <section aria-labelledby="formations-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 id="formations-heading" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            01. Select Legion Tactical Formation (8 Canonical Topologies)
          </h2>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
            Active: {currentSpec.name} · Posture: {currentSpec.posture} · Max DoF: {currentSpec.maxDegreesOfFreedom}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {LEGION_FORMATIONS.map((f) => {
            const active = f.id === selectedFormation;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setSelectedFormation(f.id)}
                aria-pressed={active}
                className={`text-left p-4 rounded-xl border transition-colors ${
                  active
                    ? 'bg-amber-50/70 dark:bg-amber-500/10 border-amber-500 dark:border-amber-400'
                    : 'bg-white dark:bg-[#0B101D] border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {f.name}
                  </span>
                  <span className="text-xs font-mono tabular-nums text-cyan-700 dark:text-cyan-400">
                    {f.workerCount}w · {f.defaultHelmShots}s
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {f.posture} · DoF {f.maxDegreesOfFreedom}
                </div>
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed">
                  {f.topologySummary}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {/* Formation Dispatch Form + Execution Receipt Viewer */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <form
          onSubmit={handleSubmit}
          className="xl:col-span-5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
        >
          <div className="flex items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              02. Dispatch Cloud Formation + Falsifier
            </h2>
            <Sliders className="w-4 h-4 text-slate-400" aria-hidden="true" />
          </div>

          {/* Preset Missions */}
          <div>
            <span className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
              Load Real Estate Backlog Mission:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_ESTATE_MISSIONS.map((m) => (
                <button
                  key={m.instructionId}
                  type="button"
                  onClick={() => {
                    setInstructionId(m.instructionId);
                    setRepo(m.repo);
                    setSelectedFormation(m.formation);
                    setObjective(m.objective);
                    setErrorMsg(null);
                  }}
                  className="px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="legion-repo" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Target Repository
              </label>
              <select
                id="legion-repo"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                <option value="chidionyema/idp">chidionyema/idp (public)</option>
                <option value="chidionyema/hermes-v2">chidionyema/hermes-v2 (public)</option>
                <option value="chidionyema/estate-guards">chidionyema/estate-guards (public)</option>
                <option value="chidionyema/argon">chidionyema/argon (private)</option>
                <option value="chidionyema/estate-graph">chidionyema/estate-graph (private)</option>
              </select>
            </div>

            <div>
              <label htmlFor="legion-inst-id" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                FLOW Instruction ID
              </label>
              <input
                id="legion-inst-id"
                type="text"
                value={instructionId}
                onChange={(e) => setInstructionId(e.target.value)}
                placeholder="INS-07981"
                className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="helm-shots" className="text-xs font-medium text-slate-700 dark:text-slate-300">
                HELM Behavioural Helmet Shot Budget (1–10 shots)
              </label>
              <span className="text-xs font-mono tabular-nums text-amber-600 dark:text-amber-400 font-semibold">
                {helmShots} shot{helmShots === 1 ? '' : 's'}
              </span>
            </div>
            <input
              id="helm-shots"
              type="range"
              min={1}
              max={10}
              value={helmShots}
              onChange={(e) => setHelmShots(Number(e.target.value))}
              className="w-full accent-amber-500"
            />
            <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono">
              <span>1-Shot Surgical</span>
              <span>Bounded Trial (4)</span>
              <span>10-Shot Exploratory</span>
            </div>
          </div>

          <div>
            <label htmlFor="legion-objective" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Engineering Objective & Acceptance Contract
            </label>
            <textarea
              id="legion-objective"
              rows={4}
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 leading-relaxed"
              placeholder="Specify exact defect, target file/workflow, and falsifying negative test..."
            />
          </div>

          {errorMsg && (
            <div role="alert" className="p-3 text-xs text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg">
              {errorMsg}
            </div>
          )}

          <div className="pt-1 flex items-center justify-between gap-3">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Falsifier: <span className="font-medium text-slate-700 dark:text-slate-300">{currentSpec.falsifierMechanism}</span>
            </div>
            <button
              type="submit"
              disabled={isRunning}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Play className="w-3.5 h-3.5" aria-hidden="true" />
              {isRunning ? 'Executing Worker + Falsifier...' : `Dispatch ${currentSpec.name}`}
            </button>
          </div>
        </form>

        {/* Live Cloud Execution Artifact & Geburah Falsifier Receipt */}
        <section
          aria-labelledby="execution-receipt-heading"
          className="xl:col-span-7 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="execution-receipt-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
                03. Verified Cloud Execution & Claim-Gate Receipt
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Real server-side model execution + independent Geburah falsifier + deterministic Claim-Gate audit.
              </p>
            </div>

            {executions.length > 1 && (
              <select
                aria-label="Select historical execution receipt"
                value={activeRun?.executionId ?? ''}
                onChange={(e) => setSelectedExecId(e.target.value)}
                className="px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                {executions.map((ex) => (
                  <option key={ex.executionId} value={ex.executionId}>
                    {ex.executionId} · {ex.formationName} · {ex.claimGateVerdict}
                  </option>
                ))}
              </select>
            )}
          </div>

          {!activeRun ? (
            <div className="p-8 text-center space-y-2">
              <Terminal className="w-7 h-7 text-slate-400 mx-auto" aria-hidden="true" />
              <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                No Cloud Formation Dispatched in This Session Yet
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
                Select one of the 8 Legion formations on the left and click Dispatch to run a real cloud worker + independent Geburah falsifier with full token, latency, SHA-256 digest, and 7-Gate provenance.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              {/* Telemetry Metadata Bar */}
              <div className="px-5 py-3.5 bg-slate-50/70 dark:bg-slate-950/50 flex flex-wrap items-center justify-between gap-3 text-xs font-mono tabular-nums">
                <div className="flex flex-wrap items-center gap-2">
                  {activeRun.claimGateVerdict === 'PASS' ? (
                    <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      CLAIM_GATE: PASS ({activeRun.epistemicScore}/100)
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-red-700 dark:text-red-400 font-semibold">
                      <XCircle className="w-3.5 h-3.5" />
                      {activeRun.claimGateVerdict} ({activeRun.epistemicScore}/100)
                    </span>
                  )}
                  <span aria-hidden="true" className="text-slate-400">·</span>
                  <span className="text-slate-800 dark:text-slate-200">{activeRun.executionId}</span>
                  <span aria-hidden="true" className="text-slate-400">·</span>
                  <span className="text-slate-600 dark:text-slate-400">{activeRun.modelId}</span>
                  <span aria-hidden="true" className="text-slate-400">·</span>
                  <span className="text-slate-600 dark:text-slate-400">HELM {activeRun.helmShots}s</span>
                </div>
                <div className="text-slate-600 dark:text-slate-400">
                  {activeRun.latencyMs}ms · {activeRun.inputTokens + activeRun.outputTokens} tok · ${activeRun.costUsd.toFixed(5)} · SHA {activeRun.artifactSha256.slice(0, 10)}
                </div>
              </div>

              {/* Worker Summary & Greenlane Branch */}
              <div className="p-5 space-y-3">
                <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  Instruction {activeRun.instructionId} · Worker {activeRun.workerId} (Epoch {activeRun.leaseEpoch}) · Branch {activeRun.laneBranch}
                </div>
                <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                  {activeRun.summary}
                </p>

                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1.5">
                    Generated Patch / Executable Artifact
                  </div>
                  <pre className="p-3.5 text-xs font-mono bg-slate-950 text-slate-100 rounded-lg overflow-x-auto max-h-64 leading-relaxed">
                    {activeRun.patchArtifact}
                  </pre>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  <div>
                    <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1">
                      Governed Greenlane Commands
                    </div>
                    <ul className="space-y-1 text-xs font-mono text-slate-700 dark:text-slate-300">
                      {activeRun.proposedCommands.map((c, idx) => (
                        <li key={idx} className="break-all">
                          $ {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1">
                      Falsifying Negative Test Assertions
                    </div>
                    <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
                      {activeRun.testAssertions.map((t, idx) => (
                        <li key={idx}>• {t}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Geburah Independent Falsifier Critique */}
              <div className="p-5 bg-slate-50/50 dark:bg-slate-950/30 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900 dark:text-slate-100">
                  <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400" aria-hidden="true" />
                  Geburah Independent Falsifier Audit
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  {activeRun.geburahFalsifierNotes}
                </p>
                {activeRun.geburahCounterexamples.length > 0 && (
                  <div className="pt-1 text-xs text-slate-600 dark:text-slate-400 space-y-1">
                    {activeRun.geburahCounterexamples.map((cx, i) => (
                      <div key={i}>Counterexample {i + 1}: {cx}</div>
                    ))}
                  </div>
                )}
                {activeRun.violations.length > 0 && (
                  <div className="pt-2 space-y-1">
                    {activeRun.violations.map((v, idx) => (
                      <div key={idx} className="text-xs text-red-700 dark:text-red-400 font-medium">
                        [{v.code}] {v.message}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
