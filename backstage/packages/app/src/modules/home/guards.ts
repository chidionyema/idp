// The guard ledger, as the Ops page reads it.
//
// Founder, 2026-09-12: "the final proof is me seeing everything real time on ops dashboard, every
// active guard or extension... need to see it working and doing this thing realtime." A guard
// whose only evidence is a README is a claim. This is the record of it having fired, with the
// command that caused it.
//
// Every guard decision is one JSON line in ~/.estate/guards.jsonl, written by the extension as it
// happens. This module parses those lines and states what they mean; it never invents a value for
// a guard that has not run, because "no evidence" and "not working" are different answers and the
// page must not confuse them.

export type GuardEvent = {
  at: string;
  guard: string;
  action: 'allow' | 'block' | 'warn';
  session?: string;
  pid?: number;
  command?: string;
  seconds?: number;
  budget_s?: number;
  set_to_ms?: number;
  overdue_ms?: number;
};

export type GuardSummary = {
  guard: string;
  name: string;
  what: string;
  /** How many times it fired inside the window this page reads. */
  events: number;
  blocked: number;
  lastAt: string;
  lastCommand: string;
};

/** What each guard is, in the page's own words. A guard missing from here is shown by its id. */
export const GUARD_NAMES: Record<string, { name: string; what: string }> = {
  'turn-ceiling': {
    name: 'Turn ceiling',
    what:
      'Caps every bash call so a turn cannot block. A command that would run longer comes back to ' +
      'the agent instead of leaving the session silent.',
  },
  'sleep-ban': {
    name: 'Sleep ban',
    what:
      'Refuses a bare sleep of ten seconds or more. A wait on a clock is a missing event: the ' +
      'estate\u2019s own answer for CI is the merge queue, which returns at once and merges on green.',
  },
  'feed-guard': {
    name: 'Handoff guard',
    what:
      'Blocks work when this session\u2019s last handoff to the estate feed is too old, so what one ' +
      'session learns reaches the others.',
  },
};

/** Parse one ledger line. A line that will not parse is skipped, never guessed at. */
export function parseEvent(line: string): GuardEvent | null {
  const t = line.trim();
  if (!t) return null;
  try {
    const o = JSON.parse(t) as GuardEvent;
    if (!o || typeof o.guard !== 'string' || typeof o.action !== 'string') return null;
    return o;
  } catch {
    return null;
  }
}

/**
 * Parse a whole ledger and summarise it per guard.
 *
 * `sinceMs` is the window the page reports: an old block from yesterday is not evidence that the
 * guard is working now, and showing it as such would be the same lie in the other direction.
 */
export function summarise(text: string, sinceMs: number, now = Date.now()): GuardSummary[] {
  const cutoff = now - sinceMs;
  const byGuard = new Map<string, GuardSummary>();
  for (const line of text.split('\n')) {
    const e = parseEvent(line);
    if (!e) continue;
    const at = Date.parse(e.at);
    if (Number.isNaN(at) || at < cutoff) continue;
    const known = GUARD_NAMES[e.guard] ?? { name: e.guard, what: '' };
    const cur =
      byGuard.get(e.guard) ??
      { guard: e.guard, name: known.name, what: known.what, events: 0, blocked: 0, lastAt: e.at, lastCommand: '' };
    cur.events += 1;
    if (e.action === 'block') cur.blocked += 1;
    if (e.at >= cur.lastAt) {
      cur.lastAt = e.at;
      cur.lastCommand = e.command ?? '';
    }
    byGuard.set(e.guard, cur);
  }
  return [...byGuard.values()].sort((a, b) => (a.lastAt < b.lastAt ? 1 : -1));
}

/**
 * The sentence above the table. It states the window and how many guards answered, and it says
 * plainly when nothing has fired -- because an empty ledger is the honest "no evidence" and not a
 * green tick.
 */
export function guardsSentence(rows: GuardSummary[], windowMin: number): string {
  if (!rows.length) {
    return `No guard has fired in the last ${windowMin} minutes. That is the absence of evidence, not proof the guards are idle.`;
  }
  const blocks = rows.reduce((n, r) => n + r.blocked, 0);
  const names = rows.map(r => r.name).join(', ');
  return `${rows.length} guard${rows.length === 1 ? '' : 's'} fired in the last ${windowMin} minutes (${names}); ${blocks} refused work.`;
}
