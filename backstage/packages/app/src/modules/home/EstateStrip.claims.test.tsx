// The claims segment of the estate strip: who holds what, and how much is left. Both /fleet and
// /face draw this strip, so one envelope keeps the two surfaces -- and the voice's brief -- from
// describing two different estates.
//
// Founder, 2026-10-23: "can we estimate based on goals and subgoals how much time or work left?"
// The number comes from the claim's own pace (claims.claims_glance -> plan_pace). This test pins
// the three honest readings: a live claim with time left, a claim whose pace is not measurable
// ("unknown", never a fabricated number), and an unreachable reader ("unavailable" with why).
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom/jest-globals';
import { describe, it, expect } from '@jest/globals';
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { fetchApiRef } from '@backstage/frontend-plugin-api';
import { EstateStrip } from './EstateStrip';

// An issue number written as a literal ("#6999") is a colour literal to the kit's purity guard
// -- six hex digits is a valid hex colour -- so the expectation is built from the number instead.
const ref = (n: number) => `#${n}`;

const render = (claims: unknown) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [
          fetchApiRef,
          {
            fetch: (async () => ({
              ok: true,
              json: async () => ({
                generated_at: '2026-10-23T19:00:00Z',
                green: { available: true, main: { green: true, sha: '892136c93' } },
                burn: { measured: true, total_usd: 0, calls: 0 },
                research: { available: true, claims: [] },
                claims,
              }),
            })) as unknown as typeof fetch,
          },
        ],
      ]}
    >
      <EstateStrip />
    </TestApiProvider>,
  );

describe('the strip tells the founder how much work is left', () => {
  it('shows the live count and the time left on the claim closest to done', async () => {
    await render({
      available: true,
      live: 3,
      stale: 1,
      next: {
        agent: 'pi',
        issue: 6999,
        title: 'status: one block',
        subgoals: '4/6',
        time_left:
          "5m-17m left (4 of 6 closed in 0.4h (this claim's own pace), +/-50%)",
      },
    });
    const text = await screen.findByText(
      new RegExp(`3 live · next pi ${ref(6999)} 5m-17m left`),
    );
    expect(text).toBeInTheDocument();
  });

  it('says unknown when the claim has no measurable pace, instead of inventing hours', async () => {
    await render({
      available: true,
      live: 1,
      stale: 0,
      next: {
        agent: 'claude',
        issue: 6974,
        title: 'fleet: each live plan shows time left',
        subgoals: '0/3',
        time_left: 'unknown -- no pace yet: 0 of 3 closed in 7.2h',
      },
    });
    expect(
      await screen.findByText(
        new RegExp(`1 live · next claude ${ref(6974)} unknown -- no pace yet`),
      ),
    ).toBeInTheDocument();
  });

  it('says unavailable with its reason when the claims reader did not answer', async () => {
    await render({ available: false, error: 'TimeoutError: gh stalled' });
    const chip = await screen.findByText('Claims: unavailable');
    expect(chip).toHaveAttribute('title', 'TimeoutError: gh stalled');
  });
});
