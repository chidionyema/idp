// The four states, drawn as MOTION rather than as one dot.
//
// A council of three independent frontier models, asked to design this interface, converged on
// the same finding: an agent that has not emitted for ten minutes is not one state but four, and
// the interface's whole value is telling them apart. One of them put the mechanism exactly:
//
//   thinking   slow 4s inhale/exhale, ring stays lit            -- it is BREATHING
//   waiting    ring goes dashed, node DRIFTS 2px/s toward its dependency
//                                                               -- the drift IS the tell
//   stuck      ring desaturates, node JITTERS at 8Hz            -- caught pre-attentively
//   finished   breathing stops, ring closes solid, node SINKS 8px -- sinking is terminal
//
//   "Never use a spinner for any of these. Spinners mean 'working' and destroy the distinction."
//
// WHY MOTION AND NOT COLOUR. A person watching a fleet is not staring at the screen; the signal
// has to arrive through peripheral vision, and peripheral vision reads movement before it reads
// hue. That is also why these are keyframes and not spinners: a spinner has one meaning, and this
// interface needs four that cannot be confused with each other.
//
// EVERY KEYFRAME BELOW IS EARNED. The state comes from `activity`, which is derived server-side
// from real evidence (recency plus the body of work behind the row -- see sessions.py's
// `_activity_from_evidence`). A node that jitters must be jittering because a session really
// stopped producing. Inventing motion to look alive is the same offence as a green dot, and it
// is worse, because it is harder to notice.

export type Activity = 'thinking' | 'waiting' | 'stuck' | 'finished' | 'unknown';

/** The one word a reader gets, for the aria-label and the tooltip. */
export const ACTIVITY_WORD: Record<Activity, string> = {
  thinking: 'Working',
  waiting: 'Waiting',
  stuck: 'Stopped producing',
  finished: 'Finished',
  unknown: 'Not measured',
};

/** The sentence, because a bare word beside a bare dot is the thing the founder complained about. */
export const ACTIVITY_SENTENCE: Record<Activity, string> = {
  thinking: 'Producing output right now.',
  waiting: 'Live and quiet: blocked on something outside itself — CI, an API, or a person.',
  stuck: 'It was producing and has stopped. Worth a look.',
  finished: 'Past the live window. It will not write again unless something restarts it.',
  unknown: 'No timestamp, so whether it is alive is not known.',
};

/**
 * The animation name for each state, or none.
 *
 * Returned as a name rather than a style so the CSS lives in one place (styles.css carries the
 * keyframes) and a test can assert the mapping without a browser.
 */
export function motionFor(a: Activity): string | undefined {
  switch (a) {
    case 'thinking':
      return 'fleet-breathe 4s ease-in-out infinite';
    case 'waiting':
      return 'fleet-drift 6s ease-in-out infinite';
    case 'stuck':
      return 'fleet-jitter 0.125s steps(2, end) infinite';
    case 'finished':
      return undefined; // no motion: stillness is the signal, and it is the one state that is over
    default:
      return undefined;
  }
}

/** The ring style. Dashed means blocked; solid-and-faded means over; solid means alive. */
export function ringStyleFor(a: Activity): { borderStyle: string; opacity: number } {
  switch (a) {
    case 'waiting':
      return { borderStyle: 'dashed', opacity: 1 };
    case 'finished':
      return { borderStyle: 'solid', opacity: 0.4 };
    case 'unknown':
      return { borderStyle: 'dotted', opacity: 0.6 };
    default:
      return { borderStyle: 'solid', opacity: 1 };
  }
}

/** Does this state need a person? `stuck` is the whole reason the board exists. */
export function needsAPerson(a: Activity): boolean {
  return a === 'stuck';
}
