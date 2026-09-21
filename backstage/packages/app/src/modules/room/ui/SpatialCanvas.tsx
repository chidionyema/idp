// ui/SpatialCanvas.tsx
// The fleet is not a chart. It is a room. Only the EDGES are shown: the stuck,
// the loud, the new, the dying. The rest stay in the hum. Trails are visible.

import { useEffect, useRef, useState } from 'react';
import type { AgentId, EventBus, RoomEvents } from '../core/types';
import type {  } from '../core/types';

interface Node {
  id: AgentId;
  x: number; y: number;
  z: number;                  // depth, 0..1
  radius: number;
  state: 'working' | 'stuck' | 'idle' | 'done' | 'new';
  trail: Array<{ x: number; y: number; t: number }>;
  costUsd: number;
}

export interface SpatialCanvasProps {
  readonly events: EventBus<RoomEvents>;
  readonly spotlight: AgentId | null;
  readonly awake: boolean;
}

const MIN_RADIUS = 26;
const MAX_RADIUS = 64;
const TRAIL_MS = 60 * 60 * 1000; // one hour

export function SpatialCanvas(props: SpatialCanvasProps): JSX.Element {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<Map<AgentId, Node>>(new Map());
  const rafRef = useRef<number>(0);
  const [, force] = useState(0);

  // Seed nodes. In production this comes from the fleet API.
  useEffect(() => {
    const nodes = nodesRef.current;
    if (nodes.size > 0) return;
    for (let i = 0; i < 24; i++) {
      const id = `agent-${i}` as AgentId;
      nodes.set(id, {
        id,
        x: Math.random() * 0.8 + 0.1,
        y: Math.random() * 0.8 + 0.1,
        z: Math.random() * 0.6 + 0.2,
        radius: MIN_RADIUS + Math.random() * (MAX_RADIUS - MIN_RADIUS),
        state: i % 7 === 0 ? 'stuck' : i % 5 === 0 ? 'new' : 'working',
        trail: [],
        costUsd: Math.random() * 0.5,
      });
    }
  }, []);

  // Draw loop.
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const { clientWidth: w, clientHeight: h } = canvas;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = (now: number) => {
      const { clientWidth: w, clientHeight: h } = canvas;
      ctx.clearRect(0, 0, w, h);

      const nodes = Array.from(nodesRef.current.values());

      // Update trails.
      for (const n of nodes) {
        const isSpot = props.spotlight === n.id;
        const drift = isSpot ? 0.0002 : 0.0005 * (1 - n.z);
        n.x += (Math.random() - 0.5) * drift;
        n.y += (Math.random() - 0.5) * drift;
        n.x = Math.max(0.05, Math.min(0.95, n.x));
        n.y = Math.max(0.05, Math.min(0.95, n.y));
        n.trail.push({ x: n.x, y: n.y, t: now });
        while (n.trail.length > 0 && now - n.trail[0].t > TRAIL_MS) {
          n.trail.shift();
        }
      }

      // Draw trails first (behind nodes).
      for (const n of nodes) {
        drawTrail(ctx, n, w, h, props.spotlight === n.id);
      }

      // Draw nodes.
      for (const n of nodes) {
        drawNode(ctx, n, w, h, props.spotlight === n.id);
      }

      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [props.spotlight, props.awake]);

  // Re-render on event (for state changes).
  useEffect(() => {
    const off1 = props.events.on('agent:stuck', (e) => {
      const n = nodesRef.current.get(e.agentId);
      if (n) n.state = 'stuck';
      force((v) => v + 1);
    });
    const off2 = props.events.on('agent:unstuck', (e) => {
      const n = nodesRef.current.get(e.agentId);
      if (n) n.state = 'working';
      force((v) => v + 1);
    });
    return () => { off1(); off2(); };
  }, [props.events]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        display: 'block',
      }}
    />
  );
}

function drawTrail(
  ctx: CanvasRenderingContext2D,
  n: Node,
  w: number,
  h: number,
  spotlight: boolean,
): void {
  if (n.trail.length < 2) return;
  const now = n.trail[n.trail.length - 1].t;
  ctx.save();
  ctx.lineCap = 'round';
  for (let i = 1; i < n.trail.length; i++) {
    const a = n.trail[i - 1];
    const b = n.trail[i];
    const age = (now - b.t) / TRAIL_MS;
    const alpha = Math.max(0, 1 - age) * (spotlight ? 0.9 : 0.35);
    const width = n.state === 'working' ? 3 : 1.2;
    ctx.strokeStyle = trailColor(n.state, alpha);
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(a.x * w, a.y * h);
    ctx.lineTo(b.x * w, b.y * h);
    ctx.stroke();
  }
  ctx.restore();
}

function drawNode(
  ctx: CanvasRenderingContext2D,
  n: Node,
  w: number,
  h: number,
  spotlight: boolean,
): void {
  const cx = n.x * w;
  const cy = n.y * h;
  const r = n.radius * (0.6 + n.z * 0.4) * (spotlight ? 3 : 1);
  const alpha = spotlight ? 1 : 0.25 + n.z * 0.55;

  ctx.save();
  // Glow.
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 2);
  grad.addColorStop(0, nodeColor(n.state, alpha));
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, r * 2, 0, Math.PI * 2);
  ctx.fill();

  // Core.
  ctx.fillStyle = nodeColor(n.state, alpha);
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function nodeColor(state: Node['state'], alpha: number): string {
  switch (state) {
    case 'working': return `rgba(255, 196, 120, ${alpha})`;
    case 'stuck':   return `rgba(220, 100, 100, ${alpha})`;
    case 'idle':    return `rgba(160, 160, 180, ${alpha})`;
    case 'done':    return `rgba(140, 220, 160, ${alpha})`;
    case 'new':     return `rgba(180, 160, 240, ${alpha})`;
  }
}

function trailColor(state: Node['state'], alpha: number): string {
  return nodeColor(state, alpha);
}
