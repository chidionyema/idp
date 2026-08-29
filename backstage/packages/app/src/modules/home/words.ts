// Every sentence the front page says out loud, in one file (crew#612, founder 2026-08-29).
//
// The founder's complaint was "6 RED 6 WHAT?" and "DON'T ASSUME THE USER KNOWS WHAT YOU KNOW".
// So nothing here is a bare number beside a bare word: every count arrives inside a sentence a
// stranger can read once and act on. Rules and sources: ./DESIGN-RULES.md.

import { State, STATE_ORDER, STATE_WORD } from '../theme/tokens';

/** A running service of software, said the way a stranger says it. */
const THING = { one: 'service', many: 'services' } as const;

const plural = (n: number) => (n === 1 ? THING.one : THING.many);
const verb = (n: number) => (n === 1 ? 'is' : 'are');

/** "6 of 31 services" — never "6" on its own. */
const outOf = (n: number, total: number) =>
  total > 0 && n < total
    ? `${n} of ${total} ${plural(total)}`
    : `${n} ${plural(n)}`;

const endStop = (sentence: string) =>
  /[.!?]$/.test(sentence.trim()) ? sentence.trim() : `${sentence.trim()}.`;

export type PageWords = {
  title: string;
  tagline: string;
  liveLabel: (readAtClock: string) => string;
  notLive: (why: string) => string;
  /** The plain sentence shown when the read failed; the raw reason goes in `notLiveDetail`. */
  notLivePlain: string;
  notLiveDetail: (why: string) => string;
};

export const PAGE: PageWords = {
  title: 'The Bytesync estate',
  tagline:
    'This is every service of software we run and every door we sign in through, read live from the machines that run them.',
  liveLabel: (readAtClock: string) => `Live: read at ${readAtClock}`,
  notLive: (why: string) => endStop(`Not live: ${why}`),
  notLivePlain:
    'Not live: we could not reach the machines just now, so what you see may be old.',
  notLiveDetail: (why: string) => endStop(`What the read said: ${why}`),
};

/** The one sentence at the top: worst state first, always a sentence. */
export function verdictSentence(
  counts: Record<State, number>,
  total: number,
): string {
  const at = (s: State) => Math.max(0, Math.trunc(counts?.[s] ?? 0));

  if (total <= 0) {
    return 'We have nothing to show yet, because nothing has been read.';
  }
  if (at('good') >= total) {
    return 'Everything we run is working.';
  }

  const worst = STATE_ORDER.find(s => at(s) > 0);
  if (!worst) {
    return `We cannot tell what any of these ${total} ${plural(total)} ${verb(
      total,
    )} doing.`;
  }

  const n = at(worst);
  switch (worst) {
    case 'red':
      return `${outOf(n, total)} ${verb(n)} failing right now.`;
    case 'needs':
      return `${outOf(n, total)} need${n === 1 ? 's' : ''} a person to act.`;
    case 'stale':
      return `${outOf(n, total)} ${verb(
        n,
      )} overdue a check, so what we say about them may be old.`;
    case 'blind':
      return `${outOf(
        n,
        total,
      )} cannot be read at all, so we do not know if they work.`;
    case 'running':
      return `${outOf(n, total)} ${verb(n)} still starting or changing.`;
    default:
      return 'Everything we run is working.';
  }
}

export type StateMeaning = {
  /** The word on the dot, from the theme so the page and the chart agree. */
  word: string;
  /** Three to six words, for a card. */
  short: string;
  /** One sentence a stranger understands. */
  long: string;
  /** What pressing it does. */
  action: string;
};

export const STATE_MEANING: Record<State, StateMeaning> = {
  red: {
    word: STATE_WORD.red,
    short: 'Failing right now',
    long: 'The machines that run this service report an error, so it is not doing its job.',
    action: 'Show only the failing services.',
  },
  needs: {
    word: STATE_WORD.needs,
    short: 'Waiting for a person',
    long: 'A person has to act before this service can work.',
    action: 'Show only the services waiting for a person.',
  },
  stale: {
    word: STATE_WORD.stale,
    short: 'Not checked recently',
    long: 'Nobody has checked this service recently, so what we say about it may be old.',
    action: 'Show only the services nobody has checked recently.',
  },
  blind: {
    word: STATE_WORD.blind,
    short: 'Nothing can read it',
    long: 'Nothing is able to read this service, so we cannot say whether it works.',
    action: 'Show only the services we cannot read.',
  },
  running: {
    word: STATE_WORD.running,
    short: 'Starting or changing',
    long: 'This service is still starting or changing, so its answer will move shortly.',
    action: 'Show only the services that are still changing.',
  },
  good: {
    word: STATE_WORD.good,
    short: 'Working as expected',
    long: 'This service reports itself healthy and is doing its job.',
    action: 'Show only the working services.',
  },
};

export type SectionWords = { title: string; blurb: string };

export const SECTIONS: {
  screens: SectionWords;
  kubernetes: SectionWords;
  everything: SectionWords;
  layers: SectionWords;
  doors: SectionWords;
  actions: SectionWords;
} = {
  screens: {
    title: 'Screens',
    blurb:
      'The screens you open and sign in to, each in a new tab, already knowing who you are. A grey one runs but has no address yet.',
  },
  kubernetes: {
    title: 'Kubernetes tooling',
    blurb:
      'Every tool that runs the cluster underneath everything: what deploys, routes, scales, secures and watches it. A grey one is running, but has no screen or no address yet; its manifest is the truth.',
  },
  everything: {
    title: 'Everything we hold',
    blurb:
      'Every thing the catalogue knows about, counted by what it is; choose one to list them.',
  },
  layers: {
    title: 'What we run',
    blurb:
      'Every service of software we run, grouped by the job it does; open a group to see each service and how it is doing.',
  },
  doors: {
    title: 'Doors',
    blurb:
      'The places you sign in to; choose one and it opens in a new tab, already knowing who you are.',
  },
  actions: {
    title: 'Do',
    blurb:
      'Jobs the platform can run for you; choose one, answer what it asks, and watch it finish here.',
  },
};

/** "No address yet" on a screen that runs without a public address. */
export const NO_ADDRESS_WORDS = 'No address yet';
/** A tool with no screen at all: nothing to open, and that is by design. */
export const NO_SCREEN_WORDS = 'No screen';
/** "Open" on a screen that has one. */
export const OPEN_WORD = 'Open';

/**
 * The plain word for each kind of thing the catalogue holds, keyed by `kind/type`. A key not
 * listed falls back to the type with its hyphens turned to spaces, so a new kind is still
 * readable, never hidden.
 */
export const INVENTORY_WORDS: Record<string, { one: string; many: string }> = {
  'Component/platform-layer': { one: 'service', many: 'services' },
  'Component/founder-surface': { one: 'door', many: 'doors' },
  'Component/flux-row': { one: 'deployment row', many: 'deployment rows' },
  'Component/helm-chart': { one: 'chart', many: 'charts' },
  'Component/service': { one: 'app', many: 'apps' },
  'Component/website': { one: 'website', many: 'websites' },
  'Component/cluster-choice': {
    one: 'cluster choice',
    many: 'cluster choices',
  },
  'Resource/ledger': { one: 'ledger', many: 'ledgers' },
  'Resource/guard': { one: 'guard', many: 'guards' },
  'Resource/data-store': { one: 'data store', many: 'data stores' },
  'Resource/port': { one: 'port', many: 'ports' },
  'Resource/drill': { one: 'drill', many: 'drills' },
  'Resource/scheduled-job': { one: 'scheduled job', many: 'scheduled jobs' },
  'Resource/vendor': { one: 'vendor', many: 'vendors' },
  'System/': { one: 'system', many: 'systems' },
  'Domain/': { one: 'company', many: 'companies' },
  'Group/team': { one: 'team', many: 'teams' },
  'Group/organization': { one: 'organisation', many: 'organisations' },
  'Template/': { one: 'action', many: 'actions' },
};

export function inventoryWord(
  kind: string,
  type: string | undefined,
  n: number,
): string {
  const w = INVENTORY_WORDS[`${kind}/${type ?? ''}`];
  if (w) return n === 1 ? w.one : w.many;
  const base = (type ?? kind).replace(/-/g, ' ').toLowerCase();
  return n === 1 ? base : `${base}s`;
}

/** "521 things" — the headline count of everything we hold. */
export const everythingSentence = (n: number) =>
  n === 1 ? 'We hold 1 thing.' : `We hold ${n} things.`;

export type GlossaryTerm = 'service' | 'door' | 'system' | 'cluster';

export const GLOSSARY: Record<GlossaryTerm, string> = {
  service:
    'A service is one running service of our software. Some screens call it a layer; it means the same thing.',
  door: 'A door is somewhere you sign in, such as the place we keep code or the screen for a tool we pay for.',
  system: 'A system is a group of services that work together to do one job.',
  cluster:
    'A cluster is the set of machines that runs our software and tells us whether each service is working.',
};
