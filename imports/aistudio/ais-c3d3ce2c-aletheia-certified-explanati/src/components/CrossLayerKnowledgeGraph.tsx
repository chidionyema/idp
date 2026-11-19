/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Interactive D3.js Cross-Layer Epistemic Knowledge Graph (L1 Mechanistic -> L2/L3 Gate -> L4 Comprehension)
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import type { CertifiedExplanationRecord } from '../core/epistemicCalculus';
import {
  buildCrossLayerKnowledgeGraph,
  type EpistemicGraphLink,
  type EpistemicGraphNode,
} from '../core/knowledgeGraph';

interface CrossLayerKnowledgeGraphProps {
  compiled: CertifiedExplanationRecord;
  selectedL4NodeId: string | null;
  onSelectL4NodeId: (nodeId: string) => void;
}

type LayoutMode = 'stratified' | 'force';
type EdgeFilterMode = 'all' | 'grounded-only' | 'bottlenecks-and-dark';

interface SimNode extends EpistemicGraphNode, d3.SimulationNodeDatum {
  x: number;
  y: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  id: string;
  source: SimNode;
  target: SimNode;
  weight: number;
  edgeType: EpistemicGraphLink['edgeType'];
  isBottleneckPath: boolean;
  formulaLabel: string;
}

function getNodeColors(status: EpistemicGraphNode['status']): {
  fill: string;
  stroke: string;
  text: string;
  glyph: string;
} {
  switch (status) {
    case 'verified':
      return {
        fill: '#062822',
        stroke: '#34d399',
        text: '#a7f3d0',
        glyph: '●',
      };
    case 'novel':
      return {
        fill: '#082538',
        stroke: '#22d3ee',
        text: '#a5f3fc',
        glyph: '◆',
      };
    case 'dark-matter':
      return {
        fill: '#2b1d07',
        stroke: '#f59e0b',
        text: '#fde68a',
        glyph: '▲',
      };
    case 'bottleneck':
      return {
        fill: '#2e1f09',
        stroke: '#fbbf24',
        text: '#fef08a',
        glyph: '▲',
      };
    case 'breach':
      return {
        fill: '#330b16',
        stroke: '#fb7185',
        text: '#fecdd3',
        glyph: '✖',
      };
  }
}

function getEdgeStroke(edgeType: EpistemicGraphLink['edgeType'], isBottleneck: boolean): {
  stroke: string;
  dasharray: string;
} {
  if (edgeType === 'dark-matter-leakage') {
    return { stroke: '#f59e0b', dasharray: '5,4' };
  }
  if (isBottleneck) {
    return { stroke: '#fb7185', dasharray: '3,3' };
  }
  switch (edgeType) {
    case 'mechanistic-grounding':
      return { stroke: '#22d3ee', dasharray: 'none' };
    case 'gate-witness':
      return { stroke: '#34d399', dasharray: 'none' };
    case 'mental-map-dependency':
      return { stroke: '#60a5fa', dasharray: 'none' };
    case 'correspondence-bridge':
      return { stroke: '#a78bfa', dasharray: 'none' };
  }
}

const SVG_WIDTH = 960;
const SVG_HEIGHT = 470;
const COLUMN_X: Record<0 | 1 | 2 | 3, number> = {
  0: 140,
  1: 400,
  2: 665,
  3: 865,
};

export const CrossLayerKnowledgeGraph: React.FC<CrossLayerKnowledgeGraphProps> = ({
  compiled,
  selectedL4NodeId,
  onSelectL4NodeId,
}) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  const [layoutMode, setLayoutMode] = useState<LayoutMode>('stratified');
  const [edgeFilter, setEdgeFilter] = useState<EdgeFilterMode>('all');
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  const topology = useMemo(() => buildCrossLayerKnowledgeGraph(compiled), [compiled]);

  const filteredLinks = useMemo(() => {
    if (edgeFilter === 'grounded-only') {
      return topology.links.filter((l) => l.edgeType !== 'dark-matter-leakage');
    }
    if (edgeFilter === 'bottlenecks-and-dark') {
      return topology.links.filter(
        (l) => l.isBottleneckPath || l.edgeType === 'dark-matter-leakage'
      );
    }
    return topology.links;
  }, [topology, edgeFilter]);

  // Synchronize selected node with parent L4 selection or default to weakest bottleneck L4 node
  const activeGraphNode: EpistemicGraphNode = useMemo(() => {
    if (selectedGraphNodeId) {
      const found = topology.nodes.find((n) => n.id === selectedGraphNodeId);
      if (found) return found;
    }
    if (selectedL4NodeId) {
      const foundL4 = topology.nodes.find((n) => n.l4NodeId === selectedL4NodeId);
      if (foundL4) return foundL4;
    }
    return (
      topology.nodes.find((n) => n.id === topology.summary.weakestL4NodeId) ||
      topology.nodes[0]
    );
  }, [topology, selectedGraphNodeId, selectedL4NodeId]);

  const handleNodeSelect = (node: EpistemicGraphNode) => {
    setSelectedGraphNodeId(node.id);
    if (node.l4NodeId) {
      onSelectL4NodeId(node.l4NodeId);
    }
  };

  // Keep latest selection handler in ref so D3 event listeners never go stale
  const selectHandlerRef = useRef(handleNodeSelect);
  selectHandlerRef.current = handleNodeSelect;

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    // Define SVG arrowhead markers
    const defs = svg.append('defs');
    const markerConfigs = [
      { id: 'arrow-cyan', color: '#22d3ee' },
      { id: 'arrow-emerald', color: '#34d399' },
      { id: 'arrow-amber', color: '#f59e0b' },
      { id: 'arrow-rose', color: '#fb7185' },
      { id: 'arrow-violet', color: '#a78bfa' },
    ];

    markerConfigs.forEach((m) => {
      defs
        .append('marker')
        .attr('id', m.id)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 26)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L10,0L0,4')
        .attr('fill', m.color);
    });

    const rootG = svg.append('g').attr('class', 'graph-viewport');

    // Setup Zoom & Pan
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.6, 2.4])
      .on('zoom', (event) => {
        rootG.attr('transform', event.transform.toString());
        setZoomLevel(Math.round(event.transform.k * 100) / 100);
      });

    zoomBehaviorRef.current = zoom;
    svg.call(zoom);

    // Draw stratified column guides when in stratified mode
    if (layoutMode === 'stratified') {
      const tierHeaders: Array<{ col: 0 | 1 | 2 | 3; title: string; sub: string }> = [
        { col: 0, title: 'L1 · MECHANISTIC INTERNALS', sub: 'SAE / Transcoder / ε_dark' },
        { col: 1, title: 'L2 & L3 · EPISTEMIC GATES', sub: 'Confession + Merkle Witness' },
        { col: 2, title: 'L4 · MENTAL-MAP DAG', sub: 'Moshkovitz Bottleneck Nodes' },
        { col: 3, title: 'L4 · CORRESPONDENCE', sub: 'P_formal ≡ H_inf' },
      ];

      const guidesG = rootG.append('g').attr('class', 'tier-guides');
      tierHeaders.forEach((th) => {
        const cx = COLUMN_X[th.col];
        guidesG
          .append('line')
          .attr('x1', cx)
          .attr('y1', 48)
          .attr('x2', cx)
          .attr('y2', SVG_HEIGHT - 20)
          .attr('stroke', '#1e293b')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '3,5');

        guidesG
          .append('text')
          .attr('x', cx)
          .attr('y', 22)
          .attr('text-anchor', 'middle')
          .attr('fill', '#94a3b8')
          .attr('font-family', 'JetBrains Mono, monospace')
          .attr('font-size', '10px')
          .attr('font-weight', '600')
          .text(th.title);

        guidesG
          .append('text')
          .attr('x', cx)
          .attr('y', 36)
          .attr('text-anchor', 'middle')
          .attr('fill', '#64748b')
          .attr('font-family', 'JetBrains Mono, monospace')
          .attr('font-size', '9.5px')
          .text(th.sub);
      });
    }

    // Prepare simulation nodes with deterministic starting coordinates per column
    const colCounts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };
    const colTotals: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };
    topology.nodes.forEach((n) => {
      colTotals[n.tierColumn] = (colTotals[n.tierColumn] || 0) + 1;
    });

    const simNodes: SimNode[] = topology.nodes.map((n) => {
      const idxInCol = colCounts[n.tierColumn]++;
      const totalInCol = colTotals[n.tierColumn];
      const usableHeight = SVG_HEIGHT - 90;
      const stepY = usableHeight / (totalInCol + 1);
      return {
        ...n,
        x: COLUMN_X[n.tierColumn],
        y: 52 + stepY * (idxInCol + 1),
      };
    });

    const nodeById = new Map<string, SimNode>(simNodes.map((n) => [n.id, n]));

    const simLinks: SimLink[] = filteredLinks
      .map((l) => {
        const s = nodeById.get(l.source);
        const t = nodeById.get(l.target);
        if (!s || !t) return null;
        return {
          id: l.id,
          source: s,
          target: t,
          weight: l.weight,
          edgeType: l.edgeType,
          isBottleneckPath: l.isBottleneckPath,
          formulaLabel: l.formulaLabel,
        };
      })
      .filter((l): l is SimLink => l !== null);

    // Configure D3 Force Simulation
    const simulation = d3
      .forceSimulation<SimNode>(simNodes)
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(layoutMode === 'stratified' ? 195 : 145)
          .strength(layoutMode === 'stratified' ? 0.15 : 0.65)
      )
      .force(
        'charge',
        d3.forceManyBody<SimNode>().strength(layoutMode === 'stratified' ? -140 : -460)
      )
      .force('collide', d3.forceCollide<SimNode>().radius(38).strength(0.95));

    if (layoutMode === 'stratified') {
      simulation
        .force(
          'x',
          d3.forceX<SimNode>((d) => COLUMN_X[d.tierColumn]).strength(0.98)
        )
        .force(
          'y',
          d3
            .forceY<SimNode>((d) => d.y)
            .strength(0.85)
        );
    } else {
      simulation
        .force('center', d3.forceCenter(SVG_WIDTH / 2, SVG_HEIGHT / 2 + 12))
        .force(
          'x',
          d3.forceX<SimNode>((d) => COLUMN_X[d.tierColumn]).strength(0.32)
        )
        .force('y', d3.forceY<SimNode>(SVG_HEIGHT / 2 + 12).strength(0.28));
    }

    // Pre-tick warm-up synchronously so initial render is immediately settled and crisp
    simulation.stop();
    for (let i = 0; i < 120; i++) {
      simulation.tick();
      simNodes.forEach((n) => {
        n.x = Math.max(85, Math.min(SVG_WIDTH - 85, n.x));
        n.y = Math.max(68, Math.min(SVG_HEIGHT - 42, n.y));
      });
    }

    // Render Links
    const linksG = rootG.append('g').attr('class', 'graph-links');
    const linkElements = linksG
      .selectAll<SVGPathElement, SimLink>('path')
      .data(simLinks, (d) => d.id)
      .join('path')
      .attr('fill', 'none')
      .attr('stroke', (d) => getEdgeStroke(d.edgeType, d.isBottleneckPath).stroke)
      .attr('stroke-width', (d) =>
        d.source.id === activeGraphNode.id || d.target.id === activeGraphNode.id
          ? Math.max(2.2, d.weight * 3.4)
          : Math.max(1.2, d.weight * 2.2)
      )
      .attr('stroke-opacity', (d) =>
        d.source.id === activeGraphNode.id || d.target.id === activeGraphNode.id ? 0.95 : 0.38
      )
      .attr('stroke-dasharray', (d) => getEdgeStroke(d.edgeType, d.isBottleneckPath).dasharray)
      .attr('marker-end', (d) => {
        if (d.edgeType === 'dark-matter-leakage') return 'url(#arrow-amber)';
        if (d.isBottleneckPath) return 'url(#arrow-rose)';
        if (d.edgeType === 'gate-witness') return 'url(#arrow-emerald)';
        if (d.edgeType === 'correspondence-bridge') return 'url(#arrow-violet)';
        return 'url(#arrow-cyan)';
      });

    // Render Nodes
    const nodesG = rootG.append('g').attr('class', 'graph-nodes');
    const nodeGroups = nodesG
      .selectAll<SVGGElement, SimNode>('g.epistemic-node')
      .data(simNodes, (d) => d.id)
      .join('g')
      .attr('class', 'epistemic-node')
      .style('cursor', 'pointer')
      .on('click', (_event, d) => {
        selectHandlerRef.current(d);
      });

    // Outer halo for currently selected node
    nodeGroups
      .filter((d) => d.id === activeGraphNode.id)
      .append('circle')
      .attr('r', 24)
      .attr('fill', 'none')
      .attr('stroke', '#22d3ee')
      .attr('stroke-width', 1.75)
      .attr('stroke-dasharray', '3,2');

    // Main Node Circle
    nodeGroups
      .append('circle')
      .attr('r', (d) => (d.tier === 'L4_CORRESPONDENCE' ? 20 : 17))
      .attr('fill', (d) => getNodeColors(d.status).fill)
      .attr('stroke', (d) => getNodeColors(d.status).stroke)
      .attr('stroke-width', (d) => (d.id === activeGraphNode.id ? 2.5 : 1.75));

    // Node Center Belief Readout
    nodeGroups
      .append('text')
      .attr('dy', '0.32em')
      .attr('text-anchor', 'middle')
      .attr('fill', (d) => getNodeColors(d.status).text)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '9.5px')
      .attr('font-weight', '700')
      .text((d) => `${Math.round(d.belief * 100)}%`);

    // Node ShortCode Label above circle
    nodeGroups
      .append('text')
      .attr('dy', -23)
      .attr('text-anchor', 'middle')
      .attr('fill', '#f1f5f9')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .text((d) => `${getNodeColors(d.status).glyph} ${d.shortCode}`);

    // Truncated Concept Title below circle
    nodeGroups
      .append('text')
      .attr('dy', 29)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-family', 'Public Sans, sans-serif')
      .attr('font-size', '9.5px')
      .text((d) => (d.label.length > 24 ? `${d.label.slice(0, 22)}…` : d.label));

    const updatePositions = () => {
      linkElements.attr('d', (d) => {
        const sx = d.source.x;
        const sy = d.source.y;
        const tx = d.target.x;
        const ty = d.target.y;
        if (Math.abs(tx - sx) < 35) {
          const offset = 38;
          return `M${sx},${sy} C${sx + offset},${(sy + ty) / 2} ${tx + offset},${(sy + ty) / 2} ${tx},${ty}`;
        }
        const midX = (sx + tx) / 2;
        return `M${sx},${sy} C${midX},${sy} ${midX},${ty} ${tx},${ty}`;
      });

      nodeGroups.attr('transform', (d) => `translate(${d.x},${d.y})`);
    };

    updatePositions();

    // Enable interactive D3 node dragging
    const dragBehavior = d3
      .drag<SVGGElement, SimNode>()
      .on('start', (event, d) => {
        d.fx = d.x;
        d.fy = d.y;
        selectHandlerRef.current(d);
        if (!event.active) simulation.alphaTarget(0.15).restart();
      })
      .on('drag', (event, d) => {
        d.fx = Math.max(60, Math.min(SVG_WIDTH - 60, event.x));
        d.fy = Math.max(55, Math.min(SVG_HEIGHT - 35, event.y));
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    nodeGroups.call(dragBehavior);
    simulation.on('tick', updatePositions);

    return () => {
      simulation.stop();
    };
  }, [topology, filteredLinks, layoutMode, activeGraphNode.id]);

  const handleZoomStep = (factor: number) => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(150).call(zoomBehaviorRef.current.scaleBy, factor);
  };

  const handleResetZoom = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(150)
      .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
  };

  // Connected incoming and outgoing edges for the active node
  const incomingLinks = topology.links.filter((l) => l.target === activeGraphNode.id);
  const outgoingLinks = topology.links.filter((l) => l.source === activeGraphNode.id);

  return (
    <article
      aria-label="L1 to L4 Cross-Layer Epistemic Knowledge Graph"
      className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4"
    >
      {/* Top Header & Interactive Graph Controls */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-slate-800/80 pb-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-wider">
            <span>D3.js Cross-Layer Epistemic Knowledge Graph</span>
            <span aria-hidden="true">·</span>
            <span className="text-slate-400 tabular-nums">
              {topology.summary.totalNodes} Nodes / {filteredLinks.length} Active Bridges
            </span>
          </div>
          <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
            Mechanistic Feature Attribution (L1) → Provenance Gate (L2/L3) → Human Mental Map (L4)
          </h2>
        </div>

        {/* Segmented Control Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Layout Mode Switcher */}
          <div
            role="group"
            aria-label="Graph Layout Mode"
            className="flex items-center gap-1 p-1 bg-[#080B12] border border-slate-800 rounded-md"
          >
            <button
              type="button"
              onClick={() => setLayoutMode('stratified')}
              className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                layoutMode === 'stratified'
                  ? 'bg-cyan-400 text-slate-950 font-semibold'
                  : 'text-slate-300 hover:text-slate-100'
              }`}
            >
              Stratified L1→L4
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('force')}
              className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                layoutMode === 'force'
                  ? 'bg-cyan-400 text-slate-950 font-semibold'
                  : 'text-slate-300 hover:text-slate-100'
              }`}
            >
              Force Topology
            </button>
          </div>

          {/* Edge Filter Mode */}
          <div
            role="group"
            aria-label="Epistemic Path Filter"
            className="flex items-center gap-1 p-1 bg-[#080B12] border border-slate-800 rounded-md"
          >
            <button
              type="button"
              onClick={() => setEdgeFilter('all')}
              className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                edgeFilter === 'all'
                  ? 'bg-slate-800 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Bridges
            </button>
            <button
              type="button"
              onClick={() => setEdgeFilter('grounded-only')}
              className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                edgeFilter === 'grounded-only'
                  ? 'bg-slate-800 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Grounded Only
            </button>
            <button
              type="button"
              onClick={() => setEdgeFilter('bottlenecks-and-dark')}
              className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                edgeFilter === 'bottlenecks-and-dark'
                  ? 'bg-slate-800 text-amber-300 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Dark Matter &amp; Bottlenecks
            </button>
          </div>

          {/* Zoom Controls */}
          <div
            role="group"
            aria-label="Graph Zoom Controls"
            className="flex items-center gap-1 p-1 bg-[#080B12] border border-slate-800 rounded-md text-xs font-mono"
          >
            <button
              type="button"
              aria-label="Zoom In Knowledge Graph"
              onClick={() => handleZoomStep(1.25)}
              className="px-2 py-1 text-slate-300 hover:text-cyan-300"
            >
              +
            </button>
            <span className="px-1.5 text-slate-400 tabular-nums">{Math.round(zoomLevel * 100)}%</span>
            <button
              type="button"
              aria-label="Zoom Out Knowledge Graph"
              onClick={() => handleZoomStep(0.8)}
              className="px-2 py-1 text-slate-300 hover:text-cyan-300"
            >
              −
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-2 py-1 text-slate-300 hover:text-cyan-300 border-l border-slate-800"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Main Graph Viewport + Selected Node Epistemic Bridge Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        {/* Left/Center D3 SVG Stage */}
        <div className="lg:col-span-8 bg-[#070A10] border border-slate-800/90 rounded-md overflow-hidden flex flex-col justify-between">
          <svg
            ref={svgRef}
            data-testid="d3-epistemic-knowledge-graph"
            viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            className="w-full h-[390px] sm:h-[440px] select-none cursor-grab active:cursor-grabbing"
            role="img"
            aria-label={`D3 Knowledge Graph mapping ${topology.summary.totalNodes} nodes between L1 mechanistic internals and L4 human comprehension`}
          />

          {/* Graph Legend & Telemetry Strip */}
          <div className="px-4 py-2.5 bg-[#090D16] border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-emerald-400">● Verified Node</span>
              <span aria-hidden="true">·</span>
              <span className="text-cyan-300">◆ Novel L1 Abstraction</span>
              <span aria-hidden="true">·</span>
              <span className="text-amber-300">▲ Dark Matter / Bottleneck</span>
              <span aria-hidden="true">·</span>
              <span className="text-rose-400">✖ Containment Breach</span>
            </div>
            <div className="tabular-nums text-slate-300">
              L1→L4 Grounded Flux: {(topology.summary.l1ToL4GroundingRatio * 100).toFixed(1)}% · Dark-Matter Flux: {(topology.summary.darkMatterFluxRatio * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Right Column: Synchronized Node & Cross-Layer Bridge Inspector */}
        <div className="lg:col-span-4 bg-[#090D15] border border-slate-800/90 rounded-md p-4 flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="border-b border-slate-800 pb-2.5">
              <div className="flex items-center justify-between text-xs font-mono text-cyan-400">
                <span>{activeGraphNode.tier}</span>
                <span className="tabular-nums">Warrant: {(activeGraphNode.belief * 100).toFixed(1)}%</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100 font-display mt-1">
                {activeGraphNode.shortCode} — {activeGraphNode.label}
              </h3>
              <div className="text-xs font-mono text-slate-400 mt-0.5 tabular-nums">
                {activeGraphNode.subtitle}
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {activeGraphNode.detail}
            </p>

            {/* Incoming & Outgoing Cross-Layer Relational Bridges */}
            <div className="space-y-2 pt-2 border-t border-slate-800/80 text-xs">
              <div className="font-mono text-slate-400 uppercase text-[11px]">
                Incoming Epistemic Feeds ({incomingLinks.length})
              </div>
              {incomingLinks.length === 0 ? (
                <div className="text-slate-500 font-mono text-[11px]">
                  Root Layer 1 Mechanistic Source (No upstream parents)
                </div>
              ) : (
                <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
                  {incomingLinks.map((link) => {
                    const srcNode = topology.nodes.find((n) => n.id === link.source);
                    return (
                      <button
                        key={link.id}
                        type="button"
                        onClick={() => srcNode && handleNodeSelect(srcNode)}
                        className="w-full text-left px-2.5 py-1.5 rounded bg-[#0D1320] border border-slate-800 hover:border-cyan-500/60 flex items-center justify-between gap-2 font-mono text-[11px]"
                      >
                        <span className="text-slate-200 shrink-0">
                          ← {srcNode?.shortCode || link.source}
                        </span>
                        <span className="text-cyan-300 tabular-nums truncate">
                          {link.formulaLabel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="font-mono text-slate-400 uppercase text-[11px] pt-1">
                Downstream Comprehension Targets ({outgoingLinks.length})
              </div>
              {outgoingLinks.length === 0 ? (
                <div className="text-slate-500 font-mono text-[11px]">
                  Terminal L4 Correspondence Anchor
                </div>
              ) : (
                <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
                  {outgoingLinks.map((link) => {
                    const tgtNode = topology.nodes.find((n) => n.id === link.target);
                    return (
                      <button
                        key={link.id}
                        type="button"
                        onClick={() => tgtNode && handleNodeSelect(tgtNode)}
                        className="w-full text-left px-2.5 py-1.5 rounded bg-[#0D1320] border border-slate-800 hover:border-cyan-500/60 flex items-center justify-between gap-2 font-mono text-[11px]"
                      >
                        <span className="text-slate-200 shrink-0">
                          → {tgtNode?.shortCode || link.target}
                        </span>
                        <span className="text-emerald-400 tabular-nums truncate">
                          {link.formulaLabel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Accessible Quick-Select Node Strip */}
          <div className="pt-3 border-t border-slate-800/80">
            <div className="text-[11px] font-mono text-slate-400 mb-1.5">
              Inspect Graph Node ({topology.nodes.length}):
            </div>
            <div
              role="listbox"
              aria-label="Select Knowledge Graph Node"
              className="flex flex-wrap gap-1.5"
            >
              {topology.nodes.map((node) => {
                const isSelected = node.id === activeGraphNode.id;
                const colors = getNodeColors(node.status);
                return (
                  <button
                    key={node.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleNodeSelect(node)}
                    className={`px-2 py-1 text-[11px] font-mono rounded border transition-colors whitespace-nowrap ${
                      isSelected
                        ? 'bg-cyan-400/20 border-cyan-400 text-cyan-200 font-semibold'
                        : 'bg-[#0D121D] border-slate-800 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    {colors.glyph} {node.shortCode}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
};
