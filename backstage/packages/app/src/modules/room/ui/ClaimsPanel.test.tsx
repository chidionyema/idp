import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ClaimsPanel,{
  ageLine,
  claimLabel,
  claimTone,
  claimToneFor,
  type Claims,
} from './ClaimsPanel';

const reply = (body: unknown): Response =>
  ({ ok: true, status: 200, json: async () => body }) as unknown as Response;

// The shape fleetview_backend/claims.py really returns, read on 2026-10-12.
const board: Claims = {
  available: true,
  claims: [
    {
      issue: 5818,
      title: 'front door: enforce the second factor',
      agent: 'otto',
      paths: ['.github/workflows/oke-check.yml', 'bin/idp-identity-apply'],
      heartbeat: '2026-10-12T05:30:00Z',
      age_s: 105,
      live: true,
      reason: 'live',
      url: 'https://github.com/chidionyema/idp/issues/5818',
      issue_open: true,
    },
    {
      issue: 5616,
      title: 'e2e: the phone voice turn must be heard',
      agent: 'opencode',
      paths: ['backstage/packages/app/e2e-tests/mobile-voice-turn.test.ts'],
      heartbeat: '2026-10-11T23:00:00Z',
      age_s: 17_547,
      live: false,
      reason: 'stale heartbeat',
      url: 'https://github.com/chidionyema/idp/issues/5616',
      issue_open: true,
    },
    {
      issue: 5788,
      title: "the twin's bus probe is unbounded",
      agent: 'chidionyema',
      paths: ['bin/estate-twin-runtime'],
      heartbeat: '2026-10-11T19:00:00Z',
      age_s: 37_268,
      live: false,
      reason: 'issue closed',
      url: 'https://github.com/chidionyema/idp/issues/5788',
      issue_open: false,
    },
  ],
  counts: { live: 1, released: 1, stale: 1, issues: 3 },
  source: 'chidionyema/idp issue comments',
  window_h: 12,
  truncated: true,
  read_at: '2026-10-12T05:32:00Z',
};

describe('the claim board', () => {
  it('says an age the way a person reads a clock', () => {
    expect(ageLine(45)).toBe('45s ago');
    expect(ageLine(600)).toBe('10 min ago');
    expect(ageLine(7200)).toBe('2.0 h ago');
    expect(ageLine(3 * 86400)).toBe('3 d ago');
    expect(ageLine(null)).toBe('heartbeat unreadable');
  });

  it('keeps a stale heartbeat apart from a released claim', () => {
    expect(claimTone('live')).toContain('emerald');
    expect(claimTone('stale heartbeat')).toContain('amber');
    expect(claimTone('unreadable heartbeat')).toContain('rose');
    expect(claimTone('issue closed')).toContain('white');
  });

  it('counts live claims only, and never reads an unreadable board as empty', () => {
    expect(claimLabel(null, 'boom')).toBe('claims · unreachable');
    expect(claimLabel(null, null)).toBe('claims · …');
    expect(claimLabel({ available: false, claims: [] }, null)).toBe('claims · unreadable');
    expect(claimLabel({ available: true, claims: [], counts: { live: 0, stale: 0 } }, null)).toBe(
      'claims · 0 live',
    );
    expect(claimLabel(board, null)).toBe('claims · 1 live · 1 stale');
    expect(claimToneFor({ available: false, claims: [] }, null)).toContain('rose');
    expect(claimToneFor(board, null)).toContain('amber');
  });

  it('leads with the live claims and their heartbeat age', async () => {
    render(<ClaimsPanel call={async () => reply(board)} />);
    await waitFor(() => expect(screen.getByText('claims · 1 live · 1 stale')).toBeTruthy());
    fireEvent.click(screen.getByText('claims · 1 live · 1 stale'));
    const list = screen.getByTestId('claims-list');
    expect(list.textContent).toContain('otto');
    expect(list.textContent).toContain('#5818 · 2 min ago');
    expect(list.textContent).toContain('.github/workflows/oke-check.yml');
    expect(screen.getByTestId('claim-reason-5616').textContent).toBe('stale heartbeat');
    expect(screen.getByTestId('claim-reason-5788').textContent).toBe('issue closed');
    // A claim read over a window must say how far back it looked and that the window filled.
    expect(screen.getByTestId('claims-footnote').textContent).toContain('last 12h');
    expect(screen.getByTestId('claims-footnote').textContent).toContain('older claims were not read');
  });

  it('a read that never reached GitHub is unreadable, not "nobody holds anything"', async () => {
    render(<ClaimsPanel call={async () => Promise.reject(new Error('discovery not ready'))} />);
    await waitFor(() => expect(screen.getByText('claims · unreachable')).toBeTruthy());
    fireEvent.click(screen.getByText('claims · unreachable'));
    expect(screen.getByTestId('claims-error').textContent).toContain('discovery not ready');
    expect(screen.queryByText(/no claim was posted/)).toBeNull();
  });

  it('an unreadable board body is not drawn as an empty one', async () => {
    render(
      <ClaimsPanel
        call={async () => reply({ available: false, error: 'GitHub is unreachable', claims: [] })}
      />,
    );
    await waitFor(() => expect(screen.getByText('claims · unreadable')).toBeTruthy());
    fireEvent.click(screen.getByText('claims · unreadable'));
    expect(screen.getByTestId('claims-error').textContent).toContain('GitHub is unreachable');
  });

  it('a readable board with no claims says so, with the window it looked over', async () => {
    render(
      <ClaimsPanel
        call={async () =>
          reply({
            available: true,
            claims: [],
            counts: { live: 0, released: 0, stale: 0, issues: 0 },
            source: 'chidionyema/idp issue comments',
            window_h: 12,
          })
        }
      />,
    );
    await waitFor(() => expect(screen.getByText('claims · 0 live')).toBeTruthy());
    fireEvent.click(screen.getByText('claims · 0 live'));
    expect(screen.getByTestId('claims-empty').textContent).toContain('last 12h');
  });
});
