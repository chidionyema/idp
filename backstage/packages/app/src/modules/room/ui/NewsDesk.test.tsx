import { describe, it, expect } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import NewsDesk from './NewsDesk.tsx';
import { emptyRundown } from './newsRundown';
import type { Rundown, Story } from './newsRundown';

const NOW = Date.parse('2026-09-27T12:00:00Z');

function makeStory(overrides: Partial<Story>): Story {
  return {
    id: 's1',
    channel: 'news',
    source: 'director',
    severity: 'info',
    state: 'reported',
    headline: 'Cluster stabilised after node drain',
    anchor: 'Calico came back Ready on all nodes.',
    entity: 'oke-cluster',
    evidence: [],
    score: 2,
    count: 1,
    breaking: false,
    first_at: new Date(NOW - 60_000).toISOString(),
    at: new Date(NOW - 30_000).toISOString(),
    ...overrides,
  };
}

function rundownWith(stories: Story[]): Rundown {
  const rundown = emptyRundown();
  for (const s of stories) {
    rundown[s.channel] = [...rundown[s.channel], s];
  }
  return rundown;
}

describe('NewsDesk', () => {
  it('is dark until summoned: nothing is rendered over the void', () => {
    const story = makeStory({});
    const { container } = render(
      <NewsDesk rundown={rundownWith([story])} channel={0} breaking={null} nowMs={NOW} />,
    );

    // THE ZERO-CHROME CONTRACT: with nothing summoned and nothing breaking, the desk renders no
    // visible node at all -- no persistent bar, ribbon or badge over the void.
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId('news-bug')).toBeNull();
    expect(screen.queryByTestId('news-lower-third')).toBeNull();
  });

  it('renders the on-screen story headline, anchor, and meta when summoned', () => {
    const story = makeStory({ count: 6 });
    render(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={0}
        breaking={null}
        nowMs={NOW}
        summoned
      />,
    );

    expect(screen.getByTestId('news-lower-third')).toHaveTextContent(
      'Cluster stabilised after node drain',
    );
    expect(screen.getByTestId('news-lower-third')).toHaveTextContent(
      'Calico came back Ready on all nodes.',
    );
    expect(screen.getByTestId('news-lower-third')).toHaveTextContent('×6');
  });

  it('shows the LIVE pill only when the on-screen story is confirmed', () => {
    const confirmed = makeStory({ state: 'confirmed' });
    const { rerender } = render(
      <NewsDesk
        rundown={rundownWith([confirmed])}
        channel={0}
        breaking={null}
        nowMs={NOW}
        summoned
      />,
    );
    expect(screen.getByTestId('news-bug')).toHaveTextContent('LIVE');

    const reported = makeStory({ state: 'reported' });
    rerender(
      <NewsDesk
        rundown={rundownWith([reported])}
        channel={0}
        breaking={null}
        nowMs={NOW}
        summoned
      />,
    );
    expect(screen.getByTestId('news-bug')).not.toHaveTextContent('LIVE');
    expect(screen.getByTestId('news-bug')).toHaveTextContent('REPORTED');
  });

  it('renders the breaking band only when a breaking story is set', () => {
    const story = makeStory({ breaking: true });
    const { rerender } = render(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={0}
        breaking={story}
        nowMs={NOW}
      />,
    );
    expect(screen.getByTestId('news-breaking')).toHaveTextContent('BREAKING NEWS');
    expect(screen.getByTestId('news-breaking')).toHaveTextContent(story.headline);

    rerender(
      <NewsDesk rundown={rundownWith([story])} channel={0} breaking={null} nowMs={NOW} />,
    );
    expect(screen.queryByTestId('news-breaking')).toBeNull();
  });

  it('renders nothing on channel 6 (MOVIE) even when summoned', () => {
    const story = makeStory({});
    const { container } = render(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={6}
        breaking={null}
        nowMs={NOW}
        summoned
      />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId('news-bug')).toBeNull();
    expect(screen.queryByTestId('news-lower-third')).toBeNull();
  });

  it('shows the empty-channel message when the summoned channel has no stories', () => {
    render(
      <NewsDesk
        rundown={emptyRundown()}
        channel={0}
        breaking={null}
        nowMs={NOW}
        summoned
      />,
    );
    expect(screen.getByTestId('news-lower-third')).toHaveTextContent('NO STORIES · NEWS');
  });
});
