/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useMemo, useState } from 'react';
import type { CertifiedExplanationRecord } from '../core/epistemicCalculus';
import {
  buildExplanationRecordAuditBundle,
  generateExplanationRecordPdfBytes,
  serializeExplanationRecordJson,
} from '../core/recordExporter';

interface AuditExportModalProps {
  compiled: CertifiedExplanationRecord;
  onClose: () => void;
  onExportTriggered: (format: 'PDF' | 'JSON', filename: string, byteSize: number, checksum: string) => void;
}

export function triggerBrowserDownload(
  bytes: Uint8Array,
  filename: string,
  mimeType: string
): void {
  const blob = new Blob([new Uint8Array(bytes)], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const AuditExportModal: React.FC<AuditExportModalProps> = ({
  compiled,
  onClose,
  onExportTriggered,
}) => {
  const [activeTab, setActiveTab] = useState<'dossier-preview' | 'json-manifest'>('dossier-preview');
  const [copiedJson, setCopiedJson] = useState(false);

  const exportTimestamp = useMemo(() => new Date().toISOString(), []);

  const bundle = useMemo(
    () => buildExplanationRecordAuditBundle(compiled, exportTimestamp),
    [compiled, exportTimestamp]
  );

  const jsonString = useMemo(
    () => serializeExplanationRecordJson(compiled, exportTimestamp),
    [compiled, exportTimestamp]
  );

  const pdfBytes = useMemo(
    () => generateExplanationRecordPdfBytes(compiled, exportTimestamp),
    [compiled, exportTimestamp]
  );

  const handleDownloadPdf = () => {
    const filename = `${compiled.input.id.toLowerCase()}-l1-l4-audit-dossier.pdf`;
    triggerBrowserDownload(pdfBytes, filename, 'application/pdf');
    onExportTriggered('PDF', filename, pdfBytes.byteLength, bundle.manifestHeader.bundleIntegrityChecksum);
  };

  const handleDownloadJson = () => {
    const filename = `${compiled.input.id.toLowerCase()}-explanation-record.json`;
    const bytes = new TextEncoder().encode(jsonString);
    triggerBrowserDownload(bytes, filename, 'application/json');
    onExportTriggered('JSON', filename, bytes.byteLength, bundle.manifestHeader.bundleIntegrityChecksum);
  };

  const handleCopyJson = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(jsonString).catch(() => {});
    }
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-export-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto"
    >
      <div className="w-full max-w-4xl bg-[#0B0F19] border border-slate-700/90 rounded-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#070A10] border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
              External Auditor Export Package · Schema v1
            </div>
            <h2
              id="audit-export-dialog-title"
              className="text-lg font-bold text-slate-100 font-display mt-0.5"
            >
              Export L1–L4 Certified Explanation Record ({compiled.input.id})
            </h2>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleDownloadPdf}
              className="px-3.5 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors whitespace-nowrap cursor-pointer"
            >
              Download PDF Dossier ({(pdfBytes.byteLength / 1024).toFixed(1)} KB)
            </button>
            <button
              type="button"
              onClick={handleDownloadJson}
              className="px-3.5 py-2 text-xs font-semibold text-slate-100 bg-[#141C2E] border border-cyan-500/50 rounded-md hover:border-cyan-400 transition-colors whitespace-nowrap cursor-pointer"
            >
              Download JSON Bundle ({(jsonString.length / 1024).toFixed(1)} KB)
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close Export Modal"
              className="px-3 py-2 text-xs font-mono text-slate-400 hover:text-slate-100 border border-slate-800 rounded-md"
            >
              Close
            </button>
          </div>
        </div>

        {/* Sub-Navigation Bar */}
        <div className="px-6 py-2.5 bg-[#090D15] border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2" role="tablist" aria-label="Export Format Preview">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'dossier-preview'}
              onClick={() => setActiveTab('dossier-preview')}
              className={`px-3 py-1.5 font-mono rounded transition-colors ${
                activeTab === 'dossier-preview'
                  ? 'bg-slate-800 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              PDF Audit Dossier Preview
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'json-manifest'}
              onClick={() => setActiveTab('json-manifest')}
              className={`px-3 py-1.5 font-mono rounded transition-colors ${
                activeTab === 'json-manifest'
                  ? 'bg-slate-800 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Canonical JSON Manifest (aletheia.explanation-record.v1)
            </button>
          </div>

          <div className="font-mono text-slate-400 tabular-nums">
            Integrity Checksum: <span className="text-emerald-400">{bundle.manifestHeader.bundleIntegrityChecksum}</span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          {activeTab === 'dossier-preview' ? (
            <div className="bg-[#07090F] border border-slate-800 rounded-md p-6 space-y-5 font-mono">
              <div className="border-b border-slate-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div>
                  <div className="text-cyan-400 font-bold text-sm">
                    ALETHEIA CERTIFIED EXPLANATION RECORD // EXTERNAL AUDIT DOSSIER
                  </div>
                  <div className="text-slate-300 mt-1">
                    RECORD: {compiled.input.id} · DOMAIN: {compiled.input.domain} · GRADE: {compiled.evidenceGrade}
                  </div>
                </div>
                <div className="text-right text-slate-400 tabular-nums">
                  <div>CERT: {compiled.certificateHash}</div>
                  <div>MERKLE: {compiled.l3Metrics.merkleRootHex}</div>
                </div>
              </div>

              {/* Epistemic Interval & Legal Compliance Attestation */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-[#0C111D] p-3.5 rounded border border-slate-800/90 tabular-nums">
                <div>
                  <div className="text-slate-400 text-[11px]">WARRANTED BELIEF Bel(C)</div>
                  <div className="text-base font-bold text-emerald-400">
                    {(compiled.epistemicInterval.beliefLowerBound * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-[11px]">UPPER PLAUSIBILITY Pl(C)</div>
                  <div className="text-base font-bold text-cyan-300">
                    {(compiled.epistemicInterval.plausibilityUpperBound * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-[11px]">IGNORANCE RESIDUAL Ω(C)</div>
                  <div className="text-base font-bold text-amber-300">
                    {(compiled.epistemicInterval.ignoranceWidth * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-[11px]">EU AI ACT ART. 12/14/86</div>
                  <div
                    className={`text-base font-bold ${
                      compiled.l3Metrics.euAiActCompliance.overallCompliant
                        ? 'text-emerald-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {compiled.l3Metrics.euAiActCompliance.overallCompliant
                      ? '● PASS (COMPLIANT)'
                      : '✖ FAIL (NON-COMPLIANT)'}
                  </div>
                </div>
              </div>

              {/* 4-Layer Summary Table */}
              <div className="space-y-3">
                <div className="text-slate-300 font-semibold">
                  LAYER-BY-LAYER MATHEMATICAL ATTESTATION SUMMARY
                </div>
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2 pr-3">Layer</th>
                      <th className="py-2 px-3">Governing Theorem</th>
                      <th className="py-2 px-3">Measured Metrics</th>
                      <th className="py-2 pl-3 text-right">Audit Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 tabular-nums">
                    <tr>
                      <td className="py-2.5 pr-3 text-cyan-300">L1 · Internals</td>
                      <td className="py-2.5 px-3 text-slate-300">Theorem 3 (Dark-Matter Bound)</td>
                      <td className="py-2.5 px-3 text-slate-200">
                        Circuit Cov: {(compiled.l1Metrics.explainedCircuitCoverage * 100).toFixed(1)}% · ε_dark: {(compiled.l1Metrics.darkMatterResidual * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 pl-3 text-right text-slate-200">
                        {compiled.input.l1.accessMode}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2.5 pr-3 text-cyan-300">L2 · Reasoning</td>
                      <td className="py-2.5 px-3 text-slate-300">Theorem 1 (CoT Asymmetry)</td>
                      <td className="py-2.5 px-3 text-slate-200">
                        ΔBel⁺: 0.0% · Λ⁻: {(compiled.l2Metrics.incriminationMultiplier * 100).toFixed(1)}% · Stack Cov: {(compiled.l2Metrics.honestyStackCoverage * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 pl-3 text-right text-slate-200">
                        {compiled.input.l2.confessionStatus}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2.5 pr-3 text-cyan-300">L3 · Provenance</td>
                      <td className="py-2.5 px-3 text-slate-300">Theorem 2 (Merkle Fencing Gate)</td>
                      <td className="py-2.5 px-3 text-slate-200">
                        Integrity: {(compiled.l3Metrics.provenanceIntegrity * 100).toFixed(1)}% · Divergences: {compiled.l3Metrics.selfReportDivergenceCount}
                      </td>
                      <td className="py-2.5 pl-3 text-right text-slate-200">
                        {compiled.l3Metrics.euAiActCompliance.article12TamperEvidentLogs
                          ? 'Art.12 Verified'
                          : 'Art.12 Breach'}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2.5 pr-3 text-cyan-300">L4 · Meaning</td>
                      <td className="py-2.5 px-3 text-slate-300">Theorem 4 (Correspondence &amp; Map)</td>
                      <td className="py-2.5 px-3 text-slate-200">
                        Corr: {(compiled.l4Metrics.correspondenceScore * 100).toFixed(1)}% · Retention: {(compiled.l4Metrics.durabilityPillars.capabilityRetention * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 pl-3 text-right text-slate-200">
                        Weakest: {compiled.l4Metrics.weakestBottleneckNode.id}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-slate-400">
                  Deterministic JSON Schema (`aletheia.explanation-record.v1`)
                </span>
                <button
                  type="button"
                  onClick={handleCopyJson}
                  className="px-3 py-1.5 text-xs font-mono bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded transition-colors"
                >
                  {copiedJson ? 'Copied JSON to Clipboard' : 'Copy Raw JSON'}
                </button>
              </div>
              <pre className="p-4 rounded bg-[#06080E] border border-slate-800 text-[11px] font-mono text-slate-200 overflow-x-auto max-h-96 leading-relaxed">
                {jsonString}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
