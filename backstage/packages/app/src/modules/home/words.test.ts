import { State, STATE_ORDER, STATE_WORD } from '../theme/tokens';
import {
  GLOSSARY,
  PAGE,
  SECTIONS,
  STATE_MEANING,
  verdictSentence,
  everythingSentence,
  inventoryWord,
  NO_ADDRESS_WORDS,
} from './words';

const zero: Record<State, number> = {
  red: 0,
  needs: 0,
  stale: 0,
  blind: 0,
  running: 0,
  good: 0,
};
const counts = (
  over: Partial<Record<State, number>>,
): Record<State, number> => ({ ...zero, ...over });

describe('PAGE', () => {
  it('says what the page is in one sentence a stranger can read', () => {
    expect(PAGE.title.length).toBeGreaterThan(3);
    expect(PAGE.tagline).toMatch(/every service of software we run/);
    expect(PAGE.tagline.split(' ').length).toBeLessThan(40);
  });

  it('labels a live read with the clock time', () => {
    expect(PAGE.liveLabel('16:52')).toBe('Live: read at 16:52');
  });

  it('says why it is not live, as a finished sentence', () => {
    expect(PAGE.notLive('we could not reach the machines')).toBe(
      'Not live: we could not reach the machines.',
    );
    expect(PAGE.notLive('the last read failed.')).toBe(
      'Not live: the last read failed.',
    );
  });
});

describe('verdictSentence', () => {
  it('empty: says there is nothing to show and why', () => {
    expect(verdictSentence(zero, 0)).toBe(
      'We have nothing to show yet, because nothing has been read.',
    );
  });

  it('all good: one short sentence, no numbers needed', () => {
    expect(verdictSentence(counts({ good: 31 }), 31)).toBe(
      'Everything we run is working.',
    );
  });

  it('one red: names the count against the total', () => {
    expect(verdictSentence(counts({ red: 1, good: 30 }), 31)).toBe(
      '1 of 31 services is failing right now.',
    );
  });

  it('mixed: the worst state speaks first', () => {
    expect(
      verdictSentence(counts({ red: 6, needs: 3, stale: 2, good: 20 }), 31),
    ).toBe('6 of 31 services are failing right now.');
    expect(verdictSentence(counts({ needs: 3, good: 28 }), 31)).toBe(
      '3 of 31 services need a person to act.',
    );
    expect(verdictSentence(counts({ needs: 1, good: 30 }), 31)).toBe(
      '1 of 31 services needs a person to act.',
    );
    expect(
      verdictSentence(counts({ blind: 4, running: 1, good: 26 }), 31),
    ).toBe(
      '4 of 31 services cannot be read at all, so we do not know if they work.',
    );
  });

  it('never puts a bare number next to a bare state word', () => {
    const sentence = verdictSentence(counts({ red: 6, good: 25 }), 31);
    expect(sentence).not.toMatch(/^\d+\s+(Red|Good|Stale|Running)\b/);
    expect(sentence.endsWith('.')).toBe(true);
  });

  it('appends blind count when worst is not blind', () => {
    const result = verdictSentence(counts({ red: 3, blind: 9 }), 40);
    expect(result.endsWith('We cannot check 9 more.')).toBe(true);
    expect(result.startsWith('3 of 40 services are failing right now.')).toBe(true);
  });

  it('does not append blind clause when blind is zero', () => {
    const result = verdictSentence(counts({ red: 3, blind: 0 }), 40);
    expect(result).not.toContain('We cannot check');
  });

  // When 'blind' is itself the worst state the base sentence is already about the unreadable
  // ones, so the clause must not be bolted on after it and say the same thing twice.
  it('does not append the clause when blind is already the subject', () => {
    const result = verdictSentence(counts({ blind: 5 }), 40);
    expect(result).not.toContain('We cannot check');
    expect(result).toContain('cannot be read at all');
  });

  it('all good with blind zero does not change', () => {
    const result = verdictSentence(counts({ good: 40, blind: 0 }), 40);
    expect(result).toBe('Everything we run is working.');
  });
});

describe('STATE_MEANING', () => {
  it('covers all six states and agrees with the theme on the word', () => {
    STATE_ORDER.forEach((s: State) => {
      const m = STATE_MEANING[s];
      expect(m.word).toBe(STATE_WORD[s]);
      const shortWords = m.short.split(' ').length;
      expect(shortWords).toBeGreaterThanOrEqual(3);
      expect(shortWords).toBeLessThanOrEqual(6);
      expect(m.long.endsWith('.')).toBe(true);
      expect(m.action.startsWith('Show only')).toBe(true);
    });
  });
});

describe('SECTIONS', () => {
  it('gives every section a plain title and a one-sentence blurb', () => {
    expect(SECTIONS.layers.title).toBe('What we run');
    expect(SECTIONS.doors.title).toBe('Sign-in pages');
    expect(SECTIONS.actions.title).toBe('Do');
    [SECTIONS.layers, SECTIONS.doors, SECTIONS.actions].forEach(s => {
      expect(s.blurb.endsWith('.')).toBe(true);
      expect(s.blurb.split(' ').length).toBeLessThan(40);
    });
  });
});

describe('GLOSSARY', () => {
  it('defines each word without using the word to define itself alone', () => {
    (['service', 'sign-in page', 'system', 'cluster'] as const).forEach(term => {
      expect(GLOSSARY[term].toLowerCase()).toContain(term);
      expect(GLOSSARY[term].endsWith('.')).toBe(true);
    });
  });
});

describe('no insider words anywhere on the page', () => {
  const banned = [
    'k8s',
    'kustomization',
    'flux',
    'pod',
    'reconcile',
    'entity',
    'catalogue',
  ];

  const strings: string[] = [
    PAGE.title,
    PAGE.tagline,
    PAGE.liveLabel('16:52'),
    PAGE.notLive('the read failed'),
    verdictSentence(zero, 0),
    verdictSentence(counts({ good: 31 }), 31),
    verdictSentence(counts({ red: 6, good: 25 }), 31),
    verdictSentence(counts({ needs: 3, good: 28 }), 31),
    verdictSentence(counts({ stale: 3, good: 28 }), 31),
    verdictSentence(counts({ blind: 3, good: 28 }), 31),
    verdictSentence(counts({ running: 3, good: 28 }), 31),
    ...STATE_ORDER.flatMap((s: State) => [
      STATE_MEANING[s].word,
      STATE_MEANING[s].short,
      STATE_MEANING[s].long,
      STATE_MEANING[s].action,
    ]),
    ...[SECTIONS.layers, SECTIONS.doors, SECTIONS.actions].flatMap(s => [
      s.title,
      s.blurb,
    ]),
    ...Object.values(GLOSSARY),
  ];

  it.each(banned)('never says "%s"', word => {
    const offenders = strings.filter(s => s.toLowerCase().includes(word));
    expect(offenders).toEqual([]);
  });
});

describe('inventory words', () => {
  it('names each kind of thing in plain words, one or many', () => {
    expect(inventoryWord('Component', 'platform-layer', 1)).toBe('service');
    expect(inventoryWord('Component', 'founder-surface', 29)).toBe('sign-in pages');
    expect(inventoryWord('Resource', 'ledger', 187)).toBe('ledgers');
    expect(inventoryWord('Domain', undefined, 4)).toBe('companies');
    expect(inventoryWord('Resource', 'odd-thing', 2)).toBe('odd things');
  });

  it('says how many things we hold, in a sentence', () => {
    expect(everythingSentence(521)).toBe('We hold 521 things.');
    expect(everythingSentence(1)).toBe('We hold 1 thing.');
    expect(NO_ADDRESS_WORDS).toBe('No address yet');
  });
});

describe('role grouping (directive 3: kind reads as one thing, not a tag split)', () => {
  it('gives each band-of-kind a role, in the estate plain voice', () => {
    // Screens, Kubernetes tooling and Sign-in pages are the same kind of thing a person opens.
    // The role line lets a reader see that instead of three unrelated tag bands.
    expect(SECTIONS.screens.role).toBe('Pages you open');
    expect(SECTIONS.kubernetes.role).toBe('Pages you open');
    expect(SECTIONS.doors.role).toBe('Pages you open');
  });

  it('keeps the role a single short phrase in the shared plain vocabulary', () => {
    for (const s of [SECTIONS.screens, SECTIONS.kubernetes, SECTIONS.doors]) {
      expect(s.role).toBeTruthy();
      // No banned insider jargon smuggled into the grouping line.
      for (const banned of [
        'k8s',
        'kustomization',
        'flux',
        'entity',
        'catalogue',
        'tag',
        'band',
      ]) {
        expect((s.role as string).toLowerCase()).not.toContain(banned);
      }
    }
  });
});
