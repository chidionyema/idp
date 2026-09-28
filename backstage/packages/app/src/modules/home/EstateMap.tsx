// FleetView: the estate as a map instead of a table.
//
// This is the answer to the standing complaint that blast-radius (item #7) computes a real
// graph walk -- nodes, edges, hops -- and then renders it as a bullet list. `GET
// /fleetview/graph` (src/graph.py) hands over the whole estate graph once, unfiltered; this
// component lays it out with dagre and draws it with React Flow, and a click still asks the
// same `/blast-radius` endpoint for the walk -- that logic is not reimplemented here.
//
// Idle state is deliberately muted: every node sits at low contrast until something is
// selected, so 879 nodes read as a map, not a wall of alarms. A click lights up exactly what
// the query answered -- downstream warm (darker with more hops away), upstream cool, the node
// itself bright, everything else faded -- and nothing is colored on a guess.
import { useCallback, useEffect, useMemo, useState } from 'react';
import dagre from 'dagre';
import {
  Background,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Chip } from '../shell';

type GraphNode = { id: string; domain: string; type: string; status: string };
type GraphEdge = { source_id: string; target_id: string; relation: string };
type GraphSnapshot = { nodes: GraphNode[]; edges: GraphEdge[] };

type BlastResult = {
  node_id: string;
  downstream: { node_id: string; hops: number; relation: string }[];
  upstream: { node_id: string; relation: string }[];
};

// Domain -> fill. Status decides the border (solid = active, dashed = anything else honest
// about its own state -- dead, stranded, unknown -- never a fourth color inventing a category
// the estate twin does not itself report).
const DOMAIN_FILL: Record<string, string> = {
  runtime: '#2b6cb0',
  code: '#805ad5',
  git: '#38a169',
};
const DEFAULT_FILL = '#718096';
const NODE_W = 170;
const NODE_H = 40;

function EstateNode({ id, data }: NodeProps) {
  const d = data as unknown as {
    label: string;
    domain: string;
    status: string;
    opacity: number;
    ring: 'downstream' | 'upstream' | 'origin' | null;
  };
  const ringColor =
    d.ring === 'origin' ? '#f6e05e' : d.ring === 'downstream' ? '#e53e3e' : d.ring === 'upstream' ? '#3182ce' : 'transparent';
  return (
    <div
      title={id}
      style={{
        width: NODE_W,
        height: NODE_H,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 8px',
        borderRadius: 6,
        fontSize: 11,
        color: '#fff',
        background: DOMAIN_FILL[d.domain] ?? DEFAULT_FILL,
        border: `2px ${d.status === 'active' ? 'solid' : 'dashed'} ${ringColor === 'transparent' ? 'rgba(255,255,255,0.5)' : ringColor}`,
        opacity: d.opacity,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        transition: 'opacity 200ms ease, border-color 200ms ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      {d.label}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const NODE_TYPES = { estate: EstateNode };

function layout(snapshot: GraphSnapshot): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'TB', nodesep: 24, ranksep: 60 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of snapshot.nodes) g.setNode(n.id, { width: NODE_W, height: NODE_H });
  for (const e of snapshot.edges) {
    if (g.hasNode(e.source_id) && g.hasNode(e.target_id)) g.setEdge(e.source_id, e.target_id);
  }
  dagre.layout(g);

  const nodes: Node[] = snapshot.nodes.map(n => {
    const pos = g.node(n.id) ?? { x: 0, y: 0 };
    return {
      id: n.id,
      type: 'estate',
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: { label: shortLabel(n.id), domain: n.domain, status: n.status, opacity: 0.55, ring: null },
    };
  });
  const edges: Edge[] = snapshot.edges.map(e => ({
    id: `${e.source_id}->${e.target_id}:${e.relation}`,
    source: e.source_id,
    target: e.target_id,
    animated: false,
    style: { stroke: '#cbd5e0', strokeWidth: 1, opacity: 0.4 },
  }));
  return { nodes, edges };
}

function shortLabel(id: string): string {
  const parts = id.split(':');
  return parts[parts.length - 1] || id;
}

export function EstateMap() {
  const fetchApi = useApi(fetchApiRef);
  const [snapshot, setSnapshot] = useState<GraphSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [blast, setBlast] = useState<BlastResult | null>(null);
  const [blastError, setBlastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/graph');
        const body = await res.json();
        if (cancelled) return;
        if (!res.ok) {
          setError(body.error ?? `HTTP ${res.status}`);
        } else {
          setSnapshot(body);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchApi]);

  const base = useMemo(() => (snapshot ? layout(snapshot) : null), [snapshot]);

  const onNodeClick = useCallback(
    async (_: unknown, node: Node) => {
      setSelected(node.id);
      setBlast(null);
      setBlastError(null);
      try {
        const res = await fetchApi.fetch(
          `plugin://proxy/fleetview/blast-radius?node_id=${encodeURIComponent(node.id)}`,
        );
        const body = await res.json();
        if (!res.ok) {
          setBlastError(body.error ?? `HTTP ${res.status}`);
        } else {
          setBlast(body);
        }
      } catch (err) {
        setBlastError(err instanceof Error ? err.message : String(err));
      }
    },
    [fetchApi],
  );

  const clearSelection = useCallback(() => {
    setSelected(null);
    setBlast(null);
    setBlastError(null);
  }, []);

  const { nodes, edges } = useMemo(() => {
    if (!base) return { nodes: [] as Node[], edges: [] as Edge[] };
    if (!selected) return base;

    const hopsById = new Map<string, number>();
    for (const d of blast?.downstream ?? []) hopsById.set(d.node_id, d.hops);
    const upstreamIds = new Set((blast?.upstream ?? []).map(u => u.node_id));

    const nodes = base.nodes.map(n => {
      if (n.id === selected) {
        return { ...n, data: { ...n.data, opacity: 1, ring: 'origin' } };
      }
      if (hopsById.has(n.id)) {
        const hops = hopsById.get(n.id)!;
        return { ...n, data: { ...n.data, opacity: Math.max(0.4, 1 - hops * 0.15), ring: 'downstream' } };
      }
      if (upstreamIds.has(n.id)) {
        return { ...n, data: { ...n.data, opacity: 0.85, ring: 'upstream' } };
      }
      return { ...n, data: { ...n.data, opacity: 0.15, ring: null } };
    });

    const litIds = new Set([selected, ...hopsById.keys(), ...upstreamIds]);
    const edges = base.edges.map(e => {
      const lit = litIds.has(e.source) && litIds.has(e.target);
      return {
        ...e,
        style: {
          stroke: lit ? '#e53e3e' : '#cbd5e0',
          strokeWidth: lit ? 2 : 1,
          opacity: lit ? 0.9 : 0.1,
        },
      };
    });
    return { nodes, edges };
  }, [base, selected, blast]);

  if (loading) return <div aria-label="estate graph loading">Loading the estate graph…</div>;
  if (error) return <Chip>Estate graph unavailable: {error}</Chip>;
  if (!snapshot || snapshot.nodes.length === 0) {
    return <div>No nodes swept yet -- run `bin/estate-twin-runtime --once`.</div>;
  }

  return (
    <div>
      <div style={{ height: 480, border: '1px solid #e2e8f0', borderRadius: 8 }} data-testid="estate-graph-canvas">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            onNodeClick={onNodeClick}
            onPaneClick={clearSelection}
            fitView
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={24} />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
      <div style={{ marginTop: 8, fontSize: 13 }}>
        {selected ? (
          <>
            <strong>{shortLabel(selected)}</strong> selected --{' '}
            {blastError ? (
              <span>blast radius unavailable: {blastError}</span>
            ) : blast ? (
              <span>
                {blast.downstream.length} downstream, {blast.upstream.length} upstream. Click empty
                space to clear.
              </span>
            ) : (
              <span>checking blast radius…</span>
            )}
          </>
        ) : (
          <span>Click a node for its blast radius. Solid border = active, dashed = anything else.</span>
        )}
      </div>
    </div>
  );
}
