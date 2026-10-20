/**
 * attention: one rule for how loud a Fleet panel may be.
 *
 * Every status panel on the rail reports a Signal -- a tier, one line, and the panel it came from
 * -- and the rail decides what reaches the founder. The rule is the dark cockpit's: a panel that is
 * fine is not drawn, and silence means "read, and fine". Only warnings (someone must act now),
 * cautions (something is wrong and will need a person) and advisories (worth knowing, then gone)
 * are shown, worst first, at most MAX_SHOWN of them; the rest are counted, never hidden silently.
 * EEMUA 191 asks for under one alarm per ten minutes in steady state; a rail that shows eight
 * pills all day is the opposite of that.
 *
 * A panel that cannot read its own source is a caution, never clear: "I could not look" and
 * "nothing is wrong" must never look the same.
 */

import { useEffect, useRef } from 'react';

export type Tier = 'warning' | 'caution' | 'advisory' | 'clear';

export type Signal = {
  /** Which panel: the rail's key for it. */
  source: string;
  tier: Tier;
  /** One line, spoken or shown as is. Empty when clear. */
  summary: string;
};

export const MAX_SHOWN = 3;
/** An advisory is worth knowing once; after this long unchanged it stops asking. */
export const ADVISORY_TTL_MS = 60_000;

const RANK: Record<Tier, number> = { warning: 0, caution: 1, advisory: 2, clear: 3 };

export const clear = (source: string): Signal => ({ source, tier: 'clear', summary: '' });

/** "Could not read" is a caution, in the panel's own words. */
export const unreadable = (source: string, what = 'unreachable'): Signal => ({
  source,
  tier: 'caution',
  summary: `${source} · ${what}`,
});

export type Seen = Record<string, { key: string; since: number }>;

/**
 * Remember when each panel's current signal first appeared, so an unchanged advisory can expire.
 * A signal that changes (new tier or new words) starts its clock again.
 */
export function noteSeen(seen: Seen, signals: Signal[], nowMs: number): Seen {
  const next: Seen = {};
  for (const s of signals) {
    const key = `${s.tier}|${s.summary}`;
    const prev = seen[s.source];
    next[s.source] = prev && prev.key === key ? prev : { key, since: nowMs };
  }
  return next;
}

/** Is this signal still asking for attention? Warnings and cautions stand until they clear. */
export function isLive(s: Signal, seen: Seen, nowMs: number, ttlMs = ADVISORY_TTL_MS): boolean {
  if (s.tier === 'clear') return false;
  if (s.tier !== 'advisory') return true;
  const at = seen[s.source]?.since ?? nowMs;
  return nowMs - at < ttlMs;
}

export type Board = {
  /** What the rail shows, worst first, at most `max`. */
  shown: Signal[];
  /** Live signals past the cap: counted on screen, never dropped silently. */
  more: number;
  /** Sources asking for attention; the rail draws these panels and hides the rest. */
  loud: Set<string>;
  /** The worst live tier, or clear. */
  worst: Tier;
  /** One sentence for the whole rail: the calm line, and the spoken answer. */
  line: string;
};

export function board(
  signals: Signal[],
  seen: Seen,
  nowMs: number,
  max = MAX_SHOWN,
  ttlMs = ADVISORY_TTL_MS,
): Board {
  const live = signals
    .filter(s => isLive(s, seen, nowMs, ttlMs))
    .sort((a, b) => RANK[a.tier] - RANK[b.tier] || a.source.localeCompare(b.source));
  const shown = live.slice(0, max);
  const more = live.length - shown.length;
  const line = live.length
    ? `${live.length} need${live.length === 1 ? 's' : ''} you: ${shown
        .map(s => s.summary)
        .join('; ')}${more ? `; and ${more} more` : ''}.`
    : 'All quiet.';
  return {
    shown,
    more,
    loud: new Set(live.map(s => s.source)),
    worst: live.length ? live[0].tier : 'clear',
    line,
  };
}

/** A panel reports its signal to the rail whenever the tier or words change, and only then. */
export function useSignal(onSignal: ((s: Signal) => void) | undefined, s: Signal): void {
  const cb = useRef(onSignal);
  cb.current = onSignal;
  useEffect(() => {
    cb.current?.(s);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.source, s.tier, s.summary]);
}
