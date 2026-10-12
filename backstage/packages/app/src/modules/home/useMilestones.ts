/*
 * The face's milestone voice: subscribe to the news stream and SPEAK the milestones the gate
 * above allows -- and only those.
 *
 * idp#5737 item 3. The pieces already existed and this file is the join between them: the news
 * stream carries the milestones (`n.<channel>` -> `{type:'story', on, story}`, published on
 * `/fleetview/stream` by serve.py), `voice.speak` says things, and `milestoneSpeech.ts` decides
 * whether a given milestone may be said aloud. Nothing here decides anything: it moves a decided
 * milestone to the mouth. That separation is what keeps the refusals testable.
 *
 * WHY `speak` IS PASSED IN, NOT CALLED HERE. `useEstateVoice` is the canonical voice engine
 * (AGENTS.md: every surface mounts the hook; none reaches around it). The face already holds that
 * hook and its `speak`; taking it as an argument keeps exactly one voice engine on the page and
 * keeps this file a subscriber, not a second mouth.
 *
 * WHY THE SUBSCRIPTION IS GATED ON THE TOGGLE. With the toggle off this opens no connection at
 * all -- not a connection whose frames are dropped. An open stream on a sleeping phone is a
 * battery cost for a feature the founder turned off, and "we are connected but staying quiet" is
 * the worst of both.
 *
 * THE STREAM IS THE ONE /fleet ALREADY READS. Same `/api/proxy/fleetview/stream`, same
 * authenticated `openSse` (the native `EventSource` cannot carry the token, so it 401s -- see
 * sse.ts). Session frames, cues and stories share that response; `milestoneFromFrame` is what
 * sorts a story out of a stream that is mostly about sessions, and returns null for the rest.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { openSse, type SseHandle } from './sse';
import {
  DEFAULT_MILESTONE_PREFS,
  milestoneFromFrame,
  pruneSpoken,
  shouldSpeak,
  type MilestonePrefs,
} from './milestoneSpeech';

const STORAGE_KEY = 'estate.face.milestones';

/**
 * The founder's standing choice, from the device it was made on. Anything unreadable, absent or
 * half-written falls back to the defaults -- which ship OFF. A corrupt value must never be read
 * as consent to talk.
 */
function readPrefs(): MilestonePrefs {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_MILESTONE_PREFS;
    const parsed = JSON.parse(raw) as Partial<MilestonePrefs>;
    return {
      ...DEFAULT_MILESTONE_PREFS,
      ...parsed,
      // Only a literal `true` turns the voice on: `"false"`, `1`, `undefined` and a garbled object
      // all mean quiet.
      enabled: parsed?.enabled === true,
    };
  } catch {
    return DEFAULT_MILESTONE_PREFS;
  }
}

export interface MilestoneSpeech {
  prefs: MilestonePrefs;
  setEnabled: (on: boolean) => void;
}

/**
 * Speak fleet milestones through `speak`, subject to the gate. Returns the standing prefs and the
 * one control the founder needs: on or off.
 */
export function useMilestones(speak: (text: string) => void): MilestoneSpeech {
  const fetchApi = useApi(fetchApiRef);
  const discoveryApi = useApi(discoveryApiRef);
  const [prefs, setPrefs] = useState<MilestonePrefs>(readPrefs);

  // What has already been said in the sliding hour. A ref, not state: it is remembered for the
  // cap, and a spoken stamp must not re-render the face.
  const spokenRef = useRef<number[]>([]);
  // The mouth is read at call time, so a re-created `speak` never restarts the stream (which
  // would drop frames and double-subscribe).
  const speakRef = useRef(speak);
  speakRef.current = speak;

  const setEnabled = useCallback((on: boolean) => {
    setPrefs(current => {
      const next = { ...current, enabled: on };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // A device that refuses storage (private mode, quota) still gets a working toggle for
        // this session; it just will not be remembered. Talking is not worth throwing for.
      }
      return next;
    });
  }, []);

  const { enabled, quietFromHour, quietToHour, maxPerHour } = prefs;

  useEffect(() => {
    if (!enabled) return undefined;
    let source: SseHandle | undefined;
    let closed = false;

    void (async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        if (closed) return;
        source = openSse(fetchApi, `${base}/fleetview/stream`, {
          onmessage: event => {
            const milestone = milestoneFromFrame(event.data);
            if (!milestone) return;
            const now = Date.now();
            const verdict = shouldSpeak(
              milestone,
              { enabled, quietFromHour, quietToHour, maxPerHour },
              spokenRef.current,
              now,
            );
            if (!verdict.speak) return;
            spokenRef.current = [...pruneSpoken(spokenRef.current, now), now];
            speakRef.current(verdict.text);
          },
        });
      } catch {
        // The face stays up and quiet. The stream is best-effort by design (same call as /fleet):
        // losing the news feed must not take down the surface the founder talks to.
        source = undefined;
      }
    })();

    return () => {
      closed = true;
      source?.close();
    };
  }, [enabled, quietFromHour, quietToHour, maxPerHour, fetchApi, discoveryApi]);

  return { prefs, setEnabled };
}
