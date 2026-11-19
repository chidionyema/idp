import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Search,
  Plus,
  FileCheck2,
  SlidersHorizontal,
} from 'lucide-react';
import {
  InstructionRecord,
  SpecialistAgent,
  calculateYield,
  validateInstructionProof,
} from '../lib/protocolEngine';

interface InstructionYieldLedgerViewProps {
  instructions: InstructionRecord[];
  agents: SpecialistAgent[];
  onUpdateInstructionOutcomeAndClaim: (
    instructionId: string,
    claimStatement: string,
    proofArtifact: string,
    actualValue: number
  ) => void;
  onFounderReviewAction: (
    instructionId: string,
    decision: 'Approved' | 'Revision Requested',
    notes: string
  ) => void;
  onOpenNewInstruction: () => void;
}

export const InstructionYieldLedgerView: React.FC<InstructionYieldLedgerViewProps> = ({
  instructions,
  agents,
  onUpdateInstructionOutcomeAndClaim,
  onFounderReviewAction,
  onOpenNewInstruction,
}) => {
  const [statusFilter, setStatusFilter] = useState<
    'ALL' | 'Pending Review' | 'Approved' | 'Revision Requested'
  >('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedId, setSelectedId] = useState<string>(
    instructions[1]?.id || instructions[0]?.id || ''
  );

  const selectedInstruction =
    instructions.find((i) => i.id === selectedId) || instructions[0];

  const [claimDraft, setClaimDraft] = useState<string>(
    selectedInstruction?.claimStatement || ''
  );
  const [proofDraft, setProofDraft] = useState<string>(
    selectedInstruction?.proofArtifact || ''
  );
  const [actualDraft, setActualDraft] = useState<string>(
    selectedInstruction ? String(selectedInstruction.actualValue) : '0'
  );
  const [founderNotesDraft, setFounderNotesDraft] = useState<string>(
    selectedInstruction?.founderReview.notes || ''
  );
  const [actionFeedback, setActionFeedback] = useState<string>('');
  const [validationError, setValidationError] = useState<string>('');

  const handleSelectInstruction = (item: InstructionRecord) => {
    setSelectedId(item.id);
    setClaimDraft(item.claimStatement);
    setProofDraft(item.proofArtifact);
    setActualDraft(String(item.actualValue));
    setFounderNotesDraft(item.founderReview.notes);
    setActionFeedback('');
    setValidationError('');
  };

  const filteredInstructions = instructions.filter((item) => {
    const matchesStatus =
      statusFilter === 'ALL' || item.founderReview.status === statusFilter;
    const q = searchQuery.trim().toLowerCase();
    const matchesSearch =
      !q ||
      item.title.toLowerCase().includes(q) ||
      item.id.toLowerCase().includes(q) ||
      item.estateAsset.toLowerCase().includes(q) ||
      item.protocolId.toLowerCase().includes(q) ||
      item.claimStatement.toLowerCase().includes(q);
    return matchesStatus && matchesSearch;
  });

  const parsedActual = Number(actualDraft);
  const liveYield = selectedInstruction
    ? calculateYield(
        selectedInstruction.expectedValue,
        Number.isNaN(parsedActual) ? 0 : parsedActual,
        selectedInstruction.lowerIsBetter
      )
    : null;

  const liveProofValidation = selectedInstruction
    ? validateInstructionProof(
        claimDraft,
        proofDraft,
        selectedInstruction.protocolId
      )
    : null;

  const handleSaveClaimAndOutcome = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstruction) return;

    if (Number.isNaN(parsedActual) || parsedActual < 0) {
      setValidationError('Actual outcome value must be a valid non-negative number.');
      return;
    }
    const proofCheck = validateInstructionProof(
      claimDraft,
      proofDraft,
      selectedInstruction.protocolId
    );
    if (!proofCheck.valid) {
      setValidationError(
        `Proof validation failed: ${proofCheck.missingElements.join('; ')}`
      );
      return;
    }

    setValidationError('');
    onUpdateInstructionOutcomeAndClaim(
      selectedInstruction.id,
      claimDraft.trim(),
      proofDraft.trim(),
      parsedActual
    );
    setActionFeedback(
      `Updated claim, verified proof (${proofCheck.completenessScore}% completeness), and recalculated Yield to ${liveYield?.yieldPercent.toFixed(1)}%.`
    );
  };

  const handleFounderDecision = (decision: 'Approved' | 'Revision Requested') => {
    if (!selectedInstruction) return;
    if (!founderNotesDraft.trim() || founderNotesDraft.trim().length < 6) {
      setValidationError(
        'Please provide a Founder review note (at least 6 characters) before recording sign-off.'
      );
      return;
    }
    setValidationError('');
    onFounderReviewAction(
      selectedInstruction.id,
      decision,
      founderNotesDraft.trim()
    );
    setActionFeedback(
      `Founder review recorded: ${decision} for ${selectedInstruction.id}.`
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Instruction Tracking · Specialist Claims & Proofs · Outcome vs. Expected Yield · Founder Review
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">
            Instruction, Claim, Proof & Yield Audit Ledger
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 max-w-3xl">
            Every estate instruction is tracked from issuance through specialist claim, cryptographic proof verification, outcome vs. expected yield calculation, and final Founder sign-off.
          </p>
        </div>

        <button
          type="button"
          onClick={onOpenNewInstruction}
          className="px-4 py-2.5 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 inline-flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Issue New Estate Instruction</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg self-start">
          {(
            [
              { id: 'ALL', label: `All Instructions (${instructions.length})` },
              {
                id: 'Pending Review',
                label: `Pending Founder Review (${
                  instructions.filter((i) => i.founderReview.status === 'Pending Review')
                    .length
                })`,
              },
              {
                id: 'Approved',
                label: `Founder Approved (${
                  instructions.filter((i) => i.founderReview.status === 'Approved')
                    .length
                })`,
              },
              {
                id: 'Revision Requested',
                label: `Revision Requested (${
                  instructions.filter(
                    (i) => i.founderReview.status === 'Revision Requested'
                  ).length
                })`,
              },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-72">
          <label htmlFor="instruction-search" className="sr-only">
            Search instructions, protocols, or claims
          </label>
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="instruction-search"
            type="search"
            placeholder="Search instructions, assets, proofs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
          />
        </div>
      </div>

      {/* Main Split: Instruction Ledger Table + Selected Instruction Audit & Founder Review Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 7 Cols: High-Density Ledger */}
        <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg overflow-hidden">
          {filteredInstructions.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                No estate instructions match the current filter
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Clear the search filter or issue a new Estate Instruction to dispatch work to a specialist squad.
              </p>
              <button
                type="button"
                onClick={() => {
                  setStatusFilter('ALL');
                  setSearchQuery('');
                }}
                className="px-3 py-1.5 text-xs font-medium bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 rounded-md cursor-pointer"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              {filteredInstructions.map((item) => {
                const isSelected = selectedInstruction?.id === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelectInstruction(item)}
                    className={`w-full text-left p-5 transition-colors block cursor-pointer ${
                      isSelected
                        ? 'bg-slate-100/90 dark:bg-slate-800/70'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/30'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
                      <span>
                        <strong className="text-slate-900 dark:text-slate-100">
                          {item.id}
                        </strong>{' '}
                        · {item.specialistId} · {item.protocolId}
                      </span>
                      <span
                        className={`font-bold tabular-nums ${
                          item.yieldPercent >= 100
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : item.yieldPercent >= 95
                            ? 'text-slate-900 dark:text-slate-100'
                            : 'text-amber-700 dark:text-amber-400'
                        }`}
                      >
                        Yield: {item.yieldPercent.toFixed(1)}% ({item.yieldGrade})
                      </span>
                    </div>

                    <div className="font-semibold text-sm text-slate-900 dark:text-slate-100 mt-1">
                      {item.title}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      Asset: {item.estateAsset} · Stage: {item.stage}
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-slate-200/80 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-mono text-slate-600 dark:text-slate-400 truncate max-w-sm">
                        Proof: {item.proofArtifact}
                      </span>
                      <span className="inline-flex items-center gap-1 font-medium">
                        {item.founderReview.status === 'Approved' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        ) : (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                        )}
                        <span
                          className={
                            item.founderReview.status === 'Approved'
                              ? 'text-emerald-700 dark:text-emerald-400'
                              : item.founderReview.status === 'Revision Requested'
                              ? 'text-rose-700 dark:text-rose-400'
                              : 'text-amber-700 dark:text-amber-400'
                          }
                        >
                          Founder: {item.founderReview.status}
                        </span>
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 5 Cols: Claim, Proof, Yield & Founder Review Workbench */}
        {selectedInstruction && (
          <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-6">
            <div className="border-b border-slate-200 dark:border-slate-800 pb-4 space-y-1">
              <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
                {selectedInstruction.id} · {selectedInstruction.protocolId} ·{' '}
                {selectedInstruction.specialistId}
              </div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {selectedInstruction.title}
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {selectedInstruction.instructionSpec}
              </p>
            </div>

            {/* Live Yield Formula Box */}
            {liveYield && (
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    Yield Measurement (Outcome vs. Expected)
                  </span>
                  <span className="font-mono font-bold text-sm tabular-nums text-emerald-700 dark:text-emerald-400">
                    {liveYield.yieldPercent.toFixed(1)}% · {liveYield.grade}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1 text-xs font-mono tabular-nums">
                  <div>
                    <div className="text-slate-500 dark:text-slate-400">Expected</div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {selectedInstruction.expectedValue} {selectedInstruction.unit}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500 dark:text-slate-400">Actual</div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {Number.isNaN(parsedActual) ? 0 : parsedActual} {selectedInstruction.unit}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500 dark:text-slate-400">Net Delta</div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {liveYield.delta >= 0 ? `+${liveYield.delta}` : liveYield.delta}{' '}
                      {selectedInstruction.unit}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Form to Update Claim, Proof & Actual Outcome */}
            <form onSubmit={handleSaveClaimAndOutcome} className="space-y-3">
              <div>
                <label
                  htmlFor="claim-statement-input"
                  className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"
                >
                  Specialist Claim Statement
                </label>
                <textarea
                  id="claim-statement-input"
                  rows={2}
                  value={claimDraft}
                  onChange={(e) => setClaimDraft(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label
                  htmlFor="proof-artifact-input"
                  className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"
                >
                  Cryptographic Proof Token (PRF-*, LEDGER-*, DIFF-*, or sha256:)
                </label>
                <input
                  id="proof-artifact-input"
                  type="text"
                  value={proofDraft}
                  onChange={(e) => setProofDraft(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
                {liveProofValidation && (
                  <div className="text-[11px] font-mono mt-1 text-slate-500 dark:text-slate-400">
                    Protocol Proof Completeness: {liveProofValidation.completenessScore}%{' '}
                    {liveProofValidation.valid ? '(Verified)' : '(Incomplete)'}
                  </div>
                )}
              </div>

              <div>
                <label
                  htmlFor="actual-outcome-input"
                  className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"
                >
                  Measured Actual Outcome ({selectedInstruction.expectedMetricLabel} in{' '}
                  {selectedInstruction.unit})
                </label>
                <div className="flex gap-2">
                  <input
                    id="actual-outcome-input"
                    type="number"
                    step="0.1"
                    value={actualDraft}
                    onChange={(e) => setActualDraft(e.target.value)}
                    className="flex-1 px-3 py-2 text-xs font-mono tabular-nums rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="submit"
                    className="px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-800 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                  >
                    Verify Claim & Recalculate Yield
                  </button>
                </div>
              </div>
            </form>

            {/* Founder Review Decision Section */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-900 dark:text-slate-100">
                  Founder Outcome & Yield Review
                </span>
                <span className="font-mono text-slate-500 dark:text-slate-400">
                  Status: {selectedInstruction.founderReview.status}
                </span>
              </div>

              <div>
                <label
                  htmlFor="founder-notes-input"
                  className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Founder Audit Notes & Directives
                </label>
                <textarea
                  id="founder-notes-input"
                  rows={2}
                  value={founderNotesDraft}
                  onChange={(e) => setFounderNotesDraft(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleFounderDecision('Approved')}
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-md transition-colors cursor-pointer"
                >
                  Approve Outcome & Yield
                </button>
                <button
                  type="button"
                  onClick={() => handleFounderDecision('Revision Requested')}
                  className="px-4 py-2 text-xs font-semibold text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 hover:bg-rose-100 rounded-md transition-colors cursor-pointer"
                >
                  Request Specialist Revision
                </button>
              </div>

              {validationError && (
                <p
                  role="alert"
                  className="text-xs text-rose-600 dark:text-rose-400 font-medium"
                >
                  {validationError}
                </p>
              )}

              {actionFeedback && (
                <div
                  role="status"
                  className="p-3 rounded-md bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-200 font-medium"
                >
                  {actionFeedback}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
