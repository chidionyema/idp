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
// `jest` IS DELIBERATELY THE GLOBAL HERE, NOT THE @jest/globals IMPORT. backstage-cli transpiles
// with @swc/jest, whose jest pass hoists `jest.mock(...)` above the imports only when it sees the
// bare global; with `jest` imported the call stays AFTER the require, the real module is already
// loaded, and the factory mocks nothing (measured 2026-09-22).
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FacePage } from './FacePage';

// This suite pins the LEGACY voice path's button mapping (useEstateVoice). FacePage's default
// path is the router (useVoiceRouter, 2026-10-16); the flag is read per render, so the suite
// routes itself to the path it tests before each render.
beforeEach(() => {
  window.localStorage.setItem('estate.face.voice', 'legacy');
});

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
// useResearch drags the catalogue graph in through useEstate (the same chain that
// breaks core-plugin-api under jsdom here); the page renders one list, so it gets
// a ready envelope and nothing else.
jest.mock('./useResearch', () => ({
  useResearch: () => ({ state: 'ready', claims: [] }),
}));

const mocked = require('./useEstateVoice').useEstateVoice as jest.Mock;

function voiceIn(state: EstateVoiceState, micRecoveryUrl?: string) {
  return {
    state,
    detail: state === 'error' ? 'microphone is off for this page — tap the mic to try again' : '',
    micRecoveryUrl,
    heard: '',
    reply: '',
    available: true,
    current: { engine: 'cloud', voice: 'hannah' },
    catalogue: { cloud: [], say: [], kokoro: [], piper: [] },
    selectVoice: jest.fn(),
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

  // (4) THE HOME-SCREEN ESCAPE, 2026-10-08. "tap again to be asked" is a lie inside a
  // standalone icon (useEstateVoice.ts: isStandaloneHomeScreen) -- the page must offer the one
  // fix that actually clears the refusal, and must not offer it when there is nothing to escape.
  it('offers a real link to Safari when the hook sets micRecoveryUrl', () => {
    mocked.mockReturnValue(voiceIn('error', 'https://catalogue.mumchimp.com/face'));
    render(<FacePage />);
    const link = screen.getByText('Open in Safari to use the mic') as HTMLAnchorElement;
    expect(link.tagName).toBe('A');
    expect(link.getAttribute('href')).toBe('https://catalogue.mumchimp.com/face');
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.getAttribute('rel')).toBe('noopener');
  });

  it('shows no recovery link for an ordinary error (Safari tab, Android, desktop)', () => {
    mocked.mockReturnValue(voiceIn('error'));
    render(<FacePage />);
    expect(screen.queryByText('Open in Safari to use the mic')).toBeNull();
  });
});

describe('FacePage — the mic button before the service has answered', () => {
  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  // 2026-10-14: `available` starts false, so every load announced "Voice is not available here"
  // until /voice/voices came back. A wait is not a refusal.
  it('says it is connecting, not that voice is unavailable, while the check is in flight', () => {
    mocked.mockReturnValue({ ...voiceIn('off'), available: false, checking: true });
    render(<FacePage />);
    expect(screen.getByTestId('face-mic')).toHaveTextContent('Connecting…');
    expect(screen.getByTestId('face-mic')).not.toHaveTextContent('not available');
  });

  it('still says voice is not available once the service has said so', () => {
    mocked.mockReturnValue({ ...voiceIn('off'), available: false, checking: false });
    render(<FacePage />);
    expect(screen.getByTestId('face-mic')).toHaveTextContent('Voice is not available here');
  });
});
