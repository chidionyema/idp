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
import {
  type Camera,
  type Particle,
  type Pulse,
  WIDE,
  cameraOn,
  easeCamera,
  fire,
  gravityOf,
  PULSE_MS,
  pulseRadius,
  stepParticles,
} from './reactor';

export interface SpatialCanvasProps {
  readonly sessions: readonly Session[];
  /** The one agent drawn forward of the fleet, or null. */
  readonly spotlight?: string | null;
  /** Which session a person has selected, if any. */
  readonly selected?: string | null;
  onSelect?: (sessionId: string | null) => void;
  /**
   * WHERE the selected node is, in the canvas's own pixel space.
   *
   * A radial menu anchored on a node needs the node's position, and only the canvas knows it --
   * the positions are derived from a seeded layout inside this component. Reporting it upward is
   * what lets the menu snap onto the agent instead of living in a bar at the bottom of the page,
   * which is the difference between one gesture and a journey across the screen.
   */
  onSelectedPosition?: (pos: { x: number; y: number } | null) => void;
  /**
   * WHAT THE POINTER IS OVER, which is what makes "kill it" mean something.
   *
   * Without this, voice is a separate channel: the person looks at a red node and says "stop
   * that one", and the system has to guess from the sentence which of twenty-four agents was
   * meant. Reported from the canvas, the referent is not inferred at all -- it is the node under
   * the cursor, and the sentence only has to say what to DO, not which one to do it to.
   *
   * It is reported as a referent rather than a selection on purpose: hovering must not select,
   * or merely moving the mouse across the room would open menus and move the camera.
   */
  onHover?: (sessionId: string | null) => void;
  /**
   * EVENTS PER SECOND, keyed by session id -- the live stream's own velocity.
   *
   * This is what turns the room from a picture into an instrument. Without it the only thing
   * that can vary is a total, and a total does not move. It arrives already counted from the
   * stream, so an agent that emitted nothing this second fires nothing: a quiet room is
   * genuinely still, and a burst means work arrived rather than that an animation is running.
   */
  readonly eventRate?: Readonly<Record<string, number>>;
  /**
   * Fire a blast-radius ping for this session id. Null cancels.
   *
   * The cascade itself is drawn from the dependency graph the backend already answers; what this
   * prop carries is only WHICH node asked. The canvas owns the travelling wave, because a wave
   * has to be drawn every frame and asking React to re-render for it would be absurd.
   */
  readonly pingFor?: string | null;
  /** Called when the ping completes, so the page can clear its own state. */
  onPingDone?: () => void;
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
  /** How hard this node bends the space around it, recomputed every frame from its work. */
  gravity: number;
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

/** A wake of the right LENGTH for the work done, drawn before the first frame. */
function seedTrail(
  x: number,
  y: number,
  events: number,
  seed: number,
): Array<{ x: number; y: number; t: number }> {
  // One point per ~3 events, capped: a trail is a shape, not a data record, and 453 points at
  // one pixel each is a smudge rather than a ribbon.
  const points = Math.min(28, Math.max(0, Math.floor(events / 16)));
  if (points < 2) return [];
  const now = Date.now();
  const out: Array<{ x: number; y: number; t: number }> = [];
  for (let k = points; k >= 0; k--) {
    const age = k / points; // 1 = oldest
    // The wake points backward from the agent with a slow curve, so it reads as a path taken
    // rather than as a straight line.
    const bend = (seed - 0.5) * 0.16;
    out.push({
      x: x - bend * age * (1 - age * 0.5),
      y: y - 0.05 * age + bend * 0.4 * age,
      // Time travels forward, so the newest point is now and the oldest is an hour back. The
      // draw pass fades by age, which is what makes the wake point backward.
      t: now - age * TRAIL_MS * 0.9,
    });
  }
  return out;
}

export function SpatialCanvas(props: SpatialCanvasProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<Map<string, Node>>(new Map());
  /** Live particles. A ref, not state: they are redrawn every frame and never rendered by React. */
  const particlesRef = useRef<Particle[]>([]);
  /** The travelling sonar wave. Survives the effect re-running, which is what makes it travel. */
  const pulseRefOuter = useRef<Pulse>({ id: '', t: 0 });
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
        gravity: gravityOf(s),
        // SEEDED FROM REAL WORK. A trail that only grows from page-load is empty for the first
        // minute -- which is precisely when someone decides whether to be impressed. The wake's
        // length comes from `event_count`, which the API already returns, so an agent that has
        // done 453 events opens with a long ribbon and one that has done nothing opens empty.
        // It is the same fact the radius carries, drawn as history rather than as size.
        trail: existing?.trail?.length
          ? existing.trail
          : seedTrail(
              0.08 + 0.84 * ((h1 + i * 0.618) % 1),
              0.1 + 0.8 * ((h2 + i * 0.382) % 1),
              s.event_count ?? 0,
              h3,
            ),
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

    let lastFrame = 0;
    let camera: Camera = { ...WIDE };
    // THE WAVE IS A REF, AND THAT IS THE WHOLE POINT.
    //
    // Measured 2026-09-19: the wave drew for one frame and then died -- "8729 → 0 → 0 → 0", and
    // it looked like the source node was missing. It was not. This variable was a `const` inside
    // an effect whose dependency list includes `pingFor`, so pressing Blast RE-RAN the effect,
    // rebuilt `pulse` at `t: 0`, and the first frame of every new closure restarted the wave
    // from the centre. A travelling wave cannot live in a value that is recreated by the thing
    // that starts it.
    //
    // Held across runs, it survives the re-render and the wave actually travels.
    const pulseRef = pulseRefOuter;

    const draw = (now: number) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const dt = lastFrame ? Math.min(64, now - lastFrame) : 16;
      lastFrame = now;
      ctx.clearRect(0, 0, w, h);

      const nodes = Array.from(nodesRef.current.values());
      const anySpotlit = Boolean(props.spotlight);

      // ---- WHERE THE CAMERA WANTS TO BE ------------------------------------------------
      // Selecting an agent PUSHES THE CAMERA INTO IT. This is the drill-down: the macro room
      // becomes the micro one, because a tooltip about an agent is a caption and a camera
      // arriving at it is an answer. Dismissing pulls back out along the same path.
      const selectedNode = props.selected
        ? nodesRef.current.get(props.selected) ?? null
        : null;
      const want: Camera = selectedNode
        ? cameraOn(selectedNode.x, selectedNode.y)
        : WIDE;
      // The ping holds the camera wide: a cascade that travels off-screen answers nothing.
      camera = easeCamera(camera, props.pingFor ? WIDE : want, dt);

      // ---- THE FIELD ------------------------------------------------------------------
      // Busy agents warp the space around themselves, so every node is nudged toward every
      // heavier one. This is the difference between drawing twenty-four dots and drawing a
      // topology: the room's SHAPE is the fleet's shape, and it changes as the fleet changes.
      for (const n of nodes) {
        n.gravity = gravityOf(n.session);
      }
      const heavy = nodes.filter(n => n.gravity > 0);
      for (const n of nodes) {
        if (n.id === props.selected) continue; // the agent you are inside does not drift away
        let fx = 0;
        let fy = 0;
        for (const g of heavy) {
          if (g.id === n.id) continue;
          const dx = g.x - n.x;
          const dy = g.y - n.y;
          const dist = Math.hypot(dx, dy) || 0.001;
          // Only the neighbourhood pulls: an inverse square over the whole room would make one
          // busy session drag the entire fleet into a single point.
          if (dist > 0.42) continue;
          const force = (g.gravity * 0.000013) / Math.max(0.05, dist * dist);
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
        }
        n.x += fx * dt;
        n.y += fy * dt;
      }

      // ---- THE JETS -------------------------------------------------------------------
      // A burst fires on EVENTS ARRIVED, so nothing is animated that did not happen. The rate is
      // the stream's own count for this second; a session that emitted nothing fires nothing.
      const rate = props.eventRate ?? {};
      for (const n of nodes) {
        const arrived = rate[n.id] ?? 0;
        if (arrived > 0) {
          fire(particlesRef.current, n.x, n.y, n.id, arrived, n.session.activity);
        }
      }
      stepParticles(particlesRef.current, dt);

      for (const n of nodes) {
        // Movement: the room breathes at rest and comes alive when something is named.
        const isSpot = props.spotlight === n.id;
        // MEASURED 2026-09-19, by reading the canvas back as a brightness grid: the room drew
        // six soft blobs and NO trail at all. The movement was 0.00035 of the canvas per frame
        // -- about 1% a minute -- so every wake was a dot rather than a ribbon, and the one
        // thing here that a dashboard cannot do was invisible.
        //
        // 0.0016 is roughly 10% a minute: still a drift, not a jitter, and the eye reads it as a
        // ribbon within a few seconds of looking.
        const drift = isSpot ? 0.0006 : 0.0016 * (0.5 + n.z * 0.5);
        n.x += Math.sin(now * 0.00021 + n.z * 6) * drift;
        n.y += Math.cos(now * 0.00027 + n.z * 5) * drift;
        n.x = Math.max(0.04, Math.min(0.96, n.x));
        n.y = Math.max(0.04, Math.min(0.96, n.y));

        // The wake. One point per frame bounded to one hour, so memory is capped without a timer.
        n.trail.push({ x: n.x, y: n.y, t: now });
        while (n.trail.length > 0 && now - n.trail[0].t > TRAIL_MS) n.trail.shift();
        // A long idle room would accumulate points at one spot; cap the array so a session left
        // open overnight cannot grow without bound.
        if (n.trail.length > 900) n.trail.splice(0, n.trail.length - 900);
      }

      // ---- THE CAMERA -----------------------------------------------------------------
      ctx.save();
      const z = camera.zoom;
      ctx.translate(w / 2, h / 2);
      ctx.scale(z, z);
      ctx.translate(-camera.x * w, -camera.y * h);

      // The field itself, drawn before anything sits in it: a faint lattice that the gravity
      // displaces. Without it the warp is invisible -- you cannot see space bend unless there is
      // something in the space to bend.
      drawField(ctx, w, h, heavy, now);

      // Trails behind, nodes in front.
      for (const n of nodes) drawTrail(ctx, n, w, h, props.spotlight === n.id, anySpotlit);
      drawParticles(ctx, particlesRef.current, w, h);
      const ordered = [...nodes].sort((a, b) => a.z - b.z);
      for (const n of ordered) {
        drawNode(ctx, n, w, h, props.spotlight === n.id, anySpotlit);
      }
      ctx.restore();

      // ---- THE SONAR, outside the camera -----------------------------------------------
      // Drawn in screen space so the wave is the same thickness wherever the camera has pushed
      // in -- a cascade read from inside a node must still be legible.
      if (props.pingFor) {
        // A ping aimed at a NEW node restarts the wave; the same node carries on travelling.
        if (pulseRef.current.id !== props.pingFor) {
          pulseRef.current.id = props.pingFor;
          pulseRef.current.t = 0;
        }
        const src = nodesRef.current.get(props.pingFor);
        if (!src) {
          props.onPingDone?.();
        } else {
          pulseRef.current.t += dt / PULSE_MS;
          if (pulseRef.current.t >= 1.35) {
            pulseRef.current.t = 0;
            props.onPingDone?.();
          } else {
            drawPulse(ctx, src, nodes, w, h, pulseRef.current.t, camera);
          }
        }
      } else {
        // Reset only when the ping is actually cancelled, so a re-render does not rewind it.
        pulseRefOuter.current.t = 0;
      }

      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
    // THE DEPENDENCY LIST WAS A BUG, measured 2026-09-19. It listed only `spotlight` and
    // `selected`, so the render closure kept the `props` it was created with -- and pressing
    // Blast set `pingFor` on the PAGE while this loop carried on reading `pingFor: null`. The
    // sonar drew zero red pixels, six samples in a row, which is how it was caught.
    //
    // The rule this restores: every prop read inside the loop must be a dependency, because the
    // loop is a closure and a closure captures values, not variables.
  }, [props.spotlight, props.selected, props.eventRate, props.pingFor, props.onPingDone]);

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

  // Report the pointer's referent upward. Held in a ref so a page re-render does not need the
  // canvas to re-render, and only sent when it CHANGES: a mousemove fires dozens of times a
  // second and reporting the same id each time would re-render the page for nothing.
  const lastHover = useRef<string | null>(null);
  useEffect(() => {
    if (lastHover.current === hovered) return;
    lastHover.current = hovered;
    props.onHover?.(hovered);
  }, [hovered, props.onHover]);

  // Report the selected node's position whenever it moves, so the menu follows the agent it
  // belongs to rather than hanging in place while the node drifts out from under it.
  useEffect(() => {
    const report = props.onSelectedPosition;
    if (!report) return;
    const tick = () => {
      const id = props.selected;
      const n = id ? nodesRef.current.get(id) : null;
      const c = canvasRef.current;
      if (!n || !c) {
        report(null);
      } else {
        report({ x: n.x * c.clientWidth, y: n.y * c.clientHeight });
      }
      raf = requestAnimationFrame(tick);
    };
    let raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [props.selected, props.onSelectedPosition]);

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

/**
 * THE FIELD: a lattice that the heavy nodes bend.
 *
 * WHY DRAW ANYTHING AT ALL. Gravity that only moves the nodes is invisible -- the nodes would
 * simply sit somewhere and the reader would never know the space was warped, only that the layout
 * was odd. A grid gives the eye a reference, so the warp reads as the room being pulled rather
 * than as the nodes being badly placed.
 *
 * Cost is deliberately tiny: a 14x9 lattice is 126 short lines per frame, which is nothing even
 * on the integrated GPU of a laptop, and it is drawn at 6% alpha so it never competes with an
 * agent for attention.
 */
function drawField(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  heavy: readonly Node[],
  now: number,
): void {
  if (heavy.length === 0) return;
  const COLS = 14;
  const ROWS = 9;

  // Where a lattice point ends up after the heavy nodes have pulled on it.
  const warp = (gx: number, gy: number): [number, number] => {
    let x = gx;
    let y = gy;
    for (const g of heavy) {
      const dx = g.x - gx;
      const dy = g.y - gy;
      const dist = Math.hypot(dx, dy) || 0.001;
      if (dist > 0.5) continue;
      // Pulled TOWARD the mass, by an amount that falls off with distance, so the lattice
      // dimples into each busy agent instead of sliding uniformly.
      const pull = (g.gravity * 0.055) / Math.max(0.09, dist);
      x += (dx / dist) * pull;
      y += (dy / dist) * pull;
    }
    return [x * w, y * h];
  };

  ctx.save();
  // A slow shimmer, so a still room is not a dead one -- but small enough that it reads as
  // breathing rather than as noise.
  const shimmer = 0.045 + 0.015 * Math.sin(now * 0.0004);
  ctx.strokeStyle = `rgba(120,150,190,${shimmer})`;
  ctx.lineWidth = 1;

  for (let c = 0; c <= COLS; c++) {
    ctx.beginPath();
    for (let r = 0; r <= ROWS; r++) {
      const [px, py] = warp(c / COLS, r / ROWS);
      if (r === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  for (let r = 0; r <= ROWS; r++) {
    ctx.beginPath();
    for (let c = 0; c <= COLS; c++) {
      const [px, py] = warp(c / COLS, r / ROWS);
      if (c === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * THE JETS: work leaving an agent, drawn as a comet rather than a dot.
 *
 * Each particle is a two-point line from where it is to where it just was, so a fast particle
 * reads as a streak and a slow one as a grain. That single trick is the difference between
 * "sparkles" and "thrust".
 */
function drawParticles(
  ctx: CanvasRenderingContext2D,
  particles: readonly Particle[],
  w: number,
  h: number,
): void {
  if (particles.length === 0) return;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.globalCompositeOperation = 'lighter';
  for (const p of particles) {
    const a = Math.max(0, Math.min(1, p.life));
    // Warm, because this is output: the same family as the thinking colour, one step hotter.
    ctx.strokeStyle = `rgba(255,214,150,${a * 0.55})`;
    ctx.lineWidth = 1 + a * 1.6;
    ctx.beginPath();
    ctx.moveTo((p.x - p.vx * 12) * w, (p.y - p.vy * 12) * h);
    ctx.lineTo(p.x * w, p.y * h);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * THE SONAR: one wave leaving one node, and every node it has already reached lit as it passes.
 *
 * The point is to SEE a cascade before reading it. A list of affected session ids is a report;
 * a ring that travels outward and lights what it touches is the same fact in the form a person
 * can act on at a glance.
 */
function drawPulse(
  ctx: CanvasRenderingContext2D,
  src: Node,
  nodes: readonly Node[],
  w: number,
  h: number,
  t: number,
  camera: Camera,
): void {
  // Screen position: the pulse is drawn outside the camera transform, so the source has to be
  // projected through it by hand.
  const sx = (src.x - camera.x) * w * camera.zoom + w / 2;
  const sy = (src.y - camera.y) * h * camera.zoom + h / 2;
  const reach = pulseRadius({ id: src.id, t });
  const radius = reach * Math.hypot(w, h) * 0.55;

  ctx.save();
  // The travelling ring, brightest as it leaves and fading as it spends itself.
  const fade = Math.max(0, 1 - t);
  ctx.strokeStyle = `rgba(255,170,90,${fade * 0.75})`;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(sx, sy, radius, 0, Math.PI * 2);
  ctx.stroke();
  // A second, wider and fainter ring: one line reads as a drawn circle, two read as a wave.
  ctx.strokeStyle = `rgba(255,170,90,${fade * 0.22})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(sx, sy, radius * 1.06, 0, Math.PI * 2);
  ctx.stroke();

  // Everything the wave has already passed is marked, so the cascade accumulates rather than
  // flashing past.
  for (const n of nodes) {
    if (n.id === src.id) continue;
    const nx = (n.x - camera.x) * w * camera.zoom + w / 2;
    const ny = (n.y - camera.y) * h * camera.zoom + h / 2;
    const d = Math.hypot(nx - sx, ny - sy);
    if (d > radius) continue;
    // Caught in this wave: a bright halo that fades as the wave moves on.
    const caught = Math.max(0, 1 - (radius - d) / 160) * fade;
    ctx.strokeStyle = `rgba(255,120,120,${caught * 0.9})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(nx, ny, n.radius * 1.25, 0, Math.PI * 2);
    ctx.stroke();
    // And a tether back to the source: the cascade has a direction, and a direction needs a line.
    ctx.strokeStyle = `rgba(255,120,120,${caught * 0.35})`;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 5]);
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(nx, ny);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
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
    // EMPTY READS AS EMPTY: a hollow ring, unmistakable as nothing done, and VISIBLE. The first
    // version was a 1px dashed hairline at 40% opacity and it did not register at all -- the
    // room showed seven agents when the fleet has twenty-four, which is the opposite of telling
    // the truth about a fleet. Now 1.5px solid at 70%: clearly present, clearly empty.
    ctx.strokeStyle = `rgba(150,158,170,${0.7 * dim})`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.6, 0, Math.PI * 2);
    ctx.stroke();
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
