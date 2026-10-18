/**
 * THE FACE ON THE ROUTER PATH -- the surface the founder actually sees (2026-10-16).
 *
 * The face's voice moved to useVoiceRouter (streaming, lip-synced, first audio median 2.26s);
 * these pin what that move must look like on the page, stated as things that can fail:
 *
 *   1. While the router is being probed the button says "Connecting…" and is DISABLED -- the
 *      founder never mistaps a voice that is not there yet (the "Connecting…" UX, idp#6149).
 *   2. The one refusal a tap cannot clear (iOS home-screen icon) shows the one-tap Safari
 *      escape, the same affordance the legacy path had -- the shape never depends on the path.
 *   3. Partials are captioned live: the words appear while the person is still speaking.
 *   4. A long reply is CLAMPED -- the caption pill must never grow over the face again.
 *   5. No flag means the router path: a fresh face never lands on the legacy loop by accident.
 */
// `jest` IS DELIBERATELY THE GLOBAL HERE, NOT THE @jest/globals IMPORT -- see
// FacePage.micRetry.test.tsx for the measurement behind that.
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FacePage } from './FacePage';

jest.mock('./useVoiceRouter', () => ({
  useVoiceRouter: jest.fn(),
}));
jest.mock('./useEstateVoice', () => ({
  useEstateVoice: jest.fn(),
  getClauseSink: () => null,
  setClauseSink: () => undefined,
}));
jest.mock('@backstage/frontend-plugin-api', () => ({
  configApiRef: { id: 'core.config' },
  useApi: () => ({ getOptionalString: () => 'Estate' }),
}));
jest.mock('./EstateFace', () => ({ __esModule: true, default: () => null }));
jest.mock('./FleetBackdrop', () => ({ __esModule: true, default: () => null }));
jest.mock('./useResearch', () => ({
  useResearch: () => ({ state: 'ready', claims: [] }),
}));

const routerHook = require('./useVoiceRouter').useVoiceRouter as jest.Mock;
const legacyHook = require('./useEstateVoice').useEstateVoice as jest.Mock;

function routerIn(over: Record<string, unknown> = {}) {
  return {
    state: 'off',
    partial: '',
    heard: '',
    reply: '',
    detail: '',
    checking: false,
    reachable: true,
    available: true,
    start: jest.fn(),
    stop: jest.fn(),
    speak: jest.fn(),
    ...over,
  };
}

function legacyIdle() {
  return {
    state: 'off',
    heard: '',
    reply: '',
    detail: '',
    available: true,
    start: jest.fn(),
    stop: jest.fn(),
    speak: jest.fn(),
  };
}

beforeEach(() => {
  window.localStorage.removeItem('estate.face.voice');
  legacyHook.mockReturnValue(legacyIdle());
});

afterEach(() => {
  cleanup();
  window.localStorage.removeItem('estate.face.voice');
});

describe('FacePage on the router voice path', () => {
  it('says Connecting… and disables the mic while the router is still being probed', () => {
    routerHook.mockReturnValue(routerIn({ checking: true, available: false }));
    render(<FacePage />);
    const button = screen.getByTestId('face-mic');
    expect(button).toHaveTextContent('Connecting…');
    expect(button).toBeDisabled();
  });

  it('shows the one-tap Safari escape for the one refusal a tap cannot clear', () => {
    routerHook.mockReturnValue(
      routerIn({
        state: 'error',
        micRecoveryUrl: 'http://localhost:3100/face',
        detail: 'the home-screen icon cannot keep microphone access on iOS',
      }),
    );
    render(<FacePage />);
    const link = screen.getByText('Open in Safari to use the mic');
    expect(link).toHaveAttribute('href', 'http://localhost:3100/face');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('captions the partial while the person is still speaking', () => {
    routerHook.mockReturnValue(
      routerIn({ state: 'listening', partial: 'what is the burn' }),
    );
    render(<FacePage />);
    expect(screen.getByText(/You: what is the burn/)).toBeInTheDocument();
  });

  it('clamps a long reply to three lines so the caption never covers the face', () => {
    routerHook.mockReturnValue(
      routerIn({
        state: 'speaking',
        reply: 'word '.repeat(400),
      }),
    );
    render(<FacePage />);
    const caption = screen
      .getByText(/^word/)
      .closest('div') as HTMLElement;
    expect(caption.style.webkitLineClamp).toBe('3');
    expect(caption.style.overflow).toBe('hidden');
  });

  it('wires the mic button to the router hook when no flag is set', () => {
    const start = jest.fn();
    routerHook.mockReturnValue(routerIn({ start }));
    render(<FacePage />);
    fireEvent.click(screen.getByTestId('face-mic'));
    expect(start).toHaveBeenCalledTimes(1);
    expect(legacyHook.mock.results.length).toBeGreaterThan(0); // mounted (rules of hooks)…
    const legacy = legacyHook.mock.results[0].value;
    expect(legacy.start).not.toHaveBeenCalled(); // …but never wired to the page
  });

  it('wires the mic button to the legacy hook under estate.face.voice=legacy', () => {
    window.localStorage.setItem('estate.face.voice', 'legacy');
    const start = jest.fn();
    legacyHook.mockReturnValue({ ...legacyIdle(), start });
    render(<FacePage />);
    fireEvent.click(screen.getByTestId('face-mic'));
    expect(start).toHaveBeenCalledTimes(1);
    const router = routerHook.mock.results[0].value;
    expect(router.start).not.toHaveBeenCalled();
  });
});
