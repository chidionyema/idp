// The plan-links segment of the estate strip: how many plans are linked to the instruction they
// serve and to the founder prompt that started them. The same canonical reader /plan-links
// serves, so the strip, the endpoint and the voice cannot disagree about the numbers.
//
// The three honest readings, the same contract the rest of the strip keeps: the numbers when
// the reader answered, "unavailable" WITH ITS REASON when it did not, and never a fabricated
// zero.
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect } from '@jest/globals';
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { fetchApiRef } from '@backstage/frontend-plugin-api';
import { EstateStrip } from './EstateStrip';

const render = (planLinks: unknown) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [
          fetchApiRef,
          {
            fetch: (async () => ({
              ok: true,
              json: async () => ({
                generated_at: '2026-10-31T13:00:00Z',
                green: { available: true, main: { green: true, sha: 'ad12f788f' } },
                burn: { measured: true, total_usd: 0, calls: 0 },
                research: { available: true, claims: [] },
                claims: { available: true, live: 0, stale: 0, next: null },
                plan_links: planLinks,
              }),
            })) as unknown as typeof fetch,
          },
        ],
      ]}
    >
      <EstateStrip />
    </TestApiProvider>,
  );

describe('the strip tells the founder how the plan links stand', () => {
  it('shows the counts when the reader answered', async () => {
    await render({
      available: true,
      sessions: 25,
      linked: 9,
      unlinked: 16,
      violations: 0,
      gaps: 46,
      summary: 'plan links: 25 sessions, 0 violations, 46 gaps',
    });
    const text = await screen.findByText(
      'plan links: 25 sessions, 0 violations, 46 gaps',
    );
    expect(text).toBeInTheDocument();
  });

  it('says unavailable with its reason when the reader did not answer', async () => {
    await render({ available: false, error: 'FileNotFoundError: no plan-link module' });
    const chip = await screen.findByText('Plan links: unavailable');
    expect(chip).toHaveAttribute('title', 'FileNotFoundError: no plan-link module');
  });
});
