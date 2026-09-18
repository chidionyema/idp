import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { dark as T } from '../theme/tokens';
import type { Session } from './fleetBoard';
import type { Activity } from './fleetMotion';

/* ------------------------------------------------------------------ *
 * FleetCanvas
 *
 * A force-directed "ops board" for the fleet. The layout is computed
 * once per data change and then frozen: a map that rearranges itself on
 * every poll is unreadable, and stability beats beauty in ops tooling.
 * ------------------------------------------------------------------ */

// --- design tokens we reference often enough to alias -----------------
const STATE_COLOR: Record<string, string> = {
  running: '#22c55e',
  paused: '#f59e0b',
  failed: '#ef4444',
  stopped: T.textMuted,
  unknown: T.textMuted,
};

const ACTIVITY_WORD: Record<string, string> = {
  thinking: 'thinking',
  waiting: 'waiting',
  stuck: 'stuck',
  finished: 'finished',
  unknown: 'unknown',
};

// The four motions map to existing keyframes in styles.css. We only pick
// the animation name here; the keyframes themselves are NOT redefined.
const ACTIVITY_ANIMATION: Record<string, string> = {
  thinking: 'fleet-breathe 4s ease-in-out infinite',
  waiting: 'fleet-drift 6s ease-in-out infinite',
  stuck: 'fleet-jitter 0.125s steps(2, end) infinite',
  finished: 'none',
  unknown: 'none',
};

const DAILY_CAP_USD = 50;
const RATE_ALERT_USD_PER_MIN = 5;
const MIN_RADIUS = 18;
const MAX_RADIUS = 42;
const EVENT_COUNT_FOR_MAX_RADIUS = 200;

// --- deterministic PRNG ----------------------------------------------
// A seeded PRNG keyed off the session_id hash guarantees the same data
// always produces the same layout. This is non-negotiable: without it
// the fleet reshuffles on every poll.
function hashString(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function makeRng(seed: number): () => number {
  // mulberry32 — small, fast, good enough for layout jitter.
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// --- geometry ---------------------------------------------------------

interface LayoutNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

interface LayoutEdge {
  a: number;
  b: number;
}

function radiusFor(eventCount: number): number {
  const t = Math.min(1, Math.max(0, eventCount) / EVENT_COUNT_FOR_MAX_RADIUS);
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * t;
}

/**
 * Deterministic force simulation. Attraction along repo edges, repulsion
 * between all nodes, and a centering force. Runs a fixed number of
 * iterations with no animation — the result is a frozen snapshot.
 */
function computeLayout(
  sessions: Session[],
  width: number,
  height: number,
): LayoutNode[] {
  const n = sessions.length;
  if (n === 0) return [];

  const seed = sessions.reduce(
    (acc, s) => (acc ^ hashString(s.session_id)) >>> 0,
    0x9e3779b9,
  );
  const rng = makeRng(seed);

  const cx = width / 2;
  const cy = height / 2;

  const nodes: LayoutNode[] = sessions.map((s) => {
    // Seed positions in a jittered ring so the sim has somewhere to start
    // but the outcome is still fully determined by the data.
    const angle = rng() * Math.PI * 2;
    const radius = Math.min(width, height) * (0.15 + rng() * 0.25);
    return {
      id: s.session_id,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
      r: radiusFor(s.event_count ?? 0),
    };
  });

  // Edges: agents sharing a repo are linked.
  const byRepo = new Map<string, number[]>();
  sessions.forEach((s, i) => {
    const key = s.repo || '__none__';
    const list = byRepo.get(key);
    if (list) list.push(i);
    else byRepo.set(key, [i]);
  });
  const edges: LayoutEdge[] = [];
  byRepo.forEach((indices) => {
    for (let i = 0; i < indices.length; i += 1) {
      for (let j = i + 1; j < indices.length; j += 1) {
        edges.push({ a: indices[i], b: indices[j] });
      }
    }
  });

  const ITERATIONS = 300;
  const REPULSION = 4200;
  const ATTRACTION = 0.012;
  const CENTERING = 0.008;
  const DAMPING = 0.85;
  const IDEAL_EDGE = 140;

  for (let iter = 0; iter < ITERATIONS; iter += 1) {
    // Repulsion between all pairs.
    for (let i = 0; i < n; i += 1) {
      for (let j = i + 1; j < n; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let distSq = dx * dx + dy * dy;
        if (distSq < 0.01) {
          // Deterministic nudge for coincident nodes.
          dx = (rng() - 0.5) * 0.5;
          dy = (rng() - 0.5) * 0.5;
          distSq = dx * dx + dy * dy + 0.01;
        }
        const dist = Math.sqrt(distSq);
        const force = REPULSION / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // Attraction along edges.
    for (let e = 0; e < edges.length; e += 1) {
      const a = nodes[edges[e].a];
      const b = nodes[edges[e].b];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const force = (dist - IDEAL_EDGE) * ATTRACTION;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Centering + integrate.
    for (let i = 0; i < n; i += 1) {
      const node = nodes[i];
      node.vx += (cx - node.x) * CENTERING;
      node.vy += (cy - node.y) * CENTERING;
      node.vx *= DAMPING;
      node.vy *= DAMPING;
      node.x += node.vx;
      node.y += node.vy;

      // Keep nodes inside the canvas with a margin equal to their radius.
      const margin = node.r + 8;
      if (node.x < margin) node.x = margin;
      if (node.x > width - margin) node.x = width - margin;
      if (node.y < margin) node.y = margin;
      if (node.y > height - margin) node.y = height - margin;
    }
  }

  return nodes;
}

// --- number roll ------------------------------------------------------
// 150ms fade on change. No library; a keyed span re-mounts and the CSS
// animation replays. Honours prefers-reduced-motion via the stylesheet.
function RollingNumber({ value }: { value: number }): JSX.Element {
  return (
    <span key={value} className="fleet-num-roll" aria-hidden="true">
      {value}
    </span>
  );
}

// --- ticker -----------------------------------------------------------
interface TickerProps {
  counts: Record<string, number>;
  ratePerMin: number;
  todaySpend: number;
  totalAgents: number;
  activeFilter: string | null;
  onToggleFilter: (activity: string) => void;
  filterRef: React.RefObject<HTMLInputElement>;
  filterText: string;
  onFilterText: (value: string) => void;
}

function Ticker({
  counts,
  ratePerMin,
  todaySpend,
  totalAgents,
  activeFilter,
  onToggleFilter,
  filterRef,
  filterText,
  onFilterText,
}: TickerProps): JSX.Element {
  const rateHot = ratePerMin > RATE_ALERT_USD_PER_MIN;
  const order: Array<{ key: string; glyph: string }> = [
    { key: 'thinking', glyph: '●' },
    { key: 'waiting', glyph: '◐' },
    { key: 'stuck', glyph: '▲' },
    { key: 'finished', glyph: '✓' },
  ];

  return (
    <div
      style={{
        height: 44,
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        padding: '0 16px',
        background: T.surface1,
        borderBottom: `1px solid ${T.borderSubtle}`,
        fontFamily:
          'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
        fontSize: 13,
        lineHeight: 1.5,
        color: T.textSecondary,
        flexShrink: 0,
      }}
    >
      {order.map(({ key, glyph }) => {
        const count = counts[key] ?? 0;
        const pressed = activeFilter === key;
        return (
          <button
            key={key}
            type="button"
            aria-pressed={pressed}
            aria-label={`Filter: ${count} ${key}`}
            onClick={() => onToggleFilter(key)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              // Fixed column width so the eye scans at a steady rhythm.
              minWidth: 96,
              padding: '4px 8px',
              background: pressed ? T.surface3 : 'transparent',
              border: `1px solid ${pressed ? T.borderStrong : 'transparent'}`,
              borderRadius: 4,
              color: pressed ? T.textPrimary : T.textSecondary,
              font: 'inherit',
              cursor: 'pointer',
            }}
          >
            <span aria-hidden="true">{glyph}</span>
            <RollingNumber value={count} />
            <span>{key}</span>
          </button>
        );
      })}

      <span
        style={{
          minWidth: 96,
          color: T.textPrimary,
          // Amber leading edge when burn rate is hot.
          borderLeft: rateHot ? `2px solid #f59e0b` : '2px solid transparent',
          paddingLeft: 8,
        }}
      >
        ${ratePerMin.toFixed(1)}/min
      </span>

      <span style={{ minWidth: 120, color: T.textSecondary }}>
        ${todaySpend.toFixed(2)} today
      </span>

      <span style={{ minWidth: 96, color: T.textSecondary }}>
        {totalAgents} agents
      </span>

      <input
        ref={filterRef}
        value={filterText}
        onChange={(e) => onFilterText(e.target.value)}
        placeholder="filter…"
        aria-label="Filter agents by text"
        style={{
          marginLeft: 'auto',
          width: 160,
          height: 28,
          padding: '0 8px',
          background: T.surface2,
          border: `1px solid ${T.border}`,
          borderRadius: 4,
          color: T.textPrimary,
          font: 'inherit',
          outline: 'none',
        }}
      />
    </div>
  );
}

// --- burn bar ---------------------------------------------------------
interface BurnBarProps {
  todaySpend: number;
  ratePerMin: number;
  totalAgents: number;
}

function BurnBar({
  todaySpend,
  ratePerMin,
  totalAgents,
}: BurnBarProps): JSX.Element {
  const fraction = Math.min(1, Math.max(0, todaySpend / DAILY_CAP_USD));
  const remaining = 1 - fraction;
  const edgeOpacity = Math.min(1, ratePerMin / RATE_ALERT_USD_PER_MIN);

  // Below 20% remaining the edge turns amber; below 5% it also pulses.
  const low = remaining < 0.2;
  const critical = remaining < 0.05;
  const edgeColor = low ? '#f59e0b' : T.accent;

  return (
    <div style={{ padding: '8px 16px 12px', flexShrink: 0 }}>
      <div
        style={{
          position: 'relative',
          height: 6,
          width: '100%',
          background: T.surface3,
          borderRadius: 3,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: 6,
            width: `${fraction * 100}%`,
            background: T.accent,
            borderRadius: 3,
            // The leading edge glow encodes the burn rate.
            boxShadow: `0 0 12px 2px ${edgeColor}`,
            opacity: 1,
          }}
        >
          <div
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              height: 6,
              width: 2,
              background: edgeColor,
              opacity: edgeOpacity,
              boxShadow: `0 0 12px 2px ${edgeColor}`,
              animation: critical
                ? 'fleet-halo 1.6s ease-out infinite'
                : 'none',
            }}
          />
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: 4,
          fontSize: 11,
          lineHeight: 1.2,
          color: T.textMuted,
          fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
        }}
      >
        <span>
          today ${todaySpend.toFixed(2)} / ${DAILY_CAP_USD}
        </span>
        <span>{totalAgents} agents</span>
      </div>
    </div>
  );
}

// --- detail panel -----------------------------------------------------
interface DetailPanelProps {
  session: Session;
  x: number;
  y: number;
  pinned: boolean;
}

function DetailPanel({
  session,
  x,
  y,
  pinned,
}: DetailPanelProps): JSX.Element {
  return (
    <div
      role="dialog"
      aria-label={`Details for ${session.runtime} ${session.session_id}`}
      style={{
        position: 'absolute',
        left: x,
        top: y,
        background: T.surface2,
        border: `1px solid ${T.border}`,
        borderRadius: 8,
        padding: '12px 14px',
        maxWidth: 320,
        boxShadow: '0 8px 24px rgba(0,0,0,.5)',
        color: T.textPrimary,
        fontSize: 13,
        lineHeight: 1.5,
        pointerEvents: pinned ? 'auto' : 'none',
        zIndex: 10,
      }}
    >
      <div
        style={{
          fontSize: 14,
          lineHeight: 1.5,
          fontWeight: 600,
          marginBottom: 8,
          // Clamp the task to three lines.
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {session.task || '(no task)'}
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontSize: 12,
            lineHeight: 1.2,
            padding: '2px 8px',
            borderRadius: 4,
            background: T.surface3,
            color: T.textSecondary,
          }}
        >
          {session.runtime}
        </span>
        <span
          style={{
            fontSize: 12,
            lineHeight: 1.2,
            padding: '2px 8px',
            borderRadius: 4,
            background: T.surface3,
            color: T.textSecondary,
          }}
        >
          {session.activity}
        </span>
        <span
          style={{
            fontSize: 12,
            lineHeight: 1.2,
            padding: '2px 8px',
            borderRadius: 4,
            background: T.surface3,
            color: T.textSecondary,
          }}
        >
          {session.state}
        </span>
      </div>

      <dl
        style={{
          margin: 0,
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          columnGap: 12,
          rowGap: 4,
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        <dt style={{ color: T.textMuted }}>events</dt>
        <dd style={{ margin: 0 }}>{session.event_count}</dd>
        <dt style={{ color: T.textMuted }}>spend</dt>
        <dd style={{ margin: 0 }}>{typeof session.spend_usd === 'number' ? `$${session.spend_usd.toFixed(2)}` : '—'}</dd>
        <dt style={{ color: T.textMuted }}>repo</dt>
        <dd style={{ margin: 0, wordBreak: 'break-all' }}>
          {session.repo || '—'}
        </dd>
        <dt style={{ color: T.textMuted }}>id</dt>
        <dd style={{ margin: 0, wordBreak: 'break-all' }}>
          {session.session_id}
        </dd>
      </dl>
    </div>
  );
}

// --- node -------------------------------------------------------------
interface NodeProps {
  session: Session;
  node: LayoutNode;
  hovered: boolean;
  pinned: boolean;
  onHover: (id: string | null) => void;
  onSelect: (id: string) => void;
}

function Node({
  session,
  node,
  hovered,
  pinned,
  onHover,
  onSelect,
}: NodeProps): JSX.Element {
  const stateColor = STATE_COLOR[session.state ?? 'unknown'] ?? T.textMuted;
  // `activity` is optional on the wire (an older backend omits it) and absent must mean
  // `unknown`, never a default of thinking -- a node that breathes when nobody knows whether
  // it is alive is the same lie as a green dot.
  const activity: Activity = session.activity ?? 'unknown';
  const animation = ACTIVITY_ANIMATION[activity] ?? 'none';
  const isStuck = activity === 'stuck';
  const isFinished = activity === 'finished';
  const isWaiting = activity === 'waiting';
  const isThinking = activity === 'thinking';

  const last6 = session.session_id.slice(-6);
  const initial = (session.runtime || '?').charAt(0).toUpperCase();
  const label = `${initial} #${last6}`;
  const activityWord = ACTIVITY_WORD[activity] ?? 'unknown';

  const ariaLabel = `${session.runtime} ${activityWord}. ${
    session.task || 'no task'
  }. ${session.event_count} events.`;

  const scale = hovered || pinned ? 1.08 : 1;

  return (
    <g
      role="button"
      tabIndex={0}
      // The session id as a testid, so a test addresses the SESSION rather than a glyph or a
      // layout position -- both of which change as the design moves.
      data-testid={`session-${session.session_id}`}
      aria-label={ariaLabel}
      onMouseEnter={() => onHover(session.session_id)}
      onMouseLeave={() => onHover(null)}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(session.session_id);
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(session.session_id);
        }
      }}
      style={{
        cursor: 'pointer',
        outline: 'none',
        transformOrigin: `${node.x}px ${node.y}px`,
        transform: `scale(${scale})`,
        transition:
          'transform 180ms cubic-bezier(.34,1.56,.64,1)',
      }}
    >
      {/* Stuck halo — a persistent expanding ring, not a one-shot. */}
      {isStuck && (
        <circle
          cx={node.x}
          cy={node.y}
          r={node.r}
          fill="none"
          stroke={stateColor}
          strokeWidth={2}
          style={{
            transformOrigin: `${node.x}px ${node.y}px`,
            animation: 'fleet-halo 1.6s ease-out infinite',
          }}
        />
      )}

      {/* Activity ring: solid=thinking, dashed=waiting, none=finished. */}
      {isThinking && (
        <circle
          cx={node.x}
          cy={node.y}
          r={node.r + 4}
          fill="none"
          stroke={stateColor}
          strokeWidth={1.5}
          opacity={0.7}
        />
      )}
      {isWaiting && (
        <circle
          cx={node.x}
          cy={node.y}
          r={node.r + 4}
          fill="none"
          stroke={stateColor}
          strokeWidth={1.5}
          strokeDasharray="4 4"
          opacity={0.7}
        />
      )}

      {/* Body — area encodes work done. */}
      <circle
        cx={node.x}
        cy={node.y}
        r={node.r}
        fill={T.surface2}
        stroke={stateColor}
        strokeWidth={2}
      />

      {/* Inner pulse — the activity motion lives on a smaller circle so
          the body stays a stable target. */}
      <circle
        cx={node.x}
        cy={node.y}
        r={node.r * 0.55}
        fill={stateColor}
        opacity={isFinished ? 0.25 : 0.5}
        style={{
          transformOrigin: `${node.x}px ${node.y}px`,
          animation: isFinished ? 'none' : animation,
        }}
      />

      {/* Identity label: runtime initial + last 6 of the id. */}
      <text
        x={node.x}
        y={node.y + node.r + 14}
        textAnchor="middle"
        fill={T.textSecondary}
        fontSize={11}
        style={{ lineHeight: 1.2, pointerEvents: 'none' }}
      >
        {label}
      </text>

      {/* Activity word — colour is never the only channel. */}
      <text
        x={node.x}
        y={node.y + node.r + 26}
        textAnchor="middle"
        fill={T.textMuted}
        fontSize={11}
        style={{ lineHeight: 1.2, pointerEvents: 'none' }}
      >
        {activityWord}
      </text>
    </g>
  );
}

// --- main component ---------------------------------------------------
export interface FleetCanvasProps {
  sessions: Session[];
  board?: { state: string; reason?: string };
}

export default function FleetCanvas({
  sessions,
  board,
}: FleetCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const filterRef = useRef<HTMLInputElement>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({
    w: 960,
    h: 520,
  });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');

  // Measure the container so the layout can be computed against real
  // dimensions. ResizeObserver keeps it honest without a window listener.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const update = () => {
      const rect = el.getBoundingClientRect();
      setSize({ w: rect.width || 960, h: rect.height || 520 });
    };
    update();
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(update);
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  // Keyboard: `/` focuses the filter, Escape clears it and unpins.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== filterRef.current) {
        e.preventDefault();
        filterRef.current?.focus();
      } else if (e.key === 'Escape') {
        setActiveFilter(null);
        setFilterText('');
        setPinnedId(null);
        filterRef.current?.blur();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Filtering is by activity (ticker) and by free text (filter box).
  const filtered = useMemo(() => {
    const text = filterText.trim().toLowerCase();
    return sessions.filter((s) => {
      if (activeFilter && s.activity !== activeFilter) return false;
      if (text) {
        const hay = `${s.runtime} ${s.task} ${s.repo} ${s.session_id}`.toLowerCase();
        if (!hay.includes(text)) return false;
      }
      return true;
    });
  }, [sessions, activeFilter, filterText]);

  // Layout is recomputed only when the filtered set or size changes.
  const layout = useMemo(
    () => computeLayout(filtered, size.w, size.h),
    [filtered, size.w, size.h],
  );

  const layoutById = useMemo(() => {
    const map = new Map<string, LayoutNode>();
    layout.forEach((n) => map.set(n.id, n));
    return map;
  }, [layout]);

  // Counts are computed against the full session set so the ticker always
  // reflects reality, not the current filter.
  const counts = useMemo(() => {
    const c: Record<string, number> = {
      thinking: 0,
      waiting: 0,
      stuck: 0,
      finished: 0,
      unknown: 0,
    };
    sessions.forEach((s) => {
      const a = s.activity ?? 'unknown';
      c[a] = (c[a] ?? 0) + 1;
    });
    return c;
  }, [sessions]);

  // Rate = sum of last-hour spend × 60. We approximate "last hour" by
  // treating spend_usd as the session's hourly burn (the board only
  // exposes a running total, so this is the best available signal).
  const ratePerMin = useMemo(() => {
    const total = sessions.reduce((acc, s) => acc + (s.spend_usd || 0), 0);
    return total * 60;
  }, [sessions]);

  const todaySpend = useMemo(
    () => sessions.reduce((acc, s) => acc + (s.spend_usd || 0), 0),
    [sessions],
  );

  const handleToggleFilter = useCallback((activity: string) => {
    setActiveFilter((prev) => (prev === activity ? null : activity));
  }, []);

  const handleSelect = useCallback((id: string) => {
    setPinnedId((prev) => (prev === id ? null : id));
  }, []);

  const handleCanvasClick = useCallback(() => {
    setPinnedId(null);
  }, []);

  // --- unavailable state: never render a fake empty canvas -------------
  if (board && board.state === 'unavailable') {
    return (
      <div
        style={{
          height: 'calc(100vh - 240px)',
          minHeight: 520,
          background: T.canvas,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: T.textSecondary,
          fontSize: 14,
          lineHeight: 1.5,
          padding: 24,
          textAlign: 'center',
        }}
      >
        {board.reason || 'Fleet data is unavailable.'}
      </div>
    );
  }

  const activeSession =
    pinnedId != null
      ? sessions.find((s) => s.session_id === pinnedId) ?? null
      : hoveredId != null
        ? sessions.find((s) => s.session_id === hoveredId) ?? null
        : null;

  const activeNode =
    activeSession != null
      ? layoutById.get(activeSession.session_id) ?? null
      : null;

  return (
    <div
      style={{
        height: 'calc(100vh - 240px)',
        minHeight: 520,
        background: T.canvas,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Ticker
        counts={counts}
        ratePerMin={ratePerMin}
        todaySpend={todaySpend}
        totalAgents={sessions.length}
        activeFilter={activeFilter}
        onToggleFilter={handleToggleFilter}
        filterRef={filterRef}
        filterText={filterText}
        onFilterText={setFilterText}
      />

      <BurnBar
        todaySpend={todaySpend}
        ratePerMin={ratePerMin}
        totalAgents={sessions.length}
      />

      <div
        ref={containerRef}
        onClick={handleCanvasClick}
        style={{
          position: 'relative',
          flex: 1,
          minHeight: 0,
          background: T.canvas,
        }}
      >
        {filtered.length === 0 ? (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: T.textSecondary,
              fontSize: 14,
              lineHeight: 1.5,
              gap: 12,
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: 10,
                height: 10,
                borderRadius: 999,
                background: T.textMuted,
                animation: 'fleet-breathe 4s ease-in-out infinite',
              }}
            />
            No agents running. Nothing to watch.
          </div>
        ) : (
          <svg
            width="100%"
            height="100%"
            style={{ display: 'block' }}
            role="group"
            aria-label="Fleet canvas"
          >
            {filtered.map((s) => {
              const node = layoutById.get(s.session_id);
              if (!node) return null;
              return (
                <Node
                  key={s.session_id}
                  session={s}
                  node={node}
                  hovered={hoveredId === s.session_id}
                  pinned={pinnedId === s.session_id}
                  onHover={setHoveredId}
                  onSelect={handleSelect}
                />
              );
            })}
          </svg>
        )}

        {activeSession && activeNode && (
          <DetailPanel
            session={activeSession}
            x={Math.min(activeNode.x + activeNode.r + 12, size.w - 340)}
            y={Math.max(activeNode.y - 40, 8)}
            pinned={pinnedId === activeSession.session_id}
          />
        )}
      </div>
    </div>
  );
}
