// MindPanel.tsx — the inside of an agent, shown where the agent is.
//
// THE CRIME THIS REMOVES. The camera pushes into a selected agent (SpatialCanvas), and then the
// detail -- trace, ledger, receipt, history -- sat in a fold BELOW the canvas. So the drill-down
// arrived at a node and found nothing in it, and the reader's eye had to leave the room they had
// just flown into to read a fold underneath it. A zoom that reveals no interior is a zoom that
// wasted the gesture.
//
// So the interior is an OVERLAY ON THE NODE, positioned at the node's own screen point. The
// panel is deliberately translucent with a blurred backdrop rather than opaque: the fleet stays
// visible behind it, because the question "what else is affected while I am in here" is the
// question you have when you go into an agent, and the answer is the room behind the panel.
//
// IT DOES NOT DUPLICATE THE FOLD. The fold is not deleted -- Trace, Ledger, Receipt and History
// still load there for the reader who wants to sit with them, and both read from the same state
// and the same loaders. What differs is the SURFACE, not the truth.

import type { Session } from '../../home/fleetBoard';

export interface MindPanelProps {
  readonly session: Session;
  /** Screen position of the agent, in the canvas's pixel space. */
  readonly x: number;
  readonly y: number;
  /** How much work this agent has done in the last second, the live pulse. */
  readonly rate: number;
  /** Where its trace can be read, if the backend knows. */
  readonly traceUrl?: string | null;
  /** The last few events this agent emitted, newest first, as the backend holds them. */
  readonly recent?: readonly { type?: string; ts?: string; summary?: string }[];
  /** Loaded on demand; each returns its own truth or an honest refusal. */
  onLoadTrace: () => void;
  onLoadLedger: () => void;
  /** Exactly the shape the page already holds (`TraceState`): available plus the spans it found. */
  trace: { available: boolean; nodes: unknown[]; error?: string } | null;
  /** Exactly the shape the page already holds: the ledger rows it loaded. */
  ledger: { rows: unknown[] } | null;
  onClose: () => void;
}

/**
 * The panel is placed at the node but CLAMPED to the canvas: a node near the right edge would
 * otherwise put its own interior half off-screen, which is the worst place to lose text.
 */
const WIDTH = 340;
const HEIGHT_HINT = 250;

export function MindPanel(props: MindPanelProps): JSX.Element {
  const { session, x, y, rate } = props;
  const events = session.event_count ?? 0;
  const left = Math.max(8, x - WIDTH / 2);
  const top = y + 70;
  const activity = session.activity ?? 'unknown';

  return (
    <div
      data-testid="mind-panel"
      style={{
        position: 'absolute',
        left,
        top,
        width: WIDTH,
        maxHeight: HEIGHT_HINT * 1.6,
        overflowY: 'auto',
        zIndex: 15,
        padding: '12px 14px',
        borderRadius: 12,
        border: '1px solid rgba(255,196,120,0.30)',
        // Translucent, not opaque: the fleet behind is part of the answer.
        background: 'rgba(10,13,18,0.82)',
        backdropFilter: 'blur(10px)',
        boxShadow: '0 18px 50px rgba(0,0,0,0.6)',
        color: '#e6edf3',
        fontSize: 12,
        lineHeight: 1.45,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <strong style={{ fontSize: 13 }}>
          {session.runtime} · {String(session.session_id).slice(-6)}
        </strong>
        <button
          type="button"
          data-testid="mind-close"
          onClick={props.onClose}
          aria-label="Leave this agent and return to the fleet"
          style={{
            background: 'transparent',
            border: 0,
            color: '#8b949e',
            cursor: 'pointer',
            fontSize: 15,
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      {/* THE LIVE PULSE, first, because it is the thing that changes while you read.
          A rate of zero is stated as zero rather than hidden: a session you have flown into
          that has done nothing this second is a fact worth seeing, not an absence to paper over. */}
      <div data-testid="mind-rate" style={{ marginTop: 6, color: rate > 0 ? '#ffd68a' : '#8b949e' }}>
        {rate > 0 ? `▲ ${rate} event(s) in the last second` : 'quiet — nothing emitted this second'}
      </div>

      <div data-testid="mind-summary" style={{ marginTop: 6, color: '#a8afba' }}>
        <div>
          <strong style={{ color: '#e6edf3' }}>State</strong> {activity}
          {session.repo ? ` · ${session.repo}` : ''}
        </div>
        <div>
          <strong style={{ color: '#e6edf3' }}>Work</strong> {events} events
          {typeof session.spend_usd === 'number' ? ` · $${session.spend_usd.toFixed(4)}` : ''}
        </div>
        {session.step != null ? (
          <div>
            <strong style={{ color: '#e6edf3' }}>Step</strong> {session.step}
          </div>
        ) : null}
        {session.task ? (
          <div style={{ marginTop: 4, color: '#c9d1d9' }}>{session.task.slice(0, 220)}</div>
        ) : null}
      </div>

      {/* THE INTERIOR. Each affordance loads its own truth and reports its own refusal; nothing
          here is pre-computed to look populated. */}
      <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" data-testid="mind-trace" onClick={props.onLoadTrace} style={BTN}>
          Stream
        </button>
        <button type="button" data-testid="mind-ledger" onClick={props.onLoadLedger} style={BTN}>
          Ledger
        </button>
        {props.traceUrl ? (
          <a
            href={props.traceUrl}
            target="_blank"
            rel="noreferrer"
            style={{ ...BTN, textDecoration: 'none', display: 'inline-block' }}
          >
            Langfuse ↗
          </a>
        ) : null}
      </div>

      {props.trace ? (
        <div data-testid="mind-trace-body" style={{ marginTop: 8, color: '#a8afba' }}>
          {props.trace.error
            ? `Stream unavailable — ${props.trace.error}`
            : props.trace.available
              ? `Stream: ${props.trace.nodes.length} span(s)`
              : 'Stream unavailable here — the trace backend has not been told about this estate'}
        </div>
      ) : null}
      {props.ledger ? (
        <div data-testid="mind-ledger-body" style={{ marginTop: 6, color: '#a8afba' }}>
          Ledger: {props.ledger.rows.length} row(s)
        </div>
      ) : null}

      {props.recent && props.recent.length > 0 ? (
        <div data-testid="mind-recent" style={{ marginTop: 8 }}>
          <strong style={{ color: '#e6edf3' }}>Recent</strong>
          <div style={{ marginTop: 3 }}>
            {props.recent.slice(0, 5).map((e, i) => (
              <div key={i} style={{ color: '#8b949e', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {e.ts ? `${String(e.ts).slice(11, 19)} ` : ''}
                {e.summary || e.type || 'event'}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

const BTN: React.CSSProperties = {
  padding: '3px 10px',
  fontSize: 12,
  borderRadius: 14,
  border: '1px solid rgba(255,196,120,0.45)',
  background: 'rgba(24,20,13,0.9)',
  color: '#f0e4c8',
  cursor: 'pointer',
};
