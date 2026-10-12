import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import GreenlaneHud, {
  laneCounts,
  laneLabel,
  laneTone,
  laneToneFor,
  notGreen,
  type Greenlane,
} from './GreenlaneHud';

const reply = (body: unknown): Response =>
  ({ ok: true, status: 200, json: async () => body }) as unknown as Response;

// The shape bin/idp-greenlane status really prints, read on 2026-10-12.
const lane: Greenlane = {
  available: true,
  alarm: true,
  main: {
    green: false,
    sha: 'efdd4705485e',
    required: {
      'ci-success': 'absent',
      bdd: 'skipped',
      test: 'success',
      'guarded-paths': 'success',
    },
  },
  open_prs: [{ number: 5617, head: 'lane/test/voice-heard-2', user: 'chidionyema' }],
  invariants: { work_lost: 1, open_prs_not_raised_by_engine: 1 },
  state: {
    available: true,
    landed_total: 202,
    candidates_total: 2426,
    lanes: {
      'lane/a': { head: '8c83dd7fbea9', status: 'red', reason: 'executes-gate failure' },
      'lane/b': { head: '1111111111', status: 'red' },
      'lane/c': { head: '2222222222', status: 'landed' },
    },
  },
  read_at: '2026-10-12T05:00:00Z',
};

describe('the lane verdict', () => {
  it('lists only the checks the engine calls not-green', () => {
    // bin/idp-greenlane:278 -- success, skipped and neutral are all green; `absent` is not.
    expect(notGreen(lane.main!.required)).toEqual([['ci-success', 'absent']]);
    expect(notGreen({})).toEqual([]);
  });

  it('counts lanes worst-first', () => {
    expect(laneCounts(lane.state!.lanes)).toEqual([
      ['red', 2],
      ['landed', 1],
    ]);
    expect(laneCounts()).toEqual([]);
  });

  it('colours a red lane apart from a landed one', () => {
    expect(laneTone('red')).toContain('rose');
    expect(laneTone('landed')).toContain('emerald');
    expect(laneTone('conflict')).toContain('amber');
  });

  it('says main is not green and names the check that is not', async () => {
    render(<GreenlaneHud call={async () => reply(lane)} />);
    await waitFor(() => expect(screen.getByText('lanes · main red · 2 red')).toBeTruthy());
    fireEvent.click(screen.getByText('lanes · main red · 2 red'));
    expect(screen.getByTestId('greenlane-main').textContent).toContain('NOT green');
    expect(screen.getByTestId('greenlane-checks').textContent).toContain('ci-success · absent');
    // Work lost is the one thing the founder must never have to look for: it leads.
    expect(screen.getByTestId('greenlane-work-lost').textContent).toContain('work is lost');
    expect(screen.getByTestId('greenlane-open-prs').textContent).toContain('#5617');
    expect(screen.getByTestId('greenlane-lanes').textContent).toContain('executes-gate failure');
  });

  it('never says main is green without a main it actually read', () => {
    expect(laneLabel(null, 'boom')).toBe('lanes · unreachable');
    expect(laneLabel(null, null)).toBe('lanes · …');
    expect(laneLabel({ available: false }, null)).toBe('lanes · unreadable');
    expect(laneLabel({ available: true, main: { green: false } }, null)).toBe('lanes · main red');
    expect(laneLabel({ available: true, main: { green: true } }, null)).toBe('lanes · main green');
    // A green main carrying an alarm is still an alarm.
    expect(laneLabel({ available: true, main: { green: true }, alarm: true }, null)).toBe(
      'lanes · main green · alarm',
    );
    expect(laneToneFor({ available: false }, null)).toContain('rose');
    expect(laneToneFor(null, 'boom')).toContain('rose');
    expect(laneToneFor({ available: true, main: { green: true } }, null)).toContain('white');
  });

  it('a lane it cannot read says unreachable, never green', async () => {
    render(
      <GreenlaneHud call={async () => Promise.reject(new Error('discovery not ready'))} />,
    );
    await waitFor(() => expect(screen.getByText('lanes · unreachable')).toBeTruthy());
    fireEvent.click(screen.getByText('lanes · unreachable'));
    expect(screen.getByTestId('greenlane-error').textContent).toContain('discovery not ready');
  });

  it('an unreadable lane body is not drawn as a verdict', async () => {
    render(<GreenlaneHud call={async () => reply({ available: false, error: 'no bin/idp-greenlane' })} />);
    await waitFor(() => expect(screen.getByText('lanes · unreadable')).toBeTruthy());
    fireEvent.click(screen.getByText('lanes · unreadable'));
    expect(screen.getByTestId('greenlane-error').textContent).toContain('no bin/idp-greenlane');
  });
});
