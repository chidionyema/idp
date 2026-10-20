import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import GreenlaneHud, { isLoud, loudLabel, type Brief, type Greenlane } from './GreenlaneHud';

const reply = (body: unknown): Response =>
  ({ ok: true, status: 200, json: async () => body }) as unknown as Response;

const quietBrief: Brief = {
  loud: false,
  summary: 'nothing landing. all clear.',
  landing: null,
  waiting: 0,
  stuck: [],
  red: [],
  main_red: [],
  work_lost: 0,
};
const quiet: Greenlane = { available: true, brief: quietBrief };
const loud: Greenlane = {
  available: true,
  alarm: true,
  brief: {
    ...quietBrief,
    loud: true,
    landing: { lanes: ['lane/a', 'lane/b'], minutes: 41 },
    waiting: 2,
    stuck: [{ lane: 'lane/c', why: 'conflicts with main', status: 'conflict' }],
    red: [{ lane: 'lane/d', why: 'portal-app failure', owner: 'alice' }],
    main_red: ['ci-success'],
    work_lost: 1,
  },
};

describe('the quiet dot', () => {
  it('is quiet when the engine says nothing needs a person, and has no words', async () => {
    render(<GreenlaneHud call={async () => reply(quiet)} />);
    const dot = screen.getByTestId('greenlane-dot');
    await waitFor(() => expect(dot.getAttribute('aria-label')).toBe('greenlane · all quiet'));
    expect(dot.getAttribute('data-loud')).toBe('false');
    expect(dot.textContent).toBe('');
  });

  it('goes loud, with words, for an alarm, a red lane, a conflict or a long test', async () => {
    render(<GreenlaneHud call={async () => reply(loud)} />);
    await waitFor(() => expect(screen.getByText('lanes · main red')).toBeTruthy());
    expect(screen.getByTestId('greenlane-dot').getAttribute('data-loud')).toBe('true');
  });

  it('is loud, never quiet, for a lane it could not read', async () => {
    expect(isLoud(null, 'boom')).toBe(true);
    expect(isLoud({ available: false }, null)).toBe(true);
    expect(isLoud(null, null)).toBe(false); // still reading: nothing to shout about yet
    expect(loudLabel(null, 'boom')).toBe('lanes · unreachable');
    expect(loudLabel({ available: false }, null)).toBe('lanes · unreadable');
    render(<GreenlaneHud call={async () => Promise.reject(new Error('discovery not ready'))} />);
    await waitFor(() => expect(screen.getByText('lanes · unreachable')).toBeTruthy());
    fireEvent.click(screen.getByTestId('greenlane-dot'));
    expect(screen.getByTestId('greenlane-error').textContent).toContain('discovery not ready');
  });
});

describe('the detail answers three things', () => {
  it('says what is landing and for how long, what is stuck and why, what is red and who owns it', async () => {
    render(<GreenlaneHud call={async () => reply(loud)} />);
    await waitFor(() => expect(screen.getByText('lanes · main red')).toBeTruthy());
    fireEvent.click(screen.getByTestId('greenlane-dot'));
    expect(screen.getByTestId('greenlane-landing').textContent).toContain('a, b · 41 min');
    expect(screen.getByTestId('greenlane-stuck').textContent).toContain('conflicts with main');
    expect(screen.getByTestId('greenlane-red').textContent).toContain('portal-app failure · alice');
    expect(screen.getByTestId('greenlane-main').textContent).toContain('ci-success');
    expect(screen.getByTestId('greenlane-work-lost').textContent).toContain('work is lost');
  });

  it('says plainly when there is nothing to say', async () => {
    render(<GreenlaneHud call={async () => reply(quiet)} />);
    await waitFor(() => expect(screen.getByTestId('greenlane-dot')).toBeTruthy());
    fireEvent.click(screen.getByTestId('greenlane-dot'));
    expect(screen.getByText('nothing landing')).toBeTruthy();
    expect(screen.getByText('nothing stuck')).toBeTruthy();
    expect(screen.getByText('nothing red')).toBeTruthy();
  });
});

describe('opening by voice, then fading', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('a summon opens the detail and it fades; touching it keeps it alive', async () => {
    const { rerender } = render(<GreenlaneHud call={async () => reply(quiet)} fadeMs={1000} />);
    expect(screen.queryByRole('region')).toBeNull();
    rerender(<GreenlaneHud call={async () => reply(quiet)} fadeMs={1000} summon={1} />);
    await act(async () => {});
    const region = screen.getByRole('region');
    act(() => {
      jest.advanceTimersByTime(800);
    });
    fireEvent.pointerDown(region); // a person reading it keeps it alive
    act(() => {
      jest.advanceTimersByTime(800);
    });
    expect(screen.queryByRole('region')).not.toBeNull();
    act(() => {
      jest.advanceTimersByTime(300);
    });
    expect(screen.queryByRole('region')).toBeNull();
  });
});
