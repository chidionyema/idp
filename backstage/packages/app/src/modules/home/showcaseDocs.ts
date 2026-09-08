// The Showcase page's two documents, both read through the /estate-state proxy off the state
// branch (docs/specs/backstage-as-a-product.md, "The showcase page"): the estate bar that
// bin/estate-showcase writes into docs/SHOWCASE.md, and the Otto capability inventory whose
// LIVE lines are the abilities a buyer can try on the door today. Nothing is recomputed here;
// the page reads the numbers the writers already graded.
export const SHOWCASE_FILE = '/estate-state/docs/SHOWCASE.md';
export const OTTO_INVENTORY_FILE =
  '/estate-state/docs/specs/otto-capability-inventory.md';

export type Bar = {
  /** When bin/estate-showcase took the inventory, as the page states it. */
  takenAt?: string;
  entities: { elite: number; gap: number; blind: number; total: number };
  standards: { live: number; notYet: number; total: number };
};

const ENTITIES =
  /Entities:\s*\*\*(\d+) ELITE\*\*,\s*\*\*(\d+) GAP\*\*,\s*\*\*(\d+) BLIND\*\* of (\d+)/;
const STANDARDS = /Standards rows:\s*\*\*(\d+) live\*\*,\s*\*\*(\d+) not yet\*\* of (\d+)/;
const TAKEN = /inventory taken ([0-9TZ:.-]+)/;

/** The bar out of docs/SHOWCASE.md; undefined when the page does not carry it. */
export const parseBar = (md: string): Bar | undefined => {
  const e = ENTITIES.exec(md);
  const s = STANDARDS.exec(md);
  if (!e || !s) return undefined;
  const n = (x: string) => Number(x);
  return {
    takenAt: TAKEN.exec(md)?.[1],
    entities: { elite: n(e[1]), gap: n(e[2]), blind: n(e[3]), total: n(e[4]) },
    standards: { live: n(s[1]), notYet: n(s[2]), total: n(s[3]) },
  };
};

export type Ability = {
  /** The "### Senses" heading the line sits under. */
  sense: string;
  /** The plain sentence, bold stripped, up to the status word. */
  text: string;
  /** File receipts named after the status word, backticks stripped. */
  receipts: string[];
};

const LIVE = /(^|[\s,.])LIVE\b/;

/** Every LIVE line of the inventory's marketing list, in the file's own order. */
export const parseAbilities = (md: string): Ability[] => {
  const out: Ability[] = [];
  let sense = '';
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    if (line.startsWith('### ')) {
      sense = line.slice(4).trim();
      continue;
    }
    if (!line.startsWith('- ') || sense === '') continue;
    const m = LIVE.exec(line);
    if (!m) continue;
    const at = m.index + m[1].length;
    const text = line
      .slice(2, at)
      .replace(/\*\*/g, '')
      .replace(/[\s,.:;]+$/, '')
      .trim();
    const receipts = [...line.slice(at).matchAll(/`([^`]+)`/g)].map(x => x[1]);
    if (text) out.push({ sense, text, receipts });
  }
  return out;
};

/** A row one spec step away from LIVE: BUILT, or IN THE IMAGE (with optional suffix). */
export type ProgressionRow = {
  /** The "### Senses" heading the line sits under. */
  sense: string;
  /** The plain sentence, bold stripped, up to the status word. */
  text: string;
  /** The status as it appeared in the file (BUILT / IN THE IMAGE, ...). */
  status: string;
  /** "Step N" extracted from the line, when present; null otherwise. */
  stepNumber: number | null;
  /** File receipts named after the status word, backticks stripped. */
  receipts: string[];
};

const PROGRESSION = /(^|[\s,.])(BUILT|IN THE IMAGE(?:,?\s+(?:enabled|KEY NEEDED|and PLATFORM))?)\b/;
const STEP = /[Ss]tep\s+(\d+)/;

/**
 * Every BUILT or IN THE IMAGE row of the inventory's marketing list. Each row carries the
 * "Step N" the spec (`docs/specs/otto-door-hands-and-senses.md`) names that moves it to LIVE,
 * when the line says so. Order is the file's own order, under each heading. Live rows are
 * not returned; the LIVE filter above already covers them.
 */
export const parseProgression = (md: string): ProgressionRow[] => {
  const out: ProgressionRow[] = [];
  let sense = '';
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    if (line.startsWith('### ')) {
      sense = line.slice(4).trim();
      continue;
    }
    if (!line.startsWith('- ') || sense === '') continue;
    // Skip LIVE lines: they belong on the abilities section, not here.
    if (LIVE.exec(line)) continue;
    const m = PROGRESSION.exec(line);
    if (!m) continue;
    const at = m.index + m[1].length;
    const status = m[2];
    const text = line
      .slice(2, at)
      .replace(/\*\*/g, '')
      .replace(/[\s,.:;]+$/, '')
      .trim();
    const tail = line.slice(at);
    const stepMatch = STEP.exec(tail);
    const stepNumber = stepMatch ? Number(stepMatch[1]) : null;
    const receipts = [...tail.matchAll(/`([^`]+)`/g)].map(x => x[1]);
    if (text) out.push({ sense, text, status, stepNumber, receipts });
  }
  return out;
};

export const barSentence = (bar: Bar): string => {
  const { entities: e, standards: s } = bar;
  return `${e.total} catalogued things: ${e.elite} elite, ${e.gap} with a gap, ${e.blind} blind. ${s.live} of ${s.total} standards rows are live.`;
};

export const abilitiesSentence = (abilities: Ability[]): string => {
  if (abilities.length === 0) return 'No Otto ability is marked live yet.';
  const senses = [...new Set(abilities.map(a => a.sense))];
  return `${abilities.length} ${
    abilities.length === 1 ? 'ability' : 'abilities'
  } live on the door today, across ${senses.join(', ').toLowerCase()}.`;
};

/** One sentence about the BUILT/IN THE IMAGE rows the spec says move to LIVE next. */
export const progressionSentence = (rows: ProgressionRow[]): string => {
  if (rows.length === 0) return 'Nothing on the roadmap yet.';
  const withStep = rows.filter(r => r.stepNumber !== null);
  if (withStep.length === 0) return `${rows.length} rows on the roadmap, none pinned to a spec step yet.`;
  const steps = [...new Set(withStep.map(r => r.stepNumber as number))].sort((a, b) => a - b);
  const first = steps[0];
  const last = steps[steps.length - 1];
  return `${withStep.length} ${
    withStep.length === 1 ? 'row is' : 'rows are'
  } one spec step from live: step ${first}${first !== last ? ` to step ${last}` : ''}.`;
};

/**
 * Parse a duration string like "1h", "4h", "30m", "1h30m" to milliseconds. Returns undefined
 * for any other shape; the caller treats undefined as "the policy did not pin a hold, refuse
 * to draw a countdown rather than claim one".
 */
export const parseHoldMs = (s: string | undefined): number | undefined => {
  if (!s) return undefined;
  const m = /^(\d+)(h|m|s)$/.exec(s.trim());
  if (!m) return undefined;
  const n = Number(m[1]);
  if (!Number.isFinite(n) || n <= 0) return undefined;
  switch (m[2]) {
    case 'h': return n * 60 * 60 * 1000;
    case 'm': return n * 60 * 1000;
    case 's': return n * 1000;
    default: return undefined;
  }
};

/** Format a remaining-millisecond count as "N minutes left" / "N seconds left" / "gone". */
export const formatRemaining = (ms: number): string => {
  if (ms <= 0) return 'gone';
  if (ms < 60_000) {
    const s = Math.max(1, Math.round(ms / 1000));
    return `${s} ${s === 1 ? 'second' : 'seconds'} left`;
  }
  const m = Math.round(ms / 60_000);
  return `${m} ${m === 1 ? 'minute' : 'minutes'} left`;
};
