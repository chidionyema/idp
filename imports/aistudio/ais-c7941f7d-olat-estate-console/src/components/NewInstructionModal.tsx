import React, { useState } from 'react';
import { X } from 'lucide-react';
import {
  SpecialistAgent,
  compileFounderPromptToBddAndFormalSpec,
} from '../lib/protocolEngine';

interface NewInstructionModalProps {
  isOpen: boolean;
  agents: SpecialistAgent[];
  onClose: () => void;
  onCreateInstruction: (payload: {
    title: string;
    estateAsset: string;
    specialistId: string;
    protocolId: string;
    instructionSpec: string;
    expectedMetricLabel: string;
    expectedValue: number;
    actualValue: number;
    unit: string;
    claimStatement: string;
    proofArtifact: string;
  }) => void;
}

export const NewInstructionModal: React.FC<NewInstructionModalProps> = ({
  isOpen,
  agents,
  onClose,
  onCreateInstruction,
}) => {
  const [title, setTitle] = useState<string>('');
  const [estateAsset, setEstateAsset] = useState<string>('');
  const [specialistId, setSpecialistId] = useState<string>(
    agents[0]?.id || 'SPC-ESTATE-01'
  );
  const [instructionSpec, setInstructionSpec] = useState<string>('');
  const [expectedMetricLabel, setExpectedMetricLabel] = useState<string>(
    'Verified Recovery / Units Cleared'
  );
  const [expectedValue, setExpectedValue] = useState<string>('120');
  const [actualValue, setActualValue] = useState<string>('126');
  const [unit, setUnit] = useState<string>('$k');
  const [claimStatement, setClaimStatement] = useState<string>(
    'Claimed headless execution across target estate schedules with zero manual overrides.'
  );
  const [proofArtifact, setProofArtifact] = useState<string>(
    'PRF-ESTATE-9042 · sha256:6b81d29e'
  );
  const [error, setError] = useState<string>('');

  if (!isOpen) return null;

  const selectedAgent =
    agents.find((a) => a.id === specialistId) || agents[0];

  const liveCompiledBddSpec = compileFounderPromptToBddAndFormalSpec(
    `${title.trim() || 'Surgical Estate Audit'} — ${instructionSpec.trim() || 'Verify lease covenants and seal SHA-256 proof'}`,
    'DIRECT_FOUNDER_KERNEL'
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || title.trim().length < 6) {
      setError('Instruction title must be at least 6 characters.');
      return;
    }
    if (!estateAsset.trim()) {
      setError('Estate asset / portfolio name is required.');
      return;
    }
    if (!instructionSpec.trim() || instructionSpec.trim().length < 10) {
      setError('Protocol instruction specification must be at least 10 characters.');
      return;
    }
    const expNum = Number(expectedValue);
    const actNum = Number(actualValue);
    if (Number.isNaN(expNum) || expNum <= 0) {
      setError('Expected outcome value must be greater than 0.');
      return;
    }
    if (Number.isNaN(actNum) || actNum < 0) {
      setError('Actual outcome value must be 0 or greater.');
      return;
    }

    setError('');
    onCreateInstruction({
      title: title.trim(),
      estateAsset: estateAsset.trim(),
      specialistId: selectedAgent.id,
      protocolId: selectedAgent.protocolId,
      instructionSpec: instructionSpec.trim(),
      expectedMetricLabel: expectedMetricLabel.trim() || 'Outcome Units',
      expectedValue: expNum,
      actualValue: actNum,
      unit: unit.trim() || 'units',
      claimStatement: claimStatement.trim(),
      proofArtifact: proofArtifact.trim(),
    });
    setTitle('');
    setEstateAsset('');
    setInstructionSpec('');
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="issue-instruction-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs"
    >
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg p-6 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div>
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
              QUAD-LAYER DISPATCH · ON-THE-FLY BDD &amp; FORMAL SPEC COMPILER
            </div>
            <h2
              id="issue-instruction-modal-title"
              className="text-lg font-bold text-slate-900 dark:text-slate-50"
            >
              Issue New Estate Protocol Instruction
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close issue instruction modal"
            className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="modal-inst-title"
                className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
              >
                Instruction Title
              </label>
              <input
                id="modal-inst-title"
                type="text"
                placeholder="e.g., Q4 Industrial Roof CapEx Audit"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label
                htmlFor="modal-inst-asset"
                className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
              >
                Target Estate Asset / Portfolio
              </label>
              <input
                id="modal-inst-asset"
                type="text"
                placeholder="e.g., Westgate Logistics Park (22 Units)"
                value={estateAsset}
                onChange={(e) => setEstateAsset(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="modal-inst-specialist"
              className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
            >
              Assign Autonomous Specialist Squad &amp; Strict Protocol
            </label>
            <select
              id="modal-inst-specialist"
              value={specialistId}
              onChange={(e) => setSpecialistId(e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              {agents.map((ag) => (
                <option key={ag.id} value={ag.id}>
                  {ag.id} — {ag.name} ({ag.protocolId})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="modal-inst-spec"
              className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
            >
              Protocol Execution Specification
            </label>
            <textarea
              id="modal-inst-spec"
              rows={2}
              placeholder="Specify exact lease covenants, title records, or CAM invoices to verify headlessly..."
              value={instructionSpec}
              onChange={(e) => setInstructionSpec(e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          {/* Live On-the-Fly BDD Gherkin + Formal Spec Compilation Box */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-[11px] text-slate-200 space-y-1.5">
            <div className="flex items-center justify-between text-emerald-400 font-semibold">
              <span>LIVE AUTO-COMPILED BDD &amp; FORMAL SPEC</span>
              <span>
                WWFD Approval: {liveCompiledBddSpec.wwfdAlignmentAudit.predictedFounderApprovalPercent}%
              </span>
            </div>
            <div className="text-amber-300">
              {liveCompiledBddSpec.bddGherkinScenarios.scenarioTitle}
            </div>
            <div className="text-slate-300">
              • {liveCompiledBddSpec.bddGherkinScenarios.whenAction}
            </div>
            <div className="text-emerald-300">
              • {liveCompiledBddSpec.bddGherkinScenarios.thenTestableOutcomes[0]}
            </div>
            <div className="text-sky-300 pt-1 border-t border-slate-800">
              TLA+: {liveCompiledBddSpec.formalMathematicalSpec.tlaPlusTemporalInvariant}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="modal-expected-val"
                className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
              >
                Expected Outcome
              </label>
              <input
                id="modal-expected-val"
                type="number"
                step="0.1"
                value={expectedValue}
                onChange={(e) => setExpectedValue(e.target.value)}
                className="w-full px-3 py-2 font-mono tabular-nums rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label
                htmlFor="modal-actual-val"
                className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
              >
                Initial Measured Outcome
              </label>
              <input
                id="modal-actual-val"
                type="number"
                step="0.1"
                value={actualValue}
                onChange={(e) => setActualValue(e.target.value)}
                className="w-full px-3 py-2 font-mono tabular-nums rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label
                htmlFor="modal-unit-val"
                className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
              >
                Outcome Unit
              </label>
              <input
                id="modal-unit-val"
                type="text"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full px-3 py-2 font-mono rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="modal-proof-token"
              className="block font-semibold text-slate-700 dark:text-slate-300 mb-1"
            >
              Initial Proof Artifact Token
            </label>
            <input
              id="modal-proof-token"
              type="text"
              value={proofArtifact}
              onChange={(e) => setProofArtifact(e.target.value)}
              className="w-full px-3 py-2 font-mono rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          {error && (
            <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 font-medium">
              {error}
            </p>
          )}

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Dispatch Instruction &amp; Enqueue to Inbox
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

