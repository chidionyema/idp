/*
 * The router path names a missing microphone API instead of throwing a TypeError.
 *
 * WHY THIS TEST EXISTS. 2026-10-19: the phone e2e "/face names a fix this device can follow" hides
 * navigator.mediaDevices and failed on every backstage lane with the page saying
 * "undefined is not an object (evaluating 'navigator.mediaDevices.getUserMedia')". /face's default
 * path is useVoiceRouter, whose start() called getUserMedia unguarded; the legacy path's
 * micBlocker already had the right words.
 */
import { act, renderHook } from '@testing-library/react';
import { useVoiceRouter } from './useVoiceRouter';

describe('useVoiceRouter.start with no microphone API', () => {
  const original = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
  const secure = Object.getOwnPropertyDescriptor(window, 'isSecureContext');

  beforeEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, get: () => undefined });
  });

  afterEach(() => {
    if (original) Object.defineProperty(navigator, 'mediaDevices', original);
    else delete (navigator as any).mediaDevices;
    if (secure) Object.defineProperty(window, 'isSecureContext', secure);
    else delete (window as any).isSecureContext;
  });

  it('names the device on a secure page and does not throw', async () => {
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true });
    const { result } = renderHook(() => useVoiceRouter());
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.state).toBe('error');
    expect(result.current.detail).toMatch(/microphone/i);
    expect(result.current.detail).not.toMatch(/undefined is not an object|getUserMedia/);
  });

  it('names the URL on an insecure page', async () => {
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false });
    const { result } = renderHook(() => useVoiceRouter());
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.detail).toMatch(/https/);
  });
});
