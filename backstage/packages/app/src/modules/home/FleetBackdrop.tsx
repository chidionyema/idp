/**
 * <FleetBackdrop/>: the live fleet, drawn behind the estate face, so /face is never an empty room.
 *
 * One point of light per real session from `GET /sessions` -- the same endpoint the board and the
 * voice speak from -- and nothing invented: no session, no point. Motion is `motionOf` from the
 * room's reactor, so a node here moves exactly as it does on /fleet: working breathes, waiting
 * drifts, stuck jitters, finished sinks. Distance from the face is the state: working agents
 * crowd close, finished ones fade to the edge, so how busy the estate is reads at a glance.
 */
import { useEffect, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/core-plugin-api';
import type { Session, SessionsEnvelope } from './fleetBoard';
import { gravityOf, motionOf, type Activity } from '../room/ui/reactor';

const POLL_MS = 15_000;
const MAX_NODES = 600;

// Ring (as a fraction of the half-diagonal) and colour per state. Stuck sits close to the face
// on purpose: it is the one a person has to see.
const BAND: Record<Activity, { r: number; spread: number; rgb: string }> = {
  stuck: { r: 0.42, spread: 0.08, rgb: '255,107,107' },
  thinking: { r: 0.5, spread: 0.12, rgb: '127,209,185' },
  waiting: { r: 0.72, spread: 0.14, rgb: '138,160,200' },
  finished: { r: 0.92, spread: 0.1, rgb: '90,104,128' },
};

function activityOf(s: Session): Activity {
  const a = s.activity;
  return a === 'thinking' || a === 'waiting' || a === 'stuck' ? a : 'finished';
}

/** A stable 0..1 from a session id, so a node keeps its place across polls. */
function hash01(id: string, salt = 0): number {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return ((h >>> 0) % 10_000) / 10_000;
}

export default function FleetBackdrop() {
  const fetchApi = useApi(fetchApiRef);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const sessions = useRef<Session[]>([]);
  const [line, setLine] = useState('');

  useEffect(() => {
    let gone = false;
    const load = async () => {
      try {
        const res = await fetchApi.fetch('plugin://proxy/fleetview/sessions');
        const env = (await res.json()) as SessionsEnvelope;
        if (gone || !env.available) return;
        const all = env.sessions ?? [];
        sessions.current = all.slice(0, MAX_NODES);
        const n = (a: Activity) => all.filter((s) => activityOf(s) === a).length;
        const stuck = n('stuck');
        setLine(
          `${all.length} agents · ${n('thinking')} working${stuck ? ` · ${stuck} stuck` : ''}`,
        );
      } catch {
        /* the backdrop is ambience; the face and voice work without it */
      }
    };
    load();
    const t = setInterval(load, POLL_MS);
    return () => {
      gone = true;
      clearInterval(t);
    };
  }, [fetchApi]);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext('2d');
    if (!el || !ctx) return undefined;
    const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    const draw = (ms: number) => {
      const dpr = window.devicePixelRatio || 1;
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (el.width !== Math.round(w * dpr) || el.height !== Math.round(h * dpr)) {
        el.width = Math.round(w * dpr);
        el.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const now = still ? 0 : ms / 1000;
      const cx = w / 2;
      const cy = h * 0.4;
      const reach = Math.hypot(w, h) / 2;
      const spin = now * ((Math.PI * 2) / 240); // one slow turn every four minutes
      sessions.current.forEach((s, i) => {
        const a = activityOf(s);
        const band = BAND[a];
        const id = s.session_id || String(i);
        const m = motionOf(a, now, i);
        const r = reach * (band.r + (hash01(id, 1) - 0.5) * band.spread);
        const ang = hash01(id) * Math.PI * 2 + spin * (a === 'finished' ? 0.4 : 1);
        const x = cx + Math.cos(ang) * r + m.ringX * Math.sin(now * 3 + i);
        const y = cy + Math.sin(ang) * r * 0.8 - m.dy * 4;
        const size = (1.6 + gravityOf(s) * 3.5) * m.scale;
        const glow = Math.min(1, 0.35 + m.glow * 3);
        const g = ctx.createRadialGradient(x, y, 0, x, y, size * 4);
        g.addColorStop(0, `rgba(${band.rgb},${glow})`);
        g.addColorStop(1, `rgba(${band.rgb},0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, size * 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgba(${band.rgb},${Math.min(1, glow + 0.3)})`;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      });
      if (!still) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    // Reduced motion still redraws when the fleet changes, just without animating between polls.
    const t = still ? setInterval(() => requestAnimationFrame(draw), POLL_MS) : undefined;
    return () => {
      cancelAnimationFrame(raf);
      if (t) clearInterval(t);
    };
  }, []);

  return (
    <div aria-hidden="true" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <canvas ref={canvas} style={{ width: '100%', height: '100%', opacity: 0.85 }} />
      {line && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(env(safe-area-inset-top, 0px) + 14px)',
            width: '100%',
            textAlign: 'center',
            fontSize: 12,
            letterSpacing: 1,
            opacity: 0.55,
          }}
        >
          {line}
        </div>
      )}
    </div>
  );
}
