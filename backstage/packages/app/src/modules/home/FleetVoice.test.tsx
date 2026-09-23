// `jest` IS DELIBERATELY THE GLOBAL HERE, NOT THE @jest/globals IMPORT.
//
// backstage-cli transpiles with @swc/jest, and swc's jest pass hoists `jest.mock(...)` above the
// imports only when it sees the bare global identifier. With `jest` imported from '@jest/globals'
// the call stays where it is written, which in CommonJS output is AFTER `require('./FleetVoice')`
// -- the real module is already in the registry and the factory mocks nothing. Measured
// 2026-09-22 with a one-assertion probe: identical file, imported `jest` fails, global `jest`
// passes. Everything else still comes from @jest/globals.
import { describe, it, expect, afterEach, beforeEach } from '@jest/globals';
import { render, fireEvent, act, screen } from '@testing-library/react';
import FleetVoice, { parseIntent } from './FleetVoice';
import type { Session } from './fleetBoard';

// ---------------------------------------------------------------------------
// The engine, which is the seam now
// ---------------------------------------------------------------------------

// THE ENGINE OWNS THE MICROPHONE, SO THE ENGINE IS WHAT THESE TESTS DRIVE.
//
// `8201aa21c feat(voice,ironcage): land the local-floor work` replaced the browser recogniser
// inside `startListening` with `void engine.start()`. The transcript now arrives from whisper
// through useEstateVoice as `engine.heard`, and listening/thinking/speaking are `engine.state`,
// mapped onto this component's vocabulary by one effect. The tests below went on emitting
// `SpeechRecognition` results at a component that no longer constructs one, so six of them were
// asserting a transport that had been deleted -- the click produced no instance and the state
// word never left IDLE.
//
// The real hook cannot run here either: `start()` calls `getUserMedia` and `new AudioContext`,
// and jsdom has neither, so it would answer every click with state 'error'. So the hook is the
// mock and the component's own behaviour -- intent parsing, the mutation grace window, the deck,
// Escape, the state word -- is what is under test, which is the part that is this file's.
const mockStart = jest.fn();
const mockStop = jest.fn();
const mockSpeak = jest.fn();
const mockSilence = jest.fn();
/** Set on every render of the mocked hook; `engineReports` pushes through it. */
let mockPush: ((patch: Record<string, string>) => void) | null = null;

jest.mock('./useEstateVoice', () => {
  const React = require('react');
  const useEstateVoice = () => {
    const [engine, setEngine] = React.useState({
      state: 'off',
      heard: '',
      detail: '',
    });
    mockPush = (patch: Record<string, string>) =>
      setEngine((prev: Record<string, string>) => ({ ...prev, ...patch }));
    return {
      ...engine,
      reply: '',
      available: true,
      start: mockStart,
      stop: mockStop,
      speak: mockSpeak,
      silence: mockSilence,
      catalogue: null,
      voiceLog: [],
    };
  };
  // FleetVoice imports the NAMED export (`import { useEstateVoice } from './useEstateVoice'`),
  // so a `default` here mocks nothing and the real hook keeps running.
  return { __esModule: true, useEstateVoice };
});

/** What the estate engine reports back, as one act()-wrapped update. */
function engineReports(patch: {
  state?: string;
  heard?: string;
  detail?: string;
}) {
  if (!mockPush) throw new Error('FleetVoice has not been rendered yet');
  const push = mockPush;
  act(() => {
    push(patch as Record<string, string>);
  });
}

// ---------------------------------------------------------------------------
// Fakes for jsdom
// ---------------------------------------------------------------------------

/**
 * All that is left of the browser recogniser: a capability probe.
 *
 * `supported` in FleetVoice is still `recognitionCtor !== null && synthesisAvailable`, so the
 * constructor has to exist for the button to be enabled even though nothing constructs one any
 * more. Removing the probe is a product decision (it gates the estate engine on a Chrome API the
 * estate engine does not use) and not this file's to make, so the stub stays and the "unsupported"
 * test below still deletes it to prove the disabled path.
 */
class FakeSpeechRecognition {
  start() {}
  stop() {}
  abort() {}
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
  mockStart.mockClear();
  mockStop.mockClear();
  mockSpeak.mockClear();
  mockSilence.mockClear();
  mockPush = null;
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
  it('starts the estate engine on press and shows what it heard', () => {
    render(<FleetVoice sessions={sessions} />);
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    expect(mockStart).toHaveBeenCalledTimes(1);

    // The word follows the ENGINE, not the click: the microphone is open when the engine says
    // it is, so a start that fails leaves the button honest instead of showing LISTENING at a
    // dead transport.
    engineReports({ state: 'listening' });
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'LISTENING',
    );

    engineReports({ heard: 'what is' });
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
    engineReports({ state: 'listening', heard: 'what is stuck' });
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
    engineReports({
      state: 'listening',
      heard: 'steer agent-beta try the other branch',
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

  /**
   * BARGE-IN IS THE ENGINE'S JOB NOW, SO THIS TESTS THE HALF THAT IS STILL THIS COMPONENT'S.
   *
   * The old version asserted `window.speechSynthesis.cancel()` was called from the component's
   * own `onresult` interceptor. That interceptor is dead code after 8201aa21c -- it reads
   * `recognitionRef.current`, which nothing assigns any more -- and the capability moved into the
   * engine, whose VAD keeps running through playback and stops the audio itself.
   *
   * What remains here, and is worth protecting, is that the component FOLLOWS the engine out of
   * SPEAKING. Without the mapping effect a person who talks over the answer sees a surface still
   * claiming to be speaking while the engine is already listening to them.
   */
  it('follows the engine back to LISTENING when it hears a barge-in', () => {
    render(<FleetVoice sessions={sessions} />);
    const button = screen.getByTestId('voice-ptt');

    fireEvent.click(button);
    engineReports({ state: 'listening', heard: 'what is stuck' });
    fireEvent.click(button);

    act(() => {
      jest.advanceTimersByTime(1500);
    });
    // The answer is spoken by the estate engine, not by the OS formant voices, and the engine
    // reports the playback it was asked for.
    expect(mockSpeak).toHaveBeenCalled();
    engineReports({ state: 'speaking' });
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'SPEAKING',
    );

    // The VAD hears the person over the playback and the engine goes back to listening.
    engineReports({ state: 'listening' });
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
    engineReports({ state: 'listening', heard: 'stop agent-beta' });
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

    // ONE click. The control toggles, so this is the whole gesture -- and the word is the
    // engine's answer to it, which is why the click alone is not enough to show LISTENING.
    fireEvent.click(screen.getByTestId('voice-ptt'));
    engineReports({ state: 'listening' });
    expect(screen.getByTestId('voice-state-word').textContent).toBe(
      'LISTENING',
    );
  });
});
