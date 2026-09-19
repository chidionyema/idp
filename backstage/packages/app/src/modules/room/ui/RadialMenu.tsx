// RadialMenu.tsx — the actions snap around the agent, not into a bar at the bottom.
//
// THE CRIME THIS REMOVES. Measured 2026-09-19: selecting an agent put its four actions in a
// horizontal bar BELOW the canvas. A person's eye had to leave the thing that is wrong (a red
// node, top-left) and travel to the bottom of the screen to find the thing that fixes it, then
// back to see whether it worked. The gap between problem and solution is the whole cost.
//
// So the menu is radial and anchored ON the node: one gesture, one place, nothing to travel to.
// Stop sits at the top because it is the action taken in a hurry; the destructive ones are spaced
// from the ones that only inform.
//
// WHY RADIAL AND NOT A CONTEXT MENU. A list of four items is read top to bottom, which costs a
// sweep of the eye. Four items at equal angles around a point are read by DIRECTION, which the
// hand already knows -- and each target is the same distance away, so a hurried press cannot land
// on Deny when it meant Stop.
//
// THE BACKGROUND IS A CLICK-THROUGH SCRIM: it takes the click that dismisses, and it dims the
// fleet so the node under the menu is the only bright thing on screen.

import type { Session } from '../home/fleetBoard';

export interface RadialMenuProps {
  readonly session: Session;
  /** Screen position of the node, in the canvas's own pixel space. */
  readonly x: number;
  readonly y: number;
  /** The four signals this runtime actually has a channel for. */
  readonly available: ReadonlySet<string>;
  readonly busy?: string | null;
  readonly result?: string | null;
  onAct: (kind: 'stop' | 'approve' | 'deny' | 'steer' | 'dictate' | 'ping') => void;
  /** True while this agent's mic is open, so the button reports it rather than looking idle. */
  readonly dictating?: boolean;
  /**
   * True while this agent's cascade is being pinged, so the button can say so.
   *
   * 'ping' is always offered, and the reason is worth writing down: the four signal verbs ask
   * "may I act on this runtime", and the answer is often no. A cascade question is a READ of a
   * graph the backend already holds, so it is answerable for any session on any runtime --
   * greying it out would hide the one question you can always ask.
   */
  readonly pinging?: boolean;
  onDismiss: () => void;
}

const RADIUS = 62;

// The four directions, and why each sits where it does:
//   stop    up      the urgent one, found without looking
//   approve right   the affirmative, where a yes usually sits
//   deny    left    the refusal, opposite its partner
//   steer   down    the one that opens a channel rather than closing one
// A FIFTH VERB, because the four directions had room and dictation had none. It sits at
// lower-left, clear of Stop at the top: speaking a steer and stopping an agent are the two a
// person reaches for in a hurry, and they must not be adjacent.
// SIX VERBS NOW. The five do things TO an agent; the sixth ASKS about it, so it sits alone in
// the upper-left, away from every verb that changes state. Pressing Deny when you meant to ask a
// question is the mistake this separation exists to prevent.
const ANGLES: Array<{
  kind: 'stop' | 'approve' | 'deny' | 'steer' | 'dictate' | 'ping';
  label: string;
  deg: number;
}> = [
  { kind: 'stop', label: 'Stop', deg: -90 },
  { kind: 'approve', label: 'Approve', deg: 0 },
  { kind: 'deny', label: 'Deny', deg: 180 },
  { kind: 'steer', label: 'Steer', deg: 90 },
  { kind: 'dictate', label: '🎤', deg: 135 },
  { kind: 'ping', label: 'Blast', deg: -135 },
];

export function RadialMenu(props: RadialMenuProps): JSX.Element {
  const { session, x, y, available, busy, result } = props;

  return (
    <div
      data-testid="radial-scrim"
      onClick={props.onDismiss}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 20,
        // A scrim rather than a blackout: the fleet stays visible behind the choice, so the
        // decision is made with the context in sight.
        background: 'radial-gradient(circle at 50% 50%, rgba(5,7,10,0.55), rgba(5,7,10,0.82))',
        backdropFilter: 'blur(2px)',
      }}
    >
      {/* The halo: the node's own ring, drawn larger, so the menu reads as belonging to it. */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: x - RADIUS - 30,
          top: y - RADIUS - 30,
          width: (RADIUS + 30) * 2,
          height: (RADIUS + 30) * 2,
          borderRadius: '50%',
          border: '1px solid rgba(255,196,120,0.22)',
          boxShadow: '0 0 40px rgba(255,180,80,0.10) inset',
          pointerEvents: 'none',
        }}
      />

      <div
        role="menu"
        aria-label={`Actions for ${session.runtime} ${String(session.session_id).slice(-6)}`}
        data-testid="radial-menu"
        style={{
          position: 'absolute',
          left: x,
          top: y,
        }}
      >
        {ANGLES.map(({ kind, label, deg }) => {
          const has = available.has(kind);
          const rad = (deg * Math.PI) / 180;
          const bx = Math.cos(rad) * RADIUS;
          const by = Math.sin(rad) * RADIUS;
          const isBusy = busy === kind;
          return (
            <button
              key={kind}
              type="button"
              role="menuitem"
              data-testid={`radial-${kind}`}
              disabled={!has || isBusy}
              onClick={e => {
                // The scrim dismisses on click; a menu button must not also dismiss, or the
                // action and the teardown race and the teardown wins.
                e.stopPropagation();
                if (has && !isBusy) props.onAct(kind);
              }}
              aria-label={
                has
                  ? `${label} ${session.runtime} ${String(session.session_id).slice(-6)}`
                  : `${label} unavailable: ${session.runtime} has no channel for it`
              }
              style={{
                position: 'absolute',
                left: bx - 40,
                top: by - 17,
                width: 80,
                height: 34,
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: 0.3,
                borderRadius: 17,
                border: `1px solid ${has ? 'rgba(255,196,120,0.5)' : 'rgba(120,130,145,0.28)'}`,
                background: has ? 'rgba(24,20,13,0.96)' : 'rgba(20,22,26,0.9)',
                color: has ? '#f0e4c8' : '#6b7280',
                cursor: has ? 'pointer' : 'not-allowed',
                // A disabled control still says what it is and why -- the same rule signals.py
                // follows with its 422.
                opacity: has ? 1 : 0.55,
                boxShadow: has ? '0 6px 20px rgba(0,0,0,0.5)' : 'none',
              }}
            >
              {isBusy ? '…' : kind === 'dictate' && props.dictating ? '●' : kind === 'ping' && props.pinging ? '◉' : label}
            </button>
          );
        })}

        {/* The node's identity and the result of the last press, at the centre: this is the
            only place the answer appears, and it appears where the question was asked. */}
        <div
          data-testid="radial-centre"
          style={{
            position: 'absolute',
            left: -60,
            top: -26,
            width: 120,
            textAlign: 'center',
            pointerEvents: 'none',
            fontSize: 11,
            lineHeight: 1.3,
          }}
        >
          <div style={{ color: '#f0e4c8', fontWeight: 700 }}>
            {session.runtime} · {String(session.session_id).slice(-6)}
          </div>
          {result ? (
            <div style={{ color: '#fca5a5', marginTop: 2 }}>{result}</div>
          ) : (
            <div style={{ color: '#8b949e', marginTop: 2 }}>
              {session.event_count ?? 0} events
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
