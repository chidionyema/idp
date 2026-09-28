import {
  CHANNELS,
  channelForKey,
  parseStoryFrame,
  emptyRundown,
  ingest,
  shouldInterrupt,
  visualFor,
  ago,
} from './newsRundown';
import type { Story, StoryFrame } from './newsRundown';

function makeStory(overrides: Partial<Story> = {}): Story {
  return {
    id: 's1',
    channel: 'news',
    source: 'director',
    severity: 'info',
    state: 'reported',
    headline: 'headline',
    anchor: 'anchor',
    entity: 'entity',
    evidence: [],
    score: 1,
    count: 1,
    breaking: false,
    first_at: '2026-09-27T00:00:00.000Z',
    at: '2026-09-27T00:00:00.000Z',
    ...overrides,
  };
}

function makeFrame(story: Partial<Story> = {}, on: Story['channel'] = 'news'): StoryFrame {
  return { type: 'story', on, story: makeStory(story) };
}

describe('CHANNELS', () => {
  it('has the seven channels in order with movie last', () => {
    expect(CHANNELS.map(c => c.key)).toEqual([
      'news',
      'agents',
      'deploys',
      'cluster',
      'metrics',
      'products',
      'movie',
    ]);
    expect(CHANNELS[6]).toEqual({ n: 6, key: 'movie', label: 'MOVIE' });
  });
});

describe('channelForKey', () => {
  it('maps keys 0-6', () => {
    expect(channelForKey('news')).toBe(0);
    expect(channelForKey('deploys')).toBe(2);
    expect(channelForKey('movie')).toBe(6);
  });

  it('returns null for unknown keys', () => {
    expect(channelForKey('bogus')).toBeNull();
  });
});

describe('parseStoryFrame', () => {
  it('parses a valid frame', () => {
    const raw = makeFrame({ id: 'abc' });
    const parsed = parseStoryFrame(raw);
    expect(parsed).not.toBeNull();
    expect(parsed?.story.id).toBe('abc');
    expect(parsed?.on).toBe('news');
  });

  it('rejects a frame with the wrong type', () => {
    expect(parseStoryFrame({ type: 'cue', on: 'news', story: makeStory() })).toBeNull();
  });

  it('rejects a frame with an unknown channel', () => {
    expect(parseStoryFrame({ type: 'story', on: 'bogus', story: makeStory() })).toBeNull();
  });

  it('rejects a story missing required fields', () => {
    const bad = { type: 'story', on: 'news', story: { id: 'x' } };
    expect(parseStoryFrame(bad)).toBeNull();
  });

  it('rejects a story with an invalid severity', () => {
    const raw = { type: 'story', on: 'news', story: { ...makeStory(), severity: 'critical' } };
    expect(parseStoryFrame(raw)).toBeNull();
  });

  it('rejects non-object input', () => {
    expect(parseStoryFrame(null)).toBeNull();
    expect(parseStoryFrame('hello')).toBeNull();
    expect(parseStoryFrame(42)).toBeNull();
  });

  it('accepts an optional supersedes and link', () => {
    const raw = makeFrame({ supersedes: 'old-id', link: 'https://example.test' });
    const parsed = parseStoryFrame(raw);
    expect(parsed?.story.supersedes).toBe('old-id');
    expect(parsed?.story.link).toBe('https://example.test');
  });
});

describe('ingest', () => {
  it('adds a new story to its channel', () => {
    const rundown = emptyRundown();
    const frame = makeFrame({ id: 's1' }, 'agents');
    const next = ingest(rundown, frame, 0);
    expect(next.agents.map(s => s.id)).toEqual(['s1']);
    expect(next.news).toEqual([]);
  });

  it('replaces an existing id in place rather than duplicating', () => {
    const rundown = emptyRundown();
    const first = ingest(rundown, makeFrame({ id: 's1', count: 1 }), 0);
    const second = ingest(first, makeFrame({ id: 's1', count: 2 }), 0);
    expect(second.news).toHaveLength(1);
    expect(second.news[0].count).toBe(2);
  });

  it('removes a superseded id from every channel', () => {
    let rundown = emptyRundown();
    rundown = ingest(rundown, makeFrame({ id: 'old' }, 'agents'), 0);
    rundown = ingest(rundown, makeFrame({ id: 'old' }, 'cluster'), 0);
    rundown = ingest(
      rundown,
      makeFrame({ id: 'new', supersedes: 'old' }, 'agents'),
      0,
    );
    expect(rundown.agents.map(s => s.id)).toEqual(['new']);
    expect(rundown.cluster.map(s => s.id)).toEqual([]);
  });

  it('caps a channel at 50, dropping the lowest-ranked', () => {
    let rundown = emptyRundown();
    for (let i = 0; i < 51; i++) {
      rundown = ingest(
        rundown,
        makeFrame({ id: `s${i}`, score: i, at: '2026-09-27T00:00:00.000Z' }, 'metrics'),
        0,
      );
    }
    expect(rundown.metrics).toHaveLength(50);
    expect(rundown.metrics.find(s => s.id === 's0')).toBeUndefined();
    expect(rundown.metrics.find(s => s.id === 's50')).toBeDefined();
  });

  it('ranks breaking stories first, then by score desc, then by at desc', () => {
    let rundown = emptyRundown();
    rundown = ingest(
      rundown,
      makeFrame({ id: 'low-score', score: 1, at: '2026-09-27T00:00:00.000Z' }, 'products'),
      0,
    );
    rundown = ingest(
      rundown,
      makeFrame({ id: 'high-score', score: 9, at: '2026-09-27T00:00:00.000Z' }, 'products'),
      0,
    );
    rundown = ingest(
      rundown,
      makeFrame(
        { id: 'breaking', score: 0, breaking: true, at: '2026-09-27T00:00:00.000Z' },
        'products',
      ),
      0,
    );
    rundown = ingest(
      rundown,
      makeFrame({ id: 'newer-same-score', score: 9, at: '2026-09-27T00:05:00.000Z' }, 'products'),
      0,
    );
    expect(rundown.products.map(s => s.id)).toEqual([
      'breaking',
      'newer-same-score',
      'high-score',
      'low-score',
    ]);
  });
});

describe('shouldInterrupt', () => {
  const nowMs = Date.parse('2026-09-27T00:00:00.000Z');

  it('is true for a fresh breaking story within 120s and unseen', () => {
    const story = makeStory({ breaking: true, at: '2026-09-27T00:00:00.000Z' });
    expect(shouldInterrupt(story, nowMs, new Set())).toBe(true);
  });

  it('is false for a non-breaking story', () => {
    const story = makeStory({ breaking: false, at: '2026-09-27T00:00:00.000Z' });
    expect(shouldInterrupt(story, nowMs, new Set())).toBe(false);
  });

  it('is false when the story is older than 120s', () => {
    const story = makeStory({ breaking: true, at: '2026-09-26T23:57:00.000Z' });
    expect(shouldInterrupt(story, nowMs, new Set())).toBe(false);
  });

  it('never interrupts again once the id has already interrupted (replay)', () => {
    const story = makeStory({ id: 'already-seen', breaking: true, at: '2026-09-27T00:00:00.000Z' });
    expect(shouldInterrupt(story, nowMs, new Set(['already-seen']))).toBe(false);
  });
});

describe('visualFor', () => {
  it('renders fire for danger severity', () => {
    expect(visualFor(makeStory({ severity: 'danger' }))).toEqual({
      ring: 'fire',
      color: '#ff0055',
      burst: 8,
      shot: 'MACRO_DOV',
    });
  });

  it('renders fire for breaking regardless of severity', () => {
    expect(visualFor(makeStory({ severity: 'info', breaking: true }))).toEqual({
      ring: 'fire',
      color: '#ff0055',
      burst: 8,
      shot: 'MACRO_DOV',
    });
  });

  it('renders a green orbit pulse for a confirmed deploy', () => {
    expect(
      visualFor(makeStory({ channel: 'deploys', state: 'confirmed', severity: 'info' })),
    ).toEqual({
      ring: 'pulse',
      color: '#00ffaa',
      burst: 3,
      shot: 'ORBIT_FOCUS',
    });
  });

  it('renders a green pulse with no burst for a corrected story', () => {
    expect(visualFor(makeStory({ state: 'corrected', severity: 'info' }))).toEqual({
      ring: 'pulse',
      color: '#00ffaa',
      burst: 0,
      shot: null,
    });
  });

  it('renders an amber pulse for warn', () => {
    expect(visualFor(makeStory({ severity: 'warn' }))).toEqual({
      ring: 'pulse',
      color: '#ffb000',
      burst: 0,
      shot: null,
    });
  });

  it('renders a cyan pulse for info', () => {
    expect(visualFor(makeStory({ severity: 'info' }))).toEqual({
      ring: 'pulse',
      color: '#00f0ff',
      burst: 0,
      shot: null,
    });
  });
});

describe('ago', () => {
  const nowMs = Date.parse('2026-09-27T12:00:00.000Z');

  it('renders "now" for under a minute', () => {
    expect(ago('2026-09-27T11:59:30.000Z', nowMs)).toBe('now');
  });

  it('renders minutes for under an hour', () => {
    expect(ago('2026-09-27T11:57:00.000Z', nowMs)).toBe('3m');
  });

  it('renders hours for an hour or more', () => {
    expect(ago('2026-09-27T10:00:00.000Z', nowMs)).toBe('2h');
  });
});
