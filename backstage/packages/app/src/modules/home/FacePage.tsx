/**
 * /face: the estate's face, full screen, phone first. One page for every surface that talks to the
 * founder -- Fleet links here, Otto and Concierge send this link -- so there is one face, not three
 * (AGENTS.md section 6). Tap to talk; the estate hears, answers and speaks through the face.
 *
 * CHROME-FREE BY LAYER, NOT BY REQUEST (crew#1017: "nav sidebar still docked, not chrome-free").
 * `noHeader` on the page blueprint removes the page header, not the app's docked sidebar; this
 * component rendered inside the layout pane, 224px to the right of the sidebar, on every laptop.
 * A `position: fixed; inset: 0` layer at a z-index above every drawer and app bar paints over ALL
 * app chrome deterministically -- no dependency on Backstage's layout class names, which change
 * between versions, and nothing to keep in sync. The page IS the screen.
 *
 * THE AVATAR IS NEVER CROPPED BY THE CONTROLS (crew#1017: "'Tap to talk' cuts off avatar bottom").
 * The old layout was `grid-template-rows: 1fr auto`: the control block consumed viewport height
 * and the avatar's chest was cropped at the canvas bottom edge -- the 'upper' camera view ends
 * mid-torso wherever the canvas ends. The face now owns the whole viewport and the controls float
 * over it as a glass pill near the bottom, so the model is framed once by the camera, never by the
 * button.
 */
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import EstateFace from './EstateFace';
import FleetBackdrop from './FleetBackdrop';
import { useEstateVoice } from './useEstateVoice';

const LABEL: Record<string, string> = {
  off: 'Tap to talk',
  listening: 'Listening…',
  thinking: 'Thinking…',
  speaking: 'Speaking…',
  error: 'Tap to try again',
};

export function FacePage() {
  const voice = useEstateVoice();
  // A FAILED MICROPHONE MUST BE RE-ASKABLE -- and the tap must not depend on a state comparison
  // that has to be kept in step with the label below.
  //
  // The rule here was `on = state !== 'off' && state !== 'error'`, with the handler
  // `on ? stop() : start()`. That happens to re-ask in 'error', but it gets there by two
  // negations that must stay inverted against the label map: add a state, and the button
  // silently changes meaning. The label directly below already promises the behaviour --
  // `error: 'Tap to try again'` -- so the tap is expressed as the same fact: stop a live
  // microphone, start anything else. 'error' is not running, so it can only mean "ask again".
  // Matching FleetReactorApp.openVoice, which was fixed for the founder's phone on 2026-10-05
  // ("it says tap the mic to try again, and when you tap nothing happens" -- the tap WAS
  // firing, as a stop, on a microphone that had already failed).
  const live =
    voice.state === 'listening' ||
    voice.state === 'thinking' ||
    voice.state === 'speaking';
  const on = live;
  // The wordmark is the estate's own name (LAW 46), not a string in this file. On a chrome-free
  // page nothing else names the product, so it reads here, crisp on near-black -- the fix for
  // "Bytesync title washed out", which was the sidebar's faded wordmark doing the naming before.
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2000,
        background:
          'radial-gradient(ellipse at 50% 30%, #1d2533 0%, #0b0e14 70%)',
        color: '#e8edf5',
        overflow: 'hidden',
      }}
    >
      <FleetBackdrop />

      {/* The face owns the whole viewport; everything else floats over it. */}
      <EstateFace height="100%" />

      {/* THE WORDMARK, top centre under the status line. */}
      <div
        style={{
          position: 'absolute',
          top: 'calc(env(safe-area-inset-top, 0px) + 16px)',
          width: '100%',
          textAlign: 'center',
          fontSize: 13,
          fontWeight: 700,
          letterSpacing: '0.28em',
          textTransform: 'uppercase',
          color: 'rgba(232,237,245,0.92)',
          textShadow: '0 1px 8px rgba(11,14,20,0.8)',
          pointerEvents: 'none',
        }}
      >
        {title}
      </div>

      {/* THE CONTROLS, one glass pill floating over the avatar's lower edge. `pointerEvents:
          'none'` on the pill lets gaze/mouse through to the face everywhere except the button. */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          bottom: 'calc(env(safe-area-inset-bottom, 0px) + 16px)',
          width: 'min(480px, calc(100% - 32px))',
          display: 'grid',
          gap: 10,
          padding: '14px 16px',
          textAlign: 'center',
          background: 'rgba(11,14,20,0.55)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: '1px solid rgba(232,237,245,0.14)',
          borderRadius: 22,
          pointerEvents: 'none',
        }}
      >
        {voice.heard && (
          <div style={{ opacity: 0.65, fontSize: 14 }}>You: {voice.heard}</div>
        )}
        {voice.reply && (
          <div style={{ fontSize: 17, lineHeight: 1.45 }}>{voice.reply}</div>
        )}
        {voice.detail && (
          <div style={{ opacity: 0.55, fontSize: 12 }}>{voice.detail}</div>
        )}
        {/* ONE TAP, NOT A SETTINGS TOUR (2026-10-08). Set only when the mic was refused inside a
            home-screen icon, where iOS does not persist a grant and "tap again" replays the same
            refusal forever (useEstateVoice.ts: isStandaloneHomeScreen). `target="_blank"` from a
            standalone shell is handed to Safari as a real tab -- the one place this refusal
            actually clears -- so this is a working escape, not an instruction to go find a toggle. */}
        {voice.micRecoveryUrl && (
          <a
            href={voice.micRecoveryUrl}
            target="_blank"
            rel="noopener"
            style={{
              pointerEvents: 'auto',
              fontSize: 13,
              fontWeight: 600,
              color: '#7fd1b9',
              textDecoration: 'underline',
            }}
          >
            Open in Safari to use the mic
          </a>
        )}
        <button
          type="button"
          data-testid="face-mic"
          onClick={() => (live ? voice.stop() : voice.start())}
          disabled={!voice.available}
          style={{
            pointerEvents: 'auto',
            justifySelf: 'center',
            minWidth: 200,
            padding: '16px 28px',
            borderRadius: 999,
            border: 'none',
            fontSize: 17,
            fontWeight: 600,
            color: '#0b0e14',
            background: on ? '#7fd1b9' : '#e8edf5',
            cursor: voice.available ? 'pointer' : 'not-allowed',
            boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
          }}
        >
          {voice.available
            ? on
              ? `${LABEL[voice.state]} · tap to stop`
              : LABEL[voice.state]
            : 'Voice is not available here'}
        </button>
      </div>
    </div>
  );
}
