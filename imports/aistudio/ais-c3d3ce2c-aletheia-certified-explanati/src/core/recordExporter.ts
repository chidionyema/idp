/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Aletheia External Audit Exporter (JSON Manifest & Native Vector PDF 1.4 Generator)
 * Pure TypeScript module with zero DOM dependencies so both JSON and PDF generation
 * are deterministically verifiable via unit tests and work inside sandboxed iFrames
 * without window.open().
 */

import {
  computeDeterministicHash,
  type CertifiedExplanationRecord,
} from './epistemicCalculus';
import { buildCrossLayerKnowledgeGraph } from './knowledgeGraph';

export interface AletheiaExternalAuditBundle {
  schema: 'aletheia.explanation-record.v1';
  exportedAt: string;
  manifestHeader: {
    recordId: string;
    title: string;
    domain: string;
    recordTimestamp: string;
    evidenceGrade: string;
    certificateHash: string;
    merkleRootHex: string;
    bundleIntegrityChecksum: string;
    mathematicalVerdict: string;
  };
  epistemicInterval: {
    beliefLowerBound: number;
    plausibilityUpperBound: number;
    ignoranceWidth: number;
  };
  euAiActCompliance: {
    riskTier: string;
    retentionMonthsConfigured: number;
    article12TamperEvidentLogs: boolean;
    article14HumanOversightGate: boolean;
    article86MeaningfulExplanation: boolean;
    overallCompliant: boolean;
  };
  layerMetrics: {
    l1: CertifiedExplanationRecord['l1Metrics'];
    l2: CertifiedExplanationRecord['l2Metrics'];
    l3: CertifiedExplanationRecord['l3Metrics'];
    l4: CertifiedExplanationRecord['l4Metrics'];
    knowledgeGraphSummary: ReturnType<typeof buildCrossLayerKnowledgeGraph>['summary'];
  };
  record: CertifiedExplanationRecord['input'];
}

/**
 * Builds the canonical JSON audit bundle with a deterministic integrity checksum.
 */
export function buildExplanationRecordAuditBundle(
  compiled: CertifiedExplanationRecord,
  exportedAt = '2026-11-04T17:25:00Z'
): AletheiaExternalAuditBundle {
  const graph = buildCrossLayerKnowledgeGraph(compiled);

  const coreDigestPayload = JSON.stringify({
    id: compiled.input.id,
    cert: compiled.certificateHash,
    merkle: compiled.l3Metrics.merkleRootHex,
    bel: compiled.epistemicInterval.beliefLowerBound,
    pl: compiled.epistemicInterval.plausibilityUpperBound,
    l1Cov: compiled.l1Metrics.explainedCircuitCoverage,
    l4Corr: compiled.l4Metrics.correspondenceScore,
  });

  const bundleIntegrityChecksum = computeDeterministicHash(
    `AUDIT_BUNDLE::${coreDigestPayload}`
  );

  return {
    schema: 'aletheia.explanation-record.v1',
    exportedAt,
    manifestHeader: {
      recordId: compiled.input.id,
      title: compiled.input.title,
      domain: compiled.input.domain,
      recordTimestamp: compiled.input.timestamp,
      evidenceGrade: compiled.evidenceGrade,
      certificateHash: compiled.certificateHash,
      merkleRootHex: compiled.l3Metrics.merkleRootHex,
      bundleIntegrityChecksum,
      mathematicalVerdict: compiled.mathematicalVerdict,
    },
    epistemicInterval: compiled.epistemicInterval,
    euAiActCompliance: {
      riskTier: compiled.input.l3.euAiActRiskTier,
      retentionMonthsConfigured: compiled.input.l3.retentionMonthsConfigured,
      ...compiled.l3Metrics.euAiActCompliance,
    },
    layerMetrics: {
      l1: compiled.l1Metrics,
      l2: compiled.l2Metrics,
      l3: compiled.l3Metrics,
      l4: compiled.l4Metrics,
      knowledgeGraphSummary: graph.summary,
    },
    record: compiled.input,
  };
}

/**
 * Serializes the canonical JSON audit bundle with 2-space indentation.
 */
export function serializeExplanationRecordJson(
  compiled: CertifiedExplanationRecord,
  exportedAt = '2026-11-04T17:25:00Z'
): string {
  const bundle = buildExplanationRecordAuditBundle(compiled, exportedAt);
  return JSON.stringify(bundle, null, 2);
}

/**
 * Escapes ASCII text for PDF string literals (...)
 */
function sanitizePdfText(input: string): string {
  return input
    .replace(/—/g, '--')
    .replace(/–/g, '-')
    .replace(/·/g, '|')
    .replace(/→/g, '->')
    .replace(/←/g, '<-')
    .replace(/≥/g, '>=')
    .replace(/≤/g, '<=')
    .replace(/≠/g, '!=')
    .replace(/≡/g, '==')
    .replace(/⊢/g, '|-')
    .replace(/⊥/g, 'FALSE')
    .replace(/∧/g, 'AND')
    .replace(/∨/g, 'OR')
    .replace(/¬/g, 'NOT ')
    .replace(/∃/g, 'EXISTS ')
    .replace(/∀/g, 'FORALL ')
    .replace(/∈/g, ' in ')
    .replace(/ℝ/g, 'R')
    .replace(/ℕ/g, 'N')
    .replace(/ε/g, 'eps')
    .replace(/δ/g, 'delta')
    .replace(/ρ/g, 'rho')
    .replace(/τ/g, 'tau')
    .replace(/μ/g, 'mu')
    .replace(/φ/g, 'phi')
    .replace(/Ω/g, 'Omega')
    .replace(/Δ/g, 'Delta')
    .replace(/Λ/g, 'Lambda')
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/[^\x20-\x7E]/g, '')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');
}

function wrapTextLines(text: string, maxChars: number): string[] {
  const words = sanitizePdfText(text).split(/\s+/).filter(Boolean);
  if (words.length === 0) return [''];
  const lines: string[] = [];
  let current = words[0];
  for (let i = 1; i < words.length; i++) {
    const word = words[i];
    if (current.length + 1 + word.length <= maxChars) {
      current += ` ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
  }
  lines.push(current);
  return lines;
}

/**
 * Generates a complete, standards-compliant PDF 1.4 document (Uint8Array) containing
 * the L1-L4 Certified Explanation Record, Epistemic Interval Bar, Merkle Provenance Log,
 * and EU AI Act Art. 12/14/86 Audit Attestation.
 */
export function generateExplanationRecordPdfBytes(
  compiled: CertifiedExplanationRecord,
  exportedAt = '2026-11-04T17:25:00Z'
): Uint8Array {
  const bundle = buildExplanationRecordAuditBundle(compiled, exportedAt);
  const { input, l1Metrics, l2Metrics, l3Metrics, l4Metrics, epistemicInterval } = compiled;

  const ops: string[] = [];

  // Page dimensions: Letter 612 x 792 pt
  // Dark header banner
  ops.push('0.04 0.06 0.10 rg');
  ops.push('36 706 540 56 re f');

  // Header text
  ops.push('BT /F2 13 Tf 0.13 0.83 0.93 rg 48 742 Td (ALETHEIA CERTIFIED EXPLANATION RECORD // EXTERNAL AUDIT DOSSIER) Tj ET');
  ops.push(
    `BT /F3 8.5 Tf 0.82 0.86 0.92 rg 48 726 Td (${sanitizePdfText(
      `ID: ${input.id}  |  GRADE: ${compiled.evidenceGrade}  |  CERT: ${compiled.certificateHash}`
    )}) Tj ET`
  );
  ops.push(
    `BT /F3 8 Tf 0.60 0.66 0.75 rg 48 713 Td (${sanitizePdfText(
      `MERKLE ROOT: ${l3Metrics.merkleRootHex}  |  CHECKSUM: ${bundle.manifestHeader.bundleIntegrityChecksum}  |  EXPORTED: ${exportedAt}`
    )}) Tj ET`
  );

  let y = 686;

  const drawText = (
    text: string,
    x: number,
    yPos: number,
    font: 'F1' | 'F2' | 'F3' = 'F1',
    size = 9,
    rgb: [number, number, number] = [0.1, 0.14, 0.2]
  ) => {
    ops.push(
      `BT /${font} ${size} Tf ${rgb[0].toFixed(2)} ${rgb[1].toFixed(2)} ${rgb[2].toFixed(2)} rg ${x} ${yPos} Td (${sanitizePdfText(
        text
      )}) Tj ET`
    );
  };

  const drawRule = (yPos: number) => {
    ops.push('0.82 0.85 0.90 RG 0.75 w');
    ops.push(`36 ${yPos} m 576 ${yPos} l S`);
  };

  // Title & Summary
  drawText(input.title, 36, y, 'F2', 12, [0.05, 0.08, 0.15]);
  y -= 14;
  for (const line of wrapTextLines(input.summary, 96)) {
    drawText(line, 36, y, 'F1', 8.5, [0.25, 0.3, 0.38]);
    y -= 11;
  }

  y -= 4;
  drawRule(y);
  y -= 16;

  // Section 0: Epistemic Interval & EU AI Act Status
  drawText(
    '00. DEMPSTER-SHAFER BOUNDED EPISTEMIC CERTIFICATE & EU AI ACT COMPLIANCE',
    36,
    y,
    'F2',
    9.5,
    [0.05, 0.35, 0.55]
  );
  y -= 14;

  const belPct = (epistemicInterval.beliefLowerBound * 100).toFixed(1);
  const plPct = (epistemicInterval.plausibilityUpperBound * 100).toFixed(1);
  const ignPct = (epistemicInterval.ignoranceWidth * 100).toFixed(1);

  drawText(
    `Warranted Belief Bel(C): ${belPct}%   |   Upper Plausibility Pl(C): ${plPct}%   |   Ignorance Width Omega(C): ${ignPct}%`,
    36,
    y,
    'F3',
    8.5,
    [0.08, 0.12, 0.18]
  );
  y -= 16;

  // Vector Epistemic Interval Bar (width = 540pt)
  const barWidth = 540;
  const belW = Math.max(0, Math.round(barWidth * epistemicInterval.beliefLowerBound));
  const ignW = Math.max(0, Math.round(barWidth * epistemicInterval.ignoranceWidth));
  const refW = Math.max(0, barWidth - belW - ignW);

  // Bel(C) green bar
  if (belW > 0) {
    ops.push(`0.09 0.64 0.45 rg 36 ${y} ${belW} 10 re f`);
  }
  // Ignorance amber bar
  if (ignW > 0) {
    ops.push(`0.92 0.62 0.08 rg ${36 + belW} ${y} ${ignW} 10 re f`);
  }
  // Refuted rose bar
  if (refW > 0) {
    ops.push(`0.85 0.22 0.32 rg ${36 + belW + ignW} ${y} ${refW} 10 re f`);
  }
  y -= 13;

  const c12 = l3Metrics.euAiActCompliance.article12TamperEvidentLogs ? 'PASS' : 'FAIL';
  const c14 = l3Metrics.euAiActCompliance.article14HumanOversightGate ? 'PASS' : 'FAIL';
  const c86 = l3Metrics.euAiActCompliance.article86MeaningfulExplanation ? 'PASS' : 'FAIL';
  drawText(
    `EU AI Act Audit -> Art.12 Tamper-Evident Logs: [${c12}]  |  Art.14 Oversight Gate: [${c14}]  |  Art.86 Meaningful Explanation: [${c86}]`,
    36,
    y,
    'F3',
    8,
    [0.15, 0.2, 0.28]
  );
  y -= 12;

  for (const line of wrapTextLines(`Verdict: ${compiled.mathematicalVerdict}`, 96)) {
    drawText(line, 36, y, 'F1', 8.5, [0.15, 0.2, 0.28]);
    y -= 11;
  }

  y -= 4;
  drawRule(y);
  y -= 15;

  // Section 1: Layer 1 Mechanistic Internals
  drawText(
    `01. LAYER 1 (MODEL INTERNALS - THEOREM 3) // ${input.l1.modelFamily} (${input.l1.accessMode})`,
    36,
    y,
    'F2',
    9.5,
    [0.05, 0.35, 0.55]
  );
  y -= 13;
  drawText(
    `Explained Circuit Coverage: ${(l1Metrics.explainedCircuitCoverage * 100).toFixed(1)}%  |  Dark-Matter Residual (eps_dark): ${(l1Metrics.darkMatterResidual * 100).toFixed(1)}%  |  L1 Warrant: ${(l1Metrics.mechanisticBeliefWarrant * 100).toFixed(1)}%`,
    36,
    y,
    'F3',
    8,
    [0.12, 0.16, 0.22]
  );
  y -= 12;

  if (input.l1.activeFeatures.length === 0) {
    drawText(
      'No open-weights SAE/Transcoder features available (API-Black-Box mode: 100% Dark-Matter Residual enforced).',
      44,
      y,
      'F1',
      8,
      [0.45, 0.25, 0.05]
    );
    y -= 12;
  } else {
    for (const feat of input.l1.activeFeatures.slice(0, 4)) {
      drawText(
        `- [${feat.id}] L${feat.layer} (${feat.category}): ${feat.label} | Act=${feat.activation.toFixed(2)}, do(z=0)=${feat.causalEffect.toFixed(2)}`,
        44,
        y,
        'F3',
        7.5,
        [0.2, 0.25, 0.32]
      );
      y -= 10.5;
    }
  }

  y -= 3;
  drawRule(y);
  y -= 15;

  // Section 2: Layer 2 Stated Reasoning
  drawText(
    '02. LAYER 2 (STATED REASONING & CONFESSIONS - THEOREM 1 ASYMMETRY INVARIANT)',
    36,
    y,
    'F2',
    9.5,
    [0.05, 0.35, 0.55]
  );
  y -= 13;
  drawText(
    `Positive Self-Report Exoneration (Delta Bel+): +0.0% (Invariant)  |  Pl Multiplier: ${(l2Metrics.incriminationMultiplier * 100).toFixed(1)}%  |  Honesty Stack Cov: ${(l2Metrics.honestyStackCoverage * 100).toFixed(1)}%`,
    36,
    y,
    'F3',
    8,
    [0.12, 0.16, 0.22]
  );
  y -= 11;
  for (const line of wrapTextLines(`CoT (${input.l2.cotVerdict}): "${input.l2.statedCotExcerpt}"`, 96).slice(0, 2)) {
    drawText(line, 44, y, 'F1', 8, [0.25, 0.3, 0.38]);
    y -= 10.5;
  }
  for (const line of wrapTextLines(`Confession (${input.l2.confessionStatus}): "${input.l2.confessionExcerpt}"`, 96).slice(0, 2)) {
    drawText(line, 44, y, 'F1', 8, [0.25, 0.3, 0.38]);
    y -= 10.5;
  }

  y -= 3;
  drawRule(y);
  y -= 15;

  // Section 3: Layer 3 Action Provenance
  drawText(
    `03. LAYER 3 (CRYPTOGRAPHIC PROVENANCE GATE - THEOREM 2) // WORKFLOW: ${input.l3.workflowId}`,
    36,
    y,
    'F2',
    9.5,
    [0.05, 0.35, 0.55]
  );
  y -= 13;
  drawText(
    `Merkle Root: ${l3Metrics.merkleRootHex}  |  Fencing Monotonic: ${l3Metrics.fencingMonotonicityValid ? 'YES' : 'NO'}  |  Divergences: ${l3Metrics.selfReportDivergenceCount}`,
    36,
    y,
    'F3',
    8,
    [0.12, 0.16, 0.22]
  );
  y -= 11;

  for (const step of input.l3.steps.slice(0, 3)) {
    const matchTag = step.stateMatchesSelfReport ? 'MATCH' : 'MISMATCH';
    drawText(
      `#${step.fencingToken} [${matchTag}] ${step.authorityPrincipal} (${step.instructionScope})`,
      44,
      y,
      'F3',
      7.5,
      [0.15, 0.2, 0.28]
    );
    y -= 10;
    drawText(
      `   Kernel State Diff: ${step.verifiedStateDiff.slice(0, 88)} (${step.preStateHash} -> ${step.postStateHash})`,
      44,
      y,
      'F3',
      7.2,
      [0.3, 0.35, 0.42]
    );
    y -= 10.5;
  }

  y -= 3;
  drawRule(y);
  y -= 15;

  // Section 4: Layer 4 Human Comprehension & Mental Map
  drawText(
    '04. LAYER 4 (HUMAN COMPREHENSION, CORRESPONDENCE & MOSHKOVITZ MENTAL MAP - THEOREM 4)',
    36,
    y,
    'F2',
    9.5,
    [0.05, 0.35, 0.55]
  );
  y -= 13;
  drawText(
    `Correspondence: ${(l4Metrics.correspondenceScore * 100).toFixed(1)}%  |  Compression: ${l4Metrics.compressionRatio}:1  |  Comprehension: ${(l4Metrics.durabilityPillars.comprehension * 100).toFixed(1)}%  |  Retention: ${(l4Metrics.durabilityPillars.capabilityRetention * 100).toFixed(1)}%`,
    36,
    y,
    'F3',
    8,
    [0.12, 0.16, 0.22]
  );
  y -= 11;
  drawText(
    `Formal Proposition (${input.l4.formalVerifierStatus}): ${input.l4.formalKernelProposition.slice(0, 85)}`,
    44,
    y,
    'F3',
    7.5,
    [0.15, 0.25, 0.38]
  );
  y -= 11;

  for (const node of input.l4.mentalMapNodes.slice(0, 5)) {
    if (y < 52) break;
    const recTag = node.humanReconstructible ? 'Reconstructible' : 'Opaque';
    drawText(
      `- [${node.id}] ${node.title} (${recTag}, Bel ${(node.nodeBelief * 100).toFixed(0)}%, ${node.rawSpanCount} lines)`,
      44,
      y,
      'F3',
      7.5,
      [0.2, 0.25, 0.32]
    );
    y -= 10;
  }

  // Footer attestation
  ops.push('0.04 0.06 0.10 rg 36 24 540 18 re f');
  ops.push(
    `BT /F3 7.5 Tf 0.75 0.82 0.90 rg 44 30 Td (${sanitizePdfText(
      `SIGNED ALETHEIA AUDIT ARTIFACT  |  CERT ${compiled.certificateHash}  |  BUNDLE CHECKSUM ${bundle.manifestHeader.bundleIntegrityChecksum}`
    )}) Tj ET`
  );

  const contentStream = ops.join('\n');

  // Assemble PDF 1.4 objects with exact byte offsets
  const objects: string[] = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R >> >> /Contents 7 0 R >>\nendobj\n',
    '4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n',
    '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n',
    '6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n',
    `7 0 obj\n<< /Length ${contentStream.length} >>\nstream\n${contentStream}\nendstream\nendobj\n`,
  ];

  let pdfBody = '%PDF-1.4\n';
  const offsets: number[] = [];

  for (const obj of objects) {
    offsets.push(pdfBody.length);
    pdfBody += obj;
  }

  const xrefOffset = pdfBody.length;
  pdfBody += `xref\n0 ${objects.length + 1}\n`;
  pdfBody += '0000000000 65535 f \n';
  for (const offset of offsets) {
    pdfBody += `${offset.toString().padStart(10, '0')} 00000 n \n`;
  }

  pdfBody += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;

  const encoder = new TextEncoder();
  return encoder.encode(pdfBody);
}
