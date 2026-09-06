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
