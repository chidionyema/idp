import test from 'node:test';
import assert from 'node:assert/strict';
import { compileExplanationRecord } from './epistemicCalculus';
import { buildCrossLayerKnowledgeGraph } from './knowledgeGraph';
import { INITIAL_SCENARIOS } from './scenarios';

test('buildCrossLayerKnowledgeGraph maps L1 SAE features, L2/L3 Gates, and L4 Mental-Map nodes with valid edges', () => {
  const ugcCompiled = compileExplanationRecord(INITIAL_SCENARIOS[0]);
  const graph = buildCrossLayerKnowledgeGraph(ugcCompiled);

  // Must contain nodes across all 4 tier columns (0: L1, 1: L2/L3 Gate, 2: L4 Mental Map, 3: L4 Correspondence)
  const tiersPresent = new Set(graph.nodes.map((n) => n.tierColumn));
  assert.deepEqual([...tiersPresent].sort(), [0, 1, 2, 3]);

  // Every link must reference existing source and target node IDs
  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  for (const link of graph.links) {
    assert.ok(nodeIds.has(link.source), `Missing source node ${link.source}`);
    assert.ok(nodeIds.has(link.target), `Missing target node ${link.target}`);
  }

  // UGC has open-weights L1 features and high L4 comprehension
  assert.ok(graph.summary.l1ToL4GroundingRatio > 0.45);
  assert.equal(graph.summary.weakestL4NodeId, 'L4::UGC-2');
});

test('buildCrossLayerKnowledgeGraph injects explicit 100% Dark-Matter node on API-black-box records', () => {
  const nsCompiled = compileExplanationRecord(INITIAL_SCENARIOS[1]); // Navier-Stokes API-black-box
  const graph = buildCrossLayerKnowledgeGraph(nsCompiled);

  const darkNode = graph.nodes.find((n) => n.id === 'L1::DARK-MATTER-RESIDUAL');
  assert.ok(darkNode, 'Expected explicit dark-matter residual node for API-black-box record');
  assert.equal(darkNode.status, 'dark-matter');
  assert.equal(graph.summary.darkMatterFluxRatio, 1);
  assert.equal(graph.summary.l1ToL4GroundingRatio, 0);
});
