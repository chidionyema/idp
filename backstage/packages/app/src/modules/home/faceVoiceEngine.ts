import { useRef } from 'react';

// WHICH VOICE ENGINE THE FACE TALKS THROUGH, DECIDED ONCE (idp#6594 follow-up).
//
// The router path is the default, but production has no voice router behind /voice/*: measured
// 2026-10-19, https://catalogue.mumchimp.com/voice/ws and /voice/turns answer the SPA's HTML. The
// only voice door there is /api/proxy/fleetview/voice/*, which is the legacy engine's. So a
// production face whose router probe settles unreachable used to sit on a dead button; it now
// falls back to the legacy engine, which that door serves.
//
// STICKY, because the engines must not swap under a live conversation: the first answer wins.
// Once the router has been reached the face stays on it through any later blip; once it has given
// up on the router it stays on legacy even if the router appears later. An explicit
// `estate.face.voice = legacy` always wins and is never stored (it is read per render).

export type FaceVoiceEngine = 'router' | 'legacy';

export interface RouterProbe {
  checking?: boolean;
  reachable?: boolean;
}

/** The router has been probed and is not there. Strict `=== false`: a hook that does not report
 *  reachability is never taken for an unreachable one. */
export function routerGaveUp(p: RouterProbe): boolean {
  return p.checking === false && p.reachable === false;
}

export function useFaceVoiceEngine(
  prefersLegacy: boolean,
  router: RouterProbe,
): FaceVoiceEngine {
  const decided = useRef<FaceVoiceEngine | null>(null);
  if (prefersLegacy) return 'legacy';
  if (decided.current === null) {
    if (router.reachable === true) decided.current = 'router';
    else if (routerGaveUp(router)) decided.current = 'legacy';
  }
  return decided.current ?? 'router';
}
