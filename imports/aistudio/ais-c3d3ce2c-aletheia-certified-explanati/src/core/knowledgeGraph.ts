/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Cross-Layer Epistemic Knowledge Graph Builder (L1 Mechanistic -> L2/L3 Gate -> L4 Comprehension)
 * Pure mathematical topology builder decoupled from DOM/D3 rendering for deterministic unit testing.
 */

import type { CertifiedExplanationRecord } from './epistemicCalculus';

export type GraphLayerTier = 'L1_MECHANISTIC' | 'L2_L3_GATE' | 'L4_MENTAL_MAP' | 'L4_CORRESPONDENCE';

export type GraphNodeStatus = 'verified' | 'novel' | 'dark-matter' | 'bottleneck' | 'breach';

export interface EpistemicGraphNode {
  id: string;
  label: string;
  shortCode: string;
  tier: GraphLayerTier;
  tierColumn: 0 | 1 | 2 | 3;
  belief: number;
  causalWeight: number;
  status: GraphNodeStatus;
  subtitle: string;
  detail: string;
  /** Optional reference to original L4 mental map node ID */
  l4NodeId?: string;
}

export type EpistemicEdgeType =
  | 'mechanistic-grounding'
  | 'dark-matter-leakage'
  | 'gate-witness'
  | 'mental-map-dependency'
  | 'correspondence-bridge';

export interface EpistemicGraphLink {
  id: string;
  source: string;
  target: string;
  weight: number;
  edgeType: EpistemicEdgeType;
  isBottleneckPath: boolean;
  formulaLabel: string;
}

export interface KnowledgeGraphTopology {
  recordId: string;
  nodes: EpistemicGraphNode[];
  links: EpistemicGraphLink[];
  summary: {
    totalNodes: number;
    totalLinks: number;
    /** Ratio of L4 comprehension belief grounded in observed L1 circuits [0, 1] */
    l1ToL4GroundingRatio: number;
    /** Unexplained dark matter flux entering L4 comprehension [0, 1] */
    darkMatterFluxRatio: number;
    weakestL4NodeId: string;
  };
}

function round3(val: number): number {
  return Math.round(val * 1000) / 1000;
}

/**
 * Builds the deterministic L1 -> L2/L3 -> L4 knowledge graph topology from a CertifiedExplanationRecord.
 */
export function buildCrossLayerKnowledgeGraph(
  compiled: CertifiedExplanationRecord
): KnowledgeGraphTopology {
  const { input, l1Metrics, l2Metrics, l3Metrics, l4Metrics } = compiled;
  const nodes: EpistemicGraphNode[] = [];
  const links: EpistemicGraphLink[] = [];

  // 1. Layer 1 Mechanistic Nodes (Column 0)
  if (input.l1.accessMode === 'open-weights' && input.l1.activeFeatures.length > 0) {
    for (const feat of input.l1.activeFeatures) {
      const isDark = feat.category === 'error-node';
      const isDeceptive = feat.category === 'deception';
      nodes.push({
        id: `L1::${feat.id}`,
        label: feat.label,
        shortCode: feat.id,
        tier: 'L1_MECHANISTIC',
        tierColumn: 0,
        belief: isDeceptive
          ? round3(1 - feat.activation)
          : isDark
            ? round3(1 - l1Metrics.darkMatterResidual)
            : round3(feat.causalEffect),
        causalWeight: round3(feat.activation),
        status: isDeceptive
          ? 'breach'
          : isDark
            ? 'dark-matter'
            : feat.category === 'novel-abstraction'
              ? 'novel'
              : 'verified',
        subtitle: `Layer ${feat.layer} · Act ${feat.activation.toFixed(2)} · do(z=0)=${feat.causalEffect.toFixed(2)}`,
        detail: isDark
          ? `Unexplained cross-layer transcoder error node representing ${(l1Metrics.darkMatterResidual * 100).toFixed(1)}% dark-matter residual.`
          : `Causal mechanistic feature extracted at Layer ${feat.layer} with interventional effect ${feat.causalEffect.toFixed(2)}.`,
      });
    }
  }

  // Always include an explicit Dark-Matter Residual node if residual > 0 and no error-node was explicitly listed
  const hasExplicitDarkNode = nodes.some((n) => n.status === 'dark-matter');
  if (!hasExplicitDarkNode && l1Metrics.darkMatterResidual > 0) {
    nodes.push({
      id: 'L1::DARK-MATTER-RESIDUAL',
      label:
        input.l1.accessMode === 'api-black-box'
          ? 'Closed-API Black-Box Residual (100% Unobserved Internals)'
          : `Unexplained Circuit Residual (ε_dark = ${(l1Metrics.darkMatterResidual * 100).toFixed(1)}%)`,
      shortCode: input.l1.accessMode === 'api-black-box' ? 'API-OPAQUE' : 'ε_DARK',
      tier: 'L1_MECHANISTIC',
      tierColumn: 0,
      belief: round3(1 - l1Metrics.darkMatterResidual),
      causalWeight: round3(l1Metrics.darkMatterResidual),
      status: 'dark-matter',
      subtitle: `Dark Matter ε_dark = ${(l1Metrics.darkMatterResidual * 100).toFixed(1)}%`,
      detail:
        input.l1.accessMode === 'api-black-box'
          ? 'Zero model weights or internal activations accessible; 100% of computation flows through unobserved channels.'
          : `Represents the ${(l1Metrics.darkMatterResidual * 100).toFixed(1)}% fraction of neural computation not captured by the sparse replacement circuit.`,
    });
  }

  // 2. Layer 2 & Layer 3 Epistemic Gate Nodes (Column 1)
  const honestyGateId = 'GATE::L2-HONESTY-STACK';
  const provenanceGateId = 'GATE::L3-MERKLE-PROVENANCE';

  nodes.push({
    id: honestyGateId,
    label: 'L2 Asymmetric CoT & Confession Gate',
    shortCode: 'L2-HONESTY',
    tier: 'L2_L3_GATE',
    tierColumn: 1,
    belief: round3(l2Metrics.honestyStackCoverage * l2Metrics.incriminationMultiplier),
    causalWeight: round3(l2Metrics.incriminationMultiplier),
    status:
      l2Metrics.incriminationMultiplier < 0.5
        ? 'breach'
        : l2Metrics.incriminationMultiplier < 0.9
          ? 'bottleneck'
          : 'verified',
    subtitle: `ΔBel⁺=0% · Λ⁻=${(l2Metrics.incriminationMultiplier * 100).toFixed(0)}% · Stack Cov ${(l2Metrics.honestyStackCoverage * 100).toFixed(1)}%`,
    detail: `Enforces Theorem 1: clean CoT grants 0% positive exoneration; confessions & probes bound deception escape to ${(l2Metrics.jointBlindspotProbability * 100).toFixed(1)}%.`,
  });

  nodes.push({
    id: provenanceGateId,
    label: `L3 Merkle State Gate (${input.l3.workflowId})`,
    shortCode: 'L3-MERKLE',
    tier: 'L2_L3_GATE',
    tierColumn: 1,
    belief: round3(l3Metrics.provenanceIntegrity),
    causalWeight: round3(l3Metrics.provenanceIntegrity),
    status: l3Metrics.selfReportDivergenceCount > 0 ? 'breach' : 'verified',
    subtitle: `Root ${l3Metrics.merkleRootHex.slice(0, 10)}… · Divergence=${l3Metrics.selfReportDivergenceCount}`,
    detail: `Enforces Theorem 2: verifies monotonic fencing tokens and compares agent self-reports against kernel state diffs under EU AI Act Art. 12.`,
  });

  // Connect L1 nodes -> L2/L3 Gates
  const l1Nodes = nodes.filter((n) => n.tier === 'L1_MECHANISTIC');
  for (const l1Node of l1Nodes) {
    const isDark = l1Node.status === 'dark-matter';
    links.push({
      id: `EDGE::${l1Node.id}->${honestyGateId}`,
      source: l1Node.id,
      target: honestyGateId,
      weight: round3(Math.max(0.2, l1Node.causalWeight)),
      edgeType: isDark ? 'dark-matter-leakage' : 'mechanistic-grounding',
      isBottleneckPath: isDark || l1Node.status === 'breach',
      formulaLabel: isDark
        ? `ε_dark=${(l1Metrics.darkMatterResidual * 100).toFixed(0)}%`
        : `do(z)=${l1Node.belief.toFixed(2)}`,
    });

    links.push({
      id: `EDGE::${l1Node.id}->${provenanceGateId}`,
      source: l1Node.id,
      target: provenanceGateId,
      weight: round3(Math.max(0.25, l1Node.belief)),
      edgeType: isDark ? 'dark-matter-leakage' : 'mechanistic-grounding',
      isBottleneckPath: l3Metrics.selfReportDivergenceCount > 0,
      formulaLabel: isDark ? 'Unwitnessed Internal Flux' : 'Circuit-to-Action Trace',
    });
  }

  // 3. Layer 4 Mental-Map Bottleneck DAG Nodes (Column 2)
  const weakestId = l4Metrics.weakestBottleneckNode.id;
  for (const mmNode of input.l4.mentalMapNodes) {
    const isWeakest = mmNode.id === weakestId;
    const isOpaque = !mmNode.humanReconstructible;
    nodes.push({
      id: `L4::${mmNode.id}`,
      label: mmNode.title,
      shortCode: mmNode.id,
      tier: 'L4_MENTAL_MAP',
      tierColumn: 2,
      belief: round3(mmNode.nodeBelief),
      causalWeight: round3(
        Math.min(1, mmNode.rawSpanCount / Math.max(1, input.l4.rawArtifactLines))
      ),
      status: isOpaque ? 'breach' : isWeakest ? 'bottleneck' : 'verified',
      subtitle: `${mmNode.role} · Bel ${(mmNode.nodeBelief * 100).toFixed(0)}% · ${mmNode.rawSpanCount.toLocaleString()} lines`,
      detail: mmNode.summary,
      l4NodeId: mmNode.id,
    });
  }

  // Connect Gates -> Root L4 Mental-Map Nodes (and all L4 nodes that represent key constructions/axioms)
  const l4Nodes = input.l4.mentalMapNodes;
  l4Nodes.forEach((mmNode, idx) => {
    const targetGraphId = `L4::${mmNode.id}`;
    const isRoot = mmNode.dependsOn.length === 0 || idx === 0;
    const isWeakest = mmNode.id === weakestId;

    if (isRoot) {
      links.push({
        id: `EDGE::${honestyGateId}->${targetGraphId}`,
        source: honestyGateId,
        target: targetGraphId,
        weight: round3(mmNode.nodeBelief),
        edgeType: 'gate-witness',
        isBottleneckPath: isWeakest || !mmNode.humanReconstructible,
        formulaLabel: `L2→L4 (${(mmNode.nodeBelief * 100).toFixed(0)}%)`,
      });
    }

    links.push({
      id: `EDGE::${provenanceGateId}->${targetGraphId}`,
      source: provenanceGateId,
      target: targetGraphId,
      weight: round3(l3Metrics.provenanceIntegrity * mmNode.nodeBelief),
      edgeType: 'gate-witness',
      isBottleneckPath: isWeakest || l3Metrics.selfReportDivergenceCount > 0,
      formulaLabel: `τ_k Witness`,
    });

    // Connect L1 non-dark features directly to matching L4 nodes to show direct mechanistic-to-comprehension concept mapping
    const matchingL1 = l1Nodes[idx % Math.max(1, l1Nodes.length)];
    if (matchingL1) {
      links.push({
        id: `EDGE::DIRECT::${matchingL1.id}->${targetGraphId}`,
        source: matchingL1.id,
        target: targetGraphId,
        weight: round3((matchingL1.causalWeight + mmNode.nodeBelief) / 2),
        edgeType:
          matchingL1.status === 'dark-matter'
            ? 'dark-matter-leakage'
            : 'mechanistic-grounding',
        isBottleneckPath: isWeakest || matchingL1.status === 'dark-matter',
        formulaLabel:
          matchingL1.status === 'dark-matter'
            ? 'Dark-Matter Uncertainty'
            : `Concept Bridge (${matchingL1.shortCode}→${mmNode.id})`,
      });
    }

    // Internal L4 Mental-Map DAG dependencies
    for (const parentId of mmNode.dependsOn) {
      const parentGraphId = `L4::${parentId}`;
      if (nodes.some((n) => n.id === parentGraphId)) {
        links.push({
          id: `EDGE::DAG::${parentGraphId}->${targetGraphId}`,
          source: parentGraphId,
          target: targetGraphId,
          weight: round3(mmNode.nodeBelief),
          edgeType: 'mental-map-dependency',
          isBottleneckPath: isWeakest || parentId === weakestId,
          formulaLabel: 'Lemma Dependency',
        });
      }
    }
  });

  // 4. Layer 4 Correspondence & Retention Terminal Node (Column 3)
  const correspondenceId = 'L4::CORRESPONDENCE-ANCHOR';
  nodes.push({
    id: correspondenceId,
    label: `Certified Human Comprehension & Correspondence (Bel ${(compiled.epistemicInterval.beliefLowerBound * 100).toFixed(1)}%)`,
    shortCode: 'P_FORMAL ≡ H_INF',
    tier: 'L4_CORRESPONDENCE',
    tierColumn: 3,
    belief: round3(compiled.epistemicInterval.beliefLowerBound),
    causalWeight: round3(l4Metrics.correspondenceScore),
    status:
      compiled.evidenceGrade === 'CONTAINMENT_BREACH'
        ? 'breach'
        : compiled.evidenceGrade === 'CORRESPONDENCE_GAP'
          ? 'bottleneck'
          : 'verified',
    subtitle: `Correspondence ${(l4Metrics.correspondenceScore * 100).toFixed(1)}% · Retention ${(l4Metrics.durabilityPillars.capabilityRetention * 100).toFixed(1)}%`,
    detail: `Theorem 4 Terminal Synthesis: verifies that formal proposition "${input.l4.formalKernelProposition}" faithfully encodes the informal claim and survives human reconstruction.`,
  });

  // Connect terminal L4 mental map nodes to the Correspondence Anchor
  for (const mmNode of l4Nodes) {
    const sourceGraphId = `L4::${mmNode.id}`;
    const isWeakest = mmNode.id === weakestId;
    links.push({
      id: `EDGE::${sourceGraphId}->${correspondenceId}`,
      source: sourceGraphId,
      target: correspondenceId,
      weight: round3(mmNode.nodeBelief * l4Metrics.correspondenceScore),
      edgeType: 'correspondence-bridge',
      isBottleneckPath: isWeakest || !mmNode.humanReconstructible,
      formulaLabel: isWeakest ? 'Weakest Bottleneck Link' : 'Retention Bridge',
    });
  }

  const l1ToL4GroundingRatio = round3(
    l1Metrics.explainedCircuitCoverage * l4Metrics.durabilityPillars.comprehension
  );
  const darkMatterFluxRatio = round3(l1Metrics.darkMatterResidual);

  return {
    recordId: input.id,
    nodes,
    links,
    summary: {
      totalNodes: nodes.length,
      totalLinks: links.length,
      l1ToL4GroundingRatio,
      darkMatterFluxRatio,
      weakestL4NodeId: `L4::${weakestId}`,
    },
  };
}
