// The estate's guards, as the page reads them. WHAT THIS IS FOR, in the founder's words:
// "nothing is operational until proven to be in use and actively working." Fifty-six guards
// existing on disk proves nothing; a guard that fired 249 times and refused 105 commands is the
// proof. So this module draws the guards that FIRED, and it states the total beside them, because
// a table showing two rows and saying nothing about the other fifty-four reads as the whole estate
// when it is two guards out of fifty-six.
//
// The shape is what mcp/plugins/estate_guards.py returns: a total, a map of guards that fired
// (each with how many times it fired and how many commands it refused), and whatever could not be
// read. Nothing here invents a number; a guard with no reading is named as unreadable rather than
// drawn as zero, because zero fired and never ran are the same number and opposite facts.

export type GuardReading = {
  /** How many times this guard was consulted. */
  fired: number;
  /** How many of those times it answered no. A guard that never refuses is untested. */
  blocked: number;
  last_at?: string;
  last_command?: string;
};

export type GuardsDoc = {
  total_guards: number;
  fired: Record<string, GuardReading>;
  unreadable: string[];
};

export type GuardRow = {
  id: string;
  /** The name a person reads, not the identifier the file is called. */
  title: string;
  fired: number;
  blocked: number;
  last_at: string;
  last_command: string;
};

/** `sleep-ban` reads as "Sleep ban", `pre-commit` as "Pre commit`. */
export const title = (id: string): string => {
  const words = id.split(/[-_/]/).filter(Boolean);
  if (!words.length) return id;
  const [first, ...rest] = words;
  return [first.charAt(0).toUpperCase() + first.slice(1), ...rest].join(' ');
};

/**
 * Every guard that fired, busiest first. A guard with no firing is absent from this list on
 * purpose: it is not doing nothing, it is not being asked, and those are different findings.
 */
export const guardRows = (doc: GuardsDoc): GuardRow[] =>
  Object.entries(doc.fired ?? {})
    .map(([id, r]) => ({
      id,
      title: title(id),
      fired: r.fired ?? 0,
      blocked: r.blocked ?? 0,
      last_at: r.last_at ?? '',
      last_command: r.last_command ?? '',
    }))
    .sort((a, b) => b.fired - a.fired || a.id.localeCompare(b.id));

/**
 * One sentence carrying both numbers, so a short table is never mistaken for the whole estate.
 * The count of guards that fired is stated against the total that exist.
 */
export const guardsSentence = (doc: GuardsDoc): string => {
  const rows = guardRows(doc);
  const total = doc.total_guards ?? 0;
  const refused = rows.reduce((n, r) => n + r.blocked, 0);
  const fired = rows.reduce((n, r) => n + r.fired, 0);
  if (!rows.length) {
    return `No guard in the estate has fired yet, out of ${total} that exist — so none of them has been proved to be in use.`;
  }
  const unread =
    doc.unreadable?.length > 0
      ? ` ${doc.unreadable.length} could not be read and are not counted here.`
      : '';
  return `${rows.length} guards fired of ${total} that exist — ${fired} time(s), refusing ${refused} command(s).${unread}`;
};

/** True when the estate could not be asked about its guards at all. */
export const guardsUnreadable = (doc: GuardsDoc): boolean =>
  (doc.unreadable?.length ?? 0) > 0 && guardRows(doc).length === 0;
