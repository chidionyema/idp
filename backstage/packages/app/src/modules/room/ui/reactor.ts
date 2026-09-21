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
  const events = Math.max(0, session.event_count ?? 0);
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
    const speed = (0.00035 + ((seed >> (i % 8)) % 40) / 40000) * (activity === 'stuck' ? 0.4 : 1);
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
    p.vx *= 0.985;
    p.vy *= 0.985;
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
