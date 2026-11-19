/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  compileExplanationRecord,
  type CertifiedExplanationRecord,
  type EvidenceGrade,
  type ExplanationRecordInput,
} from '../core/epistemicCalculus';
import {
  buildExplanationRecordAuditBundle,
  generateExplanationRecordPdfBytes,
  serializeExplanationRecordJson,
} from '../core/recordExporter';
import { AuditExportModal, triggerBrowserDownload } from './AuditExportModal';
import { CrossLayerKnowledgeGraph } from './CrossLayerKnowledgeGraph';
import { EpistemicConfidenceProgressBar } from './EpistemicConfidenceProgressBar';

interface RecordInspectorViewProps {
  records: ExplanationRecordInput[];
  selectedRecordId: string;
  onSelectRecordId: (id: string) => void;
  onOpenCompilerWithTemplate: (template: ExplanationRecordInput) => void;
}

function formatGradeLabel(grade: EvidenceGrade): {
  glyph: string;
  label: string;
  toneClass: string;
} {
  switch (grade) {
    case 'CERTIFIED_L1_L4':
      return {
        glyph: '●',
        label: 'Certified L1–L4 (Full Epistemic Warrant)',
        toneClass: 'text-emerald-400',
      };
    case 'PROVENANCE_LOCKED':
      return {
        glyph: '●',
        label: 'Provenance-Locked (Bounded Residual)',
        toneClass: 'text-cyan-400',
      };
    case 'DEGRADED_API_ONLY':
      return {
        glyph: '▲',
        label: 'Degraded API-Only (100% L1 Dark Matter)',
        toneClass: 'text-amber-400',
      };
    case 'CORRESPONDENCE_GAP':
      return {
        glyph: '▲',
        label: 'Correspondence Gap (Verified Without Understanding)',
        toneClass: 'text-amber-400',
      };
    case 'CONTAINMENT_BREACH':
      return {
        glyph: '✖',
        label: 'Containment Breach (Plausibility Collapsed)',
        toneClass: 'text-rose-400',
      };
  }
}

export const RecordInspectorView: React.FC<RecordInspectorViewProps> = ({
  records,
  selectedRecordId,
  onSelectRecordId,
  onOpenCompilerWithTemplate,
}) => {
  const canonicalRecord =
    records.find((r) => r.id === selectedRecordId) || records[0];

  // Counterfactual perturbation state keyed to the active record
  const [overrideInput, setOverrideInput] = useState<ExplanationRecordInput | null>(null);
  const [selectedMapNodeId, setSelectedMapNodeId] = useState<string | null>(null);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [lastExportReceipt, setLastExportReceipt] = useState<{
    format: 'PDF' | 'JSON';
    filename: string;
    byteSize: number;
    checksum: string;
  } | null>(null);

  // Ensure override resets when switching records
  const activeInput: ExplanationRecordInput =
    overrideInput && overrideInput.id === canonicalRecord.id
      ? overrideInput
      : canonicalRecord;

  const compiled: CertifiedExplanationRecord = compileExplanationRecord(activeInput);
  const isPerturbed =
    overrideInput !== null &&
    overrideInput.id === canonicalRecord.id &&
    JSON.stringify(overrideInput) !== JSON.stringify(canonicalRecord);

  const gradeMeta = formatGradeLabel(compiled.evidenceGrade);

  const activeMapNode =
    activeInput.l4.mentalMapNodes.find((n) => n.id === selectedMapNodeId) ||
    activeInput.l4.mentalMapNodes.find(
      (n) => n.id === compiled.l4Metrics.weakestBottleneckNode.id
    ) ||
    activeInput.l4.mentalMapNodes[0];

  const handleSelectScenario = (id: string) => {
    setOverrideInput(null);
    setSelectedMapNodeId(null);
    setLastExportReceipt(null);
    onSelectRecordId(id);
  };

  const applyPerturbation = (updater: (prev: ExplanationRecordInput) => ExplanationRecordInput) => {
    setOverrideInput(updater(structuredClone(activeInput)));
  };

  const handleDirectExportPdf = () => {
    const nowIso = new Date().toISOString();
    const bundle = buildExplanationRecordAuditBundle(compiled, nowIso);
    const pdfBytes = generateExplanationRecordPdfBytes(compiled, nowIso);
    const filename = `${activeInput.id.toLowerCase()}-l1-l4-audit-dossier.pdf`;
    triggerBrowserDownload(pdfBytes, filename, 'application/pdf');
    setLastExportReceipt({
      format: 'PDF',
      filename,
      byteSize: pdfBytes.byteLength,
      checksum: bundle.manifestHeader.bundleIntegrityChecksum,
    });
  };

  const handleDirectExportJson = () => {
    const nowIso = new Date().toISOString();
    const bundle = buildExplanationRecordAuditBundle(compiled, nowIso);
    const jsonString = serializeExplanationRecordJson(compiled, nowIso);
    const bytes = new TextEncoder().encode(jsonString);
    const filename = `${activeInput.id.toLowerCase()}-explanation-record.json`;
    triggerBrowserDownload(bytes, filename, 'application/json');
    setLastExportReceipt({
      format: 'JSON',
      filename,
      byteSize: bytes.byteLength,
      checksum: bundle.manifestHeader.bundleIntegrityChecksum,
    });
  };

  const belPct = Math.round(compiled.epistemicInterval.beliefLowerBound * 1000) / 10;
  const plPct = Math.round(compiled.epistemicInterval.plausibilityUpperBound * 1000) / 10;
  const ignPct = Math.round(compiled.epistemicInterval.ignoranceWidth * 1000) / 10;
  const disbeliefPct = Math.max(0, Math.round((100 - plPct) * 10) / 10);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[calc(100vh-57px)]">
      {/* Left Control & Parameter Column */}
      <aside
        aria-label="Explanation Corpus and Counterfactual Perturbation Controls"
        className="lg:col-span-4 xl:col-span-3 border-b lg:border-b-0 lg:border-r border-slate-800/90 bg-[#0A0E17] p-5 flex flex-col gap-6"
      >
        {/* Section 1: Corpus Selector */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold tracking-wider uppercase text-slate-400 font-mono">
              01. Explanation Record Corpus
            </h2>
            <span className="text-xs font-mono text-slate-400 tabular-nums">
              {records.length} records
            </span>
          </div>
          <div className="flex flex-col gap-2" role="listbox" aria-label="Select Explanation Record">
            {records.map((rec) => {
              const recCompiled = compileExplanationRecord(rec);
              const recMeta = formatGradeLabel(recCompiled.evidenceGrade);
              const isSelected = rec.id === canonicalRecord.id;
              return (
                <button
                  key={rec.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelectScenario(rec.id)}
                  className={`text-left p-3 rounded-md border transition-colors ${
                    isSelected
                      ? 'bg-[#111827] border-cyan-500/70 text-slate-100'
                      : 'bg-[#0C101B] border-slate-800/80 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 text-xs font-mono mb-1">
                    <span className="text-slate-400 tabular-nums">{rec.id}</span>
                    <span className={`${recMeta.toneClass} tabular-nums`}>
                      {recMeta.glyph} Bel {(recCompiled.epistemicInterval.beliefLowerBound * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-slate-100 leading-snug mb-1.5 font-display">
                    {rec.title}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <span>{rec.domain}</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono tabular-nums">
                      {rec.l1.accessMode === 'open-weights' ? 'Open-Weights' : 'API-Only'}
                    </span>
                  </div>
                  <EpistemicConfidenceProgressBar
                    score={
                      isSelected
                        ? activeInput.epistemic_confidence_score
                        : rec.epistemic_confidence_score
                    }
                    recordId={rec.id}
                    variant="compact"
                  />
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 2: Counterfactual Theorem Stress-Tester */}
        <div className="border-t border-slate-800/80 pt-5">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold tracking-wider uppercase text-slate-400 font-mono">
              02. Counterfactual Stress Test
            </h2>
            {isPerturbed && (
              <button
                type="button"
                onClick={() => setOverrideInput(null)}
                className="text-xs font-mono text-cyan-400 hover:text-cyan-300 underline whitespace-nowrap"
              >
                Reset Canonical
              </button>
            )}
          </div>
          <p className="text-xs text-slate-400 mb-3 leading-relaxed">
            Perturb individual layers to verify how Aletheia’s mathematical bounds respond in real time.
          </p>

          <div className="grid grid-cols-1 gap-2 mb-4">
            <button
              type="button"
              onClick={() =>
                applyPerturbation((draft) => {
                  draft.l1.accessMode =
                    draft.l1.accessMode === 'open-weights' ? 'api-black-box' : 'open-weights';
                  if (draft.l1.accessMode === 'open-weights' && draft.l1.replacementFidelity === 0) {
                    draft.l1.replacementFidelity = 0.58;
                    draft.l1.causalNecessity = 0.82;
                    draft.l1.nlaCosineSimilarity = 0.86;
                  }
                  return draft;
                })
              }
              className="px-3 py-2 text-xs font-medium text-left rounded border border-slate-700/80 bg-[#111827] hover:border-cyan-500/60 text-slate-200 transition-colors flex items-center justify-between"
            >
              <span>Toggle L1 Weight Access</span>
              <span className="font-mono text-cyan-300 tabular-nums">
                {activeInput.l1.accessMode === 'open-weights' ? 'Open-Weights' : 'API-Only'}
              </span>
            </button>

            <button
              type="button"
              onClick={() =>
                applyPerturbation((draft) => {
                  draft.l2.confessionStatus =
                    draft.l2.confessionStatus === 'confessed-violation'
                      ? 'compliant'
                      : 'confessed-violation';
                  return draft;
                })
              }
              className="px-3 py-2 text-xs font-medium text-left rounded border border-slate-700/80 bg-[#111827] hover:border-cyan-500/60 text-slate-200 transition-colors flex items-center justify-between"
            >
              <span>Toggle L2 Confession Violation</span>
              <span className="font-mono text-amber-300 tabular-nums">
                {activeInput.l2.confessionStatus === 'confessed-violation' ? 'Confessed' : 'Compliant'}
              </span>
            </button>

            <button
              type="button"
              onClick={() =>
                applyPerturbation((draft) => {
                  const firstStep = draft.l3.steps[0];
                  if (firstStep) {
                    firstStep.stateMatchesSelfReport = !firstStep.stateMatchesSelfReport;
                  }
                  return draft;
                })
              }
              className="px-3 py-2 text-xs font-medium text-left rounded border border-slate-700/80 bg-[#111827] hover:border-cyan-500/60 text-slate-200 transition-colors flex items-center justify-between"
            >
              <span>Toggle L3 Self-Report Divergence</span>
              <span className="font-mono text-rose-300 tabular-nums">
                {compiled.l3Metrics.selfReportDivergenceCount > 0 ? 'Divergent' : 'Verified'}
              </span>
            </button>

            <button
              type="button"
              onClick={() =>
                applyPerturbation((draft) => {
                  draft.l4.vacuousAntecedentDetected = !draft.l4.vacuousAntecedentDetected;
                  return draft;
                })
              }
              className="px-3 py-2 text-xs font-medium text-left rounded border border-slate-700/80 bg-[#111827] hover:border-cyan-500/60 text-slate-200 transition-colors flex items-center justify-between"
            >
              <span>Toggle L4 Vacuous Antecedent</span>
              <span className="font-mono text-amber-300 tabular-nums">
                {activeInput.l4.vacuousAntecedentDetected ? 'Vacuous (A ⊢ ⊥)' : 'Non-Vacuous'}
              </span>
            </button>
          </div>

          {/* Parameter Sliders */}
          <div className="space-y-3 pt-2 border-t border-slate-800/60">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <label htmlFor="slider-epistemic-confidence" className="text-slate-300">
                  Epistemic Confidence Score (0.0–1.0)
                </label>
                <span className="font-mono text-emerald-400 tabular-nums">
                  {activeInput.epistemic_confidence_score.toFixed(2)}
                </span>
              </div>
              <input
                id="slider-epistemic-confidence"
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={activeInput.epistemic_confidence_score}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  applyPerturbation((draft) => {
                    draft.epistemic_confidence_score = val;
                    return draft;
                  });
                }}
                className="w-full accent-cyan-400"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <label htmlFor="slider-l1-fidelity" className="text-slate-300">
                  L1 Circuit Replacement Fidelity
                </label>
                <span className="font-mono text-cyan-300 tabular-nums">
                  {(activeInput.l1.replacementFidelity * 100).toFixed(0)}%
                </span>
              </div>
              <input
                id="slider-l1-fidelity"
                type="range"
                min={0}
                max={1}
                step={0.01}
                disabled={activeInput.l1.accessMode === 'api-black-box'}
                value={activeInput.l1.replacementFidelity}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  applyPerturbation((draft) => {
                    draft.l1.replacementFidelity = val;
                    return draft;
                  });
                }}
                className="w-full accent-cyan-400 disabled:opacity-40"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <label htmlFor="slider-l1-probe" className="text-slate-300">
                  L1 Linear Probe Deception Score
                </label>
                <span className="font-mono text-amber-300 tabular-nums">
                  {(activeInput.l1.probeDeceptionScore * 100).toFixed(0)}%
                </span>
              </div>
              <input
                id="slider-l1-probe"
                type="range"
                min={0}
                max={1}
                step={0.01}
                disabled={activeInput.l1.accessMode === 'api-black-box'}
                value={activeInput.l1.probeDeceptionScore}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  applyPerturbation((draft) => {
                    draft.l1.probeDeceptionScore = val;
                    return draft;
                  });
                }}
                className="w-full accent-cyan-400 disabled:opacity-40"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <label htmlFor="slider-l4-drift" className="text-slate-300">
                  L4 Definitional Drift Score
                </label>
                <span className="font-mono text-slate-300 tabular-nums">
                  {(activeInput.l4.definitionalDriftScore * 100).toFixed(0)}%
                </span>
              </div>
              <input
                id="slider-l4-drift"
                type="range"
                min={0}
                max={0.8}
                step={0.01}
                value={activeInput.l4.definitionalDriftScore}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  applyPerturbation((draft) => {
                    draft.l4.definitionalDriftScore = val;
                    return draft;
                  });
                }}
                className="w-full accent-cyan-400"
              />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Viewport Stage */}
      <section
        aria-label="Certified Explanation Record Details"
        className="lg:col-span-8 xl:col-span-9 p-6 lg:p-8 space-y-6 bg-[#07090E]"
      >
        {/* Top Record Header */}
        <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4 pb-5 border-b border-slate-800/90">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 font-mono mb-2">
              <span className="text-slate-200 font-semibold">{activeInput.id}</span>
              <span aria-hidden="true">·</span>
              <span>{activeInput.domain}</span>
              <span aria-hidden="true">·</span>
              <span className="tabular-nums">{activeInput.timestamp}</span>
              <span aria-hidden="true">·</span>
              <span>Cert {compiled.certificateHash}</span>
              {isPerturbed && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="text-amber-300 font-semibold">Counterfactual Perturbation Active</span>
                </>
              )}
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-100 tracking-tight font-display">
              {activeInput.title}
            </h1>
            <p className="text-sm text-slate-300 mt-2 max-w-4xl leading-relaxed">
              {activeInput.summary}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => onOpenCompilerWithTemplate(activeInput)}
              className="px-3 py-2 text-xs font-medium text-slate-200 bg-[#111827] border border-slate-700 rounded-md hover:border-slate-500 transition-colors whitespace-nowrap"
            >
              Clone into Compiler
            </button>
            <button
              type="button"
              onClick={() => setIsExportModalOpen(true)}
              className="px-3 py-2 text-xs font-medium text-cyan-300 bg-[#0F172A] border border-cyan-500/50 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap"
            >
              Inspect Audit Dossier
            </button>
            <button
              type="button"
              onClick={handleDirectExportJson}
              className="px-3.5 py-2 text-xs font-semibold text-slate-100 bg-[#162033] border border-slate-600 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap cursor-pointer"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={handleDirectExportPdf}
              className="px-3.5 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors whitespace-nowrap cursor-pointer"
            >
              Export PDF Dossier
            </button>
          </div>
        </div>

        {/* Export Attestation Receipt Banner */}
        {lastExportReceipt && (
          <div
            role="status"
            aria-live="polite"
            className="bg-[#0B1520] border border-cyan-500/50 rounded-md px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono"
          >
            <div className="text-slate-200">
              <span className="text-emerald-400 font-semibold">● External Audit Package Exported ({lastExportReceipt.format})</span>
              <span aria-hidden="true" className="mx-2 text-slate-500">·</span>
              <span className="text-cyan-300">{lastExportReceipt.filename}</span>
              <span aria-hidden="true" className="mx-2 text-slate-500">·</span>
              <span className="text-slate-400 tabular-nums">{lastExportReceipt.byteSize.toLocaleString()} bytes</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-slate-400 tabular-nums">
                Bundle Checksum: <strong className="text-emerald-400">{lastExportReceipt.checksum}</strong>
              </span>
              <button
                type="button"
                onClick={() => setIsExportModalOpen(true)}
                className="text-cyan-300 hover:text-cyan-200 underline whitespace-nowrap"
              >
                View Dossier
              </button>
            </div>
          </div>
        )}

        {isExportModalOpen && (
          <AuditExportModal
            compiled={compiled}
            onClose={() => setIsExportModalOpen(false)}
            onExportTriggered={(format, filename, byteSize, checksum) => {
              setLastExportReceipt({ format, filename, byteSize, checksum });
            }}
          />
        )}

        {/* Dominant Visual Anchor: Epistemic Belief-Plausibility Interval & Legal Verdict */}
        <div className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-1">
                Dempster–Shafer Bounded Epistemic Certificate
              </div>
              <div className={`text-lg font-bold font-display ${gradeMeta.toneClass}`}>
                {gradeMeta.glyph} {gradeMeta.label}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 text-right">
              <div>
                <div className="text-xs font-mono text-slate-400 uppercase">Warranted Belief Bel(C)</div>
                <div className="text-2xl font-bold font-mono text-emerald-400 tabular-nums">
                  {belPct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-slate-400 uppercase">Upper Plausibility Pl(C)</div>
                <div className="text-2xl font-bold font-mono text-cyan-300 tabular-nums">
                  {plPct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-slate-400 uppercase">Epistemic Ignorance Ω(C)</div>
                <div className="text-2xl font-bold font-mono text-amber-300 tabular-nums">
                  {ignPct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Calibrated Epistemic Coordinate Bar */}
          <div>
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-1.5 tabular-nums">
              <span>0% (Zero Warrant)</span>
              <span>
                Interval: [{belPct.toFixed(1)}%, {plPct.toFixed(1)}%] · Residual Ω = {ignPct.toFixed(1)}%
              </span>
              <span>100% (Full Certainty)</span>
            </div>
            <div
              className="h-6 w-full bg-slate-950 rounded border border-slate-800 overflow-hidden flex"
              role="img"
              aria-label={`Epistemic interval bar: Warranted Belief ${belPct} percent, Unexplained Ignorance ${ignPct} percent, Disbelief ${disbeliefPct} percent`}
            >
              <div
                style={{ width: `${belPct}%` }}
                className="bg-emerald-500/80 border-r border-emerald-300 transition-all duration-150 flex items-center justify-center text-[11px] font-mono font-semibold text-slate-950 overflow-hidden whitespace-nowrap"
                title={`Warranted Lower Bound Bel(C): ${belPct}%`}
              >
                {belPct >= 12 ? `Bel ${belPct.toFixed(1)}%` : ''}
              </div>
              <div
                style={{ width: `${ignPct}%` }}
                className="bg-amber-500/30 border-r border-amber-400/60 transition-all duration-150 flex items-center justify-center text-[11px] font-mono text-amber-200 overflow-hidden whitespace-nowrap"
                title={`Epistemic Ignorance / Unexplained Dark Matter Ω(C): ${ignPct}%`}
              >
                {ignPct >= 14 ? `Ignorance Ω ${ignPct.toFixed(1)}%` : ''}
              </div>
              <div
                style={{ width: `${disbeliefPct}%` }}
                className="bg-rose-950/60 transition-all duration-150 flex items-center justify-center text-[11px] font-mono text-rose-300 overflow-hidden whitespace-nowrap"
                title={`Refuted / Disbelief Mass (1 - Pl(C)): ${disbeliefPct}%`}
              >
                {disbeliefPct >= 15 ? `Refuted ${disbeliefPct.toFixed(1)}%` : ''}
              </div>
            </div>
          </div>

          {/* Mathematical Robustness Progress Bar (epistemic_confidence_score) */}
          <EpistemicConfidenceProgressBar
            score={activeInput.epistemic_confidence_score}
            recordId={activeInput.id}
            variant="detailed"
          />

          {/* Mathematical Verdict & EU AI Act Legal Surface */}
          <div className="pt-3 border-t border-slate-800/80 flex flex-col lg:flex-row lg:items-center justify-between gap-4 text-xs">
            <p className="font-mono text-slate-200 leading-relaxed">
              {compiled.mathematicalVerdict}
            </p>
            <div className="flex flex-wrap items-center gap-3 font-mono shrink-0">
              <span
                className={
                  compiled.l3Metrics.euAiActCompliance.article12TamperEvidentLogs
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {compiled.l3Metrics.euAiActCompliance.article12TamperEvidentLogs ? '●' : '✖'} Art.12 Logs
              </span>
              <span aria-hidden="true" className="text-slate-600">·</span>
              <span
                className={
                  compiled.l3Metrics.euAiActCompliance.article14HumanOversightGate
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {compiled.l3Metrics.euAiActCompliance.article14HumanOversightGate ? '●' : '✖'} Art.14 Oversight
              </span>
              <span aria-hidden="true" className="text-slate-600">·</span>
              <span
                className={
                  compiled.l3Metrics.euAiActCompliance.article86MeaningfulExplanation
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {compiled.l3Metrics.euAiActCompliance.article86MeaningfulExplanation ? '●' : '✖'} Art.86 Explanation
              </span>
            </div>
          </div>
        </div>

        {/* Interactive D3.js Cross-Layer Knowledge Graph (L1 -> L2/L3 -> L4) */}
        <CrossLayerKnowledgeGraph
          compiled={compiled}
          selectedL4NodeId={selectedMapNodeId}
          onSelectL4NodeId={setSelectedMapNodeId}
        />

        {/* 4-Layer Evidence Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* LAYER 1: MODEL INTERNALS */}
          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                    Layer 1 · Model Internals (Theorem 3)
                  </span>
                  <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
                    Mechanistic Circuit Attribution & Dark-Matter Bound
                  </h2>
                </div>
                <span className="text-xs font-mono text-slate-400 tabular-nums">
                  {activeInput.l1.modelFamily}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 bg-[#090D15] p-3 rounded border border-slate-800/70">
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Explained Circuit</div>
                  <div className="text-lg font-bold font-mono text-slate-100 tabular-nums">
                    {(compiled.l1Metrics.explainedCircuitCoverage * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Dark Matter ε_dark</div>
                  <div className="text-lg font-bold font-mono text-amber-300 tabular-nums">
                    {(compiled.l1Metrics.darkMatterResidual * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">L1 Belief Warrant</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 tabular-nums">
                    {(compiled.l1Metrics.mechanisticBeliefWarrant * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {activeInput.l1.accessMode === 'api-black-box' ? (
                <div className="p-3.5 rounded bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200 space-y-1">
                  <div className="font-semibold font-mono">
                    ▲ Closed-API Deployment Detected — Zero Weight Access
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    Per Anthropic’s blind auditing game (3/4 success with weights vs. 0/4 API-only), Aletheia refuses to fabricate mechanistic certainty for black-box endpoints. Dark-matter residual is locked at 100.0%.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-xs font-mono text-slate-400 flex justify-between">
                    <span>Extracted SAE / Transcoder / NLA Features</span>
                    <span className="tabular-nums">
                      KL Bound: {compiled.l1Metrics.klReplacementBoundBits.toFixed(2)} bits
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-mono">
                          <th className="py-1.5 pr-2">Feature ID</th>
                          <th className="py-1.5 px-2">Interpreted Concept</th>
                          <th className="py-1.5 px-2 text-right">Act</th>
                          <th className="py-1.5 pl-2 text-right">do(z=0)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {activeInput.l1.activeFeatures.map((feat) => (
                          <tr key={feat.id} className="hover:bg-slate-900/40">
                            <td className="py-2 pr-2 font-mono text-cyan-300 whitespace-nowrap">
                              {feat.id}
                            </td>
                            <td className="py-2 px-2 text-slate-200">{feat.label}</td>
                            <td className="py-2 px-2 text-right font-mono tabular-nums text-slate-300">
                              {feat.activation.toFixed(2)}
                            </td>
                            <td className="py-2 pl-2 text-right font-mono tabular-nums text-emerald-400">
                              {feat.causalEffect.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-slate-800/70 text-xs font-mono text-slate-400 flex justify-between">
              <span>Status: {compiled.l1Metrics.statusLabel}</span>
              <span className="tabular-nums">
                Pl Cap: {(compiled.l1Metrics.mechanisticPlausibilityCap * 100).toFixed(0)}%
              </span>
            </div>
          </article>

          {/* LAYER 2: STATED REASONING */}
          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                    Layer 2 · Stated Reasoning (Theorem 1)
                  </span>
                  <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
                    Asymmetric CoT Monitor & Confession Honesty Stack
                  </h2>
                </div>
                <span className="text-xs font-mono text-slate-400 tabular-nums">
                  Faithfulness Baseline: {(activeInput.l2.empiricalFaithfulnessBaseline * 100).toFixed(0)}%
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 bg-[#090D15] p-3 rounded border border-slate-800/70">
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Self-Report ΔBel⁺</div>
                  <div className="text-lg font-bold font-mono text-slate-200 tabular-nums">
                    +0.0% (Invariant)
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Pl Multiplier Λ⁻</div>
                  <div className="text-lg font-bold font-mono text-cyan-300 tabular-nums">
                    {(compiled.l2Metrics.incriminationMultiplier * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Honesty Stack Cov</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 tabular-nums">
                    {(compiled.l2Metrics.honestyStackCoverage * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="p-3 rounded bg-[#090D15] border border-slate-800/80">
                  <div className="flex items-center justify-between font-mono text-slate-400 mb-1">
                    <span>Stated Chain-of-Thought Scratchpad</span>
                    <span className="tabular-nums">
                      Monitorability μ={(activeInput.l2.cotMonitorabilityIndex * 100).toFixed(0)}% · Verdict: {activeInput.l2.cotVerdict}
                    </span>
                  </div>
                  <p className="text-slate-300 font-mono leading-relaxed">
                    “{activeInput.l2.statedCotExcerpt}”
                  </p>
                </div>

                <div className="p-3 rounded bg-[#090D15] border border-slate-800/80">
                  <div className="flex items-center justify-between font-mono text-slate-400 mb-1">
                    <span>Post-Hoc Confession Channel (74.3% Known-Violation Recall)</span>
                    <span
                      className={
                        activeInput.l2.confessionStatus === 'confessed-violation'
                          ? 'text-rose-400 font-semibold'
                          : 'text-emerald-400'
                      }
                    >
                      {activeInput.l2.confessionStatus}
                    </span>
                  </div>
                  <p className="text-slate-300 font-mono leading-relaxed">
                    “{activeInput.l2.confessionExcerpt}”
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/70 text-xs font-mono text-slate-400 flex justify-between">
              <span>{compiled.l2Metrics.asymmetryVerdict}</span>
              <span className="tabular-nums">
                Blindspot: {(compiled.l2Metrics.jointBlindspotProbability * 100).toFixed(1)}%
              </span>
            </div>
          </article>
        </div>

        {/* LAYER 3: ACTION PROVENANCE GATE */}
        <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                Layer 3 · Action Provenance & EU AI Act Art. 12 Gate (Theorem 2)
              </span>
              <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
                Fencing-Token Merkle Witness vs. Agent Self-Report Audit
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
              <span>Workflow: {activeInput.l3.workflowId}</span>
              <span aria-hidden="true">·</span>
              <span className="text-cyan-300">Merkle Root: {compiled.l3Metrics.merkleRootHex}</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-mono">
                  <th className="py-2 pr-3">Fencing τ_k</th>
                  <th className="py-2 px-3">Authority Principal & Scope</th>
                  <th className="py-2 px-3">Agent Verbal Self-Report (Untrusted L2)</th>
                  <th className="py-2 px-3">Kernel-Verified State Diff ΔS (Trusted L3)</th>
                  <th className="py-2 pl-3 text-right">Witness Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {activeInput.l3.steps.map((step) => (
                  <tr key={step.stepIndex} className="hover:bg-slate-900/40">
                    <td className="py-2.5 pr-3 font-mono tabular-nums text-cyan-300 whitespace-nowrap">
                      #{step.fencingToken}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-mono text-slate-200">{step.authorityPrincipal}</div>
                      <div className="font-mono text-[11px] text-slate-400">{step.instructionScope}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">{step.agentSelfReport}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-200">
                      <div>{step.verifiedStateDiff}</div>
                      <div className="text-[11px] text-slate-400 tabular-nums">
                        {step.preStateHash} → {step.postStateHash}
                      </div>
                    </td>
                    <td className="py-2.5 pl-3 text-right font-mono whitespace-nowrap">
                      {step.stateMatchesSelfReport ? (
                        <span className="text-emerald-400">● Verified Match</span>
                      ) : (
                        <span className="text-rose-400 font-semibold">✖ Silent Misreport</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        {/* LAYER 4: HUMAN COMPREHENSION & MOSHKOVITZ MENTAL MAP */}
        <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                Layer 4 · Human Comprehension & Correspondence Bisimulation (Theorem 4)
              </span>
              <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
                Three-Object Separation & Moshkovitz Mental-Map Bottleneck Decomposition
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-300 tabular-nums">
              <span>Raw Size: {activeInput.l4.rawArtifactLines.toLocaleString()} lines</span>
              <span aria-hidden="true">·</span>
              <span>Compression: {compiled.l4Metrics.compressionRatio}:1</span>
              <span aria-hidden="true">·</span>
              <span>Correspondence: {(compiled.l4Metrics.correspondenceScore * 100).toFixed(1)}%</span>
            </div>
          </div>

          {/* Three Conflated Objects Audit (arXiv:2608.14673v3) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="p-3.5 rounded bg-[#090D15] border border-slate-800/80">
              <div className="text-[11px] font-mono uppercase text-slate-400 mb-1">
                1. Advertised Headline Claim (H_adv)
              </div>
              <div className="text-xs text-slate-200 font-medium leading-relaxed">
                {activeInput.l4.advertisedHeadline}
              </div>
            </div>
            <div className="p-3.5 rounded bg-[#090D15] border border-slate-800/80">
              <div className="text-[11px] font-mono uppercase text-slate-400 mb-1">
                2. Informal Specification (H_inf)
              </div>
              <div className="text-xs text-slate-200 leading-relaxed">
                {activeInput.l4.informalClaim}
              </div>
            </div>
            <div className="p-3.5 rounded bg-[#090D15] border border-slate-800/80">
              <div className="flex items-center justify-between text-[11px] font-mono uppercase text-slate-400 mb-1">
                <span>3. Kernel-Checked Proposition (P_formal)</span>
                <span className="text-cyan-300">{activeInput.l4.formalVerifierStatus}</span>
              </div>
              <code className="text-xs text-cyan-200 font-mono break-words leading-relaxed block">
                {activeInput.l4.formalKernelProposition}
              </code>
            </div>
          </div>

          {/* Interactive Mental-Map Bottleneck DAG & Durability Pillars */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-7 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                <span>Interactive Mental-Map Bottleneck Nodes (Click node to inspect)</span>
                <span>
                  Weakest Link: <strong className="text-amber-300">{compiled.l4Metrics.weakestBottleneckNode.id}</strong> ({(compiled.l4Metrics.weakestBottleneckNode.belief * 100).toFixed(0)}%)
                </span>
              </div>

              <div className="space-y-2" role="listbox" aria-label="Mental Map Bottleneck Nodes">
                {activeInput.l4.mentalMapNodes.map((node, idx) => {
                  const isWeakest = node.id === compiled.l4Metrics.weakestBottleneckNode.id;
                  const isFocused = activeMapNode?.id === node.id;
                  return (
                    <button
                      key={node.id}
                      type="button"
                      role="option"
                      aria-selected={isFocused}
                      onClick={() => setSelectedMapNodeId(node.id)}
                      className={`w-full text-left p-3 rounded border transition-colors ${
                        isFocused
                          ? 'bg-[#131C2E] border-cyan-400'
                          : 'bg-[#090D15] border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono mb-1">
                        <span className="text-slate-300">
                          {idx + 1}. {node.id} · {node.role}
                          {isWeakest ? ' · [Weakest Bottleneck]' : ''}
                        </span>
                        <span
                          className={`tabular-nums ${
                            node.humanReconstructible ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {node.humanReconstructible ? '● Reconstructible' : '✖ Opaque to Humans'} · Bel {(node.nodeBelief * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-slate-100 font-display">
                        {node.title}
                      </div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                        {node.summary}
                      </p>
                      <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 mt-1.5 tabular-nums">
                        <span>Compresses {node.rawSpanCount.toLocaleString()} raw lines</span>
                        {node.dependsOn.length > 0 && (
                          <>
                            <span aria-hidden="true">·</span>
                            <span>Depends on: {node.dependsOn.join(', ')}</span>
                          </>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right sub-column: Selected Node Deep Dive + 3 Durability Pillars */}
            <div className="lg:col-span-5 space-y-4">
              {activeMapNode && (
                <div className="p-4 rounded bg-[#090D15] border border-slate-800 space-y-2">
                  <div className="text-xs font-mono text-cyan-400 uppercase">
                    Selected Node Audit · {activeMapNode.id}
                  </div>
                  <div className="text-sm font-bold text-slate-100 font-display">
                    {activeMapNode.title}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {activeMapNode.summary}
                  </p>
                  <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs font-mono">
                    <div>
                      <span className="text-slate-400 block">Compressed Span</span>
                      <span className="text-slate-100 tabular-nums">
                        {activeMapNode.rawSpanCount.toLocaleString()} lines
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Node Warrant</span>
                      <span className="text-emerald-400 tabular-nums">
                        {(activeMapNode.nodeBelief * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div className="p-4 rounded bg-[#090D15] border border-slate-800 space-y-3">
                <div className="text-xs font-mono uppercase text-slate-400">
                  Human Durability Test (arXiv:2610.36116v1)
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-300">1. Comprehension (Key Idea Extraction)</span>
                    <span className="tabular-nums text-cyan-300">
                      {(compiled.l4Metrics.durabilityPillars.comprehension * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-900 rounded overflow-hidden">
                    <div
                      className="h-full bg-cyan-400"
                      style={{ width: `${compiled.l4Metrics.durabilityPillars.comprehension * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-300">2. Critical Assessment (Weakest-Link Audit)</span>
                    <span className="tabular-nums text-cyan-300">
                      {(compiled.l4Metrics.durabilityPillars.criticalAssessment * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-900 rounded overflow-hidden">
                    <div
                      className="h-full bg-cyan-400"
                      style={{ width: `${compiled.l4Metrics.durabilityPillars.criticalAssessment * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-300">3. Capability Retention (Human Reconstructibility)</span>
                    <span className="tabular-nums text-emerald-400">
                      {(compiled.l4Metrics.durabilityPillars.capabilityRetention * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-900 rounded overflow-hidden">
                    <div
                      className="h-full bg-emerald-400"
                      style={{ width: `${compiled.l4Metrics.durabilityPillars.capabilityRetention * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
};
