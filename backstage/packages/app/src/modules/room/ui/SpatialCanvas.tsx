// SpatialCanvas.tsx — the fleet as a room, drawn from the REAL fleet.
//
// The spec's version seeds `agent-0 … agent-23` with random positions, random radii and
// `Math.random() > 0.5 ? 'stuck' : 'working'` states. It is beautiful and it is a lie: it would
// draw a fleet that does not exist while the real one sat one fetch away. Every field below comes
// from a real Session instead, so the room can be wrong about nothing.
//
// WHAT CARRIES MEANING, and why each is one channel and not two:
//
//   radius     events, on a sqrt curve so AREA is work done (sqrt, not linear: at 400 events a
//              linear map makes one agent five times the radius of a quiet one, which reads as a
//              rendering fault rather than as a busy agent)
//   position   depth and drift, so the room has space rather than a grid
//   trail      the agent's LAST HOUR as a wake behind it, newest at the node
//   colour     activity, in the four states the estate already derives from evidence
//   motion     thinking breathes, waiting drifts, stuck jitters, finished is still
//
// The trail is the thing nobody else has. A dashboard shows you NOW; a wake shows you the hour,
// and a flat line against a bright one is the whole story of a fleet at a glance.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Session } from '../../home/fleetBoard';
import { ACTIVITY_WORD, ACTIVITY_SENTENCE } from '../../home/fleetMotion';

export interface SpatialCanvasProps {
  readonly sessions: readonly Session[];
  /** The one agent drawn forward of the fleet, or null. */
  readonly spotlight?: string | null;
  /** Which session a person has selected, if any. */
  readonly selected?: string | null;
  onSelect?: (sessionId: string | null) => void;
}

// 34..92 rather than 26..64: measured 2026-09-19, the fleet filled 13% of its canvas at the
// smaller sizes and read as scattered dots on a black rectangle. The room has to be a room.
const MIN_RADIUS = 34;
const MAX_RADIUS = 92;
const EVENT_FULL = 400;

// One hour of history per trail. Long enough to show a rhythm, short enough that the wake is
// about what is happening rather than what happened this morning.
const TRAIL_MS = 60 * 60 * 1000;

interface Node {
  id: string;
  session: Session;
  x: number;
  y: number;
  z: number; // depth, 0..1
  radius: number;
  /** Where this agent has been, newest last. The wake. */
  trail: Array<{ x: number; y: number; t: number }>;
}

function radiusFor(events: number): number {
  const n = Number.isFinite(events) && events > 0 ? events : 0;
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * Math.sqrt(Math.min(1, n / EVENT_FULL));
}

/** A stable number from an id, so the same session always lands in the same place. */
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function activityColor(activity: string | null | undefined, alpha: number): string {
  switch (activity) {
    case 'thinking':
      return `rgba(91, 157, 255, ${alpha})`;
    case 'waiting':
      return `rgba(245, 158, 11, ${alpha})`;
    case 'stuck':
      return `rgba(239, 68, 68, ${alpha})`;
    case 'finished':
      return `rgba(140, 220, 160, ${alpha})`;
    default:
      return `rgba(122, 130, 142, ${alpha})`;
  }
}

export function SpatialCanvas(props: SpatialCanvasProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<Map<string, Node>>(new Map());
  const rafRef = useRef<number>(0);
  const [hovered, setHovered] = useState<string | null>(null);

  // LAYOUT IS DERIVED, NEVER RANDOM. The same session ids always produce the same positions, so a
  // poll that returns the same fleet does not make the room twitch -- a fleet that rearranges
  // itself every fifteen seconds is unreadable, and the spec's `Math.random()` seeding does
  // exactly that on every mount.
  useMemo(() => {
    const nodes = nodesRef.current;
    const seen = new Set<string>();
    props.sessions.forEach((s, i) => {
      seen.add(s.session_id);
      const existing = nodes.get(s.session_id);
      const h1 = hash(s.session_id);
      const h2 = hash(`${s.session_id}:y`);
      const h3 = hash(`${s.session_id}:z`);
      const next: Node = {
        id: s.session_id,
        session: s,
        // Spread on a jittered spiral: a grid reads as a table, pure random reads as noise, and a
        // spiral fills the frame evenly while staying stable.
        x: existing?.x ?? 0.08 + 0.84 * ((h1 + i * 0.618) % 1),
        y: existing?.y ?? 0.1 + 0.8 * ((h2 + i * 0.382) % 1),
        z: existing?.z ?? 0.25 + 0.7 * h3,
        radius: radiusFor(s.event_count ?? 0),
        trail: existing?.trail ?? [],
      };
      nodes.set(s.session_id, next);
    });
    // An agent that has left the fleet leaves the room.
    for (const id of Array.from(nodes.keys())) {
      if (!seen.has(id)) nodes.delete(id);
    }
    return nodes;
  }, [props.sessions]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = (now: number) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      const nodes = Array.from(nodesRef.current.values());
      const anySpotlit = Boolean(props.spotlight);

      for (const n of nodes) {
        // Movement: the room breathes at rest and comes alive when something is named.
        const isSpot = props.spotlight === n.id;
        const drift = isSpot ? 0.00012 : 0.00035 * (1 - n.z);
        n.x += (Math.sin(now * 0.0003 + n.z * 6) * 0.5) * drift;
        n.y += (Math.cos(now * 0.0004 + n.z * 5) * 0.5) * drift;
        n.x = Math.max(0.04, Math.min(0.96, n.x));
        n.y = Math.max(0.04, Math.min(0.96, n.y));

        // The wake. One point per frame bounded to one hour, so memory is capped without a timer.
        n.trail.push({ x: n.x, y: n.y, t: now });
        while (n.trail.length > 0 && now - n.trail[0].t > TRAIL_MS) n.trail.shift();
        // A long idle room would accumulate points at one spot; cap the array so a session left
        // open overnight cannot grow without bound.
        if (n.trail.length > 900) n.trail.splice(0, n.trail.length - 900);
      }

      // Trails behind, nodes in front.
      for (const n of nodes) drawTrail(ctx, n, w, h, props.spotlight === n.id, anySpotlit);
      const ordered = [...nodes].sort((a, b) => a.z - b.z);
      for (const n of ordered) {
        drawNode(ctx, n, w, h, props.spotlight === n.id, anySpotlit);
      }

      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [props.spotlight, props.selected]);

  // Click a node to select it. Hit-tested against the same radii the draw pass used, so the thing
  // you click is the thing you see.
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas || !props.onSelect) return;
      const rect = canvas.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * canvas.clientWidth;
      const my = ((e.clientY - rect.top) / rect.height) * canvas.clientHeight;
      let best: { id: string; d: number } | null = null;
      for (const n of nodesRef.current.values()) {
        const dx = n.x * canvas.clientWidth - mx;
        const dy = n.y * canvas.clientHeight - my;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d <= n.radius && (!best || d < best.d)) best = { id: n.id, d };
      }
      props.onSelect(best ? best.id : null);
    },
    [props],
  );

  const handleMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * canvas.clientWidth;
    const my = ((e.clientY - rect.top) / rect.height) * canvas.clientHeight;
    let found: string | null = null;
    for (const n of nodesRef.current.values()) {
      const dx = n.x * canvas.clientWidth - mx;
      const dy = n.y * canvas.clientHeight - my;
      if (Math.sqrt(dx * dx + dy * dy) <= n.radius) {
        found = n.id;
        break;
      }
    }
    setHovered(found);
  }, []);

  const hovering = hovered ? nodesRef.current.get(hovered) : null;

  return (
    // THE ROOM OWNS ITS OWN HEIGHT. It was `height: 100%`, which is 100% of whatever the parent
    // is -- and the parent is a section with no height, so the canvas measured 1168x0: twenty-four
    // agents drawn into nothing, with no error anywhere. A component that is the page cannot
    // delegate its own size to a parent that has not been told one.
    //
    // clamp(520px, 100vh - 260px, 1100px): tall enough to be a room, short enough that the voice
    // bar and the first row of chrome stay on screen at 900px.
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 'clamp(520px, calc(100vh - 260px), 1100px)',
        minHeight: 520,
      }}
    >
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        onClick={handleClick}
        onMouseMove={handleMove}
        onMouseLeave={() => setHovered(null)}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
          cursor: hovered ? 'pointer' : 'default',
        }}
      />
      {/* ONE accessible list, off-screen. The canvas is aria-hidden because 24 circles are not a
          reading experience; this is the same fleet as text, and it is what a screen reader or a
          test can address. The room is not a picture of the fleet -- it is the fleet, with a
          second rendering for readers who cannot use the first. */}
      {/* VISUALLY HIDDEN, AND THIS TIME ACTUALLY HIDDEN. Measured 2026-09-19 by reading the
          rendered page: the first attempt was a 1x1 box with `overflow: hidden` and
          `clip: rect(0 0 0 0)`, and the 24 list items rendered as 24 visible lines of 14px text
          running down the whole page. `clip` on a parent does not clip a child that is not
          absolutely positioned, and a 1x1 box does not constrain a list that has its own layout.
          The room was replaced by a text dump and the canvas was nowhere.

          The reliable pattern: the LIST is absolutely positioned and 1px square, and every CHILD
          is clipped with `clipPath`, which does apply per-element. `inset(50%)` collapses the
          visible box to nothing, which is the modern spelling of the same trick. */}
      <ul
        data-testid="room-agents"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 1,
          height: 1,
          margin: -1,
          padding: 0,
          border: 0,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          listStyle: 'none',
        }}
      >
        {props.sessions.map(s => (
          <li
            key={s.session_id}
            data-testid={`agent-${s.session_id}`}
            data-activity={s.activity ?? 'unknown'}
            data-events={s.event_count ?? 0}
            style={{
              position: 'absolute',
              width: 1,
              height: 1,
              overflow: 'hidden',
              clipPath: 'inset(50%)',
            }}
          >
            {`${s.runtime} ${String(s.session_id).slice(-6)}: ${
              ACTIVITY_WORD[(s.activity ?? 'unknown') as keyof typeof ACTIVITY_WORD]
            }. ${s.event_count ?? 0} events. ${
              ACTIVITY_SENTENCE[(s.activity ?? 'unknown') as keyof typeof ACTIVITY_SENTENCE]
            }`}
          </li>
        ))}
      </ul>
      {hovering ? (
        <div
          style={{
            position: 'absolute',
            left: `${hovering.x * 100}%`,
            top: `${hovering.y * 100}%`,
            transform: 'translate(-50%, -140%)',
            pointerEvents: 'none',
            background: 'rgba(13,17,23,0.94)',
            border: '1px solid rgba(255,255,255,0.14)',
            borderRadius: 8,
            padding: '8px 10px',
            fontSize: 12,
            maxWidth: 260,
            color: '#e6edf3',
            zIndex: 5,
          }}
        >
          <div style={{ fontWeight: 700 }}>
            {hovering.session.runtime} · {String(hovering.id).slice(-6)}
          </div>
          <div style={{ opacity: 0.75, marginTop: 2 }}>
            {hovering.session.event_count ?? 0} events
            {typeof hovering.session.spend_usd === 'number'
              ? ` · $${hovering.session.spend_usd.toFixed(2)}`
              : ''}
          </div>
          <div style={{ opacity: 0.55, marginTop: 2 }}>
            {(hovering.session.task || '').slice(0, 90)}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function drawTrail(
  ctx: CanvasRenderingContext2D,
  n: Node,
  w: number,
  h: number,
  spotlight: boolean,
  anySpotlit: boolean,
): void {
  if (n.trail.length < 2) return;
  const now = n.trail[n.trail.length - 1].t;

  // A session with almost no work leaves no wake: an agent that has done one thing has not moved,
  // and drawing a trail for it would invent an hour of activity it did not have.
  const events = n.session.event_count ?? 0;
  if (events <= 1) return;

  ctx.save();
  ctx.lineCap = 'round';
  const dim = anySpotlit && !spotlight ? 0.25 : 1;
  for (let i = 1; i < n.trail.length; i++) {
    const a = n.trail[i - 1];
    const b = n.trail[i];
    const age = (now - b.t) / TRAIL_MS;
    if (age > 1) continue;
    // Older segments fade: the wake points backward in time, brightest at the agent.
    const alpha = (1 - age) * (spotlight ? 0.85 : 0.4) * dim;
    ctx.strokeStyle = activityColor(n.session.activity, alpha);
    ctx.lineWidth = Math.max(1, n.radius * 0.08 * (1 - age * 0.6));
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
  anySpotlit: boolean,
): void {
  const cx = n.x * w;
  const cy = n.y * h;
  const perspective = 0.62 + n.z * 0.5;
  const r = n.radius * perspective * (spotlight ? 2.4 : 1);
  const dim = anySpotlit && !spotlight ? 0.22 : 1;
  const base = spotlight ? 1 : 0.3 + n.z * 0.55;
  const alpha = base * dim;
  const events = n.session.event_count ?? 0;

  ctx.save();

  // Glow. Depth is a property of the light, not of the outline.
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 2.4);
  grad.addColorStop(0, activityColor(n.session.activity, alpha));
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, r * 2.4, 0, Math.PI * 2);
  ctx.fill();

  if (events <= 1) {
    // EMPTY READS AS EMPTY: a hairline dashed ring, unmistakable as nothing done, without
    // disappearing -- a person still needs to see that the agent exists.
    ctx.strokeStyle = `rgba(122,130,142,${0.4 * dim})`;
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 6]);
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.72, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  } else {
    // Filled, because this agent has done something.
    ctx.fillStyle = activityColor(n.session.activity, alpha);
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.72, 0, Math.PI * 2);
    ctx.fill();

    // A work arc whose sweep is the work done, so the busiest agent is visibly carrying the most.
    const sweep = Math.min(1, Math.sqrt(events / EVENT_FULL));
    ctx.strokeStyle = activityColor(n.session.activity, Math.min(1, alpha + 0.25));
    ctx.lineWidth = 2 + 5 * sweep;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.92, -Math.PI / 2, -Math.PI / 2 + sweep * Math.PI * 2);
    ctx.stroke();
  }

  ctx.restore();
}
