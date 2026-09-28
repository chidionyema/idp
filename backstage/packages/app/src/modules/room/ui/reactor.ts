// reactor.ts — the physics that turns a diagram into a machine.
//
// WHY THIS FILE EXISTS. Measured 2026-09-19: the room drew twenty-four soft circles and their
// wakes. Every channel was real and read from a real Session, and it was still a picture of a
// fleet rather than an instrument for running one -- nothing in it varied with the WORK, only
// with the total. A node the size of a fist and a node the size of a pin both sat in the same
// flat space, and the space itself never moved.
//
// Four things below, each a rule rather than a decoration:
//
//   gravity   a busy agent WARPS THE SPACE AROUND ITSELF, so the room's shape is the fleet's
//             shape. This is the difference between drawing nodes and drawing a field.
//   jets      a burst of work fires particles when it HAPPENS. A trail shows where an agent has
//             been; a jet shows that it is firing, now, and how hard.
//   sonar     blast radius as a wave travelling outward from a node, so a cascade is SEEN before
//             it is read.
//   drill     a camera that moves. A 2100 interface does not show you a tooltip; it takes you
//             inside the thing you asked about and brings you back.
//
// Everything here is a pure function of (state, now). No DOM, so it can be believed on its own.

import type { Session } from '../../home/fleetBoard';

// ---------------------------------------------------------------- gravity

/**
 * How much a node bends the space around it.
 *
 * NOT proportional to events, and deliberately: a linear field means one session with 500
 * events distorts the page into a funnel and the other twenty-three vanish. sqrt compresses the
 * top -- the same reason the radius uses it -- so the field is legible whether the fleet is 24
 * fresh agents or one busy and twenty-three quiet.
 */
export function gravityOf(session: Session): number {
  // `Number(...) || 0` rather than `?? 0`: a non-numeric `event_count` (a string from a ledger
  // written by something else) makes `Math.max(0, NaN)` NaN, and NaN propagates through
  // `1 + NaN * 0.55` into `group.scale.set(NaN, NaN, NaN)` -- an invisible node, silently. Every
  // other reader of this field in the component guards with `|| 0`; this was the one that did not.
  const events = Math.max(0, Number(session.event_count) || 0);
  if (events <= 1) return 0;
  return Math.min(1, Math.sqrt(events / 400));
}

/**
 * The pull a node exerts on a point, as a unit-ish vector.
 *
 * Inverse-square with a floor: at the node's own centre the pull would be infinite, so the
 * divisor is clamped and the field is a well rather than a singularity.
 */
export function pullToward(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  strength: number,
): { dx: number; dy: number; force: number } {
  const dx = bx - ax;
  const dy = by - ay;
  const dist = Math.hypot(dx, dy) || 0.0001;
  const force = strength / Math.max(0.08, dist * dist);
  return { dx: dx / dist, dy: dy / dist, force };
}

// ---------------------------------------------------------------- jets

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  /** 1 → born, 0 → gone. Multiplied into alpha at draw time. */
  life: number;
  /** Points back at the node that fired it, so a particle can be tinted as it flies. */
  owner: string;
}

/**
 * Fire a burst, scaled to how much work arrived.
 *
 * THE RULE THAT KEEPS THIS HONEST: the number of particles is the number of events that ACTUALLY
 * ARRIVED since the last frame, not a sine wave standing in for activity. A session that emitted
 * nothing fires nothing -- so a quiet room is genuinely still, and a burst means work, not a
 * nice-looking animation.
 */
export function fire(
  out: Particle[],
  x: number,
  y: number,
  owner: string,
  arrived: number,
  activity: Session['activity'],
): void {
  if (arrived <= 0) return;
  // Five per arrived event, capped: a session that suddenly gains 200 events should look like an
  // eruption, not like a browser tab that has stopped responding.
  const n = Math.min(48, Math.max(2, arrived * 5));
  // Direction is derived from the owner id so two agents firing in the same frame do not produce
  // two identical cones stacked on top of each other.
  const seed = hash(owner);
  const spread = activity === 'stuck' ? 0.35 : 1.5;
  for (let i = 0; i < n; i++) {
    const a = ((seed + i * 97) % 360) * (Math.PI / 180) + (i / n) * 0.7;
    // ROOM UNITS PER SECOND, which is the unit `stepParticles` integrates in.
    //
    // The original used ~0.00035 per millisecond, which over a particle's ~1.4s life is about
    // 0.4 world units -- against a scene radius of 35 and a node glow of 2.5. The jets existed and
    // were effectively invisible; worse, they were INVISIBLE BY DESIGN REVIEW, because a number
    // that looks plausible in isolation (`0.00035`) reads as fine until it is multiplied out.
    //
    // 8-24 u/s crosses a visible fraction of the room during one lifetime.
    const speed =
      (8 + ((seed >> (i % 8)) % 40) * 0.4) * (activity === 'stuck' ? 0.35 : 1);
    out.push({
      x,
      y,
      vx: Math.cos(a) * speed,
      vy: Math.sin(a) * speed * (0.4 + spread * 0.3),
      life: 1,
      owner,
    });
  }
}

/** Advance every particle one step and drop the dead ones in place. */
export function stepParticles(particles: Particle[], dt: number): void {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    // Drag, so a jet blooms and settles rather than flying off the room.
    //
    // RAISED TO `dt/16.7`, i.e. normalised to one 60fps frame. The original applied 0.985 ONCE PER
    // CALL, so at 30fps a particle travelled roughly twice as far as at 60 -- the animation's shape
    // depended on the machine's frame rate, which is the kind of defect that never reproduces on
    // the developer's hardware.
    const drag = Math.pow(0.94, dt / 16.7);
    p.vx *= drag;
    p.vy *= drag;
    p.life -= dt / 1400;
    if (p.life <= 0) particles.splice(i, 1);
  }
  // A hard cap so a fleet-wide burst cannot grow without bound.
  if (particles.length > 1400) particles.splice(0, particles.length - 1400);
}

// ---------------------------------------------------------------- sonar

export interface Pulse {
  /** Whose cascade this is. Mutable: aiming at a new node restarts the wave. */
  id: string;
  /** 0 → just fired, 1 → finished travelling. */
  t: number;
}

/** How long one ping takes to cross the room, in ms. */
// ---------------------------------------------------------------- motion
//
// THE FOUR STATES ARE TOLD APART BY MOTION, NOT BY COLOUR.
//
// From docs/specs/2026-09-18-fleet-interface-design.md, where three frontier models converged
// with no coordination on the same requirement: "tables and cards force serial reading. A fleet
// of 30 agents cannot be read; it must be SEEN", and motion is what carries the meaning. Their
// named worst mistake, verbatim: "uniform 'running' state... the interface's whole value is
// discriminating the four".
//
// Measured in the Reactor on 2026-09-19: every node bobbed with the SAME `Math.sin(time*2)`
// regardless of state, so an agent stuck in a retry loop moved exactly like one thinking. The
// colour was honest; the motion was decoration. This is the fix.
//
// The design's table, implemented literally:
//
//   thinking  slow 4s inhale/exhale, ring stays lit        "it is breathing"
//   waiting   ring goes dashed, node drifts toward dep     "the drift is the tell"
//   stuck     ring desaturates, node jitters at 8Hz        "caught pre-attentively"
//   finished  breathing stops, ring closes, node sinks 8px "sinking is terminal"
//
// Everything here is a pure function of (activity, now, seed): no DOM, no THREE, no state, so
// the motion can be believed (and tested) on its own. `seed` is a per-node constant so two
// agents in the same state move out of phase rather than as a chorus.

export type Activity = 'thinking' | 'waiting' | 'stuck' | 'finished';

export interface NodeMotion {
  /** Vertical offset in world units. Negative is down. */
  dy: number;
  /** Ring rotation rates (radians/sec) for x and y. */
  ringX: number;
  ringY: number;
  /** Glow opacity target, 0..1. */
  glow: number;
  /** Ring opacity target, 0..1. A dashed-looking dim ring reads as "not turning". */
  ring: number;
  /** Uniform scale multiplier on top of baseScale. */
  scale: number;
}

/** Seconds for one full inhale/exhale. The design says "slow 4s". */
export const BREATH_S = 4;

/** 8Hz, the design's jitter frequency -- fast enough to catch peripheral vision. */
export const JITTER_HZ = 8;

/** How far a finished node sinks, in world units. The design says 8px at screen scale. */
export const SINK_UNITS = 2.2;

/**
 * The motion for one node, given its activity.
 *
 * `seed` should be stable per node (its index is enough) so identical states do not move in
 * lockstep -- a chorus of twenty breathing agents reads as one machine, not twenty.
 */
export function motionOf(activity: Activity, now: number, seed = 0): NodeMotion {
  const phase = (seed % 16) / 16;

  switch (activity) {
    case 'thinking': {
      // Breathing. Slow, wide, calm -- the only state that moves smoothly, which is what makes
      // it distinguishable from stuck at a glance.
      const t = (now / BREATH_S + phase) * Math.PI * 2;
      const breath = Math.sin(t);
      return {
        dy: breath * 0.35,
        ringX: 0.18,
        ringY: 0.12,
        glow: 0.16 + breath * 0.06,
        ring: 0.42,
        scale: 1 + breath * 0.03,
      };
    }

    case 'waiting': {
      // Drift. A slow, ~2px/s glide and a dim ring -- "the drift is the tell". No breath: an
      // agent waiting on CI is not doing work, and moving like it is would be a lie.
      const t = (now * 0.12 + phase) * Math.PI * 2;
      return {
        dy: Math.sin(t) * 0.9,
        ringX: 0.02,
        ringY: 0.02,
        glow: 0.09,
        ring: 0.16,
        scale: 1,
      };
    }

    case 'stuck': {
      // Jitter. 8Hz, small amplitude, plus a faint scale shake. Deliberately the "ugliest"
      // motion so it wins peripheral attention over any breathing node.
      const t = now * JITTER_HZ * Math.PI * 2;
      // Two incommensurate frequencies so it never looks like a clean oscillation.
      const j = Math.sin(t) * 0.6 + Math.sin(t * 1.7 + phase) * 0.4;
      return {
        dy: j * 0.22,
        ringX: 3.2,
        ringY: 2.4,
        glow: 0.2 + Math.abs(j) * 0.12,
        ring: 0.5,
        scale: 1 + j * 0.015,
      };
    }

    case 'finished':
    default: {
      // Terminal. No breath, no spin; it sinks and stays. `now` is unused on purpose: a finished
      // agent is the one node whose motion does not change, which is what "done" looks like.
      return {
        dy: -SINK_UNITS * 0.35,
        ringX: 0,
        ringY: 0,
        glow: 0.05,
        ring: 0.7,
        scale: 0.92,
      };
    }
  }
}

/**
 * The fleet ticker, from the design: a fixed-position scan line, not a dashboard.
 *
 *   "a controller scans 40 strips in two seconds because position never moves"
 *
 * One line, always the same shape, so the eye lands on the NUMBER that changed.
 */
export function tickerLine(counts: Record<Activity, number>, spendPerMin: number): string {
  // NO DOLLAR FIGURE. The design spec is explicit: "no dollar figure anywhere except on tap."
  // The rate is carried by the BURN BAR instead -- see `burnBar` below -- because a rate is
  // perceived rather than read, and a number in a permanent scan line competes with the four state
  // counts that a person actually acts on.
  void spendPerMin;
  const parts = [
    `${counts.thinking} thinking`,
    `${counts.waiting} waiting`,
    `${counts.stuck} stuck`,
    `${counts.finished} done`,
  ];
  // `needs you` is first because it is the only number a human must act on.
  const needsYou = counts.stuck > 0 ? `${counts.stuck} NEEDS YOU · ` : '';
  return `${needsYou}${parts.join('  ·  ')}`;
}

export const PULSE_MS = 2400;

/**
 * How far a ping has travelled, as a fraction of the room's diagonal.
 *
 * The ping is measured in ROOM, not in pixels: the same cascade reads identically on a laptop
 * and on a wall display, which pixels would not give.
 */
export function pulseRadius(p: Pulse): number {
  return Math.min(1.25, p.t * 1.25);
}

// ---------------------------------------------------------------- drill camera

export interface Camera {
  /** Where the camera is looking, as a fraction of the room. */
  x: number;
  y: number;
  /** 1 → the whole fleet, 3.2 → inside one agent. */
  zoom: number;
}

export const WIDE: Camera = { x: 0.5, y: 0.5, zoom: 1 };

/**
 * Ease a camera toward a target.
 *
 * Exponential rather than linear so the last few percent of the move are quick and the arrival
 * is soft. A linear camera into a node reads as a cut; this reads as a push in, which is what
 * makes the transition feel like movement through a space rather than a redraw.
 */
export function easeCamera(from: Camera, to: Camera, dt: number): Camera {
  const k = 1 - Math.pow(0.002, dt / 1000);
  return {
    x: from.x + (to.x - from.x) * k,
    y: from.y + (to.y - from.y) * k,
    zoom: from.zoom + (to.zoom - from.zoom) * k,
  };
}

/** The camera that puts one node in the middle of the room at drill depth. */
export function cameraOn(x: number, y: number): Camera {
  return { x, y, zoom: 3.2 };
}

// ---------------------------------------------------------------- misc

/** Stable 32-bit hash of a string. Only used to decorrelate agent directions. */
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}


// ---------------------------------------------------------------- burn bar

/** Turn a spend rate into what a bar should look like, without printing a number. */
export function burnBar(spendPerMin: number, totalSpend: number): {
  /** 0..1 across the bar's width. */
  fill: number;
  /** 0..1, how hot the leading edge glows. THIS is the rate. */
  heat: number;
  /** A word for the accessible label and the hover tooltip -- the only place a figure may appear. */
  label: string;
} {
  // The denominator is a rate this estate actually reaches on a busy day; without one the bar would
  // be pinned at zero and carry nothing. It is a DISPLAY constant, named, not a claim about cost.
  const HOT = 8.0;   // $/min at which the edge is fully hot
  const FULL = 40;   // $ total at which the bar is full
  const heat = Math.max(0, Math.min(1, spendPerMin / HOT));
  const fill = Math.max(0, Math.min(1, totalSpend / FULL));
  return {
    fill,
    heat,
    label:
      spendPerMin > 0
        ? `burning $${spendPerMin.toFixed(2)}/min · $${totalSpend.toFixed(2)} today`
        : `idle · $${totalSpend.toFixed(2)} today`,
  };
}
