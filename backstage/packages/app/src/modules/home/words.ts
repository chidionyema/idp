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
  notLivePlain: 'Not live: we could not reach the machines just now, so what you see may be old.',
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
    return `We cannot tell what any of these ${total} ${plural(total)} ${verb(total)} doing.`;
  }

  const n = at(worst);
  switch (worst) {
    case 'red':
      return `${outOf(n, total)} ${verb(n)} failing right now.`;
    case 'needs':
      return `${outOf(n, total)} need${n === 1 ? 's' : ''} a person to act.`;
    case 'stale':
      return `${outOf(n, total)} ${verb(n)} overdue a check, so what we say about them may be old.`;
    case 'blind':
      return `${outOf(n, total)} cannot be read at all, so we do not know if they work.`;
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
  layers: SectionWords;
  doors: SectionWords;
  actions: SectionWords;
} = {
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

export type GlossaryTerm = 'service' | 'door' | 'system' | 'cluster';

export const GLOSSARY: Record<GlossaryTerm, string> = {
  service: 'A service is one running service of our software. Some screens call it a layer; it means the same thing.',
  door: 'A door is somewhere you sign in, such as the place we keep code or the screen for a tool we pay for.',
  system: 'A system is a group of services that work together to do one job.',
  cluster:
    'A cluster is the set of machines that runs our software and tells us whether each service is working.',
};
