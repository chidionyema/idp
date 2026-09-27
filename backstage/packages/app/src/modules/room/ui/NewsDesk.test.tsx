import { describe, it, expect } from '@jest/globals';
import { render, fireEvent, screen } from '@testing-library/react';
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
  it('renders the on-screen story headline, anchor, and meta', () => {
    const story = makeStory({ count: 6 });
    render(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={0}
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
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
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
      />,
    );
    expect(screen.getByTestId('news-bug')).toHaveTextContent('LIVE');

    const reported = makeStory({ state: 'reported' });
    rerender(
      <NewsDesk
        rundown={rundownWith([reported])}
        channel={0}
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
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
        onChannel={() => {}}
        breaking={story}
        nowMs={NOW}
      />,
    );
    expect(screen.getByTestId('news-breaking')).toHaveTextContent('BREAKING NEWS');
    expect(screen.getByTestId('news-breaking')).toHaveTextContent(story.headline);

    rerender(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={0}
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
      />,
    );
    expect(screen.queryByTestId('news-breaking')).toBeNull();
  });

  it('hides the lower third and crawl on channel 6 (MOVIE)', () => {
    const story = makeStory({});
    render(
      <NewsDesk
        rundown={rundownWith([story])}
        channel={6}
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
      />,
    );
    expect(screen.getByTestId('news-bug')).toBeInTheDocument();
    expect(screen.getByTestId('news-channels')).toBeInTheDocument();
    expect(screen.queryByTestId('news-lower-third')).toBeNull();
    expect(screen.queryByTestId('news-crawl')).toBeNull();
  });

  it('calls onChannel(3) when the chip for channel 3 is clicked', () => {
    let clicked: number | null = null;
    render(
      <NewsDesk
        rundown={emptyRundown()}
        channel={0}
        onChannel={n => {
          clicked = n;
        }}
        breaking={null}
        nowMs={NOW}
      />,
    );
    fireEvent.click(screen.getByTestId('news-chip-3'));
    expect(clicked).toBe(3);
  });

  it('shows the empty-channel message when the channel has no stories', () => {
    render(
      <NewsDesk
        rundown={emptyRundown()}
        channel={0}
        onChannel={() => {}}
        breaking={null}
        nowMs={NOW}
      />,
    );
    expect(screen.getByTestId('news-lower-third')).toHaveTextContent('NO STORIES · NEWS');
    expect(screen.getByTestId('news-crawl')).toHaveTextContent('quiet on this channel');
  });
});
