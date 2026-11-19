/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  compileExplanationRecord,
  type AccessMode,
  type ExplanationRecordInput,
} from '../core/epistemicCalculus';

interface RecordCompilerViewProps {
  initialTemplate: ExplanationRecordInput;
  existingIds: string[];
  onCommitRecord: (newRecord: ExplanationRecordInput) => void;
}

export const RecordCompilerView: React.FC<RecordCompilerViewProps> = ({
  initialTemplate,
  existingIds,
  onCommitRecord,
}) => {
  const [recordId, setRecordId] = useState(`REC-2026-CUSTOM-00${existingIds.length + 1}`);
  const [title, setTitle] = useState(
    'Gemma-3-27B Sovereign Fortress Protocol — Automated Treasury Settlement'
  );
  const [domain, setDomain] = useState<ExplanationRecordInput['domain']>('autonomous-agent');
  const [summary, setSummary] = useState(
    'End-to-end 4-layer certified execution across Gemma Scope 2 open-weights probes, post-hoc confession audit, fencing-token Merkle state gate, and Map-Once protocol decomposition.'
  );
  const [epistemicConfidenceScore, setEpistemicConfidenceScore] = useState(0.91);

  // Layer 1 state
  const [accessMode, setAccessMode] = useState<AccessMode>('open-weights');
  const [modelFamily, setModelFamily] = useState('Gemma-3-27B-Scope2-Probed');
  const [replacementFidelity, setReplacementFidelity] = useState(0.62);
  const [causalNecessity, setCausalNecessity] = useState(0.85);
  const [probeDeceptionScore, setProbeDeceptionScore] = useState(0.02);
  const [nlaCovertFlag, setNlaCovertFlag] = useState(false);

  // Layer 2 state
  const [cotVerdict, setCotVerdict] = useState<'clean' | 'suspicious' | 'incriminating'>('clean');
  const [confessionStatus, setConfessionStatus] = useState<
    'compliant' | 'confessed-violation' | 'unaware-blindspot'
  >('compliant');
  const [statedCotExcerpt, setStatedCotExcerpt] = useState(
    'Verifying multi-sig treasury policy limit (€50,000 cap) and executing idempotent ledger transfer with fencing token #50201.'
  );
  const [confessionExcerpt, setConfessionExcerpt] = useState(
    'Confession channel: All instruction bounds and fencing token prerequisites were strictly satisfied.'
  );

  // Layer 3 state
  const [workflowId, setWorkflowId] = useState('WF-FORTRESS-GATE-101');
  const [fencingToken, setFencingToken] = useState(50201);
  const [authorityPrincipal, setAuthorityPrincipal] = useState('principal:founder@fortress.estate');
  const [agentSelfReport, setAgentSelfReport] = useState(
    'Settled €14,200 invoice #INV-902; post-state balance verified.'
  );
  const [verifiedStateDiff, setVerifiedStateDiff] = useState(
    'ledger_tx=0x99a1...44c0; amount_eur=14200; fencing_token=50201; status=COMMITTED'
  );
  const [stateMatchesSelfReport, setStateMatchesSelfReport] = useState(true);

  // Layer 4 state
  const [advertisedHeadline, setAdvertisedHeadline] = useState(
    'Zero-Drift Sovereign Treasury Settlement under EU AI Act Art. 12/14/86'
  );
  const [informalClaim, setInformalClaim] = useState(
    'Invoice #INV-902 settles iff amount <= €50,000, authority signature is valid, and post-state Merkle witness matches self-report.'
  );
  const [formalKernelProposition, setFormalKernelProposition] = useState(
    'theorem settlement_safe (tx : Tx) : tx.amount <= 50000 ∧ ValidFencing tx.token → KernelStateCommitted tx'
  );
  const [rawArtifactLines, setRawArtifactLines] = useState(1450);
  const [definitionalDriftScore, setDefinitionalDriftScore] = useState(0.02);
  const [humanReconstructible, setHumanReconstructible] = useState(true);

  const [validationError, setValidationError] = useState<string | null>(null);

  const loadFromTemplate = (tpl: ExplanationRecordInput) => {
    setRecordId(`${tpl.id}-FORK`);
    setTitle(`${tpl.title} (Forked Audit)`);
    setDomain(tpl.domain);
    setSummary(tpl.summary);
    setEpistemicConfidenceScore(tpl.epistemic_confidence_score);
    setAccessMode(tpl.l1.accessMode);
    setModelFamily(tpl.l1.modelFamily);
    setReplacementFidelity(tpl.l1.replacementFidelity);
    setCausalNecessity(tpl.l1.causalNecessity);
    setProbeDeceptionScore(tpl.l1.probeDeceptionScore);
    setNlaCovertFlag(tpl.l1.nlaCovertFlag);
    setCotVerdict(tpl.l2.cotVerdict);
    setConfessionStatus(tpl.l2.confessionStatus);
    setStatedCotExcerpt(tpl.l2.statedCotExcerpt);
    setConfessionExcerpt(tpl.l2.confessionExcerpt);
    setWorkflowId(tpl.l3.workflowId);
    const firstStep = tpl.l3.steps[0];
    if (firstStep) {
      setFencingToken(firstStep.fencingToken);
      setAuthorityPrincipal(firstStep.authorityPrincipal);
      setAgentSelfReport(firstStep.agentSelfReport);
      setVerifiedStateDiff(firstStep.verifiedStateDiff);
      setStateMatchesSelfReport(firstStep.stateMatchesSelfReport);
    }
    setAdvertisedHeadline(tpl.l4.advertisedHeadline);
    setInformalClaim(tpl.l4.informalClaim);
    setFormalKernelProposition(tpl.l4.formalKernelProposition);
    setRawArtifactLines(tpl.l4.rawArtifactLines);
    setDefinitionalDriftScore(tpl.l4.definitionalDriftScore);
    setHumanReconstructible(
      tpl.l4.mentalMapNodes.every((n) => n.humanReconstructible)
    );
    setValidationError(null);
  };

  const draftRecord: ExplanationRecordInput = {
    id: recordId.trim(),
    title: title.trim(),
    domain,
    timestamp: new Date().toISOString(),
    summary: summary.trim(),
    epistemic_confidence_score: epistemicConfidenceScore,
    l1: {
      accessMode,
      modelFamily: modelFamily.trim() || 'Unspecified-Model',
      replacementFidelity,
      causalNecessity,
      probeDeceptionScore,
      nlaCosineSimilarity: 0.88,
      nlaCovertFlag,
      activeFeatures:
        accessMode === 'open-weights'
          ? [
              {
                id: 'SAE-L24-701',
                label: 'Instruction Authority & Numeric Cap Invariant',
                layer: 24,
                activation: 0.92,
                causalEffect: causalNecessity,
                category: probeDeceptionScore > 0.4 ? 'deception' : 'nominal',
              },
            ]
          : [],
    },
    l2: {
      empiricalFaithfulnessBaseline: 0.35,
      cotMonitorabilityIndex: 0.78,
      cotVerdict,
      confessionStatus,
      statedCotExcerpt: statedCotExcerpt.trim(),
      confessionExcerpt: confessionExcerpt.trim(),
    },
    l3: {
      workflowId: workflowId.trim(),
      euAiActRiskTier: 'high-risk-annex-iii',
      retentionMonthsConfigured: 24,
      steps: [
        {
          stepIndex: 1,
          fencingToken,
          authorityPrincipal: authorityPrincipal.trim(),
          instructionScope: 'GATED_PROVENANCE_EXECUTION',
          agentSelfReport: agentSelfReport.trim(),
          verifiedStateDiff: verifiedStateDiff.trim(),
          preStateHash: '0x4100ab12',
          postStateHash: stateMatchesSelfReport ? '0x99f2c804' : '0x4100ab12',
          stateMatchesSelfReport,
        },
      ],
    },
    l4: {
      advertisedHeadline: advertisedHeadline.trim(),
      informalClaim: informalClaim.trim(),
      formalKernelProposition: formalKernelProposition.trim(),
      formalVerifierStatus: 'lean-kernel-verified',
      rawArtifactLines,
      vacuousAntecedentDetected: false,
      definitionalDriftScore,
      mutationSurvivalRate: 0.95,
      mentalMapNodes: [
        {
          id: 'MAP-1',
          title: 'Pre-Condition Authority & Fencing Verification',
          role: 'axiom-input',
          summary: 'Verifies monotonic fencing token and cryptographic principal scope.',
          rawSpanCount: Math.max(10, Math.floor(rawArtifactLines * 0.4)),
          nodeBelief: humanReconstructible ? 0.94 : 0.4,
          dependsOn: [],
          humanReconstructible,
        },
        {
          id: 'MAP-2',
          title: 'Post-Condition Merkle State Correspondence',
          role: 'conclusion',
          summary: 'Confirms state transition diff matches formal proposition and L2 report.',
          rawSpanCount: Math.max(10, Math.floor(rawArtifactLines * 0.6)),
          nodeBelief: humanReconstructible ? 0.92 : 0.38,
          dependsOn: ['MAP-1'],
          humanReconstructible,
        },
      ],
    },
  };

  const liveCompiled = compileExplanationRecord(draftRecord);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!recordId.trim() || !title.trim() || !authorityPrincipal.trim() || !formalKernelProposition.trim()) {
      setValidationError(
        'Validation Error: Record ID, Title, Authority Principal, and Formal Kernel Proposition are required to emit a cryptographically signed Explanation Record.'
      );
      return;
    }
    setValidationError(null);
    onCommitRecord(draftRecord);
  };

  return (
    <div className="max-w-7xl mx-auto p-6 lg:p-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
            L1–L4 Epistemic Provenance Gate & Compiler
          </span>
          <h1 className="text-2xl font-bold text-slate-100 font-display mt-1">
            Compile & Sign New Explanation Record
          </h1>
          <p className="text-sm text-slate-300 mt-1">
            Assemble verified L3 state transitions, L2 confession channels, L1 probe readouts, and L4 correspondence specifications into an immutable record.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadFromTemplate(initialTemplate)}
          className="px-3.5 py-2 text-xs font-medium text-slate-200 bg-[#111827] border border-slate-700 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap self-start"
        >
          Load Active Inspector Scenario ({initialTemplate.id})
        </button>
      </div>

      {validationError && (
        <div
          role="alert"
          className="p-4 rounded-md bg-rose-950/40 border border-rose-500/60 text-xs font-mono text-rose-200"
        >
          ✖ {validationError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 space-y-6">
          {/* Envelope Metadata */}
          <div className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-bold text-slate-100 font-display border-b border-slate-800 pb-2">
              01. Record Envelope & Instruction Identity
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="comp-record-id" className="block text-xs font-mono text-slate-300 mb-1">
                  Record Identifier
                </label>
                <input
                  id="comp-record-id"
                  type="text"
                  value={recordId}
                  onChange={(e) => setRecordId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                />
              </div>
              <div>
                <label htmlFor="comp-domain" className="block text-xs font-mono text-slate-300 mb-1">
                  Operational Domain
                </label>
                <select
                  id="comp-domain"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value as ExplanationRecordInput['domain'])}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                >
                  <option value="autonomous-agent">autonomous-agent</option>
                  <option value="formal-mathematics">formal-mathematics</option>
                  <option value="frontier-safety-audit">frontier-safety-audit</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="comp-title" className="block text-xs font-mono text-slate-300 mb-1">
                Explanation Record Title
              </label>
              <input
                id="comp-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#07090E] border border-slate-700 rounded text-slate-100"
              />
            </div>

            <div>
              <label htmlFor="comp-summary" className="block text-xs font-mono text-slate-300 mb-1">
                Executive Audit Summary
              </label>
              <textarea
                id="comp-summary"
                rows={2}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-[#07090E] border border-slate-700 rounded text-slate-100"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <label htmlFor="comp-epistemic-confidence" className="text-slate-300">
                  Epistemic Confidence Score (epistemic_confidence_score: 0.0–1.0)
                </label>
                <span className="text-emerald-400 font-semibold tabular-nums">
                  {epistemicConfidenceScore.toFixed(2)} ({Math.round(epistemicConfidenceScore * 100)}%)
                </span>
              </div>
              <input
                id="comp-epistemic-confidence"
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={epistemicConfidenceScore}
                onChange={(e) => setEpistemicConfidenceScore(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>
          </div>

          {/* Layer 1 & Layer 2 Inputs */}
          <div className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-bold text-slate-100 font-display border-b border-slate-800 pb-2">
              02. Layer 1 (Mechanistic Probes) & Layer 2 (Confession Honesty Stack)
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="comp-access-mode" className="block text-xs font-mono text-slate-300 mb-1">
                  L1 Weight Access Mode
                </label>
                <select
                  id="comp-access-mode"
                  value={accessMode}
                  onChange={(e) => setAccessMode(e.target.value as AccessMode)}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                >
                  <option value="open-weights">open-weights (L1 Probed)</option>
                  <option value="api-black-box">api-black-box (100% L1 Dark Matter)</option>
                </select>
              </div>
              <div>
                <label htmlFor="comp-model-family" className="block text-xs font-mono text-slate-300 mb-1">
                  Target Model & Probe Suite
                </label>
                <input
                  id="comp-model-family"
                  type="text"
                  value={modelFamily}
                  onChange={(e) => setModelFamily(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="comp-cot-verdict" className="block text-xs font-mono text-slate-300 mb-1">
                  L2 CoT Monitor Verdict
                </label>
                <select
                  id="comp-cot-verdict"
                  value={cotVerdict}
                  onChange={(e) =>
                    setCotVerdict(e.target.value as 'clean' | 'suspicious' | 'incriminating')
                  }
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                >
                  <option value="clean">clean (Zero Exoneration by Theorem 1)</option>
                  <option value="suspicious">suspicious (Plausibility Penalty)</option>
                  <option value="incriminating">incriminating (Plausibility Collapse)</option>
                </select>
              </div>
              <div>
                <label htmlFor="comp-confession" className="block text-xs font-mono text-slate-300 mb-1">
                  L2 Post-Hoc Confession Status
                </label>
                <select
                  id="comp-confession"
                  value={confessionStatus}
                  onChange={(e) =>
                    setConfessionStatus(
                      e.target.value as 'compliant' | 'confessed-violation' | 'unaware-blindspot'
                    )
                  }
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                >
                  <option value="compliant">compliant</option>
                  <option value="confessed-violation">confessed-violation</option>
                  <option value="unaware-blindspot">unaware-blindspot</option>
                </select>
              </div>
            </div>
          </div>

          {/* Layer 3 & Layer 4 Inputs */}
          <div className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-bold text-slate-100 font-display border-b border-slate-800 pb-2">
              03. Layer 3 (Provenance Gate) & Layer 4 (Formal Correspondence)
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="comp-authority" className="block text-xs font-mono text-slate-300 mb-1">
                  Authority Principal (EU AI Act Art. 12)
                </label>
                <input
                  id="comp-authority"
                  type="text"
                  value={authorityPrincipal}
                  onChange={(e) => setAuthorityPrincipal(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                />
              </div>
              <div>
                <label htmlFor="comp-fencing" className="block text-xs font-mono text-slate-300 mb-1">
                  Monotonic Fencing Token τ_k
                </label>
                <input
                  id="comp-fencing"
                  type="number"
                  value={fencingToken}
                  onChange={(e) => setFencingToken(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-slate-100"
                />
              </div>
            </div>

            <div>
              <label htmlFor="comp-formal-prop" className="block text-xs font-mono text-slate-300 mb-1">
                Formal Kernel Proposition / Invariant (P_formal)
              </label>
              <input
                id="comp-formal-prop"
                type="text"
                value={formalKernelProposition}
                onChange={(e) => setFormalKernelProposition(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-[#07090E] border border-slate-700 rounded text-cyan-200"
              />
            </div>

            <div className="flex flex-wrap items-center gap-6 pt-2">
              <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={stateMatchesSelfReport}
                  onChange={(e) => setStateMatchesSelfReport(e.target.checked)}
                  className="accent-cyan-400"
                />
                <span>L3 Kernel State Diff Matches Agent Self-Report</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={humanReconstructible}
                  onChange={(e) => setHumanReconstructible(e.target.checked)}
                  className="accent-cyan-400"
                />
                <span>L4 Mental-Map Nodes Human-Reconstructible</span>
              </label>
            </div>
          </div>
        </div>

        {/* Right Live Preview & Commit Panel */}
        <div className="lg:col-span-5 bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-5 sticky top-20">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
              Real-Time Pre-Commit Verification
            </span>
            <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
              Computed Certificate Preview
            </h2>
          </div>

          <div className="grid grid-cols-3 gap-3 bg-[#080B12] p-3.5 rounded border border-slate-800">
            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase">Bel(C) Lower</div>
              <div className="text-xl font-bold font-mono text-emerald-400 tabular-nums">
                {(liveCompiled.epistemicInterval.beliefLowerBound * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase">Pl(C) Upper</div>
              <div className="text-xl font-bold font-mono text-cyan-300 tabular-nums">
                {(liveCompiled.epistemicInterval.plausibilityUpperBound * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase">Ignorance Ω</div>
              <div className="text-xl font-bold font-mono text-amber-300 tabular-nums">
                {(liveCompiled.epistemicInterval.ignoranceWidth * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="space-y-2 text-xs font-mono bg-[#080B12] p-3.5 rounded border border-slate-800">
            <div className="flex justify-between">
              <span className="text-slate-400">Evidence Grade:</span>
              <span className="text-cyan-300 font-semibold">{liveCompiled.evidenceGrade}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">L3 Merkle Root:</span>
              <span className="text-slate-200 tabular-nums">{liveCompiled.l3Metrics.merkleRootHex}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Certificate Digest:</span>
              <span className="text-slate-200 tabular-nums">{liveCompiled.certificateHash}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">EU AI Act Art. 12/14/86:</span>
              <span
                className={
                  liveCompiled.l3Metrics.euAiActCompliance.overallCompliant
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {liveCompiled.l3Metrics.euAiActCompliance.overallCompliant
                  ? '● COMPLIANT'
                  : '✖ NON-COMPLIANT'}
              </span>
            </div>
          </div>

          <p className="text-xs font-mono text-slate-300 leading-relaxed">
            {liveCompiled.mathematicalVerdict}
          </p>

          <button
            type="submit"
            className="w-full py-2.5 px-4 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors cursor-pointer"
          >
            Sign & Append Record to Corpus
          </button>
        </div>
      </form>
    </div>
  );
};
