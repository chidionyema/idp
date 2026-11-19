import React, { useState } from 'react';
import {
  AsymmetricProposal,
  AsymmetryEvaluationReceipt,
  evaluateAndEnforceAsymmetry,
  INITIAL_ASYMMETRIC_EXEMPLARS,
  ingestAndClarifyInstruction,
  ClarifiedInstructionSpec,
  EnforcementMechanism,
  ExecutionPhase,
} from '../lib/protocolEngine';

export const CompoundingEngineeringSurface: React.FC = () => {
  // Asymmetry Evaluation Playground State
  const [proposalId, setProposalId] = useState('PROP-ASYM-2026-1080');
  const [phase, setPhase] = useState<ExecutionPhase>('PreFlightAnticipatory');
  const [symptom, setSymptom] = useState('Text sprawl and lack of typography hierarchy on luxury cockpit surface');
  const [problemClass, setProblemClass] = useState('CLASS-UNCONSTRAINED-TYPOGRAPHY-AND-LAYOUT');
  const [cardinality, setCardinality] = useState(48);
  const [probesSaved, setProbesSaved] = useState(3.5);
  const [implCost, setImplCost] = useState(1.0);
  const [founderFriction, setFounderFriction] = useState(0.0);
  const [hardInvariants, setHardInvariants] = useState(true);
  const [wwfdScore, setWwfdScore] = useState(0.98);
  const [mechanism, setMechanism] = useState<EnforcementMechanism>('CompileTimeTypeGate');
  const [remediationCmd, setRemediationCmd] = useState(
    'npm run enforce && npx tsx scripts/enforce-typography-tokens.ts'
  );
  const [evalReceipt, setEvalReceipt] = useState<AsymmetryEvaluationReceipt | null>(null);

  // Vague Instruction Ingestion State
  const [rawPromptInput, setRawPromptInput] = useState(
    'Fix the messy layout and make sure it never happens again and sync'
  );
  const [clarifiedSpec, setClarifiedSpec] = useState<ClarifiedInstructionSpec | null>(null);

  const handleEvaluateProposal = (e: React.FormEvent) => {
    e.preventDefault();
    const proposal: AsymmetricProposal = {
      proposal_id: proposalId,
      phase,
      specific_symptom: symptom,
      problem_equivalence_class: problemClass,
      class_cardinality_estimate: cardinality,
      expected_probes_saved_per_instance: probesSaved,
      implementation_probe_cost: implCost,
      founder_friction_cost: founderFriction,
      hard_invariants_preserved: hardInvariants,
      wwfd_alignment_score: wwfdScore,
      enforcement_mechanism: mechanism,
      structural_remediation_cmd: remediationCmd,
    };
    const receipt = evaluateAndEnforceAsymmetry(proposal);
    setEvalReceipt(receipt);
  };

  const handleClarifyPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    const spec = ingestAndClarifyInstruction(rawPromptInput);
    setClarifiedSpec(spec);
  };

  return (
    <div className="space-y-6 bg-slate-950 p-6 rounded-2xl border border-slate-800 font-mono text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <h2 className="text-base font-bold tracking-tight text-white">
              COMPOUNDING ENGINEERING DOCTRINE & ASYMMETRY ENGINE (CORE LAW #7)
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Canonical Mandate: <span className="text-emerald-400">Implicitly reject single-bug fixes</span> · Enforce Asymmetric Class-Elimination (<code className="text-cyan-300">A(s) ≥ 10.0</code>, <code className="text-cyan-300">P_recur = 0</code>)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/olat-estate-genesis-main.bundle"
            download
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer transition flex items-center gap-1.5"
          >
            <span>📦</span>
            <span>Download Genesis Bundle</span>
          </a>
        </div>
      </div>

      {/* The 3 Canonical Exemplars of Asymmetry */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          The 3 Canonical Exemplars of Founder-Driven Asymmetry (Encoded in DNA)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {INITIAL_ASYMMETRIC_EXEMPLARS.map((ex) => (
            <div
              key={ex.id}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-300">{ex.id}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 font-bold">
                    {ex.leverageRatio}x Asymmetry
                  </span>
                </div>
                <div className="text-xs font-bold text-white">{ex.name}</div>
                <div className="text-[11px] text-slate-400">
                  <span className="text-rose-400">Symmetric Hack Rejected: </span>
                  {ex.rejectedSymmetricFix}
                </div>
                <div className="text-[11px] text-slate-300 bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-cyan-300 font-semibold">Asymmetric Solution: </span>
                  {ex.asymmetricSolution}
                </div>
              </div>
              <div className="text-[10px] text-emerald-400 font-semibold pt-1 border-t border-slate-800">
                Eradicated: {ex.eliminatedClass}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Asymmetry Ratio Calculator */}
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400">
              Interactive Asymmetry Proposal Gate (\mathcal&#123;A&#125;(s) &gt;= 10.0, P_recur = 0)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Simulate how Genesis rejects linear point-fixes and enforces whole-class structural eradication.
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded bg-slate-950 text-cyan-300 border border-slate-800">
            Formula: ([p] · ΔB · (1 - P_recur)) / (Cost + λ · Friction)
          </span>
        </div>

        <form onSubmit={handleEvaluateProposal} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Problem Equivalence Class [p]</label>
              <input
                type="text"
                value={problemClass}
                onChange={(e) => setProblemClass(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Class Cardinality (Future Occurrences)</label>
              <input
                type="number"
                value={cardinality}
                onChange={(e) => setCardinality(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Enforcement Mechanism</label>
              <select
                value={mechanism}
                onChange={(e) => setMechanism(e.target.value as EnforcementMechanism)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-indigo-300"
              >
                <option value="CompileTimeTypeGate">CompileTimeTypeGate (P_recur = 0)</option>
                <option value="BootTimeDayZeroGate">BootTimeDayZeroGate (P_recur = 0)</option>
                <option value="OracleShieldPass0Gate">OracleShieldPass0Gate (P_recur = 0)</option>
                <option value="CiPreMergeRegressionGate">CiPreMergeRegressionGate (P_recur = 0)</option>
                <option value="AdHocPointFix">AdHocPointFix (FORBIDDEN: P_recur = 0.85)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Probes Saved per Instance</label>
              <input
                type="number"
                step="0.5"
                value={probesSaved}
                onChange={(e) => setProbesSaved(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Impl Probe Cost</label>
              <input
                type="number"
                step="0.5"
                value={implCost}
                onChange={(e) => setImplCost(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">Founder Friction Cost</label>
              <input
                type="number"
                step="0.1"
                value={founderFriction}
                onChange={(e) => setFounderFriction(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 uppercase mb-1">WWFD Alignment Score</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={wwfdScore}
                onChange={(e) => setWwfdScore(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-slate-200"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-400">
              {mechanism === 'AdHocPointFix'
                ? '⚠️ Warning: Selecting AdHocPointFix will simulate immediate gate rejection.'
                : '✓ Structural gate selected: Guarantees zero recurrence across all instances.'}
            </span>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer transition"
            >
              Evaluate Proposal Against Core Law #7
            </button>
          </div>
        </form>

        {evalReceipt && (
          <div
            className={`p-4 rounded-xl border text-xs space-y-2 ${
              evalReceipt.approved
                ? 'bg-emerald-950/30 border-emerald-700 text-emerald-200'
                : 'bg-rose-950/30 border-rose-700 text-rose-200'
            }`}
          >
            <div className="flex items-center justify-between font-bold">
              <span>{evalReceipt.approved ? '✅ PROPOSAL APPROVED' : '❌ PROPOSAL REJECTED'}</span>
              <span>Leverage Ratio: {evalReceipt.computed_asymmetry_ratio}x (P_recur = {evalReceipt.recurrence_probability})</span>
            </div>
            <p className="text-[11px]">{evalReceipt.verdict_reason}</p>
            <div className="text-[10px] font-mono text-slate-400">
              Permanent DNA Pointer: <code>{evalReceipt.permanent_dna_uri}</code>
            </div>
          </div>
        )}
      </div>

      {/* Vague-by-Default Instruction Ingestion Simulator */}
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400">
              Vague-by-Default Ingestion Protocol (\text&#123;Vague&#125;_&#123;\text&#123;default&#125;&#125; = 1)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Assumes founder prompts are casual/vague by default. Deconstructs, flags ambiguities, and repeats back formal models before touching the estate.
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded bg-slate-950 text-amber-300 border border-slate-800">
            Pipeline: Clarify → Repeat → Model → Confirm
          </span>
        </div>

        <form onSubmit={handleClarifyPrompt} className="space-y-3 text-xs">
          <div>
            <label className="block text-[10px] text-slate-400 uppercase mb-1">Raw Founder Input</label>
            <textarea
              rows={2}
              value={rawPromptInput}
              onChange={(e) => setRawPromptInput(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer transition"
            >
              Parse & Formalize Ingestion Spec
            </button>
          </div>
        </form>

        {clarifiedSpec && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-cyan-300 font-bold">
                Inferred Protocol: <code className="text-amber-300">{clarifiedSpec.inferred_protocol}</code>
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  clarifiedSpec.ready_for_execution
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                    : 'bg-amber-950 text-amber-300 border border-amber-700'
                }`}
              >
                {clarifiedSpec.ready_for_execution ? 'READY FOR EXECUTION' : 'AMBIGUITY FLAGGED (PAUSE PRE-FLIGHT)'}
              </span>
            </div>

            <p className="text-slate-300 text-[11px]">{clarifiedSpec.formal_deconstruction}</p>

            {clarifiedSpec.identified_ambiguities.length > 0 && (
              <div className="space-y-1 bg-amber-950/20 p-2.5 rounded-lg border border-amber-800/40">
                <span className="text-amber-400 font-bold text-[10px] uppercase">Identified Ambiguities Defaulted Safely:</span>
                <ul className="list-disc list-inside text-[11px] text-slate-300">
                  {clarifiedSpec.identified_ambiguities.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {clarifiedSpec.model_scenarios.map((sc, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                  <div className="font-bold text-slate-200 text-[11px]">{sc.scenario_name}</div>
                  <div className="text-[10px] text-slate-400">Condition: {sc.input_condition}</div>
                  <div className="text-[10px] text-emerald-400">Expected: {sc.expected_behavior}</div>
                  <div className="text-[10px] font-mono text-cyan-300">Target CIF Receipt: {sc.cif_receipt_target}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
