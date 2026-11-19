/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import {
  evaluateProposal,
  deconstructVagueInstruction,
  CANONICAL_EXEMPLARS,
  ProposalEvaluationRequest,
} from '../lib/protocolEngine.ts';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  Sparkles,
  Layers,
  Activity,
  FileCheck,
} from 'lucide-react';

export const CompoundingEngineeringSurface: React.FC = () => {
  // Evaluator state
  const [proposal, setProposal] = useState<ProposalEvaluationRequest>({
    title: 'Zod network-boundary schema gate at WebSocket ingress',
    targetScope: 'API Socket Ingestion Boundary',
    founderFrictionDelta: 0,
    rootCauseCoverage: 1.0,
    reusableAssetGenerated: true,
    automatedTestAdded: true,
    estimatedFutureHoursSaved: 48,
    hoursToImplement: 4,
  });

  // Active exemplar
  const [selectedExemplarId, setSelectedExemplarId] = useState<string>('EX-01');

  // Vague instruction state
  const [instructionText, setInstructionText] = useState<string>(
    'push to private inboc agon and argon sync'
  );

  const evaluationResult = useMemo(() => {
    return evaluateProposal(proposal);
  }, [proposal]);

  const deconstruction = useMemo(() => {
    return deconstructVagueInstruction(instructionText);
  }, [instructionText]);

  const activeExemplar = useMemo(() => {
    return CANONICAL_EXEMPLARS.find((e) => e.id === selectedExemplarId) || CANONICAL_EXEMPLARS[0];
  }, [selectedExemplarId]);

  return (
    <div className="space-y-8">
      {/* Doctrine Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Sparkles className="w-4 h-4" />
              <span>CORE LAW #7 · ASYMMETRY ENGINE & DETERMINISTIC GATE</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              The Compounding Engineering Doctrine
            </h1>
            <p className="text-slate-400 text-sm leading-relaxed">
              By enforcing this canon machine-wide, Genesis converts every error from an entropy tax into an engine of continuous, compounding leverage. Point fixes that patch symptoms or transfer manual operational friction to the Founder are mathematically rejected at the gate.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 text-xs font-mono space-y-1.5 shrink-0 min-w-[280px]">
            <div className="text-slate-400 uppercase tracking-wider text-[10px]">Mathematical Invariants</div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Asymmetry Ratio:</span>
              <span className="text-cyan-400 font-bold tabular-nums">R_asym ≥ 2.00x</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Founder Friction:</span>
              <span className="text-emerald-400 font-bold tabular-nums">Δ_founder ≡ 0</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Root Cause Coverage:</span>
              <span className="text-cyan-400 font-bold tabular-nums">C_root ≥ 0.80</span>
            </div>
            <div className="flex justify-between items-center text-slate-200">
              <span>Invariant Regression:</span>
              <span className="text-emerald-400 font-bold">AUTOMATED TEST</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Interactive Evaluator & Invariant Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Live Asymmetric Proposal Evaluator (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-semibold text-white">Deterministic Proposal Evaluator</h2>
              <p className="text-xs text-slate-400">Test any code change against Genesis Core Law #7 invariants</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  setProposal({
                    title: 'Ad-hoc inline fallback `val || ""` in user avatar',
                    targetScope: 'Single component inline patch',
                    founderFrictionDelta: 1,
                    rootCauseCoverage: 0.25,
                    reusableAssetGenerated: false,
                    automatedTestAdded: false,
                    estimatedFutureHoursSaved: 1,
                    hoursToImplement: 1,
                  })
                }
                className="px-2.5 py-1 text-xs font-medium text-rose-300 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-800/80 rounded transition-colors"
              >
                Load Point-Fix (Defect)
              </button>
              <button
                onClick={() =>
                  setProposal({
                    title: 'Zod network-boundary schema gate at WebSocket ingress',
                    targetScope: 'Global API Ingestion Boundary',
                    founderFrictionDelta: 0,
                    rootCauseCoverage: 1.0,
                    reusableAssetGenerated: true,
                    automatedTestAdded: true,
                    estimatedFutureHoursSaved: 54,
                    hoursToImplement: 4,
                  })
                }
                className="px-2.5 py-1 text-xs font-medium text-cyan-300 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800/80 rounded transition-colors"
              >
                Load Compounding Fix
              </button>
            </div>
          </div>

          {/* Form inputs */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Proposal Title</label>
              <input
                type="text"
                value={proposal.title}
                onChange={(e) => setProposal({ ...proposal, title: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Architectural Scope</label>
                <input
                  type="text"
                  value={proposal.targetScope}
                  onChange={(e) => setProposal({ ...proposal, targetScope: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-300">Founder Friction Delta (Δ_founder)</span>
                  <span className={`font-mono font-bold ${proposal.founderFrictionDelta > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    +{proposal.founderFrictionDelta} (Requires 0)
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="1"
                  value={proposal.founderFrictionDelta}
                  onChange={(e) => setProposal({ ...proposal, founderFrictionDelta: Number(e.target.value) })}
                  className="w-full accent-cyan-400 bg-slate-950 rounded cursor-pointer"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-300">Root Cause Coverage (C_root)</span>
                  <span className="font-mono font-bold text-cyan-400 tabular-nums">
                    {(proposal.rootCauseCoverage * 100).toFixed(0)}% (Min 80%)
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={proposal.rootCauseCoverage}
                  onChange={(e) => setProposal({ ...proposal, rootCauseCoverage: Number(e.target.value) })}
                  className="w-full accent-cyan-400 bg-slate-950 rounded cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Hours Spent</label>
                  <input
                    type="number"
                    min="1"
                    value={proposal.hoursToImplement}
                    onChange={(e) => setProposal({ ...proposal, hoursToImplement: Math.max(1, Number(e.target.value)) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 tabular-nums font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Hours Saved</label>
                  <input
                    type="number"
                    min="0"
                    value={proposal.estimatedFutureHoursSaved}
                    onChange={(e) => setProposal({ ...proposal, estimatedFutureHoursSaved: Math.max(0, Number(e.target.value)) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 tabular-nums font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 select-none">
                <input
                  type="checkbox"
                  checked={proposal.reusableAssetGenerated}
                  onChange={(e) => setProposal({ ...proposal, reusableAssetGenerated: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-0"
                />
                <span>Generates Reusable Estate Asset (+35% leverage)</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 select-none">
                <input
                  type="checkbox"
                  checked={proposal.automatedTestAdded}
                  onChange={(e) => setProposal({ ...proposal, automatedTestAdded: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-0"
                />
                <span>Includes Automated Invariant Test (+25% leverage)</span>
              </label>
            </div>
          </div>

          {/* Gate Decision Display */}
          <div className={`p-4 rounded-xl border ${
            evaluationResult.isCompliant
              ? 'bg-emerald-950/30 border-emerald-800/80'
              : 'bg-rose-950/30 border-rose-800/80'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {evaluationResult.isCompliant ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                ) : (
                  <XCircle className="w-6 h-6 text-rose-400" />
                )}
                <div>
                  <div className="text-xs uppercase tracking-wider text-slate-400 font-mono">Autonomous Deterministic Gate</div>
                  <div className={`text-base font-bold ${
                    evaluationResult.isCompliant ? 'text-emerald-300' : 'text-rose-300'
                  }`}>
                    {evaluationResult.gateDecision}: {evaluationResult.isCompliant ? 'APPROVED FOR INTEGRATION' : 'BLOCKED BY CANON'}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs text-slate-400 font-mono">Calculated R_asym</div>
                <div className={`text-2xl font-bold font-mono tabular-nums ${
                  evaluationResult.asymmetryScore >= 2.0 ? 'text-cyan-400' : 'text-rose-400'
                }`}>
                  {evaluationResult.asymmetryScore.toFixed(2)}x
                </div>
              </div>
            </div>

            {/* Reasons / Violations */}
            {evaluationResult.reasons.length > 0 && (
              <div className="mt-3 pt-3 border-t border-rose-800/40 text-xs space-y-1">
                <div className="text-rose-300 font-medium">Violations Detected:</div>
                {evaluationResult.reasons.map((r, idx) => (
                  <div key={idx} className="text-rose-200 flex items-start gap-1.5">
                    <span className="text-rose-400">•</span>
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Recommendations */}
            {evaluationResult.recommendations.length > 0 && (
              <div className="mt-2 text-xs space-y-1 text-slate-300">
                <div className="text-cyan-300 font-medium">Prescribed Compounding Remedy:</div>
                {evaluationResult.recommendations.map((rec, idx) => (
                  <div key={idx} className="text-slate-300 flex items-start gap-1.5">
                    <span className="text-cyan-400">→</span>
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: 3 Canonical Exemplars (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-lg font-semibold text-white">3 Canonical Exemplars</h2>
              <p className="text-xs text-slate-400">Point-Fix vs Compounding Invariant</p>
            </div>
            <Layers className="w-5 h-5 text-cyan-400" />
          </div>

          {/* Selector pills */}
          <div className="grid grid-cols-3 gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {CANONICAL_EXEMPLARS.map((ex) => (
              <button
                key={ex.id}
                onClick={() => setSelectedExemplarId(ex.id)}
                className={`py-1.5 px-2 text-[11px] font-medium rounded transition-colors truncate ${
                  selectedExemplarId === ex.id
                    ? 'bg-slate-800 text-cyan-300 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {ex.id}: {ex.category.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Exemplar Card */}
          <div className="space-y-4">
            <div>
              <div className="text-xs text-cyan-400 font-mono font-medium">{activeExemplar.id} · {activeExemplar.category}</div>
              <h3 className="text-base font-bold text-white">{activeExemplar.title}</h3>
              <div className="mt-1.5 p-2 bg-slate-950 rounded border border-slate-800 text-xs font-mono text-slate-300">
                <span className="text-amber-400">Symptom: </span>
                {activeExemplar.symptom}
              </div>
            </div>

            {/* Point-fix (Rejected) */}
            <div className="p-3 bg-rose-950/20 border border-rose-900/50 rounded-lg space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-400 flex items-center gap-1">
                  <XCircle className="w-3.5 h-3.5" /> POINT-FIX (REJECTED)
                </span>
                <span className="text-xs font-mono text-rose-300 tabular-nums">
                  R_asym: {activeExemplar.pointFix.asymmetryScore.toFixed(1)}x
                </span>
              </div>
              <div className="text-xs font-medium text-slate-200">{activeExemplar.pointFix.name}</div>
              <p className="text-xs text-slate-400">{activeExemplar.pointFix.description}</p>
              <div className="text-[11px] text-rose-300/90 pt-1">
                <strong>Failure Vector: </strong> {activeExemplar.pointFix.failureReason}
              </div>
            </div>

            {/* Compounding Fix (Approved) */}
            <div className="p-3 bg-emerald-950/20 border border-emerald-900/50 rounded-lg space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> COMPOUNDING FIX (APPROVED)
                </span>
                <span className="text-xs font-mono text-emerald-300 font-bold tabular-nums">
                  R_asym: {activeExemplar.compoundingFix.asymmetryScore.toFixed(1)}x
                </span>
              </div>
              <div className="text-xs font-medium text-white">{activeExemplar.compoundingFix.name}</div>
              <p className="text-xs text-slate-300">{activeExemplar.compoundingFix.description}</p>
              <div className="pt-1 space-y-1">
                {activeExemplar.compoundingFix.mechanisms.map((m, idx) => (
                  <div key={idx} className="text-[11px] text-cyan-200 flex items-center gap-1.5">
                    <ArrowRight className="w-3 h-3 text-cyan-400 shrink-0" />
                    <span>{m}</span>
                  </div>
                ))}
              </div>
              <div className="pt-2 text-xs font-mono text-emerald-400 flex items-center justify-between border-t border-emerald-900/40">
                <span>Permanent Leverage Tally:</span>
                <span className="font-bold">+{activeExemplar.compoundingFix.futureDefectsEliminated} Defects Eliminated</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Vague-by-Default Law Ingestion Simulator */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
              VAGUE-BY-DEFAULT LAW (I_amb → 0)
            </div>
            <h2 className="text-xl font-bold text-white">
              Deterministic Instruction Ingestion Simulator
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              When an instruction arrives, agents are mathematically barred from guessing. The system deconstructs parameters into formal contracts.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">Ambiguity Index:</span>
            <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
              deconstruction.ambiguityScore > 0.4 ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
            }`}>
              I_amb = {deconstruction.ambiguityScore.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Input box */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-slate-300">
            Raw Natural Language Founder Instruction
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={instructionText}
              onChange={(e) => setInstructionText(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-cyan-200 font-mono focus:outline-none focus:border-cyan-500"
              placeholder="e.g. push to private inboc agon and argon sync"
            />
            <button
              onClick={() => setInstructionText('push to private inboc agon and argon sync')}
              className="px-3 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors whitespace-nowrap"
            >
              Reset to Session Prompt
            </button>
          </div>
        </div>

        {/* Deconstruction Output Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Box 1: Inferred Contract & Ambiguities */}
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="text-xs font-mono font-bold text-cyan-400 flex items-center gap-1.5">
              <FileCheck className="w-4 h-4" /> INFERRED CONTRACT & ECHO
            </div>
            <div className="text-xs text-slate-300">
              <span className="text-slate-500 block">Deconstructed Intent:</span>
              <span className="font-medium text-white">{deconstruction.inferredContract.intent}</span>
            </div>
            
            {deconstruction.flaggedAmbiguities.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80 space-y-1">
                <span className="text-[11px] font-mono text-amber-400 uppercase tracking-wide">Flagged Ambiguities Resolved:</span>
                {deconstruction.flaggedAmbiguities.map((a, idx) => (
                  <div key={idx} className="text-xs text-amber-200/90 flex items-start gap-1">
                    <span className="text-amber-400">•</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 border-t border-slate-800/80 text-xs font-mono space-y-1 text-slate-300">
              <div className="text-slate-500 text-[10px] uppercase">Formal Preconditions:</div>
              {deconstruction.inferredContract.preconditions.map((p, idx) => (
                <div key={idx} className="text-slate-300">• {p}</div>
              ))}
            </div>
          </div>

          {/* Box 2: Schema Extraction */}
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="text-xs font-mono font-bold text-teal-400 flex items-center gap-1.5">
              <Layers className="w-4 h-4" /> FORMAL PARAMETERS & INVARIANTS
            </div>

            <div>
              <div className="text-[10px] font-mono text-slate-500 uppercase">Extracted Input Schema:</div>
              <pre className="mt-1 p-2 bg-slate-900 rounded text-[11px] font-mono text-cyan-300 overflow-x-auto">
                {JSON.stringify(deconstruction.inferredContract.inputSchema, null, 2)}
              </pre>
            </div>

            <div className="pt-1">
              <div className="text-[10px] font-mono text-slate-500 uppercase">Non-Negotiable Invariants:</div>
              <ul className="mt-1 text-xs text-emerald-300/90 space-y-1">
                {deconstruction.inferredContract.invariants.map((inv, idx) => (
                  <li key={idx} className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                    <span>{inv}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Box 3: Execution Traces */}
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="text-xs font-mono font-bold text-blue-400 flex items-center gap-1.5">
              <Activity className="w-4 h-4" /> DETERMINISTIC EXECUTION TRACES
            </div>

            <div>
              <div className="text-[10px] font-mono text-emerald-400 uppercase">Happy Path Trace:</div>
              <div className="mt-1 space-y-1 text-xs text-slate-300 font-mono">
                {deconstruction.executionTraces.happyPath.map((step, idx) => (
                  <div key={idx} className="text-slate-200">{step}</div>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/80">
              <div className="text-[10px] font-mono text-rose-400 uppercase">Strictly Prohibited Actions:</div>
              <div className="mt-1 space-y-1 text-xs text-rose-300/90 font-mono">
                {deconstruction.executionTraces.prohibitedActions.map((act, idx) => (
                  <div key={idx}>✕ {act}</div>
                ))}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
