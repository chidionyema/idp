/**
 * THE FACE MIC BUTTON, FROM THE STATE THAT BROKE IT.
 *
 * The founder's phone, twice: "it says microphone is off for this page, tap the mic to try again,
 * and when you tap nothing happens." The tap was firing -- as a STOP, on a microphone that had
 * already failed. Fleet was fixed for that (FleetReactorApp.openVoice, 234fd3ced); the face is the
 * other surface, and nothing here exercised it.
 *
 * These are the invariants, stated as things that can fail:
 *
 *   1. In 'error' the tap ASKS AGAIN. It does not stop, and it does not do nothing.
 *   2. In 'error' the button is ENABLED. A retry you cannot press is a settings instruction.
 *   3. In a live state the tap STOPS -- the fix must not turn every tap into a start.
 *
 * The hook is mocked, because the defect is in the button's state->verb mapping and nothing else.
 * Mocking getUserMedia here would test the browser, not this page.
 */
// `jest` IS DELIBERATELY THE GLOBAL HERE, NOT THE @jest/globals IMPORT -- see FleetVoice.test.tsx:
// swc's jest pass hoists `jest.mock(...)` above the imports only when it sees the bare global.
import { describe, it, expect, afterEach } from '@jest/globals';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FacePage } from './FacePage';

// The hook's state union, spelled out rather than imported: this suite runs through the app's
// babel transform, which does not accept `import type`. The string set is the contract either way.
type EstateVoiceState = 'off' | 'listening' | 'thinking' | 'speaking' | 'error';

jest.mock('./useEstateVoice', () => ({
  useEstateVoice: jest.fn(),
}));
// Nothing in this test reaches the estate's app shell or the face renderer.
jest.mock('@backstage/frontend-plugin-api', () => ({
  configApiRef: { id: 'core.config' },
  useApi: () => ({ getOptionalString: () => 'Estate' }),
}));
jest.mock('./EstateFace', () => ({ __esModule: true, default: () => null }));
jest.mock('./FleetBackdrop', () => ({ __esModule: true, default: () => null }));

const mocked = require('./useEstateVoice').useEstateVoice as jest.Mock;

function voiceIn(state: EstateVoiceState) {
  return {
    state,
    detail: state === 'error' ? 'microphone is off for this page — tap the mic to try again' : '',
    heard: '',
    reply: '',
    available: true,
    start: jest.fn(),
    stop: jest.fn(),
  };
}

describe('FacePage — the mic button', () => {
  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  // (1) THE INVARIANT THE FOUNDER HIT.
  it('asks again when the microphone has failed, rather than stopping or doing nothing', () => {
    const voice = voiceIn('error');
    mocked.mockReturnValue(voice);

    render(<FacePage />);
    fireEvent.click(screen.getByTestId('face-mic'));

    expect(voice.start).toHaveBeenCalledTimes(1);
    expect(voice.stop).not.toHaveBeenCalled();
  });

  // (2) A RETRY THAT CANNOT BE PRESSED IS NOT A RETRY.
  it('leaves the button pressable in the error state', () => {
    mocked.mockReturnValue(voiceIn('error'));
    render(<FacePage />);
    expect(screen.getByTestId('face-mic')).toBeEnabled();
  });

  // (3) THE FIX MUST NOT SWALLOW A LIVE MICROPHONE INTO A RESTART.
  it.each(['listening', 'thinking', 'speaking'] as EstateVoiceState[])(
    'stops the microphone while it is live (%s)',
    state => {
      const voice = voiceIn(state);
      mocked.mockReturnValue(voice);

      render(<FacePage />);
      fireEvent.click(screen.getByTestId('face-mic'));

      expect(voice.stop).toHaveBeenCalledTimes(1);
      expect(voice.start).not.toHaveBeenCalled();
    },
  );

  // And the state it is meant to start from.
  it('starts from off', () => {
    const voice = voiceIn('off');
    mocked.mockReturnValue(voice);

    render(<FacePage />);
    fireEvent.click(screen.getByTestId('face-mic'));

    expect(voice.start).toHaveBeenCalledTimes(1);
    expect(voice.stop).not.toHaveBeenCalled();
  });

  // The promise on screen and the behaviour of the tap are the same fact, so pin them together:
  // whatever the button SAYS it will do when tapped, tapping it must do.
  it('does what its own label promises, in every state', () => {
    const saysTryAgain: Partial<Record<EstateVoiceState, boolean>> = {
      error: true,
      off: true, // "Tap to talk"
    };
    (['off', 'listening', 'thinking', 'speaking', 'error'] as EstateVoiceState[]).forEach(state => {
      cleanup();
      jest.clearAllMocks();
      const voice = voiceIn(state);
      mocked.mockReturnValue(voice);

      render(<FacePage />);
      fireEvent.click(screen.getByTestId('face-mic'));

      if (saysTryAgain[state]) {
        expect([state, voice.start.mock.calls.length]).toEqual([state, 1]);
      } else {
        expect([state, voice.stop.mock.calls.length]).toEqual([state, 1]);
      }
    });
  });
});
