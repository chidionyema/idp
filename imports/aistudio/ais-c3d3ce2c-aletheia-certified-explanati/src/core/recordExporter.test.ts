import test from 'node:test';
import assert from 'node:assert/strict';
import { compileExplanationRecord } from './epistemicCalculus';
import {
  buildExplanationRecordAuditBundle,
  generateExplanationRecordPdfBytes,
  serializeExplanationRecordJson,
} from './recordExporter';
import { INITIAL_SCENARIOS } from './scenarios';

test('serializeExplanationRecordJson emits complete L1-L4 audit bundle with deterministic integrity checksum', () => {
  const compiled = compileExplanationRecord(INITIAL_SCENARIOS[0]);
  const jsonString = serializeExplanationRecordJson(compiled, '2026-11-04T17:25:00Z');
  const parsed = JSON.parse(jsonString);

  assert.equal(parsed.schema, 'aletheia.explanation-record.v1');
  assert.equal(parsed.manifestHeader.recordId, 'REC-2026-UGC-001');
  assert.equal(parsed.manifestHeader.certificateHash, compiled.certificateHash);
  assert.equal(parsed.manifestHeader.merkleRootHex, compiled.l3Metrics.merkleRootHex);
  assert.ok(parsed.manifestHeader.bundleIntegrityChecksum.startsWith('0x'));
  assert.equal(parsed.euAiActCompliance.overallCompliant, true);
  assert.equal(parsed.layerMetrics.knowledgeGraphSummary.totalNodes, 12);
});

test('generateExplanationRecordPdfBytes produces a valid PDF 1.4 binary containing certificate hash, Merkle root, and L1-L4 audit sections', () => {
  const compiled = compileExplanationRecord(INITIAL_SCENARIOS[0]);
  const bundle = buildExplanationRecordAuditBundle(compiled, '2026-11-04T17:25:00Z');
  const pdfBytes = generateExplanationRecordPdfBytes(compiled, '2026-11-04T17:25:00Z');

  assert.ok(pdfBytes instanceof Uint8Array);
  assert.ok(pdfBytes.byteLength > 1500, `Expected PDF > 1500 bytes, got ${pdfBytes.byteLength}`);

  const pdfText = new TextDecoder().decode(pdfBytes);
  assert.ok(pdfText.startsWith('%PDF-1.4\n'), 'PDF must start with %PDF-1.4 header');
  assert.ok(pdfText.endsWith('%%EOF\n'), 'PDF must end with %%EOF trailer');
  assert.ok(pdfText.includes(compiled.certificateHash), 'PDF must embed certificateHash');
  assert.ok(pdfText.includes(compiled.l3Metrics.merkleRootHex), 'PDF must embed L3 Merkle root');
  assert.ok(
    pdfText.includes(bundle.manifestHeader.bundleIntegrityChecksum),
    'PDF must embed bundle integrity checksum'
  );
  assert.ok(
    pdfText.includes('01. LAYER 1 \\(MODEL INTERNALS - THEOREM 3\\)'),
    'PDF stream must contain escaped Layer 1 section header'
  );
  assert.ok(
    pdfText.includes('04. LAYER 4 \\(HUMAN COMPREHENSION'),
    'PDF stream must contain escaped Layer 4 section header'
  );
});
