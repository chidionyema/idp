import { describe, it, expect } from '@jest/globals';
import { renderHook } from '@testing-library/react';
import { routerGaveUp, useFaceVoiceEngine, RouterProbe } from './faceVoiceEngine';

const pick = (legacy: boolean, first: RouterProbe) =>
  renderHook(({ l, p }) => useFaceVoiceEngine(l, p), {
    initialProps: { l: legacy, p: first },
  });

describe('routerGaveUp', () => {
  it('is only true once the probe settled AND failed', () => {
    expect(routerGaveUp({ checking: true, reachable: false })).toBe(false);
    expect(routerGaveUp({ checking: false, reachable: true })).toBe(false);
    expect(routerGaveUp({ checking: false, reachable: false })).toBe(true);
  });
  it('never mistakes a hook that does not report reachability for an unreachable router', () => {
    expect(routerGaveUp({ checking: false })).toBe(false);
  });
});

describe('useFaceVoiceEngine', () => {
  it('stays on the router while the first probe is in flight', () => {
    expect(pick(false, { checking: true, reachable: false }).result.current).toBe('router');
  });

  it('falls back to legacy when the router is not there (production)', () => {
    expect(pick(false, { checking: false, reachable: false }).result.current).toBe('legacy');
  });

  it('stays on the router once reached, through a later blip', () => {
    const h = pick(false, { checking: false, reachable: true });
    h.rerender({ l: false, p: { checking: false, reachable: false } });
    expect(h.result.current).toBe('router');
  });

  it('stays on legacy once it gave up, even if the router appears later', () => {
    const h = pick(false, { checking: true, reachable: false });
    h.rerender({ l: false, p: { checking: false, reachable: false } });
    h.rerender({ l: false, p: { checking: false, reachable: true } });
    expect(h.result.current).toBe('legacy');
  });

  it('the explicit legacy flag wins and is not remembered', () => {
    const h = pick(true, { checking: false, reachable: true });
    expect(h.result.current).toBe('legacy');
    h.rerender({ l: false, p: { checking: false, reachable: true } });
    expect(h.result.current).toBe('router');
  });
});
