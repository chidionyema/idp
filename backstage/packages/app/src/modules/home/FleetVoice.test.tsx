import {
  describe,
  it,
  expect,
  jest,
  afterEach,
  beforeEach,
} from '@jest/globals';
import { render, fireEvent, act, screen } from '@testing-library/react';
import FleetVoice, { parseIntent } from './FleetVoice';
import type { Session } from './fleetBoard';

// ---------------------------------------------------------------------------
// Fakes for jsdom
// ---------------------------------------------------------------------------

class FakeSpeechRecognition {
  static instances: FakeSpeechRecognition[] = [];
  lang = '';
  continuous = false;
  interimResults = false;
  started = false;
  stopped = false;
  aborted = false;
  onresult: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onend: (() => void) | null = null;

  /** Cumulative, exactly as the platform exposes it. */
  results: any[] = [];

  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }

  start() {
    this.started = true;
  }

  stop() {
    this.stopped = true;
    if (this.onend) this.onend();
  }

  abort() {
    this.aborted = true;
  }

  /**
   * Emit a result the way the REAL API does.
   *
   * `SpeechRecognitionEvent.results` is CUMULATIVE: results[0] is the first utterance of the
   * session and results[n] the latest, and `resultIndex` says which one this event is about. The
   * first version of this fake sent a one-element array with `resultIndex: 0` for every call, so
   * a second emit re-reported the first transcript as final and the component -- which correctly
   * accumulates from `resultIndex` -- produced
   * "try the other branch steer agent-beta try the other branch".
   *
   * The bug was in the fake, not the component. That is worth keeping written down: a fake that
   * is not the real shape invents product bugs and hides real ones.
   */
  emitResult(transcript: string, isFinal: boolean) {
    this.results.push(Object.assign([{ transcript }], { isFinal }));
    const event = {
      resultIndex: this.results.length - 1,
      results: this.results,
    };
    if (this.onresult) this.onresult(event);
  }
}

interface FakeUtterance {
  text: string;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}

const spoken: FakeUtterance[] = [];
let cancelCount = 0;

function installSynthesis() {
  const synth = {
    speak: (u: FakeUtterance) => {
      spoken.push(u);
    },
    cancel: () => {
      cancelCount += 1;
    },
  };
  (window as any).speechSynthesis = synth;
  (window as any).SpeechSynthesisUtterance = function (
    this: FakeUtterance,
    text: string,
  ) {
    this.text = text;
    this.onend = null;
    this.onerror = null;
  } as any;
}

function uninstallSynthesis() {
  delete (window as any).speechSynthesis;
  delete (window as any).SpeechSynthesisUtterance;
}

function installRecognition() {
  (window as any).webkitSpeechRecognition = FakeSpeechRecognition;
}

function uninstallRecognition() {
  delete (window as any).webkitSpeechRecognition;
  delete (window as any).SpeechRecognition;
}

const sessions: Session[] = [
  {
    session_id: 'agent-alpha',
    runtime: 'claude',
    task: 'fix the parser',
    state: 'running',
    activity: 'stuck',
    event_count: 12,
    repo: 'idp',
    updated_at: '2026-09-18T00:00:00Z',
    spend_usd: 1.2,
    pull_requests: [],
    ticket: 'IDP-1',
  },
  {
    session_id: 'agent-beta',
    runtime: 'codex',
    task: 'write tests',
    state: 'running',
    activity: 'waiting',
    event_count: 3,
    repo: 'idp',
    updated_at: '2026-09-18T00:00:00Z',
    spend_usd: 0.4,
    pull_requests: [],
    ticket: 'IDP-2',
  },
];

beforeEach(() => {
  FakeSpeechRecognition.instances = [];
  spoken.length = 0;
  cancelCount = 0;
  installRecognition();
  installSynthesis();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
  uninstallRecognition();
  uninstallSynthesis();
});

// ---------------------------------------------------------------------------
// parseIntent unit coverage
// ---------------------------------------------------------------------------

describe('parseIntent', () => {
  it('maps "what is stuck" to a stuck query', () => {
    expect(parseIntent('what is stuck')).toEqual({
      kind: 'query',
      activity: 'stuck',
      raw: 'what is stuck',
    });
  });

  it('maps "show me waiting" to a waiting query', () => {
    expect(parseIntent('show me waiting')).toEqual({
      kind: 'query',
      activity: 'waiting',
      raw: 'show me waiting',
    });
  });

  it('maps "stop <agent>" to a stop mutation', () => {
    expect(parseIntent('stop agent-alpha')).toEqual({
      kind: 'stop',
      target: 'agent-alpha',
      raw: 'stop agent-alpha',
    });
  });

  it('maps "steer <agent> <text>" to a steer mutation', () => {
    expect(parseIntent('steer agent-beta try the other branch')).toEqual({
      kind: 'steer',
      target: 'agent-beta',
      text: 'try the other branch',
      raw: 'steer agent-beta try the other branch',
    });
  });

  it('treats unnamed input as unknown, never a mutation', () => {
    expect(parseIntent('delete everything')).toEqual({
      kind: 'unknown',
      raw: 'delete everything',
    });
  });
});

// ---------------------------------------------------------------------------
// Component behaviour
// ---------------------------------------------------------------------------

describe('FleetVoice', () => {
  it('starts recognition on press and shows interim text live', () => {
    render(<FleetVoice sessions={sessions} />);
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    expect(FakeSpeechRecognition.instances.length).toBe(1);
    expect(FakeSpeechRecognition.instances[0].started).toBe(true);
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'LISTENING',
    );

    act(() => {
      FakeSpeechRecognition.instances[0].emitResult('what is', false);
    });
    expect(screen.getByTestId('voice-interim').textContent).toContain(
      'what is',
    );
  });

  /**
   * A QUESTION FILTERS IMMEDIATELY, AND THE CHIP IS FOR MUTATIONS ONLY.
   *
   * This test used to assert the opposite -- that releasing showed a chip and that `onFilter`
   * waited 1.5s for a grace window -- and it was left behind when GRACE_MS was deliberately made
   * mutation-only. The reason is in FleetVoice's own comment and it is a measurement: a question
   * changes nothing, so a cancellation window protects nothing, and it cost 1500ms of the 3093ms
   * before the first spoken clause. Removing it is the whole point of that commit.
   *
   * So the assertion is inverted to match the design, and it now checks the thing that actually
   * protects a person: the query lands at once, and NO chip appears asking to cancel something
   * that has already run.
   */
  it('applies a QUERY immediately, with no grace window and no cancellation chip', () => {
    const onFilter = jest.fn();
    render(<FleetVoice sessions={sessions} onFilter={onFilter} />);
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    act(() => {
      FakeSpeechRecognition.instances[0].emitResult('what is stuck', true);
    });
    fireEvent.click(button);

    // The filter has already been applied -- no timer was armed, so no advanceTimersByTime.
    expect(onFilter).toHaveBeenCalledWith('stuck');
    // And there is nothing to cancel, so there is no chip offering to.
    expect(screen.queryByTestId('voice-intent-chip')).toBeNull();
  });

  it('does NOT send a mutation: opens the deck with text and changes nothing else', () => {
    const onOpenDeck = jest.fn();
    const onHighlight = jest.fn();
    const onFilter = jest.fn();
    render(
      <FleetVoice
        sessions={sessions}
        onOpenDeck={onOpenDeck}
        onHighlight={onHighlight}
        onFilter={onFilter}
      />,
    );
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    act(() => {
      FakeSpeechRecognition.instances[0].emitResult(
        'steer agent-beta try the other branch',
        true,
      );
    });
    fireEvent.click(button);

    act(() => {
      jest.advanceTimersByTime(1500);
    });

    expect(onHighlight).toHaveBeenCalledWith('agent-beta');
    expect(onOpenDeck).toHaveBeenCalledWith(
      'agent-beta',
      'try the other branch',
    );
    expect(onFilter).not.toHaveBeenCalled();
    expect(screen.getByTestId('voice-deck-text')).toBeTruthy();
  });

  it('cancels synthesis and returns to listening on barge-in', () => {
    render(<FleetVoice sessions={sessions} />);
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    act(() => {
      FakeSpeechRecognition.instances[0].emitResult('what is stuck', true);
    });
    fireEvent.click(button);

    act(() => {
      jest.advanceTimersByTime(1500);
    });
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'SPEAKING',
    );

    const before = cancelCount;
    act(() => {
      FakeSpeechRecognition.instances[0].emitResult('stop', false);
    });
    expect(cancelCount).toBeGreaterThan(before);
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'LISTENING',
    );
  });

  it('disables the button with a reason when the browser is unsupported', () => {
    uninstallRecognition();
    render(<FleetVoice sessions={sessions} />);
    const button = screen.getByTestId('voice-ptt') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(screen.getByTestId('voice-disabled-reason').textContent).toContain(
      'Voice unavailable',
    );
  });

  /**
   * ESCAPE CANCELS A MUTATION, NOT A QUESTION.
   *
   * The grace window is mutation-only (see FleetVoice's own comment), so this test now exercises
   * a STOP -- the case where 1.5 seconds of cancellation genuinely protects someone, because the
   * command would change a running agent. It previously used "what is stuck", a query that has
   * no window to cancel, so the chip was never there to escape from and the test was asserting a
   * behaviour the design had deliberately removed.
   *
   * The two things worth checking are both here: nothing is dispatched while the window is open,
   * and Escape closes it so nothing is dispatched afterwards either.
   */
  it('cancels a pending MUTATION on Escape', () => {
    const onOpenDeck = jest.fn();
    const onHighlight = jest.fn();
    render(
      <FleetVoice sessions={sessions} onOpenDeck={onOpenDeck} onHighlight={onHighlight} />,
    );
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    act(() => {
      FakeSpeechRecognition.instances[0].emitResult('stop agent-beta', true);
    });
    fireEvent.click(button);

    // A mutation DOES show a chip: there is something real to take back for 1.5s.
    expect(screen.getByTestId('voice-intent-chip')).toBeTruthy();
    // And it has NOT acted yet -- that is the whole value of the window.
    expect(onHighlight).not.toHaveBeenCalled();

    act(() => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });

    expect(screen.queryByTestId('voice-intent-chip')).toBeNull();

    act(() => {
      jest.advanceTimersByTime(1500);
    });
    // Escape means it never runs, even after the window would have closed.
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it('shows a visible state WORD, not only a colour', () => {
    render(<FleetVoice sessions={sessions} />);
    const word = screen.getByTestId('voice-state-word');
    expect(word.textContent).toBe('IDLE');

    // ONE click. The control toggles, so this is the whole gesture.
    fireEvent.click(screen.getByTestId('voice-ptt'));
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'LISTENING',
    );
  });
});
